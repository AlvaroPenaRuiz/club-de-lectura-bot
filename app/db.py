import os
import sqlite3
from pathlib import Path
from contextlib import closing

DB_PATH = os.getenv("SQLITE_PATH", "/data/app.db")

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def _conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def inicializar():
    with closing(_conectar()) as conn, conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clubes (
                chat_id       INTEGER PRIMARY KEY,
                nombre_grupo  TEXT,
                libro         TEXT,
                autor         TEXT,
                tematica      TEXT,
                caracteristicas TEXT,
                formatos      TEXT,
                paginas       INTEGER,
                sinopsis      TEXT,
                saga          TEXT,
                capitulos     TEXT,
                version_capitulos INTEGER NOT NULL DEFAULT 1,
                actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                modo_presion  INTEGER NOT NULL DEFAULT 0,
                capitulos_cambiados_en TEXT,
                presion_enviado_en TEXT,
                modo_verguenza INTEGER NOT NULL DEFAULT 0,
                verguenza_enviada_version INTEGER,
                auto_resumen  INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS lectores (
                chat_id    INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                nombre     TEXT NOT NULL,
                username   TEXT,
                apuntado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id),
                FOREIGN KEY (chat_id) REFERENCES clubes(chat_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS progreso (
                chat_id           INTEGER NOT NULL,
                user_id           INTEGER NOT NULL,
                version_capitulos INTEGER NOT NULL,
                leido_en          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id, version_capitulos),
                FOREIGN KEY (chat_id) REFERENCES clubes(chat_id) ON DELETE CASCADE,
                FOREIGN KEY (chat_id, user_id)
                    REFERENCES lectores(chat_id, user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS whitelist (
                chat_id      INTEGER PRIMARY KEY,
                autorizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS capitulos_contenido (
                chat_id    INTEGER NOT NULL,
                numero     INTEGER NOT NULL,
                contenido  TEXT NOT NULL,
                subido_en  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, numero)
            );
        """)



def registrar_club(chat_id: int, nombre_grupo: str | None = None):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            INSERT INTO clubes (chat_id, nombre_grupo)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                nombre_grupo = COALESCE(excluded.nombre_grupo, clubes.nombre_grupo),
                actualizado_en = CURRENT_TIMESTAMP
        """, (chat_id, nombre_grupo))


def ver_club(chat_id: int):
    with closing(_conectar()) as conn:
        row = conn.execute("""
            SELECT chat_id, nombre_grupo, libro, autor, tematica,
                   caracteristicas, formatos, paginas, sinopsis, saga,
                   capitulos, version_capitulos
            FROM clubes
            WHERE chat_id = ?
        """, (chat_id,)).fetchone()
        return dict(row) if row else None


def cambiar_libro(chat_id: int, nombre_grupo: str | None, libro: str):
    registrar_club(chat_id, nombre_grupo)

    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes
            SET libro = ?,
                autor = NULL,
                tematica = NULL,
                caracteristicas = NULL,
                formatos = NULL,
                paginas = NULL,
                sinopsis = NULL,
                saga = NULL,
                capitulos = NULL,
                version_capitulos = 1,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        """, (libro, chat_id))

        conn.execute("DELETE FROM progreso WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM lectores WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM capitulos_contenido WHERE chat_id = ?", (chat_id,))


CAMPOS_LIBRO = {
    "titulo": "libro",
    "autor": "autor",
    "tematica": "tematica",
    "caracteristicas": "caracteristicas",
    "formatos": "formatos",
    "paginas": "paginas",
    "sinopsis": "sinopsis",
    "saga": "saga",
}


def modificar_campo(chat_id: int, campo: str, valor: str):
    columna = CAMPOS_LIBRO.get(campo)
    if not columna:
        raise ValueError(f"Campo desconocido: {campo}")

    if columna == "paginas":
        try:
            valor = int(valor)
        except ValueError:
            raise ValueError("El número de páginas debe ser un número entero.")

    with closing(_conectar()) as conn, conn:
        conn.execute(f"""
            UPDATE clubes
            SET {columna} = ?,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        """, (valor, chat_id))


def cambiar_capitulos(chat_id: int, nombre_grupo: str | None, capitulos: str):
    registrar_club(chat_id, nombre_grupo)

    with closing(_conectar()) as conn, conn:
        actual = conn.execute("""
            SELECT version_capitulos
            FROM clubes
            WHERE chat_id = ?
        """, (chat_id,)).fetchone()

        nueva_version = (actual["version_capitulos"] if actual else 0) + 1

        conn.execute("""
            UPDATE clubes
            SET capitulos = ?,
                version_capitulos = ?,
                capitulos_cambiados_en = CURRENT_TIMESTAMP,
                presion_enviado_en = NULL,
                verguenza_enviada_version = NULL,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE chat_id = ?
        """, (capitulos, nueva_version, chat_id))

        conn.execute("DELETE FROM progreso WHERE chat_id = ?", (chat_id,))


def apuntar_lector(chat_id: int, nombre_grupo: str | None, user_id: int, nombre: str, username: str | None):
    registrar_club(chat_id, nombre_grupo)

    with closing(_conectar()) as conn, conn:
        conn.execute("""
            INSERT INTO lectores (chat_id, user_id, nombre, username)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                nombre = excluded.nombre,
                username = excluded.username
        """, (chat_id, user_id, nombre, username))


def borrar_lector(chat_id: int, user_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            DELETE FROM lectores
            WHERE chat_id = ? AND user_id = ?
        """, (chat_id, user_id))


def marcar_leido(chat_id: int, user_id: int):
    with closing(_conectar()) as conn, conn:
        club = conn.execute("""
            SELECT version_capitulos, capitulos
            FROM clubes
            WHERE chat_id = ?
        """, (chat_id,)).fetchone()

        if not club or not club["capitulos"]:
            raise ValueError("No hay capítulos activos en este grupo.")

        lector = conn.execute("""
            SELECT 1
            FROM lectores
            WHERE chat_id = ? AND user_id = ?
        """, (chat_id, user_id)).fetchone()

        if not lector:
            raise ValueError("Primero tienes que apuntarte con /meapunto.")

        conn.execute("""
            INSERT INTO progreso (chat_id, user_id, version_capitulos)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, user_id, version_capitulos) DO NOTHING
        """, (chat_id, user_id, club["version_capitulos"]))


def desmarcar_leido(chat_id: int, user_id: int):
    with closing(_conectar()) as conn, conn:
        club = conn.execute("""
            SELECT version_capitulos, capitulos
            FROM clubes
            WHERE chat_id = ?
        """, (chat_id,)).fetchone()

        if not club or not club["capitulos"]:
            raise ValueError("No hay capítulos activos en este grupo.")

        conn.execute("""
            DELETE FROM progreso
            WHERE chat_id = ? AND user_id = ? AND version_capitulos = ?
        """, (chat_id, user_id, club["version_capitulos"]))


def ver_lectores(chat_id: int):
    with closing(_conectar()) as conn:
        rows = conn.execute("""
            SELECT user_id, nombre, username
            FROM lectores
            WHERE chat_id = ?
            ORDER BY LOWER(nombre)
        """, (chat_id,)).fetchall()
        return [dict(r) for r in rows]


# ─── Whitelist ───────────────────────────────────────────────


def grupo_autorizado(chat_id: int) -> bool:
    with closing(_conectar()) as conn:
        row = conn.execute(
            "SELECT 1 FROM whitelist WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return row is not None


def autorizar_grupo(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            INSERT INTO whitelist (chat_id) VALUES (?)
            ON CONFLICT(chat_id) DO NOTHING
        """, (chat_id,))


def desautorizar_grupo(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("DELETE FROM whitelist WHERE chat_id = ?", (chat_id,))


def quienes_leyeron(chat_id: int):
    with closing(_conectar()) as conn:
        club = conn.execute("""
            SELECT version_capitulos
            FROM clubes
            WHERE chat_id = ?
        """, (chat_id,)).fetchone()

        if not club:
            return []

        rows = conn.execute("""
            SELECT l.user_id, l.nombre, l.username
            FROM progreso p
            JOIN lectores l
              ON l.chat_id = p.chat_id
             AND l.user_id = p.user_id
            WHERE p.chat_id = ?
              AND p.version_capitulos = ?
            ORDER BY LOWER(l.nombre)
        """, (chat_id, club["version_capitulos"])).fetchall()

        return [dict(r) for r in rows]


def quienes_faltan(chat_id: int):
    with closing(_conectar()) as conn:
        club = conn.execute("""
            SELECT version_capitulos
            FROM clubes
            WHERE chat_id = ?
        """, (chat_id,)).fetchone()

        if not club:
            return []

        rows = conn.execute("""
            SELECT l.user_id, l.nombre, l.username
            FROM lectores l
            LEFT JOIN progreso p
              ON p.chat_id = l.chat_id
             AND p.user_id = l.user_id
             AND p.version_capitulos = ?
            WHERE l.chat_id = ?
              AND p.user_id IS NULL
            ORDER BY LOWER(l.nombre)
        """, (club["version_capitulos"], chat_id)).fetchall()

        return [dict(r) for r in rows]


# ─── Capítulos contenido ─────────────────────────────────────


def guardar_capitulos_contenido(chat_id: int, capitulos: list[tuple[int, str]]):
    with closing(_conectar()) as conn, conn:
        conn.executemany("""
            INSERT INTO capitulos_contenido (chat_id, numero, contenido)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, numero) DO UPDATE SET
                contenido = excluded.contenido,
                subido_en = CURRENT_TIMESTAMP
        """, [(chat_id, num, texto) for num, texto in capitulos])


def obtener_capitulo_contenido(chat_id: int, numero: int) -> str | None:
    with closing(_conectar()) as conn:
        row = conn.execute("""
            SELECT contenido
            FROM capitulos_contenido
            WHERE chat_id = ? AND numero = ?
        """, (chat_id, numero)).fetchone()
        return row["contenido"] if row else None


def obtener_capitulos_contenido(chat_id: int, numeros: list[int]) -> dict[int, str]:
    with closing(_conectar()) as conn:
        placeholders = ",".join("?" for _ in numeros)
        rows = conn.execute(f"""
            SELECT numero, contenido
            FROM capitulos_contenido
            WHERE chat_id = ? AND numero IN ({placeholders})
            ORDER BY numero
        """, [chat_id] + numeros).fetchall()
        return {r["numero"]: r["contenido"] for r in rows}


def listar_capitulos_contenido(chat_id: int) -> list[int]:
    with closing(_conectar()) as conn:
        rows = conn.execute("""
            SELECT numero
            FROM capitulos_contenido
            WHERE chat_id = ?
            ORDER BY numero
        """, (chat_id,)).fetchall()
        return [r["numero"] for r in rows]


# ─── Modo presión ─────────────────────────────────────────────


def activar_modo_presion(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes SET modo_presion = 1 WHERE chat_id = ?
        """, (chat_id,))


def desactivar_modo_presion(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes
            SET modo_presion = 0, presion_enviado_en = NULL
            WHERE chat_id = ?
        """, (chat_id,))


def grupos_con_modo_presion() -> list[dict]:
    with closing(_conectar()) as conn:
        rows = conn.execute("""
            SELECT chat_id, capitulos_cambiados_en, presion_enviado_en
            FROM clubes
            WHERE modo_presion = 1
        """).fetchall()
        return [dict(r) for r in rows]


def registrar_envio_presion(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes SET presion_enviado_en = CURRENT_TIMESTAMP WHERE chat_id = ?
        """, (chat_id,))


# ─── Modo vergüenza ──────────────────────────────────────────


def activar_modo_verguenza(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes SET modo_verguenza = 1 WHERE chat_id = ?
        """, (chat_id,))


def desactivar_modo_verguenza(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes
            SET modo_verguenza = 0, verguenza_enviada_version = NULL
            WHERE chat_id = ?
        """, (chat_id,))


def lector_pendiente_verguenza(chat_id: int) -> dict | None:
    """Devuelve al único lector pendiente cuando corresponde enviar el aviso."""
    with closing(_conectar()) as conn:
        club = conn.execute("""
            SELECT modo_verguenza, version_capitulos, verguenza_enviada_version
            FROM clubes
            WHERE chat_id = ?
        """, (chat_id,)).fetchone()
        if (
            not club
            or not club["modo_verguenza"]
            or club["verguenza_enviada_version"] == club["version_capitulos"]
        ):
            return None

        total = conn.execute(
            "SELECT COUNT(*) FROM lectores WHERE chat_id = ?", (chat_id,)
        ).fetchone()[0]
        if total <= 1:
            return None

        pendientes = conn.execute("""
            SELECT l.user_id, l.nombre, l.username
            FROM lectores l
            LEFT JOIN progreso p
              ON p.chat_id = l.chat_id
             AND p.user_id = l.user_id
             AND p.version_capitulos = ?
            WHERE l.chat_id = ?
              AND p.user_id IS NULL
        """, (club["version_capitulos"], chat_id)).fetchall()
        return dict(pendientes[0]) if len(pendientes) == 1 else None


def registrar_envio_verguenza(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes
            SET verguenza_enviada_version = version_capitulos
            WHERE chat_id = ?
        """, (chat_id,))


# ─── Auto-resumen ──────────────────────────────────────────


def activar_auto_resumen(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes SET auto_resumen = 1 WHERE chat_id = ?
        """, (chat_id,))


def desactivar_auto_resumen(chat_id: int):
    with closing(_conectar()) as conn, conn:
        conn.execute("""
            UPDATE clubes SET auto_resumen = 0 WHERE chat_id = ?
        """, (chat_id,))


def auto_resumen_activo(chat_id: int) -> bool:
    with closing(_conectar()) as conn:
        row = conn.execute("""
            SELECT auto_resumen FROM clubes WHERE chat_id = ?
        """, (chat_id,)).fetchone()
        return bool(row and row["auto_resumen"])
