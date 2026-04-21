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
| `GET` | `/api/results` | ❌ **Missing — ResultsView calls this but it doesn't exist yet** |

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
- ❌ No `GET /api/results` endpoint — **ResultsView UI is built but backend is missing** ← immediate fix needed
- ❌ Screener only checks price % change and 52-week proximity — **no RSI or volume spike detection**
- ❌ No custom watchlist management (add/remove tickers) — only predefined index lists
- ❌ No batch analysis — can only run one stock at a time
- ❌ No scheduled/automatic scanning
- ❌ No prediction history or accuracy tracking
- ❌ No alerts or notifications
- ❌ No intraday data (yfinance = end-of-day only)

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

### Phase 1: Complete the Foundation ⏱️ ~1 hour — 🔴 DO THIS FIRST

**Goal**: Fix the broken `GET /api/results` endpoint and add the missing screener indicators.

| Task | Details | Status |
|---|---|---|
| `GET /api/results` endpoint | Scan `results/` directory, parse JSON logs, return `[{ticker, date, rating, reports}]` | ❌ Blocked |
| Upgrade screener with `tradingview-ta` | Add RSI, MACD, volume indicators to screening. Flag RSI < 30 or > 70, volume spikes | ❌ Not started |
| Auto-date in analysis | Default to today's date when triggering analysis | ✅ Done (App.tsx line 74) |

**Files to modify**:
- [api_server.py](file:///d:/TradingAgents/api_server.py) — add `GET /api/results` endpoint
- [nse_api.py](file:///d:/TradingAgents/tradingagents/dataflows/nse_api.py) — integrate `tradingview-ta` for RSI/volume screening

---

### Phase 2: Watchlist Management + Batch Analysis ⏱️ ~2 hours

**Goal**: Manage custom watchlists and analyse multiple stocks with one click.

| Task | Details | Status |
|---|---|---|
| Custom watchlist UI | Add/remove individual tickers beyond predefined indices | ⏳ |
| Backend batch endpoint | `POST /api/analyze/batch` — accepts list of tickers, streams progress per ticker | ⏳ |
| UI: batch progress | Show "Analysing 3/10: TCS.NS" progress bar | ⏳ |
| Persist custom watchlists | Save user-created watchlists to `watchlists.json` | ⏳ |

**Files to create/modify**:
- [api_server.py](file:///d:/TradingAgents/api_server.py) — new batch SSE endpoint
- [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx) — watchlist management UI
- New: `watchlists.json` — user custom ticker lists

---

### Phase 3: Scheduled Scanning ⏱️ ~2-3 hours

**Goal**: The agent automatically scans your watchlist every morning before market opens (e.g., 8:30 AM IST).

| Task | Details | Status |
|---|---|---|
| Background scheduler | Use `APScheduler` or a simple `asyncio` loop in the backend | ⏳ |
| Pre-market scan | At 8:30 AM: run screener → run pipeline on flagged stocks | ⏳ |
| Store results | Save to `results/` directory with timestamp | ⏳ |
| UI: "Morning Report" view | Show today's pre-market scan results as a dashboard card | ⏳ |
| Config | Set scan time, watchlist, and screening thresholds in `config.json` | ⏳ |

**Files to create/modify**:
- [api_server.py](file:///d:/TradingAgents/api_server.py) — add scheduler integration
- New: `scheduler.py` — background scanning loop
- New: `config.json` — scheduler settings

---

### Phase 4: Prediction Tracking & Accuracy ⏱️ ~3-4 hours

**Goal**: Track every prediction and compare with actual price movement to measure agent accuracy.

*Note: We can borrow backtesting metric formulas (Sharpe ratio, Calmar ratio, Max Drawdown) from `tradingview-mcp`'s local backtest engine when building the accuracy dashboard.*

| Task | Details | Status |
|---|---|---|
| Prediction database | SQLite table: `(id, ticker, date, decision, price_at_prediction, reports_json)` | ⏳ |
| Outcome tracker | Daily job: for predictions older than N days, fetch current price and compute returns | ⏳ |
| Accuracy dashboard | Show win rate, avg return, per-agent accuracy breakdown | ⏳ |
| Memory integration | Feed actual outcomes back into [reflect_and_remember()](file:///d:/TradingAgents/tradingagents/graph/trading_graph.py#277-294) to improve agents over time | ⏳ |

**Files to create/modify**:
- New: `database.py` — SQLite wrapper for predictions
- [api_server.py](file:///d:/TradingAgents/api_server.py) — save predictions, expose `GET /api/predictions` endpoint
- [App.tsx](file:///d:/TradingAgents/frontend/src/App.tsx) — accuracy dashboard component

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
| **1. Fix Foundation** (`/api/results` + screener upgrade) | 1h | 🔴 Critical blocker | **Next** |
| 2. Watchlist + Batch Analysis | 2h | 🔴 Essential | Queued |
| 3. Scheduled Scanning | 2-3h | 🟡 High | Queued |
| 4. Prediction Tracking | 3-4h | 🟡 High | Queued |
| 5. Alerts (Telegram) | 2-3h | 🟢 Nice to have | Later |
| 6. Live Data (Broker API) | 5+h | 🟢 Advanced | Later |

### What's Already Done
- ✅ NSE index screener (price + 52-week flagging)
- ✅ Full React dashboard with 3-view routing
- ✅ SSE streaming analysis pipeline
- ✅ Auto-date (uses today's date)
- ✅ Results history UI (frontend only — backend API missing)

**Total remaining effort**: ~15-18 hours for Phases 1-5
