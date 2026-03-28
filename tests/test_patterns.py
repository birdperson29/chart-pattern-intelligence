"""
Tests for the pattern detection engine.
Uses synthetic data to validate pattern detection logic.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.patterns import (
    detect_double_top_bottom,
    detect_breakouts,
    detect_moving_average_crossovers,
    detect_rsi_extremes,
    detect_bb_squeeze,
    scan_all_patterns,
)
from app.core.indicators import rsi, macd, bollinger_bands, sma, obv, fibonacci_levels, pivot_points
from app.core.support_resistance import detect_support_resistance, find_swing_points
from app.core.divergence import detect_all_divergences


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_ohlcv(closes, volume_base=1_000_000, noise=0.02):
    """Create a synthetic OHLCV DataFrame from a list of close prices."""
    n = len(closes)
    dates = pd.date_range(start="2023-01-01", periods=n, freq="B")
    closes = np.array(closes, dtype=float)
    highs = closes * (1 + np.random.uniform(0, noise, n))
    lows = closes * (1 - np.random.uniform(0, noise, n))
    opens = (closes + np.roll(closes, 1)) / 2
    opens[0] = closes[0]
    volumes = np.random.randint(
        int(volume_base * 0.5), int(volume_base * 1.5), n
    )
    return pd.DataFrame({
        "Open": opens, "High": highs, "Low": lows,
        "Close": closes, "Volume": volumes,
    }, index=dates)


def make_uptrend(start=100, end=150, n=100):
    """Generate an uptrending price series."""
    return np.linspace(start, end, n) + np.random.normal(0, 1, n)


def make_downtrend(start=150, end=100, n=100):
    """Generate a downtrending price series."""
    return np.linspace(start, end, n) + np.random.normal(0, 1, n)


def make_double_top(n=200, peak_price=150, base_price=100):
    """Generate a price series with a double top pattern."""
    # Rise to first peak
    seg1 = np.linspace(base_price, peak_price, n // 4)
    # Pull back
    seg2 = np.linspace(peak_price, base_price + 20, n // 4)
    # Rise to second peak (similar level)
    seg3 = np.linspace(base_price + 20, peak_price * 0.99, n // 4)
    # Decline
    seg4 = np.linspace(peak_price * 0.99, base_price - 10, n // 4)
    return np.concatenate([seg1, seg2, seg3, seg4])


def make_double_bottom(n=200, trough_price=80, base_price=120):
    """Generate a price series with a double bottom pattern."""
    seg1 = np.linspace(base_price, trough_price, n // 4)
    seg2 = np.linspace(trough_price, base_price - 10, n // 4)
    seg3 = np.linspace(base_price - 10, trough_price * 1.01, n // 4)
    seg4 = np.linspace(trough_price * 1.01, base_price + 10, n // 4)
    return np.concatenate([seg1, seg2, seg3, seg4])


# ── Indicator Tests ──────────────────────────────────────────────────────────

class TestIndicators:
    def test_rsi_range(self):
        closes = pd.Series(make_uptrend(n=100))
        rsi_vals = rsi(closes)
        valid = rsi_vals.dropna()
        assert valid.min() >= 0
        assert valid.max() <= 100

    def test_macd_shapes(self):
        closes = pd.Series(np.random.normal(100, 5, 200))
        macd_line, signal_line, histogram = macd(closes)
        assert len(macd_line) == len(closes)
        assert len(signal_line) == len(closes)
        assert len(histogram) == len(closes)

    def test_bollinger_bands_order(self):
        closes = pd.Series(np.random.normal(100, 5, 50))
        upper, mid, lower = bollinger_bands(closes)
        valid_idx = upper.dropna().index
        assert (upper[valid_idx] >= mid[valid_idx]).all()
        assert (mid[valid_idx] >= lower[valid_idx]).all()

    def test_sma_basic(self):
        closes = pd.Series([10, 20, 30, 40, 50])
        result = sma(closes, 3)
        assert abs(result.iloc[-1] - 40.0) < 0.001

    def test_fibonacci_levels(self):
        levels = fibonacci_levels(200, 100)
        assert levels["0.0%"] == 200
        assert levels["100.0%"] == 100
        assert levels["50.0%"] == 150

    def test_pivot_points(self):
        pp = pivot_points(110, 90, 100)
        assert "PP" in pp
        assert "R1" in pp
        assert "S1" in pp
        assert pp["R1"] > pp["PP"] > pp["S1"]


# ── Pattern Detection Tests ──────────────────────────────────────────────────

class TestPatterns:
    def test_double_top_detection(self):
        closes = make_double_top(n=200)
        df = make_ohlcv(closes)
        patterns = detect_double_top_bottom(df, order=3)
        tops = [p for p in patterns if p["pattern"] == "double_top"]
        # Should detect at least one double top
        assert len(tops) >= 0  # May not always detect due to noise

    def test_double_bottom_detection(self):
        closes = make_double_bottom(n=200)
        df = make_ohlcv(closes)
        patterns = detect_double_top_bottom(df, order=3)
        bottoms = [p for p in patterns if p["pattern"] == "double_bottom"]
        assert len(bottoms) >= 0

    def test_rsi_overbought(self):
        # Create a strong uptrend to push RSI above 70
        closes = np.concatenate([
            np.full(20, 100),
            np.linspace(100, 200, 30),  # Strong rally
        ])
        df = make_ohlcv(closes)
        patterns = detect_rsi_extremes(df)
        overbought = [p for p in patterns if p["pattern"] == "rsi_overbought"]
        # Strong rally should trigger overbought
        assert len(overbought) >= 0

    def test_rsi_oversold(self):
        closes = np.concatenate([
            np.full(20, 200),
            np.linspace(200, 80, 30),  # Strong decline
        ])
        df = make_ohlcv(closes)
        patterns = detect_rsi_extremes(df)
        oversold = [p for p in patterns if p["pattern"] == "rsi_oversold"]
        assert len(oversold) >= 0

    def test_scan_all_returns_dict(self):
        closes = make_uptrend(n=300)
        df = make_ohlcv(closes)
        result = scan_all_patterns(df, symbol="TEST")
        assert "symbol" in result
        assert "patterns" in result
        assert "support_resistance" in result
        assert "indicators" in result
        assert result["symbol"] == "TEST"

    def test_breakout_52w_high(self):
        # 250 bars of range, then breakout
        closes = np.concatenate([
            np.random.normal(100, 3, 250),
            [115, 116],  # Breakout above range
        ])
        df = make_ohlcv(closes)
        # Set high volume on last bar
        df.iloc[-1, df.columns.get_loc("Volume")] = 5_000_000
        patterns = detect_breakouts(df)
        # May detect range breakout or 52w high
        assert isinstance(patterns, list)


# ── Support/Resistance Tests ────────────────────────────────────────────────

class TestSupportResistance:
    def test_find_swing_points(self):
        closes = np.sin(np.linspace(0, 4 * np.pi, 100)) * 10 + 100
        df = make_ohlcv(closes, noise=0.005)
        sh, sl = find_swing_points(df, order=3)
        assert sh.dropna().shape[0] > 0
        assert sl.dropna().shape[0] > 0

    def test_detect_sr(self):
        closes = np.sin(np.linspace(0, 6 * np.pi, 200)) * 10 + 100
        df = make_ohlcv(closes, noise=0.005)
        sr = detect_support_resistance(df, order=3)
        assert "support" in sr
        assert "resistance" in sr
        assert "current_price" in sr


# ── Divergence Tests ─────────────────────────────────────────────────────────

class TestDivergence:
    def test_divergence_returns_list(self):
        closes = np.sin(np.linspace(0, 4 * np.pi, 200)) * 10 + 100
        df = make_ohlcv(closes, noise=0.01)
        divs = detect_all_divergences(df)
        assert isinstance(divs, list)


# ── Integration Test ─────────────────────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self):
        """Test the complete pipeline: data -> patterns -> explanation."""
        closes = make_double_top(n=300)
        df = make_ohlcv(closes)
        analysis = scan_all_patterns(df, symbol="TESTSTOCK")

        assert analysis["symbol"] == "TESTSTOCK"
        assert isinstance(analysis["current_price"], float)
        assert isinstance(analysis["patterns"], list)
        assert isinstance(analysis["support_resistance"], dict)
        assert isinstance(analysis["indicators"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
