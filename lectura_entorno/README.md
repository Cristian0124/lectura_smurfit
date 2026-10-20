# Lectura de entorno – Smurfit Westrock (adelanto / MVP) – Grupo 1

Python + Flask + SQLite.

Este avance incluye el apartado **Metodología PESTEL** (`/pestel`): permite explorar las seis dimensiones, consultar preguntas guía y ver cuántas señales se han registrado en cada una. El contexto incluido es una guía inicial de investigación, no un conjunto de hallazgos confirmados. La captura de información sigue siendo manual; todavía no hay conexión a APIs.

En la edición de una señal, administradores y analistas pueden agregar comentarios de seguimiento. Cada comentario conserva su autor y fecha, y se guarda separado de los datos de la señal.

    pip install -r requirements.txt
    python app.py          # http://127.0.0.1:5000

Usuarios de prueba: admin/admin123, analista/analista123, directivo/decisor123 (cambiarlos).

## Requisitos del Grupo 1 y dónde se cubren
1. Información (tipo, cantidad): señales con factor, ámbito, tipo, riesgo y vigencia; el panel muestra el total por factor.
2. Funciones: registrar, actualizar, calcular (riesgo = impacto x probabilidad) y leer.
3. Para quién: directivos y analistas de Smurfit Westrock que toman decisiones sobre el entorno.
4. Tipo de entorno: factores PESTEL + ámbito (país, sector, competencia, proveedores, clientes).
5. Fuentes: catálogo de fuentes con tipo y confiabilidad, elegibles al registrar.
6. Seguridad: claves con hash, sesión con cookie HttpOnly/SameSite, CSRF, permisos por rol, validación de datos.
7. Dispositivos: web responsive (computador y celular).
8. Acceso / roles: admin, analista y decisor (solo ve lo publicado).
Del tablero también: nivel de riesgo y horizonte de tiempo (Grupo 2), tipo de salida tablas/alertas/informes
(Grupo 5: panel, alertas de riesgo alto o vencidas, informe imprimible y CSV) y vigencia (Grupo 6).

## PythonAnywhere
Subir la carpeta y crear una web app Flask (manual config). En el archivo WSGI de PythonAnywhere, configurar
`DB` antes de importar la aplicación, usando una ruta persistente dentro de la cuenta:

```python
import os
os.environ["DB"] = "/home/tu_usuario/lectura_entorno/entorno.db"

from app import app as application
```

Crear previamente esa carpeta desde la pestaña **Files**. La variable `SECRET_KEY` también debe definirse
en la configuración de la web app y mantenerse secreta. En local, si `DB` no está definida, la aplicación
continúa usando `entorno.db` junto a `app.py`. La base de datos de PythonAnywhere es independiente de la local:
no se copian automáticamente los registros existentes y el archivo SQLite no se sincroniza con GitHub al
actualizar el código. Para mover registros, exportarlos desde la app local e importarlos en el servidor.
