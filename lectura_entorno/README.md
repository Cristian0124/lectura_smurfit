# Radar Cafetero · Lectura de entorno

Aplicación Flask para vigilar acontecimientos PESTEL que puedan afectar la producción y comercialización del café colombiano. Conserva el registro manual, roles, comentarios, filtros y análisis Firecrawl bajo demanda; agrega un catálogo institucional, trazabilidad de señales automáticas y un panel con exportaciones.

## Arquitectura

- `app.py`: rutas Flask, login, permisos, CSRF, formularios y consumo de Firecrawl.
- `bd.py`: SQLite local o PostgreSQL (Neon), con migraciones aditivas y trazabilidad de ejecución.
- `worker.py`: proceso separado que mapea publicaciones oficiales con Firecrawl, extrae páginas nuevas y guarda novedades cafeteras.
- `fuentes_cafeteras.py`: catálogo institucional inicial, agregado sin reemplazar fuentes existentes.
- `mercado.py`: consultas estructuradas de TRM de datos.gov.co y precios anuales al productor de café verde en FAOSTAT.
- `excel_export.py` y `pdf_export.py`: informes de las señales filtradas en el Panel.
- `templates/`: navegación, formulario manual, análisis automático, fuentes, PESTEL y Panel.

## Ejecución local

En Windows, ejecuta `iniciar.bat`. Cuando `FIRECRAWL_API_KEY` está configurada, el script inicia además un worker local oculto que revisa las fuentes cada 10 minutos. También puedes usar:

```sh
pip install -r requirements.txt
python app.py
```

SQLite usa `entorno.db` por defecto; configura `DB` para cambiar su ruta. En una base local nueva se crean las cuentas de demostración `admin/admin123`, `analista/analista123` y `directivo/decisor123`. No expongas esas credenciales.

## Variables

- `DATABASE_URL`: PostgreSQL/Neon. Si no está definida, se usa SQLite.
- `DB`: ruta opcional de SQLite.
- `SECRET_KEY`: clave de sesión; requerida cuando existe `DATABASE_URL`.
- `FIRECRAWL_API_KEY`: análisis de URL, consulta de precio FNC y revisión programada.
- `INITIAL_ADMIN_USER` y `INITIAL_ADMIN_PASSWORD`: primer administrador de una base PostgreSQL vacía; mínimo 12 caracteres para la clave.

No incluyas credenciales en el repositorio. Firecrawl aplica límites y créditos; mapear sitios y extraer páginas estructuradas consume cuota. El Cron Job de Render se programa cada 10 minutos (`*/10 * * * *`). En cada fuente se priorizan publicaciones cafeteras y se extraen hasta tres páginas nuevas por ejecución (`RADAR_MAX_PAGINAS_POR_FUENTE`). Los precios FNC, ICO y TRM se consultan cada 10 minutos por defecto; FAOSTAT se revisa diariamente porque su serie es anual. La cadencia indica cuándo consulta el sistema, no cuándo una institución publica.

## Render y Neon

`render.yaml` define el servicio web y un Cron Job separado. Ambos requieren `DATABASE_URL`, `FIRECRAWL_API_KEY` y una `SECRET_KEY`; la inicialización de una base vacía requiere además las dos variables `INITIAL_ADMIN_*`. Render cron ejecuta en UTC. Configura los valores en ambos servicios antes de desplegar. La conexión real a Neon y Firecrawl depende de las credenciales del entorno de Render.

El Worker usa Firecrawl Map para descubrir enlaces institucionales y Scrape para extraer páginas nuevas dentro del dominio de cada fuente. Guarda las URL ya consultadas para no volver a gastar créditos en la misma publicación. Cada página se analiza con criterios explícitos de relación con cultivo, producción, calidad, clima en zonas productoras, costos, precio, compra, comercialización o exportación del café. Las alertas ambientales generales solo se guardan cuando la fuente y el análisis documentan su efecto en cafetales. La vista **Fuentes de información** muestra únicamente el enlace y la fecha de revisión; su fecha corresponde a la última consulta, no confirma una publicación nueva.

