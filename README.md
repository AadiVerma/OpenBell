# OpenBell

LLM-powered next-day stock signal generator for Indian (NSE/BSE) and global markets.

Analyses price action, volume, RSI, and recent news for each watchlisted stock, then uses Claude to generate a structured **bullish / bearish / neutral** signal with confidence score, price targets, suggested entry price, and reasoning.

---

## Architecture

```
OpenBell/
├── Client/                    React + Vite + Tailwind frontend
│   └── src/
│       ├── api/index.js       All HTTP calls (single source of truth)
│       ├── components/        Navbar, SignalCard
│       └── pages/             Dashboard, Watchlist, Predict, History,
│                              Accuracy, Settings
│
└── Server/                    FastAPI backend
    └── app/
        ├── main.py            FastAPI app + lifespan
        ├── core/
        │   ├── config.py      Pydantic settings (.env + .settings.json overrides)
        │   └── database.py    SQLAlchemy async engine + session factory
        ├── models/            SQLAlchemy ORM models (Prediction, WatchlistStock)
        ├── schemas/           Pydantic request/response schemas
        ├── repositories/      All DB access — services never touch SQLAlchemy directly
        │   ├── prediction.py
        │   └── watchlist.py
        ├── ai/                AI layer — isolated from the rest of the app
        │   ├── client.py      Lazy Anthropic SDK singleton
        │   ├── tools.py       Tool definition (structured output schema)
        │   ├── prompts.py     Prompt builders (token-optimised)
        │   └── analyzer.py    analyze_stock() entry point
        ├── services/
        │   ├── orchestrator.py  Background analysis job (BackgroundTasks, no threads)
        │   ├── market_data.py   yfinance wrapper
        │   ├── news.py          Google News RSS + Finnhub
        │   ├── report.py        WhatsApp message builder
        │   ├── excel.py         Excel workbook generation
        │   ├── notification.py  Twilio WhatsApp sender
        │   └── seed.py          NSE index CSV fetcher
        └── routers/
            ├── watchlist.py     /watchlist/*
            ├── predictions.py   /predictions/*
            └── settings.py      /settings/*
```

---

## Token Optimisation

The original implementation called Claude via subprocess (`claude` CLI) with a verbose prompt that embedded the full JSON schema on every call. This approach wasted roughly 300–400 tokens per prediction on schema description alone, and another 200–300 on verbose market data formatting.

The rewrite does three things:

1. **Anthropic SDK + `tool_use`** — The JSON schema lives in `app/ai/tools.py` as a tool definition. Claude is forced to call `submit_prediction`, guaranteeing structured output with no parsing needed. The schema is sent as a tool spec, not as prompt text.

2. **Compressed market data** — `app/ai/prompts.py` converts the raw market data dict into a compact block:
   ```
   TICKER: RELIANCE.NS
   PRICE: 2847.50 (+0.42%)
   VOL: 1.2x avg | RSI14: 58.3
   52W: 2340.00/3200.00 (pos: 62%)
   PE: 24.5 | SECTOR: Energy
   NEWS:
   1. JIO announces 5G expansion [2h]
   2. Quarterly results inline [1d]
   ```
   This is ~150 tokens vs ~700 tokens in the original (~78% reduction).

3. **Haiku by default** — `ANTHROPIC_MODEL=claude-haiku-4-5-20251001` is cheap and fast for structured extraction. Change to `claude-sonnet-4-6` in `.env` for higher reasoning quality.

---

## Setup

### Prerequisites

- Python 3.12+
- Node 20+
- PostgreSQL
- Claude access — either:
  - `claude` CLI installed and logged in (Claude Code subscription) — **no API key needed**
  - Or an Anthropic API key (more token-efficient via SDK + tool_use)

### Backend

```bash
cd Server

# Copy and fill in your credentials
cp .env.example .env

# Install dependencies (uv recommended)
uv sync
# or: pip install -e .

# Start the server
uvicorn app.main:app --reload --port 8000
```

The server auto-creates database tables on first startup.

### Frontend

```bash
cd Client
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to FastAPI on port 8000.

---

## Configuration

All settings live in `Server/.env`. A subset can also be changed at runtime through the **Settings** page in the UI — these overrides are written to `Server/.settings.json` (gitignored).

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async URL | `postgresql+asyncpg://...` |
| `ANTHROPIC_API_KEY` | Optional — leave blank to use `claude` CLI instead | — |
| `ANTHROPIC_MODEL` | Claude model (SDK path only) | `claude-haiku-4-5-20251001` |
| `FINNHUB_API_KEY` | Optional, for non-Indian stocks | — |
| `TWILIO_ACCOUNT_SID` | WhatsApp reports | — |
| `TWILIO_AUTH_TOKEN` | WhatsApp reports | — |
| `TWILIO_FROM_NUMBER` | Twilio sandbox number | `whatsapp:+14155238886` |
| `WHATSAPP_TO` | Your WhatsApp number | — |
| `WHATSAPP_ENABLED` | Auto-send after analysis | `false` |
| `PORTFOLIO_BUDGET` | Budget for position sizing (₹) | `10000.0` |

