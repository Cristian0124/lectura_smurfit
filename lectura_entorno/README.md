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
Subir la carpeta, crear web app Flask (manual config), WSGI: `from app import app as application`,
y definir la variable de entorno SECRET_KEY. Para una base de datos persistente, configurar `DB` en `app.py`
con una ruta dentro del espacio de archivos de la cuenta de PythonAnywhere; el archivo SQLite no se sincroniza
con GitHub cuando se actualiza el código.
