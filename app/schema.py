from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# ─── Weather Schemas ────────────────────────────────────────

class WeatherBase(BaseModel):
    city:        str
    country:     str
    temperature: float
    feels_like:  float
    humidity:    int
    description: str
    wind_speed:  float

class WeatherResponse(WeatherBase):
    id:          int
    recorded_at: datetime

    class Config:
        from_attributes = True


# ─── Market Schemas ─────────────────────────────────────────

class MarketBase(BaseModel):
    symbol:      str
    open_price:  float
    close_price: float
    high_price:  float
    low_price:   float
    volume:      float
    date:        datetime

class MarketResponse(MarketBase):
    id:          int
    recorded_at: datetime

    class Config:
        from_attributes = True


# ─── Correlation Schemas ─────────────────────────────────────

class CorrelationResponse(BaseModel):
    id:          int
    city:        str
    symbol:      str
    temperature: float
    close_price: float
    created_at:  datetime

    class Config:
        from_attributes = True


# ─── Request Schemas ─────────────────────────────────────────

class FetchWeatherRequest(BaseModel):
    city:    str = Field(..., example="Guatemala City")
    country: str = Field(..., example="GT")

class FetchMarketRequest(BaseModel):
    symbols: List[str] = Field(..., example=["AAPL", "AMZN"])
    limit:   int       = Field(10, ge=1, le=100)

class AnalysisRequest(BaseModel):
    city:    str       = Field(..., example="Guatemala City")
    symbols: List[str] = Field(..., example=["AAPL", "AMZN"])


# ─── Analysis Response ───────────────────────────────────────

class SymbolStats(BaseModel):
    symbol:        str
    avg_price:     float
    min_price:     float
    max_price:     float
    data_points:   int

class AnalysisResponse(BaseModel):
    city:            str
    avg_temperature: float
    weather_records: int
    symbols:         List[SymbolStats]
    message:         str