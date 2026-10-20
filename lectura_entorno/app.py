"""Lectura de entorno - Smurfit Westrock (MVP / adelanto). Grupo 1.
Python + Flask + SQLite. Corre local o en PythonAnywhere.
"""
import csv, io, os, secrets, sqlite3
from datetime import date
from functools import wraps

from flask import (Flask, Response, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambiar-en-produccion")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
DB = os.path.join(os.path.dirname(__file__), "entorno.db")

FACTORES = ["Político", "Económico", "Social", "Tecnológico", "Ecológico", "Legal"]      # PESTEL
AMBITOS = ["País (Colombia)", "Sector empaques/papel", "Competencia", "Proveedores", "Clientes"]  # tipo de entorno
TIPOS = ["Oportunidad", "Amenaza"]
HORIZONTES = ["Corto plazo", "Mediano plazo", "Largo plazo"]
ESTADOS = ["Nueva", "En análisis", "Publicada", "Cerrada"]
CONFIABILIDAD = ["Alta", "Media", "Baja"]
ROLES = ["admin", "analista", "decisor"]   # admin=diseña, analista=usuario que registra, decisor=lee

# Guía inicial de trabajo. Son temas para investigar, no conclusiones verificadas.
PESTEL = [
    # P · Político
    {
        "nombre": "Político",
        "letra": "P",
        "color": "#647d56",
        "descripcion": (
            "Decisiones y políticas públicas que pueden cambiar las condiciones "
            "para producir y vender."
        ),
        "contexto": (
            "Para una empresa de empaques en Colombia, conviene observar políticas "
            "industriales, comerciales y de gestión de residuos."
        ),
        "preguntas": [
            "¿Hay cambios en políticas de producción, comercio o empaques?",
            "¿Qué incentivos o restricciones públicas podrían afectar al sector?",
        ],
        "fuentes": (
            "Ministerios y entidades públicas, Datos Abiertos Colombia, "
            "publicaciones empresariales."
        ),
    },

    # E · Económico
    {
        "nombre": "Económico",
        "letra": "E",
        "color": "#a87832",
        "descripcion": (
            "Variables económicas que pueden influir en los costos, la demanda "
            "y la rentabilidad."
        ),
        "contexto": (
            "En empaques, vale la pena seguir costos de materias primas, energía "
            "y transporte, además de la demanda de clientes comerciales e industriales."
        ),
        "preguntas": [
            "¿Cómo cambian la inflación, la tasa de cambio y los costos de energía?",
            "¿Qué señales hay sobre la demanda de empaques?",
        ],
        "fuentes": "DANE, Banco de la República, Banco Mundial y reportes sectoriales.",
    },

    # S · Social
    {
        "nombre": "Social",
        "letra": "S",
        "color": "#896a8b",
        "descripcion": (
            "Cambios en las personas, sus hábitos, expectativas y formas de consumo."
        ),
        "contexto": (
            "Los hábitos de compra y las expectativas sobre empaques reciclables "
            "o de menor impacto pueden influir en las necesidades de los clientes."
        ),
        "preguntas": [
            "¿Qué esperan los consumidores de los empaques?",
            "¿Cómo cambian las preferencias hacia opciones reciclables o reutilizables?",
        ],
        "fuentes": "Estadísticas del DANE, estudios de consumo y publicaciones del sector.",
    },

    # T · Tecnológico
    {
        "nombre": "Tecnológico",
        "letra": "T",
        "color": "#54758a",
        "descripcion": "Tecnologías que pueden transformar productos, procesos y canales de venta.",
        "contexto": (
            "La automatización, el diseño de empaques y los canales digitales son temas "
            "que se pueden revisar para el sector y la oferta comercial de la empresa."
        ),
        "preguntas": [
            "¿Qué tecnologías están cambiando el diseño o la fabricación de empaques?",
            "¿Qué oportunidades ofrece el comercio digital?",
        ],
        "fuentes": "Publicaciones técnicas, gremios, ferias e información corporativa.",
    },

    # E · Ecológico
    {
        "nombre": "Ecológico",
        "letra": "E",
        "color": "#3f8063",
        "descripcion": "Condiciones ambientales, recursos, residuos y efectos del cambio climático.",
        "contexto": (
            "En empaques de papel son relevantes la gestión de residuos, el reciclaje, "
            "el uso de agua y energía y la disponibilidad de materias primas."
        ),
        "preguntas": [
            "¿Qué cambios hay en reciclaje y gestión de residuos?",
            "¿Qué riesgos ambientales pueden afectar recursos o continuidad operativa?",
        ],
        "fuentes": (
            "Ministerio de Ambiente, IDEAM, autoridades ambientales e informes "
            "de sostenibilidad."
        ),
    },

    # L · Legal
    {
        "nombre": "Legal",
        "letra": "L",
        "color": "#9a5a4e",
        "descripcion": "Leyes y normas que establecen obligaciones para la actividad empresarial.",
        "contexto": (
            "Se deben seguir normas ambientales, laborales y comerciales, además de "
            "requisitos sanitarios aplicables a empaques destinados a contacto con alimentos."
        ),
        "preguntas": [
            "¿Se publicaron normas nuevas o cambios que apliquen a empaques?",
            "¿Qué requisitos aplican a materiales en contacto con alimentos?",
        ],
        "fuentes": (
            "Diario Oficial, SUIN-Juriscol, INVIMA, ministerios y autoridades competentes."
        ),
    },
]
FACTORES = [d["nombre"] for d in PESTEL]


def nivel(p):
    return "Alto" if p >= 15 else "Medio" if p >= 8 else "Bajo"


# ---------- base de datos ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def cerrar(_):
    c = g.pop("db", None)
    if c:
        c.close()


def init_db():
    con = sqlite3.connect(DB)
    con.executescript("""
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
    if not con.execute("SELECT 1 FROM usuarios").fetchone():
        for u, c, r in [("admin", "admin123", "admin"), ("analista", "analista123", "analista"),
                        ("directivo", "decisor123", "decisor")]:
            con.execute("INSERT INTO usuarios(usuario,clave,rol) VALUES(?,?,?)", (u, generate_password_hash(c), r))
    con.commit()
    con.close()


# ---------- seguridad: CSRF, login y roles ----------
@app.context_processor
def ctx():
    session.setdefault("csrf", secrets.token_hex(16))
    return {"csrf": session["csrf"], "hoy": date.today().isoformat()}


@app.before_request
def revisar_csrf():
    if request.method == "POST" and request.form.get("csrf_token") != session.get("csrf"):
        abort(400)


def requiere(*roles):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if "usuario" not in session:
                return redirect(url_for("login"))
            if roles and session["rol"] not in roles:
                abort(403)
            return f(*a, **k)
        return w
    return deco


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT * FROM usuarios WHERE usuario=?", (request.form["usuario"].strip(),)).fetchone()
        if u and check_password_hash(u["clave"], request.form["clave"]):
            session.clear()
            session["usuario"], session["rol"] = u["usuario"], u["rol"]
            return redirect(url_for("panel"))
        flash("Usuario o clave incorrectos.")
    return render_template("login.html")


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("login"))


# ---------- leer: tablas, alertas e informes ----------
def consulta():
    sql = """SELECT s.*, f.nombre AS fuente, f.confiabilidad AS conf FROM senales s
             LEFT JOIN fuentes f ON f.id=s.fuente_id WHERE 1=1"""
    args = []
    if session["rol"] == "decisor":                 # el decisor solo ve lo publicado
        sql += " AND s.estado='Publicada'"
    for campo, lista in (("factor", FACTORES), ("horizonte", HORIZONTES)):
        v = request.args.get(campo, "")
        if v in lista:
            sql += f" AND s.{campo}=?"; args.append(v)
    return db().execute(sql + " ORDER BY s.puntaje DESC, s.id DESC", args).fetchall()


@app.route("/")
@requiere()
def panel():
    filas = consulta()
    hoy = date.today().isoformat()
    abiertas = [s for s in filas if s["estado"] != "Cerrada"]
    alertas = {"altas": [s for s in abiertas if s["puntaje"] >= 15],
               "vencidas": [s for s in abiertas if s["vigencia"] and s["vigencia"] < hoy]}
    resumen = {f: sum(1 for s in filas if s["factor"] == f) for f in FACTORES}
    return render_template("panel.html", senales=filas, resumen=resumen, alertas=alertas, nivel=nivel,
                           factores=FACTORES, horizontes=HORIZONTES,
                           fa=request.args.get("factor", ""), ho=request.args.get("horizonte", ""))


@app.route("/pestel")
@requiere()
def pestel():
    elegido = request.args.get("dimension", "Político")
    if elegido not in [d["nombre"] for d in PESTEL]:
        elegido = "Político"
    dimension = next(d for d in PESTEL if d["nombre"] == elegido)
    conteos = {d["nombre"]: db().execute("SELECT COUNT(*) FROM senales WHERE factor=?", (d["nombre"],)).fetchone()[0]
               for d in PESTEL}
    return render_template("pestel.html", dimensiones=PESTEL, dimension=dimension, conteos=conteos)


@app.route("/informe")
@requiere()
def informe():
    return render_template("informe.html", senales=consulta(), nivel=nivel)


@app.route("/exportar.csv")
@requiere()
def exportar():
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Título", "Factor", "Ámbito", "Tipo", "Horizonte", "Fuente", "Confiabilidad",
                "Impacto", "Probabilidad", "Riesgo", "Nivel", "Vigencia", "Estado"])
    for s in consulta():
        w.writerow([s["titulo"], s["factor"], s["ambito"], s["tipo"], s["horizonte"], s["fuente"], s["conf"],
                    s["impacto"], s["probabilidad"], s["puntaje"], nivel(s["puntaje"]), s["vigencia"], s["estado"]])
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=lectura_entorno.csv"})


# ---------- registrar, calcular y actualizar ----------
def leer_form():
    f = request.form
    imp, prob = int(f["impacto"]), int(f["probabilidad"])
    if not (1 <= imp <= 5 and 1 <= prob <= 5):
        abort(400)
    if (f["factor"] not in FACTORES or f["ambito"] not in AMBITOS or f["tipo"] not in TIPOS
            or f["horizonte"] not in HORIZONTES):
        abort(400)
    return (f["titulo"].strip(), f["descripcion"].strip(), f["factor"], f["ambito"], f["tipo"], f["horizonte"],
            int(f["fuente_id"]) or None, imp, prob, imp * prob, f["vigencia"] or None)  # riesgo = impacto x probabilidad


def vista_form(s, comentarios=None):
    fuentes = db().execute("SELECT * FROM fuentes ORDER BY nombre").fetchall()
    return render_template("form.html", s=s, fuentes=fuentes, factores=FACTORES, ambitos=AMBITOS, tipos=TIPOS,
                           horizontes=HORIZONTES, estados=ESTADOS, comentarios=comentarios or [])


@app.route("/senal/nueva", methods=["GET", "POST"])
@requiere("admin", "analista")
def nueva():
    if request.method == "POST":
        db().execute("""INSERT INTO senales(titulo,descripcion,factor,ambito,tipo,horizonte,fuente_id,
                        impacto,probabilidad,puntaje,vigencia,autor) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                     leer_form() + (session["usuario"],))
        db().commit()
        flash("Señal registrada.")
        return redirect(url_for("panel"))
    return vista_form(None)


@app.route("/senal/<int:sid>/editar", methods=["GET", "POST"])
@requiere("admin", "analista")
def editar(sid):
    s = db().execute("SELECT * FROM senales WHERE id=?", (sid,)).fetchone() or abort(404)
    if request.method == "POST":
        if request.form.get("accion") == "comentar":
            contenido = request.form.get("contenido", "").strip()
            if not contenido or len(contenido) > 2000:
                abort(400)
            db().execute("INSERT INTO comentarios(senal_id,autor,contenido) VALUES(?,?,?)",
                         (sid, session["usuario"], contenido))
            db().commit()
            flash("Comentario agregado.")
            return redirect(url_for("editar", sid=sid))
        if request.form["estado"] not in ESTADOS:
            abort(400)
        db().execute("""UPDATE senales SET titulo=?,descripcion=?,factor=?,ambito=?,tipo=?,horizonte=?,
                        fuente_id=?,impacto=?,probabilidad=?,puntaje=?,vigencia=?,estado=? WHERE id=?""",
                     leer_form() + (request.form["estado"], sid))
        db().commit()
        flash("Señal actualizada.")
        return redirect(url_for("panel"))
    comentarios = db().execute(
        "SELECT autor,contenido,creado FROM comentarios WHERE senal_id=? ORDER BY id", (sid,)
    ).fetchall()
    return vista_form(s, comentarios)


# ---------- fuentes y usuarios ----------
@app.route("/fuentes", methods=["GET", "POST"])
@requiere("admin", "analista")
def fuentes():
    if request.method == "POST":
        if request.form["confiabilidad"] not in CONFIABILIDAD:
            abort(400)
        try:
            db().execute("INSERT INTO fuentes(nombre,tipo,confiabilidad) VALUES(?,?,?)",
                         (request.form["nombre"].strip(), request.form["tipo"].strip(), request.form["confiabilidad"]))
            db().commit()
            flash("Fuente agregada.")
        except sqlite3.IntegrityError:
            flash("Esa fuente ya existe.")
    return render_template("fuentes.html", lista=db().execute("SELECT * FROM fuentes ORDER BY nombre").fetchall(),
                           niveles=CONFIABILIDAD)


@app.route("/usuarios", methods=["GET", "POST"])
@requiere("admin")
def usuarios():
    if request.method == "POST":
        if request.form["rol"] not in ROLES or len(request.form["clave"]) < 8:
            flash("Rol inválido o clave menor a 8 caracteres.")
        else:
            try:
                db().execute("INSERT INTO usuarios(usuario,clave,rol) VALUES(?,?,?)",
                             (request.form["usuario"].strip(), generate_password_hash(request.form["clave"]),
                              request.form["rol"]))
                db().commit()
                flash("Usuario creado.")
            except sqlite3.IntegrityError:
                flash("Ese usuario ya existe.")
    return render_template("usuarios.html", roles=ROLES,
                           lista=db().execute("SELECT usuario, rol FROM usuarios").fetchall())


init_db()
if __name__ == "__main__":
    app.run(debug=True)
