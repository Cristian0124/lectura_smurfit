"""Persistencia PESTEL compatible con SQLite local y PostgreSQL (Neon)."""
import os
import sqlite3

from flask import g
from werkzeug.security import generate_password_hash


RUTA_BD = os.environ.get("DB", os.path.join(os.path.dirname(__file__), "entorno.db"))
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USAR_POSTGRES = bool(DATABASE_URL)


class DuplicadoError(Exception):
    """Indica que un registro viola una restricción de unicidad."""


def _conectar():
    if USAR_POSTGRES:
        import psycopg2
        from psycopg2.extras import DictCursor

        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return ConexionPostgres(psycopg2.connect(
            url, cursor_factory=DictCursor, connect_timeout=10, sslmode="require"
        ))
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


class ConexionPostgres:
    """Adaptador pequeño para conservar el patrón connection.execute de SQLite."""
    def __init__(self, conexion):
        self.conexion = conexion

    def execute(self, sql, parametros=()):
        cursor = self.conexion.cursor()
        sql_postgres = sql.replace("?", "%s")
        try:
            cursor.execute(sql_postgres, parametros)
        except Exception as error:
            # El SQL solo contiene placeholders; no se registran sus parámetros ni secretos.
            if hasattr(error, "add_note"):
                error.add_note(f"SQL PostgreSQL que falló: {sql_postgres}")
            raise
        return cursor

    def commit(self):
        self.conexion.commit()

    def rollback(self):
        self.conexion.rollback()

    def close(self):
        self.conexion.close()


def obtener_conexion():
    """Devuelve una conexión asociada a la petición actual."""
    if "conexion_bd" not in g:
        g.conexion_bd = _conectar()
    return g.conexion_bd


def cerrar_conexion(_error=None):
    conexion = g.pop("conexion_bd", None)
    if conexion is not None:
        if _error is not None:
            conexion.rollback()
        conexion.close()


def _crear_esquema(conexion):
    if USAR_POSTGRES:
        sentencias = [
            """CREATE TABLE IF NOT EXISTS usuarios(id BIGSERIAL PRIMARY KEY, usuario TEXT UNIQUE NOT NULL,
                clave TEXT NOT NULL, rol TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS fuentes(id BIGSERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL,
                tipo TEXT NOT NULL, confiabilidad TEXT NOT NULL, url TEXT)""",
            """CREATE TABLE IF NOT EXISTS senales(id BIGSERIAL PRIMARY KEY, titulo TEXT NOT NULL, descripcion TEXT,
                factor TEXT NOT NULL, ambito TEXT NOT NULL, tipo TEXT NOT NULL, horizonte TEXT NOT NULL,
                fuente_id BIGINT REFERENCES fuentes(id), impacto INTEGER NOT NULL, probabilidad INTEGER NOT NULL,
                puntaje INTEGER NOT NULL, vigencia TEXT, estado TEXT NOT NULL DEFAULT 'Nueva',
                autor TEXT, creada TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS comentarios(id BIGSERIAL PRIMARY KEY, senal_id BIGINT NOT NULL
                REFERENCES senales(id), autor TEXT NOT NULL, contenido TEXT NOT NULL,
                creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        ]
        for sql in sentencias:
            conexion.execute(sql)
        for tabla, columna, tipo in [
            ("fuentes", "url", "TEXT"), ("senales", "justificacion", "TEXT"),
            ("senales", "fecha_publicacion", "TEXT"), ("senales", "fecha_identificacion", "TEXT"),
            ("senales", "implicaciones", "TEXT"),
        ]:
            existe = conexion.execute(
                "SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() "
                "AND table_name=? AND column_name=?", (tabla, columna)
            ).fetchone()
            if not existe:
                conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}")
    else:
        conexion.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, usuario TEXT UNIQUE NOT NULL,
            clave TEXT NOT NULL, rol TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fuentes(id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL, confiabilidad TEXT NOT NULL, url TEXT);
        CREATE TABLE IF NOT EXISTS senales(id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, descripcion TEXT,
            factor TEXT NOT NULL, ambito TEXT NOT NULL, tipo TEXT NOT NULL, horizonte TEXT NOT NULL,
            fuente_id INTEGER REFERENCES fuentes(id), impacto INTEGER NOT NULL, probabilidad INTEGER NOT NULL,
            puntaje INTEGER NOT NULL, vigencia TEXT, estado TEXT NOT NULL DEFAULT 'Nueva',
            autor TEXT, creada TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS comentarios(id INTEGER PRIMARY KEY, senal_id INTEGER NOT NULL
            REFERENCES senales(id), autor TEXT NOT NULL, contenido TEXT NOT NULL,
            creado TEXT DEFAULT CURRENT_TIMESTAMP);
        """)
        columnas_fuentes = {fila[1] for fila in conexion.execute("PRAGMA table_info(fuentes)")}
        if "url" not in columnas_fuentes:
            conexion.execute("ALTER TABLE fuentes ADD COLUMN url TEXT")
        columnas_senales = {fila[1] for fila in conexion.execute("PRAGMA table_info(senales)")}
        for columna in ("justificacion", "fecha_publicacion", "fecha_identificacion", "implicaciones"):
            if columna not in columnas_senales:
                conexion.execute(f"ALTER TABLE senales ADD COLUMN {columna} TEXT")


