"""
Plain-English Explanation Generator
Generates human-readable explanations for detected patterns.
Uses template-based explanations by default, with optional LLM enhancement.
"""

import os
from typing import Dict, Optional

# Pattern explanation templates
PATTERN_EXPLANATIONS = {
    "head_and_shoulders": {
        "name": "Head & Shoulders",
        "what": "A bearish reversal pattern with three peaks — the middle peak (head) is the highest, flanked by two lower peaks (shoulders). It signals that buyers are losing momentum.",
        "action": "Watch for a break below the neckline (₹{neckline:.2f}). If confirmed with volume, the price target is ₹{target:.2f}.",
        "psychology": "Buyers pushed prices up three times but couldn't sustain the head's high. Each failed attempt weakens bullish conviction, and sellers start to dominate.",
    },
    "inverse_head_and_shoulders": {
        "name": "Inverse Head & Shoulders",
        "what": "A bullish reversal pattern with three troughs — the middle trough (head) is the lowest, flanked by two higher troughs (shoulders). It signals that selling pressure is exhausting.",
        "action": "Watch for a break above the neckline (₹{neckline:.2f}). If confirmed with volume, the price target is ₹{target:.2f}.",
        "psychology": "Sellers pushed prices down three times but couldn't break below the head's low. The pattern shows sellers losing steam and buyers stepping in at higher levels.",
    },
    "double_top": {
        "name": "Double Top",
        "what": "A bearish reversal pattern where price hits the same resistance level twice and fails to break above it. Think of it as the market saying 'no higher' twice.",
        "action": "The neckline is at ₹{neckline:.2f}. A break below with volume confirms the pattern, with a target of ₹{target:.2f}.",
        "psychology": "Buyers tried to push past resistance twice and failed both times. This double rejection often triggers a sell-off as traders lose confidence in further upside.",
    },
    "double_bottom": {
        "name": "Double Bottom",
        "what": "A bullish reversal pattern where price hits the same support level twice and bounces. The market is saying 'no lower' — buyers step in at this price.",
        "action": "The neckline is at ₹{neckline:.2f}. A break above with volume confirms the pattern, with a target of ₹{target:.2f}.",
        "psychology": "Sellers tried to push below support twice and failed. This double support test shows strong buying interest at this level, often leading to a rally.",
    },
    "ascending_triangle": {
        "name": "Ascending Triangle",
        "what": "A bullish continuation pattern with a flat resistance line and rising support (higher lows). Buyers are getting more aggressive, pushing price up to resistance.",
        "action": "Resistance is at ₹{resistance:.2f}. A breakout above this level with high volume is a buy signal.",
        "psychology": "Each pullback finds buyers at higher prices, compressing the range against resistance. This building pressure typically resolves with an upward breakout.",
    },
    "descending_triangle": {
        "name": "Descending Triangle",
        "what": "A bearish continuation pattern with a flat support line and falling resistance (lower highs). Sellers are getting more aggressive.",
        "action": "Support is at ₹{support:.2f}. A breakdown below this level with high volume is a sell signal.",
        "psychology": "Each rally is sold at lower prices, compressing the range against support. Sellers are in control, and a breakdown is the likely resolution.",
    },
    "symmetrical_triangle": {
        "name": "Symmetrical Triangle",
        "what": "A neutral continuation pattern with converging trendlines (lower highs and higher lows). The market is coiling — a big move is coming, but direction is uncertain.",
        "action": "Wait for a breakout in either direction with volume confirmation before taking a position.",
        "psychology": "Buyers and sellers are in equilibrium, but the narrowing range means a resolution is imminent. The breakout direction typically continues the prior trend.",
    },
    "rising_wedge": {
        "name": "Rising Wedge",
        "what": "A bearish reversal pattern where both support and resistance lines slope upward but converge. Despite prices rising, the momentum is weakening.",
        "action": "A break below the lower trendline is a sell signal. The target is typically the start of the wedge.",
        "psychology": "Price is rising but each advance is smaller than the last. Buyers are running out of steam, and when the wedge breaks down, it often leads to a sharp reversal.",
    },
    "falling_wedge": {
        "name": "Falling Wedge",
        "what": "A bullish reversal pattern where both support and resistance lines slope downward but converge. Despite prices falling, selling pressure is diminishing.",
        "action": "A break above the upper trendline is a buy signal. The target is typically the start of the wedge.",
        "psychology": "Price is falling but each decline is smaller. Sellers are losing conviction, and when the wedge breaks upward, pent-up buying often creates a sharp rally.",
    },
    "bull_flag": {
        "name": "Bull Flag",
        "what": "A bullish continuation pattern — a strong upward move (the pole) followed by a short, shallow pullback (the flag). The consolidation is a pause before the next leg up.",
        "action": "Pole gained {pole_return_pct:.1f}%. Target on breakout: ₹{target:.2f} (measured move equal to the pole).",
        "psychology": "After a strong rally, traders take partial profits causing a minor pullback. But the shallow pullback shows sellers can't push prices much lower — bulls are still in control.",
    },
    "bear_flag": {
        "name": "Bear Flag",
        "what": "A bearish continuation pattern — a sharp decline (the pole) followed by a brief consolidation (the flag). It's a pause before the next leg down.",
        "action": "Pole dropped {pole_return_pct:.1f}%. Target on breakdown: ₹{target:.2f}.",
        "psychology": "After a sharp sell-off, short-covering causes a minor bounce. But the weak bounce shows buyers can't push prices much higher — bears are still in control.",
    },
    "range_breakout_up": {
        "name": "Upward Range Breakout",
        "what": "Price has broken above the {lookback_days}-day trading range with {volume_ratio:.1f}x average volume. This is a significant move.",
        "action": "The breakout level ₹{range_high:.2f} now becomes support. Stay long as long as price holds above this level.",
        "psychology": "A breakout with high volume shows genuine institutional interest, not just retail noise. Volume confirms that real money is behind this move.",
    },
    "range_breakout_down": {
        "name": "Downward Range Breakdown",
        "what": "Price has broken below the {lookback_days}-day trading range with {volume_ratio:.1f}x average volume.",
        "action": "The breakdown level ₹{range_low:.2f} now becomes resistance. Avoid buying until price reclaims this level.",
        "psychology": "A breakdown with volume shows institutional selling pressure. The previous support has failed, and the next support level becomes the target.",
    },
    "52_week_high_breakout": {
        "name": "52-Week High Breakout",
        "what": "The stock has hit a new 52-week high! This is one of the strongest bullish signals in technical analysis.",
        "action": "52-week high breakouts have historically led to continuation in the same direction. The old high ₹{yearly_high:.2f} is now support.",
        "psychology": "New highs attract momentum traders and clear out overhead resistance (no sellers who bought higher are waiting to get out). It's clean air above.",
    },
    "52_week_low_breakdown": {
        "name": "52-Week Low Breakdown",
        "what": "The stock has hit a new 52-week low. This is a strong bearish signal indicating persistent selling pressure.",
        "action": "Avoid bottom-fishing. Wait for a clear reversal pattern before considering entry. The old low ₹{yearly_low:.2f} is now resistance.",
        "psychology": "New lows mean every buyer in the past year is underwater. This creates panic selling and margin calls, which can accelerate the decline.",
    },
    "golden_cross": {
        "name": "Golden Cross",
        "what": "The 50-day moving average just crossed above the 200-day moving average. This is a classic long-term bullish signal.",
        "action": "Golden crosses historically precede sustained uptrends. Consider accumulating on dips to the 50-day SMA.",
        "psychology": "The short-term trend is now decisively bullish relative to the long-term trend. Institutional investors often use this as a systematic buy signal.",
    },
    "death_cross": {
        "name": "Death Cross",
        "what": "The 50-day moving average just crossed below the 200-day moving average. This is a classic long-term bearish signal.",
        "action": "Death crosses historically precede sustained downtrends. Consider reducing positions or hedging.",
        "psychology": "The short-term trend has turned bearish relative to the long-term trend. Institutional investors often use this as a systematic sell signal.",
    },
    "bb_squeeze_release": {
        "name": "Bollinger Band Squeeze Release",
        "what": "Volatility has been contracting (Bollinger Bands squeezing inside Keltner Channels) and just released. A big move is starting.",
        "action": "Direction: {signal}. The squeeze lasted {squeeze_bars} bars — longer squeezes tend to produce bigger moves.",
        "psychology": "Markets alternate between low and high volatility. Extended calm periods (squeezes) are followed by explosive moves as pent-up energy releases.",
    },
    "bb_squeeze_active": {
        "name": "Bollinger Band Squeeze (Active)",
        "what": "Volatility is currently compressed — Bollinger Bands are squeezing inside Keltner Channels. An explosive move is building.",
        "action": "Prepare for a breakout in either direction. The squeeze has lasted {squeeze_bars} bars so far. Set alerts above and below the Bollinger Bands.",
        "psychology": "This is like a coiled spring. The longer the squeeze, the more powerful the eventual breakout. Be ready, but don't guess the direction.",
    },
    "rsi_overbought": {
        "name": "RSI Overbought",
        "what": "RSI is at {rsi:.1f} — well above 70. The stock is overbought, meaning the recent rally may be stretched too far.",
        "action": "This doesn't mean sell immediately — strong trends can stay overbought for weeks. But it's a caution flag. Avoid chasing at these levels.",
        "psychology": "RSI overbought means recent gains have been unusually large. While momentum can persist, mean reversion becomes increasingly likely.",
    },
    "rsi_oversold": {
        "name": "RSI Oversold",
        "what": "RSI is at {rsi:.1f} — below 30. The stock is oversold, meaning the recent decline may be overdone.",
        "action": "This could be a buying opportunity, especially if other signals (like support levels or bullish divergence) confirm. Look for reversal candles.",
        "psychology": "RSI oversold means recent losses have been unusually large. While the decline can continue, a bounce becomes increasingly likely.",
    },
    "bullish_divergence": {
        "name": "Bullish {indicator} Divergence",
        "what": "Price made a lower low, but {indicator} made a higher low. This disconnect suggests the downtrend is losing momentum — a potential reversal is brewing.",
        "action": "Bullish divergences are strongest at support levels. Wait for price confirmation (a higher close) before entering.",
        "psychology": "Even though price went lower, the indicator shows selling pressure is actually decreasing. Smart money may be accumulating while price drifts lower.",
    },
    "bearish_divergence": {
        "name": "Bearish {indicator} Divergence",
        "what": "Price made a higher high, but {indicator} made a lower high. The uptrend's internal momentum is weakening — potential reversal ahead.",
        "action": "Bearish divergences are strongest at resistance levels. Consider tightening stop-losses on long positions.",
        "psychology": "Despite new price highs, the indicator shows buying pressure is decreasing. The rally may be running on fumes.",
    },
    "resistance_breakout": {
        "name": "Resistance Level Breakout",
        "what": "Price has broken above a key resistance level at ₹{level:.2f} that was tested {strength} times. Volume is {volume_ratio:.1f}x the average.",
        "action": "The old resistance now becomes support. The breakout is more reliable with higher volume confirmation.",
        "psychology": "Multiple prior rejections at this level meant many sellers were waiting there. Breaking through clears this overhead supply.",
    },
    "support_breakdown": {
        "name": "Support Level Breakdown",
        "what": "Price has broken below a key support level at ₹{level:.2f} that held {strength} times before. Volume is {volume_ratio:.1f}x the average.",
        "action": "The old support now becomes resistance. Be cautious about buying until a clear recovery signal appears.",
        "psychology": "Multiple prior bounces at this level meant many buyers were defending it. The failure of this defense often triggers stop-loss selling.",
    },
}


