from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from models import (
    CompteCreateCourant, CompteCreateEpargne, CompteCreateBloque,
    CompteUpdate, DepotRetrait, CompteResponse, MessageResponse,
    InteretsResponse, ErrorResponse
)
from storage import BanqueStorage, StorageError, init_pool, close_pool
from services import BanqueService, ServiceError  # Assure-toi que le fichier s'appelle bien service.py


# --- LIFESPAN (Gestion du cycle de vie de l'API) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    app.state.service = BanqueService(BanqueStorage())
    yield
    close_pool()


app = FastAPI(
    title="API Gestion de Comptes Bancaires",
    description="API REST pour la gestion de comptes bancaires (courant, épargne, bloqué) avec stockage PostgreSQL",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- EXCEPTION HANDLER GLOBAL (Le vrai plus senior) ---
@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(
        status_code=exc.status_code, 
        content={"detail": exc.message}
    )

@app.exception_handler(StorageError)
async def storage_error_handler(request: Request, exc: StorageError):
    return JSONResponse(
        status_code=500, 
        content={"detail": f"Erreur base de données : {str(exc)}"}
    )


# --- ROUTES RACINE ---

@app.get("/", tags=["Racine"], summary="Page d'accueil de l'API")
def racine():
    return {
        "message": "Bienvenue sur l'API Gestion de Comptes Bancaires",
        "documentation": "/docs",
        "version": "2.0.0"
    }


# --- ROUTES LECTURE ---

@app.get(
    "/comptes",
    response_model=List[CompteResponse],
    tags=["Comptes"],
    summary="Lister tous les comptes",
    description="Retourne la liste complète des comptes triés par titulaire."
)
def lister_comptes(request: Request):
    return request.app.state.service.tous()


@app.get(
    "/comptes/type/courant",
    response_model=List[CompteResponse],
    tags=["Comptes"],
    summary="Lister les comptes courants"
)
def lister_courants(request: Request):
    return request.app.state.service.tous_par_type("courant")


@app.get(
    "/comptes/type/epargne",
    response_model=List[CompteResponse],
    tags=["Comptes"],
    summary="Lister les comptes épargne"
)
def lister_epargnes(request: Request):
    return request.app.state.service.tous_par_type("epargne")


@app.get(
    "/comptes/type/bloque",
    response_model=List[CompteResponse],
    tags=["Comptes"],
    summary="Lister les comptes bloqués"
)
def lister_bloques(request: Request):
    return request.app.state.service.tous_par_type("bloque")


@app.get(
    "/comptes/{numero}",
    response_model=CompteResponse,
    tags=["Comptes"],
    summary="Récupérer un compte par numéro",
    responses={404: {"model": ErrorResponse, "description": "Compte introuvable"}}
)
def obtenir_compte(numero: str, request: Request):
    return request.app.state.service.get_compte(numero)


# --- ROUTES CRÉATION ---

@app.post(
    "/comptes/courant",
    response_model=CompteResponse,
    status_code=201,
    tags=["Création"],
    summary="Créer un compte courant",
    responses={400: {"model": ErrorResponse, "description": "Données invalides"}}
)
def creer_courant(data: CompteCreateCourant, request: Request):
    return request.app.state.service.creer_compte_courant(data)


@app.post(
    "/comptes/epargne",
    response_model=CompteResponse,
    status_code=201,
    tags=["Création"],
    summary="Créer un compte épargne",
    responses={400: {"model": ErrorResponse, "description": "Données invalides"}}
)
def creer_epargne(data: CompteCreateEpargne, request: Request):
    return request.app.state.service.creer_compte_epargne(data)


@app.post(
    "/comptes/bloque",
    response_model=CompteResponse,
    status_code=201,
    tags=["Création"],
    summary="Créer un compte bloqué",
    responses={400: {"model": ErrorResponse, "description": "Données invalides"}}
)
def creer_bloque(data: CompteCreateBloque, request: Request):
    return request.app.state.service.creer_compte_bloque(data)


# --- ROUTES OPÉRATIONS ---

@app.post(
    "/comptes/{numero}/deposer",
    response_model=CompteResponse,
    tags=["Opérations"],
    summary="Déposer de l'argent sur un compte",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Compte introuvable"}
    }
)
def deposer(numero: str, operation: DepotRetrait, request: Request):
    return request.app.state.service.deposer(numero, operation.montant)


@app.post(
    "/comptes/{numero}/retirer",
    response_model=CompteResponse,
    tags=["Opérations"],
    summary="Retirer de l'argent d'un compte",
    responses={
        400: {"model": ErrorResponse, "description": "Solde insuffisant ou compte bloqué"},
        404: {"model": ErrorResponse, "description": "Compte introuvable"}
    }
)
def retirer(numero: str, operation: DepotRetrait, request: Request):
    return request.app.state.service.retirer(numero, operation.montant)


@app.post(
    "/comptes/interets",
    response_model=InteretsResponse,
    tags=["Opérations"],
    summary="Appliquer les intérêts aux comptes épargne"
)
def appliquer_interets(request: Request):
    return request.app.state.service.appliquer_interets()


# --- ROUTES MODIFICATION / SUPPRESSION ---

@app.put(
    "/comptes/{numero}",
    response_model=CompteResponse,
    tags=["Comptes"],
    summary="Modifier un compte existant",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "Compte introuvable"}
    }
)
def modifier_compte(numero: str, maj: CompteUpdate, request: Request):
    return request.app.state.service.modifier(numero, maj)


@app.delete(
    "/comptes/{numero}",
    response_model=MessageResponse,
    tags=["Comptes"],
    summary="Supprimer un compte",
    responses={404: {"model": ErrorResponse, "description": "Compte introuvable"}}
)
def supprimer_compte(numero: str, request: Request):
    request.app.state.service.supprimer(numero)
    return {"message": "Compte supprimé avec succès."}