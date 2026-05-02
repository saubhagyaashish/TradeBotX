# TradeBotX — Full Autonomy Roadmap

> **Vision**: A fully autonomous trading agent that hunts for opportunities on its own, decides when to buy/hold/sell, executes trades, manages risk — and the user only opens the dashboard to see how much money the bot made.

---

## ⚠️ Reality Check — What's Honest, What's Dreamy

Before going further, here's a brutally honest assessment of this roadmap.

### What Is Grounded and Achievable

| Item | Why it's real |
|---|---|
| Automated screener + scheduler | Pure engineering. Already done. Works today. |
| Watchlist + batch analysis | Data plumbing. Done. |
| Prediction tracking + accuracy dashboard | Just a database + math. Done. |
| Paper trading engine | Virtual portfolio with real prices. Standard stuff. Achievable. |
| Stop-loss / take-profit automation | Simple conditionals. Every algo platform does this. |
| Telegram alerts | Trivial API integration. |
| Cloud deployment | Standard DevOps. Nothing novel. |
| Trade logging with full context | SQLite writes. Straightforward. |

### What Is Partly Dreamy — Needs Honest Expectations

| Item | The dream | The reality |
|---|---|---|
| **"Win rate > 52%"** | Sounds easy — barely above coin flip | After fees, slippage, and taxes, consistently beating 52% is **hard**. Most retail algo bots end up around 45–55%. The edge is thin and fragile. |
| **"Sharpe > 1.0"** | The stated minimum | Most successful retail algos sit at 0.6–1.2 Sharpe. A retail bot hitting 1.5+ consistently would outperform most hedge funds. Be realistic. |
| **"Self-improving bot after 100 trades"** | Patterns emerge fast | 100 trades is **statistically meaningless**. You need 500+ trades in different market regimes (bull, bear, sideways, high-VIX, low-VIX) before signal weight changes are trustworthy. Overfitting to a small sample is the #1 killer of quant strategies. |
| **"Chart pattern detection"** | Head & shoulders, cup & handle | Academic studies show most visual chart patterns have **zero edge** in liquid markets. They're popular but not profitable. Don't build an engine around them. Focus on quantifiable signals (RSI, EMA, VWAP, volume). |
| **"FII/DII flow as a signal"** | Big money moves markets | FII data is published at **6 PM** — the market already moved by then. It's a lagging indicator. Useful for context, not for intraday signals. |
| **"Options PCR predicts direction"** | PCR > 1.2 = bullish | PCR is noisy. It works on expiry week, barely. On non-expiry days, it's nearly random. Don't over-rely on it. |
| **"Capital doubling every 3 months"** | ₹10k → ₹1L in a year | This implies ~100% annual return with zero drawdown impact. Professional quant funds target 15–30% annually. Scale based on **Sharpe remaining stable**, not calendar dates. |
| **"Full autonomy — user is spectator"** | The dream | Even Renaissance Technologies has human oversight. Full autonomy is a goal, not a state. The bot needs a **supervisor** (you), especially in the first year. |

### What Is Actually the Hardest Part (And Nobody Talks About It)

**It's not the code. It's the waiting.**

The hardest moment in trading — human or bot — is when a stock is sitting at +1.3% and your target is +4%. You *know* it might reverse. You want to book the profit. But the rule says wait.

Or worse: it's at -0.8% and your stop is -1.5%. It's not hit yet but it's drifting. The right move might be to just exit now at -0.8% instead of hoping for a reversal and eating the full -1.5%.

**This is the core truth: trading is not about prediction. It's about managing the uncertainty that comes after you enter.**

The bot can't predict the future. Nobody can. What the bot *can* do is:
1. Enter only when multiple signals agree (high-probability setups)
2. **Exit early if the trade isn't behaving as expected** (time-based exits)
3. **Take partial profits instead of being greedy** (tranche selling)
4. **Accept small losses before they become big losses** (aggressive stop management)
5. **Never let a winning trade turn into a losing trade** (trailing stops)

The rest of this roadmap is designed around these five principles.

---

## Table of Contents

