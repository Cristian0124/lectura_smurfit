# Radar Cafetero · Lectura de entorno

Aplicación Flask para vigilar acontecimientos PESTEL que puedan afectar la producción y comercialización del café colombiano. Conserva el registro manual, roles, comentarios, filtros y análisis Firecrawl bajo demanda; agrega un catálogo institucional, trazabilidad de señales automáticas y un panel con exportaciones.

## Arquitectura

- `app.py`: rutas Flask, login, permisos, CSRF, formularios y consumo de Firecrawl.
- `bd.py`: SQLite local o PostgreSQL (Neon), con migraciones aditivas y trazabilidad de ejecución.
- `worker.py`: proceso separado que consulta las fuentes habilitadas con Firecrawl y guarda publicaciones nuevas.
- `fuentes_cafeteras.py`: catálogo institucional inicial, agregado sin reemplazar fuentes existentes.
- `mercado.py`: consultas estructuradas de TRM de datos.gov.co y precios anuales al productor de café verde en FAOSTAT.
- `excel_export.py` y `pdf_export.py`: informes de las señales filtradas en el Panel.
- `templates/`: navegación, formulario manual, análisis automático, fuentes, PESTEL y Panel.

## Ejecución local

En Windows, ejecuta `iniciar.bat`. También puedes usar:

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

No incluyas credenciales en el repositorio. Firecrawl aplica límites y créditos; el análisis estructurado y la verificación de inyección consumen cuota. La frecuencia por fuente se puede ajustar en **Fuentes** a 30 min, 1 h, 3 h, 6 h o 24 h. El Cron Job de Render se despierta cada hora y procesa las fuentes que ya vencieron por su frecuencia configurada. Los indicadores FNC e ICO se revisan cada seis horas por defecto (`RADAR_INDICADORES_FRECUENCIA_MINUTOS`) y se leen del almacenamiento al abrir el Panel, sin pagar otra extracción por cada visita.

## Render y Neon

`render.yaml` define el servicio web y un Cron Job separado. Ambos requieren `DATABASE_URL`, `FIRECRAWL_API_KEY` y una `SECRET_KEY`; la inicialización de una base vacía requiere además las dos variables `INITIAL_ADMIN_*`. Render cron ejecuta en UTC. Configura los valores en ambos servicios antes de desplegar. La conexión real a Neon y Firecrawl depende de las credenciales del entorno de Render.

El Worker revisa la URL registrada para cada fuente mediante una extracción estructurada de Firecrawl. Las páginas institucionales tienen diseños y mecanismos de publicación distintos: un sitio que no exponga sus publicaciones recientes en esa URL puede requerir configurar una URL más específica o una integración oficial/API/feed. El catálogo no afirma que una extracción haya funcionado: muestra última revisión, ejecuciones, errores y señales guardadas. Las publicaciones manuales y automáticas se distinguen en la base.

La extracción solo se guarda cuando Firecrawl devuelve una señal con campos válidos. La aplicación no sigue instrucciones incluidas en páginas externas, valida las URLs de publicación contra el dominio institucional y conserva fecha de publicación, revisión, evidencia y fuente. El deduplicado se basa en fuente, título y factor PESTEL.

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

Desde la carpeta `lectura_entorno`, ejecuta `python -m unittest discover -s tests -v`. Estas pruebas cubren migración aditiva, persistencia, permisos, filtros, exportaciones, esquema de análisis, extracción del precio e idempotencia del Worker con respuestas HTTP simuladas; no prueban credenciales ni disponibilidad externa de Neon, Firecrawl, FNC, ICO o FAOSTAT.

## Referencias institucionales

- La [Federación Nacional de Cafeteros](https://federaciondecafeteros.org/publicaciones/) describe el precio interno como precio base de mercado ligado a Bolsa de Nueva York, tasa de cambio y diferencial. El sitio también presenta el indicador de referencia por carga de 125 kg.
- El [IDEAM publica boletines, alertas y pronósticos](https://www.ideam.gov.co/sala-de-prensa/boletines); su informe hidrometeorológico diario cubre lluvias, temperaturas y alertas nacionales.
- El [Diario Oficial de la Imprenta Nacional](https://svrpubindc.imprenta.gov.co/diario/) y [SUIN-Juriscol](https://www.suin-juriscol.gov.co/suin/) son los enlaces institucionales del catálogo normativo.
- [FAOSTAT](https://www.fao.org/faostat/) ofrece datos oficiales por país y año; la aplicación distingue esos precios al productor de una cotización diaria.
- La [ICO explica su indicador compuesto diario I-CIP](https://www.ico.org/resources/public-market-information/) y señala qué extractos de datos requieren solicitud o acceso según la categoría de usuario.
- The Open Group organiza TOGAF 10 en contenido fundamental que incluye por separado [Core Concepts y ADM](https://help.opengroup.org/hc/en-us/articles/32726995273362-Understanding-the-TOGAF-Standard). Su ciclo incluye fases de visión, arquitectura de negocio/sistemas/tecnología, soluciones, migración, gobernanza y gestión del cambio, con gestión continua de requisitos.
- El [Blueprint de Render](https://render.com/docs/blueprint-spec) admite Cron Jobs con una expresión cron para ejecutar tareas programadas separadas del servidor web.
