"""Radar de entorno: análisis PESTEL para organizaciones de cualquier sector.
Python + Flask + SQLite. Corre local o en PythonAnywhere.
"""
import hashlib, io, json, logging, os, re, secrets, traceback
from datetime import date
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from flask import (Flask, Response, abort, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from excel_export import generar_excel
import bd

app = Flask(__name__)
SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if os.environ.get("DATABASE_URL") and not SECRET_KEY:
    raise RuntimeError("SECRET_KEY debe configurarse en el entorno de producción.")
app.secret_key = SECRET_KEY or "solo-desarrollo-local-cambiar-en-produccion"
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.environ.get("DATABASE_URL")))

FACTORES = ["Político", "Económico", "Social", "Tecnológico", "Ecológico", "Legal"]      # PESTEL
AMBITOS = ["País o región", "Sector", "Mercado", "Competencia", "Proveedores", "Clientes", "Tecnología"]
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
            "Analiza decisiones públicas, estabilidad institucional y políticas que puedan "
            "cambiar las condiciones de operación en el territorio de interés."
        ),
        "preguntas": [
            "¿Qué cambios de política pública afectan a la actividad o al mercado?",
            "¿Qué incentivos, restricciones o riesgos institucionales están surgiendo?",
        ],
        "fuentes": (
            "Entidades publicas, registros oficiales y comunicados institucionales."
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
            "Observa inflación, tasas, empleo, costos, inversión, comercio y demanda "
            "en los mercados relevantes para la organización."
        ),
        "preguntas": [
            "¿Cómo cambian la inflación, la tasa de cambio y los costos de energía?",
            "¿Qué señales muestran cambios en la demanda o en el costo de operar?",
        ],
        "fuentes": "Institutos estadisticos, bancos centrales y reportes economicos del territorio analizado.",
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
            "Los cambios demográficos, culturales, laborales y de consumo pueden "
            "modificar expectativas y necesidades de las partes interesadas."
        ),
        "preguntas": [
            "\u00bfQu\u00e9 esperan las personas usuarias o clientes?",
            "¿Qué cambios de hábitos, valores o composición poblacional son relevantes?",
        ],
        "fuentes": "Estudios demograficos, encuestas de consumo y publicaciones sociales.",
    },

    # T · Tecnológico
    {
        "nombre": "Tecnológico",
        "letra": "T",
        "color": "#54758a",
        "descripcion": "Tecnologías que pueden transformar productos, procesos y canales de venta.",
        "contexto": (
            "La automatización, la inteligencia artificial, la ciberseguridad y la "
            "infraestructura digital pueden transformar procesos y modelos de negocio."
        ),
        "preguntas": [
            "¿Qué tecnologías emergentes pueden cambiar productos, procesos o servicios?",
            "¿Qué oportunidades y riesgos digitales afectan a la organización?",
        ],
        "fuentes": "Publicaciones tecnicas, centros de investigacion y asociaciones profesionales.",
    },

    # E · Ecológico
    {
        "nombre": "Ecológico",
        "letra": "E",
        "color": "#3f8063",
        "descripcion": "Condiciones ambientales, recursos, residuos y efectos del cambio climático.",
        "contexto": (
            "Examina clima, recursos naturales, energía, contaminación, biodiversidad "
            "y las expectativas ambientales aplicables al contexto analizado."
        ),
        "preguntas": [
            "¿Qué cambios hay en reciclaje y gestión de residuos?",
            "¿Qué riesgos ambientales pueden afectar recursos o continuidad operativa?",
        ],
        "fuentes": (
            "Autoridades ambientales, datos climaticos oficiales e informes de sostenibilidad."
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
            "requisitos sectoriales aplicables a productos, servicios u operaciones."
        ),
        "preguntas": [
            "\u00bfSe publicaron normas nuevas o cambios que apliquen a la actividad?",
            "¿Qué normas nuevas o cambios regulatorios podrían aplicar a la actividad?",
        ],
        "fuentes": (
            "Diarios oficiales, registros normativos y autoridades competentes."
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
    rol = session["rol"]
    conteos = {d["nombre"]: len(bd.consultar_senales(rol, factor=d["nombre"])) for d in PESTEL}
    senales_dimension = bd.consultar_senales(rol, factor=elegido)
    return render_template("pestel.html", dimensiones=PESTEL, dimension=dimension,
                           conteos=conteos, senales=senales_dimension, nivel=nivel)


def esquema_senales_estructuradas():
    fecha_opcional = {"type": ["string", "null"], "format": "date"}
    senal = {
        "type": "object",
        "properties": {
            "titulo": {"type": "string", "description": "Titulo breve y fiel al acontecimiento de la fuente."},
            "descripcion": {"type": "string", "description": "Resumen factual del acontecimiento, sin agregar datos que no aparezcan en la fuente."},
            "implicaciones": {"type": "string", "description": "Implicacion razonada para organizaciones de cualquier sector que operan en Colombia."},
            "factor": {"type": "string", "enum": FACTORES, "description": "La dimension PESTEL principal a la que corresponde el hecho."},
            "ambito": {"type": "string", "enum": AMBITOS, "description": "Ambito colombiano mas directamente relacionado con el hecho."},
            "tipo": {"type": "string", "enum": TIPOS, "description": "Oportunidad o amenaza para organizaciones de cualquier sector en Colombia."},
            "horizonte": {"type": "string", "enum": HORIZONTES, "description": "Horizonte temporal probable de la implicacion."},
            "impacto": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Impacto potencial: 1 minimo y localizado; 3 relevante para varias organizaciones; 5 amplio o sistemico en Colombia."},
            "probabilidad": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Probabilidad de que la implicacion ocurra: 1 especulativa; 3 plausible; 5 hecho confirmado o altamente probable. Justifica la estimacion."},
            "vigencia": {**fecha_opcional, "description": "Fecha de vencimiento solo si la fuente la indica claramente; null si no se conoce."},
            "fecha_publicacion": {**fecha_opcional, "description": "Fecha de publicacion indicada por la fuente; null si no se encuentra."},
            "justificacion": {"type": "string", "description": "Por que el acontecimiento corresponde a ese factor, tipo, ambito e impacto."},
            "evidencia": {"type": "string", "description": "Frase breve, literal o casi literal, que sustenta la clasificacion."},
        },
        "required": ["titulo", "descripcion", "implicaciones", "factor", "ambito", "tipo", "horizonte",
                     "impacto", "probabilidad", "vigencia", "fecha_publicacion", "justificacion", "evidencia"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"senales": {"type": "array", "items": senal, "maxItems": 5,
                                      "description": "Acontecimientos externos distintos y relevantes. Devuelve una lista vacia si la pagina no contiene una señal PESTEL clara."}},
        "required": ["senales"],
        "additionalProperties": False,
    }


@app.route("/analizar-pagina", methods=["GET", "POST"])
@requiere("admin", "analista")
def analizar_pagina():
    url = ""
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        try:
            partes = urlsplit(url)
            hostname = partes.hostname
        except ValueError:
            hostname = None
            partes = None
        if (len(url) > 2048 or not partes or partes.scheme != "https" or not hostname
                or partes.username or partes.password):
            flash("Ingresa una URL publica valida que comience con https://")
            return render_template("analizar.html", url=url)

        api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
        if not api_key:
            flash("Falta configurar FIRECRAWL_API_KEY en el entorno del servidor.")
            return render_template("analizar.html", url=url)

        payload = json.dumps({
            "url": url,
            "formats": [{"type": "json", "schema": esquema_senales_estructuradas()}],
            "onlyMainContent": True,
            "checkPromptInjection": True,
        }).encode("utf-8")
        solicitud = Request(
            "https://api.firecrawl.dev/v2/scrape",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(solicitud, timeout=90) as respuesta:
                resultado = json.loads(respuesta.read().decode("utf-8"))
            if not resultado.get("success"):
                raise ValueError("Respuesta de Firecrawl sin exito")
            datos = resultado.get("data") or {}
            metadata = datos.get("metadata") or {}
            extraccion = datos.get("json") or {}
            if isinstance(extraccion, str):
                extraccion = json.loads(extraccion)
            senales = extraccion.get("senales", []) if isinstance(extraccion, dict) else []
            hostname = urlsplit(url).hostname or "Fuente web"
            title_pagina = metadata.get("title") or hostname
            fuente = bd.buscar_fuente_por_url(url)
            fuente_id = fuente["id"] if fuente else None
            guardadas = 0
            duplicadas = 0
            senales_validas = []
            for item in senales[:5]:
                if not isinstance(item, dict):
                    continue
                item_title = str(item.get("titulo", "")).strip()[:200]
                descripcion = str(item.get("descripcion", "")).strip()[:5000]
                implicaciones = str(item.get("implicaciones", "")).strip()[:5000]
                factor = item.get("factor")
                ambito = item.get("ambito")
                tipo = item.get("tipo")
                horizonte = item.get("horizonte")
                try:
                    impacto = int(item.get("impacto"))
                    probabilidad = int(item.get("probabilidad"))
                except (TypeError, ValueError):
                    continue
                fecha_publicacion = item.get("fecha_publicacion")
                vigencia = item.get("vigencia")
                try:
                    if fecha_publicacion:
                        fecha_publicacion = date.fromisoformat(str(fecha_publicacion)[:10]).isoformat()
                    if vigencia:
                        vigencia = date.fromisoformat(str(vigencia)[:10]).isoformat()
                except ValueError:
                    fecha_publicacion, vigencia = None, None
                if (not item_title or not descripcion or not implicaciones or factor not in FACTORES
                        or ambito not in AMBITOS or tipo not in TIPOS or horizonte not in HORIZONTES
                        or not (1 <= impacto <= 5 and 1 <= probabilidad <= 5)):
                    continue
                senales_validas.append({
                    "titulo": item_title, "descripcion": descripcion, "implicaciones": implicaciones,
                    "factor": factor, "ambito": ambito, "tipo": tipo, "horizonte": horizonte,
                    "impacto": impacto, "probabilidad": probabilidad, "fecha_publicacion": fecha_publicacion,
                    "vigencia": vigencia, "justificacion": str(item.get("justificacion", "")).strip()[:2000],
                    "evidencia": str(item.get("evidencia", "")).strip()[:2000],
                })

            if senales_validas and not fuente_id:
                nombre_fuente = f"{title_pagina[:120]} ({hostname})"
                try:
                    fuente_id = bd.crear_fuente_analizada(nombre_fuente, url)
                except bd.DuplicadoError:
                    huella = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
                    fuente_id = bd.crear_fuente_analizada(f"{title_pagina[:100]} ({hostname}) {huella}", url)
            for item in senales_validas:
                if bd.senal_ya_registrada(fuente_id, item["titulo"], item["factor"]):
                    duplicadas += 1
                    continue
                datos_senal = (item["titulo"], item["descripcion"], item["implicaciones"], item["factor"],
                               item["ambito"], item["tipo"], item["horizonte"], fuente_id, item["impacto"],
                               item["probabilidad"], item["impacto"] * item["probabilidad"], item["vigencia"])
                justificacion = item["justificacion"]
                if item["evidencia"]:
                    justificacion += " Evidencia de la fuente: " + item["evidencia"]
                bd.registrar_senal_analizada(datos_senal, session["usuario"], justificacion,
                                             item["fecha_publicacion"], date.today().isoformat())
                guardadas += 1
            if guardadas:
                flash(f"Analisis completo: {guardadas} señal(es) se guardaron automaticamente en PESTEL." +
                      (f" {duplicadas} ya existian y no se duplicaron." if duplicadas else ""))
                return redirect(url_for("panel"))
            if duplicadas:
                flash("La pagina ya se habia analizado; no se duplicaron sus señales.")
            else:
                flash("La pagina se extrajo, pero Firecrawl no detecto señales PESTEL suficientemente claras para guardar.")
        except HTTPError as error:
            if error.code in (401, 403):
                flash("Firecrawl rechazó la solicitud. Verifica la API key y los permisos de la cuenta.")
            elif error.code == 402:
                flash("Firecrawl no tiene creditos disponibles para esta extraccion estructurada.")
            elif error.code == 429:
                flash("Firecrawl recibió demasiadas solicitudes. Espera un momento e inténtalo de nuevo.")
            else:
                flash(f"Firecrawl respondió con un error HTTP {error.code}. Inténtalo más tarde.")
        except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
            flash("No se pudo conectar con Firecrawl. Intenta de nuevo en unos minutos.")
        except (AttributeError, TypeError, ValueError):
            flash("Firecrawl devolvio una respuesta que no se pudo interpretar.")

    return render_template("analizar.html", url=url)


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
    return (f["titulo"].strip(), f["descripcion"].strip(), f.get("implicaciones", "").strip(),
            f["factor"], f["ambito"], f["tipo"], f["horizonte"],
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


try:
    bd.inicializar_bd()
except Exception as error:
    # Incluye excepción, traceback y SQL anotado por el adaptador, ocultando cualquier DSN.
    detalle = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    detalle = re.sub(r"(?i)postgres(?:ql)?://[^\s'\"<>]+", "postgresql://[CREDENCIALES OCULTAS]", detalle)
    logging.error("No se pudo inicializar la base de datos (%s):\n%s", type(error).__name__, detalle)
    raise RuntimeError("No se pudo inicializar la base de datos; revisa DATABASE_URL y los registros del servicio.") from None

if __name__ == "__main__":
    app.run(debug=True)