---

## API Reference

All routes are prefixed with `/api` by the Vite proxy (internally no prefix).

### Watchlist

| Method | Path | Description |
|---|---|---|
| `GET` | `/watchlist/stocks` | List watchlisted stocks |
| `POST` | `/watchlist/stocks` | Add stock `{ticker, name, exchange}` |
| `DELETE` | `/watchlist/stocks/{ticker}` | Remove a stock |
| `DELETE` | `/watchlist/stocks` | Clear entire watchlist |
| `POST` | `/watchlist/seed?index=NIFTY50` | Bulk-seed from NSE index |
| `GET` | `/watchlist/signals` | Today's predictions |
| `POST` | `/watchlist/run?force=false` | Start analysis in background |
| `GET` | `/watchlist/run/status` | Poll analysis progress |

Supported indices: `NIFTY50`, `NIFTYNEXT50`, `NIFTY100`, `NIFTY200`, `NIFTY500`, `NIFTYIT`, `NIFTYBANK`, `NIFTYREIT`

### Predictions

| Method | Path | Description |
|---|---|---|
| `POST` | `/predictions/predict` | Ad-hoc single-stock prediction |
| `GET` | `/predictions/history` | Past predictions (filterable by ticker) |
| `GET` | `/predictions/accuracy` | Accuracy stats |
| `POST` | `/predictions/outcome` | Record next-day actual close |
| `POST` | `/predictions/verify?date=YYYY-MM-DD` | Auto-verify via yfinance |
| `GET` | `/predictions/backtest?days=14` | Verified predictions with deltas |
| `GET` | `/predictions/news/{ticker}` | Fetch latest news |
| `GET` | `/predictions/report.xlsx?date=YYYY-MM-DD` | Download Excel report |

### Settings

| Method | Path | Description |
|---|---|---|
| `GET` | `/settings/` | Read current settings (credentials masked) |
| `PATCH` | `/settings/` | Update mutable settings |
| `POST` | `/settings/test-whatsapp` | Send a test WhatsApp message |
| `POST` | `/settings/send-report` | Send today's report via WhatsApp |

---

## Data Flow

### Daily Analysis
1. User clicks **Run Analysis** → `POST /watchlist/run`
2. FastAPI schedules `run_analysis()` as a BackgroundTask
3. For each watchlisted stock:
   - Fetch 30-day OHLCV + fundamentals (yfinance, thread pool)
   - Fetch 5 recent news articles (Google News / Finnhub, thread pool)
   - Call Claude with compressed data + forced tool_use
   - Save structured prediction to PostgreSQL
4. Optionally auto-send WhatsApp report
5. Frontend polls `/watchlist/run/status` every 3 seconds

### Outcome Tracking
- Next day: enter actual close price in History page
- System calculates direction correctness:
  - `up`: actual change > +0.2%
  - `down`: actual change < -0.2%
  - `neutral`: actual change within ±0.5%
- Or use **Verify** to auto-fetch closing prices from yfinance

### Position Sizing
Budget is allocated by confidence tier:

| Confidence | % of Budget |
|---|---|
| ≥ 80% | 15% |
| 70–79% | 10% |
| 60–69% | 7% |
| < 60% | 5% |

---

## Scaling / Extending

**Improve prediction quality:**
- Switch `ANTHROPIC_MODEL` to `claude-sonnet-4-6` in `.env`
- Add more data fields to `app/ai/prompts.py::build_user_message()` (e.g., moving average crossovers, sector PE)
- Add earnings date proximity warning

**Add more data sources:**
- Extend `app/services/market_data.py` to include additional technical indicators
- Add FII/DII flow data for Indian stocks
- Add options OI data

**Batch predictions** (advanced):
- The AI layer in `app/ai/` is isolated — you can modify `analyzer.py` to batch multiple stocks in one API call using multi-turn messages

**Production deployment:**
- Tighten `allow_origins` in `app/main.py`
- Add Alembic migrations instead of `create_all`
- Add authentication to the settings endpoints
- Use environment-specific `.env.production`

---

## Disclaimer

OpenBell generates AI-powered signals for informational purposes only. It is **not financial advice**. Always do your own research before making investment decisions.
