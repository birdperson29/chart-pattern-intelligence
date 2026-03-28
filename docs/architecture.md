# Architecture Document — Chart Pattern Intelligence

## System Overview

Chart Pattern Intelligence (CPI) is a multi-agent AI system that performs real-time technical chart pattern detection across the NSE stock universe, provides plain-English explanations, and delivers historically back-tested success rates for every detected pattern on every specific stock.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Dashboard │  │Pattern Scanner│  │ Backtester│  │Chat Agent │  │
│  │(Streamlit)│  │  (Scan tab)  │  │  (BT tab) │  │(NLP tab)  │  │
│  └─────┬─────┘  └──────┬───────┘  └─────┬─────┘  └─────┬─────┘  │
└────────┼────────────────┼────────────────┼──────────────┼────────┘
         │                │                │              │
         ▼                ▼                ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI REST API                             │
│  GET /api/analyze/{sym} │ GET /api/scan │ GET /api/backtest │ POST /api/chat │
└────────┬────────────────┬────────────────┬──────────────┬────────┘
         │                │                │              │
    ┌────▼────┐      ┌────▼────┐      ┌───▼────┐    ┌───▼──────┐
    │ Pattern │      │ Pattern │      │ Back-  │    │ Explain  │
    │ Engine  │      │ Scanner │      │ tester │    │ Engine   │
    │(Single) │      │(Multi)  │      │        │    │(LLM/Tmpl)│
    └────┬────┘      └────┬────┘      └───┬────┘    └───┬──────┘
         │                │                │              │
         └───────────┬────┴────────────────┘              │
                     │                                    │
              ┌──────▼──────┐                       ┌─────▼─────┐
              │   Core      │                       │ Explainer │
              │   Engine    │                       │ Module    │
              │             │                       │           │
              │ ┌─────────┐ │                       │ Templates │
              │ │Reversal │ │                       │ + LLM API │
              │ │Detector │ │                       └───────────┘
              │ ├─────────┤ │
              │ │Continue │ │
              │ │Detector │ │
              │ ├─────────┤ │
              │ │Breakout │ │
              │ │Detector │ │
              │ ├─────────┤ │
              │ │Momentum │ │
              │ │Detector │ │
              │ ├─────────┤ │
              │ │Divergnce│ │
              │ │Detector │ │
              │ ├─────────┤ │
              │ │  S/R    │ │
              │ │Detector │ │
              │ └─────────┘ │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │  Data Layer │
              │             │
              │  yfinance   │
              │  (NSE/BSE)  │
              │  + Cache    │
              └─────────────┘
```

---

## Agent Roles

### 1. Pattern Detection Agent
**Role**: Runs 6 categories of pattern detectors across OHLCV data.

**Sub-agents**:
- **Reversal Detector**: Head & Shoulders, Inverse H&S, Double Top/Bottom
- **Continuation Detector**: Ascending/Descending/Symmetrical Triangle, Rising/Falling Wedge, Bull/Bear Flag
- **Breakout Detector**: Range breakout, 52-week high/low breakout (volume-confirmed)
- **Momentum Detector**: Golden/Death Cross, Bollinger Band Squeeze, RSI extremes
- **Divergence Detector**: RSI, MACD, OBV bullish/bearish divergences
- **S/R Detector**: Swing-point clustering, Fibonacci retracement, Pivot points

**Communication**: Each sub-agent receives the same OHLCV DataFrame and returns a list of detected patterns with metadata (confidence score, signal direction, key price levels).

### 2. Backtesting Agent
**Role**: Validates pattern signals by running historical analysis.

**Process**:
1. Slides a rolling window across 5 years of data
2. At each step, runs pattern detection
3. Computes 5/10/20-day forward returns from each detection
4. Aggregates success rates per pattern per stock
5. Deduplicates nearby detections (within 10 bars)

**Output**: Per-pattern statistics — success rate, average return, best/worst case.

### 3. Explanation Agent
**Role**: Translates technical patterns into plain English.

**Two modes**:
- **Template mode** (default, no API key needed): 20+ pre-written explanation templates with dynamic variable injection (price levels, confidence, targets)
- **LLM mode** (optional): Sends pattern data to Claude/GPT-4 for richer, contextual explanations

### 4. Data Agent
**Role**: Fetches and caches market data.

**Features**:
- yfinance integration for NSE/BSE OHLCV data
- In-memory TTL cache (15-minute) to avoid redundant API calls
- Symbol normalization (.NS suffix handling)
- Index-level symbol lists (Nifty 50, 100, 200)

---

## Tool Integrations

| Tool | Purpose | Required? |
|------|---------|-----------|
| yfinance | OHLCV price data from NSE/BSE | Yes |
| NumPy/SciPy | Signal processing, swing point detection | Yes |
| Pandas | Data manipulation | Yes |
| FastAPI | REST API server | Yes |
| Streamlit | Dashboard UI | Yes |
| Plotly | Interactive charts | Yes |
| Claude/GPT-4 API | Enhanced explanations | Optional |
| NewsAPI | Sentiment data | Optional |

---

## Error Handling

| Error Type | Handling |
|------------|----------|
| Data fetch failure | Returns None; scanner skips stock; API returns 404 |
| Pattern detection crash | Try/catch per detector; failed detectors logged but don't block others |
| Backtest insufficient data | Returns message "No instances found" |
| LLM API failure | Falls back to template-based explanation |
| Invalid symbol | Normalized with .NS suffix; validated against symbol list |

---

## Data Flow

```
User Request → API Endpoint → Data Fetch (+ cache check)
    → Pattern Detection (all 6 sub-agents run in parallel conceptually)
    → [Optional] Backtest on 5yr historical data
    → [Optional] Sentiment fetch from news APIs
    → Explanation generation (template or LLM)
    → JSON response with patterns, S/R levels, indicators, explanation
    → Frontend renders: chart, pattern cards, backtest stats, S/R levels
```

---

## Scalability Considerations

- **Caching**: TTL-based in-memory cache reduces API calls by ~80% during active scanning
- **Batch scanning**: Nifty 50 scan completes in ~2-3 minutes (limited by yfinance rate limits)
- **Modular detectors**: New pattern types can be added without modifying existing code
- **API-first design**: Frontend and backend are decoupled; mobile/WhatsApp clients can consume the same API
