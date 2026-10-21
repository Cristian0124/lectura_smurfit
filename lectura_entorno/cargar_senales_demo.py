"""Carga o actualiza 20 señales breves, documentadas y útiles para la demo.

Ejecutar desde esta carpeta: python cargar_senales_demo.py
Los hechos se tomaron de fuentes oficiales Smurfit Westrock. El puntaje es
una valoración académica de ejemplo, no un riesgo publicado por la empresa.
"""
import sqlite3
from datetime import date, timedelta

import app
import bd


FUENTES = {
    "Informe 2024": (
        "Smurfit Westrock · Informe de sostenibilidad 2024",
        "Informe corporativo",
        "https://www.smurfitwestrock.com/-/m/files/publications---global/sr-2024-downloads/smurfit_westrock_sustainability_report_2024.pdf?rev=8fa6453fc2294a2a894c5bedcc52de80",
    ),
    "Inversión social": (
        "Smurfit Westrock · Inversión social en Colombia (2024)",
        "Comunicado corporativo",
        "https://www.smurfitwestrock.com/newsroom/press-releases/2025/smurfit-westrock-invests-over-3-million-usd-in-social-initiatives-to-drive-a-sustainable-future",
    ),
    "Exportación Japón": (
        "Smurfit Westrock · Primer envío de pollo colombiano a Japón",
        "Caso de cliente",
        "https://www.eu.smurfitwestrock.com/innovation/customer-stories/colombian-chicken-export",
    ),
    "EasySplit": (
        "Smurfit Westrock · Diseño EasySplit Bag-in-Box",
        "Comunicado corporativo",
        "https://www.us.smurfitwestrock.com/about/company-archive/smurfit-kappa/press-releases/smurfit-westrock-unveils-new-innovation-to-help-bag-in-box-customers-meet-forthcoming-packaging-regulations",
    ),
    "Informe 2024 global": (
        "Smurfit Westrock · Informe de sostenibilidad 2024 (datos globales)",
        "Informe corporativo",
        "https://www.smurfitwestrock.com/newsroom/press-releases/2025/smurfit-westrock-publishes-its-first-sustainability-report",
    ),
}

# factor PESTEL, título, hecho documentado, fuente, tipo, impacto, probabilidad
CASOS = [
    (0, "Apoyo a acueductos rurales", "Apoya la gestión de acueductos comunitarios en municipios rurales de Colombia.", "Informe 2024", 0, 3, 3),
    (0, "Empaque para exportar a Japón", "Su empaque acompañó el primer envío colombiano de pollo a Japón.", "Exportación Japón", 0, 4, 3),
    (1, "US$2.000 millones en finanzas verdes", "La compañía reportó US$2.000 millones obtenidos en financiación verde en 2024.", "Informe 2024 global", 0, 4, 3),
    (1, "6.800 empleos en Colombia", "El informe corporativo estima cerca de 6.800 empleos directos en Colombia.", "Informe 2024", 0, 4, 4),
    (2, "Inversión social de US$3,5 millones", "En 2024 invirtió cerca de US$3,5 millones en iniciativas sociales y ambientales.", "Inversión social", 0, 4, 4),
    (2, "Alcance en 30 municipios", "Sus programas llegaron a 21.800 personas en más de 30 municipios colombianos.", "Inversión social", 0, 3, 4),
    (2, "Centro infantil El Caracolí", "El centro atendió a más de 590 niñas y niños en Yumbo durante 2024.", "Inversión social", 0, 3, 4),
    (2, "Formación técnica en ITAF", "Más de 580 estudiantes asistieron al colegio técnico ITAF en 2024.", "Inversión social", 0, 3, 4),
    (3, "24% menos agua por tonelada", "La planta de Cali redujo 24% el uso de agua por tonelada de papel en 2024.", "Informe 2024", 0, 4, 4),
    (3, "29% menos carga orgánica", "En Cali, la demanda química de oxígeno bajó casi 29% por tonelada en 2024.", "Informe 2024", 0, 3, 4),
    (3, "Nuevo diseño EasySplit", "EasySplit permite separar la caja y la bolsa del empaque Bag-in-Box.", "EasySplit", 0, 4, 3),
    (3, "Empaques para París 2024", "La compañía suministró 16.000 camas de cartón reciclables para los Juegos Olímpicos.", "Informe 2024 global", 0, 3, 4),
    (4, "67.500 hectáreas en Colombia", "Administra 67.500 ha de bosques y plantaciones forestales en Colombia.", "Informe 2024", 0, 4, 4),
    (4, "22.700 ha de bosque protegido", "Sus predios colombianos incluyen 22.700 ha de bosque natural protegido.", "Informe 2024", 0, 4, 4),
    (4, "41.700 ha de plantaciones", "Las plantaciones comerciales en Colombia suman 41.700 ha.", "Informe 2024", 0, 4, 4),
    (4, "47 especies amenazadas registradas", "El inventario 2024 registró 47 especies amenazadas en predios forestales colombianos.", "Informe 2024", 1, 5, 3),
    (4, "Inventario de 13 unidades forestales", "En 2024 completó inventarios de biodiversidad en 13 unidades de bosque natural.", "Informe 2024", 0, 3, 4),
    (5, "Certificación FSC desde 2003", "Los programas de manejo forestal en Colombia tienen certificación FSC desde 2003.", "Informe 2024", 0, 4, 4),
    (5, "Auditoría FSC sin hallazgos mayores", "La auditoría independiente de julio de 2024 no reportó observaciones mayores.", "Informe 2024", 0, 3, 4),
    (5, "Diseño ante norma europea PPWR", "EasySplit se diseñó para facilitar el reciclaje exigido por la regulación europea de envases.", "EasySplit", 0, 4, 3),
]


