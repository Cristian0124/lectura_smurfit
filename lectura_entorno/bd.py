"""Conexión y operaciones de persistencia para Lectura de entorno."""
import os
import sqlite3

from flask import g
from werkzeug.security import generate_password_hash


RUTA_BD = os.environ.get("DB", os.path.join(os.path.dirname(__file__), "entorno.db"))


class DuplicadoError(Exception):
    """Indica que un registro viola una restricción de unicidad."""


def obtener_conexion():
    """Devuelve la conexión SQLite asociada a la petición actual."""
    if "conexion_bd" not in g:
        g.conexion_bd = sqlite3.connect(RUTA_BD)
        g.conexion_bd.row_factory = sqlite3.Row
    return g.conexion_bd


def cerrar_conexion(_error=None):
    conexion = g.pop("conexion_bd", None)
    if conexion is not None:
        conexion.close()


def inicializar_bd():
    """Crea las tablas necesarias y agrega usuarios de demostración si está vacía."""
    carpeta = os.path.dirname(os.path.abspath(RUTA_BD))
    os.makedirs(carpeta, exist_ok=True)
    conexion = sqlite3.connect(RUTA_BD)
    try:
        conexion.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY, usuario TEXT UNIQUE NOT NULL,
            clave TEXT NOT NULL, rol TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fuentes(id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL, confiabilidad TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS senales(id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, descripcion TEXT,
            factor TEXT NOT NULL, ambito TEXT NOT NULL, tipo TEXT NOT NULL, horizonte TEXT NOT NULL,
            fuente_id INTEGER REFERENCES fuentes(id), impacto INTEGER NOT NULL, probabilidad INTEGER NOT NULL,
            puntaje INTEGER NOT NULL, vigencia TEXT, estado TEXT NOT NULL DEFAULT 'Nueva',
            autor TEXT, creada TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS comentarios(id INTEGER PRIMARY KEY, senal_id INTEGER NOT NULL
            REFERENCES senales(id), autor TEXT NOT NULL, contenido TEXT NOT NULL,
            creado TEXT DEFAULT CURRENT_TIMESTAMP);
        """)
        if not conexion.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone():
            usuarios_demo = [
                ("admin", "admin123", "admin"),
                ("analista", "analista123", "analista"),
                ("directivo", "decisor123", "decisor"),
            ]
            conexion.executemany(
                "INSERT INTO usuarios(usuario, clave, rol) VALUES (?, ?, ?)",
                [(usuario, generate_password_hash(clave), rol)
                 for usuario, clave, rol in usuarios_demo],
            )
        conexion.commit()
    finally:
        conexion.close()


def buscar_usuario(usuario):
    return obtener_conexion().execute(
        "SELECT * FROM usuarios WHERE usuario=?", (usuario,)
    ).fetchone()


def consultar_senales(rol, factor=None, horizonte=None):
    sql = """SELECT s.*, f.nombre AS fuente, f.confiabilidad AS conf
             FROM senales s LEFT JOIN fuentes f ON f.id=s.fuente_id WHERE 1=1"""
    parametros = []
    if rol == "decisor":
        sql += " AND s.estado='Publicada'"
    if factor:
        sql += " AND s.factor=?"
        parametros.append(factor)
    if horizonte:
        sql += " AND s.horizonte=?"
        parametros.append(horizonte)
    return obtener_conexion().execute(
        sql + " ORDER BY s.puntaje DESC, s.id DESC", parametros
    ).fetchall()


def contar_senales_por_factor(factor):
    return obtener_conexion().execute(
        "SELECT COUNT(*) FROM senales WHERE factor=?", (factor,)
    ).fetchone()[0]


def listar_fuentes():
    return obtener_conexion().execute("SELECT * FROM fuentes ORDER BY nombre").fetchall()


def listar_comentarios(senal_id):
    return obtener_conexion().execute(
        "SELECT autor,contenido,creado FROM comentarios WHERE senal_id=? ORDER BY id",
        (senal_id,),
    ).fetchall()


def buscar_senal(senal_id):
    return obtener_conexion().execute(
        "SELECT * FROM senales WHERE id=?", (senal_id,)
    ).fetchone()


def registrar_senal(datos, autor):
    obtener_conexion().execute(
        """INSERT INTO senales(titulo,descripcion,factor,ambito,tipo,horizonte,fuente_id,
           impacto,probabilidad,puntaje,vigencia,autor) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        datos + (autor,),
    )
    obtener_conexion().commit()


def actualizar_senal(senal_id, datos, estado):
    obtener_conexion().execute(
        """UPDATE senales SET titulo=?,descripcion=?,factor=?,ambito=?,tipo=?,horizonte=?,
           fuente_id=?,impacto=?,probabilidad=?,puntaje=?,vigencia=?,estado=? WHERE id=?""",
        datos + (estado, senal_id),
    )
    obtener_conexion().commit()


def agregar_comentario(senal_id, autor, contenido):
    obtener_conexion().execute(
        "INSERT INTO comentarios(senal_id,autor,contenido) VALUES(?,?,?)",
        (senal_id, autor, contenido),
    )
    obtener_conexion().commit()


def agregar_fuente(nombre, tipo, confiabilidad):
    try:
        obtener_conexion().execute(
            "INSERT INTO fuentes(nombre,tipo,confiabilidad) VALUES(?,?,?)",
            (nombre, tipo, confiabilidad),
        )
        obtener_conexion().commit()
    except sqlite3.IntegrityError as error:
        raise DuplicadoError from error


def listar_usuarios():
    return obtener_conexion().execute(
        "SELECT usuario, rol FROM usuarios"
    ).fetchall()


def agregar_usuario(usuario, clave_hash, rol):
    try:
        obtener_conexion().execute(
            "INSERT INTO usuarios(usuario,clave,rol) VALUES(?,?,?)",
            (usuario, clave_hash, rol),
        )
        obtener_conexion().commit()
    except sqlite3.IntegrityError as error:
        raise DuplicadoError from error
