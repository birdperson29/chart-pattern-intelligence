"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum


class PatternType(str, Enum):
    reversal = "reversal"
    continuation = "continuation"
    breakout = "breakout"
    momentum = "momentum"
    divergence = "divergence"
    all = "all"


class Signal(str, Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"


class ScanRequest(BaseModel):
    index: str = Field(default="nifty50", description="Index to scan: nifty50, nifty100, nifty200")
    pattern_type: Optional[PatternType] = Field(default=None, description="Filter by pattern type")
    signal: Optional[Signal] = Field(default=None, description="Filter by signal direction")
    min_confidence: int = Field(default=50, ge=0, le=100, description="Minimum confidence threshold")


class PatternResult(BaseModel):
    pattern: str
    type: str
    signal: str
    confidence: int
    symbol: str = ""
    current_price: float = 0.0
    explanation: str = ""
    extra: Dict[str, Any] = {}


class StockAnalysis(BaseModel):
    symbol: str
    current_price: float
    patterns: List[PatternResult]
    support_resistance: Dict[str, Any]
    indicators: Dict[str, Any]
    explanation: str = ""
    backtest: Optional[Dict[str, Any]] = None
    sentiment: Optional[Dict[str, Any]] = None


class BacktestRequest(BaseModel):
    symbol: str
    pattern: Optional[str] = None
    years: int = Field(default=5, ge=1, le=10)
    horizons: List[int] = Field(default=[5, 10, 20])


class BacktestResult(BaseModel):
    symbol: str
    pattern_filter: str
    total_detections: int
    patterns: Dict[str, Any]
    horizons: List[int]
    data_range: Dict[str, str]


class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    patterns: List[PatternResult] = []
    charts: List[str] = []


class ScanResult(BaseModel):
    index: str
    total_stocks_scanned: int
    stocks_with_patterns: int
    results: List[StockAnalysis]
    timestamp: str