def inicializar_bd():
    """Crea el esquema/migraciones y agrega usuarios demo solo si no hay ninguno."""
    if not USAR_POSTGRES:
        os.makedirs(os.path.dirname(os.path.abspath(RUTA_BD)), exist_ok=True)
    conexion = _conectar()
    try:
        _crear_esquema(conexion)
        if USAR_POSTGRES:
            # Evita que dos workers creen las cuentas iniciales a la vez.
            conexion.execute("LOCK TABLE usuarios IN EXCLUSIVE MODE")
        if not conexion.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
            if USAR_POSTGRES:
                usuario_admin = os.environ.get("INITIAL_ADMIN_USER", "").strip()
                clave_admin = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
                if not usuario_admin or len(clave_admin) < 12:
                    raise RuntimeError(
                        "Configura INITIAL_ADMIN_USER y una INITIAL_ADMIN_PASSWORD de al menos 12 caracteres."
                    )
                usuarios_demo = [(usuario_admin, clave_admin, "admin")]
            else:
                usuarios_demo = [("admin", "admin123", "admin"), ("analista", "analista123", "analista"),
                                 ("directivo", "decisor123", "decisor")]
            for usuario, clave, rol in usuarios_demo:
                conexion.execute(
                    "INSERT INTO usuarios(usuario, clave, rol) VALUES (?, ?, ?)",
                    (usuario, generate_password_hash(clave), rol),
                )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def _es_integridad(error):
    if USAR_POSTGRES:
        import psycopg2
        return isinstance(error, psycopg2.IntegrityError)
    return isinstance(error, sqlite3.IntegrityError)


def _ejecutar(sql, parametros=()):
    return obtener_conexion().execute(sql, parametros)


def buscar_usuario(usuario):
    return _ejecutar("SELECT * FROM usuarios WHERE usuario=?", (usuario,)).fetchone()


def consultar_senales(rol, factor=None, horizonte=None):
    sql = """SELECT s.*, f.nombre AS fuente, f.confiabilidad AS conf, f.url AS fuente_url
             FROM senales s LEFT JOIN fuentes f ON f.id=s.fuente_id WHERE 1=1"""
    parametros = []
    if rol == "decisor":
        sql += " AND s.estado='Publicada'"
    if factor:
        sql += " AND s.factor=?"; parametros.append(factor)
    if horizonte:
        sql += " AND s.horizonte=?"; parametros.append(horizonte)
    return _ejecutar(sql + " ORDER BY s.puntaje DESC, s.id DESC", parametros).fetchall()