La extracción solo se guarda cuando Firecrawl devuelve una señal con campos válidos. La aplicación no sigue instrucciones incluidas en páginas externas, valida las URLs de publicación contra el dominio institucional y conserva fecha de publicación, revisión, evidencia y fuente. El deduplicado se basa en fuente, título y factor PESTEL. Las variables de lluvia y temperatura solo se muestran cuando su publicación oficial incluye valor, unidad, fecha y región; no se estima el factor de rendimiento comercial sin análisis físico del lote.

## Indicadores y sus límites

- **FNC**: el precio interno diario de referencia para café pergamino seco se extrae de la página oficial de la Federación (carga de 125 kg) cuando Firecrawl lo verifica. Si falta valor, fecha o unidad, el Panel indica que la primera revisión está pendiente o conserva el último valor histórico, con su fecha y revisión.
- **TRM**: consulta el conjunto oficial de datos.gov.co de la Superintendencia Financiera.
- **FAOSTAT**: último precio anual al productor por país (café verde, USD/tonelada); no equivale a una cotización de bolsa ni a precio diario.
- **ICO**: el catálogo enlaza su información pública de mercado. Algunos históricos y descargas diarias requieren acceso de miembros o suscripción; no se simulan cifras.
- **Factor de rendimiento**: no se calcula sin fórmula oficial y datos de calidad suficientes.

No se conserva la sección independiente de cacao/costos. Los registros históricos existentes de usuarios, señales, fuentes e indicadores no se borran. Las migraciones solo agregan columnas/tablas; las señales antiguas quedan marcadas como manuales.

## PESTEL y ADM

PESTEL analiza factores políticos, económicos, sociales, tecnológicos, ecológicos y legales externos; aquí se aplica al sector cafetero sin cambiar la estructura de sus seis dimensiones. ADM (Architecture Development Method) es el núcleo del método TOGAF: un ciclo iterativo de fases que guía la transformación de una arquitectura actual (AS-IS) a una arquitectura objetivo (TO-BE). ADM estructura el desarrollo de arquitectura empresarial; PESTEL analiza el entorno externo. No son metodologías intercambiables.

## Verificación

Desde la carpeta `lectura_entorno`, ejecuta `python -m unittest discover -s tests -v`. Estas pruebas cubren migración aditiva, persistencia, permisos, filtros, exportaciones, análisis cafetero, descubrimiento de páginas, deduplicado e idempotencia del Worker con respuestas HTTP simuladas; no prueban credenciales ni disponibilidad externa de Neon, Firecrawl, FNC, ICO o FAOSTAT.

## Referencias institucionales

- La [Federación Nacional de Cafeteros](https://federaciondecafeteros.org/publicaciones/) describe el precio interno como precio base de mercado ligado a Bolsa de Nueva York, tasa de cambio y diferencial. El sitio también presenta el indicador de referencia por carga de 125 kg.
- El [IDEAM publica boletines, alertas y pronósticos](https://www.ideam.gov.co/sala-de-prensa/boletines); su informe hidrometeorológico diario cubre lluvias, temperaturas y alertas nacionales.
- El [Diario Oficial de la Imprenta Nacional](https://svrpubindc.imprenta.gov.co/diario/) y [SUIN-Juriscol](https://www.suin-juriscol.gov.co/suin/) son los enlaces institucionales del catálogo normativo.
- [FAOSTAT](https://www.fao.org/faostat/) ofrece datos oficiales por país y año; la aplicación distingue esos precios al productor de una cotización diaria.
- La [ICO explica su indicador compuesto diario I-CIP](https://www.ico.org/resources/public-market-information/) y señala qué extractos de datos requieren solicitud o acceso según la categoría de usuario.
- The Open Group organiza TOGAF 10 en contenido fundamental que incluye por separado [Core Concepts y ADM](https://help.opengroup.org/hc/en-us/articles/32726995273362-Understanding-the-TOGAF-Standard). Su ciclo incluye fases de visión, arquitectura de negocio/sistemas/tecnología, soluciones, migración, gobernanza y gestión del cambio, con gestión continua de requisitos.
- El [Blueprint de Render](https://render.com/docs/blueprint-spec) admite Cron Jobs con una expresión cron para ejecutar tareas programadas separadas del servidor web.
