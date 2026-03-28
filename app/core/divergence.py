"""
Divergence detection: RSI, MACD, and OBV divergences (bullish & bearish).
A divergence occurs when price makes a new high/low but the indicator does not confirm it.
"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from typing import List, Dict

from .indicators import rsi, macd, obv


def _find_peaks(series: np.ndarray, order: int = 5):
    """Find local maxima indices."""
    return argrelextrema(series, np.greater_equal, order=order)[0]


def _find_troughs(series: np.ndarray, order: int = 5):
    """Find local minima indices."""
    return argrelextrema(series, np.less_equal, order=order)[0]


def _detect_divergence(price: pd.Series, indicator: pd.Series,
                        order: int = 5, lookback: int = 60) -> List[Dict]:
    """
    Generic divergence detector.
    Returns list of divergence events with type, dates, and values.
    """
    divergences = []
    recent_price = price.tail(lookback).values
    recent_ind = indicator.tail(lookback).values
    recent_idx = price.tail(lookback).index

    # Bullish divergence: price makes lower low, indicator makes higher low
    price_troughs = _find_troughs(recent_price, order=order)
    ind_troughs = _find_troughs(recent_ind, order=order)

    if len(price_troughs) >= 2 and len(ind_troughs) >= 2:
        pt1, pt2 = price_troughs[-2], price_troughs[-1]
        # Find corresponding indicator troughs near these price troughs
        it_near_pt1 = ind_troughs[np.argmin(np.abs(ind_troughs - pt1))]
        it_near_pt2 = ind_troughs[np.argmin(np.abs(ind_troughs - pt2))]

        if (recent_price[pt2] < recent_price[pt1] and
                recent_ind[it_near_pt2] > recent_ind[it_near_pt1]):
            divergences.append({
                "type": "bullish_divergence",
                "signal": "bullish",
                "start_date": str(recent_idx[pt1]),
                "end_date": str(recent_idx[pt2]),
                "price_low_1": float(recent_price[pt1]),
                "price_low_2": float(recent_price[pt2]),
                "ind_low_1": float(recent_ind[it_near_pt1]),
                "ind_low_2": float(recent_ind[it_near_pt2]),
            })

    # Bearish divergence: price makes higher high, indicator makes lower high
    price_peaks = _find_peaks(recent_price, order=order)
    ind_peaks = _find_peaks(recent_ind, order=order)

    if len(price_peaks) >= 2 and len(ind_peaks) >= 2:
        pp1, pp2 = price_peaks[-2], price_peaks[-1]
        ip_near_pp1 = ind_peaks[np.argmin(np.abs(ind_peaks - pp1))]
        ip_near_pp2 = ind_peaks[np.argmin(np.abs(ind_peaks - pp2))]

        if (recent_price[pp2] > recent_price[pp1] and
                recent_ind[ip_near_pp2] < recent_ind[ip_near_pp1]):
            divergences.append({
                "type": "bearish_divergence",
                "signal": "bearish",
                "start_date": str(recent_idx[pp1]),
                "end_date": str(recent_idx[pp2]),
                "price_high_1": float(recent_price[pp1]),
                "price_high_2": float(recent_price[pp2]),
                "ind_high_1": float(recent_ind[ip_near_pp1]),
                "ind_high_2": float(recent_ind[ip_near_pp2]),
            })

    return divergences


def detect_rsi_divergence(df: pd.DataFrame, period: int = 14,
                           order: int = 5, lookback: int = 60) -> List[Dict]:
    """Detect bullish/bearish RSI divergences."""
    rsi_values = rsi(df["Close"], period)
    divs = _detect_divergence(df["Close"], rsi_values, order=order, lookback=lookback)
    for d in divs:
        d["indicator"] = "RSI"
    return divs


def detect_macd_divergence(df: pd.DataFrame, fast: int = 12, slow: int = 26,
                            signal: int = 9, order: int = 5,
                            lookback: int = 60) -> List[Dict]:
    """Detect bullish/bearish MACD histogram divergences."""
    _, _, histogram = macd(df["Close"], fast, slow, signal)
    divs = _detect_divergence(df["Close"], histogram, order=order, lookback=lookback)
    for d in divs:
        d["indicator"] = "MACD"
    return divs


def detect_obv_divergence(df: pd.DataFrame, order: int = 5,
                           lookback: int = 60) -> List[Dict]:
    """Detect bullish/bearish OBV divergences."""
    obv_values = obv(df["Close"], df["Volume"])
    divs = _detect_divergence(df["Close"], obv_values, order=order, lookback=lookback)
    for d in divs:
        d["indicator"] = "OBV"
    return divs


def detect_all_divergences(df: pd.DataFrame, order: int = 5,
                            lookback: int = 60) -> List[Dict]:
    """Run all divergence detectors and return combined results."""
    all_divs = []
    all_divs.extend(detect_rsi_divergence(df, order=order, lookback=lookback))
    all_divs.extend(detect_macd_divergence(df, order=order, lookback=lookback))
    all_divs.extend(detect_obv_divergence(df, order=order, lookback=lookback))
    return all_divs
