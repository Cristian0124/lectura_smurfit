"""Public commodity reference data from official national and UN sources."""
import csv
import io
import json
import time
import zipfile
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL_TRM = "https://www.datos.gov.co/resource/32sa-8pi3.json"
URL_FAO_PRECIOS = "https://bulks-faostat.fao.org/production/Prices_E_All_Data_(Normalized).zip"
URL_FAO_PP = "https://www.fao.org/faostat/en/#data/PP"
_cache_trm = {"vence": 0, "dato": None}
_cache_cafe = {"vence": 0, "datos": None}


def _leer(url, timeout=15):
    req = Request(url, headers={"User-Agent": "RadarCafetero/1.0"})
    with urlopen(req, timeout=timeout) as respuesta:
        return respuesta.read()


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
    """Latest country-level farm-gate coffee prices reported to FAOSTAT (USD/tonne)."""
    ahora = time.time()
    if _cache_cafe["datos"] and ahora < _cache_cafe["vence"]:
        return _cache_cafe["datos"]

    archivo = _leer(URL_FAO_PRECIOS, timeout=60)
    with zipfile.ZipFile(io.BytesIO(archivo)) as zf:
        nombre = next((n for n in zf.namelist()
                       if n.lower().endswith(".csv") and "all_data" in n.lower()), None)
        if not nombre:
            raise ValueError("FAOSTAT prices file has no data CSV")
        registros = {}
        with zf.open(nombre) as raw:
            lector = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            for fila in lector:
                item = (fila.get("Item") or "").strip().casefold()
                elemento = (fila.get("Element") or "").strip().casefold()
                unidad = (fila.get("Unit") or "").strip()
                area = (fila.get("Area") or "").strip()
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
                if not area or value < 0:
                    continue
                unit = "USD/tonne"
                registros.setdefault(area, {})[year] = {"year": year, "value": value, "unit": unit}

    paises = []
    for area, years in registros.items():
        historico = [years[y] for y in sorted(years)]
        if historico:
            paises.append({"pais": area, "ultimo": historico[-1], "historico": historico[-12:]})
    paises.sort(key=lambda p: p["pais"].casefold())
    if not paises:
        raise ValueError("FAOSTAT returned no country producer price observations in USD")
    datos = {"paises": paises, "frecuencia": "Anual; ultimo dato reportado por cada pais",
             "fuente": "FAO, FAOSTAT - Producer Prices (Coffee, green)",
             "url": URL_FAO_PP, "consultado": datetime.now().isoformat(timespec="minutes")}
    _cache_cafe.update(datos=datos, vence=ahora + 86400)
    return datos
