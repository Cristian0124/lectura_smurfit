# Publicar la aplicacion y guardar sus datos en PythonAnywhere

La aplicacion usa SQLite. En el servidor, el archivo quedara en:

```text
/home/cris0124/.local/share/lectura_entorno/entorno.db
```

Ese archivo vive en tu espacio de PythonAnywhere, separado de la carpeta del codigo. La app crea la carpeta, el archivo y las tablas al arrancar si todavia no existen. Los registros nuevos se guardaran alli.

## 1. Subir el codigo

En **Files**, usa la carpeta que ya creaste en tu espacio personal:

```text
/home/cris0124/LECTURA_ENTORNO
```

En tu cuenta ya creaste la carpeta `LECTURA_ENTORNO`; respeta esas mayusculas en las rutas. Sube `app.py`, `bd.py`, `requirements.txt` y la carpeta `templates`. No subas `.runtime` ni `__pycache__`.

## 2. Crear la web app y Flask

En **Web**, pulsa **Add a new web app**, elige tu dominio PythonAnywhere, selecciona **Manual configuration** y una version de Python. La guia oficial actual usa Python 3.13 como ejemplo; elige una version disponible y usa esa misma para el entorno virtual.

Abre **Consoles** y crea el entorno virtual. Cambia `3.13` si elegiste otra version de Python en **Web**:

```bash
mkvirtualenv --python=/usr/bin/python3.13 lectura_entorno_venv
workon lectura_entorno_venv
pip install -r /home/cris0124/LECTURA_ENTORNO/requirements.txt
```

En la pestaña **Web**, escribe `lectura_entorno_venv` en el campo **Virtualenv** y guarda el cambio.

## 3. Conectar WSGI con la app y la base de datos

En **Web**, abre el archivo WSGI desde el enlace que aparece en la seccion **Code**. Reemplaza su contenido por el de `pythonanywhere_wsgi.py.example`. La ruta `/home/cris0124/LECTURA_ENTORNO` ya coincide con tu cuenta.

Reemplaza `REEMPLAZA_POR_UNA_CLAVE_ALEATORIA_LARGA` por una clave secreta. Generala en Bash con:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Copiala al archivo WSGI y guardala para mantenerla estable. No la subas a GitHub.

El ejemplo establece `DB` antes de importar `app`, que es importante porque `bd.py` lee esa variable al cargarse. Al importar la app, `bd.py` crea `~/.local/share/lectura_entorno/entorno.db` y las tablas automaticamente.

## 4. Recargar y comprobar que la base remota funciona

Pulsa **Reload** en **Web** y abre tu dominio. Debe aparecer el inicio de sesion. La primera vez la base remota se crea vacia y la app agrega estos usuarios iniciales:

- `admin` / `admin123`
- `analista` / `analista123`
- `directivo` / `decisor123`

Inicia sesion, registra una señal, recarga la pagina y confirma que la señal sigue ahi. El archivo `~/.local/share/lectura_entorno/entorno.db` contiene los datos de la app en PythonAnywhere.

Si la web no inicia, mira **Web → Log files → Error log**. `No module named flask` suele indicar que no se asigno el entorno virtual o que Flask se instalo en otro entorno. Un error de importacion de `app` suele indicar que `PROJECT_DIR` no coincide con la carpeta donde subiste el codigo.

## Datos que ya tienes en tu computador

La base local `lectura_entorno/entorno.db` no se copia al publicar. Si quieres llevar esos registros, sube ese archivo a PythonAnywhere y copialo a `~/.local/share/lectura_entorno/entorno.db` antes de usar la web app. Hazlo con la app detenida y conserva una copia del archivo. Si no necesitas esos datos, deja que PythonAnywhere cree su propia base nueva.

SQLite esta disponible en PythonAnywhere y sirve para esta app. PythonAnywhere advierte que el almacenamiento en archivos puede ser mas lento y no lo recomienda para sitios de produccion con mucha carga; si el uso crece, habria que migrar a una base de datos servidor. [Tipos de bases de datos en PythonAnywhere](https://help.pythonanywhere.com/pages/KindsOfDatabases/).
