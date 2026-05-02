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

| Change | Files |
|---|---|
| India-specific global news queries (RBI, FII/DII, Nifty) | [yfinance_news.py](file:///d:/TradingAgents/tradingagents/dataflows/yfinance_news.py) |
| `.NS`/`.BO` exchange suffix support | [agent_utils.py](file:///d:/TradingAgents/tradingagents/agents/utils/agent_utils.py) |
| **India Macro Analyst** — new 5th analyst (RBI, FII/DII, INR/USD, govt policy, GDP) | [india_macro_analyst.py](file:///d:/TradingAgents/tradingagents/agents/analysts/india_macro_analyst.py) + 6 wiring files |
| Indian trading rules in risk debates (circuit limits, T+1, SEBI margin, FII/DII, promoter pledging) | [aggressive_debator.py](file:///d:/TradingAgents/tradingagents/agents/risk_mgmt/aggressive_debator.py), [conservative_debator.py](file:///d:/TradingAgents/tradingagents/agents/risk_mgmt/conservative_debator.py), [neutral_debator.py](file:///d:/TradingAgents/tradingagents/agents/risk_mgmt/neutral_debator.py) |
| **NSE Index Screener** — hardcoded Nifty 50 / Bank Nifty / IT / Pharma / Auto constituent lists, parallel yfinance fetch, price-change & 52-week proximity flagging | [nse_api.py](file:///d:/TradingAgents/tradingagents/dataflows/nse_api.py) |
| **React Dashboard (v2)** — B&W palette, 3-view routing (Screener / Analysis / Results), SSE live progress stepper, expandable report accordion | See component list below |
| **FastAPI Backend** — SSE streaming endpoint, NSE watchlist & screener endpoints | [api_server.py](file:///d:/TradingAgents/api_server.py) |

### Frontend Component Architecture (Done ✅)

| Component | Purpose | File |
|---|---|---|
| `TopNav` | Site-wide nav bar — Screener / Results tabs | [TopNav.tsx](file:///d:/TradingAgents/frontend/src/components/TopNav.tsx) |
| `ScreenerView` | Index selector, scan button, stock table | [ScreenerView.tsx](file:///d:/TradingAgents/frontend/src/components/ScreenerView.tsx) |
| `StockTable` | Sortable table of scanned stocks with flag badges + "Analyse" button | [StockTable.tsx](file:///d:/TradingAgents/frontend/src/components/StockTable.tsx) |
| `AnalysisView` | Full-screen AI analysis with live pipeline stepper | [AnalysisView.tsx](file:///d:/TradingAgents/frontend/src/components/AnalysisView.tsx) |
| `AgentPipeline` | 13-step progress indicator (dots/checkmarks) | [AgentPipeline.tsx](file:///d:/TradingAgents/frontend/src/components/AgentPipeline.tsx) |
| `ReportAccordion` | Expandable agent report sections | [ReportAccordion.tsx](file:///d:/TradingAgents/frontend/src/components/ReportAccordion.tsx) |
| `DecisionBadge` | Coloured BUY/SELL/HOLD pill | [DecisionBadge.tsx](file:///d:/TradingAgents/frontend/src/components/DecisionBadge.tsx) |
| `ResultsView` | Past analysis history table with filters + expandable rows | [ResultsView.tsx](file:///d:/TradingAgents/frontend/src/components/ResultsView.tsx) |
| `types.ts` | Shared TypeScript interfaces & pipeline constants | [types.ts](file:///d:/TradingAgents/frontend/src/types.ts) |

### Backend API Endpoints

| Method | Route | Status |
|---|---|---|
| `GET` | `/api/indices` | ✅ Working |
| `GET` | `/api/watchlist?index=NIFTY 50` | ✅ Working |
| `GET` | `/api/screen?index=NIFTY 50` | ✅ Working |
| `GET` | `/api/analyze/stream?ticker=X&date=Y` | ✅ Working (SSE) |
| `POST` | `/api/analyze` | ✅ Working (fallback) |
| `GET` | `/api/results` | ✅ Working |
| `GET` | `/api/watchlist/custom` | ✅ Working — returns `watchlists.json` |
| `POST` | `/api/watchlist/custom` | ✅ Working — adds ticker, persists to `watchlists.json` |
| `DELETE` | `/api/watchlist/custom/{ticker}` | ✅ Working — removes ticker |
| `POST` | `/api/analyze/batch` | ✅ Working (SSE) — streams per-ticker progress |

### Result File Format (saved by `_log_state()`)

Results are saved to `results/<TICKER>/TradingAgentsStrategy_logs/full_states_log_<DATE>.json` with this schema:
```
{
  "company_of_interest": "RELIANCE.NS",
  "trade_date": "2024-05-10",
  "market_report": "...",
  "sentiment_report": "...",
  "news_report": "...",
  "fundamentals_report": "...",
  "investment_debate_state": { "bull_history", "bear_history", "judge_decision" },
  "trader_investment_decision": "...",
  "risk_debate_state": { "aggressive_history", "conservative_history", "neutral_history", "judge_decision" },
  "investment_plan": "...",
  "final_trade_decision": "..."
}
```

### Current Limitations
- ✅ ~~No `GET /api/results` endpoint~~ — now implemented, reads from `results/` directory
- ✅ ~~Screener only checks price % change and 52-week proximity~~ — `tradingview-ta` installed, RSI + volume spike rules active
- ✅ ~~No custom watchlist management~~ — `watchlists.json` persistence + full CRUD API + `WatchlistPanel` UI
- ✅ ~~No batch analysis~~ — `POST /api/analyze/batch` SSE endpoint with live progress
- ✅ ~~No scheduled/automatic scanning~~ — APScheduler with `SchedulerCard` UI
- ✅ ~~No prediction history or accuracy tracking~~ — SQLite + `PredictionsView` dashboard
- ✅ ~~No intraday data~~ — Upstox API v3 with 5-min candles + dual-timeframe analysis
- ✅ ~~No real-time prices~~ — Upstox REST + batch LTP + WebSocket skeleton
- ✅ ~~No paper trading~~ — Full paper trading engine with risk management
- ❌ No alerts or notifications (Telegram — deferred)
- ❌ No backtesting framework
- ❌ No auto-trading bot (Step 8 — next)

---

## 2. Technology Decision: tradingview-mcp

We evaluated [tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp) (an MCP server for TradingView data). **Decision: We will NOT use the MCP server, but we WILL use its underlying Python libraries directly.**

| What | Decision | Reason |
|---|---|---|
| `tradingview-mcp` MCP server | ❌ Skip | It's designed for Claude Desktop chat, not for our automated platform. No dashboard, no scheduling, no Indian market specialisation. |
| `tradingview-ta` Python package | ✅ Use in screener | Gives us 26 technical indicators (RSI, MACD, Bollinger, etc.) for any symbol in a single API call, for free. Much faster than computing from raw yfinance data. |
| `tradingview-screener` Python package | 🔄 Consider later | Can scan entire exchanges for gainers/losers/squeezes. Could replace our hardcoded index lists. |

**Best implementation trick:** Instead of running full yfinance history downloads to compute RSI ourselves, we call `tradingview-ta` which returns pre-computed indicators from TradingView's servers in milliseconds. This makes our Phase 2 screener dramatically faster and adds RSI/volume screening that's currently missing.

---

## 3. What We Are Going to Build

### Phase 1: Complete the Foundation ✅ DONE

**Goal**: Fix the broken `GET /api/results` endpoint and add the missing screener indicators.

| Task | Details | Status |
|---|---|---|
| `GET /api/results` endpoint | Scan `results/` directory, parse JSON logs, return `[{ticker, date, rating, reports}]` | ✅ Done |
| Upgrade screener with `tradingview-ta` | RSI, volume spike detection via `tradingview-ta 3.3.0`. Flags RSI < 32 or > 68, volume > 2× SMA20 | ✅ Done |
| Auto-date in analysis | Default to today's date when triggering analysis | ✅ Done (App.tsx line 74) |

**Files modified**:
- [api_server.py](file:///c:/TradeBotX/api_server.py) — `GET /api/results` already implemented
- [nse_api.py](file:///c:/TradeBotX/tradingagents/dataflows/nse_api.py) — `tradingview-ta` integration already written; installed package `tradingview-ta 3.3.0`

---

### Phase 2: Watchlist Management + Batch Analysis ✅ DONE

**Goal**: Manage custom watchlists and analyse multiple stocks with one click.

| Task | Details | Status |
|---|---|---|
| Custom watchlist UI | `WatchlistPanel.tsx` — add/remove tickers, delete button per row, live count badge | ✅ Done |
| Backend CRUD endpoints | `GET/POST/DELETE /api/watchlist/custom` — reads/writes `watchlists.json` | ✅ Done |
| Backend batch SSE endpoint | `POST /api/analyze/batch` — runs pipeline per ticker, streams `ticker_start / progress / ticker_result / batch_done` | ✅ Done |
| UI: batch progress | Animated progress bar, per-ticker rows showing status icon + live agent name + rating badge on completion | ✅ Done |
| Persist custom watchlists | `watchlists.json` written atomically on every add/remove | ✅ Done |
| TopNav: Watchlist tab | Added between Screener and Results in `TopNav.tsx` | ✅ Done |

**Files created/modified**:
- [api_server.py](file:///c:/TradeBotX/api_server.py) — watchlist CRUD + batch SSE endpoint
- [WatchlistPanel.tsx](file:///c:/TradeBotX/frontend/src/components/WatchlistPanel.tsx) — **[NEW]** full watchlist + batch UI
- [TopNav.tsx](file:///c:/TradeBotX/frontend/src/components/TopNav.tsx) — added Watchlist nav link
- [App.tsx](file:///c:/TradeBotX/frontend/src/App.tsx) — routed `view === 'watchlist'` to `WatchlistPanel`
- [types.ts](file:///c:/TradeBotX/frontend/src/types.ts) — added `CustomWatchlist`, `BatchTickerState`, `BatchState` types
- [index.css](file:///c:/TradeBotX/frontend/src/index.css) — watchlist card, ticker list, batch progress bar + item row styles
- `watchlists.json` — **[NEW]** auto-created on first add

---

### Phase 3: Scheduled Scanning ✅ DONE

**Goal**: The agent automatically scans your watchlist every morning before market opens.

| Task | Details | Status |
|---|---|---|
| Background scheduler | `APScheduler 3.11.2` with `BackgroundScheduler` + `CronTrigger` at IST time | ✅ Done |
| Pre-market scan | Runs screener (index source) or pipeline directly (custom watchlist) on configured tickers | ✅ Done |
| Store results | Writes `morning_report.json` + standard `results/` directory via `_log_state()` | ✅ Done |
| UI: Scheduler Card | `SchedulerCard.tsx` at top of Screener — live dot, next/last run, shimmer bar when running, rating chips, inline config panel | ✅ Done |
| Config | `config.json` — scan time, watchlist source, RSI/volume thresholds, max stocks, enabled flag | ✅ Done |

**Files created/modified**:
- `config.json` — **[NEW]** default scheduler settings
- [scheduler.py](file:///c:/TradeBotX/scheduler.py) — **[NEW]** APScheduler loop, scan runner, `morning_report.json` writer
- [api_server.py](file:///c:/TradeBotX/api_server.py) — lifespan startup/shutdown + 5 endpoints: `GET/POST /api/scheduler/config`, `GET /api/scheduler/status`, `POST /api/scheduler/run-now`, `GET /api/morning-report`
- [SchedulerCard.tsx](file:///c:/TradeBotX/frontend/src/components/SchedulerCard.tsx) — **[NEW]** self-contained status + control card (polls every 3-15s)
- [ScreenerView.tsx](file:///c:/TradeBotX/frontend/src/components/ScreenerView.tsx) — `SchedulerCard` embedded at top
- [index.css](file:///c:/TradeBotX/frontend/src/index.css) — scheduler card styles (shimmer animation, dot states, config panel)

---

### Phase 4: Prediction Tracking & Accuracy ✅ DONE

**Goal**: Track every prediction and compare with actual price movement to measure agent accuracy.

| Task | Details | Status |
|---|---|---|
| Prediction database | SQLite: `(ticker, trade_date, decision, rating, price_at_prediction, current_price, return_pct, is_win, ...)` | ✅ Done |
| Outcome tracker | `db.update_outcomes(days=3)` — fetch current price, compute return %, determine win/loss per rating direction | ✅ Done |
| Accuracy dashboard | 4 stat cards + per-rating breakdown + full predictions table with Win/Loss badges | ✅ Done |
| Auto-save predictions | Saved after every SSE analysis, batch analysis, and morning scan | ✅ Done |

**Files created/modified**:
- [database.py](file:///c:/TradeBotX/database.py) — **[NEW]** SQLite wrapper with `init_db`, `save_prediction`, `update_outcomes`, `get_stats`
- [api_server.py](file:///c:/TradeBotX/api_server.py) — `init_db()` in lifespan, prediction save in SSE endpoint, 3 new endpoints: `GET /api/predictions`, `GET /api/predictions/stats`, `POST /api/predictions/update-outcomes`
- [scheduler.py](file:///c:/TradeBotX/scheduler.py) — saves predictions for every scheduled scan
- [PredictionsView.tsx](file:///c:/TradeBotX/frontend/src/components/PredictionsView.tsx) — **[NEW]** accuracy dashboard
- [TopNav.tsx](file:///c:/TradeBotX/frontend/src/components/TopNav.tsx) — added "Accuracy" tab
- [App.tsx](file:///c:/TradeBotX/frontend/src/App.tsx) — routed `'predictions'` view
- [types.ts](file:///c:/TradeBotX/frontend/src/types.ts) — `Prediction`, `PredictionStats`, `RatingStats`
- [index.css](file:///c:/TradeBotX/frontend/src/index.css) — stat cards, rating table, predictions table, outcome badges

---

### Phase 5: Alerts & Notifications ⏱️ ~2-3 hours

**Goal**: Get notified instantly when a strong signal is found.

| Task | Details | Status |
|---|---|---|
| Telegram bot | Send BUY/SELL alerts to a Telegram channel via Bot API | ⏳ |
| Email alerts (optional) | SMTP-based email notifications | ⏳ |
| Alert rules | Only alert on strong BUY or SELL (not HOLD), configurable threshold | ⏳ |
| UI: notification bell | In-app notification panel showing recent alerts | ⏳ |

**Files to create/modify**:
- New: `alerts/telegram_bot.py`
- New: `alerts/email_sender.py`
- [api_server.py](file:///d:/TradingAgents/api_server.py) — trigger alerts after analysis
- [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx) — notification bell component

---

### Phase 6: Live/Intraday Data (Advanced) ⏱️ ~5+ hours

**Goal**: Move beyond end-of-day data for intraday trading signals.

| Option | Pros | Cons |
|---|---|---|
| **Breeze API** (ICICI Direct) | Real-time Indian market data, free with demat account | Requires ICICI demat |
| **Kite Connect** (Zerodha) | Best Indian broker API, excellent docs | ₹2000/month subscription |
| **Upstox API** | Free tier available, decent coverage | Limited historical data |
| **Angel One SmartAPI** | Free, good for real-time data | Rate limits |

This phase would add a new data vendor in `dataflows/` alongside yfinance.

---

## 4. Architecture Overview (Target State)

```
┌─────────────────────────────────────────────────────────┐
│                    React Dashboard                       │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐ │
│  │Screener  │ │ Analysis   │ │ Results  │ │ Accuracy │ │
│  │View      │ │ View       │ │ View     │ │Dashboard │ │
│  └──────────┘ └────────────┘ └──────────┘ └──────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ SSE / REST
┌────────────────────────┴────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────┐ │
│  │Scheduler │ │  Screener  │ │ Agent    │ │  Alerts  │ │
│  │(8:30 AM) │ │(tv-ta+yf)  │ │ Pipeline │ │(Telegram)│ │
│  └──────────┘ └────────────┘ └──────────┘ └──────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │     SQLite (Predictions) + results/ (JSON logs)    │ │
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
│  yfinance │ tradingview-ta │ Kite/Breeze │ LLM (OpenAI) │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Build Priority

| Phase | Effort | Value | Status |
|---|---|---|---|
| **1. Fix Foundation** (`/api/results` + screener upgrade) | 1h | 🔴 Critical blocker | ✅ Done |
| **2. Watchlist + Batch Analysis** | 2h | 🔴 Essential | ✅ Done |
| **3. Scheduled Scanning** | 2-3h | 🟡 High | ✅ Done |
| **4. Prediction Tracking** | 3-4h | 🟡 High | ✅ Done |
| 5. Alerts (Telegram) | 2-3h | 🟢 Nice to have | Deferred |
| **6. Upstox Migration + Paper Trading + Signals** | 8h | 🔴 Critical | ✅ Done (2026-05-01) |
| **6.5 System Hardening** | 3h | 🔴 Critical | ✅ Done (2026-05-01) |
| **7. Auto Paper Trading Bot** | 3-4h | 🟡 High | **🔜 Next** |

### What's Already Done
- ✅ NSE index screener (price + 52-week + RSI + volume spike flagging via `tradingview-ta`)
- ✅ Full React dashboard with 6-view routing (Screener / Watchlist / Analysis / Results / Accuracy / **Paper Trade**)
- ✅ SSE streaming analysis pipeline
- ✅ Auto-date (uses today's date)
- ✅ Results history — full end-to-end (backend + frontend)
- ✅ Custom watchlist with persistence (`watchlists.json`)
- ✅ Batch analysis with live SSE progress per ticker
- ✅ APScheduler pre-market scan at configurable IST time with `SchedulerCard` UI
- ✅ SQLite prediction tracking with win/loss accuracy dashboard
- ✅ **Upstox API v3** — OAuth auth, REST quotes, historical candles, intraday candles, batch LTP
- ✅ **WebSocket V3 skeleton** — auto-reconnect, subscribe/unsubscribe, tick dispatch
- ✅ **Deterministic signal engine** — RSI, MACD, EMA, VWAP (intraday), Bollinger, Stochastic, ATR, volume surge
- ✅ **Dual-timeframe analysis** — daily candles (trend) + 5-min candles (entry timing + VWAP)
- ✅ **Paper trading engine** — virtual orders, SQLite persistence, state recovery on restart
- ✅ **Risk management** — 2% daily loss limit, max 5 positions, 5% sizing, mandatory SL, circuit breaker
- ✅ **Slippage model** — 0.05% on entry/exit for realistic P&L
- ✅ **NSE holiday calendar** — 2025-2026 holidays + weekend detection
- ✅ **Batch LTP + movers API** — 1 API call for 47 stocks, smart filtering
- ✅ **Paper Trading dashboard** — portfolio card, signal table, buy modal, positions, trade history

---

### Phase 6: Upstox Migration + Paper Trading ✅ DONE

**Goal**: Replace yfinance with real-time Upstox data, build paper trading engine, add deterministic signal layer.

**Files created**:
- [upstox_auth.py](file:///c:/TradeBotX/upstox_auth.py) — OAuth 2.0 token management
- [upstox_client.py](file:///c:/TradeBotX/upstox_client.py) — REST API wrapper (quotes, candles, orders, batch LTP, movers)
- [upstox_ws.py](file:///c:/TradeBotX/upstox_ws.py) — WebSocket V3 manager
- [technical.py](file:///c:/TradeBotX/technical.py) — Deterministic signal engine with dual-timeframe
- [paper_trader.py](file:///c:/TradeBotX/paper_trader.py) — Paper trading engine with risk management
- [nse_holidays.py](file:///c:/TradeBotX/nse_holidays.py) — NSE holiday calendar + market status
- [PaperTradingView.tsx](file:///c:/TradeBotX/frontend/src/components/PaperTradingView.tsx) — Dashboard view

**Files modified**:
- [api_server.py](file:///c:/TradeBotX/api_server.py) — 15+ new endpoints (Upstox + Paper Trading)
- [TopNav.tsx](file:///c:/TradeBotX/frontend/src/components/TopNav.tsx) — added Paper Trade tab
- [App.tsx](file:///c:/TradeBotX/frontend/src/App.tsx) — routed paper view
- [types.ts](file:///c:/TradeBotX/frontend/src/types.ts) — PaperPortfolio, SignalData, etc.
- [index.css](file:///c:/TradeBotX/frontend/src/index.css) — 500+ lines of Paper Trading CSS
- `.env` / `.env.example` — Upstox credentials

### Phase 6.5: System Hardening ✅ DONE

**Goal**: Fix critical bugs and add safety guards before auto-trading.

| Fix | Impact |
|---|---|
| SQLite UPDATE subquery (was using unsupported ORDER BY in UPDATE) | Bug fix |
| State persistence — positions/capital survive restarts | Critical |
| NSE holiday calendar (2025-2026) + weekend checks | Safety |
| Circuit breaker — 3 consecutive losses → 30-min pause | Safety |
| Slippage model — 0.05% on entry/exit | Accuracy |
| Signal context logging — always saves JSON context | Audit |
| Batch LTP — 1 API call for 47 stocks (was 47 individual calls) | Performance |
| Dual-timeframe — intraday VWAP + momentum (was wrong daily VWAP) | Core logic |

### Phase 7: Auto Paper Trading Bot 🔜 NEXT

**Goal**: The bot automatically scans, enters, and exits paper trades with no human input.

| Task | Details | Status |
|---|---|---|
| Signal scanner | Runs every 5 min during market hours; fetches batch LTP, filters movers, computes signals | ⏳ |
| Auto paper BUY | If score ≥ 0.65 + risk checks pass → enter paper trade | ⏳ |
| Auto paper SELL | If score ≤ 0.35 or SL/TP hit → exit paper trade | ⏳ |
| WebSocket tick handler | Wire live ticks → `paper_trader.on_price_update()` for real-time SL/TP | ⏳ |
| Force close at 15:20 IST | Scheduler job to close all positions before market close | ⏳ |
| Integrate into scheduler | Add scanner as recurring APScheduler job | ⏳ |
