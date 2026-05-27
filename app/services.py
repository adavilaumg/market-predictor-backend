"""
services.py — Capa de servicios para consumir APIs externas.

APIs integradas:
  • OpenWeatherMap: https://openweathermap.org/api
  • MarketStack:    https://marketstack.com
"""

import os
import httpx
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
MARKETSTACK_API_KEY = os.getenv("MARKETSTACK_API_KEY", "")

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
MARKETSTACK_BASE_URL = "http://api.marketstack.com/v1"          # plan gratuito = http


# ════════════════════════════════════════════════════════════
#  OPENWEATHERMAP
# ════════════════════════════════════════════════════════════

async def fetch_current_weather(city: str, country: str = "") -> dict:
    """
    Obtiene el clima actual para una ciudad.

    Args:
        city:    Nombre de la ciudad (ej. "Guatemala City")
        country: Código de país ISO 3166-1 alpha-2 (ej. "GT")

    Returns:
        Dict con temperatura, humedad, descripción, etc.

    Raises:
        httpx.HTTPStatusError: Si la API responde con error HTTP.
        ValueError: Si la respuesta no contiene los campos esperados.
    """
    q = f"{city},{country}" if country else city

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{OPENWEATHER_BASE_URL}/weather",
            params={
                "q":     q,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",   # temperatura en °C
                "lang":  "es",
            },
        )
        response.raise_for_status()
        data = response.json()

    return {
        "city":        data["name"],
        "country":     data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "feels_like":  data["main"]["feels_like"],
        "humidity":    data["main"]["humidity"],
        "description": data["weather"][0]["description"],
        "wind_speed":  data["wind"]["speed"],
    }


async def fetch_weather_forecast(city: str, country: str = "", days: int = 5) -> List[dict]:
    """
    Obtiene el pronóstico por horas para los próximos N días (máx 5).

    Returns:
        Lista de dicts con temperatura y descripción cada 3 horas.
    """
    q = f"{city},{country}" if country else city
    cnt = min(days * 8, 40)   # API devuelve datos cada 3h → 8 por día

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{OPENWEATHER_BASE_URL}/forecast",
            params={
                "q":     q,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang":  "es",
                "cnt":   cnt,
            },
        )
        response.raise_for_status()
        data = response.json()

    return [
        {
            "datetime":    item["dt_txt"],
            "temperature": item["main"]["temp"],
            "humidity":    item["main"]["humidity"],
            "description": item["weather"][0]["description"],
            "wind_speed":  item["wind"]["speed"],
        }
        for item in data["list"]
    ]


# ════════════════════════════════════════════════════════════
#  MARKETSTACK
# ════════════════════════════════════════════════════════════

async def fetch_eod_prices(symbols: List[str], limit: int = 10) -> List[dict]:
    """
    Obtiene los precios de cierre (End-of-Day) para uno o varios símbolos.

    Args:
        symbols: Lista de tickers (ej. ["AAPL", "AMZN", "CORN"])
        limit:   Número de registros por símbolo (máx 100 en plan gratuito)

    Returns:
        Lista de dicts con open, close, high, low, volume y date.
    """
    symbols_str = ",".join(symbols)

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{MARKETSTACK_BASE_URL}/eod",
            params={
                "access_key": MARKETSTACK_API_KEY,
                "symbols":    symbols_str,
                "limit":      limit,
            },
        )
        response.raise_for_status()
        data = response.json()

    if "error" in data:
        raise ValueError(f"MarketStack error: {data['error']['message']}")

    results = []
    for item in data.get("data", []):
        results.append({
            "symbol":      item["symbol"],
            "open_price":  item["open"],
            "close_price": item["close"],
            "high_price":  item["high"],
            "low_price":   item["low"],
            "volume":      item.get("volume", 0.0),
            "date":        datetime.fromisoformat(item["date"].replace("Z", "+00:00")),
        })

    return results


async def fetch_intraday_prices(symbol: str, interval: str = "1hour", limit: int = 24) -> List[dict]:
    """
    Obtiene precios intradía para un símbolo (requiere plan de pago en MarketStack).

    Args:
        symbol:   Ticker (ej. "AAPL")
        interval: Intervalo de tiempo: "1min" | "5min" | "10min" | "15min" | "30min" | "1hour" | "3hour"
        limit:    Número de puntos de datos

    Returns:
        Lista de dicts con precios por intervalo.

    Note:
        El plan gratuito de MarketStack NO incluye datos intradía.
        Esta función requiere plan Básico o superior.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{MARKETSTACK_BASE_URL}/intraday",
            params={
                "access_key": MARKETSTACK_API_KEY,
                "symbols":    symbol,
                "interval":   interval,
                "limit":      limit,
            },
        )
        response.raise_for_status()
        data = response.json()

    if "error" in data:
        raise ValueError(f"MarketStack error: {data['error']['message']}")

    return [
        {
            "symbol":   item["symbol"],
            "open":     item["open"],
            "close":    item["close"],
            "high":     item["high"],
            "low":      item["low"],
            "volume":   item.get("volume", 0.0),
            "datetime": item["date"],
        }
        for item in data.get("data", [])
    ]


async def search_tickers(query: str) -> List[dict]:
    """
    Busca tickers disponibles en MarketStack por nombre o símbolo.

    Args:
        query: Texto de búsqueda (ej. "Apple", "corn", "wheat")

    Returns:
        Lista de dicts con name, symbol, stock_exchange.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{MARKETSTACK_BASE_URL}/tickers",
            params={
                "access_key": MARKETSTACK_API_KEY,
                "search":     query,
                "limit":      10,
            },
        )
        response.raise_for_status()
        data = response.json()

    return [
        {
            "name":     item["name"],
            "symbol":   item["symbol"],
            "exchange": item.get("stock_exchange", {}).get("acronym", "N/A"),
        }
        for item in data.get("data", [])
    ]