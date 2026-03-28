# Chart Pattern Intelligence (CPI)

**Real-time technical pattern detection across the NSE universe with plain-English explanations and historical back-tested success rates.**

Built for the **ET AI Hackathon 2026** — Problem Statement #6: *AI for the Indian Investor*

---

## What It Does

Chart Pattern Intelligence (CPI) is an AI-powered system that:

1. **Detects Chart Patterns in Real-Time** — Scans NSE stocks for breakouts, reversals, support/resistance levels, and divergences using algorithmic pattern recognition.
2. **Explains in Plain English** — Every detected pattern comes with a human-readable explanation: what the pattern means, why it matters, and what typically happens next.
3. **Back-Tests Success Rates** — For every pattern detected on a specific stock, CPI runs historical back-tests showing how often that pattern led to the expected outcome *on that exact stock*.
4. **Multi-Source Sentiment Layer** — Integrates news sentiment (ET, Moneycontrol) and social signals (Reddit, Twitter/X) to validate or challenge technical signals.
5. **Conversational Interface** — Ask questions like *"Show me breakout candidates today"* or *"Is Tata Motors forming a head and shoulders?"*

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (Streamlit)               │
│  Dashboard │ Pattern Scanner │ Stock Deep-Dive │ Chat│
└──────────────────────┬──────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────┐
│                  FastAPI Backend                      │
│  /scan  │  /analyze/{symbol}  │  /backtest  │  /chat │
└──────┬────────┬──────────┬──────────┬───────────────┘
       │        │          │          │
┌──────▼──┐ ┌──▼────┐ ┌───▼────┐ ┌───▼──────┐
│ Pattern │ │ Back  │ │Senti-  │ │ LLM      │
│ Engine  │ │ Test  │ │ment    │ │ Explain  │
│         │ │Engine │ │Engine  │ │ Engine   │
└──────┬──┘ └──┬────┘ └───┬────┘ └───┬──────┘
       │        │          │          │
┌──────▼────────▼──────────▼──────────▼───────────────┐
│              Data Layer (yfinance + APIs)             │
│    NSE/BSE Price Data │ News APIs │ Social APIs       │
└─────────────────────────────────────────────────────┘
```

### Detected Patterns

| Category | Patterns |
|----------|----------|
| **Reversal** | Head & Shoulders, Inverse H&S, Double Top, Double Bottom, Triple Top/Bottom |
| **Continuation** | Ascending/Descending/Symmetrical Triangle, Rising/Falling Wedge, Bull/Bear Flag |
| **Breakout** | Volume Breakout, Range Breakout, 52-Week High/Low Breakout |
| **Support/Resistance** | Dynamic S/R Levels, Fibonacci Retracement, Pivot Points |
| **Divergence** | RSI Bullish/Bearish Divergence, MACD Divergence, OBV Divergence |
| **Momentum** | Golden/Death Cross, RSI Overbought/Oversold, Bollinger Band Squeeze |

---

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/chart-pattern-intelligence.git
cd chart-pattern-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (optional, for full features)
cp .env.example .env
# Edit .env with your API keys (OpenAI/Anthropic for explanations, NewsAPI, etc.)
```

### Run the Application

```bash
# Option 1: Run the full stack (API + Dashboard)
python run.py

# Option 2: Run components separately
# Terminal 1 — API Server
uvicorn app.api.server:app --reload --port 8000

# Terminal 2 — Streamlit Dashboard
streamlit run frontend/dashboard.py --server.port 8501
```

### Quick Test (No API keys needed)

```bash
# Run pattern detection on a single stock
python -m app.cli analyze RELIANCE.NS --days 365

# Scan Nifty 50 for patterns
python -m app.cli scan --index nifty50

# Backtest a pattern on a stock
python -m app.cli backtest TATAMOTORS.NS --pattern double_bottom --years 5
```

---

## Project Structure

```
chart-pattern-intelligence/
├── app/
│   ├── __init__.py
│   ├── cli.py                  # Command-line interface
│   ├── core/
│   │   ├── __init__.py
│   │   ├── patterns.py         # Pattern detection algorithms
│   │   ├── backtester.py       # Historical backtesting engine
│   │   ├── indicators.py       # Technical indicators (RSI, MACD, BB, etc.)
│   │   ├── support_resistance.py  # S/R level detection
│   │   └── divergence.py       # Divergence detection (RSI, MACD, OBV)
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py           # FastAPI endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── data_fetcher.py     # Market data fetching
│   │   ├── explainer.py        # Plain-English explanation generator
│   │   ├── sentiment.py        # News/social sentiment (optional)
│   │   └── nse_symbols.py      # NSE stock universe
├── frontend/
│   └── dashboard.py            # Streamlit dashboard
├── tests/
│   ├── test_patterns.py
│   └── test_backtester.py
├── docs/
│   └── architecture.md         # Architecture document
├── data/                       # Cached data (auto-created)
├── .env.example
├── requirements.txt
├── run.py                      # Launcher script
└── README.md
```

---

## API Reference

### `GET /api/scan`
Scan stocks for active patterns.

```bash
curl "http://localhost:8000/api/scan?index=nifty50&pattern_type=reversal"
```

### `GET /api/analyze/{symbol}`
Deep analysis of a single stock.

```bash
curl "http://localhost:8000/api/analyze/RELIANCE.NS"
```

### `GET /api/backtest/{symbol}`
Backtest a pattern on a specific stock.

```bash
curl "http://localhost:8000/api/backtest/TATAMOTORS.NS?pattern=double_bottom&years=5"
```

### `POST /api/chat`
Conversational interface.

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me breakout candidates today"}'
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Impact Model

| Metric | Estimate |
|--------|----------|
| **Time Saved** | 3-4 hours/day per investor (manual chart analysis → automated) |
| **Addressable Market** | 14 crore+ demat accounts; ~20M active traders |
| **Pattern Accuracy** | 55-65% directional accuracy (back-tested) |
| **Cost vs Alternatives** | ₹99-499/month vs ₹20L+/year (Bloomberg) |
| **Potential Revenue** | ₹6-20 Cr/year at scale (100K-500K users) |

**Assumptions**: Based on SEBI data showing 93% of retail F&O traders lost ₹1.8L crores (FY22-24). Even a 5% improvement in decision quality across 100K users represents significant value.

---

## Tech Stack

- **Backend**: Python, FastAPI, NumPy, Pandas, SciPy
- **Data**: yfinance, NSEpy
- **Pattern Detection**: Custom algorithms + TA-Lib
- **Explanations**: GPT-4 / Claude API (configurable)
- **Frontend**: Streamlit + Plotly
- **Sentiment**: FinBERT (optional module)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Team

Built for the ET AI Hackathon 2026 by Sejal :).
