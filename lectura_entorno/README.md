# Radar de entorno

Aplicación web Flask para registrar y analizar señales del entorno mediante PESTEL. Incluye gestión de fuentes, señales, comentarios, filtros, informes, exportación a Excel y análisis estructurado de páginas con Firecrawl.

## Ejecución local

En Windows, ejecuta `iniciar.bat`. También puedes instalar dependencias y arrancar manualmente:

```sh
pip install -r requirements.txt
python app.py
```

La aplicación usa `entorno.db` (SQLite) por defecto. `DB` permite cambiar su ubicación. En una base nueva se crean los usuarios demo `admin/admin123`, `analista/analista123` y `directivo/decisor123`; cambia esas claves antes de exponer el servicio públicamente.

## Variables de entorno

- `DATABASE_URL`: si está definida, selecciona PostgreSQL (Neon). Si no, se usa SQLite.
- `DB`: ruta opcional del archivo SQLite local.
- `SECRET_KEY`: clave de sesión de Flask. Obligatoria cuando se configura `DATABASE_URL`.
- `FIRECRAWL_API_KEY`: clave del servicio Firecrawl. Se requiere para analizar páginas web.
- `INITIAL_ADMIN_USER` y `INITIAL_ADMIN_PASSWORD`: usuario de arranque de Neon. Se usan solo si la tabla de usuarios está vacía; la contraseña debe tener al menos 12 caracteres.

No publiques estas claves ni las incluyas en Git. La extracción estructurada usa el endpoint REST v2 y consume créditos de Firecrawl. Cuando el proveedor devuelve un error, la aplicación muestra un aviso y no finge haber guardado resultados.

## Despliegue en Render + Neon

El archivo `render.yaml` prepara el servicio con raíz `lectura_entorno`, instalación desde `requirements.txt` e inicio mediante Gunicorn. En Render, crea el servicio desde el repositorio y configura:

- **Root Directory:** `lectura_entorno`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn --bind 0.0.0.0:${PORT:-10000} app:app`

Crea una base PostgreSQL en Neon y copia su cadena de conexión completa en `DATABASE_URL` dentro de **Environment** en Render. Usa la cadena con SSL que proporciona Neon y no la escribas en archivos versionados. Define `FIRECRAWL_API_KEY`, `INITIAL_ADMIN_USER` y `INITIAL_ADMIN_PASSWORD`; `SECRET_KEY` se genera desde el archivo Blueprint. Guarda y despliega de nuevo. El usuario y la contraseña iniciales solo se utilizan para crear el primer administrador en una base vacía; Neon no recibe las cuentas demo locales.

En el primer arranque, la aplicación crea las tablas y añade columnas faltantes sin borrar registros. SQLite local y Neon son bases independientes: no se copian datos entre ellas automáticamente. Para migrar información existente, primero hay que planear y validar una migración explícita.

En local se conservan las cuentas demo. En Neon se crea solo el administrador configurado en las variables iniciales, evitando publicar las credenciales demo conocidas.

La conexión real a Neon y Firecrawl solo se puede confirmar después de configurar sus credenciales en Render y probar desde el servicio desplegado.
