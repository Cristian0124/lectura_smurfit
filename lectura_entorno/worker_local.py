"""Ejecuta el radar local cada diez minutos sin bloquear las rutas web."""
import logging
import os
import time

def ejecutar_ciclo_local():
    from worker import app, ejecutar_escaneo
    with app.app_context():
        return ejecutar_escaneo()


def iniciar_bucle_local():
    intervalo = max(600, int(os.environ.get("RADAR_FRECUENCIA_LOCAL_SEGUNDOS", "600")))
    # Permite que la aplicación web inicialice primero la base SQLite local.
    time.sleep(5)
    while True:
        try:
            resultado = ejecutar_ciclo_local()
            logging.info("Revisión local terminada: %s", resultado)
        except Exception as error:
            logging.exception("Falló la revisión local del Radar (%s)", type(error).__name__)
        time.sleep(intervalo)


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    iniciar_bucle_local()
