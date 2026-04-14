from typing import List
from datetime import datetime, timedelta
from storage import BanqueStorage
from models import (
    CompteCreateCourant, CompteCreateEpargne, CompteCreateBloque,
    CompteUpdate, CompteResponse
)

DUREE_BLOCAGE_JOURS = 30

class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class BanqueService:
    def __init__(self, storage: BanqueStorage):
        self.storage = storage

    def _get_or_404(self, numero: str) -> dict:
        compte = self.storage.get(numero)
        if not compte:
            raise ServiceError("Compte introuvable.", status_code=404)
        return compte

    def _peut_retirer(self, compte: dict, montant: float) -> bool:
        date_deblocage = compte.get("date_deblocage")
        if compte["type"] == "bloque" and date_deblocage and datetime.now() < date_deblocage:
            raise ServiceError("Compte bloqué : retrait impossible avant la date de déblocage.")
        
        if compte["type"] == "courant":
            if compte["solde"] - montant < -compte["decouvert"]:
                raise ServiceError("Dépassement du découvert autorisé.")
        elif compte["solde"] - montant < 0:
            raise ServiceError("Solde insuffisant.")
        return True

    def creer_compte_courant(self, data: CompteCreateCourant) -> CompteResponse:
        self.storage.ajouter(data.model_dump(exclude_unset=True))
        return CompteResponse(**self._get_or_404(data.numero))

    def creer_compte_epargne(self, data: CompteCreateEpargne) -> CompteResponse:
        self.storage.ajouter(data.model_dump(exclude_unset=True))
        return CompteResponse(**self._get_or_404(data.numero))

    def creer_compte_bloque(self, data: CompteCreateBloque) -> CompteResponse:
        dump = data.model_dump(exclude_unset=True)
        dump["date_deblocage"] = dump["date_creation"] + timedelta(days=DUREE_BLOCAGE_JOURS)
        self.storage.ajouter(dump)
        return CompteResponse(**self._get_or_404(data.numero))

    def deposer(self, numero: str, montant: float) -> CompteResponse:
        compte = self._get_or_404(numero)
        compte["solde"] += montant
        self.storage.maj(numero, {"solde": compte["solde"]})
        return CompteResponse(**compte)

    def retirer(self, numero: str, montant: float) -> CompteResponse:
        compte = self._get_or_404(numero)
        self._peut_retirer(compte, montant)
        compte["solde"] -= montant
        self.storage.maj(numero, {"solde": compte["solde"]})
        return CompteResponse(**compte)

    def appliquer_interets(self) -> dict:
        comptes = self.storage.tous()
        total_gains, comptes_maj = 0.0, 0
        for c in comptes:
            if c["type"] == "epargne" and c.get("taux"):
                gain = c["solde"] * (c["taux"] / 100)
                self.storage.maj(c["numero"], {"solde": c["solde"] + gain})
                total_gains += gain
                comptes_maj += 1
        return {"message": "Intérêts appliqués.", "total_gains": total_gains, "comptes_mis_a_jour": comptes_maj}

    def supprimer(self, numero: str) -> None:
        self._get_or_404(numero) # Lève 404 si inexistant
        self.storage.supprimer(numero)

    def modifier(self, numero: str, maj: CompteUpdate) -> CompteResponse:
        compte = self._get_or_404(numero)
        dump = maj.model_dump(exclude_unset=True)
        
        if "decouvert" in dump and compte["type"] != "courant":
            raise ServiceError("Le découvert ne concerne que les comptes courants.")
        if "taux" in dump and compte["type"] != "epargne":
            raise ServiceError("Le taux ne concerne que les comptes épargne.")
        if not dump:
            return CompteResponse(**compte)
            
        updated = self.storage.maj(numero, dump)
        return CompteResponse(**updated)

    def get_compte(self, numero: str) -> CompteResponse:
        return CompteResponse(**self._get_or_404(numero))

    def tous(self) -> List[CompteResponse]:
        return [CompteResponse(**c) for c in self.storage.tous()]

    def tous_par_type(self, type_compte: str) -> List[CompteResponse]:
        return [CompteResponse(**c) for c in self.storage.tous_par_type(type_compte)]