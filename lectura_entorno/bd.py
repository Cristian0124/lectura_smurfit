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
            """CREATE TABLE IF NOT EXISTS indicadores_empresa(id BIGSERIAL PRIMARY KEY, clave TEXT NOT NULL,
                valor NUMERIC NOT NULL, unidad TEXT NOT NULL, fecha DATE NOT NULL, autor TEXT NOT NULL, detalle TEXT,
                creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS ejecuciones_escaneo(id BIGSERIAL PRIMARY KEY, iniciada TEXT NOT NULL,
                finalizada TEXT, procesadas INTEGER NOT NULL DEFAULT 0, nuevas INTEGER NOT NULL DEFAULT 0,
                duplicadas INTEGER NOT NULL DEFAULT 0, actualizadas INTEGER NOT NULL DEFAULT 0,
                errores INTEGER NOT NULL DEFAULT 0, detalle TEXT)""",
            """CREATE TABLE IF NOT EXISTS historial_senales(id BIGSERIAL PRIMARY KEY, senal_id BIGINT NOT NULL
                REFERENCES senales(id), version TEXT NOT NULL, registrado TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS indicadores_sector(id BIGSERIAL PRIMARY KEY, clave TEXT NOT NULL,
                valor NUMERIC NOT NULL, unidad TEXT NOT NULL, fecha TEXT NOT NULL, fuente TEXT NOT NULL,
                url TEXT NOT NULL, metodologia TEXT, consultado TEXT NOT NULL, UNIQUE(clave,fecha))""",
            """CREATE TABLE IF NOT EXISTS control_consultas(clave TEXT PRIMARY KEY, intento TEXT NOT NULL,
                estado TEXT NOT NULL)""",
        ]
        for sql in sentencias:
            conexion.execute(sql)
        for tabla, columna, tipo in [
            ("fuentes", "url", "TEXT"), ("senales", "justificacion", "TEXT"),
            ("senales", "fecha_publicacion", "TEXT"), ("senales", "fecha_identificacion", "TEXT"),
            ("senales", "implicaciones", "TEXT"),
            ("fuentes", "escaneo_habilitado", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("fuentes", "frecuencia_minutos", "INTEGER NOT NULL DEFAULT 60"),
            ("fuentes", "ultima_revision", "TEXT"),
            ("senales", "origen", "TEXT NOT NULL DEFAULT 'manual'"),
            ("senales", "url_original", "TEXT"),
            ("senales", "region_afectada", "TEXT"),
            ("senales", "impacto_produccion", "TEXT"),
            ("senales", "impacto_comercializacion", "TEXT"),
            ("senales", "actualizada", "TEXT"),
            ("senales", "tipo_publicacion", "TEXT"),
            ("senales", "numero_norma", "TEXT"),
            ("senales", "entidad_emisora", "TEXT"),
            ("ejecuciones_escaneo", "actualizadas", "INTEGER NOT NULL DEFAULT 0"),
            ("indicadores_empresa", "detalle", "TEXT"),
        ]:
            existe = conexion.execute(
                "SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() "
                "AND table_name=? AND column_name=?", (tabla, columna)
            ).fetchone()
            if not existe:
                conexion.execute(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}")
        conexion.execute("UPDATE senales SET origen='automatica' WHERE origen='manual' AND fecha_identificacion IS NOT NULL")
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
        CREATE TABLE IF NOT EXISTS indicadores_empresa(id INTEGER PRIMARY KEY, clave TEXT NOT NULL,
            valor REAL NOT NULL, unidad TEXT NOT NULL, fecha TEXT NOT NULL, autor TEXT NOT NULL, detalle TEXT,
            creado TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS ejecuciones_escaneo(id INTEGER PRIMARY KEY, iniciada TEXT NOT NULL,
            finalizada TEXT, procesadas INTEGER NOT NULL DEFAULT 0, nuevas INTEGER NOT NULL DEFAULT 0,
            duplicadas INTEGER NOT NULL DEFAULT 0, actualizadas INTEGER NOT NULL DEFAULT 0,
            errores INTEGER NOT NULL DEFAULT 0, detalle TEXT);
        CREATE TABLE IF NOT EXISTS historial_senales(id INTEGER PRIMARY KEY, senal_id INTEGER NOT NULL
            REFERENCES senales(id), version TEXT NOT NULL, registrado TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS indicadores_sector(id INTEGER PRIMARY KEY, clave TEXT NOT NULL,
            valor REAL NOT NULL, unidad TEXT NOT NULL, fecha TEXT NOT NULL, fuente TEXT NOT NULL,
            url TEXT NOT NULL, metodologia TEXT, consultado TEXT NOT NULL, UNIQUE(clave,fecha));
        CREATE TABLE IF NOT EXISTS control_consultas(clave TEXT PRIMARY KEY, intento TEXT NOT NULL,
            estado TEXT NOT NULL);
        """)
        columnas_indicadores = {fila[1] for fila in conexion.execute("PRAGMA table_info(indicadores_empresa)")}
        if "detalle" not in columnas_indicadores:
            conexion.execute("ALTER TABLE indicadores_empresa ADD COLUMN detalle TEXT")
        columnas_fuentes = {fila[1] for fila in conexion.execute("PRAGMA table_info(fuentes)")}
        if "url" not in columnas_fuentes:
            conexion.execute("ALTER TABLE fuentes ADD COLUMN url TEXT")
        columnas_senales = {fila[1] for fila in conexion.execute("PRAGMA table_info(senales)")}
        for columna in ("justificacion", "fecha_publicacion", "fecha_identificacion", "implicaciones"):
            if columna not in columnas_senales:
                conexion.execute(f"ALTER TABLE senales ADD COLUMN {columna} TEXT")
        columnas_fuentes = {fila[1] for fila in conexion.execute("PRAGMA table_info(fuentes)")}
        for columna, tipo in (("escaneo_habilitado", "INTEGER NOT NULL DEFAULT 0"),
                              ("frecuencia_minutos", "INTEGER NOT NULL DEFAULT 60"),
                              ("ultima_revision", "TEXT")):
            if columna not in columnas_fuentes:
                conexion.execute(f"ALTER TABLE fuentes ADD COLUMN {columna} {tipo}")
        columnas_senales = {fila[1] for fila in conexion.execute("PRAGMA table_info(senales)")}
        for columna, tipo in (("origen", "TEXT NOT NULL DEFAULT 'manual'"), ("url_original", "TEXT"),
                              ("region_afectada", "TEXT"), ("impacto_produccion", "TEXT"),
                              ("impacto_comercializacion", "TEXT"), ("actualizada", "TEXT"),
                              ("tipo_publicacion", "TEXT"), ("numero_norma", "TEXT"),
                              ("entidad_emisora", "TEXT")):
            if columna not in columnas_senales:
                conexion.execute(f"ALTER TABLE senales ADD COLUMN {columna} {tipo}")
        columnas_ejecuciones = {fila[1] for fila in conexion.execute("PRAGMA table_info(ejecuciones_escaneo)")}
        if "actualizadas" not in columnas_ejecuciones:
            conexion.execute("ALTER TABLE ejecuciones_escaneo ADD COLUMN actualizadas INTEGER NOT NULL DEFAULT 0")
        conexion.execute("UPDATE senales SET origen='automatica' WHERE origen='manual' AND fecha_identificacion IS NOT NULL")


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


def consultar_senales(rol, factor=None, horizonte=None, request_filter=None):
    request_filter = request_filter or {}
    sql = """SELECT s.*, f.nombre AS fuente, f.confiabilidad AS conf, f.url AS fuente_url
             FROM senales s LEFT JOIN fuentes f ON f.id=s.fuente_id WHERE 1=1"""
    parametros = []
    if rol == "decisor":
        sql += " AND s.estado='Publicada'"
    if factor:
        sql += " AND s.factor=?"; parametros.append(factor)
    if horizonte:
        sql += " AND s.horizonte=?"; parametros.append(horizonte)
    filtros = {"tipo": "s.tipo", "region": "s.region_afectada", "fuente": "f.nombre",
               "origen": "s.origen"}
    for clave, campo in filtros.items():
        valor = request_filter.get(clave)
        if valor:
            sql += f" AND {campo}=?"; parametros.append(valor)
    if request_filter.get("fecha_desde"):
        sql += " AND COALESCE(s.fecha_publicacion, CAST(s.creada AS TEXT)) >= ?"; parametros.append(request_filter["fecha_desde"])
    if request_filter.get("fecha_hasta"):
        sql += " AND COALESCE(s.fecha_publicacion, CAST(s.creada AS TEXT)) <= ?"; parametros.append(request_filter["fecha_hasta"] + " 23:59:59")
    riesgo = request_filter.get("riesgo")
    if riesgo in ("Alto", "Medio", "Bajo"):
        limites = {"Alto": (15, 25), "Medio": (8, 14), "Bajo": (1, 7)}[riesgo]
        sql += " AND s.puntaje BETWEEN ? AND ?"; parametros.extend(limites)
    return _ejecutar(sql + " ORDER BY COALESCE(s.fecha_publicacion, CAST(s.creada AS TEXT)) DESC, "
                     "s.puntaje DESC, s.id DESC", parametros).fetchall()


def contar_senales_por_factor(factor):
    return _ejecutar("SELECT COUNT(*) FROM senales WHERE factor=?", (factor,)).fetchone()[0]


def listar_fuentes():
    return _ejecutar("SELECT * FROM fuentes ORDER BY nombre").fetchall()


def actualizar_programacion_fuente(fuente_id, habilitada, frecuencia_minutos):
    _ejecutar("UPDATE fuentes SET escaneo_habilitado=?,frecuencia_minutos=? WHERE id=?",
              (habilitada if USAR_POSTGRES else int(habilitada), frecuencia_minutos, fuente_id))
    obtener_conexion().commit()


def fuentes_para_escaneo():
    return _ejecutar("SELECT * FROM fuentes WHERE escaneo_habilitado=? AND url IS NOT NULL ORDER BY nombre",
                     (True if USAR_POSTGRES else 1,)).fetchall()


def marcar_revision_fuente(fuente_id, revisada):
    _ejecutar("UPDATE fuentes SET ultima_revision=? WHERE id=?", (revisada, fuente_id))
    obtener_conexion().commit()


def asegurar_fuente_catalogo(nombre, tipo, confiabilidad, url, frecuencia_minutos=60):
    existente = buscar_fuente_por_url(url)
    if existente:
        return existente["id"]
    try:
        fila = _ejecutar("INSERT INTO fuentes(nombre,tipo,confiabilidad,url,escaneo_habilitado,frecuencia_minutos) "
                         "VALUES(?,?,?,?,?,?) RETURNING id",
                         (nombre, tipo, confiabilidad, url, True if USAR_POSTGRES else 1,
                          frecuencia_minutos)).fetchone()
        obtener_conexion().commit()
        return fila[0]
    except Exception as error:
        obtener_conexion().rollback()
        if _es_integridad(error):
            return None
        raise


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


def registrar_senal_automatica(datos):
    _ejecutar("""INSERT INTO senales(titulo,descripcion,implicaciones,factor,ambito,tipo,horizonte,fuente_id,
        impacto,probabilidad,puntaje,vigencia,autor,justificacion,fecha_publicacion,fecha_identificacion,
        origen,url_original,region_afectada,impacto_produccion,impacto_comercializacion,actualizada,tipo_publicacion,
        numero_norma,entidad_emisora)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", datos)
    obtener_conexion().commit()


def guardar_senal_automatica(datos, ahora):
    """Inserta una señal o actualiza su versión conservando una instantánea anterior."""
    columnas = ("titulo", "descripcion", "implicaciones", "factor", "ambito", "tipo", "horizonte", "fuente_id",
        "impacto", "probabilidad", "puntaje", "vigencia", "autor", "justificacion", "fecha_publicacion",
        "fecha_identificacion", "origen", "url_original", "region_afectada", "impacto_produccion",
        "impacto_comercializacion", "actualizada", "tipo_publicacion", "numero_norma", "entidad_emisora")
    actual = _ejecutar("SELECT * FROM senales WHERE fuente_id=? AND lower(titulo)=lower(?) AND factor=? "
                       "AND origen='automatica' ORDER BY id DESC LIMIT 1",
                       (datos[7], datos[0], datos[3])).fetchone()
    if not actual:
        registrar_senal_automatica(datos)
        return "nueva"
    actual_dict = dict(actual)
    incoming = dict(zip(columnas, datos))
    for campo in ("vigencia", "fecha_publicacion"):
        if not incoming[campo]:
            incoming[campo] = actual_dict[campo]
    for campo in ("region_afectada", "impacto_produccion", "impacto_comercializacion", "numero_norma", "entidad_emisora"):
        if incoming[campo] in (None, "", "No disponible") and actual_dict[campo]:
            incoming[campo] = actual_dict[campo]
    comparables = tuple(c for c in columnas if c not in ("autor", "fecha_identificacion", "actualizada"))
    if all(incoming[c] == actual_dict[c] for c in comparables):
        return "duplicada"
    import json
    _ejecutar("INSERT INTO historial_senales(senal_id,version,registrado) VALUES(?,?,?)",
        (actual_dict["id"], json.dumps(actual_dict, ensure_ascii=False, default=str), ahora))
    actualizables = [c for c in columnas if c not in ("autor",)]
    _ejecutar("UPDATE senales SET " + ",".join(f"{c}=?" for c in actualizables) + " WHERE id=?",
        tuple(incoming[c] for c in actualizables) + (actual_dict["id"],))
    obtener_conexion().commit()
    return "actualizada"


def ultima_ejecucion_escaneo():
    return _ejecutar("SELECT * FROM ejecuciones_escaneo ORDER BY id DESC LIMIT 1").fetchone()


def iniciar_ejecucion_escaneo(iniciada):
    fila = _ejecutar("INSERT INTO ejecuciones_escaneo(iniciada) VALUES(?) RETURNING id", (iniciada,)).fetchone()
    obtener_conexion().commit()
    return fila[0]


def finalizar_ejecucion_escaneo(ejecucion_id, finalizada, procesadas, nuevas, duplicadas, actualizadas, errores, detalle=""):
    _ejecutar("UPDATE ejecuciones_escaneo SET finalizada=?,procesadas=?,nuevas=?,duplicadas=?,actualizadas=?,errores=?,detalle=? WHERE id=?",
              (finalizada, procesadas, nuevas, duplicadas, actualizadas, errores, detalle[:2000], ejecucion_id))
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

def registrar_indicador(clave, valor, unidad, fecha, autor, detalle=""):
    _ejecutar("INSERT INTO indicadores_empresa(clave,valor,unidad,fecha,autor,detalle) VALUES(?,?,?,?,?,?)",
              (clave, valor, unidad, fecha, autor, detalle))
    obtener_conexion().commit()


def listar_indicadores():
    return _ejecutar("SELECT * FROM indicadores_empresa ORDER BY fecha DESC, id DESC LIMIT 250").fetchall()


def guardar_indicador_sector(clave, valor, unidad, fecha, fuente, url, metodologia, consultado):
    _ejecutar("""INSERT INTO indicadores_sector(clave,valor,unidad,fecha,fuente,url,metodologia,consultado)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(clave,fecha) DO UPDATE SET valor=excluded.valor,
        unidad=excluded.unidad,fuente=excluded.fuente,url=excluded.url,metodologia=excluded.metodologia,
        consultado=excluded.consultado""", (clave, valor, unidad, fecha, fuente, url, metodologia, consultado))
    obtener_conexion().commit()


def listar_indicadores_sector(clave=None, limite=30):
    if clave:
        return _ejecutar("SELECT * FROM indicadores_sector WHERE clave=? ORDER BY fecha DESC LIMIT ?",
                         (clave, limite)).fetchall()
    return _ejecutar("SELECT * FROM indicadores_sector ORDER BY fecha DESC, id DESC LIMIT ?", (limite,)).fetchall()


def obtener_indicador_sector(clave):
    return _ejecutar("SELECT * FROM indicadores_sector WHERE clave=? ORDER BY fecha DESC LIMIT 1",
                     (clave,)).fetchone()


def obtener_ultimo_intento_indicador(clave):
    return _ejecutar("SELECT intento,estado FROM control_consultas WHERE clave=?", (clave,)).fetchone()


def registrar_intento_indicador(clave, intento, estado):
    _ejecutar("""INSERT INTO control_consultas(clave,intento,estado) VALUES(?,?,?)
        ON CONFLICT(clave) DO UPDATE SET intento=excluded.intento,estado=excluded.estado""",
        (clave, intento, estado))
    obtener_conexion().commit()