def contar_senales_por_factor(factor):
    return _ejecutar("SELECT COUNT(*) FROM senales WHERE factor=?", (factor,)).fetchone()[0]


def listar_fuentes():
    return _ejecutar("SELECT * FROM fuentes ORDER BY nombre").fetchall()


def listar_comentarios(senal_id):
    return _ejecutar("SELECT autor,contenido,creado FROM comentarios WHERE senal_id=? ORDER BY id",
                     (senal_id,)).fetchall()


def buscar_senal(senal_id):
    return _ejecutar("SELECT * FROM senales WHERE id=?", (senal_id,)).fetchone()


def registrar_senal(datos, autor):
    _ejecutar("""INSERT INTO senales(titulo,descripcion,implicaciones,factor,ambito,tipo,horizonte,fuente_id,
        impacto,probabilidad,puntaje,vigencia,autor) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", datos + (autor,))
    obtener_conexion().commit()


def registrar_senal_analizada(datos, autor, justificacion, fecha_publicacion, fecha_identificacion):
    _ejecutar("""INSERT INTO senales(titulo,descripcion,implicaciones,factor,ambito,tipo,horizonte,fuente_id,
        impacto,probabilidad,puntaje,vigencia,autor,justificacion,fecha_publicacion,fecha_identificacion)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        datos + (autor, justificacion, fecha_publicacion, fecha_identificacion))
    obtener_conexion().commit()


def actualizar_senal(senal_id, datos, estado):
    _ejecutar("""UPDATE senales SET titulo=?,descripcion=?,implicaciones=?,factor=?,ambito=?,tipo=?,horizonte=?,
        fuente_id=?,impacto=?,probabilidad=?,puntaje=?,vigencia=?,estado=? WHERE id=?""",
        datos + (estado, senal_id))
    obtener_conexion().commit()


def agregar_comentario(senal_id, autor, contenido):
    _ejecutar("INSERT INTO comentarios(senal_id,autor,contenido) VALUES(?,?,?)", (senal_id, autor, contenido))
    obtener_conexion().commit()


def agregar_fuente(nombre, tipo, confiabilidad, url=None):
    try:
        _ejecutar("INSERT INTO fuentes(nombre,tipo,confiabilidad,url) VALUES(?,?,?,?)",
                  (nombre, tipo, confiabilidad, url))
        obtener_conexion().commit()
    except Exception as error:
        obtener_conexion().rollback()
        if _es_integridad(error):
            raise DuplicadoError from error
        raise


def buscar_fuente_por_url(url):
    return _ejecutar("SELECT id FROM fuentes WHERE url=?", (url,)).fetchone()


def senal_ya_registrada(fuente_id, titulo, factor):
    return _ejecutar("SELECT 1 FROM senales WHERE fuente_id=? AND lower(titulo)=lower(?) AND factor=? LIMIT 1",
                     (fuente_id, titulo, factor)).fetchone() is not None


def crear_fuente_analizada(nombre, url):
    try:
        fila = _ejecutar("INSERT INTO fuentes(nombre,tipo,confiabilidad,url) VALUES(?,?,?,?) RETURNING id",
                         (nombre, "Pagina web", "Media", url)).fetchone()
        obtener_conexion().commit()
        return fila[0]
    except Exception as error:
        obtener_conexion().rollback()
        if _es_integridad(error):
            raise DuplicadoError from error
        raise


def listar_usuarios():
    return _ejecutar("SELECT usuario, rol FROM usuarios").fetchall()


def agregar_usuario(usuario, clave_hash, rol):
    try:
        _ejecutar("INSERT INTO usuarios(usuario,clave,rol) VALUES(?,?,?)", (usuario, clave_hash, rol))
        obtener_conexion().commit()
    except Exception as error:
        obtener_conexion().rollback()
        if _es_integridad(error):
            raise DuplicadoError from error
        raise
