"""Genera una hoja .xlsx con formato sin dependencias externas."""
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


ENCABEZADOS = [
    "Título", "Descripción", "Factor PESTEL", "Ámbito", "Tipo", "Horizonte",
    "Fuente", "Confiabilidad", "Impacto", "Probabilidad", "Riesgo",
    "Nivel de riesgo", "Vigencia", "Estado", "Autor", "Fecha de registro",
]
ANCHOS = [34, 58, 20, 25, 17, 18, 28, 17, 12, 14, 12, 18, 16, 18, 18, 22]
LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _celda(referencia, valor, estilo=0, numerica=False):
    atributo_estilo = f' s="{estilo}"' if estilo else ""
    if numerica:
        return f'<c r="{referencia}"{atributo_estilo}><v>{valor}</v></c>'
    texto = escape(str(valor if valor is not None else ""))
    return f'<c r="{referencia}" t="inlineStr"{atributo_estilo}><is><t xml:space="preserve">{texto}</t></is></c>'


def generar_excel(senales, nivel):
    filas = ['<row r="1" ht="30" customHeight="1">' + "".join(
        _celda(f"{LETRAS[i]}1", texto, 1) for i, texto in enumerate(ENCABEZADOS)) + "</row>"]
    estilos_riesgo = {"Alto": 3, "Medio": 4, "Bajo": 5}
    for numero_fila, senal in enumerate(senales, 2):
        riesgo = nivel(senal["puntaje"])
        datos = [senal["titulo"], senal["descripcion"], senal["factor"], senal["ambito"],
                 senal["tipo"], senal["horizonte"], senal["fuente"] or "-", senal["conf"] or "-",
                 senal["impacto"], senal["probabilidad"], senal["puntaje"], riesgo,
                 senal["vigencia"] or "-", senal["estado"], senal["autor"] or "-", senal["creada"] or "-"]
        estilo_fila = 2 if numero_fila % 2 == 0 else 0
        celdas = []
        for indice, valor in enumerate(datos):
            estilo = estilos_riesgo[riesgo] if indice == 10 else estilo_fila
            celdas.append(_celda(f"{LETRAS[indice]}{numero_fila}", valor, estilo,
                                 numerica=indice in (8, 9, 10)))
        filas.append(f'<row r="{numero_fila}" ht="36" customHeight="1">' + "".join(celdas) + "</row>")

    total_filas = len(filas)
    columnas = "".join(f'<col min="{i}" max="{i}" width="{ancho}" customWidth="1"/>'
                       for i, ancho in enumerate(ANCHOS, 1))
    hoja = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView showGridLines="0" workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        f'<cols>{columnas}</cols><sheetData>{"".join(filas)}</sheetData>'
        f'<autoFilter ref="A1:P{total_filas}"/><pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.2" footer="0.2"/>'
        '</worksheet>')
    estilos = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
      <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts>
      <fills count="7"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FF24543D"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFF3F6F3"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFFCE4D6"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/></patternFill></fill>
        <fill><patternFill patternType="solid"><fgColor rgb="FFE2F0D9"/></patternFill></fill></fills>
      <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
      <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
      <cellXfs count="6"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
        <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
        <xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
        <xf numFmtId="0" fontId="0" fillId="4" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
        <xf numFmtId="0" fontId="0" fillId="5" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
        <xf numFmtId="0" fontId="0" fillId="6" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs>
      <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
    </styleSheet>'''
    salida = BytesIO()
    with ZipFile(salida, "w", ZIP_DEFLATED) as archivo:
        archivo.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
          <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
          <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
          <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
          </Types>''')
        archivo.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
          <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
          </Relationships>''')
        archivo.writestr("xl/workbook.xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
          <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          <sheets><sheet name="Lectura de entorno" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        archivo.writestr("xl/_rels/workbook.xml.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
          <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
          <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
          </Relationships>''')
        archivo.writestr("xl/worksheets/sheet1.xml", hoja)
        archivo.writestr("xl/styles.xml", estilos)
    return salida.getvalue()
