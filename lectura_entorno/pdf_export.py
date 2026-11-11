"""Generador PDF minimo para informes de señales, sin bibliotecas binarias externas."""
import textwrap
from datetime import datetime


def generar_pdf(senales, nivel):
    lineas = [f"Radar Cafetero - Informe | Generado {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
              f"Acontecimientos incluidos: {len(senales)}", ""]
    for i, s in enumerate(senales, 1):
        fuente = s["fuente"] or "Sin fuente"
        bloque = [f"{i}. {s['titulo']}",
                  f"PESTEL: {s['factor']} | Tipo: {s['tipo']} | Riesgo: {nivel(s['puntaje'])} ({s['puntaje']}/25)",
                  f"Fuente: {fuente} | Publicación: {s['fecha_publicacion'] or 'No disponible'}",
                  f"URL original: {s['url_original'] or s['fuente_url'] or 'No disponible'}",
                  f"Resumen: {s['descripcion'] or 'No disponible'}"]
        if s["tipo_publicacion"] == "Norma":
            bloque.append(f"Norma: {s['numero_norma'] or 'No disponible'} | Entidad: {s['entidad_emisora'] or 'No disponible'} | Vigencia: {s['vigencia'] or 'No disponible'}")
        lineas.extend(textwrap.wrap(" ".join(bloque), width=105, break_long_words=True, break_on_hyphens=False))
        lineas.append("")

    paginas = [lineas[i:i + 48] for i in range(0, len(lineas), 48)] or [[]]
    objetos = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    ids_pagina = [4 + i * 2 for i in range(len(paginas))]
    objetos.append((f"<< /Type /Pages /Kids [{' '.join(f'{i} 0 R' for i in ids_pagina)}] /Count {len(ids_pagina)} >>").encode())
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for indice, lineas_pagina in enumerate(paginas):
        contenido = ["BT", "/F1 9 Tf", "48 790 Td", "12 TL"]
        for linea in lineas_pagina:
            raw = linea.encode("cp1252", errors="replace")
            literal = "".join(chr(b) if 32 <= b <= 126 and b not in (40, 41, 92)
                              else "\\" + chr(b) if b in (40, 41, 92) else f"\\{b:03o}" for b in raw)
            contenido.append(f"({literal}) Tj T*")
        contenido.append("ET")
        stream = "\n".join(contenido).encode("cp1252", errors="replace")
        page_id = ids_pagina[indice]
        content_id = page_id + 1
        objetos.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
                        f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>").encode())
        objetos.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for numero, contenido in enumerate(objetos, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{numero} 0 obj\n".encode() + contenido + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)
