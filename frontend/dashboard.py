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
    "💬 Chat",
    "🔍 Stock Analysis",
    "📡 Pattern Scanner",
    "📈 Backtester",
], index=0)

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
    st.title("💬 Smart Stock Chat")

    st.info("Ask anything in plain English! Examples: 'I have ₹10,000 to invest for 4 months', 'Best bullish stocks right now', 'Is RELIANCE a good buy?', 'Which stocks are oversold?'")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ── Smart Intent Engine ──────────────────────────────────────
    import re

    def parse_budget(msg):
        """Extract budget amount from message."""
        patterns_re = [
            r'₹\s*([\d,]+)', r'rs\.?\s*([\d,]+)', r'inr\s*([\d,]+)',
            r'([\d,]+)\s*(?:rupees|rs|inr)', r'([\d,]+)\s*(?:to invest|budget)',
            r'(?:invest|have|got)\s*(?:₹|rs\.?|inr)?\s*([\d,]+)',
        ]
        for p in patterns_re:
            m = re.search(p, msg, re.IGNORECASE)
            if m:
                return int(m.group(1).replace(',', ''))
        return None

    def parse_timeframe(msg):
        """Extract investment timeframe in months."""
        m = re.search(r'(\d+)\s*(?:-\s*\d+\s*)?(?:month|mo)', msg, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.search(r'(\d+)\s*(?:-\s*\d+\s*)?(?:year|yr)', msg, re.IGNORECASE)
        if m:
            return int(m.group(1)) * 12
        m = re.search(r'(\d+)\s*(?:-\s*\d+\s*)?(?:week|wk)', msg, re.IGNORECASE)
        if m:
            return max(1, int(m.group(1)) // 4)
        if any(w in msg.lower() for w in ['short term', 'short-term', 'quick']):
            return 3
        if any(w in msg.lower() for w in ['long term', 'long-term']):
            return 12
        return None

    def detect_intent(msg):
        """Classify user intent."""
        msg_lower = msg.lower()
        msg_upper = msg.upper()

        # Check for specific stock symbol
        symbol_found = None
        for sym in NIFTY_50:
            # Match whole word to avoid partial matches
            if re.search(r'\b' + re.escape(sym) + r'\b', msg_upper):
                symbol_found = sym
                break

        # Investment recommendation intent
        invest_words = ['invest', 'buy', 'which stock', 'best stock', 'recommend',
                       'suggestion', 'where to put', 'good stock', 'returns',
                       'portfolio', 'money', 'rupees', 'budget', 'pick']
        is_invest = any(w in msg_lower for w in invest_words)

        # Scan intent
        scan_words = ['scan', 'breakout', 'breaking', 'all stocks', 'nifty',
                     'screen', 'filter', 'find stocks', 'show me stocks']
        is_scan = any(w in msg_lower for w in scan_words)

        # Specific pattern query
        pattern_words = ['oversold', 'overbought', 'divergence', 'support', 'resistance',
                        'golden cross', 'death cross', 'squeeze', 'double top',
                        'double bottom', 'head and shoulders', 'triangle', 'wedge', 'flag']
        pattern_match = None
        for pw in pattern_words:
            if pw in msg_lower:
                pattern_match = pw
                break

        # Comparison intent
        is_compare = any(w in msg_lower for w in ['vs', 'versus', 'compare', 'or', 'better'])

        # Sector query
        sector_words = {'it': 'IT', 'tech': 'IT', 'bank': 'Banking', 'banking': 'Banking',
                       'pharma': 'Pharma', 'auto': 'Auto', 'fmcg': 'FMCG', 'metal': 'Metals',
                       'oil': 'Oil & Gas', 'power': 'Power', 'telecom': 'Telecom',
                       'cement': 'Cement', 'insurance': 'Insurance', 'finance': 'Finance'}
        sector_found = None
        for sw, sector_name in sector_words.items():
            if re.search(r'\b' + sw + r'\b', msg_lower):
                sector_found = sector_name
                break

        return {
            'symbol': symbol_found,
            'is_invest': is_invest,
            'is_scan': is_scan,
            'pattern_match': pattern_match,
            'is_compare': is_compare,
            'sector': sector_found,
            'budget': parse_budget(msg),
            'timeframe': parse_timeframe(msg),
        }

    def smart_invest_response(intent, status_placeholder):
        """Handle investment recommendation queries."""
        budget = intent['budget']
        timeframe = intent['timeframe'] or 3
        sector = intent['sector']

        # Determine which stocks to scan
        if sector:
            symbols = [s for s, sec in SECTOR_MAP.items() if sec == sector]
            scan_label = f"{sector} sector stocks"
        else:
            symbols = NIFTY_50
            scan_label = "Nifty 50"

        status_placeholder.text(f"🔍 Scanning {scan_label} for bullish patterns...")

        bullish_picks = []
        for i, sym in enumerate(symbols):
            status_placeholder.text(f"Analyzing {sym}... ({i+1}/{len(symbols)})")
            df = fetch_stock_data(sym, period="1y")
            if df is None:
                continue

            analysis = scan_all_patterns(df, symbol=sym)
            bullish_patterns = [p for p in analysis["patterns"] if p.get("signal") == "bullish" and p.get("confidence", 0) >= 55]

            if bullish_patterns:
                price = analysis["current_price"]
                rsi_val = analysis["indicators"].get("rsi_14", 50)
                # Score: more bullish patterns + higher confidence + favorable RSI = better
                score = sum(p.get("confidence", 50) for p in bullish_patterns) + (60 - rsi_val if rsi_val < 50 else 0)

                bullish_picks.append({
                    "symbol": sym,
                    "price": price,
                    "patterns": bullish_patterns,
                    "pattern_count": len(bullish_patterns),
                    "top_confidence": max(p.get("confidence", 0) for p in bullish_patterns),
                    "rsi": rsi_val,
                    "score": score,
                    "sector": SECTOR_MAP.get(sym, "Unknown"),
                })

        status_placeholder.empty()

        if not bullish_picks:
            return "I scanned the market but didn't find strong bullish setups right now. The market might be in a consolidation phase. Try again in a few days or check specific stocks you're interested in."

        # Sort by score
        bullish_picks.sort(key=lambda x: x["score"], reverse=True)
        top_picks = bullish_picks[:5]

        # Build response
        lines = []

        # Personalized intro
        if budget:
            lines.append(f"💰 **Budget: ₹{budget:,}** | ⏱️ **Timeframe: ~{timeframe} months**\n")
        lines.append(f"I scanned **{len(symbols)} stocks** in {scan_label} and found **{len(bullish_picks)} with bullish signals**. Here are the top picks:\n")
        lines.append("---")

        for i, pick in enumerate(top_picks):
            emoji_rank = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]
            lines.append(f"\n{emoji_rank} **{pick['symbol']}** — ₹{pick['price']:,.2f}")
            lines.append(f"   Sector: {pick['sector']} | RSI: {pick['rsi']:.1f}")

            for p in pick["patterns"][:3]:
                pname = p["pattern"].replace("_", " ").title()
                lines.append(f"   🟢 {pname} (confidence: {p.get('confidence', '?')}%)")

            # Budget-aware note
            if budget and pick["price"] > 0:
                shares = int(budget / pick["price"])
                if shares > 0:
                    invest_amount = shares * pick["price"]
                    lines.append(f"   📊 With ₹{budget:,} → you can buy **{shares} shares** (₹{invest_amount:,.0f})")
                else:
                    lines.append(f"   ⚠️ Price ₹{pick['price']:,.0f} exceeds your budget per share")

        lines.append("\n---")

        # Timeframe-specific advice
        if timeframe and timeframe <= 3:
            lines.append("\n⏱️ **Short-term (1-3 months)**: Focus on breakout and momentum patterns. Use strict stop-losses (5-7% below entry).")
        elif timeframe and timeframe <= 6:
            lines.append("\n⏱️ **Medium-term (3-6 months)**: Reversal patterns (double bottom, inverse H&S) tend to play out well. Consider averaging in over 2-3 tranches.")
        elif timeframe:
            lines.append("\n⏱️ **Long-term (6+ months)**: Golden cross and trend-following setups work best. SIP approach recommended over lump sum.")

        if budget and budget <= 15000:
            lines.append("\n💡 **Tip for small portfolios**: Consider 2-3 stocks max to avoid over-diversification. Or look at ETFs (NIFTYBEES, JUNIORBEES) for diversified exposure at low cost.")

        lines.append("\n⚠️ *This is pattern-based technical analysis, not financial advice. Always do your own research and consider consulting a SEBI-registered advisor.*")

        return "\n".join(lines)

    def smart_pattern_scan(pattern_keyword, status_placeholder):
        """Scan for a specific pattern type across Nifty 50."""
        pattern_map = {
            'oversold': ('rsi_oversold', 'bullish'),
            'overbought': ('rsi_overbought', 'bearish'),
            'divergence': ('divergence', None),
            'golden cross': ('golden_cross', 'bullish'),
            'death cross': ('death_cross', 'bearish'),
            'squeeze': ('bb_squeeze', None),
            'double top': ('double_top', 'bearish'),
            'double bottom': ('double_bottom', 'bullish'),
            'head and shoulders': ('head_and_shoulders', None),
            'triangle': ('triangle', None),
            'wedge': ('wedge', None),
            'flag': ('flag', None),
            'support': ('support', None),
            'resistance': ('resistance', None),
        }

        target_pattern, _ = pattern_map.get(pattern_keyword, (pattern_keyword, None))
        found = []

        for i, sym in enumerate(NIFTY_50):
            status_placeholder.text(f"Scanning {sym} for {pattern_keyword}... ({i+1}/{len(NIFTY_50)})")
            df = fetch_stock_data(sym, period="1y")
            if df is None:
                continue

            analysis = scan_all_patterns(df, symbol=sym)
            matching = [p for p in analysis["patterns"] if target_pattern in p.get("pattern", "")]

            if matching:
                found.append({
                    "symbol": sym,
                    "price": analysis["current_price"],
                    "patterns": matching,
                    "sector": SECTOR_MAP.get(sym, "Unknown"),
                })

        status_placeholder.empty()

        if not found:
            return f"No stocks in Nifty 50 currently showing **{pattern_keyword}** pattern. This pattern may appear when market conditions change."

        lines = [f"Found **{len(found)} stocks** with **{pattern_keyword}** signals:\n"]
        for f_item in found[:8]:
            emoji = "🟢" if any(p.get("signal") == "bullish" for p in f_item["patterns"]) else "🔴" if any(p.get("signal") == "bearish" for p in f_item["patterns"]) else "🟡"
            lines.append(f"{emoji} **{f_item['symbol']}** — ₹{f_item['price']:,.2f} ({f_item['sector']})")
            for p in f_item["patterns"][:2]:
                pname = p["pattern"].replace("_", " ").title()
                lines.append(f"   → {pname} | Confidence: {p.get('confidence', '?')}% | Signal: {p.get('signal', 'N/A')}")
        return "\n".join(lines)

    def smart_compare(symbols_list, status_placeholder):
        """Compare two or more stocks."""
        results = []
        for sym in symbols_list:
            status_placeholder.text(f"Analyzing {sym}...")
            df = fetch_stock_data(sym, period="1y")
            if df is None:
                continue
            analysis = scan_all_patterns(df, symbol=sym)
            bullish = [p for p in analysis["patterns"] if p.get("signal") == "bullish"]
            bearish = [p for p in analysis["patterns"] if p.get("signal") == "bearish"]
            results.append({
                "symbol": sym,
                "price": analysis["current_price"],
                "bullish_count": len(bullish),
                "bearish_count": len(bearish),
                "rsi": analysis["indicators"].get("rsi_14", 0),
                "patterns": analysis["patterns"],
                "sector": SECTOR_MAP.get(sym, "Unknown"),
            })
        status_placeholder.empty()

        if len(results) < 2:
            return "Need at least 2 valid stocks to compare. Make sure the symbols are in the Nifty 50."

        lines = ["📊 **Head-to-Head Comparison**\n"]
        lines.append("| Metric | " + " | ".join(r["symbol"] for r in results) + " |")
        lines.append("|--------|" + "|".join(["--------"] * len(results)) + "|")
        lines.append("| Price | " + " | ".join(f"₹{r['price']:,.2f}" for r in results) + " |")
        lines.append("| RSI | " + " | ".join(f"{r['rsi']:.1f}" for r in results) + " |")
        lines.append("| Bullish Signals | " + " | ".join(f"🟢 {r['bullish_count']}" for r in results) + " |")
        lines.append("| Bearish Signals | " + " | ".join(f"🔴 {r['bearish_count']}" for r in results) + " |")

        # Winner
        best = max(results, key=lambda r: r["bullish_count"] - r["bearish_count"])
        lines.append(f"\n**Technical edge: {best['symbol']}** has the strongest bullish setup with {best['bullish_count']} bullish vs {best['bearish_count']} bearish signals.")

        for r in results:
            if r["patterns"]:
                lines.append(f"\n**{r['symbol']}** patterns:")
                for p in r["patterns"][:3]:
                    emoji = "🟢" if p.get("signal") == "bullish" else "🔴" if p.get("signal") == "bearish" else "🟡"
                    lines.append(f"  {emoji} {p['pattern'].replace('_', ' ').title()} ({p.get('confidence', '?')}%)")

        return "\n".join(lines)

    # ── Chat UI ──────────────────────────────────────────────────
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask anything about stocks, investments, or patterns...")

    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            status = st.empty()
            intent = detect_intent(user_input)
            response = ""

            # 1. Compare stocks (e.g., "RELIANCE vs TCS" or "compare INFY and WIPRO")
            if intent['is_compare'] and not intent['symbol']:
                msg_upper = user_input.upper()
                compare_symbols = [s for s in NIFTY_50 if re.search(r'\b' + re.escape(s) + r'\b', msg_upper)]
                if len(compare_symbols) >= 2:
                    response = smart_compare(compare_symbols[:4], status)
                else:
                    response = "Please mention at least 2 stock symbols to compare. Example: 'Compare RELIANCE vs TCS'"

            # 2. Specific stock analysis
            elif intent['symbol'] and not intent['is_invest']:
                status.text(f"🔍 Analyzing {intent['symbol']}...")
                df = fetch_stock_data(intent['symbol'], period="1y")
                if df is not None:
                    analysis = scan_all_patterns(df, symbol=intent['symbol'])
                    patterns = analysis["patterns"]
                    price = analysis["current_price"]
                    indicators = analysis["indicators"]

                    lines = [f"## {intent['symbol']} — ₹{price:,.2f}\n"]

                    # Quick verdict
                    bullish = [p for p in patterns if p.get("signal") == "bullish"]
                    bearish = [p for p in patterns if p.get("signal") == "bearish"]
                    if len(bullish) > len(bearish):
                        lines.append(f"**Overall: 🟢 BULLISH** ({len(bullish)} bullish vs {len(bearish)} bearish signals)\n")
                    elif len(bearish) > len(bullish):
                        lines.append(f"**Overall: 🔴 BEARISH** ({len(bearish)} bearish vs {len(bullish)} bullish signals)\n")
                    else:
                        lines.append(f"**Overall: 🟡 NEUTRAL** ({len(bullish)} bullish, {len(bearish)} bearish)\n")

                    # Key indicators
                    rsi_val = indicators.get("rsi_14", 0)
                    rsi_label = "Overbought ⚠️" if rsi_val > 70 else "Oversold 👀" if rsi_val < 30 else "Neutral"
                    lines.append(f"**RSI:** {rsi_val:.1f} ({rsi_label})")
                    if indicators.get("sma_50") and indicators.get("sma_200"):
                        above200 = "✅ Above" if price > indicators["sma_200"] else "❌ Below"
                        lines.append(f"**200-day SMA:** ₹{indicators['sma_200']:,.0f} ({above200})")

                    # Patterns
                    if patterns:
                        lines.append(f"\n**Detected Patterns:**")
                        for p in patterns[:5]:
                            emoji = "🟢" if p.get("signal") == "bullish" else "🔴" if p.get("signal") == "bearish" else "🟡"
                            pname = p["pattern"].replace("_", " ").title()
                            lines.append(f"  {emoji} **{pname}** — {p.get('signal', 'N/A')} (confidence: {p.get('confidence', '?')}%)")
                    else:
                        lines.append("\nNo significant patterns detected right now.")

                    # S/R levels
                    sr = analysis.get("support_resistance", {})
                    supports = sr.get("support", [])[:2]
                    resistances = sr.get("resistance", [])[:2]
                    if supports or resistances:
                        lines.append(f"\n**Key Levels:**")
                        for s in supports:
                            lines.append(f"  🟢 Support: ₹{s['level']:,.0f} ({s['touches']}x tested)")
                        for r in resistances:
                            lines.append(f"  🔴 Resistance: ₹{r['level']:,.0f} ({r['touches']}x tested)")

                    # Buy/sell context
                    msg_lower = user_input.lower()
                    if any(w in msg_lower for w in ['buy', 'good buy', 'should i', 'worth']):
                        lines.append(f"\n**Should you buy?**")
                        if len(bullish) > len(bearish) and rsi_val < 65:
                            lines.append(f"Technical signals are leaning bullish with {len(bullish)} positive patterns. RSI at {rsi_val:.0f} suggests room to run.")
                        elif rsi_val > 70:
                            lines.append(f"⚠️ RSI is overbought at {rsi_val:.0f} — consider waiting for a pullback before entering.")
                        elif len(bearish) > len(bullish):
                            lines.append(f"⚠️ More bearish signals ({len(bearish)}) than bullish ({len(bullish)}). May want to wait for reversal confirmation.")
                        else:
                            lines.append(f"Signals are mixed. Consider waiting for a clearer setup or average in gradually.")

                    lines.append("\n⚠️ *Technical analysis only — not financial advice.*")
                    response = "\n".join(lines)
                else:
                    response = f"Sorry, couldn't fetch data for {intent['symbol']}. Check the symbol and try again."
                status.empty()

            # 3. Investment recommendation (budget/timeframe based)
            elif intent['is_invest'] or intent['budget']:
                response = smart_invest_response(intent, status)

            # 4. Specific pattern scan
            elif intent['pattern_match']:
                response = smart_pattern_scan(intent['pattern_match'], status)

            # 5. Sector query
            elif intent['sector'] and not intent['is_invest']:
                sector = intent['sector']
                sector_symbols = [s for s, sec in SECTOR_MAP.items() if sec == sector]
                if sector_symbols:
                    lines = [f"## {sector} Sector Analysis\n"]
                    for sym in sector_symbols:
                        df = fetch_stock_data(sym, period="1y")
                        if df is None:
                            continue
                        analysis = scan_all_patterns(df, symbol=sym)
                        bullish = sum(1 for p in analysis["patterns"] if p.get("signal") == "bullish")
                        bearish = sum(1 for p in analysis["patterns"] if p.get("signal") == "bearish")
                        emoji = "🟢" if bullish > bearish else "🔴" if bearish > bullish else "🟡"
                        lines.append(f"{emoji} **{sym}** — ₹{analysis['current_price']:,.2f} | {bullish} bullish, {bearish} bearish")
                    response = "\n".join(lines)
                else:
                    response = f"No stocks found for sector: {sector}"
                status.empty()

            # 6. Scan / breakout search
            elif intent['is_scan']:
                response = smart_invest_response({**intent, 'is_invest': True, 'budget': None, 'timeframe': None, 'sector': None}, status)

            # 7. Fallback — but still helpful
            else:
                response = (
                    "I can help with a lot! Here are some things you can ask:\n\n"
                    "💰 **Investment queries:**\n"
                    "  • 'I have ₹10,000 to invest for 3 months'\n"
                    "  • 'Best stocks to buy right now'\n"
                    "  • 'Good banking stocks for long term'\n\n"
                    "📊 **Stock analysis:**\n"
                    "  • 'Analyze RELIANCE'\n"
                    "  • 'Is TATAMOTORS a good buy?'\n"
                    "  • 'Compare INFY vs TCS vs WIPRO'\n\n"
                    "🔍 **Pattern scanning:**\n"
                    "  • 'Which stocks are oversold?'\n"
                    "  • 'Find golden cross stocks'\n"
                    "  • 'Show me breakout candidates'\n\n"
                    "🏢 **Sector analysis:**\n"
                    "  • 'How is the IT sector looking?'\n"
                    "  • 'Best pharma stocks'\n\n"
                    "Just ask naturally — I'll figure out what you need! 🚀"
                )

            st.markdown(response)
            st.session_state.chat_history.append({"role": "assistant", "content": response})


# ── Footer ───────────────────────────────────────────────────────────────────

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<small>Built for ET AI Hackathon 2026<br>"
    "⚠️ Not financial advice. For educational purposes only.</small>",
    unsafe_allow_html=True,
)
