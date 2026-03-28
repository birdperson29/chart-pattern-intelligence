"""
FastAPI server for Chart Pattern Intelligence.
Endpoints: /api/scan, /api/analyze/{symbol}, /api/backtest/{symbol}, /api/chat
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
import traceback

from ..core.patterns import scan_all_patterns
from ..core.backtester import backtest_pattern, backtest_summary_text
from ..utils.data_fetcher import (
    fetch_stock_data, fetch_multiple, get_index_symbols, get_stock_info
)
from ..utils.explainer import explain_analysis, explain_pattern
from ..utils.sentiment import get_sentiment_summary
from ..models.schemas import (
    ScanRequest, StockAnalysis, BacktestResult, ChatRequest, ChatResponse
)


app = FastAPI(
    title="Chart Pattern Intelligence API",
    description="Real-time technical pattern detection for NSE stocks with plain-English explanations and backtested success rates.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "Chart Pattern Intelligence",
        "version": "1.0.0",
        "endpoints": ["/api/scan", "/api/analyze/{symbol}", "/api/backtest/{symbol}", "/api/chat"],
    }


@app.get("/api/scan")
def scan_index(
    index: str = Query(default="nifty50", description="Index to scan"),
    pattern_type: Optional[str] = Query(default=None, description="Filter: reversal, continuation, breakout, momentum, divergence"),
    signal: Optional[str] = Query(default=None, description="Filter: bullish, bearish, neutral"),
    min_confidence: int = Query(default=50, ge=0, le=100),
):
    """Scan an index for stocks showing active chart patterns."""
    symbols = get_index_symbols(index)
    results = []
    errors = []

    for sym in symbols:
        try:
            df = fetch_stock_data(sym, period="2y")
            if df is None:
                continue

            analysis = scan_all_patterns(df, symbol=sym)
            patterns = analysis["patterns"]

            # Apply filters
            if pattern_type:
                patterns = [p for p in patterns if p.get("type") == pattern_type]
            if signal:
                patterns = [p for p in patterns if p.get("signal") == signal]
            patterns = [p for p in patterns if p.get("confidence", 0) >= min_confidence]

            if patterns:
                analysis["patterns"] = patterns
                results.append(analysis)
        except Exception as e:
            errors.append({"symbol": sym, "error": str(e)})

    # Sort by number of patterns (most active first)
    results.sort(key=lambda x: len(x["patterns"]), reverse=True)

    return {
        "index": index,
        "total_stocks_scanned": len(symbols),
        "stocks_with_patterns": len(results),
        "results": results,
        "errors": errors[:5],
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/analyze/{symbol}")
def analyze_stock(
    symbol: str,
    period: str = Query(default="2y", description="Data period: 1y, 2y, 5y"),
    include_backtest: bool = Query(default=True, description="Include backtested success rates"),
    include_sentiment: bool = Query(default=False, description="Include news sentiment"),
):
    """Deep technical analysis of a single stock."""
    df = fetch_stock_data(symbol, period=period)
    if df is None:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for {symbol}")

    # Run pattern detection
    analysis = scan_all_patterns(df, symbol=symbol)

    # Run backtest if requested
    backtest_results = None
    if include_backtest and analysis["patterns"]:
        try:
            bt_df = fetch_stock_data(symbol, period="5y")
            if bt_df is not None:
                backtest_results = backtest_pattern(bt_df)
                analysis["backtest"] = backtest_results
        except Exception as e:
            analysis["backtest_error"] = str(e)

    # Add sentiment if requested
    if include_sentiment:
        try:
            sentiment = get_sentiment_summary(symbol)
            analysis["sentiment"] = sentiment
        except Exception:
            pass

    # Generate explanation
    analysis["explanation"] = explain_analysis(analysis, backtest_results)

    # Stock info
    try:
        info = get_stock_info(symbol)
        if info:
            analysis["stock_info"] = info
    except Exception:
        pass

    return analysis


@app.get("/api/backtest/{symbol}")
def backtest_stock(
    symbol: str,
    pattern: Optional[str] = Query(default=None, description="Specific pattern to backtest"),
    years: int = Query(default=5, ge=1, le=10),
    horizons: str = Query(default="5,10,20", description="Comma-separated forward return horizons"),
):
    """Backtest patterns on a specific stock."""
    period = f"{years}y"
    df = fetch_stock_data(symbol, period=period)
    if df is None:
        raise HTTPException(status_code=404, detail=f"Could not fetch data for {symbol}")

    horizon_list = [int(h.strip()) for h in horizons.split(",")]

    result = backtest_pattern(df, pattern_name=pattern, horizons=horizon_list)
    result["symbol"] = symbol
    result["summary_text"] = backtest_summary_text(result)

    return result


@app.post("/api/chat")
def chat(request: ChatRequest):
    """
    Conversational interface for pattern intelligence.
    Understands natural language queries about stocks and patterns.
    """
    message = request.message.lower().strip()
    response_text = ""
    patterns_found = []

    # Simple intent detection
    if any(w in message for w in ["breakout", "breaking out", "broken out"]):
        # Scan for breakout patterns
        symbols = get_index_symbols("nifty50")
        for sym in symbols[:20]:  # Limit for speed
            try:
                df = fetch_stock_data(sym, period="1y")
                if df is None:
                    continue
                from ..core.patterns import detect_breakouts
                breakouts = detect_breakouts(df)
                for b in breakouts:
                    b["symbol"] = sym
                    patterns_found.extend(breakouts)
            except Exception:
                continue

        if patterns_found:
            response_text = f"Found {len(patterns_found)} breakout signals:\n\n"
            for p in patterns_found[:5]:
                response_text += f"• {p['symbol']}: {p['pattern'].replace('_', ' ').title()} "
                response_text += f"(confidence: {p.get('confidence', 'N/A')}%)\n"
        else:
            response_text = "No breakout signals found in the Nifty 50 right now."

    elif any(w in message for w in ["analyze", "analysis", "check", "look at"]):
        # Extract symbol
        words = message.upper().split()
        # Try to find a stock symbol in the message
        from ..utils.nse_symbols import NIFTY_50
        symbol = None
        for w in words:
            clean = w.replace(",", "").replace(".", "").replace("?", "")
            if clean in NIFTY_50:
                symbol = clean
                break

        if symbol:
            df = fetch_stock_data(symbol, period="2y")
            if df is not None:
                analysis = scan_all_patterns(df, symbol=symbol)
                response_text = explain_analysis(analysis)
            else:
                response_text = f"Couldn't fetch data for {symbol}."
        else:
            response_text = "Which stock would you like me to analyze? Please mention the NSE symbol (e.g., RELIANCE, TATAMOTORS, INFY)."

    elif any(w in message for w in ["divergence", "rsi", "macd"]):
        response_text = "Scanning for divergences... Mention a specific stock for detailed divergence analysis, or I'll scan the Nifty 50."

    elif any(w in message for w in ["support", "resistance", "levels"]):
        response_text = "Mention a stock symbol and I'll show you key support and resistance levels."

    else:
        response_text = (
            "I can help you with:\n"
            "• 'Show me breakout candidates' — scan for breakout signals\n"
            "• 'Analyze RELIANCE' — deep technical analysis of a stock\n"
            "• 'Check TATAMOTORS for divergence' — divergence scan\n"
            "• 'Support resistance for INFY' — S/R levels\n"
            "\nJust ask in plain English!"
        )

    return ChatResponse(
        response=response_text,
        patterns=[],
    )


@app.get("/api/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
