"""
Market data fetcher using yfinance.
Handles NSE/BSE symbol formatting and caching.
"""

import pandas as pd
import yfinance as yf
from typing import Optional, List
from datetime import datetime, timedelta
from cachetools import TTLCache
import os
import json

from .nse_symbols import NIFTY_50, NIFTY_100, NIFTY_200


# In-memory cache: 15-minute TTL
_cache = TTLCache(maxsize=500, ttl=900)

# Disk cache directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _to_nse_symbol(symbol: str) -> str:
    """Ensure symbol has .NS suffix for NSE stocks."""
    symbol = symbol.upper().strip()
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        symbol += ".NS"
    return symbol


def fetch_stock_data(symbol: str, period: str = "2y",
                      interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data for a single stock.

    Args:
        symbol: Stock symbol (e.g., 'RELIANCE' or 'RELIANCE.NS')
        period: Data period ('1y', '2y', '5y', 'max')
        interval: Bar interval ('1d', '1wk', '1mo')

    Returns:
        DataFrame with Open, High, Low, Close, Volume columns, or None on error.
    """
    symbol = _to_nse_symbol(symbol)
    cache_key = f"{symbol}_{period}_{interval}"

    if cache_key in _cache:
        return _cache[cache_key]

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            print(f"[WARN] No data returned for {symbol}")
            return None

        # Standardize column names
        df = df.rename(columns={
            "Stock Splits": "Stock_Splits",
            "Capital Gains": "Capital_Gains",
        })

        # Keep only OHLCV
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in df.columns:
                print(f"[WARN] Missing column {col} for {symbol}")
                return None

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = df.dropna()

        if len(df) < 30:
            print(f"[WARN] Insufficient data for {symbol}: {len(df)} bars")
            return None

        _cache[cache_key] = df
        return df

    except Exception as e:
        print(f"[ERROR] Failed to fetch {symbol}: {e}")
        return None


def fetch_multiple(symbols: List[str], period: str = "2y",
                    interval: str = "1d") -> dict:
    """
    Fetch data for multiple symbols. Returns dict of symbol -> DataFrame.
    """
    results = {}
    for sym in symbols:
        df = fetch_stock_data(sym, period=period, interval=interval)
        if df is not None:
            results[_to_nse_symbol(sym)] = df
    return results


def get_index_symbols(index: str = "nifty50") -> List[str]:
    """Get list of symbols for a market index."""
    index = index.lower().replace(" ", "").replace("-", "").replace("_", "")
    if index in ("nifty50", "nifty"):
        return NIFTY_50
    elif index in ("nifty100", "niftynext50"):
        return NIFTY_100
    elif index in ("nifty200",):
        return NIFTY_200
    else:
        return NIFTY_50


def get_stock_info(symbol: str) -> Optional[dict]:
    """Get basic stock info (name, sector, market cap, etc.)."""
    symbol = _to_nse_symbol(symbol)
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception as e:
        print(f"[ERROR] Failed to get info for {symbol}: {e}")
        return None