1. [Where We Are Now](#1-where-we-are-now)
2. [The Gap — What's Missing](#2-the-gap--whats-missing)
3. [Phase Roadmap](#3-phase-roadmap-to-full-autonomy)
4. [Real-Time Data Layer](#4-real-time-data-layer)
5. [Order Execution Engine](#5-order-execution-engine)
6. [Signal Architecture (Speed Fix)](#6-signal-architecture--the-speed-problem)
7. [Risk Management Engine](#7-risk-management-engine)
8. [Portfolio Management](#8-portfolio-management)
9. [Market Intelligence — What an Expert Trader Looks At](#9-market-intelligence--what-an-expert-trader-looks-at)
10. [Performance Dashboard](#10-performance-dashboard--what-the-user-sees)
11. [Notification System](#11-notification-system)
12. [Infrastructure — 24/7 Uptime](#12-infrastructure--247-uptime)
13. [Paper Trading Period](#13-paper-trading-period--proving-the-edge)
14. [Going Live Checklist](#14-going-live-checklist)
15. [Smart Stop-Loss & Take-Profit Execution](#15-smart-stop-loss--take-profit-execution)
16. [Self-Improvement Loop — Learning from Every Trade](#16-self-improvement-loop--learning-from-every-trade)
17. [Code Robustness — Minimising LLM Dependency](#17-code-robustness--minimising-llm-dependency)

---

## 1. Where We Are Now

| Feature | Status |
|---|---|
| NSE index screener (RSI, volume, 52-week proximity) | ✅ Done |
| Full 13-agent LLM analysis pipeline | ✅ Done |
| Custom watchlist with persistence | ✅ Done |
| Batch analysis with live SSE progress | ✅ Done |
| APScheduler pre-market scan (8:30 AM IST) | ✅ Done |
| SQLite prediction tracking + accuracy dashboard | ✅ Done |
| **Upstox API v3 integration (replacing yfinance for live data)** | ✅ Done (2026-05-01) |
| **Real-time price feed (REST + WebSocket skeleton)** | ✅ Done |
| **Paper trading engine (virtual orders + SQLite)** | ✅ Done |
| **Deterministic fast signal layer (RSI/MACD/EMA/VWAP/BB/Stoch)** | ✅ Done |
| **Dual-timeframe analysis (daily + 5-min intraday)** | ✅ Done |
| **Risk management (SL, position sizing, circuit breaker, holidays)** | ✅ Done |
| **Paper Trading dashboard (React)** | ✅ Done |
| **Batch LTP + smart movers API** | ✅ Done |
| **Slippage model (0.05% per trade)** | ✅ Done |
| **State persistence (survives server restarts)** | ✅ Done |
| Telegram alerts | 🔜 Later |
| Smart stop-loss & take-profit execution | 🔜 Step 8 (auto-bot) |
| Auto signal scanner (every 5 min) | 🔜 Step 8 |
| Self-improvement / trade learning loop | ❌ Later |
| Cloud deployment (24/7 uptime) | ❌ Later |

**Current description:** ~~A sophisticated research assistant~~ → An autonomous intraday trading agent with real-time Upstox market data, deterministic technical analysis, and paper trading with risk management.

**Target description:** A fully autonomous trading agent. You open the dashboard once a day, see portfolio value, today's P&L, bot's win rate, and current positions. Everything else is automated.

---

## 2. The Gap — What's Missing

### 🔴 Critical (Without These, Autonomy Is Impossible)

#### A. Real-Time Market Data
~~`yfinance` gives end-of-day data with a 15-minute delay on intraday quotes.~~

✅ **SOLVED (2026-05-01):** Migrated to **Upstox API v3**. Live LTP via REST, 5-minute intraday candles, WebSocket V3 skeleton for tick-by-tick. Batch LTP (1 API call for 47 stocks).

#### B. Order Execution
~~The bot can shout "BUY INFY" all day — but nothing happens.~~

✅ **SOLVED (2026-05-01):** Paper trading engine (`paper_trader.py`) with virtual portfolio, slippage model (0.05%), SQLite persistence. Ready for live execution via `upstox_client.place_order()` when graduating from paper.

#### C. Risk Management
~~No professional trading system operates without stop-losses, position sizing rules, and circuit breakers.~~

✅ **SOLVED (2026-05-01):** Full risk management: 2% daily loss limit, max 5 positions, 5% position sizing, mandatory stop-loss, trailing stops, **consecutive loss circuit breaker (3 losses → 30-min pause)**, NSE holiday calendar, market hours enforcement.

### 🟡 Important (Significantly Improves Edge)

#### D. Speed — LLM Pipeline Is Too Slow for Intraday
~~The current 13-agent pipeline takes 2–5 minutes per stock.~~

✅ **SOLVED (2026-05-01):** Deterministic fast signal layer (`technical.py`) runs in <1 second. RSI, MACD, EMA, VWAP (intraday), Bollinger, Stochastic, ATR, volume surge. Dual-timeframe (daily + 5-min). Smart API strategy: batch LTP (1 call) → filter movers → only compute signals on movers.

#### E. Market Intelligence Gaps
~~The bot currently sees: price, RSI, volume.~~

✅ **PARTIALLY SOLVED:** Now sees: RSI, MACD, EMA-20/50, VWAP (intraday), Bollinger Bands, Stochastic, ATR, volume surge, intraday momentum (5-min trend). Still missing: FII/DII flow, options PCR, sector rotation, earnings calendar.

#### F. Portfolio Awareness
✅ **SOLVED:** Paper trader tracks: open positions, capital, per-trade P&L, win rate, sector exposure. Dashboard shows all of this in real-time.

### 🟢 Nice to Have (Makes the Dashboard Impressive)

- ❌ Sharpe/Sortino/Calmar ratios
- ❌ Alpha vs NIFTY 50 benchmark
- ❌ Backtesting engine
- ❌ Interactive Telegram bot (`/positions`, `/pnl`, `/stop`)
- ❌ Cloud deployment for 24/7 operation

---

## 3. Phase Roadmap to Full Autonomy

```
CURRENT: Research assistant (analyses on demand)
    ↓
Phase 5:  Telegram alerts              (~2-3h)   ✅ Deferred — doing live trading first
    ↓
Phase 6:  Paper trading engine          (~5-6h)   ✅ DONE (2026-05-01)
    ↓
Phase 6.5: System hardening            (~3h)      ✅ DONE (2026-05-01)
    ↓
Phase 7:  Real-time data layer          (~4-5h)   ✅ DONE (Upstox API v3)
    ↓
Phase 8:  Fast signal layer             (~3-4h)   ✅ DONE (technical.py dual-timeframe)
    ↓
Phase 9:  Risk management engine        (~4-5h)   ✅ DONE (circuit breaker, holidays, slippage)
    ↓
Phase 10: Auto Paper Trading Bot        (~3-4h)   🔜 NEXT ← Step 8 in task.md
    ↓
Phase 11: Advanced analytics dashboard  (~3-4h)   ⏳
    ↓
Phase 12: Cloud deployment              (~2-3h)   ⏳
    ↓
Phase 13: 3-month paper trading period  (3 months of data)
    ↓
Phase 14: Go live with real capital     (₹10,000 to start)
    ↓
GOAL: Fully autonomous trading bot. User = spectator.
```

---

## 4. Real-Time Data Layer

### Why yfinance Is Not Enough
| | yfinance | What We Need |
|---|---|---|
| Price update speed | 15-min delayed | Real-time tick-by-tick |
| Historical granularity | 1-minute (only last 7 days) | 1-minute, unlimited history |
| Options data | Basic | Full options chain, PCR, OI |
| Order book | None | Level 2 (bid/ask depth) |
| News | Delayed, unreliable | Real-time with sentiment score |

### Recommended: Zerodha Kite API

**Why Kite:**
- Most popular algo trading API in India
- Free for Zerodha account holders (`kiteconnect` Python package — ₹2,000 one-time API subscription)
- Live WebSocket price feed (tick-by-tick)
- Full order placement, modification, cancellation
- Historical data: minute-level OHLCV, unlimited history for daily
- Paper trading mode available

**Other options:**
- **Upstox API** — Similar to Kite, slightly simpler
- **Angel Broking SmartAPI** — Free, good for NSE/BSE
- **Fyers API** — Better WebSocket performance
- **TrueData** / **GlobalDataFeeds** — Paid tick data vendors (more reliable for HFT)

### Data Source Map — What Comes From Where

This is the practical answer to "how do we get all that data?"

| Data Point | Source | How |
|---|---|---|
| **Live price (tick-by-tick)** | ✅ Kite WebSocket | Subscribe to instruments, get LTP + bid/ask + volume in real time |
| **OHLCV candles** (1min → daily) | ✅ Kite API | `kite.historical_data()` — all intervals: minute, 5min, 15min, 60min, day |
| **Bid/Ask depth** (Level 2) | ✅ Kite WebSocket | Full mode subscription gives top 5 bid/ask levels |
| **India VIX** | ✅ Kite WebSocket | VIX is a subscribable instrument (`INDIA VIX`) — live value |
| **Sectoral indices** | ✅ Kite WebSocket | NIFTY IT, NIFTY BANK, NIFTY PHARMA etc. are instruments — subscribe for live values |
| **VWAP** | 🔧 Compute ourselves | Formula: `cumsum(price × volume) / cumsum(volume)` from tick data. Simple math, no external source needed. |
| **RSI, MACD, EMA, Bollinger, Stochastic** | 🔧 Compute ourselves | Use `pandas-ta` or `ta-lib` Python library on Kite's OHLCV candles. Pure math. |
| **Multi-timeframe confluence** | 🔧 Compute ourselves | Fetch candles from Kite at 15min + 1hr + daily → compute RSI/EMA on each → check alignment |
| **Sector rotation / relative strength** | 🔧 Compute ourselves | Track sectoral index prices from Kite → compute RS = (sector % change) / (NIFTY % change) |
| **Chart patterns** | 🔧 Compute ourselves | From candle data. **But:** Reality Check says most patterns have zero proven edge. Low priority. |
| **Options chain / PCR** | ⚠️ NSE website | Kite can quote individual options, but NSE provides the full chain in one page. Scrape NSE option chain page or use `jugaad-data` package. |
| **FII/DII flow** | ⚠️ NSE website | Published daily ~6 PM. Scrape NSE FII/DII page. Lagging indicator — useful for overnight bias, not intraday signals. |
| **Earnings calendar** | ⚠️ BSE / Tickertape | BSE publishes board meeting dates. Tickertape has a clean earnings calendar. Scrape weekly. |
| **Delivery percentage** | ⚠️ NSE website | NSE publishes delivery data next day. Not available intraday. Useful for overnight swing trade decisions. |

**Key takeaway:** Kite gives us **live prices, historical candles, order execution, and VIX**. We compute all technical indicators ourselves from that raw data using `pandas-ta`. Three things need separate scraping: **FII/DII, options chain, and earnings calendar** — all from NSE/BSE websites.

### Python Packages for Each Layer

```
kiteconnect          — Broker API (prices, orders, WebSocket)
pandas-ta  or  ta-lib — Technical indicators (RSI, MACD, EMA, VWAP, BB, etc.)
jugaad-data          — NSE/BSE data scraping (FII/DII, delivery, option chain)
beautifulsoup4       — Scrape NSE/BSE/Tickertape for earnings calendar
newsapi-python       — News headlines for sentiment analysis
```

### News + Sentiment Sources

| Source | Type | Cost |
|---|---|---|
| NewsAPI | Global news, filtered by ticker | Free tier (100 req/day) |
| Tickertape | Indian market focused, earnings calendar | Scraping |
| Moneycontrol / ET Markets | Best Indian stock coverage | Scraping |
| NSE announcements | Corporate actions, board meetings, results | Free (NSE website) |

---

## 5. Order Execution Engine

### The Trading Loop

```
Signal generated → Risk check → Position size calculated
        ↓
Order placed via Broker API
        ↓
Order confirmed (filled price, qty, time)
        ↓
Position opened → Stop-loss order placed immediately
        ↓
Monitor: price hits target → Exit
         price hits stop-loss → Exit (auto)
         time-based exit (if intraday, exit before 3:20 PM)
        ↓
Trade logged to database → P&L updated → Alert sent
```

### Order Types We Need

| Order Type | When Used |
|---|---|
| **Market order** | Fast entry when signal is strong and time-sensitive |
| **Limit order** | Entry at a specific price, avoid chasing |
| **Stop-loss order** | Automatic exit if trade goes wrong |
| **Trailing stop** | Lock in profits as price moves in our favour |
| **Bracket order** | Entry + SL + Target in one shot (Zerodha supports this) |

### Paper Trading Mode (Phase 6)

Before touching real money, the bot runs in **paper trading mode**:
- Uses real live prices (from Kite WebSocket)
- Places "virtual" orders in our own database (not on exchange)
- Tracks virtual portfolio P&L as if trades were real
- Builds 3 months of verifiable track record

```python
# Paper trade flow
if config.paper_mode:
    order = PaperOrder(ticker, qty, price, direction)
    paper_portfolio.execute(order)
    db.log_paper_trade(order)
else:
    order = kite.place_order(...)  # Real money
```

---

## 6. Signal Architecture — The Speed Problem

### Current Problem
The LLM pipeline is a **sequential waterfall** — 13 agents run one after another, taking 2–5 minutes. This is fine for "analyse this stock overnight." It is completely wrong for "should I buy this right now?"

### Solution: Tiered Signal Architecture

```
Market Open (9:15 AM)
        ↓
🟢 FAST LAYER  (< 1 second, runs every minute)
   ├── RSI < 32 or > 68?
   ├── Price crossing 20 EMA from below?
   ├── Volume > 2× 20-day average?
   ├── Price > VWAP (bullish intraday bias)?
   └── Flags 3-5 stocks as "interesting right now"
        ↓
🟡 MEDIUM LAYER  (< 10 seconds, runs on flagged stocks)
   ├── Multi-timeframe confirmation (15min + 1hr aligned?)
   ├── Quantitative momentum score
   ├── Sector leader/laggard check
   ├── Support/resistance proximity
   └── Scores stocks 0–100, selects top 2
        ↓
🔴 LLM DEEP ANALYSIS  (2–5 min, runs on top 2 only)
   ├── Full 13-agent pipeline
   ├── News sentiment analysis
   ├── Fundamental check
   └── Final BUY / HOLD / SELL decision
        ↓
Risk check → Order execution
```

**Key insight:** The LLM never runs on all 50 stocks. It only runs on the **2 stocks** the fast layer is most excited about. This cuts LLM calls by 96% while keeping the deep intelligence for final decisions.

### Fast Layer Indicators to Implement

**Momentum:**
- EMA crossovers (9 EMA crossing 21 EMA)
- RSI with divergence detection
- MACD crossover + histogram flip
- Stochastic oscillator

**Volume:**
- Volume surge (> 2× avg)
- On-Balance Volume (OBV) trend
- Accumulation/Distribution line
- VWAP deviation

**Price Action:**
- Bollinger Band squeeze then expansion (volatility breakout)
- Pivot points (support/resistance levels)
- Candlestick patterns: Engulfing, Hammer, Doji, Morning Star
- Chart patterns: Double bottom, Head & Shoulders, Flag/Pennant

**Market Context:**
- NIFTY 50 direction (don't buy individual stocks in a falling market)
- India VIX level (if VIX > 20, reduce position sizes; if > 30, stay flat)
- Advance/Decline ratio (breadth)

---

## 7. Risk Management Engine

> "The first rule of trading is don't lose money. The second rule is don't forget rule one." — Warren Buffett (adapted)

This is the **most critical** missing piece. Without risk management, a few bad trades can wipe out months of gains.

### Position Sizing — How Much to Buy

**Kelly Criterion (modified):**
```
f* = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
         ────────────────────────────────────────
                      Avg Win

Deploy: min(f* × 0.5, max_position_pct) × portfolio_value
```
*The 0.5 multiplier is a safety factor — use half-Kelly in practice.*

**Simpler version (fixed fractional):**
- Never risk more than **1–2% of portfolio** on any single trade
- At 1% risk and a 1.5% stop-loss: position = (1% × ₹1L) / 1.5% = ~₹6,667 position size

### Stop-Loss Rules

| Type | Level | When to Use |
|---|---|---|
| **Hard stop** | 1.5% below entry | Always. Non-negotiable. |
| **Trailing stop** | 2.5% below current high | When trade is profitable, lock in gains |
| **Time stop** | EOD exit if not profitable | Intraday positions must close before 3:20 PM |
| **Volatility stop** | ATR × 2 below entry | For high-volatility stocks |

### Circuit Breakers

```python
RISK_RULES = {
    # Never risk more than this per trade
    "max_single_trade_risk_pct": 1.5,

    # If today's P&L drops below this, stop all trading for the day
    "daily_loss_limit_pct": 2.0,

    # If portfolio drops this much from its peak, pause everything
    "max_drawdown_limit_pct": 10.0,

    # Never put more than this in one sector
    "max_sector_exposure_pct": 30.0,

    # Never put more than this in one stock
    "max_single_position_pct": 15.0,

    # Maximum number of open positions at once
    "max_open_positions": 8,

    # Don't trade if India VIX is above this (market too chaotic)
    "max_vix_to_trade": 25.0,

    # Don't trade in last 10 minutes of market (high volatility, wide spreads)
    "no_trade_after": "15:20",

    # Don't hold positions over earnings announcement
    "exit_before_earnings_days": 2,
}
```

### Correlation Guard
Don't hold too many stocks that move together. If INFY, TCS, WIPRO, HCLTECH are all in the portfolio, when IT sector sells off, all 4 lose at once — amplifying the loss.

```python
# If correlation between any two positions > 0.75, don't open the new one
if max_correlation(existing_positions, new_stock) > 0.75:
    skip("Too correlated with existing positions")
```

---

## 8. Portfolio Management

### What the Bot Needs to "Know" at All Times

```python
portfolio = {
    "cash_available": 45000,        # ₹ available to deploy
    "total_value": 132400,          # cash + positions market value
    "positions": [
        {
            "ticker": "INFY.NS",
            "qty": 10,
            "avg_cost": 1842.00,
            "current_price": 1897.50,
            "unrealized_pnl": 555.00,  # ₹ gain
            "pnl_pct": 3.01,
            "stop_loss": 1814.00,
            "target": 1920.00,
            "opened_at": "2026-04-22 09:47:00",
        }
    ],
    "today_realized_pnl": 2340,
    "today_pnl_pct": 1.8,
    "all_time_pnl": 14200,
    "all_time_pnl_pct": 12.1,
}
```

### Position Management Loop (Runs Every Minute During Market Hours)

```
For each open position:
  1. Fetch current price (real-time)
  2. Check: has stop-loss been hit? → Close position, log trade
  3. Check: has target been hit? → Close position, log trade
  4. Check: update trailing stop if price moved up
  5. Check: is it 3:20 PM and this is an intraday position? → Close
  6. Update unrealized P&L in database
  7. Update portfolio dashboard
```

---

## 9. Market Intelligence — What an Expert Trader Looks At

This is what separates a good bot from a great one.

### Technical Analysis (Currently Missing)

**Multi-Timeframe Confluence**
- A BUY signal is **3× stronger** if it appears on 15-min, 1-hr, AND daily charts simultaneously
- Current bot: only uses daily-level data from yfinance

**VWAP (Volume-Weighted Average Price)**
- The institutional reference price for the day
- Price above VWAP → buyers in control → lean long
- Price below VWAP → sellers in control → lean short
- Best entry: dip to VWAP on high-volume stock in uptrend

**Chart Patterns to Detect**
| Pattern | Signal |
|---|---|
| Double Bottom | Strong BUY reversal |
| Head & Shoulders | Strong SELL reversal |
| Bull Flag | BUY continuation |
| Cup & Handle | BUY breakout |
| Triangle breakout | BUY or SELL depending on direction |

**Candlestick Patterns**
| Pattern | Signal |
|---|---|
| Bullish Engulfing | BUY reversal |
| Bearish Engulfing | SELL reversal |
| Hammer | BUY reversal (at support) |
| Shooting Star | SELL reversal (at resistance) |
| Doji | Indecision — wait for confirmation |

### Macro/Fundamental Intelligence

**FII/DII Flow**
- NSE publishes Foreign Institutional Investor and Domestic Institutional Investor buy/sell data daily
- If FIIs sell ₹5,000 crore in 3 consecutive days → strong negative signal
- Available free from NSE website

**India VIX**
- India's "fear index" — measures expected volatility
- VIX < 13: Calm, trend-following works well
- VIX 13–20: Normal, mixed conditions
- VIX 20–25: Elevated fear, reduce position sizes by 50%
- VIX > 25: High fear, only trade with tight stops or stay flat
- VIX > 30: Crisis mode, no new positions

**Earnings Calendar**
- Never hold a stock through earnings if risk-averse (price can gap ±10% instantly)
- Exit 2 days before earnings date
- NSE publishes quarterly result dates in advance

**Options Data (Advanced)**
- **PCR (Put-Call Ratio)**: Total Put OI / Total Call OI
  - PCR > 1.2 = Bullish (everyone is hedging puts = market likely to go up)
  - PCR < 0.7 = Bearish
- **Max Pain**: The strike price where maximum options expire worthless. Price often gravitates toward this on expiry
- **IV (Implied Volatility)**: Rising IV = big move expected. Use this for sizing (smaller position = bigger expected move)

**Sector Rotation**
- Markets rotate between sectors: IT → Banking → FMCG → Pharma → etc.
- Identify which sector is leading (highest relative strength vs NIFTY)
- Buy stocks in the leading sector, avoid laggards
- Example: If BANKEX is outperforming NIFTY → focus on banking stocks

---

## 10. Performance Dashboard — What the User Sees

The user shouldn't need to understand trading. They should just see:

### Main Dashboard
```
╔══════════════════════════════════════════════════════╗
║  TradeBotX — Live Dashboard          IST: 14:32:00  ║
╠══════════════════════════════════════════════════════╣
║  Portfolio Value: ₹1,32,400  (+₹2,340 today +1.8%) ║
║  All-time P&L:   +₹14,200  (+12.1%)                ║
║  vs NIFTY 50:    +4.3% Alpha  (NIFTY +7.8%, us 12%) ║
╠══════════════════════════════════════════════════════╣
║  Open Positions (3)                                  ║
║  INFY    10 qty  +3.0%  ₹555  🟢 SL: 1814          ║
║  HDFC    5 qty   +1.2%  ₹420  🟢 SL: 1620          ║
║  WIPRO   8 qty   -0.4%  -₹80  🔴 SL: 498           ║
╠══════════════════════════════════════════════════════╣
║  Bot Stats (Last 90 days)                            ║
║  Win Rate: 62%  |  Sharpe: 1.84  |  Max DD: -5.2%  ║
║  Avg Win: +2.4% | Avg Loss: -1.3% | Expectancy: +0.9║
╚══════════════════════════════════════════════════════╝
```

### Key Metrics to Show

| Metric | Formula | Good Range |
|---|---|---|
| **Win Rate** | Winning trades / Total trades | > 50% |
| **Risk/Reward Ratio** | Avg Win / Avg Loss | > 1.5 |
| **Expectancy** | (WR × Avg Win) − (LR × Avg Loss) | > 0 (positive edge) |
| **Sharpe Ratio** | (Return − Risk Free Rate) / Std Dev | > 1.0 excellent, >1.5 exceptional |
| **Sortino Ratio** | (Return − Risk Free) / Downside Std Dev | > 1.5 |
| **Max Drawdown** | Worst peak-to-trough drop | < 15% for a retail bot |
| **Calmar Ratio** | Annual Return / Max Drawdown | > 2.0 |
| **Alpha vs NIFTY** | Bot Return − NIFTY 50 Return | Positive = we're beating index |
| **Profit Factor** | Total Wins / Total Losses | > 1.5 |

---

## 11. Notification System

### Phase 5 (Next): Basic Telegram Alerts
- BUY/SELL signals pushed as Telegram messages
- Error alerts (scan failed, connection lost)

### Phase 11 (Advanced): Interactive Telegram Bot
The user can **ask** the bot questions via Telegram:

| Command | Bot Response |
|---|---|
| `/status` | "Bot running. 3 positions open. Watching 12 stocks." |
| `/positions` | Table of all open positions with P&L |
| `/pnl` | Today's P&L + all-time summary |
| `/portfolio` | Full portfolio value breakdown |
| `/stop` | "Emergency stop. Closing all positions. Bot paused." |
| `/resume` | "Bot resumed. Starting next market scan." |
| `/report` | Send today's full PDF trading report |
| `/watchlist` | Show what bot is monitoring right now |

### Daily Automated Messages

| Time | Message |
|---|---|
| **8:00 AM** | "Good morning! Today's pre-market scan complete. Watching: INFY, HDFC, RELIANCE" |
| **9:15 AM** | "Market open. Bot is active." |
| **Whenever** | "BUY signal: INFY @ ₹1,842. SL: ₹1,814. Target: ₹1,920. Confidence: HIGH" |
| **Whenever** | "EXIT: INFY closed @ ₹1,897. Profit: +₹555 (+3.0%). Trade was open 2h 34m" |
| **3:30 PM** | "Market closed. Today: +₹2,340 (+1.8%). 3 trades, 2 wins, 1 loss." |
| **4:00 PM** | "Daily Report: [full PDF with all trades, chart screenshots, tomorrow's watchlist]" |

---

## 12. Infrastructure — 24/7 Uptime

### The Problem
The bot currently runs on your local PC. If you:
- Close the laptop → bot dies
- Lose internet connection during market hours → missed trades, open positions unmonitored
- PC crashes → positions stuck with no stop-loss management

### Solution: Cloud VM

**Recommended: AWS Lightsail or DigitalOcean Droplet**
- ₹700–1,200/month for a small VPS
- Always on, 24/7
- Low latency to NSE servers (use Mumbai region)
- Set up systemd service → bot auto-restarts if it crashes

```bash
# Run api_server.py as a persistent service
[Unit]
Description=TradeBotX API Server
After=network.target

[Service]
WorkingDirectory=/home/ubuntu/TradeBotX
ExecStart=/home/ubuntu/TradeBotX/venv/bin/python api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Market Hours Logic

```
00:00 – 08:00 IST  →  Bot sleeps (no trading)
08:00 – 09:15 IST  →  Pre-market scan, prepare watchlist
09:15 – 15:20 IST  →  ACTIVE: fast layer runs every minute, LLM on demand
15:20 – 15:30 IST  →  Close all intraday positions (last 10 min = chaotic)
15:30 – 16:00 IST  →  Post-market: review, log, update DB, send daily report
16:00 – 00:00 IST  →  Idle: DB maintenance, model updates, backtests
```

---

## 13. Paper Trading Period — Proving the Edge

> **Rule:** Never trade real money until the bot has a verified 3-month paper trading track record.

### Minimum Criteria to Go Live

| Metric | Minimum Threshold | Honest Note |
|---|---|---|
| Win Rate | > 50% after fees & slippage | Even 50% is respectable if avg win > avg loss |
| Sharpe Ratio | > 0.7 | > 1.0 is excellent. Don't expect hedge-fund Sharpe from a retail bot. |
| Max Drawdown | < 15% | 20% drawdown means you need +25% just to recover. Keep it tight. |
| Profit Factor | > 1.2 | 1.5+ is great but rare in practice |
| Total Trades | > 200 across different market conditions | 50 is NOT enough — you need bull, bear, and sideways data |
| Consecutive Losing Streak | < 6 trades | If risk management is working, 6 losses in a row should be rare |
| Time span | Must include at least one NIFTY correction (> -5%) | A bot that only saw a bull run tells you nothing |

### Paper Trading Setup
- Virtual portfolio: ₹1,00,000
- All trades logged with real prices from live Kite feed
- All risk rules enforced identically to live mode
- Daily P&L tracked and graphed
- **Must run through at least one high-VIX period (VIX > 20)**
- **Must run through at least one sideways/range-bound week**
- Treat it as if it were real money — emotions reveal bugs

---

## 14. Going Live Checklist

Before placing the first real-money trade:

- [ ] Paper trading: 200+ trades across bull/bear/sideways markets
- [ ] Sharpe ≥ 0.7 sustained over at least 4 months (not just one good month)
- [ ] Risk management: all circuit breakers tested and verified
- [ ] Stop-loss automation: confirmed it executes automatically without human approval
- [ ] Time-based exits: confirmed the bot exits stale positions, not just stop/target ones
- [ ] Emergency stop: `/stop` Telegram command closes all positions within 10 seconds
- [ ] Cloud deployment: bot running 24/7 on VPS, not local PC
- [ ] Broker API tested: paper orders placed and cancelled successfully via Kite API
- [ ] Monitoring alerts: get Telegram alert if bot crashes or API connection drops
- [ ] Start capital: **₹10,000 only** (prove live mode works before scaling up)
- [ ] **Human supervisor commitment: check dashboard at least once daily for the first 6 months**

### Capital Scaling Plan

| When | Capital | Condition |
|---|---|---|
| Start | ₹10,000 | Prove live mode works, find bugs |
| After Sharpe ≥ 0.7 sustained 3 months | ₹25,000 | Scale only if performance holds, NOT by calendar |
| After Sharpe ≥ 0.8 sustained 6 months | ₹50,000 | If max drawdown stayed < 12% |
| After 1 year of live profit | ₹1,00,000 | Only if you've survived a correction |
| Beyond | Scale by Sharpe stability | Never scale during a winning streak. Scale during boring periods when performance is consistent. |

> **Scale on consistency, not on winning streaks.** A bot that made 8% last month might have just been lucky. A bot that made 1.5% every month for 6 months has an edge.

---

## 15. Smart Stop-Loss & Take-Profit Execution

> **Core idea:** The bot should never be stuck holding a position because it couldn't get filled at the exact target price. Smart order logic ensures exits always happen.

### The Problem with Naive Targets

A naive bot sets a target at ₹1,920 and waits. The stock touches ₹1,919.80, reverses, and drops back to ₹1,860. The bot never sold because the price never hit the exact number. This is a well-known failure mode.

### Stop-Loss Execution — "Just Above Stop" Logic

When the stop-loss level is approached:

```
Entry price:     ₹1,842
Hard stop set:   ₹1,814  (1.5% below entry)

Price falls to ₹1,816 (getting close):
  → Cancel any resting limit stop order
  → Place a MARKET sell order immediately
  → Reason: better to exit at ₹1,815 than wait for ₹1,814
             and find the stock has gapped to ₹1,800

Why "just above":
  Market orders in a falling stock fill just above the stop price
  Limit orders at exactly ₹1,814 may not fill if the stock
  gaps down past it — leaving us stuck in the trade
```

**Rule:** When price is within 0.2% of stop-loss → switch from limit stop to **market order**. Accept minor slippage. The priority is **guaranteed exit**, not perfect price.

### Take-Profit Execution — "Just Below Target" Logic

When the profit target is approached:

```
Entry price:     ₹1,842
Target set:      ₹1,920  (+4.2%)

Price reaches ₹1,918 (0.1% below target):
  → Place a LIMIT sell order at ₹1,917  (0.15% below target)
  → Reason: the stock may not tick exactly to ₹1,920.
             Selling at ₹1,917 vs waiting is +₹750 vs ₹0.

If limit order at ₹1,917 not filled within 60 seconds:
  → Drop limit to ₹1,915 (0.25% below target)
If still not filled within 60 more seconds:
  → Convert to MARKET sell order
  → Accept whatever price the market gives
```

**Rule:** Target is an intention, not a hard constraint. As price approaches the target, step the limit order down aggressively. **Execution > perfection.**

### Trailing Stop — Locking In Profits

Once a trade is profitable, a trailing stop protects gains:

```
Entry:          ₹1,842
Trailing stop:  2.5% below current highest price seen

Price rises to ₹1,900:  trailing stop = ₹1,852.50  (locks in ₹10.50 profit)
Price rises to ₹1,950:  trailing stop = ₹1,901.25  (locks in ₹59.25 profit)
Price rises to ₹1,980:  trailing stop = ₹1,930.50
Price drops to ₹1,931:  → SELL at market  (profit: +₹89 locked in)
```

**Key insight:** A stock that runs from ₹1,842 to ₹1,980 and then falls should NOT be sold at the original ₹1,920 target. The trailing stop lets profits run while guaranteeing we don't give it all back.

### Full Exit Decision Tree

```
Every minute during market hours, for each position:

  LAYER 1: HARD EXITS (non-negotiable)
  Is price ≤ hard stop?            → MARKET SELL immediately
  Is price within 0.2% of stop?    → MARKET SELL (don't wait for exact price)
  Is trailing stop hit?             → MARKET SELL
  Is it 3:20 PM (intraday)?         → MARKET SELL regardless

  LAYER 2: TAKE-PROFIT EXITS
  Is price ≥ take-profit target?    → LIMIT SELL at (target - 0.15%)
  Is price within 0.1% of target?   → LIMIT SELL at (target - 0.15%)

  LAYER 3: TIME-BASED EXITS (the most important addition)
  Has position been open > 90 min with < 0.5% gain?  → EXIT at market
  Has position been open > 2 hours with gain shrinking? → EXIT at market
  Was position profitable (+1%+) but now back to flat?  → EXIT at market

  LAYER 4: MOMENTUM-DECAY EXITS
  Did the signal that triggered entry reverse?          → EXIT at market
    (e.g., RSI was oversold at entry, now overbought — signal expired)
  Did NIFTY reverse direction since entry?              → TIGHTEN stop to breakeven

  None of above → HOLD, update trailing stop
```

### Time-Based Exits — "Don't Wait Forever"

> This is the most overlooked rule in algo trading. **A trade that's going nowhere is costing you money** — not because it's losing, but because your capital is stuck and can't be used on a better setup.

The mistake most bots make: set a target at +4%, wait 3 hours, stock is at +0.2%, keep waiting, stock drifts to -1.5%, stop hit. Full loss. The trade was never going to work — the first 30 minutes of flat action told you that.

**Rules:**

```
Time after entry    Position status         Action
─────────────────   ────────────────────    ──────────────────────
< 30 min            Anything                Let it develop
30–60 min           Still flat (< +0.3%)    WATCH closely
60–90 min           Still flat (< +0.5%)    MOVE stop to breakeven
> 90 min            < +0.5% gain            EXIT at market (opportunity cost)
> 2 hours           Gain was +1.5% but      EXIT at market (momentum died)
                    now back to +0.3%
Anytime             Was +1%+, now < +0.1%   EXIT at market (NEVER let a
                                            winning trade turn into a loss)
```

**Why this matters more than target price:**
- A stock that's going to hit +4% usually gets to +1.5% in the first 30–45 minutes
- If it hasn't moved meaningfully in 90 minutes, the entry thesis is probably wrong
- Sitting and hoping is not a strategy — it's gambling with extra steps

### Partial Profit Taking — "Take What the Market Gives You"

Instead of selling 100% at the target, sell in tranches:

```
+1.0% gain  → Sell 25% of position  (recover brokerage + some profit. you're playing with house money now)
+2.0% gain  → Sell another 25%      (half the position is banked)
+3.5% gain  → Sell another 25%      (75% profit locked)
Remainder   → Trail with 2% stop   (let it run if it wants to)
```

**Why start taking profit at +1% instead of waiting for +4%:**
- The stock may never reach +4%. But it reached +1%. That's real money.
- Selling 25% at +1% means if it reverses to -1.5%, your net loss on that position is much smaller.
- If it does run to +4%, you still have 50% of the position riding.
- **A bird in the hand.** Professional traders don't hold out for home runs. They take singles and doubles all day.

### The "Decaying Edge" Problem

> **The longer you hold a position, the less your entry signal matters.**

When you buy INFY because RSI was 32 and volume surged 2.3×, that signal was valid *at that moment*. An hour later, RSI is 48 and volume is back to normal. Your original reason to be in the trade has literally expired.

The bot must ask itself every 30 minutes: **"If I weren't already in this trade, would I enter it right now?"** If the answer is no — exit. Don't hold a position just because you're already in it. That's the sunk cost fallacy.

---

## 16. Self-Improvement Loop — Learning from Every Trade

> **Core idea:** Every completed trade — win or loss — is a data point that should make the next decision better. The bot must learn from its mistakes and reinforce its successes.

### The Problem With Static Rules

A bot with fixed rules will perform the same in Year 2 as it did in Year 1, regardless of how many trades it has done. Markets evolve. What worked in 2024 may not work in 2026. The bot needs a **feedback loop**.

### What Gets Logged for Every Trade

Each completed trade (paper or live) generates a `trade_log` record with the full context at the time of the decision:

```json
{
  "trade_id": "INFY_20260422_091500",
  "ticker": "INFY.NS",
  "direction": "BUY",
  "entry_price": 1842.00,
  "exit_price": 1897.50,
  "qty": 10,
  "pnl_pct": 3.01,
  "outcome": "WIN",
  "hold_duration_minutes": 154,
  "exit_reason": "trailing_stop",

  "signals_at_entry": {
    "rsi_15m": 38.4,
    "rsi_1h": 42.1,
    "rsi_daily": 44.8,
    "macd_cross": "bullish",
    "above_vwap": true,
    "volume_surge": 2.3,
    "ema_9_21_cross": "bullish",
    "bb_position": "lower_band_bounce",
    "pattern_detected": "bull_flag",
    "india_vix": 14.2,
    "nifty_trend": "up",
    "sector_rank": 2
  },

  "llm_rating": "BUY",
  "llm_confidence_text": "Strong momentum with sector tailwind",
  "rule_score": 78,

  "market_conditions": {
    "nifty_daily_change_pct": 0.8,
    "fii_net_crore": 1240,
    "india_vix": 14.2,
    "pcr": 1.18,
    "advance_decline_ratio": 1.6
  }
}
```

### Loss Analysis — What Went Wrong

After every losing trade, the bot runs an automatic post-mortem:

```python
def analyse_loss(trade_log):
    signals = trade_log['signals_at_entry']
    conditions = trade_log['market_conditions']

    # Pattern matching against known failure conditions
    flags = []

    if signals['india_vix'] > 18:
        flags.append('HIGH_VIX_ENTRY')        # Don't trade when market is fearful

    if conditions['nifty_daily_change_pct'] < -0.5:
        flags.append('NIFTY_DOWNTREND')        # Don't buy in falling market

    if signals['rsi_15m'] > 68:
        flags.append('OVERBOUGHT_ENTRY')        # Bought at top of move

    if signals['above_vwap'] is False:
        flags.append('BELOW_VWAP_ENTRY')        # Entered in weak intraday structure

    if conditions['fii_net_crore'] < -2000:
        flags.append('FII_SELLING_HEAVILY')     # Institutions distributing

    # Log the failure signature
    db.save_loss_pattern(trade_log['trade_id'], flags)
    return flags
```

Over time, the database of `loss_patterns` reveals which combinations of conditions reliably produce losses. These become **veto rules** — conditions under which the bot refuses to enter a trade.

### Win Analysis — What Made It Work

Symmetrically, winning trades reveal which signal combinations are most reliable:

```python
def analyse_win(trade_log):
    signals = trade_log['signals_at_entry']

    # Score each signal's contribution to the win
    # (simplified — real version uses historical correlation)
    win_contributors = {}

    if signals['macd_cross'] == 'bullish':
        win_contributors['macd_cross'] += 1
    if signals['above_vwap']:
        win_contributors['above_vwap'] += 1
    if signals['volume_surge'] > 2.0:
        win_contributors['volume_surge'] += 1
    if signals['ema_9_21_cross'] == 'bullish':
        win_contributors['ema_cross'] += 1

    db.save_win_pattern(trade_log['trade_id'], win_contributors)
```

After **500+ trades across different market conditions** (not 100 — that's too small), the win/loss patterns start to become statistically meaningful. Even then, treat weight changes cautiously — overfitting to past trades is the #1 reason quant strategies fail in live trading.

### The Continuous Improvement Loop

```
Trade executed
      ↓
Outcome recorded (WIN / LOSS / BREAKEVEN)
      ↓
Post-mortem analysis runs automatically
      ↓
loss_patterns or win_patterns saved to DB
      ↓
Monthly (NOT weekly — too reactive): run pattern frequency analysis
  → "RSI > 68 at entry → 73% loss rate over 50+ trades" → add as veto rule
  → "above VWAP + volume surge → 68% win rate over 80+ trades" → increase weight
      ↓
Rule weights adjusted (max ±0.03 per cycle — small moves only)
      ↓
Backtest updated rules on 12+ months of data
  (NEVER backtest on only recent data — that's curve fitting)
      ↓
Forward-test on next 2 weeks of paper trades before deploying
      ↓
If paper Sharpe holds → deploy to live
      ↓
Bot is slightly better than it was last month
  (NOT "smarter every week" — that's overfitting)
```

> **Honest warning:** Most "self-improving" trading systems end up overfitting. They optimize for the past and fail in the future. The safest approach is to change rules **rarely and conservatively** — like adjusting a recipe by a pinch of salt, not rewriting it every week.

### Signal Weight Table (Evolves Over Time)

Each signal starts with an equal weight. Over time, wins and losses shift these weights:

```python
# rule_engine.py — weights learned from trade history
SIGNAL_WEIGHTS = {
    # Core signals (high confidence from history)
    'above_vwap':           0.18,  # Strong intraday signal
    'volume_surge_2x':      0.15,  # Smart money is moving
    'ema_9_21_cross_bull':  0.14,  # Trend confirmation
    'rsi_oversold_bounce':  0.12,  # Momentum reversal

    # Secondary signals
    'macd_cross_bull':      0.10,
    'bb_lower_bounce':      0.09,
    'sector_leader':        0.08,
    'nifty_uptrend':        0.07,

    # Weak signals (low historical predictive value)
    'pattern_bull_flag':    0.04,
    'pcr_bullish':          0.03,
}

# Minimum total score to trigger BUY signal (no trade below this)
MIN_SCORE_TO_TRADE = 0.55  # Increases as bot gets more selective over time
```

### LLM as the Final Filter, Not the Driver

With the self-learning rule engine in place, the LLM's role becomes a **sanity check**, not the primary decision maker:

```
Rule engine scores the stock at 0.72 (above MIN_SCORE)  → "Quantitative signal: BUY"
         ↓
LLM reads latest news + fundamentals                    → "No red flags found"
         ↓
Combined signal: BUY  ✓
```

If rule engine scores 0.72 but LLM says "company is facing regulatory probe" → **SKIP**.
If LLM says "BUY" but rule engine scores 0.31 → **SKIP** (LLM overruled by data).

The rule engine prevents the LLM from entering bad trades. The LLM catches news-driven risks that rules can't see.

---

## 17. Code Robustness — Minimising LLM Dependency

> **Philosophy:** The LLM is the brain for qualitative reasoning. But the skeleton, muscles, and reflexes of this bot must be deterministic, testable, and fast. You cannot unit-test an LLM. You can unit-test a rule engine.

### Why Over-Relying on LLM Is Dangerous

| Risk | Impact |
|---|---|
| **Hallucination** | LLM invents a "positive earnings surprise" that didn't happen → bad BUY |
| **Non-determinism** | Same inputs, different outputs each run. Can't debug. |
| **Speed** | 2–5 minutes per stock. Can't respond to intraday moves. |
| **Cost** | Every API call costs money. 50 stocks × 5 times/day = 250 calls/day |
| **API outage** | If OpenAI is down, the bot can't make decisions at all |
| **Context limit** | LLM truncates long reports → misses key details |

### The Robustness Architecture

```
┌─────────────────────────────────────────────────────┐
│                  HARD RULES LAYER                    │  ← Never overridden by LLM
│  • Daily loss limit hit → STOP ALL TRADING           │
│  • India VIX > 25 → NO NEW POSITIONS                 │
│  • Stop-loss hit → SELL IMMEDIATELY (market order)   │
│  • 3:20 PM → CLOSE ALL INTRADAY (no exceptions)      │
└─────────────────────────────────────────────────────┘
            ↓ (only if hard rules pass)
┌─────────────────────────────────────────────────────┐
│              DETERMINISTIC RULE ENGINE               │  ← Fast, testable, auditable
│  • Computes signal score (0.0 – 1.0)                 │
│  • Uses 10+ technical indicators                     │
│  • Pattern matching against historical win/loss data │
│  • Unit tested, backtested, version controlled       │
└─────────────────────────────────────────────────────┘
            ↓ (only if score > MIN_SCORE)
┌─────────────────────────────────────────────────────┐
│               LLM INTELLIGENCE LAYER                 │  ← Slow, qualitative
│  • News sentiment analysis                           │
│  • Earnings / regulatory red flags                   │
│  • Sector narrative check                            │
│  • Final veto or confirmation                        │
└─────────────────────────────────────────────────────┘
            ↓ (only if LLM confirms)
┌─────────────────────────────────────────────────────┐
│                 ORDER EXECUTION                      │
│  • Position size calculated (risk rules)             │
│  • Limit order placed                                │
│  • Stop-loss and trailing stop armed                 │
└─────────────────────────────────────────────────────┘
```

### What Must Be Deterministic (No LLM)

| Component | Implementation |
|---|---|
| Stop-loss execution | Pure Python: `if price <= stop: market_sell()` |
| Take-profit execution | Pure Python: `if price >= target: limit_sell(target * 0.9985)` |
| Position sizing | Formula: `risk_amount / (entry - stop) = qty` |
| Daily loss limit | Counter in DB: `if today_loss >= limit: halt()` |
| Circuit breakers | Simple conditionals, no AI needed |
| Trailing stop update | `trailing_stop = max(trailing_stop, price * 0.975)` |
| Order management | State machine: `PENDING → OPEN → EXITED` |
| Trade logging | SQLite write after every state change |
| Fast signal layer | `pandas` + `ta-lib` — pure math |

### What LLM Is Good For (Keep It Here)

| Task | Why LLM |
|---|---|
| News sentiment scoring | Reading 10 articles and summarising sentiment is hard to rule-base |
| Earnings quality assessment | Understanding "beat on EPS but missed revenue" nuance |
| Management commentary | Reading concall transcripts for tone/guidance changes |
| Regulatory/legal risk | Catching SEBI notices, court cases, promoter pledging alerts |
| Narrative synthesis | Combining macro + micro + technical into one decision |

### Code Audit Trail — Every Decision Explained

Every decision the bot makes must be explainable. No black box.

```json
{
  "decision": "BUY",
  "ticker": "INFY.NS",
  "timestamp": "2026-04-22T09:47:32+05:30",

  "rule_engine": {
    "score": 0.74,
    "threshold": 0.55,
    "signals_fired": [
      "above_vwap (weight: 0.18)",
      "volume_surge_2x (weight: 0.15)",
      "ema_9_21_cross_bull (weight: 0.14)",
      "rsi_oversold_bounce (weight: 0.12)",
      "macd_cross_bull (weight: 0.10)",
      "nifty_uptrend (weight: 0.07)"
    ],
    "veto_rules_checked": [
      "india_vix_ok: 14.2 < 25 ✓",
      "daily_loss_ok: -₹200 > -₹2000 ✓",
      "position_limit_ok: 3 < 8 ✓",
      "sector_limit_ok: IT 18% < 30% ✓"
    ]
  },

  "llm_verdict": {
    "rating": "BUY",
    "reason": "Strong Q4 results expected, IT sector FII inflows last 5 days, no red flags in recent news",
    "confidence": "HIGH"
  },

  "order": {
    "qty": 5,
    "entry_price": 1842.00,
    "stop_loss": 1814.00,
    "target": 1920.00,
    "risk_pct": 1.52,
    "position_size_pct": 6.9
  }
}
```

This log is stored in the database and shown in the dashboard. If the trade loses, you can open this log and see exactly what the bot was thinking. This is how you improve the rules.

### Version-Controlled Rules

`rule_engine.py` should be version controlled with git tags:

```
v1.0  — April 2026  — Initial 8 signals, MIN_SCORE=0.55
v1.1  — May 2026    — Added VIX veto rule after 3 losses in high-VIX market
v1.2  — June 2026   — Raised above_vwap weight from 0.15 → 0.18 based on win data
v1.3  — July 2026   — Added FII flow as secondary signal after analysis
```

Each version comes with a backtest result: "v1.2 backtested on Jan–Jun 2026: Sharpe 1.84 vs v1.1 Sharpe 1.62. Deploying."

---

## Summary: Priority Order

If we were to build everything from here, the priority is:

```
1.  Telegram Alerts              ← Complete current plan (Phase 5)
2.  Zerodha Kite API             ← Real-time data + paper order execution
3.  Smart Stop/Target Engine     ← "Just below sell / just above stop" logic
4.  Comprehensive Trade Logging  ← Full context per trade (foundation for learning)
5.  Paper Trading Engine         ← Virtual portfolio, real prices
6.  Fast Signal Layer            ← Speed fix (1-sec technical screening)
7.  Rule Engine + Signal Weights ← Deterministic, testable, auditable
8.  Self-Improvement Loop        ← Learn from losses/wins, update signal weights
9.  Risk Management Engine       ← Position sizing, circuit breakers
10. Portfolio Management         ← Know what we own at all times
11. Advanced Dashboard           ← Sharpe, Sortino, Alpha, Max Drawdown
12. Cloud Deployment             ← 24/7 uptime
13. 3-Month Paper Period         ← Prove the edge
14. Live Trading (₹10k)         ← The goal
```

### The Golden Rule

> **The LLM is the analyst. The rule engine is the trader. The risk manager is the adult in the room.**
>
> LLMs generate ideas. Rules decide whether those ideas are worth acting on.
> Risk rules decide how much to bet. Stop-losses decide when to admit the bet was wrong.
> Trade logs make sure we learn from every mistake so we never make the same one twice.

---

*Last updated: April 2026*
*Status: Phases 1–4 complete. Phase 5 next.*
*New sections added: Smart Stop/Target execution, Self-Improvement Loop, Code Robustness philosophy.*