def explain_pattern(pattern: Dict, backtest_stats: Optional[Dict] = None) -> str:
    """
    Generate a plain-English explanation for a detected pattern.
    Optionally enriches with backtest statistics.
    """
    pname = pattern.get("pattern", "")
    template = PATTERN_EXPLANATIONS.get(pname)

    if not template:
        return f"Pattern detected: {pname.replace('_', ' ').title()} (signal: {pattern.get('signal', 'N/A')})"

    # Format template with pattern data
    try:
        name = template["name"].format(**pattern)
        what = template["what"].format(**pattern)
        action = template["action"].format(**pattern)
        psychology = template["psychology"].format(**pattern)
    except (KeyError, ValueError):
        name = template["name"]
        what = template["what"]
        action = template["action"]
        psychology = template["psychology"]

    lines = [
        f"📊 {name}",
        f"",
        f"What's happening: {what}",
        f"",
        f"What to do: {action}",
        f"",
        f"Why it works: {psychology}",
    ]

    # Add backtest stats if available
    if backtest_stats:
        lines.append("")
        lines.append("📈 Historical Performance on This Stock:")
        total = backtest_stats.get("total_instances", 0)
        if total > 0:
            for h in [5, 10, 20]:
                sr = backtest_stats.get(f"{h}d_success_rate")
                avg = backtest_stats.get(f"{h}d_avg_return")
                if sr is not None:
                    lines.append(f"  • {h}-day: {sr}% success rate (avg return: {avg:+.2f}%) over {total} instances")
        else:
            lines.append("  • Not enough historical instances for reliable statistics.")

    return "\n".join(lines)


