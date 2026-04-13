# TradingAgents India — Live Trading Platform Roadmap

---

## 1. What We Have Right Now

### Core Framework (Open Source)
- **13-agent LLM pipeline** via LangGraph: Market Analyst → Social Analyst → News Analyst → Fundamentals Analyst → India Macro Analyst → Bull/Bear Debate → Research Manager → Trader → Risk Debate (Aggressive/Conservative/Neutral) → Portfolio Manager
- **5 decision ratings**: BUY / OVERWEIGHT / HOLD / UNDERWEIGHT / SELL
- **Data via yfinance**: price/volume, technical indicators (RSI, MACD, Bollinger, SMA, EMA, ATR, VWMA, MFI), fundamentals (P/E, balance sheet, cashflow, income), company news
- **BM25 memory system**: agents learn from past situations via [reflect_and_remember()](file:///d:/TradingAgents/tradingagents/graph/trading_graph.py#277-294)
- **Multi-LLM support**: OpenAI, Anthropic, Google, Ollama, OpenRouter, xAI

### Our Customisations (Done ✅)
| Change | Files Modified |
|---|---|
| India-specific global news queries (RBI, FII/DII, Nifty) | [yfinance_news.py](file:///d:/TradingAgents/tradingagents/dataflows/yfinance_news.py) |
| `.NS`/`.BO` exchange suffix support | [agent_utils.py](file:///d:/TradingAgents/tradingagents/agents/utils/agent_utils.py) |
| **India Macro Analyst** — new 5th analyst (RBI, FII/DII, INR/USD, govt policy, GDP) | [india_macro_analyst.py](file:///d:/TradingAgents/tradingagents/agents/analysts/india_macro_analyst.py) + 6 wiring files |
| Indian trading rules in risk debates (circuit limits, T+1, SEBI margin, FII/DII, promoter pledging) | [aggressive_debator.py](file:///d:/TradingAgents/tradingagents/agents/risk_mgmt/aggressive_debator.py), [conservative_debator.py](file:///d:/TradingAgents/tradingagents/agents/risk_mgmt/conservative_debator.py), [neutral_debator.py](file:///d:/TradingAgents/tradingagents/agents/risk_mgmt/neutral_debator.py) |
| **React Dashboard** — B&W palette, SSE live progress stepper, expandable report accordion | [api_server.py](file:///d:/TradingAgents/api_server.py), [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx), [index.css](file:///d:/TradingAgents/frontend/src/index.css) |

### Current Limitations
- ❌ One stock at a time — manual ticker entry
- ❌ Manual date entry — no auto-today
- ❌ No watchlist or portfolio view
- ❌ No pre-screening — runs full LLM pipeline on every request (~₹2-5 per run, ~2 min)
- ❌ No scheduled/automatic scanning
- ❌ No prediction history or accuracy tracking
- ❌ No alerts or notifications
- ❌ No intraday data (yfinance = end-of-day only)

---

## 2. What We Are Going to Build

### Phase 1: Smart Watchlist + Auto-Date ⏱️ ~2 hours

**Goal**: Analyse multiple stocks with one click, auto-fill today's date.

| Task | Details |
|---|---|
| Add watchlist to UI | Predefined lists (Nifty 50, Bank Nifty, user custom) + add/remove tickers |
| Auto-date toggle | Default to today's date, option to override |
| Backend batch endpoint | `POST /api/analyze/batch` accepts a list of tickers, runs them sequentially, streams progress per ticker |
| UI: batch progress | Show which ticker is being analysed (e.g., "Analysing 3/10: TCS.NS") |

**Files to create/modify**:
- [api_server.py](file:///d:/TradingAgents/api_server.py) — new batch SSE endpoint
- [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx) — watchlist UI component, auto-date
- New: `watchlists.json` — predefined Nifty 50 / Bank Nifty ticker lists

---

### Phase 2: Pre-Screening Filter ⏱️ ~3-4 hours

**Goal**: Don't waste ₹₹₹ running LLMs on boring stocks. Quickly scan all watchlist stocks using cheap technical indicators, then only run the full agent pipeline on "interesting" ones.

| Task | Details |
|---|---|
| Build a screener function | Uses yfinance to quickly pull RSI, volume change, price change for all tickers in the watchlist |
| Define screening rules | Flag stocks with: RSI < 30 or > 70, volume spike > 2x average, price change > ±3% in last session, near 52-week high/low |
| UI: screening results table | Show all stocks with their screening scores, highlight flagged ones |
| One-click deep analysis | Click a flagged stock → triggers the full agent pipeline |

**Files to create/modify**:
- New: `tradingagents/dataflows/screener.py` — fast bulk screening via yfinance
- [api_server.py](file:///d:/TradingAgents/api_server.py) — new `GET /api/screen` endpoint
- [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx) — screener results table component

---

### Phase 3: Multi-Stock Dashboard ⏱️ ~3-4 hours

**Goal**: Show a table view of all analysed stocks with their BUY/SELL/HOLD ratings, sortable and filterable.

| Task | Details |
|---|---|
| Results table UI | Columns: Ticker, Decision, Confidence, Date, Key Reason (one-liner) |
| Expandable row detail | Click a row → expand to see all agent reports (like current accordion) |
| Sort & filter | Sort by decision type, date; filter by BUY only / SELL only |
| Persist results | Save analysis results to a local JSON/SQLite so they survive page refresh |

**Files to create/modify**:
- [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx) — major UI overhaul (table + detail view)
- [api_server.py](file:///d:/TradingAgents/api_server.py) — persist results to `results/` directory, add `GET /api/results` endpoint
- [index.css](file:///d:/TradingAgents/frontend/src/index.css) — table styles

---

### Phase 4: Scheduled Scanning ⏱️ ~2-3 hours

**Goal**: The agent automatically scans your watchlist every morning before market opens (e.g., 8:30 AM IST).

| Task | Details |
|---|---|
| Background scheduler | Use `APScheduler` or a simple `asyncio` loop in the backend |
| Pre-market scan | At 8:30 AM: run Phase 2 screener → run Phase 1 pipeline on flagged stocks |
| Store results | Save to SQLite/JSON with timestamp |
| UI: "Morning Report" view | Show today's pre-market scan results as a dashboard card |
| Config | Set scan time, watchlist, and screening thresholds in `config.json` |

**Files to create/modify**:
- [api_server.py](file:///d:/TradingAgents/api_server.py) — add scheduler integration
- New: `scheduler.py` — background scanning loop
- New: `config.json` — scheduler settings

---

### Phase 5: Prediction Tracking & Accuracy ⏱️ ~3-4 hours

**Goal**: Track every prediction and compare with actual price movement to measure agent accuracy.

| Task | Details |
|---|---|
| Prediction database | SQLite table: [(id, ticker, date, decision, price_at_prediction, reports_json)](file:///d:/TradingAgents/frontend/src/App.tsx#44-229) |
| Outcome tracker | Daily job: for predictions older than N days, fetch current price and compute returns |
| Accuracy dashboard | Show win rate, avg return, per-agent accuracy breakdown |
| Memory integration | Feed actual outcomes back into [reflect_and_remember()](file:///d:/TradingAgents/tradingagents/graph/trading_graph.py#277-294) to improve the agents over time |

**Files to create/modify**:
- New: `database.py` — SQLite wrapper for predictions
- [api_server.py](file:///d:/TradingAgents/api_server.py) — save predictions, expose `GET /api/predictions` endpoint
- [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx) — accuracy dashboard component

---

### Phase 6: Alerts & Notifications ⏱️ ~2-3 hours

**Goal**: Get notified instantly when a strong signal is found.

| Task | Details |
|---|---|
| Telegram bot | Send BUY/SELL alerts to a Telegram channel via Bot API |
| Email alerts (optional) | SMTP-based email notifications |
| Alert rules | Only alert on strong BUY or SELL (not HOLD), configurable threshold |
| UI: notification bell | In-app notification panel showing recent alerts |

**Files to create/modify**:
- New: `alerts/telegram_bot.py`
- New: `alerts/email_sender.py`
- [api_server.py](file:///d:/TradingAgents/api_server.py) — trigger alerts after analysis
- [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx) — notification bell component

---

### Phase 7: Live/Intraday Data (Advanced) ⏱️ ~5+ hours

**Goal**: Move beyond end-of-day data for intraday trading signals.

| Option | Pros | Cons |
|---|---|---|
| **Breeze API** (ICICI Direct) | Real-time Indian market data, free with demat account | Requires ICICI demat |
| **Kite Connect** (Zerodha) | Best Indian broker API, excellent docs | ₹2000/month subscription |
| **Upstox API** | Free tier available, decent coverage | Limited historical data |
| **Angel One SmartAPI** | Free, good for real-time data | Rate limits |

This phase would add a new data vendor in `dataflows/` alongside yfinance.

---

## 3. Architecture Overview (Target State)

```
┌─────────────────────────────────────────────────────────┐
│                    React Dashboard                       │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐ │
│  │Watchlist  │ │ Screener   │ │ Results  │ │ Accuracy │ │
│  │Manager   │ │ Table      │ │ Table    │ │Dashboard │ │
│  └──────────┘ └────────────┘ └──────────┘ └──────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ SSE / REST
┌────────────────────────┴────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐ │
│  │Scheduler │ │  Screener  │ │ Agent    │ │  Alerts  │ │
│  │(8:30 AM) │ │  (RSI/Vol) │ │ Pipeline │ │(Telegram)│ │
│  └──────────┘ └────────────┘ └──────────┘ └──────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │              SQLite (Predictions DB)                │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│              TradingAgents Core (LangGraph)              │
│  Market → Social → News → Fundamentals → India Macro    │
│  → Bull/Bear Debate → Research Manager → Trader         │
│  → Risk Debate (w/ Indian rules) → Portfolio Manager    │
└─────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                    Data Sources                          │
│  yfinance (free) │ Kite/Breeze (live) │ LLM (OpenAI)   │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Build Priority

| Phase | Effort | Value | Build? |
|---|---|---|---|
| 1. Watchlist + Auto-date | 2h | 🔴 Essential | First |
| 2. Pre-screening Filter | 3-4h | 🔴 Essential (saves cost) | Second |
| 3. Multi-stock Dashboard | 3-4h | 🔴 Essential | Third |
| 4. Scheduled Scanning | 2-3h | 🟡 High | Fourth |
| 5. Prediction Tracking | 3-4h | 🟡 High | Fifth |
| 6. Alerts (Telegram) | 2-3h | 🟢 Nice to have | Sixth |
| 7. Live Data (Broker API) | 5+h | 🟢 Advanced | Later |

**Total estimated effort**: ~20-25 hours for Phases 1-6