def cargar():
    conexion = sqlite3.connect(bd.RUTA_BD)
    try:
        ids_fuente = {}
        for clave, (nombre, tipo, url) in FUENTES.items():
            conexion.execute(
                "INSERT INTO fuentes(nombre,tipo,confiabilidad,url) VALUES(?,?,?,?) "
                "ON CONFLICT(nombre) DO UPDATE SET url=excluded.url",
                (nombre, tipo, "Alta", url),
            )
            ids_fuente[clave] = conexion.execute(
                "SELECT id FROM fuentes WHERE nombre=?", (nombre,)
            ).fetchone()[0]

        existentes = conexion.execute(
            "SELECT id FROM senales WHERE titulo LIKE '[DEMO]%' OR titulo LIKE '[DEMO PESTEL]%' ORDER BY id"
        ).fetchall()
        hoy = date.today()
        filas = []
        for factor, titulo, descripcion, fuente, tipo, impacto, probabilidad in CASOS:
            filas.append((
                "[DEMO] " + titulo,
                descripcion + " Hecho publicado por Smurfit Westrock.",
                app.FACTORES[factor], app.AMBITOS[factor % len(app.AMBITOS)], app.TIPOS[tipo],
                app.HORIZONTES[1], ids_fuente[fuente], impacto, probabilidad, impacto * probabilidad,
                (hoy + timedelta(days=365)).isoformat(), "Publicada", "demo",
            ))

        for indice, datos in enumerate(filas):
            if indice < len(existentes):
                conexion.execute(
                    """UPDATE senales SET titulo=?,descripcion=?,factor=?,ambito=?,tipo=?,horizonte=?,fuente_id=?,
                       impacto=?,probabilidad=?,puntaje=?,vigencia=?,estado=?,autor=? WHERE id=?""",
                    datos + (existentes[indice][0],),
                )
            else:
                conexion.execute(
                    """INSERT INTO senales(titulo,descripcion,factor,ambito,tipo,horizonte,fuente_id,
                       impacto,probabilidad,puntaje,vigencia,estado,autor) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    datos,
                )
        for extra in existentes[len(filas):]:
            conexion.execute("DELETE FROM senales WHERE id=?", (extra[0],))
        conexion.commit()
        print(f"Se cargaron/actualizaron {len(filas)} señales reales de ejemplo.")
    finally:
        conexion.close()


if __name__ == "__main__":
    cargar()
