"""
Chart Pattern Intelligence — Streamlit Dashboard
Interactive frontend for pattern scanning, stock analysis, and backtesting.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.patterns import scan_all_patterns
from app.core.backtester import backtest_pattern, backtest_summary_text
from app.core.indicators import rsi, macd, bollinger_bands, sma, obv
from app.core.support_resistance import detect_support_resistance, find_swing_points
from app.core.divergence import detect_all_divergences
from app.utils.data_fetcher import fetch_stock_data, get_index_symbols, get_stock_info
from app.utils.explainer import explain_analysis, explain_pattern
from app.utils.nse_symbols import NIFTY_50, SECTOR_MAP

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Chart Pattern Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .stMetric { background: #0e1117; border-radius: 8px; padding: 12px; border: 1px solid #1e2530; }
    div[data-testid="stMetricValue"] { font-size: 1.4rem; }
    .pattern-card {
        background: #161b22;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
        border-left: 4px solid;
    }
    .bullish { border-left-color: #26a269; }
    .bearish { border-left-color: #e01b24; }
    .neutral { border-left-color: #f5c211; }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ─────────────────────────────────────────────────────────

def plot_candlestick(df, symbol, patterns=None, sr_levels=None):
    """Create an interactive candlestick chart with indicators and pattern annotations."""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{symbol} Price", "Volume", "RSI"),
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price",
        increasing_line_color="#26a269", decreasing_line_color="#e01b24",
    ), row=1, col=1)

    # Moving averages
    if len(df) >= 20:
        sma20 = sma(df["Close"], 20)
        fig.add_trace(go.Scatter(
            x=df.index, y=sma20, name="SMA 20",
            line=dict(color="#f5c211", width=1),
        ), row=1, col=1)

    if len(df) >= 50:
        sma50 = sma(df["Close"], 50)
        fig.add_trace(go.Scatter(
            x=df.index, y=sma50, name="SMA 50",
            line=dict(color="#62a0ea", width=1),
        ), row=1, col=1)

    if len(df) >= 200:
        sma200 = sma(df["Close"], 200)
        fig.add_trace(go.Scatter(
            x=df.index, y=sma200, name="SMA 200",
            line=dict(color="#c061cb", width=1),
        ), row=1, col=1)

    # Bollinger Bands
    if len(df) >= 20:
        bb_upper, bb_mid, bb_lower = bollinger_bands(df["Close"])
        fig.add_trace(go.Scatter(
            x=df.index, y=bb_upper, name="BB Upper",
            line=dict(color="rgba(255,255,255,0.15)", width=1),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=bb_lower, name="BB Lower",
            line=dict(color="rgba(255,255,255,0.15)", width=1),
            fill="tonexty", fillcolor="rgba(255,255,255,0.03)",
        ), row=1, col=1)

    # Support / Resistance lines
    if sr_levels:
        for s in sr_levels.get("support", [])[:3]:
            fig.add_hline(
                y=s["level"], line_dash="dash",
                line_color="rgba(38,162,105,0.5)",
                annotation_text=f"S: ₹{s['level']:.0f}",
                row=1, col=1,
            )
        for r in sr_levels.get("resistance", [])[:3]:
            fig.add_hline(
                y=r["level"], line_dash="dash",
                line_color="rgba(224,27,36,0.5)",
                annotation_text=f"R: ₹{r['level']:.0f}",
                row=1, col=1,
            )

    # Volume
    colors = ["#26a269" if c >= o else "#e01b24"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="Volume",
        marker_color=colors, opacity=0.7,
    ), row=2, col=1)

    # RSI
    if len(df) >= 14:
        rsi_vals = rsi(df["Close"])
        fig.add_trace(go.Scatter(
            x=df.index, y=rsi_vals, name="RSI",
            line=dict(color="#f5c211", width=1.5),
        ), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(224,27,36,0.4)", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(38,162,105,0.4)", row=3, col=1)

    # Pattern annotations
    if patterns:
        for p in patterns[:5]:
            signal = p.get("signal", "neutral")
            color = "#26a269" if signal == "bullish" else "#e01b24" if signal == "bearish" else "#f5c211"
            emoji = "🟢" if signal == "bullish" else "🔴" if signal == "bearish" else "🟡"
            name = p["pattern"].replace("_", " ").title()

            fig.add_annotation(
                x=df.index[-1], y=p.get("current_price", df["Close"].iloc[-1]),
                text=f"{emoji} {name}",
                showarrow=True, arrowhead=2,
                arrowcolor=color, font=dict(color=color, size=10),
                bgcolor="rgba(14,17,23,0.8)", bordercolor=color,
                xshift=10,
            )

    fig.update_layout(
        template="plotly_dark",
        height=700,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=20, t=40, b=20),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
    )
    fig.update_xaxes(gridcolor="#1e2530")
    fig.update_yaxes(gridcolor="#1e2530")

    return fig


def pattern_card(pattern, show_explanation=True):
    """Render a pattern as a styled card."""
    signal = pattern.get("signal", "neutral")
    css_class = signal
    emoji = "🟢" if signal == "bullish" else "🔴" if signal == "bearish" else "🟡"
    name = pattern["pattern"].replace("_", " ").title()
    confidence = pattern.get("confidence", "?")

    st.markdown(f"""
    <div class="pattern-card {css_class}">
        <strong>{emoji} {name}</strong>
        <span style="float:right; color:#8b949e;">Confidence: {confidence}%</span>
        <br><small style="color:#8b949e;">Type: {pattern.get('type', 'N/A')} | Signal: {signal}</small>
    </div>
    """, unsafe_allow_html=True)

    if show_explanation:
        with st.expander("📖 What does this mean?"):
            st.text(explain_pattern(pattern))


# ── Sidebar ──────────────────────────────────────────────────────────────────

st.sidebar.title("📊 CPI")
st.sidebar.caption("Chart Pattern Intelligence")

page = st.sidebar.radio("Navigate", [
    "🔍 Stock Analysis",
    "📡 Pattern Scanner",
    "📈 Backtester",
    "💬 Chat",
])

st.sidebar.markdown("---")
st.sidebar.markdown("**Settings**")
data_period = st.sidebar.selectbox("Data Period", ["6mo", "1y", "2y", "5y"], index=2)


# ── Pages ────────────────────────────────────────────────────────────────────

if page == "🔍 Stock Analysis":
    st.title("🔍 Stock Technical Analysis")

    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input(
            "Enter NSE Symbol",
            value="RELIANCE",
            placeholder="e.g., RELIANCE, TATAMOTORS, INFY",
        ).upper().strip()
    with col2:
        run_backtest = st.checkbox("Include Backtest", value=True)

    if st.button("🚀 Analyze", type="primary") or symbol:
        with st.spinner(f"Analyzing {symbol}..."):
            df = fetch_stock_data(symbol, period=data_period)

        if df is None:
            st.error(f"Could not fetch data for {symbol}. Check the symbol and try again.")
        else:
            analysis = scan_all_patterns(df, symbol=symbol)
            patterns = analysis["patterns"]
            sr = analysis["support_resistance"]
            indicators = analysis["indicators"]

            # ── Metrics row ──
            col1, col2, col3, col4, col5 = st.columns(5)
            price = analysis["current_price"]
            prev_close = float(df["Close"].iloc[-2]) if len(df) > 1 else price
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            col1.metric("Price", f"₹{price:,.2f}", f"{change:+.2f} ({change_pct:+.1f}%)")
            col2.metric("RSI (14)", f"{indicators.get('rsi_14', 0):.1f}")
            col3.metric("Patterns", len(patterns))

            bullish_count = sum(1 for p in patterns if p.get("signal") == "bullish")
            bearish_count = sum(1 for p in patterns if p.get("signal") == "bearish")
            bias = "🟢 Bullish" if bullish_count > bearish_count else "🔴 Bearish" if bearish_count > bullish_count else "🟡 Neutral"
            col4.metric("Bias", bias)
            col5.metric("Data Points", len(df))

            # ── Chart ──
            fig = plot_candlestick(df, symbol, patterns, sr)
            st.plotly_chart(fig, use_container_width=True)

            # ── Patterns ──
            if patterns:
                st.subheader("Detected Patterns")
                for p in patterns:
                    pattern_card(p)
            else:
                st.info("No significant patterns detected at this time.")

            # ── Support / Resistance ──
            st.subheader("Support & Resistance Levels")
            sr_col1, sr_col2 = st.columns(2)
            with sr_col1:
                st.markdown("**🟢 Support Levels**")
                for s in sr.get("support", [])[:5]:
                    dist = (price - s["level"]) / price * 100
                    st.write(f"₹{s['level']:,.2f} — {s['touches']} touches ({dist:.1f}% below)")
            with sr_col2:
                st.markdown("**🔴 Resistance Levels**")
                for r in sr.get("resistance", [])[:5]:
                    dist = (r["level"] - price) / price * 100
                    st.write(f"₹{r['level']:,.2f} — {r['touches']} touches ({dist:.1f}% above)")

            # ── Backtest ──
            if run_backtest and patterns:
                st.subheader("📈 Historical Backtest Results")
                with st.spinner("Running backtest on 5-year data..."):
                    bt_df = fetch_stock_data(symbol, period="5y")
                    if bt_df is not None:
                        bt_result = backtest_pattern(bt_df)
                        for pname, stats in bt_result.get("patterns", {}).items():
                            name = pname.replace("_", " ").title()
                            instances = stats.get("total_instances", 0)
                            if instances == 0:
                                continue
                            st.markdown(f"**{name}** — {instances} historical instances")
                            bt_cols = st.columns(3)
                            for i, h in enumerate([5, 10, 20]):
                                sr_val = stats.get(f"{h}d_success_rate")
                                avg_ret = stats.get(f"{h}d_avg_return")
                                if sr_val is not None:
                                    bt_cols[i].metric(
                                        f"{h}-Day Success Rate",
                                        f"{sr_val:.1f}%",
                                        f"Avg return: {avg_ret:+.2f}%"
                                    )

            # ── Key Indicators ──
            with st.expander("📐 Detailed Indicators"):
                ind_cols = st.columns(4)
                ind_cols[0].write(f"**MACD**: {indicators.get('macd', 'N/A'):.2f}" if indicators.get('macd') else "**MACD**: N/A")
                ind_cols[1].write(f"**MACD Signal**: {indicators.get('macd_signal', 'N/A'):.2f}" if indicators.get('macd_signal') else "**Signal**: N/A")
                ind_cols[2].write(f"**ADX**: {indicators.get('adx', 'N/A'):.1f}" if indicators.get('adx') else "**ADX**: N/A")
                ind_cols[3].write(f"**SMA 200**: ₹{indicators.get('sma_200', 0):,.2f}" if indicators.get('sma_200') else "**SMA 200**: N/A")


elif page == "📡 Pattern Scanner":
    st.title("📡 NSE Pattern Scanner")

    col1, col2, col3 = st.columns(3)
    with col1:
        index = st.selectbox("Index", ["nifty50", "nifty100"], index=0)
    with col2:
        signal_filter = st.selectbox("Signal Filter", ["All", "Bullish", "Bearish"], index=0)
    with col3:
        min_conf = st.slider("Min Confidence", 0, 100, 55)

    if st.button("🔎 Scan Now", type="primary"):
        symbols = get_index_symbols(index)
        progress = st.progress(0)
        status = st.empty()
        results = []

        for i, sym in enumerate(symbols):
            status.text(f"Scanning {sym}... ({i+1}/{len(symbols)})")
            progress.progress((i + 1) / len(symbols))

            df = fetch_stock_data(sym, period="1y")
            if df is None:
                continue

            analysis = scan_all_patterns(df, symbol=sym)
            patterns = analysis["patterns"]

            # Apply filters
            if signal_filter != "All":
                patterns = [p for p in patterns if p.get("signal") == signal_filter.lower()]
            patterns = [p for p in patterns if p.get("confidence", 0) >= min_conf]

            if patterns:
                analysis["patterns"] = patterns
                results.append(analysis)

        progress.empty()
        status.empty()

        st.success(f"Scan complete: {len(results)}/{len(symbols)} stocks showing patterns.")

        if results:
            # Summary table
            rows = []
            for r in results:
                for p in r["patterns"]:
                    rows.append({
                        "Symbol": r["symbol"],
                        "Price": f"₹{r['current_price']:,.2f}",
                        "Pattern": p["pattern"].replace("_", " ").title(),
                        "Signal": p.get("signal", "").title(),
                        "Confidence": f"{p.get('confidence', '?')}%",
                        "Type": p.get("type", "").title(),
                    })

            scan_df = pd.DataFrame(rows)
            st.dataframe(scan_df, use_container_width=True, hide_index=True)

            # Detailed cards
            for r in results[:10]:
                with st.expander(f"{r['symbol']} — ₹{r['current_price']:,.2f} ({len(r['patterns'])} patterns)"):
                    for p in r["patterns"]:
                        pattern_card(p)


elif page == "📈 Backtester":
    st.title("📈 Pattern Backtester")

    col1, col2, col3 = st.columns(3)
    with col1:
        bt_symbol = st.text_input("Symbol", value="RELIANCE").upper().strip()
    with col2:
        bt_pattern = st.selectbox("Pattern (optional)", [
            "All Patterns",
            "head_and_shoulders", "inverse_head_and_shoulders",
            "double_top", "double_bottom",
            "ascending_triangle", "descending_triangle", "symmetrical_triangle",
            "rising_wedge", "falling_wedge",
            "bull_flag", "bear_flag",
            "range_breakout_up", "range_breakout_down",
            "golden_cross", "death_cross",
            "bb_squeeze_release",
            "rsi_overbought", "rsi_oversold",
        ])
    with col3:
        bt_years = st.slider("Years of History", 2, 10, 5)

    if st.button("▶️ Run Backtest", type="primary"):
        with st.spinner(f"Backtesting on {bt_years} years of {bt_symbol} data..."):
            df = fetch_stock_data(bt_symbol, period=f"{bt_years}y")

        if df is None:
            st.error(f"Could not fetch data for {bt_symbol}")
        else:
            st.info(f"Loaded {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")

            pattern_filter = None if bt_pattern == "All Patterns" else bt_pattern
            result = backtest_pattern(df, pattern_name=pattern_filter)

            if result.get("total_detections", 0) == 0:
                st.warning("No pattern instances found in the historical data.")
            else:
                st.success(f"Found {result['total_detections']} pattern instance(s)")

                for pname, stats in result.get("patterns", {}).items():
                    name = pname.replace("_", " ").title()
                    n = stats["total_instances"]

                    st.markdown(f"### {name}")
                    st.write(f"**{n} instances** found | Expected direction: {stats['expected_direction']}")

                    cols = st.columns(3)
                    for i, h in enumerate([5, 10, 20]):
                        sr_val = stats.get(f"{h}d_success_rate")
                        avg = stats.get(f"{h}d_avg_return")
                        best = stats.get(f"{h}d_best")
                        worst = stats.get(f"{h}d_worst")
                        if sr_val is not None:
                            cols[i].metric(f"{h}-Day Success", f"{sr_val:.1f}%", f"Avg: {avg:+.2f}%")
                            cols[i].caption(f"Best: {best:+.1f}% | Worst: {worst:+.1f}%")

                    # Show individual instances in a table
                    instances = stats.get("instances", [])
                    if instances:
                        with st.expander(f"View all {n} instances"):
                            inst_rows = []
                            for inst in instances:
                                inst_rows.append({
                                    "Date": inst.get("detection_date", ""),
                                    "Price": f"₹{inst.get('current_price', 0):,.2f}",
                                    "5d Return": f"{inst.get('5d_return', 'N/A')}%",
                                    "10d Return": f"{inst.get('10d_return', 'N/A')}%",
                                    "20d Return": f"{inst.get('20d_return', 'N/A')}%",
                                    "Confidence": f"{inst.get('confidence', '?')}%",
                                })
                            st.dataframe(pd.DataFrame(inst_rows), use_container_width=True, hide_index=True)


elif page == "💬 Chat":
    st.title("💬 Ask About Patterns")

    st.info("Ask questions in plain English. Examples: 'Analyze RELIANCE', 'Show me breakout stocks', 'What patterns is TATAMOTORS showing?'")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask about stocks, patterns, or the market...")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Simple intent parsing
                msg = user_input.upper()
                response = ""

                # Try to find a symbol
                symbol_found = None
                for sym in NIFTY_50:
                    if sym in msg:
                        symbol_found = sym
                        break

                if symbol_found:
                    df = fetch_stock_data(symbol_found, period="1y")
                    if df is not None:
                        analysis = scan_all_patterns(df, symbol=symbol_found)
                        response = explain_analysis(analysis)
                    else:
                        response = f"Sorry, couldn't fetch data for {symbol_found}."
                elif any(w in msg for w in ["BREAKOUT", "BREAKING", "SCAN"]):
                    response = "Scanning Nifty 50 for breakouts...\n\n"
                    symbols = get_index_symbols("nifty50")
                    found = []
                    for sym in symbols:
                        df = fetch_stock_data(sym, period="1y")
                        if df is None:
                            continue
                        analysis = scan_all_patterns(df, symbol=sym)
                        bk = [p for p in analysis["patterns"] if "breakout" in p.get("pattern", "")]
                        if bk:
                            found.append((sym, bk))

                    if found:
                        for sym, pats in found[:5]:
                            for p in pats:
                                emoji = "🟢" if p["signal"] == "bullish" else "🔴"
                                response += f"{emoji} **{sym}**: {p['pattern'].replace('_', ' ').title()} ({p.get('confidence', '?')}%)\n"
                    else:
                        response += "No breakout signals found right now."
                else:
                    response = (
                        "I can help with:\n"
                        "- **Analyze [SYMBOL]** — e.g., 'Analyze RELIANCE'\n"
                        "- **Breakout scan** — find breakout candidates\n"
                        "- **[SYMBOL] patterns** — e.g., 'TATAMOTORS patterns'\n\n"
                        "Just mention an NSE stock symbol and I'll analyze it!"
                    )

                st.text(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})


# ── Footer ───────────────────────────────────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<small>Built for ET AI Hackathon 2026<br>"
    "⚠️ Not financial advice. For educational purposes only.</small>",
    unsafe_allow_html=True,
)
