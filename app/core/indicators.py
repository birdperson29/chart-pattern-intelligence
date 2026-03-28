"""
Technical indicator calculations used by the pattern detection engine.
All functions take a pandas DataFrame with OHLCV columns and return Series/DataFrames.
"""

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, and histogram."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0):
    """Bollinger Bands — upper, middle, lower."""
    middle = sma(close, period)
    rolling_std = close.rolling(window=period, min_periods=period).std()
    upper = middle + std_dev * rolling_std
    lower = middle - std_dev * rolling_std
    return upper, middle, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.where(close > close.shift(1), 1, np.where(close < close.shift(1), -1, 0))
    return (volume * direction).cumsum()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Volume Weighted Average Price (cumulative, resets not implemented — use daily)."""
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3):
    """Stochastic Oscillator (%K and %D)."""
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = sma(k, d_period)
    return k, d


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index."""
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period)


def squeeze_indicator(close: pd.Series, high: pd.Series, low: pd.Series,
                      bb_period: int = 20, bb_std: float = 2.0,
                      kc_period: int = 20, kc_mult: float = 1.5):
    """
    Bollinger Band Squeeze — detects when BB narrows inside Keltner Channels.
    Returns (is_squeeze: bool Series, squeeze_intensity: float Series).
    """
    bb_upper, bb_mid, bb_lower = bollinger_bands(close, bb_period, bb_std)
    bb_width = bb_upper - bb_lower

    atr_val = atr(high, low, close, kc_period)
    kc_upper = ema(close, kc_period) + kc_mult * atr_val
    kc_lower = ema(close, kc_period) - kc_mult * atr_val

    is_squeeze = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    squeeze_intensity = 1 - (bb_width / (kc_upper - kc_lower).replace(0, np.nan))

    return is_squeeze, squeeze_intensity


def fibonacci_levels(high_price: float, low_price: float) -> dict:
    """Calculate Fibonacci retracement levels."""
    diff = high_price - low_price
    return {
        "0.0%": high_price,
        "23.6%": high_price - 0.236 * diff,
        "38.2%": high_price - 0.382 * diff,
        "50.0%": high_price - 0.500 * diff,
        "61.8%": high_price - 0.618 * diff,
        "78.6%": high_price - 0.786 * diff,
        "100.0%": low_price,
    }


def pivot_points(high: float, low: float, close: float) -> dict:
    """Standard pivot points."""
    pp = (high + low + close) / 3
    return {
        "R3": high + 2 * (pp - low),
        "R2": pp + (high - low),
        "R1": 2 * pp - low,
        "PP": pp,
        "S1": 2 * pp - high,
        "S2": pp - (high - low),
        "S3": low - 2 * (high - pp),
    }
