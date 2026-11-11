import io
import json
import os
import re
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


_temporal = tempfile.TemporaryDirectory(prefix="radar-cafetero-test-")
os.environ.pop("DATABASE_URL", None)
os.environ["DB"] = os.path.join(_temporal.name, "test.sqlite3")
os.environ["SECRET_KEY"] = "clave-test-local"

import bd
from app import AMBITOS, FACTORES, TIPOS, app, esquema_senales_estructuradas
import worker


class RadarAppTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def _login(self, usuario="admin", clave="admin123"):
        respuesta = self.client.get("/login")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', respuesta.text).group(1)
        return self.client.post("/login", data={"csrf_token": csrf, "usuario": usuario, "clave": clave},
                                follow_redirects=True)

    def _csrf(self):
        with self.client.session_transaction() as session:
            return session["csrf"]

    def test_login_permiso_y_csrf(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        self._login("analista", "analista123")
        bloqueado = self.client.post("/senal/nueva", data={"titulo": "sin token"})
        self.assertEqual(bloqueado.status_code, 400)
        self.assertEqual(self.client.get("/usuarios").status_code, 403)

    def test_registro_manual_panel_filtro_y_exportaciones(self):
        self._login()
        csrf = self._csrf()
        respuesta = self.client.post("/senal/nueva", data={
            "csrf_token": csrf, "titulo": "Lluvias intensas en zona cafetera", "descripcion": "Alerta oficial",
            "implicaciones": "Revisar cosecha", "factor": "Ecológico", "ambito": "País o región",
            "tipo": "Amenaza", "horizonte": "Corto plazo", "fuente_id": "0", "impacto": "4",
            "probabilidad": "3", "vigencia": ""})
        self.assertEqual(respuesta.status_code, 302)
        panel = self.client.get("/?factor=Ecol%C3%B3gico&tipo=Amenaza")
        self.assertEqual(panel.status_code, 200)
        self.assertIn("Lluvias intensas en zona cafetera", panel.text)
        self.assertNotIn("Mercado y costos", panel.text)
        excel = self.client.get("/exportar.xlsx?factor=Ecol%C3%B3gico")
        pdf = self.client.get("/exportar.pdf?factor=Ecol%C3%B3gico")
        self.assertEqual(excel.status_code, 200)
        self.assertTrue(excel.data.startswith(b"PK"))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.data.startswith(b"%PDF-1.4"))

    def test_catalogo_y_esquema_pestel(self):
        self._login()
        with app.app_context():
            fuentes = bd.listar_fuentes()
        self.assertGreaterEqual(len(fuentes), 12)
        self.assertTrue(any("IDEAM" in fuente["nombre"] for fuente in fuentes))
        schema = esquema_senales_estructuradas()["properties"]["senales"]["items"]
        self.assertEqual(schema["properties"]["factor"]["enum"], FACTORES)
        self.assertIn("Información de seguimiento", TIPOS)
        self.assertEqual(len(FACTORES), 6)
        self.assertTrue(AMBITOS)
        pestel = self.client.get("/pestel?dimension=Ecol%C3%B3gico")
        self.assertEqual(pestel.status_code, 200)
        self.assertIn("El Niño y La Niña", pestel.text)

    def test_configuracion_de_frecuencia_de_fuente(self):
        self._login()
        with app.app_context():
            fuente = bd.buscar_fuente_por_url("https://www.ideam.gov.co/sala-de-prensa/boletines")
        respuesta = self.client.post("/fuentes", data={"csrf_token": self._csrf(), "accion": "programar",
            "fuente_id": str(fuente["id"]), "frecuencia_minutos": "180", "escaneo_habilitado": "on"})
        self.assertEqual(respuesta.status_code, 302)
        with app.app_context():
            actualizado = next(f for f in bd.listar_fuentes() if f["id"] == fuente["id"])
        self.assertEqual(actualizado["frecuencia_minutos"], 180)
        self.assertTrue(actualizado["escaneo_habilitado"])

    def test_migracion_aditiva_preserva_senales_y_fuentes(self):
        ruta = os.path.join(_temporal.name, "db-anterior.sqlite3")
        conexion = sqlite3.connect(ruta)
        conexion.executescript("""
        CREATE TABLE usuarios(id INTEGER PRIMARY KEY, usuario TEXT UNIQUE NOT NULL, clave TEXT NOT NULL, rol TEXT NOT NULL);
        CREATE TABLE fuentes(id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL, tipo TEXT NOT NULL, confiabilidad TEXT NOT NULL, url TEXT);
        CREATE TABLE senales(id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, descripcion TEXT, factor TEXT NOT NULL,
          ambito TEXT NOT NULL, tipo TEXT NOT NULL, horizonte TEXT NOT NULL, fuente_id INTEGER, impacto INTEGER NOT NULL,
          probabilidad INTEGER NOT NULL, puntaje INTEGER NOT NULL, vigencia TEXT, estado TEXT NOT NULL DEFAULT 'Nueva',
          autor TEXT, creada TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE comentarios(id INTEGER PRIMARY KEY, senal_id INTEGER NOT NULL, autor TEXT NOT NULL, contenido TEXT NOT NULL,
          creado TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE indicadores_empresa(id INTEGER PRIMARY KEY, clave TEXT NOT NULL, valor REAL NOT NULL, unidad TEXT NOT NULL,
          fecha TEXT NOT NULL, autor TEXT NOT NULL, detalle TEXT, creado TEXT DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO usuarios VALUES(1,'historico','hash','admin');
        INSERT INTO fuentes VALUES(1,'Fuente histórica','Institucional','Alta','https://institucion.gov.co/');
        INSERT INTO senales(id,titulo,descripcion,factor,ambito,tipo,horizonte,fuente_id,impacto,probabilidad,puntaje,autor)
          VALUES(1,'Señal histórica','Registro previo','Económico','Sector','Amenaza','Corto plazo',1,3,3,9,'historico');
        INSERT INTO indicadores_empresa(id,clave,valor,unidad,fecha,autor) VALUES(1,'historico',9,'COP/kg','2025-01-01','historico');
        """)
        conexion.commit()
        conexion.close()
        original = bd.RUTA_BD
        try:
            bd.RUTA_BD = ruta
            bd.inicializar_bd()
            with app.app_context():
                senales = bd.consultar_senales("admin")
                fuentes = bd.listar_fuentes()
                indicadores = bd.listar_indicadores()
            self.assertEqual(senales[0]["titulo"], "Señal histórica")
            self.assertEqual(senales[0]["origen"], "manual")
            self.assertTrue(any(f["nombre"] == "Fuente histórica" for f in fuentes))
            self.assertEqual(indicadores[0]["clave"], "historico")
        finally:
            bd.RUTA_BD = original

    def test_worker_guardar_y_deduplicar_sin_llamada_real(self):
        self._login()
        with app.app_context():
            fuente = bd.buscar_fuente_por_url("https://www.ideam.gov.co/sala-de-prensa/boletines")
            ahora = worker.datetime.now(worker.timezone.utc).isoformat(timespec="seconds")
            for clave in ("precio_interno_fnc", "precio_ico_icip"):
                bd.registrar_intento_indicador(clave, ahora, "correcto")
        item = {"titulo": "Alerta lluvias zona cafetera", "descripcion": "Boletín de prueba institucional.",
            "implicaciones": "Posible afectación a cultivos.", "factor": "Ecológico", "ambito": "País o región",
            "tipo": "Amenaza", "horizonte": "Corto plazo", "impacto": 3, "probabilidad": 3,
            "vigencia": None, "fecha_publicacion": "2026-11-09", "justificacion": "La alerta cubre la región.",
            "evidencia": "lluvias intensas", "region_afectada": "Huila", "tipo_publicacion": "Alerta",
            "url_original": "https://www.ideam.gov.co/boletin-prueba", "impacto_produccion": "Riesgo por lluvia",
            "impacto_comercializacion": "No disponible"}
        payload = json.dumps({"success": True, "data": {"json": {"senales": [item]}}}).encode()
        with app.app_context(), patch.object(worker, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(payload)):
            resultado = worker.ejecutar_escaneo()
        self.assertEqual(resultado["errores"], 0)
        self.assertGreaterEqual(resultado["nuevas"], 1)
        with app.app_context():
            self.assertTrue(bd.senal_ya_registrada(fuente["id"], item["titulo"], item["factor"]))
            repetidas = worker._guardar_senales(fuente, [item], worker.datetime.now(worker.timezone.utc))
        self.assertEqual(repetidas, (0, 1))

    def test_analisis_url_y_precio_fnc_simulados(self):
        import app as modulo_app
        self._login()
        csrf = self._csrf()
        senal = {"titulo": "Cambio en requisitos de exportación de café", "descripcion": "La entidad publica un requisito.",
            "implicaciones": "Verificar documentación antes de exportar.", "factor": "Legal", "ambito": "Sector",
            "tipo": "Información de seguimiento", "horizonte": "Corto plazo", "impacto": 2,
            "probabilidad": 5, "vigencia": None, "fecha_publicacion": "2026-11-09",
            "justificacion": "La fuente describe el nuevo requisito.", "evidencia": "requisito de exportación",
            "region_afectada": "Colombia", "tipo_publicacion": "Norma",
            "numero_norma": "Resolución 123 de 2026", "entidad_emisora": "Ministerio de Agricultura",
            "url_original": "https://ministerio.gov.co/norma-cafe", "impacto_produccion": "No disponible",
            "impacto_comercializacion": "Verificar requisitos"}
        payload = json.dumps({"success": True, "data": {"metadata": {"title": "Fuente institucional"},
            "json": {"senales": [senal]}}}).encode()
        with patch.object(modulo_app, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(payload)):
            respuesta = self.client.post("/analizar-pagina", data={"csrf_token": csrf,
                "url": "https://ministerio.gov.co/noticias/cafe"})
        self.assertEqual(respuesta.status_code, 302)
        panel_texto = self.client.get("/").text
        self.assertIn("Radar Cafetero", panel_texto)
        self.assertIn("Resolución 123 de 2026", panel_texto)

        modulo_app._cache_precio_fnc.update(vence=0, dato=None)
        os.environ["FIRECRAWL_API_KEY"] = "test-key"
        precio = json.dumps({"success": True, "data": {"json": {"valor": 2000000,
            "fecha": "2026-11-09", "unidad": "COP/carga de 125 kg"}}}).encode()
        with patch.object(modulo_app, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(precio)):
            respuesta_precio = self.client.post("/api/precio-fnc", data={"csrf_token": self._csrf()})
        self.assertEqual(respuesta_precio.status_code, 200)
        self.assertEqual(respuesta_precio.json["valor"], 2000000)

        modulo_app._cache_precio_ico.update(vence=0, dato=None)
        ico = json.dumps({"success": True, "data": {"json": {"valor": 250.25,
            "fecha": "2026-11-09", "unidad": "US cents/lb"}}}).encode()
        with patch.object(modulo_app, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(ico)):
            respuesta_ico = self.client.post("/api/precio-ico", data={"csrf_token": self._csrf()})
        self.assertEqual(respuesta_ico.status_code, 200)
        self.assertEqual(respuesta_ico.json["unidad"], "US cents/lb")


if __name__ == "__main__":
    unittest.main()
