"""
Chart Pattern Detection Engine
Detects: Head & Shoulders, Double Top/Bottom, Triangles, Wedges, Flags,
         Breakouts, Golden/Death Cross, BB Squeeze, and more.
"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from typing import List, Dict, Optional

from .indicators import (
    sma, ema, rsi, macd, bollinger_bands, atr, obv,
    squeeze_indicator, adx, stochastic
)
from .support_resistance import (
    find_swing_points, detect_support_resistance,
    detect_breakout_from_sr
)
from .divergence import detect_all_divergences


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _swing_highs_lows(df: pd.DataFrame, order: int = 5):
    """Return arrays of swing-high and swing-low (index, price) tuples."""
    highs = argrelextrema(df["High"].values, np.greater_equal, order=order)[0]
    lows = argrelextrema(df["Low"].values, np.less_equal, order=order)[0]
    sh = [(int(i), float(df["High"].iloc[i])) for i in highs]
    sl = [(int(i), float(df["Low"].iloc[i])) for i in lows]
    return sh, sl


def _pct_diff(a: float, b: float) -> float:
    """Percentage difference between two values."""
    if b == 0:
        return 0.0
    return abs(a - b) / b * 100


# ---------------------------------------------------------------------------
# Individual Pattern Detectors
# ---------------------------------------------------------------------------

def detect_head_and_shoulders(df: pd.DataFrame, order: int = 5,
                               tolerance_pct: float = 2.0) -> List[Dict]:
    """
    Detect Head & Shoulders (bearish) and Inverse H&S (bullish).
    Requires 3 swing highs where middle > both sides (H&S)
    or 3 swing lows where middle < both sides (IH&S).
    """
    patterns = []
    sh, sl = _swing_highs_lows(df, order=order)

    # Head & Shoulders (bearish)
    if len(sh) >= 3:
        for i in range(len(sh) - 2):
            left_i, left_p = sh[i]
            head_i, head_p = sh[i + 1]
            right_i, right_p = sh[i + 2]

            if (head_p > left_p and head_p > right_p and
                    _pct_diff(left_p, right_p) < tolerance_pct * 2):
                # Check if this is a recent pattern (within last 30% of data)
                if right_i > len(df) * 0.7:
                    # Find neckline from lows between the shoulders
                    mid_lows = [s for s in sl if left_i < s[0] < right_i]
                    if mid_lows:
                        neckline = np.mean([l[1] for l in mid_lows])
                        current_price = df["Close"].iloc[-1]
                        patterns.append({
                            "pattern": "head_and_shoulders",
                            "type": "reversal",
                            "signal": "bearish",
                            "confidence": min(90, 60 + int(_pct_diff(head_p, left_p))),
                            "left_shoulder": {"index": left_i, "price": left_p},
                            "head": {"index": head_i, "price": head_p},
                            "right_shoulder": {"index": right_i, "price": right_p},
                            "neckline": float(neckline),
                            "target": float(neckline - (head_p - neckline)),
                            "current_price": float(current_price),
                            "start_date": str(df.index[left_i]),
                            "end_date": str(df.index[right_i]),
                        })

    # Inverse Head & Shoulders (bullish)
    if len(sl) >= 3:
        for i in range(len(sl) - 2):
            left_i, left_p = sl[i]
            head_i, head_p = sl[i + 1]
            right_i, right_p = sl[i + 2]

            if (head_p < left_p and head_p < right_p and
                    _pct_diff(left_p, right_p) < tolerance_pct * 2):
                if right_i > len(df) * 0.7:
                    mid_highs = [s for s in sh if left_i < s[0] < right_i]
                    if mid_highs:
                        neckline = np.mean([h[1] for h in mid_highs])
                        current_price = df["Close"].iloc[-1]
                        patterns.append({
                            "pattern": "inverse_head_and_shoulders",
                            "type": "reversal",
                            "signal": "bullish",
                            "confidence": min(90, 60 + int(_pct_diff(head_p, left_p))),
                            "left_shoulder": {"index": left_i, "price": left_p},
                            "head": {"index": head_i, "price": head_p},
                            "right_shoulder": {"index": right_i, "price": right_p},
                            "neckline": float(neckline),
                            "target": float(neckline + (neckline - head_p)),
                            "current_price": float(current_price),
                            "start_date": str(df.index[left_i]),
                            "end_date": str(df.index[right_i]),
                        })

    return patterns


def detect_double_top_bottom(df: pd.DataFrame, order: int = 5,
                              tolerance_pct: float = 2.0) -> List[Dict]:
    """
    Detect Double Top (bearish) and Double Bottom (bullish).
    Two swing highs/lows at approximately the same level.
    """
    patterns = []
    sh, sl = _swing_highs_lows(df, order=order)

    # Double Top
    if len(sh) >= 2:
        for i in range(len(sh) - 1):
            idx1, p1 = sh[i]
            idx2, p2 = sh[i + 1]
            if (_pct_diff(p1, p2) < tolerance_pct and
                    idx2 > len(df) * 0.6 and
                    (idx2 - idx1) > 10):
                mid_low = df["Low"].iloc[idx1:idx2].min()
                current_price = df["Close"].iloc[-1]
                patterns.append({
                    "pattern": "double_top",
                    "type": "reversal",
                    "signal": "bearish",
                    "confidence": max(50, 80 - int(_pct_diff(p1, p2) * 10)),
                    "peak_1": {"index": idx1, "price": p1, "date": str(df.index[idx1])},
                    "peak_2": {"index": idx2, "price": p2, "date": str(df.index[idx2])},
                    "neckline": float(mid_low),
                    "target": float(mid_low - (max(p1, p2) - mid_low)),
                    "current_price": float(current_price),
                })

    # Double Bottom
    if len(sl) >= 2:
        for i in range(len(sl) - 1):
            idx1, p1 = sl[i]
            idx2, p2 = sl[i + 1]
            if (_pct_diff(p1, p2) < tolerance_pct and
                    idx2 > len(df) * 0.6 and
                    (idx2 - idx1) > 10):
                mid_high = df["High"].iloc[idx1:idx2].max()
                current_price = df["Close"].iloc[-1]
                patterns.append({
                    "pattern": "double_bottom",
                    "type": "reversal",
                    "signal": "bullish",
                    "confidence": max(50, 80 - int(_pct_diff(p1, p2) * 10)),
                    "trough_1": {"index": idx1, "price": p1, "date": str(df.index[idx1])},
                    "trough_2": {"index": idx2, "price": p2, "date": str(df.index[idx2])},
                    "neckline": float(mid_high),
                    "target": float(mid_high + (mid_high - min(p1, p2))),
                    "current_price": float(current_price),
                })

    return patterns


def detect_triangles(df: pd.DataFrame, order: int = 5,
                      lookback: int = 60) -> List[Dict]:
    """
    Detect ascending, descending, and symmetrical triangles
    by fitting trendlines to swing highs and lows.
    """
    patterns = []
    recent = df.tail(lookback)
    sh, sl = _swing_highs_lows(recent, order=order)

    if len(sh) < 2 or len(sl) < 2:
        return patterns

    # Fit linear regression to swing highs and lows
    high_x = np.array([s[0] for s in sh[-4:]])
    high_y = np.array([s[1] for s in sh[-4:]])
    low_x = np.array([s[0] for s in sl[-4:]])
    low_y = np.array([s[1] for s in sl[-4:]])

    if len(high_x) < 2 or len(low_x) < 2:
        return patterns

    high_slope = np.polyfit(high_x, high_y, 1)[0]
    low_slope = np.polyfit(low_x, low_y, 1)[0]

    current_price = float(df["Close"].iloc[-1])
    avg_price = float(df["Close"].tail(lookback).mean())

    # Classify triangle type
    high_flat = abs(high_slope / avg_price * 100) < 0.05
    low_flat = abs(low_slope / avg_price * 100) < 0.05
    converging = high_slope < 0 and low_slope > 0

    if low_slope > 0 and high_flat:
        patterns.append({
            "pattern": "ascending_triangle",
            "type": "continuation",
            "signal": "bullish",
            "confidence": 70,
            "high_slope": float(high_slope),
            "low_slope": float(low_slope),
            "resistance": float(np.mean(high_y)),
            "current_price": current_price,
        })
    elif high_slope < 0 and low_flat:
        patterns.append({
            "pattern": "descending_triangle",
            "type": "continuation",
            "signal": "bearish",
            "confidence": 70,
            "high_slope": float(high_slope),
            "low_slope": float(low_slope),
            "support": float(np.mean(low_y)),
            "current_price": current_price,
        })
    elif converging:
        patterns.append({
            "pattern": "symmetrical_triangle",
            "type": "continuation",
            "signal": "neutral",
            "confidence": 60,
            "high_slope": float(high_slope),
            "low_slope": float(low_slope),
            "current_price": current_price,
        })

    return patterns


def detect_wedges(df: pd.DataFrame, order: int = 5,
                   lookback: int = 60) -> List[Dict]:
    """Detect rising and falling wedges."""
    patterns = []
    recent = df.tail(lookback)
    sh, sl = _swing_highs_lows(recent, order=order)

    if len(sh) < 2 or len(sl) < 2:
        return patterns

    high_x = np.array([s[0] for s in sh[-4:]])
    high_y = np.array([s[1] for s in sh[-4:]])
    low_x = np.array([s[0] for s in sl[-4:]])
    low_y = np.array([s[1] for s in sl[-4:]])

    if len(high_x) < 2 or len(low_x) < 2:
        return patterns

    high_slope = np.polyfit(high_x, high_y, 1)[0]
    low_slope = np.polyfit(low_x, low_y, 1)[0]

    current_price = float(df["Close"].iloc[-1])

    # Rising wedge: both slopes positive but converging (bearish)
    if high_slope > 0 and low_slope > 0 and low_slope > high_slope:
        patterns.append({
            "pattern": "rising_wedge",
            "type": "reversal",
            "signal": "bearish",
            "confidence": 65,
            "high_slope": float(high_slope),
            "low_slope": float(low_slope),
            "current_price": current_price,
        })

    # Falling wedge: both slopes negative but converging (bullish)
    if high_slope < 0 and low_slope < 0 and high_slope > low_slope:
        patterns.append({
            "pattern": "falling_wedge",
            "type": "reversal",
            "signal": "bullish",
            "confidence": 65,
            "high_slope": float(high_slope),
            "low_slope": float(low_slope),
            "current_price": current_price,
        })

    return patterns


def detect_flags(df: pd.DataFrame, lookback: int = 30,
                  trend_lookback: int = 60) -> List[Dict]:
    """
    Detect bull and bear flags — a strong move (pole) followed by a
    short consolidation (flag) in the opposite direction.
    """
    patterns = []
    if len(df) < trend_lookback + lookback:
        return patterns

    pole = df.iloc[-(trend_lookback + lookback):-lookback]
    flag = df.tail(lookback)

    pole_return = (pole["Close"].iloc[-1] - pole["Close"].iloc[0]) / pole["Close"].iloc[0]
    flag_return = (flag["Close"].iloc[-1] - flag["Close"].iloc[0]) / flag["Close"].iloc[0]

    flag_range = (flag["High"].max() - flag["Low"].min()) / flag["Close"].mean()
    current_price = float(df["Close"].iloc[-1])

    # Bull flag: strong up move + slight downward consolidation
    if pole_return > 0.08 and -0.05 < flag_return < 0.02 and flag_range < 0.08:
        patterns.append({
            "pattern": "bull_flag",
            "type": "continuation",
            "signal": "bullish",
            "confidence": 65,
            "pole_return_pct": float(pole_return * 100),
            "flag_return_pct": float(flag_return * 100),
            "target": float(current_price * (1 + pole_return)),
            "current_price": current_price,
        })

    # Bear flag: strong down move + slight upward consolidation
    if pole_return < -0.08 and -0.02 < flag_return < 0.05 and flag_range < 0.08:
        patterns.append({
            "pattern": "bear_flag",
            "type": "continuation",
            "signal": "bearish",
            "confidence": 65,
            "pole_return_pct": float(pole_return * 100),
            "flag_return_pct": float(flag_return * 100),
            "target": float(current_price * (1 + pole_return)),
            "current_price": current_price,
        })

    return patterns


def detect_breakouts(df: pd.DataFrame, lookback: int = 20,
                      volume_factor: float = 1.5) -> List[Dict]:
    """
    Detect volume-confirmed breakouts: range breakout, 52-week high/low.
    """
    patterns = []
    if len(df) < max(lookback, 252):
        return []

    current = df.iloc[-1]
    avg_vol = df["Volume"].tail(lookback).mean()
    current_price = float(current["Close"])

    # Range breakout
    range_high = df["High"].tail(lookback).max()
    range_low = df["Low"].tail(lookback).min()

    if (current["Close"] > range_high and
            current["Volume"] > avg_vol * volume_factor):
        patterns.append({
            "pattern": "range_breakout_up",
            "type": "breakout",
            "signal": "bullish",
            "confidence": 70,
            "range_high": float(range_high),
            "range_low": float(range_low),
            "volume_ratio": float(current["Volume"] / avg_vol),
            "current_price": current_price,
        })

    if (current["Close"] < range_low and
            current["Volume"] > avg_vol * volume_factor):
        patterns.append({
            "pattern": "range_breakout_down",
            "type": "breakout",
            "signal": "bearish",
            "confidence": 70,
            "range_high": float(range_high),
            "range_low": float(range_low),
            "volume_ratio": float(current["Volume"] / avg_vol),
            "current_price": current_price,
        })

    # 52-week high/low
    yearly_high = df["High"].tail(252).max()
    yearly_low = df["Low"].tail(252).min()

    if current["Close"] >= yearly_high:
        patterns.append({
            "pattern": "52_week_high_breakout",
            "type": "breakout",
            "signal": "bullish",
            "confidence": 75,
            "yearly_high": float(yearly_high),
            "current_price": current_price,
        })

    if current["Close"] <= yearly_low:
        patterns.append({
            "pattern": "52_week_low_breakdown",
            "type": "breakout",
            "signal": "bearish",
            "confidence": 75,
            "yearly_low": float(yearly_low),
            "current_price": current_price,
        })

    return patterns


def detect_moving_average_crossovers(df: pd.DataFrame) -> List[Dict]:
    """Detect Golden Cross (bullish) and Death Cross (bearish)."""
    patterns = []
    if len(df) < 210:
        return patterns

    sma50 = sma(df["Close"], 50)
    sma200 = sma(df["Close"], 200)
    current_price = float(df["Close"].iloc[-1])

    # Golden Cross: 50 SMA crosses above 200 SMA
    if (sma50.iloc[-1] > sma200.iloc[-1] and
            sma50.iloc[-2] <= sma200.iloc[-2]):
        patterns.append({
            "pattern": "golden_cross",
            "type": "momentum",
            "signal": "bullish",
            "confidence": 72,
            "sma50": float(sma50.iloc[-1]),
            "sma200": float(sma200.iloc[-1]),
            "current_price": current_price,
        })

    # Death Cross: 50 SMA crosses below 200 SMA
    if (sma50.iloc[-1] < sma200.iloc[-1] and
            sma50.iloc[-2] >= sma200.iloc[-2]):
        patterns.append({
            "pattern": "death_cross",
            "type": "momentum",
            "signal": "bearish",
            "confidence": 72,
            "sma50": float(sma50.iloc[-1]),
            "sma200": float(sma200.iloc[-1]),
            "current_price": current_price,
        })

    return patterns


def detect_bb_squeeze(df: pd.DataFrame) -> List[Dict]:
    """Detect Bollinger Band squeeze — volatility contraction before expansion."""
    patterns = []
    if len(df) < 30:
        return patterns

    is_sq, intensity = squeeze_indicator(df["Close"], df["High"], df["Low"])
    current_price = float(df["Close"].iloc[-1])

    # Squeeze just released (was squeezing, now not)
    if len(is_sq) > 2 and is_sq.iloc[-2] and not is_sq.iloc[-1]:
        # Determine direction from momentum
        _, _, hist = macd(df["Close"])
        direction = "bullish" if hist.iloc[-1] > 0 else "bearish"
        patterns.append({
            "pattern": "bb_squeeze_release",
            "type": "momentum",
            "signal": direction,
            "confidence": 68,
            "squeeze_bars": int(is_sq.tail(50).sum()),
            "intensity": float(intensity.iloc[-2]) if not np.isnan(intensity.iloc[-2]) else 0,
            "current_price": current_price,
        })

    # Currently in squeeze
    if is_sq.iloc[-1]:
        patterns.append({
            "pattern": "bb_squeeze_active",
            "type": "momentum",
            "signal": "neutral",
            "confidence": 55,
            "squeeze_bars": int(is_sq.tail(50).sum()),
            "current_price": current_price,
        })

    return patterns


def detect_rsi_extremes(df: pd.DataFrame, period: int = 14) -> List[Dict]:
    """Detect RSI overbought/oversold conditions."""
    patterns = []
    rsi_val = rsi(df["Close"], period)
    current_rsi = float(rsi_val.iloc[-1])
    current_price = float(df["Close"].iloc[-1])

    if current_rsi > 70:
        patterns.append({
            "pattern": "rsi_overbought",
            "type": "momentum",
            "signal": "bearish",
            "confidence": 55 + int((current_rsi - 70) * 2),
            "rsi": current_rsi,
            "current_price": current_price,
        })
    elif current_rsi < 30:
        patterns.append({
            "pattern": "rsi_oversold",
            "type": "momentum",
            "signal": "bullish",
            "confidence": 55 + int((30 - current_rsi) * 2),
            "rsi": current_rsi,
            "current_price": current_price,
        })

    return patterns


# ---------------------------------------------------------------------------
# Master Scanner
# ---------------------------------------------------------------------------

def scan_all_patterns(df: pd.DataFrame, symbol: str = "") -> Dict:
    """
    Run all pattern detectors on a single stock's OHLCV DataFrame.
    Returns a comprehensive analysis dictionary.
    """
    all_patterns = []

    # Reversal patterns
    all_patterns.extend(detect_head_and_shoulders(df))
    all_patterns.extend(detect_double_top_bottom(df))

    # Continuation patterns
    all_patterns.extend(detect_triangles(df))
    all_patterns.extend(detect_wedges(df))
    all_patterns.extend(detect_flags(df))

    # Breakout patterns
    all_patterns.extend(detect_breakouts(df))

    # Momentum patterns
    all_patterns.extend(detect_moving_average_crossovers(df))
    all_patterns.extend(detect_bb_squeeze(df))
    all_patterns.extend(detect_rsi_extremes(df))

    # Support/Resistance
    sr_levels = detect_support_resistance(df)

    # S/R Breakouts
    sr_breakouts = detect_breakout_from_sr(df, sr_levels)
    all_patterns.extend(sr_breakouts)

    # Divergences
    divergences = detect_all_divergences(df)
    for d in divergences:
        d["pattern"] = d.pop("type")
        d["type"] = "divergence"
        all_patterns.append(d)

    # Add symbol to each pattern
    for p in all_patterns:
        p["symbol"] = symbol

    # Sort by confidence
    all_patterns.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    # Current indicators snapshot
    rsi_val = rsi(df["Close"], 14)
    macd_line, signal_line, hist = macd(df["Close"])
    adx_val = adx(df["High"], df["Low"], df["Close"])

    indicators = {
        "rsi_14": float(rsi_val.iloc[-1]) if not rsi_val.empty else None,
        "macd": float(macd_line.iloc[-1]) if not macd_line.empty else None,
        "macd_signal": float(signal_line.iloc[-1]) if not signal_line.empty else None,
        "macd_histogram": float(hist.iloc[-1]) if not hist.empty else None,
        "adx": float(adx_val.iloc[-1]) if not adx_val.empty and not np.isnan(adx_val.iloc[-1]) else None,
        "sma_20": float(sma(df["Close"], 20).iloc[-1]) if len(df) >= 20 else None,
        "sma_50": float(sma(df["Close"], 50).iloc[-1]) if len(df) >= 50 else None,
        "sma_200": float(sma(df["Close"], 200).iloc[-1]) if len(df) >= 200 else None,
    }

    return {
        "symbol": symbol,
        "current_price": float(df["Close"].iloc[-1]),
        "patterns": all_patterns,
        "support_resistance": sr_levels,
        "indicators": indicators,
        "data_points": len(df),
        "date_range": {
            "start": str(df.index[0]),
            "end": str(df.index[-1]),
        },
    }
