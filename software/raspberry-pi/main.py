"""Servicio del comedor en la Raspberry Pi 4.

Uso:
    python main.py            arranca el servicio y se conecta al broker
    python main.py --check    verifica configuracion y calculo de racion
"""
import argparse
import logging
import sys

from src import config, feeding


def check() -> int:
    print(f"Comedero: {config.FEEDER_CODE}")
    print(f"Broker:   {config.MQTT_HOST}:{config.MQTT_PORT}")
    print(f"API:      {config.LOCAL_API or '(sin configurar)'}")
    print(f"Nube:     {config.CLOUD_API or '(sin sincronizacion)'}")
    print(f"Modelo:   {config.MODEL_PATH} {'OK' if config.MODEL_PATH.exists() else 'NO ENCONTRADO'}")
    print(f"Fotos:    {config.PET_PHOTOS_DIR} {'OK' if config.PET_PHOTOS_DIR.exists() else 'NO ENCONTRADO'}")
    print()
    for species, kg, profile in (("cat", 10, "adult_neutered"), ("dog", 31, "adult_neutered")):
        grams = feeding.daily_grams(species, kg, 3.6, profile)
        print(f"{species} {kg} kg -> {grams} g/dia ({round(grams/2,1)} g por comida)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="solo verifica y sale")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.check:
        return check()

    from src.service import FeedingService

    FeedingService().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
