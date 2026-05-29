"""
predict.py — Modelo de clasificación: ¿Sube o baja el precio según la temperatura?

Flujo:
  1. Obtiene datos frescos de MarketStack (precios EOD históricos)
  2. Obtiene temperatura actual de OpenWeatherMap
  3. Construye features y entrena un clasificador
  4. Predice si el precio subirá o bajará dado la temperatura actual
"""

import os
import httpx
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from typing import List
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY", "")

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
MARKETSTACK_BASE_URL = "http://api.marketstack.com/v1"


# ════════════════════════════════════════════════════════════
#  OBTENER DATOS FRESCOS
# ════════════════════════════════════════════════════════════

async def get_temperature(city: str) -> float:
    """Obtiene temperatura actual de una ciudad."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{OPENWEATHER_BASE_URL}/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"}
        )
        r.raise_for_status()
        return r.json()["main"]["temp"]


async def get_eod_data(symbol: str, limit: int = 50) -> pd.DataFrame:
    """
    Obtiene precios EOD históricos de un símbolo y construye features:
      - temperature_bucket: rango de temperatura simulado (ver nota abajo)
      - price_change: 1 si close > open (sube), 0 si baja
    
    Nota: MarketStack EOD no incluye temperatura histórica, así que usamos
    el cambio de precio (close vs open) como variable objetivo, y la 
    temperatura actual como feature de predicción.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            f"{MARKETSTACK_BASE_URL}/eod",
            params={"access_key": MARKETSTACK_API_KEY, "symbols": symbol, "limit": limit}
        )
        r.raise_for_status()
        data = r.json().get("data", [])

    if not data:
        raise ValueError(f"No hay datos EOD para {symbol}")

    df = pd.DataFrame(data)
    df = df[["open", "close", "high", "low", "volume"]].dropna()

    # ── Features ──────────────────────────────────────────
    df["price_range"]    = df["high"] - df["low"]           # rango del día
    df["open_close_pct"] = (df["close"] - df["open"]) / df["open"] * 100  # % cambio
    df["volume"]         = df["volume"].fillna(0)

    # ── Variable objetivo: 1 = sube (close > open), 0 = baja ──
    df["price_up"] = (df["close"] > df["open"]).astype(int)

    return df


# ════════════════════════════════════════════════════════════
#  ENTRENAR Y PREDECIR
# ════════════════════════════════════════════════════════════

async def train_and_predict(symbol: str, city: str) -> dict:
    """
    1. Obtiene datos frescos de MarketStack y temperatura de OpenWeatherMap
    2. Entrena un RandomForestClassifier
    3. Predice si el precio subirá o bajará con la temperatura actual

    Returns:
        dict con predicción, probabilidad, accuracy y resumen del modelo
    """

    # — Datos frescos
    df = await get_eod_data(symbol, limit=50)
    temperature = await get_temperature(city)

    if len(df) < 10:
        raise ValueError("No hay suficientes datos históricos para entrenar (mínimo 10).")

    # — Features y objetivo
    # Agregamos la temperatura actual como feature constante para el entrenamiento
    # (en un escenario real tendrías temperatura histórica por día)
    df["temperature"] = temperature

    feature_cols = ["temperature", "price_range", "open_close_pct", "volume"]
    X = df[feature_cols]
    y = df["price_up"]

    # — Entrenar modelo (mismo patrón que el ejercicio de clase)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    # — Evaluación
    y_pred   = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # — Predicción con temperatura actual
    sample = pd.DataFrame([{
        "temperature":    temperature,
        "price_range":    df["price_range"].mean(),
        "open_close_pct": df["open_close_pct"].mean(),
        "volume":         df["volume"].mean(),
    }])

    prediction    = clf.predict(sample)[0]
    probabilities = clf.predict_proba(sample)[0]

    label       = "SUBE 📈" if prediction == 1 else "BAJA 📉"
    probability = probabilities[prediction]

    # — Importancia de features
    importances = dict(zip(feature_cols, clf.feature_importances_.round(4)))

    return {
        "symbol":          symbol,
        "city":            city,
        "temperature":     temperature,
        "prediction":      label,
        "prediction_code": int(prediction),
        "probability":     round(float(probability), 4),
        "accuracy":        round(float(accuracy), 4),
        "training_samples": len(X_train),
        "feature_importance": importances,
        "message": (
            f"Con una temperatura de {temperature}°C en {city}, "
            f"el modelo predice que el precio de {symbol} {label} "
            f"con un {round(probability * 100, 1)}% de probabilidad. "
            f"Accuracy del modelo: {round(accuracy * 100, 1)}%."
        )
    }