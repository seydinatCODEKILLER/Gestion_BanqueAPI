import json
import os
from typing import Optional, List, Dict, Any
from threading import Lock
from datetime import datetime


class StorageError(Exception):
    pass


class BanqueStorage:
    def __init__(self, json_path: str = "comptes.json"):
        self.json_path = json_path
        self._lock = Lock()
        self._init_file()

    def _init_file(self) -> None:
        if not os.path.exists(self.json_path):
            try:
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump({"comptes": []}, f, ensure_ascii=False, indent=2)
            except OSError as e:
                raise StorageError(f"Impossible de créer le fichier JSON: {e}")

    def _lire_donnees(self) -> dict:
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "comptes" not in data or not isinstance(data["comptes"], list):
                    return {"comptes": []}
                for c in data["comptes"]:
                    if "date_creation" in c and c["date_creation"]:
                        c["date_creation"] = datetime.fromisoformat(c["date_creation"])
                    if "date_deblocage" in c and c["date_deblocage"]:
                        c["date_deblocage"] = datetime.fromisoformat(c["date_deblocage"])
                return data
        except (OSError, json.JSONDecodeError) as e:
            raise StorageError(f"Erreur lecture JSON: {e}")

    def _serialiser_compte(self, compte: dict) -> dict:
        c = compte.copy()
        for champ in ["date_creation", "date_deblocage"]:
            if champ in c and isinstance(c[champ], datetime):
                c[champ] = c[champ].isoformat()
        return c

    def _ecrire_donnees(self, data: dict) -> None:
        try:
            serialized = {"comptes": [self._serialiser_compte(c) for c in data["comptes"]]}
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise StorageError(f"Erreur écriture JSON: {e}")

    def ajouter(self, compte: dict) -> None:
        with self._lock:
            data = self._lire_donnees()
            for c in data["comptes"]:
                if c["numero"] == compte["numero"]:
                    raise StorageError("Ce numéro de compte existe déjà.")
            data["comptes"].append(compte)
            self._ecrire_donnees(data)

    def get(self, numero: str) -> Optional[dict]:
        with self._lock:
            data = self._lire_donnees()
            for c in data["comptes"]:
                if c["numero"] == numero:
                    return c
            return None

    def maj(self, numero: str, champs: dict) -> Optional[dict]:
        with self._lock:
            data = self._lire_donnees()
            for i, c in enumerate(data["comptes"]):
                if c["numero"] == numero:
                    data["comptes"][i].update(champs)
                    self._ecrire_donnees(data)
                    return data["comptes"][i]
            return None

    def supprimer(self, numero: str) -> bool:
        with self._lock:
            data = self._lire_donnees()
            avant = len(data["comptes"])
            data["comptes"] = [c for c in data["comptes"] if c["numero"] != numero]
            if len(data["comptes"]) == avant:
                return False
            self._ecrire_donnees(data)
            return True

    def tous(self) -> List[dict]:
        with self._lock:
            data = self._lire_donnees()
            return sorted(data["comptes"], key=lambda x: x["titulaire"].lower())

    def tous_par_type(self, type_compte: str) -> List[dict]:
        return [c for c in self.tous() if c["type"] == type_compte]