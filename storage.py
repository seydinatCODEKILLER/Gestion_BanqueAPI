import os
from typing import Optional, List
from contextlib import contextmanager
import psycopg2
import psycopg2.extras
from psycopg2 import pool

class StorageError(Exception):
    pass

# Pool global de connexions
_pool: pool.ThreadedConnectionPool = None

def init_pool():
    global _pool
    _pool = pool.ThreadedConnectionPool(
        minconn=1, maxconn=10,
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ.get("DB_NAME", "banque"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
    )
    # Init DB au démarrage
    with _get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comptes (
                numero VARCHAR(20) PRIMARY KEY, titulaire VARCHAR(80) NOT NULL,
                solde DOUBLE PRECISION NOT NULL DEFAULT 0,
                type VARCHAR(10) NOT NULL CHECK (type IN ('courant','epargne','bloque')),
                decouvert DOUBLE PRECISION, taux DOUBLE PRECISION,
                date_creation TIMESTAMP, date_deblocage TIMESTAMP
            );
        """)

def close_pool():
    global _pool
    if _pool:
        _pool.closeall()

@contextmanager
def _get_cursor(dict_cursor=False):
    """Gère automatiquement la connexion, le commit et le rollback."""
    conn = _pool.getconn()
    try:
        cursor_factory = psycopg2.extras.RealDictCursor if dict_cursor else None
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise StorageError(str(e))
    finally:
        _pool.putconn(conn)


class BanqueStorage:
    def ajouter(self, compte: dict) -> None:
        sql = """INSERT INTO comptes 
                 (numero, titulaire, solde, type, decouvert, taux, date_creation, date_deblocage)
                 VALUES (%(numero)s, %(titulaire)s, %(solde)s, %(type)s, %(decouvert)s, %(taux)s, %(date_creation)s, %(date_deblocage)s)"""
        
        params = {
            "numero": compte.get("numero"),
            "titulaire": compte.get("titulaire"),
            "solde": compte.get("solde"),
            "type": compte.get("type"),
            "decouvert": compte.get("decouvert"),
            "taux": compte.get("taux"),
            "date_creation": compte.get("date_creation"),
            "date_deblocage": compte.get("date_deblocage"),
        }
        
        try:
            with _get_cursor() as cur:
                cur.execute(sql, params)
        except psycopg2.errors.UniqueViolation:
            raise StorageError("Ce numéro de compte existe déjà.")

    def get(self, numero: str) -> Optional[dict]:
        with _get_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT * FROM comptes WHERE numero = %s", (numero,))
            return cur.fetchone()

    def maj(self, numero: str, champs: dict) -> Optional[dict]:
        if not champs: return self.get(numero)
        colonnes = ", ".join(f"{k} = %({k})s" for k in champs)
        with _get_cursor(dict_cursor=True) as cur:
            cur.execute(f"UPDATE comptes SET {colonnes} WHERE numero = %(numero)s RETURNING *", {**champs, "numero": numero})
            return cur.fetchone()

    def supprimer(self, numero: str) -> bool:
        with _get_cursor() as cur:
            cur.execute("DELETE FROM comptes WHERE numero = %s RETURNING numero", (numero,))
            return cur.fetchone() is not None

    def tous(self) -> List[dict]:
        with _get_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT * FROM comptes ORDER BY LOWER(titulaire)")
            return cur.fetchall()

    def tous_par_type(self, type_compte: str) -> List[dict]:
        with _get_cursor(dict_cursor=True) as cur:
            cur.execute("SELECT * FROM comptes WHERE type = %s ORDER BY LOWER(titulaire)", (type_compte,))
            return cur.fetchall()