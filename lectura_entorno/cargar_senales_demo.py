        print(f"Se cargaron/actualizaron {len(CASOS)} ejemplos sinteticos.")

Ejecutar desde esta carpeta: python cargar_senales_demo.py
Los ejemplos son ficticios y no representan organizaciones ni hallazgos reales.
"""
import sqlite3
from datetime import date, timedelta

import app
import bd


CASOS = [
    (0, "Propuesta de incentivo a la inversion", "Ejemplo ficticio: se propone un incentivo publico que podria modificar decisiones de inversion.", 0, 3, 3),
    (1, "Aumento previsto de costos logisticos", "Ejemplo ficticio: indicadores sectoriales anticipan presion al alza en costos de transporte.", 1, 4, 3),
    (2, "Preferencia creciente por servicios digitales", "Ejemplo ficticio: una encuesta indica mayor preferencia por canales digitales.", 0, 3, 4),
    (3, "Adopci?n de automatizaci?n en el sector", "Ejemplo ficticio: nuevas herramientas podr?an reducir tiempos de operaci?n.", 0, 4, 3),
    (4, "Mayor exposici?n a eventos clim?ticos", "Ejemplo ficticio: cambios en patrones clim?ticos pueden afectar la continuidad operativa.", 1, 5, 3),
    (5, "Cambio regulatorio en consulta publica", "Ejemplo ficticio: una propuesta normativa podria crear nuevas obligaciones de reporte.", 1, 4, 4),
]


def cargar():
    conexion = sqlite3.connect(bd.RUTA_BD)
    try:
        existente = conexion.execute("SELECT id FROM fuentes WHERE nombre=?", ("Fuente de ejemplo",)).fetchone()
        if existente:
            fuente_id = existente[0]
        else:
            fuente_id = conexion.execute(
                "INSERT INTO fuentes(nombre,tipo,confiabilidad,url) VALUES(?,?,?,?)",
                ("Fuente de ejemplo", "Referencia sintetica", "Baja", None),
            ).lastrowid
        ids = conexion.execute(
            "SELECT id FROM senales WHERE titulo LIKE '[DEMO]%' ORDER BY id"
        ).fetchall()
        hoy = date.today()
        for indice, (factor, titulo, descripcion, tipo, impacto, probabilidad) in enumerate(CASOS):
            datos = ("[DEMO] " + titulo, descripcion, app.FACTORES[factor], app.AMBITOS[factor % len(app.AMBITOS)],
                     app.TIPOS[tipo], app.HORIZONTES[1], fuente_id, impacto, probabilidad,
                     impacto * probabilidad, (hoy + timedelta(days=180)).isoformat(), "Nueva", "demo")
            if indice < len(ids):
                conexion.execute("""UPDATE senales SET titulo=?,descripcion=?,factor=?,ambito=?,tipo=?,horizonte=?,fuente_id=?,
                    impacto=?,probabilidad=?,puntaje=?,vigencia=?,estado=?,autor=? WHERE id=?""", datos + (ids[indice][0],))
            else:
                conexion.execute("""INSERT INTO senales(titulo,descripcion,factor,ambito,tipo,horizonte,fuente_id,
                    impacto,probabilidad,puntaje,vigencia,estado,autor) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", datos)
        for fila in ids[len(CASOS):]:
            conexion.execute("DELETE FROM senales WHERE id=?", (fila[0],))
        conexion.commit()
        print(f"Se cargaron/actualizaron {len(CASOS)} ejemplos sinteticos.")
    finally:
        conexion.close()


if __name__ == "__main__":
    cargar()
