"""
Support and Resistance level detection using multiple methods:
- Swing highs/lows clustering
- Volume profile
- Fibonacci retracement
- Pivot points
"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from typing import List, Dict, Tuple

from .indicators import fibonacci_levels, pivot_points


def find_swing_points(df: pd.DataFrame, order: int = 5) -> Tuple[pd.Series, pd.Series]:
    """
    Find local minima (swing lows) and maxima (swing highs).
    `order` controls how many bars on each side to compare.
    """
    high = df["High"].values
    low = df["Low"].values

    swing_high_idx = argrelextrema(high, np.greater_equal, order=order)[0]
    swing_low_idx = argrelextrema(low, np.less_equal, order=order)[0]

    swing_highs = pd.Series(np.nan, index=df.index)
    swing_lows = pd.Series(np.nan, index=df.index)

    swing_highs.iloc[swing_high_idx] = df["High"].iloc[swing_high_idx]
    swing_lows.iloc[swing_low_idx] = df["Low"].iloc[swing_low_idx]

    return swing_highs, swing_lows


def cluster_levels(prices: np.ndarray, tolerance_pct: float = 1.5) -> List[Dict]:
    """
    Cluster nearby price levels together. Returns list of
    {level, strength, touches} sorted by strength.
    """
    if len(prices) == 0:
        return []

    prices = np.sort(prices)
    clusters = []
    used = set()

    for i, p in enumerate(prices):
        if i in used:
            continue
        cluster = [p]
        used.add(i)
        for j in range(i + 1, len(prices)):
            if j in used:
                continue
            if abs(prices[j] - p) / p * 100 <= tolerance_pct:
                cluster.append(prices[j])
                used.add(j)
        clusters.append({
            "level": float(np.mean(cluster)),
            "strength": len(cluster),
            "touches": len(cluster),
        })

    return sorted(clusters, key=lambda x: x["strength"], reverse=True)


def detect_support_resistance(df: pd.DataFrame, order: int = 5,
                               tolerance_pct: float = 1.5,
                               min_touches: int = 2) -> Dict:
    """
    Detect support and resistance levels using swing point clustering.
    Returns dict with 'support' and 'resistance' lists.
    """
    swing_highs, swing_lows = find_swing_points(df, order=order)

    high_prices = swing_highs.dropna().values
    low_prices = swing_lows.dropna().values

    current_price = df["Close"].iloc[-1]

    resistance_clusters = cluster_levels(high_prices, tolerance_pct)
    support_clusters = cluster_levels(low_prices, tolerance_pct)

    resistance = [
        c for c in resistance_clusters
        if c["level"] > current_price and c["touches"] >= min_touches
    ]
    support = [
        c for c in support_clusters
        if c["level"] < current_price and c["touches"] >= min_touches
    ]

    return {
        "support": support[:5],
        "resistance": resistance[:5],
        "current_price": float(current_price),
    }


def get_fibonacci_sr(df: pd.DataFrame, lookback: int = 120) -> Dict:
    """Calculate Fibonacci retracement levels from recent swing high/low."""
    recent = df.tail(lookback)
    high_price = recent["High"].max()
    low_price = recent["Low"].min()
    levels = fibonacci_levels(high_price, low_price)

    current_price = df["Close"].iloc[-1]
    support = {k: v for k, v in levels.items() if v < current_price}
    resistance = {k: v for k, v in levels.items() if v > current_price}

    return {
        "fibonacci_support": support,
        "fibonacci_resistance": resistance,
        "swing_high": float(high_price),
        "swing_low": float(low_price),
    }


def get_pivot_sr(df: pd.DataFrame) -> Dict:
    """Calculate pivot point support/resistance from last completed period."""
    last = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    pp = pivot_points(float(last["High"]), float(last["Low"]), float(last["Close"]))
    current_price = df["Close"].iloc[-1]

    support = {k: v for k, v in pp.items() if v < current_price}
    resistance = {k: v for k, v in pp.items() if v >= current_price}

    return {
        "pivot_support": support,
        "pivot_resistance": resistance,
    }


def is_near_level(price: float, level: float, tolerance_pct: float = 1.0) -> bool:
    """Check if price is within tolerance of a support/resistance level."""
    return abs(price - level) / level * 100 <= tolerance_pct


def detect_breakout_from_sr(df: pd.DataFrame, sr_levels: Dict,
                             volume_factor: float = 1.5) -> List[Dict]:
    """
    Detect if recent price action has broken through a S/R level
    with above-average volume.
    """
    breakouts = []
    current = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None
    avg_vol = df["Volume"].tail(20).mean()

    # Check resistance breakouts
    for r in sr_levels.get("resistance", []):
        level = r["level"]
        if (prev is not None and prev["Close"] < level and
                current["Close"] > level and
                current["Volume"] > avg_vol * volume_factor):
            breakouts.append({
                "type": "resistance_breakout",
                "level": level,
                "close": float(current["Close"]),
                "volume_ratio": float(current["Volume"] / avg_vol),
                "strength": r["strength"],
                "signal": "bullish",
            })

    # Check support breakdowns
    for s in sr_levels.get("support", []):
        level = s["level"]
        if (prev is not None and prev["Close"] > level and
                current["Close"] < level and
                current["Volume"] > avg_vol * volume_factor):
            breakouts.append({
                "type": "support_breakdown",
                "level": level,
                "close": float(current["Close"]),
                "volume_ratio": float(current["Volume"] / avg_vol),
                "strength": s["strength"],
                "signal": "bearish",
            })

    return breakouts
