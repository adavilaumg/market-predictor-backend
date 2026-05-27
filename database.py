from pymongo import MongoClient
import certifi
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

client = MongoClient(
    os.getenv("MONGODB_URI"),
    tlsCAFile=certifi.where()
)

db = client["clima_mercados_db"]

# ─── Colecciones ─────────────────────────────────────────────
weather_collection     = db["weather_records"]
market_collection      = db["market_records"]
correlation_collection = db["correlation_records"]


def get_db():
    """
    Retorna el objeto db de MongoDB.
    Se usa como dependencia en FastAPI igual que antes.
    """
    return db