import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


MQTT_HOST = env("MQTT_HOST", "localhost")
MQTT_PORT = int(env("MQTT_PORT", "1883"))
FEEDER_CODE = env("FEEDER_CODE", "SPB-42")

LOCAL_API = env("LOCAL_API", "http://127.0.0.1:8000/api/v1/ingest/")
INGEST_TOKEN = env("INGEST_TOKEN", "")
CLOUD_API = env("CLOUD_API")
CLOUD_TOKEN = env("CLOUD_TOKEN")

MODEL_PATH = BASE_DIR / env("MODEL_PATH", "models/mobilenetv3.onnx")
PET_PHOTOS_DIR = BASE_DIR / env("PET_PHOTOS_DIR", "photos")
CONFIDENCE_THRESHOLD = float(env("CONFIDENCE_THRESHOLD", "0.62"))
STREAM_URL = env("STREAM_URL", "")

TOPIC_EVENT = f"comedero/{FEEDER_CODE}/evento"
TOPIC_COMMAND = f"comedero/{FEEDER_CODE}/comando"
TOPIC_STATE = f"comedero/{FEEDER_CODE}/estado"
