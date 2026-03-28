"""Tests for the backtesting engine."""

import pytest
import numpy as np
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.backtester import (
    backtest_pattern,
    compute_forward_returns,
    backtest_summary_text,
)


def make_ohlcv(closes, volume_base=1_000_000):
    n = len(closes)
    dates = pd.date_range(start="2020-01-01", periods=n, freq="B")
    closes = np.array(closes, dtype=float)
    highs = closes * 1.01
    lows = closes * 0.99
    opens = closes * 1.005
    volumes = np.full(n, volume_base)
    return pd.DataFrame({
        "Open": opens, "High": highs, "Low": lows,
        "Close": closes, "Volume": volumes,
    }, index=dates)


class TestBacktester:
    def test_compute_forward_returns(self):
        closes = np.linspace(100, 120, 50)
        df = make_ohlcv(closes)
        returns = compute_forward_returns(df, 10, horizons=[5, 10])
        assert "5d_return" in returns
        assert "10d_return" in returns
        assert returns["5d_return"] is not None
        assert returns["5d_return"] > 0  # Uptrend

    def test_compute_forward_returns_edge(self):
        closes = np.linspace(100, 120, 50)
        df = make_ohlcv(closes)
        returns = compute_forward_returns(df, 45, horizons=[10])
        assert returns["10d_return"] is None  # Not enough data

    def test_backtest_no_patterns(self):
        closes = np.full(300, 100.0)  # Flat line — no patterns
        df = make_ohlcv(closes)
        result = backtest_pattern(df, pattern_name="golden_cross")
        assert result["total_detections"] == 0

    def test_backtest_returns_structure(self):
        # Create data with some movement
        closes = np.concatenate([
            np.linspace(100, 150, 150),
            np.linspace(150, 90, 150),
            np.linspace(90, 130, 150),
        ])
        df = make_ohlcv(closes)
        result = backtest_pattern(df)
        assert "patterns" in result
        assert "data_range" in result
        assert "total_detections" in result

    def test_backtest_summary_text(self):
        result = {
            "pattern_filter": "all",
            "total_detections": 5,
            "patterns": {
                "rsi_oversold": {
                    "pattern": "rsi_oversold",
                    "total_instances": 3,
                    "expected_direction": "up",
                    "5d_success_rate": 66.7,
                    "5d_avg_return": 2.1,
                }
            },
            "horizons": [5, 10, 20],
            "data_range": {"start": "2020-01-01", "end": "2024-12-31", "bars": 1200},
        }
        text = backtest_summary_text(result)
        assert "Backtest Results" in text
        assert "Rsi Oversold" in text
        assert "66.7%" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
