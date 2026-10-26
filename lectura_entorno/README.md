# Radar de entorno

Aplicacion web para registrar, organizar y consultar senales del entorno con el metodo PESTEL. Se adapta a organizaciones, sectores y paises distintos. Al analizar una URL, Firecrawl extrae datos estructurados y guarda automaticamente las senales PESTEL detectadas para organizaciones de cualquier sector en Colombia.

## Funciones disponibles

- Registro y seguimiento de senales PESTEL, con descripcion, implicaciones, impacto, probabilidad, horizonte, vigencia y estado.
- Analisis automatico de paginas con Firecrawl, almacenamiento de fuente, evidencia y justificacion.
- Panel, alertas, informe imprimible y exportacion a Excel.
- Roles de administracion, analisis y lectura ejecutiva.
- Guia de preguntas PESTEL que se puede adaptar al contexto de analisis.

## Inicio local

En Windows, ejecuta `iniciar.bat`. En otros entornos:

```sh
pip install -r requirements.txt
python app.py
```

La aplicacion estara en http://127.0.0.1:5000. En una base nueva se crean usuarios de demostracion (`admin/admin123`, `analista/analista123`, `directivo/decisor123`); cambia estas credenciales antes de publicar la aplicacion. Define `SECRET_KEY` y, opcionalmente, `DB` mediante variables de entorno.

## Analisis automatico con Firecrawl

La opcion **Analizar pagina** extrae hasta cinco senales distintas desde una URL publica y las guarda automaticamente en SQLite. El sistema completa titulo, descripcion, implicaciones, factor, ambito, tipo, horizonte, impacto, probabilidad, puntaje, vigencia, fuente, fechas y justificacion. Cada se?al queda en estado `Nueva` y aparece en su dimension PESTEL, el panel, el informe y Excel. Las URL repetidas no crean duplicados.

Configura la clave desde PowerShell:

```powershell
setx FIRECRAWL_API_KEY "tu_clave_de_firecrawl"
```

Cierra y vuelve a abrir la terminal o el IDE para que la variable este disponible. No pongas la clave en el codigo ni la subas al repositorio. La integracion usa el endpoint REST v2 de Firecrawl y la biblioteca estandar de Python; no requiere instalar un SDK adicional. El modo JSON estructurado usa un modelo de lenguaje de Firecrawl y consume mas creditos que una extraccion de texto simple.

## Datos de demostracion

`python cargar_senales_demo.py` agrega ejemplos sinteticos que no representan organizaciones ni hallazgos reales. La base `entorno.db` se conserva entre ejecuciones.

## Publicacion

Consulta [PYTHONANYWHERE.md](PYTHONANYWHERE.md) para la guia de despliegue. Sustituye las rutas de ejemplo por las de tu entorno.
