"""Public commodity reference data from official national and UN sources."""
import csv
import io
import json
import re
import time
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL_TRM = "https://www.datos.gov.co/resource/32sa-8pi3.json"
URL_FAO_PRECIOS = "https://bulks-faostat.fao.org/production/Prices_E_All_Data_(Normalized).zip"
URL_FAO_PP = "https://www.fao.org/faostat/en/#data/PP"
_cache_trm = {"vence": 0, "dato": None}
_cache_cafe = {"vence": 0, "datos": None}
_cache_precios_fnc = {"vence": 0, "datos": None}


def _leer(url, timeout=15):
    req = Request(url, headers={"User-Agent": "RadarCafetero/1.0"})
    with urlopen(req, timeout=timeout) as respuesta:
        return respuesta.read()


class _TextoVisible(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.ocultar = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.ocultar += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.ocultar:
            self.ocultar -= 1

    def handle_data(self, data):
        if not self.ocultar and data.strip():
            self.partes.append(data.strip())


def _numero_referencia(texto, decimal=False):
    valor = texto.strip().replace(" ", "")
    if decimal:
        if "," in valor and "." in valor:
            valor = valor.replace(".", "").replace(",", ".")
        else:
            valor = valor.replace(",", ".")
        return float(valor)
    return float(re.sub(r"\D", "", valor))


def obtener_precios_fnc():
    """Read FNC's public daily internal and ICE New York reference prices without a paid API."""
    ahora = time.time()
    if _cache_precios_fnc["datos"] and ahora < _cache_precios_fnc["vence"]:
        return _cache_precios_fnc["datos"]
    # The methodology page does not publish the live quotes. The FNC homepage
    # exposes both daily values and their publication dates in its HTML.
    url = "https://federaciondecafeteros.org/inicio/"
    parser = _TextoVisible()
    parser.feed(_leer(url, timeout=20).decode("utf-8", "replace"))
    texto = re.sub(r"\s+", " ", " ".join(parser.partes))

    def extraer(etiqueta, decimal=False):
        coincidencia = re.search(etiqueta + r"\s*:\s*\$?\s*([\d.,]+)", texto, re.IGNORECASE)
        if not coincidencia:
            raise ValueError(f"FNC no publico {etiqueta} en la pagina consultada")
        alrededor = texto[coincidencia.end():coincidencia.end() + 600]
        fecha = re.search(r"Fecha\s*:\s*(\d{4}-\d{2}-\d{2})", alrededor, re.IGNORECASE)
        if not fecha:
            raise ValueError(f"FNC no publico la fecha de {etiqueta}")
        return {"valor": _numero_referencia(coincidencia.group(1), decimal), "fecha": fecha.group(1)}

    dato = {"precio_interno": extraer("Precio interno de referencia"),
            "bolsa_ny": extraer("Bolsa de NY", decimal=True),
            "fuente": "Federacion Nacional de Cafeteros",
            "url": url, "consultado": datetime.now().isoformat(timespec="minutes")}
    _cache_precios_fnc.update(datos=dato, vence=ahora + 600)
    return dato


def obtener_dolar():
    """Official Colombia TRM, published by Superintendencia Financiera."""
    ahora = time.time()
    cache = _cache_trm.get("dato")
    if cache and ahora < cache[0]:
        return cache[1]
    query = urlencode({"$limit": "1", "$order": "vigenciadesde DESC"})
    datos = json.loads(_leer(URL_TRM + "?" + query).decode("utf-8"))
    if not datos or "valor" not in datos[0] or "vigenciadesde" not in datos[0]:
        raise ValueError("TRM source returned no current record")
    registro = {"cop_usd": float(datos[0]["valor"]),
                "fecha": str(datos[0]["vigenciadesde"])[:10],
                "fuente": "Superintendencia Financiera de Colombia (datos.gov.co)"}
    _cache_trm["dato"] = (ahora + 300, registro)
    return registro


def obtener_precios_cafe():
    """Latest Colombian farm-gate coffee prices reported to FAOSTAT (USD/tonne)."""
    ahora = time.time()
    if _cache_cafe["datos"] and ahora < _cache_cafe["vence"]:
        return _cache_cafe["datos"]

    archivo = _leer(URL_FAO_PRECIOS, timeout=60)
    with zipfile.ZipFile(io.BytesIO(archivo)) as zf:
        nombre = next((n for n in zf.namelist()
                       if n.lower().endswith(".csv") and "all_data" in n.lower()), None)
        if not nombre:
            raise ValueError("FAOSTAT prices file has no data CSV")
        historico_colombia = {}
        with zf.open(nombre) as raw:
            lector = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            for fila in lector:
                # The normalized FAOSTAT bulk file is ordered by Area Code.
                # Colombia's FAO area code is 44, so stop once its block ends
                # instead of parsing the remaining million-plus observations.
                try:
                    area_code = int(fila.get("Area Code", ""))
                except (TypeError, ValueError):
                    continue
                if area_code > 44 and historico_colombia:
                    break
                if area_code != 44:
                    continue
                item = (fila.get("Item") or "").strip().casefold()
                elemento = (fila.get("Element") or "").strip().casefold()
                unidad = (fila.get("Unit") or "").strip()
                mes = (fila.get("Months") or "Annual").strip().casefold()
                if item != "coffee, green" or "producer price" not in elemento:
                    continue
                if not (unidad.casefold().startswith("usd/") or "usd" in elemento):
                    continue
                if mes not in ("annual", "annual value", "year", ""):
                    continue
                try:
                    year = int(float(fila.get("Year", "")))
                    value = float((fila.get("Value") or "").replace(",", ""))
                except (TypeError, ValueError):
                    continue
                if value < 0:
                    continue
                unit = "USD/tonne"
                historico_colombia[year] = {"year": year, "value": value, "unit": unit}

    historico = [historico_colombia[y] for y in sorted(historico_colombia)]
    if not historico:
        raise ValueError("FAOSTAT returned no Colombian coffee producer price observations in USD")
    paises = [{"pais": "Colombia", "ultimo": historico[-1], "historico": historico[-12:]}]
    datos = {"paises": paises, "frecuencia": "Anual; ultimo dato reportado por cada pais",
             "fuente": "FAO, FAOSTAT - Producer Prices (Coffee, green)",
             "url": URL_FAO_PP, "consultado": datetime.now().isoformat(timespec="minutes")}
    _cache_cafe.update(datos=datos, vence=ahora + 86400)
    return datos
