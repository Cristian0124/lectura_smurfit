"""Catalogo inicial de fuentes institucionales para vigilancia del cafe."""

FUENTES_CAFETERAS = [
    ("Ministerio de Agricultura y Desarrollo Rural", "Colombia", "https://www.minagricultura.gov.co/"),
    ("Federacion Nacional de Cafeteros", "Colombia", "https://federaciondecafeteros.org/"),
    ("IDEAM - boletines, pronosticos y alertas", "Colombia", "https://www.ideam.gov.co/sala-de-prensa/boletines"),
    ("IDEAM DHIME - datos hidrometeorologicos historicos", "Colombia", "https://ideam.gov.co/dhime"),
    ("Ministerio de Ambiente y Desarrollo Sostenible", "Colombia", "https://www.minambiente.gov.co/"),
    ("DANE", "Colombia", "https://www.dane.gov.co/"),
    ("Banco de la Republica", "Colombia", "https://www.banrep.gov.co/"),
    ("DIAN", "Colombia", "https://www.dian.gov.co/"),
    ("Diario Oficial - Imprenta Nacional", "Colombia", "https://svrpubindc.imprenta.gov.co/diario/"),
    ("SUIN-Juriscol", "Colombia", "https://www.suin-juriscol.gov.co/suin/"),
    ("Organizacion Internacional del Cafe (ICO)", "Internacional", "https://www.ico.org/"),
    ("FAOSTAT - precios y produccion", "Internacional", "https://www.fao.org/faostat/"),
    ("Organizacion Meteorologica Mundial (WMO)", "Internacional", "https://wmo.int/"),
]


def sembrar_catalogo(bd):
    """Agrega fuentes iniciales sin reemplazar el catalogo ni sus frecuencias."""
    for nombre, pais, url in FUENTES_CAFETERAS:
        bd.asegurar_fuente_catalogo(nombre, f"Entidad oficial - {pais}", "Alta", url, 10)
