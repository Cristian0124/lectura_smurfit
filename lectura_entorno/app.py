"""Lectura de entorno - Smurfit Westrock (MVP / adelanto). Grupo 1.
Python + Flask + SQLite. Corre local o en PythonAnywhere.
"""
import io, os, secrets
from datetime import date
from functools import wraps

from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from excel_export import generar_excel
import bd

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambiar-en-produccion")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

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


app.teardown_appcontext(bd.cerrar_conexion)


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
        u = bd.buscar_usuario(request.form["usuario"].strip())
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
    factor = request.args.get("factor", "")
    horizonte = request.args.get("horizonte", "")
    if factor not in FACTORES:
        factor = None
    if horizonte not in HORIZONTES:
        horizonte = None
    return bd.consultar_senales(session["rol"], factor, horizonte)


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
    conteos = {d["nombre"]: bd.contar_senales_por_factor(d["nombre"]) for d in PESTEL}
    return render_template("pestel.html", dimensiones=PESTEL, dimension=dimension, conteos=conteos)


@app.route("/informe")
@requiere()
def informe():
    return render_template("informe.html", senales=consulta(), nivel=nivel)


@app.route("/exportar.xlsx")
@requiere()
def exportar():
    contenido = generar_excel(consulta(), nivel)
    return Response(contenido,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=lectura_entorno.xlsx"})

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
    fuentes = bd.listar_fuentes()
    return render_template("form.html", s=s, fuentes=fuentes, factores=FACTORES, ambitos=AMBITOS, tipos=TIPOS,
                           horizontes=HORIZONTES, estados=ESTADOS, comentarios=comentarios or [])


@app.route("/senal/nueva", methods=["GET", "POST"])
@requiere("admin", "analista")
def nueva():
    if request.method == "POST":
        bd.registrar_senal(leer_form(), session["usuario"])
        flash("Señal registrada.")
        return redirect(url_for("panel"))
    return vista_form(None)


@app.route("/senal/<int:sid>/editar", methods=["GET", "POST"])
@requiere("admin", "analista")
def editar(sid):
    s = bd.buscar_senal(sid) or abort(404)
    if request.method == "POST":
        if request.form.get("accion") == "comentar":
            contenido = request.form.get("contenido", "").strip()
            if not contenido or len(contenido) > 2000:
                abort(400)
            bd.agregar_comentario(sid, session["usuario"], contenido)
            flash("Comentario agregado.")
            return redirect(url_for("editar", sid=sid))
        if request.form["estado"] not in ESTADOS:
            abort(400)
        bd.actualizar_senal(sid, leer_form(), request.form["estado"])
        flash("Señal actualizada.")
        return redirect(url_for("panel"))
    comentarios = bd.listar_comentarios(sid)
    return vista_form(s, comentarios)


# ---------- fuentes y usuarios ----------
@app.route("/fuentes", methods=["GET", "POST"])
@requiere("admin", "analista")
def fuentes():
    if request.method == "POST":
        if request.form["confiabilidad"] not in CONFIABILIDAD:
            abort(400)
        try:
            bd.agregar_fuente(request.form["nombre"].strip(), request.form["tipo"].strip(), request.form["confiabilidad"], request.form.get("url", "").strip() or None)
            flash("Fuente agregada.")
        except bd.DuplicadoError:
            flash("Esa fuente ya existe.")
    return render_template("fuentes.html", lista=bd.listar_fuentes(), niveles=CONFIABILIDAD)


@app.route("/usuarios", methods=["GET", "POST"])
@requiere("admin")
def usuarios():
    if request.method == "POST":
        if request.form["rol"] not in ROLES or len(request.form["clave"]) < 8:
            flash("Rol inválido o clave menor a 8 caracteres.")
        else:
            try:
                bd.agregar_usuario(
                    request.form["usuario"].strip(),
                    generate_password_hash(request.form["clave"]),
                    request.form["rol"],
                )
                flash("Usuario creado.")
            except bd.DuplicadoError:
                flash("Ese usuario ya existe.")
    return render_template("usuarios.html", roles=ROLES,
                           lista=bd.listar_usuarios())


bd.inicializar_bd()
if __name__ == "__main__":
    app.run(debug=True)
