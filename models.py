from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime

class CompteResponse(BaseModel):
    numero: str
    titulaire: str
    solde: float
    type: str
    decouvert: Optional[float] = None
    taux: Optional[float] = None
    date_creation: Optional[datetime] = None
    date_deblocage: Optional[datetime] = None
    est_bloque: Optional[bool] = None

    @property
    def est_verrouille(self) -> bool:
        if self.type != "bloque" or not self.date_deblocage:
            return False
        return datetime.now() < self.date_deblocage

    # Ajoute est_bloque dynamiquement à la sortie JSON
    def model_post_init(self, __context: any) -> None:
        self.est_bloque = self.est_verrouille


# --- Création (La validation est intégrée) ---

class CompteCreateCourant(BaseModel):
    numero: str = Field(..., pattern=r"^\d{6,20}$", examples=["12345678"])
    titulaire: str = Field(..., min_length=2, max_length=80, pattern=r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$", examples=["Jean Dupont"])
    solde: float = Field(0.0, ge=-1_000_000_000, le=1_000_000_000)
    type: Literal["courant"] = "courant"
    decouvert: float = Field(..., ge=0, le=1_000_000_000, examples=[500.00])

class CompteCreateEpargne(BaseModel):
    numero: str = Field(..., pattern=r"^\d{6,20}$", examples=["87654321"])
    titulaire: str = Field(..., min_length=2, max_length=80, pattern=r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$", examples=["Marie Martin"])
    solde: float = Field(0.0, ge=-1_000_000_000, le=1_000_000_000)
    type: Literal["epargne"] = "epargne"
    taux: float = Field(..., ge=0, le=100, examples=[2.5])

class CompteCreateBloque(BaseModel):
    numero: str = Field(..., pattern=r"^\d{6,20}$", examples=["11223344"])
    titulaire: str = Field(..., min_length=2, max_length=80, pattern=r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$", examples=["Pierre Durand"])
    solde: float = Field(0.0, ge=-1_000_000_000, le=1_000_000_000)
    type: Literal["bloque"] = "bloque"
    date_creation: datetime = Field(..., examples=["2026-02-07T14:30:00"])

class CompteUpdate(BaseModel):
    titulaire: Optional[str] = Field(None, min_length=2, max_length=80, pattern=r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$")
    decouvert: Optional[float] = Field(None, ge=0, le=1_000_000_000)
    taux: Optional[float] = Field(None, ge=0, le=100)

class DepotRetrait(BaseModel):
    montant: float = Field(..., gt=0, le=1_000_000_000, examples=[100.00])

class InteretsResponse(BaseModel):
    message: str
    total_gains: float
    comptes_mis_a_jour: int

class MessageResponse(BaseModel):
    message: str = Field(..., examples=["Opération réussie"])

class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Compte introuvable"])