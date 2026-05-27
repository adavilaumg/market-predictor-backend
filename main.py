"""
main.py — API principal del proyecto "Clima & Mercados".

Endpoints:
  GET  /                          → Health check
  GET  /weather/current           → Clima actual de una ciudad
  GET  /weather/forecast          → Pronóstico 5 días
  GET  /market/eod                → Precios EOD de símbolos
  GET  /market/search             → Búsqueda de tickers
  GET  /market/intraday           → Precios intradía (plan de pago)
  POST /data/fetch-weather        → Guarda clima en MongoDB
  POST /data/fetch-market         → Guarda precios en MongoDB
  GET  /data/correlations         → Lista correlaciones guardadas
  POST /analysis                  → Análisis clima vs precios
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pymongo.database import Database
from bson import ObjectId
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
import bcrypt
import os

from database import (
    get_db,
    weather_collection,
    market_collection,
    correlation_collection,
    db
)
from schema import (
    WeatherResponse, MarketResponse, CorrelationResponse,
    FetchWeatherRequest, FetchMarketRequest, AnalysisRequest, AnalysisResponse,
    SymbolStats,
)
from services import (
    fetch_current_weather, fetch_weather_forecast,
    fetch_eod_prices, fetch_intraday_prices, search_tickers,
)

# ─── Helpers ─────────────────────────────────────────────────

def serialize(doc: dict) -> dict:
    """Convierte ObjectId de Mongo a string para la respuesta JSON."""
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# ─── App setup ───────────────────────────────────────────────

app = FastAPI(
    title="Clima & Mercados API",
    description="Analiza cómo la temperatura afecta los precios de mercado.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Ajusta en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ════════════════════════════════════════════════════════════

@app.get("/", tags=["General"])
def root():
    return {"status": "ok", "message": "Clima & Mercados API activa"}


# ════════════════════════════════════════════════════════════
#  WEATHER — Consulta directa a OpenWeatherMap
# ════════════════════════════════════════════════════════════

@app.get("/weather/current", tags=["Weather"])
async def get_current_weather(
    city:    str = Query(..., examples="Guatemala City"),
    country: str = Query("GT", examples="GT"),
):
    """Retorna el clima actual de una ciudad. No guarda en DB."""
    try:
        return await fetch_current_weather(city, country)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/weather/forecast", tags=["Weather"])
async def get_weather_forecast(
    city:    str = Query(..., examples="Guatemala City"),
    country: str = Query("GT", examples="GT"),
    days:    int = Query(5, ge=1, le=5),
):
    """Retorna el pronóstico por horas para los próximos N días (máx 5)."""
    try:
        data = await fetch_weather_forecast(city, country, days)
        return {"city": city, "country": country, "forecast": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ════════════════════════════════════════════════════════════
#  MARKET — Consulta directa a MarketStack
# ════════════════════════════════════════════════════════════

@app.get("/market/eod", tags=["Market"])
async def get_eod_prices(
    symbols: str = Query(..., examples="AAPL,AMZN"),
    limit:   int = Query(10, ge=1, le=100),
):
    """
    Retorna precios de cierre (EOD) para los símbolos indicados.
    Acepta múltiples símbolos separados por comas.
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    try:
        data = await fetch_eod_prices(symbol_list, limit)
        return {"symbols": symbol_list, "data": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/market/search", tags=["Market"])
async def search_market_tickers(
    query: str = Query(..., examples="corn"),
):
    """Busca tickers disponibles por nombre o símbolo."""
    try:
        return {"query": query, "results": await search_tickers(query)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/market/intraday", tags=["Market"])
async def get_intraday_prices(
    symbol:   str = Query(..., examples="AAPL"),
    interval: str = Query("1hour", examples="1hour"),
    limit:    int = Query(24, ge=1, le=100),
):
    """Retorna precios intradía. Requiere plan de pago en MarketStack."""
    try:
        data = await fetch_intraday_prices(symbol, interval, limit)
        return {"symbol": symbol, "interval": interval, "data": data}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ════════════════════════════════════════════════════════════
#  DATA — Guardar en MongoDB
# ════════════════════════════════════════════════════════════

@app.post("/data/fetch-weather", tags=["Data"])
async def save_weather(req: FetchWeatherRequest):
    """Consulta clima actual y lo guarda en la colección weather_records."""
    try:
        raw = await fetch_current_weather(req.city, req.country)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    raw["recorded_at"] = datetime.utcnow()
    result = weather_collection.insert_one(raw)
    raw["id"] = str(result.inserted_id)
    raw.pop("_id", None)
    return raw


@app.post("/data/fetch-market", tags=["Data"])
async def save_market_data(req: FetchMarketRequest):
    """Consulta precios EOD y los guarda en la colección market_records."""
    try:
        raw_list = await fetch_eod_prices(req.symbols, req.limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    for raw in raw_list:
        raw["recorded_at"] = datetime.utcnow()
        # Convertir datetime a string para que Mongo lo almacene bien
        if isinstance(raw.get("date"), datetime):
            raw["date"] = raw["date"].isoformat()

    result = market_collection.insert_many(raw_list)
    inserted_ids = [str(i) for i in result.inserted_ids]

    # Limpiar _id antes de retornar
    for doc in raw_list:
        doc.pop("_id", None)

    return {"inserted": len(inserted_ids), "ids": inserted_ids, "data": raw_list}


# ════════════════════════════════════════════════════════════
#  CORRELATIONS — Leer desde MongoDB
# ════════════════════════════════════════════════════════════

@app.get("/data/correlations", tags=["Data"])
def get_correlations(
    city:   Optional[str] = None,
    symbol: Optional[str] = None,
    limit:  int = Query(50, ge=1, le=500),
):
    """
    Lista las correlaciones clima-mercado guardadas.
    Filtra opcionalmente por ciudad o símbolo.
    """
    query: dict = {}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    if symbol:
        query["symbol"] = {"$regex": symbol, "$options": "i"}

    docs = list(
        correlation_collection.find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    return [serialize(doc) for doc in docs]


# ════════════════════════════════════════════════════════════
#  ANALYSIS — Análisis clima vs precios
# ════════════════════════════════════════════════════════════

@app.post("/analysis", tags=["Analysis"])
async def run_analysis(req: AnalysisRequest):
    """
    1. Obtiene clima actual de la ciudad.
    2. Obtiene precios EOD de los símbolos.
    3. Guarda registros y correlaciones en MongoDB.
    4. Retorna resumen estadístico.
    """
    # — Clima
    try:
        weather_raw = await fetch_current_weather(req.city)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error clima: {e}")

    weather_raw["recorded_at"] = datetime.utcnow()
    weather_result = weather_collection.insert_one(weather_raw.copy())
    weather_id = weather_result.inserted_id

    # — Mercado
    try:
        market_raw_list = await fetch_eod_prices(req.symbols, limit=30)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error mercado: {e}")

    for raw in market_raw_list:
        raw["recorded_at"] = datetime.utcnow()
        if isinstance(raw.get("date"), datetime):
            raw["date"] = raw["date"].isoformat()

    market_result = market_collection.insert_many([r.copy() for r in market_raw_list])
    market_ids = market_result.inserted_ids

    # — Correlaciones: una por cada registro de mercado
    correlations = []
    for i, raw in enumerate(market_raw_list):
        correlations.append({
            "weather_id":  str(weather_id),
            "market_id":   str(market_ids[i]),
            "city":        weather_raw["city"],
            "symbol":      raw["symbol"],
            "temperature": weather_raw["temperature"],
            "close_price": raw["close_price"],
            "created_at":  datetime.utcnow(),
        })
    if correlations:
        correlation_collection.insert_many(correlations)

    # — Estadísticas por símbolo
    symbol_stats = []
    for sym in req.symbols:
        prices = [r["close_price"] for r in market_raw_list if r["symbol"] == sym]
        if prices:
            symbol_stats.append({
                "symbol":      sym,
                "avg_price":   round(sum(prices) / len(prices), 4),
                "min_price":   round(min(prices), 4),
                "max_price":   round(max(prices), 4),
                "data_points": len(prices),
            })

    return {
        "city":            weather_raw["city"],
        "avg_temperature": weather_raw["temperature"],
        "weather_records": 1,
        "symbols":         symbol_stats,
        "message": (
            f"Análisis completado. Temperatura actual en {weather_raw['city']}: "
            f"{weather_raw['temperature']}°C. "
            f"Se guardaron {len(market_raw_list)} registros de mercado."
        ),
    }

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cambia_esto_en_produccion")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 24

def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/auth/register", response_model=AuthResponse, tags=["Auth"])
async def register(req: RegisterRequest):
    print("Entra al back")
    existing = db["users"].find_one({"username": req.username})
    if existing:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt())
    db["users"].insert_one({
        "username":   req.username,
        "email":      req.email,
        "password":   hashed.decode(),
        "created_at": datetime.utcnow()
    })
    return AuthResponse(access_token=create_token(req.username))


@app.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(req: LoginRequest):
    user = db["users"].find_one({"username": req.username})
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    if not bcrypt.checkpw(req.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    return AuthResponse(access_token=create_token(req.username))