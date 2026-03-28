"""
Command-line interface for Chart Pattern Intelligence.

Usage:
    python -m app.cli analyze RELIANCE.NS --days 365
    python -m app.cli scan --index nifty50
    python -m app.cli backtest TATAMOTORS.NS --pattern double_bottom --years 5
"""

import argparse
import sys
import json
from datetime import datetime

from .core.patterns import scan_all_patterns
from .core.backtester import backtest_pattern, backtest_summary_text
from .utils.data_fetcher import fetch_stock_data, get_index_symbols
from .utils.explainer import explain_analysis, explain_pattern


def cmd_analyze(args):
    """Analyze a single stock for patterns."""
    print(f"\n🔍 Analyzing {args.symbol}...")
    period = f"{args.days}d" if args.days <= 365 else f"{args.days // 365}y"
    df = fetch_stock_data(args.symbol, period=period)

    if df is None:
        print(f"❌ Could not fetch data for {args.symbol}")
        sys.exit(1)

    print(f"   Loaded {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")

    analysis = scan_all_patterns(df, symbol=args.symbol)

    # Optionally run backtest
    backtest_results = None
    if args.backtest:
        print("   Running backtest...")
        bt_df = fetch_stock_data(args.symbol, period="5y")
        if bt_df is not None:
            backtest_results = backtest_pattern(bt_df)

    # Print explanation
    report = explain_analysis(analysis, backtest_results)
    print(report)

    if args.json:
        print("\n--- JSON Output ---")
        # Remove non-serializable items
        for p in analysis.get("patterns", []):
            for k, v in list(p.items()):
                if isinstance(v, (datetime,)):
                    p[k] = str(v)
        print(json.dumps(analysis, indent=2, default=str))


def cmd_scan(args):
    """Scan an index for patterns."""
    symbols = get_index_symbols(args.index)
    print(f"\n📡 Scanning {len(symbols)} stocks in {args.index}...")
    print(f"   Min confidence: {args.min_confidence}%")
    if args.signal:
        print(f"   Signal filter: {args.signal}")
    print()

    found = 0
    for i, sym in enumerate(symbols):
        progress = f"[{i+1}/{len(symbols)}]"
        df = fetch_stock_data(sym, period="1y")
        if df is None:
            continue

        analysis = scan_all_patterns(df, symbol=sym)
        patterns = analysis["patterns"]

        # Apply filters
        if args.signal:
            patterns = [p for p in patterns if p.get("signal") == args.signal]
        patterns = [p for p in patterns if p.get("confidence", 0) >= args.min_confidence]

        if patterns:
            found += 1
            price = analysis["current_price"]
            print(f"{progress} {sym:15s} ₹{price:>10.2f}  |  {len(patterns)} pattern(s):")
            for p in patterns[:3]:
                emoji = "🟢" if p["signal"] == "bullish" else "🔴" if p["signal"] == "bearish" else "🟡"
                print(f"      {emoji} {p['pattern'].replace('_', ' ').title()} "
                      f"({p['signal']}, {p.get('confidence', '?')}% confidence)")

    print(f"\n✅ Scan complete: {found}/{len(symbols)} stocks showing patterns.")


def cmd_backtest(args):
    """Backtest a pattern on a stock."""
    print(f"\n📊 Backtesting {args.pattern or 'all patterns'} on {args.symbol} ({args.years}yr)...")

    df = fetch_stock_data(args.symbol, period=f"{args.years}y")
    if df is None:
        print(f"❌ Could not fetch data for {args.symbol}")
        sys.exit(1)

    print(f"   Loaded {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")

    result = backtest_pattern(df, pattern_name=args.pattern)
    summary = backtest_summary_text(result)
    print()
    print(summary)

    if args.json:
        # Strip instances for cleaner JSON
        for pname in result.get("patterns", {}):
            result["patterns"][pname].pop("instances", None)
        print("\n--- JSON Output ---")
        print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        prog="cpi",
        description="Chart Pattern Intelligence — Technical pattern detection for NSE stocks",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze a single stock")
    p_analyze.add_argument("symbol", type=str, help="Stock symbol (e.g., RELIANCE.NS)")
    p_analyze.add_argument("--days", type=int, default=365, help="Number of days of data")
    p_analyze.add_argument("--backtest", action="store_true", help="Include backtest results")
    p_analyze.add_argument("--json", action="store_true", help="Output raw JSON")

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan an index for patterns")
    p_scan.add_argument("--index", type=str, default="nifty50", help="Index: nifty50, nifty100, nifty200")
    p_scan.add_argument("--signal", type=str, default=None, help="Filter: bullish, bearish, neutral")
    p_scan.add_argument("--min-confidence", type=int, default=50, dest="min_confidence")

    # backtest
    p_bt = subparsers.add_parser("backtest", help="Backtest patterns on a stock")
    p_bt.add_argument("symbol", type=str, help="Stock symbol")
    p_bt.add_argument("--pattern", type=str, default=None, help="Specific pattern name")
    p_bt.add_argument("--years", type=int, default=5, help="Years of history")
    p_bt.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
