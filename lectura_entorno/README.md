# Lectura de entorno – Smurfit Westrock (adelanto / MVP) – Grupo 1

Python + Flask + SQLite.

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
y definir la variable de entorno SECRET_KEY.
