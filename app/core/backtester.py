"""
Backtesting Engine
Runs pattern detection on historical data and measures forward returns
to compute success rates for each pattern on each stock.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import timedelta

from .patterns import (
    detect_head_and_shoulders,
    detect_double_top_bottom,
    detect_triangles,
    detect_wedges,
    detect_flags,
    detect_breakouts,
    detect_moving_average_crossovers,
    detect_bb_squeeze,
    detect_rsi_extremes,
)
from .divergence import detect_all_divergences


# Mapping of pattern names to their expected direction
PATTERN_DIRECTION = {
    # Bullish patterns
    "inverse_head_and_shoulders": "up",
    "double_bottom": "up",
    "ascending_triangle": "up",
    "falling_wedge": "up",
    "bull_flag": "up",
    "range_breakout_up": "up",
    "52_week_high_breakout": "up",
    "golden_cross": "up",
    "rsi_oversold": "up",
    "bullish_divergence": "up",

    # Bearish patterns
    "head_and_shoulders": "down",
    "double_top": "down",
    "descending_triangle": "down",
    "rising_wedge": "down",
    "bear_flag": "down",
    "range_breakout_down": "down",
    "52_week_low_breakdown": "down",
    "death_cross": "down",
    "rsi_overbought": "down",
    "bearish_divergence": "down",

    # Neutral
    "symmetrical_triangle": "neutral",
    "bb_squeeze_active": "neutral",
    "bb_squeeze_release": "neutral",
}


def _rolling_scan(df: pd.DataFrame, window_size: int = 252,
                   step: int = 5) -> List[Dict]:
    """
    Slide a window across the dataframe and run pattern detection at each step.
    Returns list of (detection_date, pattern_name, signal, detection_index).
    """
    detections = []

    for end_idx in range(window_size, len(df) - 20, step):  # leave 20 bars for forward returns
        window = df.iloc[:end_idx]

        # Run all detectors on the window
        found = []
        found.extend(detect_head_and_shoulders(window))
        found.extend(detect_double_top_bottom(window))
        found.extend(detect_triangles(window))
        found.extend(detect_wedges(window))
        found.extend(detect_flags(window))
        found.extend(detect_breakouts(window))
        found.extend(detect_moving_average_crossovers(window))
        found.extend(detect_bb_squeeze(window))
        found.extend(detect_rsi_extremes(window))
        divs = detect_all_divergences(window)
        for d in divs:
            d["pattern"] = d.pop("type")
            found.append(d)

        for p in found:
            detections.append({
                "detection_index": end_idx,
                "detection_date": str(df.index[end_idx - 1]),
                "pattern": p["pattern"],
                "signal": p.get("signal", "neutral"),
                "confidence": p.get("confidence", 50),
                "current_price": float(df["Close"].iloc[end_idx - 1]),
            })

    return detections


def compute_forward_returns(df: pd.DataFrame, detection_index: int,
                             horizons: List[int] = None) -> Dict:
    """
    Compute forward returns from a detection point.
    horizons: list of forward bar counts (default: 5, 10, 20 days).
    """
    if horizons is None:
        horizons = [5, 10, 20]

    entry_price = df["Close"].iloc[detection_index]
    returns = {}

    for h in horizons:
        exit_idx = detection_index + h
        if exit_idx < len(df):
            exit_price = df["Close"].iloc[exit_idx]
            ret = (exit_price - entry_price) / entry_price * 100
            returns[f"{h}d_return"] = float(ret)
            # Max drawdown and max gain in the window
            window = df["Close"].iloc[detection_index:exit_idx + 1]
            returns[f"{h}d_max_gain"] = float((window.max() - entry_price) / entry_price * 100)
            returns[f"{h}d_max_drawdown"] = float((window.min() - entry_price) / entry_price * 100)
        else:
            returns[f"{h}d_return"] = None

    return returns


def backtest_pattern(df: pd.DataFrame, pattern_name: Optional[str] = None,
                      window_size: int = 252, step: int = 5,
                      horizons: List[int] = None) -> Dict:
    """
    Full backtest: detect patterns historically, compute forward returns,
    and aggregate success rates.

    Args:
        df: Full OHLCV DataFrame
        pattern_name: Filter to a specific pattern (or None for all)
        window_size: Rolling window size for detection
        step: Step size for rolling window
        horizons: Forward return horizons (days)

    Returns:
        Dict with per-pattern success rates and statistics.
    """
    if horizons is None:
        horizons = [5, 10, 20]

    # Step 1: Find all historical pattern detections
    detections = _rolling_scan(df, window_size=window_size, step=step)

    if pattern_name:
        detections = [d for d in detections if d["pattern"] == pattern_name]

    if not detections:
        return {
            "pattern": pattern_name or "all",
            "total_detections": 0,
            "message": "No pattern instances found in historical data.",
        }

    # Step 2: Deduplicate — same pattern within 10 bars counts as one
    deduped = []
    seen = {}
    for d in sorted(detections, key=lambda x: x["detection_index"]):
        key = d["pattern"]
        if key not in seen or d["detection_index"] - seen[key] > 10:
            deduped.append(d)
            seen[key] = d["detection_index"]
    detections = deduped

    # Step 3: Compute forward returns for each detection
    results_by_pattern = {}
    for d in detections:
        pname = d["pattern"]
        fwd = compute_forward_returns(df, d["detection_index"], horizons)
        d.update(fwd)

        if pname not in results_by_pattern:
            results_by_pattern[pname] = []
        results_by_pattern[pname].append(d)

    # Step 4: Aggregate statistics per pattern
    summary = {}
    for pname, instances in results_by_pattern.items():
        expected_dir = PATTERN_DIRECTION.get(pname, "neutral")

        stats = {
            "pattern": pname,
            "total_instances": len(instances),
            "expected_direction": expected_dir,
        }

        for h in horizons:
            key = f"{h}d_return"
            valid = [i[key] for i in instances if i[key] is not None]

            if valid:
                arr = np.array(valid)
                if expected_dir == "up":
                    success = float(np.mean(arr > 0) * 100)
                elif expected_dir == "down":
                    success = float(np.mean(arr < 0) * 100)
                else:
                    success = float(np.mean(np.abs(arr) > 2) * 100)  # >2% move either way

                stats[f"{h}d_success_rate"] = round(success, 1)
                stats[f"{h}d_avg_return"] = round(float(np.mean(arr)), 2)
                stats[f"{h}d_median_return"] = round(float(np.median(arr)), 2)
                stats[f"{h}d_best"] = round(float(np.max(arr)), 2)
                stats[f"{h}d_worst"] = round(float(np.min(arr)), 2)
                stats[f"{h}d_win_count"] = int(np.sum(arr > 0) if expected_dir == "up" else np.sum(arr < 0))
            else:
                stats[f"{h}d_success_rate"] = None

        stats["instances"] = instances  # Full detail
        summary[pname] = stats

    return {
        "pattern_filter": pattern_name or "all",
        "total_detections": len(detections),
        "patterns": summary,
        "horizons": horizons,
        "data_range": {
            "start": str(df.index[0]),
            "end": str(df.index[-1]),
            "bars": len(df),
        },
    }


def backtest_summary_text(backtest_result: Dict) -> str:
    """Generate a plain-text summary of backtest results."""
    lines = []
    lines.append(f"=== Backtest Results ===")
    lines.append(f"Data: {backtest_result['data_range']['start']} to {backtest_result['data_range']['end']}")
    lines.append(f"Total detections: {backtest_result['total_detections']}")
    lines.append("")

    for pname, stats in backtest_result.get("patterns", {}).items():
        lines.append(f"--- {pname.replace('_', ' ').title()} ---")
        lines.append(f"  Instances found: {stats['total_instances']}")
        lines.append(f"  Expected direction: {stats['expected_direction']}")

        for h in backtest_result.get("horizons", [5, 10, 20]):
            sr = stats.get(f"{h}d_success_rate")
            avg = stats.get(f"{h}d_avg_return")
            if sr is not None:
                lines.append(f"  {h}-day: {sr}% success rate | avg return: {avg}%")
        lines.append("")

    return "\n".join(lines)