def explain_analysis(analysis: Dict, backtest_results: Optional[Dict] = None) -> str:
    """Generate a complete plain-English analysis report for a stock."""
    symbol = analysis.get("symbol", "Unknown")
    price = analysis.get("current_price", 0)
    patterns = analysis.get("patterns", [])
    sr = analysis.get("support_resistance", {})
    indicators = analysis.get("indicators", {})

    lines = [
        f"{'='*60}",
        f"  {symbol} — Technical Analysis Report",
        f"  Current Price: ₹{price:.2f}",
        f"{'='*60}",
        "",
    ]

    # Patterns
    if patterns:
        bullish = [p for p in patterns if p.get("signal") == "bullish"]
        bearish = [p for p in patterns if p.get("signal") == "bearish"]
        neutral = [p for p in patterns if p.get("signal") not in ("bullish", "bearish")]

        # Overall bias
        if len(bullish) > len(bearish):
            lines.append("🟢 OVERALL BIAS: BULLISH")
        elif len(bearish) > len(bullish):
            lines.append("🔴 OVERALL BIAS: BEARISH")
        else:
            lines.append("🟡 OVERALL BIAS: NEUTRAL")
        lines.append(f"   ({len(bullish)} bullish, {len(bearish)} bearish, {len(neutral)} neutral signals)")
        lines.append("")

        lines.append("─── DETECTED PATTERNS ───")
        lines.append("")

        for p in patterns:
            bt_stats = None
            if backtest_results and p["pattern"] in backtest_results.get("patterns", {}):
                bt_stats = backtest_results["patterns"][p["pattern"]]
            lines.append(explain_pattern(p, bt_stats))
            lines.append("")
    else:
        lines.append("No significant patterns detected at this time.")
        lines.append("")

    # Support / Resistance
    lines.append("─── SUPPORT & RESISTANCE ───")
    for s in sr.get("support", [])[:3]:
        lines.append(f"  Support: ₹{s['level']:.2f} (tested {s['touches']}x)")
    for r in sr.get("resistance", [])[:3]:
        lines.append(f"  Resistance: ₹{r['level']:.2f} (tested {r['touches']}x)")
    lines.append("")

    # Key Indicators
    lines.append("─── KEY INDICATORS ───")
    if indicators.get("rsi_14"):
        rsi_val = indicators["rsi_14"]
        rsi_label = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"
        lines.append(f"  RSI(14): {rsi_val:.1f} ({rsi_label})")
    if indicators.get("macd") is not None:
        macd_val = indicators["macd"]
        macd_sig = indicators.get("macd_signal", 0)
        label = "Bullish" if macd_val > macd_sig else "Bearish"
        lines.append(f"  MACD: {macd_val:.2f} / Signal: {macd_sig:.2f} ({label})")
    if indicators.get("adx"):
        adx_val = indicators["adx"]
        strength = "Strong" if adx_val > 25 else "Weak"
        lines.append(f"  ADX: {adx_val:.1f} (Trend {strength})")
    lines.append("")

    return "\n".join(lines)


async def llm_explain(pattern: Dict, stock_info: Dict = None,
                       provider: str = "anthropic") -> str:
    """
    Use an LLM to generate a richer, more contextual explanation.
    Falls back to template if no API key is configured.
    """
    api_key_env = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    api_key = os.getenv(api_key_env)

    if not api_key:
        return explain_pattern(pattern)

    prompt = f"""You are a friendly Indian stock market technical analyst explaining a chart pattern
to a retail investor who may not know technical analysis jargon.

Pattern detected: {pattern}
Stock info: {stock_info or 'Not available'}

Explain in 3-4 short paragraphs:
1. What the pattern is and what it looks like on a chart
2. What it historically means for the stock price
3. What the investor should consider doing (with appropriate disclaimers)

Use ₹ for prices. Be specific with numbers from the pattern data.
Keep it conversational and avoid jargon without explanation.
End with a brief disclaimer that this is technical analysis, not financial advice."""

    try:
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        else:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            return response.choices[0].message.content
    except Exception as e:
        print(f"[WARN] LLM explanation failed: {e}, using template")
        return explain_pattern(pattern)
