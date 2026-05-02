import json
from pathlib import Path
import asyncio
import logging
import queue
import threading
from typing import List, Optional
from datetime import date as dt_date
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.nse_api import get_index_stocks, screen_stocks, SUPPORTED_INDICES
import scheduler as sched
import database as db

# ── Upstox integration imports ────────────────────────────────────────────────
from upstox_auth import load_config_from_env, validate_token, UpstoxConfig
from upstox_client import (
    UpstoxClient,
    symbol_to_instrument_key,
    ALL_INSTRUMENTS,
    NIFTY_50_INSTRUMENTS,
    NIFTY_BANK_INSTRUMENTS,
)
from paper_trader import PaperTrader
import technical as ta
import signal_scanner as scanner


# ── Global Upstox state (set in lifespan) ─────────────────────────────────────
upstox_config: Optional[UpstoxConfig] = None
upstox_client: Optional[UpstoxClient] = None
paper_trader: Optional[PaperTrader] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the scheduler on startup and shut it down cleanly on exit."""
    global upstox_config, upstox_client, paper_trader

    db.init_db()
    logging.info("Database initialised")

    # ── Upstox client init ──
    upstox_config = load_config_from_env()
    if upstox_config.access_token:
        await validate_token(upstox_config)
        upstox_client = UpstoxClient(upstox_config)
        logging.info("Upstox client initialised (%s mode)", upstox_config.mode)
    else:
        logging.warning("Upstox token not set — Upstox endpoints will return errors")

    # ── Paper trader init ──
    paper_trader = PaperTrader(initial_capital=100_000)
    logging.info("Paper trader initialised with ₹%.0f capital", paper_trader.capital)

    sched.start_scheduler()
    logging.info("Scheduler initialised")

    # ── Auto-scanner: start if previously enabled ──
    scanner_cfg = scanner.load_scanner_config()
    if scanner_cfg.get("enabled", False) and upstox_client and paper_trader:
        await scanner.start_scanner(upstox_client, paper_trader)
        logging.info("Auto-scanner resumed (was enabled in config)")

    yield

    # ── Cleanup ──
    # Stop scanner first
    if scanner.scanner_state.is_running:
        await scanner.stop_scanner()
    if upstox_client:
        await upstox_client.close()
    sched.stop_scheduler()
    logging.info("All services stopped")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Helpers to detect which agent node just executed
# ---------------------------------------------------------------------------

# The ordered phases the graph walks through
PHASE_ORDER = [
    "Market Analyst",
    "Social Media Analyst",
    "News Analyst",
    "Fundamentals Analyst",
    "India Macro Analyst",
    "Bull Researcher",
    "Bear Researcher",
    "Research Manager",
    "Trader",
    "Aggressive Analyst",
    "Conservative Analyst",
    "Neutral Analyst",
    "Portfolio Manager",
]

STATE_REPORT_FIELDS = [
    ("market_report",       "Market Analyst"),
    ("sentiment_report",    "Social Media Analyst"),
    ("news_report",         "News Analyst"),
    ("fundamentals_report", "Fundamentals Analyst"),
    ("india_macro_report",   "India Macro Analyst"),
]


def _detect_phase(state: dict) -> str | None:
    """Try to figure out which node just ran by looking at the sender field."""
    return state.get("sender")


def _safe_serialize(obj):
    """Best-effort JSON serialization – turn non-serializable objects into strings."""
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_serialize(i) for i in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def _extract_reports(state: dict) -> dict:
    """Pull the interesting reports out of the final state dict."""
    reports: dict = {}

    for field, label in STATE_REPORT_FIELDS:
        val = state.get(field, "")
        if val:
            reports[label] = val

    # Investment debate
    ids = state.get("investment_debate_state", {})
    if ids:
        reports["Bull Researcher"] = ids.get("bull_history", "")
        reports["Bear Researcher"] = ids.get("bear_history", "")
        reports["Research Manager"] = ids.get("judge_decision", "")

    reports["Trader"] = state.get("trader_investment_plan", "")

    # Risk debate
    rds = state.get("risk_debate_state", {})
    if rds:
        reports["Aggressive Analyst"] = rds.get("aggressive_history", "")
        reports["Conservative Analyst"] = rds.get("conservative_history", "")
        reports["Neutral Analyst"] = rds.get("neutral_history", "")

    reports["Portfolio Manager"] = state.get("final_trade_decision", "")

    return _safe_serialize(reports)


# ---------------------------------------------------------------------------
# Results history endpoint
# ---------------------------------------------------------------------------

RATING_KEYWORDS = ["STRONG BUY", "OVERWEIGHT", "UNDERWEIGHT", "STRONG SELL", "BUY", "SELL", "HOLD"]


def _extract_rating(text: str) -> str:
    """Pull the first matching rating keyword from final_trade_decision text."""
    upper = text.upper()
    for kw in RATING_KEYWORDS:
        if kw in upper:
            return kw
    return "HOLD"


def _fetch_price(ticker: str):
    """Best-effort current price fetch for prediction logging."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).fast_info
        price = getattr(info, "last_price", None)
        return float(price) if price else None
    except Exception:
        return None


@app.get("/api/results")
async def get_results():
    """
    Walk the results/ directory and return all past analysis logs.
    Each ticker can have multiple dated logs — all are returned, newest first.
    """
    results_dir = Path("results")
    entries: list = []

    if not results_dir.exists():
        return {"results": []}

    for ticker_dir in sorted(results_dir.iterdir()):
        if not ticker_dir.is_dir():
            continue
        logs_dir = ticker_dir / "TradingAgentsStrategy_logs"
        if not logs_dir.exists():
            continue
        for log_file in sorted(logs_dir.glob("full_states_log_*.json"), reverse=True):
            try:
                with open(log_file, encoding="utf-8") as fh:
                    data = json.load(fh)

                final = data.get("final_trade_decision", "")
                rating = _extract_rating(final)

                # Build per-agent report dict (same shape as the SSE result)
                ids = data.get("investment_debate_state") or {}
                rds = data.get("risk_debate_state") or {}

                reports = {
                    "Market Analyst":        data.get("market_report", ""),
                    "Social Media Analyst":  data.get("sentiment_report", ""),
                    "News Analyst":          data.get("news_report", ""),
                    "Fundamentals Analyst":  data.get("fundamentals_report", ""),
                    "India Macro Analyst":   data.get("india_macro_report", ""),
                    "Bull Researcher":       ids.get("bull_history", ""),
                    "Bear Researcher":       ids.get("bear_history", ""),
                    "Research Manager":      ids.get("judge_decision", ""),
                    "Trader":                data.get("trader_investment_decision", ""),
                    "Aggressive Analyst":    rds.get("aggressive_history", ""),
                    "Conservative Analyst":  rds.get("conservative_history", ""),
                    "Neutral Analyst":       rds.get("neutral_history", ""),
                    "Portfolio Manager":     final,
                }

                entries.append({
                    "ticker": data.get("company_of_interest", ticker_dir.name),
                    "date":   data.get("trade_date",
                                       log_file.stem.replace("full_states_log_", "")),
                    "rating": rating,
                    "decision": final,
                    "reports": _safe_serialize(reports),
                })
            except Exception as exc:
                logging.warning("Failed to parse %s: %s", log_file, exc)

    # Sort newest date first
    entries.sort(key=lambda e: e["date"], reverse=True)
    return {"results": entries}


# ---------------------------------------------------------------------------
# NSE Watchlist & Screener endpoints
# ---------------------------------------------------------------------------

@app.get("/api/indices")
async def list_indices():
    """Return the list of supported NSE indices."""
    return {"indices": list(SUPPORTED_INDICES.keys())}


@app.get("/api/watchlist")
async def get_watchlist(index: str = Query("NIFTY 50")):
    """Fetch all stocks in an NSE index with live market data."""
    try:
        result = await asyncio.to_thread(get_index_stocks, index)
        return result
    except Exception as e:
        logging.exception("Failed to fetch watchlist")
        return {"error": str(e)}


@app.get("/api/screen")
async def screen_stocks_endpoint(
    index: str = Query("NIFTY 50"),
    pct_threshold: float = Query(2.0),
    near_52w: float = Query(5.0),
):
    """Fetch index stocks and flag interesting ones."""
    try:
        result = await asyncio.to_thread(
            screen_stocks, index, pct_threshold, near_52w
        )
        return result
    except Exception as e:
        logging.exception("Failed to screen stocks")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# SSE streaming endpoint
# ---------------------------------------------------------------------------

@app.get("/api/analyze/stream")
async def analyze_stream(
    ticker: str = Query(...),
    date: str = Query(...),
):
    """
    Server-Sent Events endpoint.
    Streams progress events as each agent node completes,
    then sends a final 'result' event with all reports + decision.
    """

    event_queue: queue.Queue = queue.Queue()

    def _run():
        try:
            config = DEFAULT_CONFIG.copy()
            config["deep_think_llm"] = "gpt-5.4-mini"
            config["quick_think_llm"] = "gpt-5.4-mini"
            config["max_debate_rounds"] = 1
            config["data_vendors"] = {
                "core_stock_apis": "yfinance",
                "technical_indicators": "yfinance",
                "fundamental_data": "yfinance",
                "news_data": "yfinance",
            }

            ta = TradingAgentsGraph(debug=True, config=config)
            ta.ticker = ticker

            seen_reports: set = set()
            final_state = None

            for chunk in ta.graph.stream(
                ta.propagator.create_initial_state(ticker, date),
                **ta.propagator.get_graph_args(),
            ):
                final_state = chunk

                # Detect which report fields just appeared
                for field, label in STATE_REPORT_FIELDS:
                    val = chunk.get(field, "")
                    if val and label not in seen_reports:
                        seen_reports.add(label)
                        event_queue.put({
                            "type": "progress",
                            "agent": label,
                            "status": "done",
                        })

                # Detect sender-based progress
                sender = chunk.get("sender")
                if sender and sender not in seen_reports:
                    seen_reports.add(sender)
                    event_queue.put({
                        "type": "progress",
                        "agent": sender,
                        "status": "done",
                    })

            if final_state is None:
                event_queue.put({"type": "error", "message": "No state returned from graph"})
                return

            # Process final signal
            ta.curr_state = final_state
            decision = ta.process_signal(final_state.get("final_trade_decision", ""))
            ta._log_state(date, final_state)

            reports = _extract_reports(final_state)
            rating = _extract_rating(final_state.get("final_trade_decision", ""))

            # Save prediction to database
            try:
                price = _fetch_price(ticker)
                db.save_prediction(
                    ticker=ticker,
                    trade_date=date,
                    decision=decision,
                    rating=rating,
                    price_at_prediction=price,
                    reports=reports,
                )
            except Exception as _dbe:
                logging.warning("Failed to save prediction to DB: %s", _dbe)

            event_queue.put({
                "type": "result",
                "decision": decision,
                "reports": reports,
            })

        except Exception as e:
            logging.exception("Error during agent execution")
            event_queue.put({"type": "error", "message": str(e)})

        finally:
            event_queue.put(None)  # sentinel

    # Kick off in a background thread
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    async def _event_generator():
        while True:
            try:
                event = event_queue.get(timeout=0.5)
            except queue.Empty:
                # Send a keepalive comment to prevent timeout
                yield ": keepalive\n\n"
                continue

            if event is None:
                break

            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Keep the original POST endpoint as a fallback
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    ticker: str
    date: str


@app.post("/api/analyze")
async def analyze_stock(request: AnalyzeRequest):
    def run_agents():
        config = DEFAULT_CONFIG.copy()
        config["deep_think_llm"] = "gpt-5.4-mini"
        config["quick_think_llm"] = "gpt-5.4-mini"
        config["max_debate_rounds"] = 1
        config["data_vendors"] = {
            "core_stock_apis": "yfinance",
            "technical_indicators": "yfinance",
            "fundamental_data": "yfinance",
            "news_data": "yfinance",
        }
        ta = TradingAgentsGraph(debug=True, config=config)
        states, decision = ta.propagate(request.ticker, request.date)
        return {"decision": decision, "states": states}

    try:
        result = await asyncio.to_thread(run_agents)
        return result
    except Exception as e:
        logging.error(f"Error during agent execution: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Custom Watchlist CRUD
# ---------------------------------------------------------------------------

WATCHLISTS_FILE = Path("watchlists.json")


def _load_watchlists() -> dict:
    """Load custom watchlists from disk. Returns {"tickers": [...]}"""
    if WATCHLISTS_FILE.exists():
        try:
            return json.loads(WATCHLISTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tickers": []}


def _save_watchlists(data: dict) -> None:
    WATCHLISTS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


@app.get("/api/watchlist/custom")
async def get_custom_watchlist():
    """Return the user's custom watchlist."""
    return _load_watchlists()


class TickerBody(BaseModel):
    ticker: str


@app.post("/api/watchlist/custom")
async def add_to_watchlist(body: TickerBody):
    """Add a ticker to the custom watchlist (e.g. 'INFY.NS')."""
    ticker = body.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker is required")
    data = _load_watchlists()
    if ticker not in data["tickers"]:
        data["tickers"].append(ticker)
        _save_watchlists(data)
    return data


@app.delete("/api/watchlist/custom/{ticker}")
async def remove_from_watchlist(ticker: str):
    """Remove a ticker from the custom watchlist."""
    data = _load_watchlists()
    ticker = ticker.upper()
    data["tickers"] = [t for t in data["tickers"] if t != ticker]
    _save_watchlists(data)
    return data


# ---------------------------------------------------------------------------
# Batch analysis SSE endpoint
# ---------------------------------------------------------------------------

class BatchAnalyzeRequest(BaseModel):
    tickers: List[str]


@app.post("/api/analyze/batch")
async def analyze_batch(request: BatchAnalyzeRequest):
    """
    SSE endpoint that runs the agent pipeline sequentially for each ticker
    and streams per-ticker progress + results.

    Events:
      {type: 'batch_start',   total: N}
      {type: 'ticker_start',  ticker: X, index: i, total: N}
      {type: 'progress',      ticker: X, agent: Y, status: 'done'}
      {type: 'ticker_result', ticker: X, index: i, total: N, decision: ..., rating: ...}
      {type: 'ticker_error',  ticker: X, index: i, error: ...}
      {type: 'batch_done'}
    """
    tickers = [t.strip().upper() for t in request.tickers if t.strip()]
    if not tickers:
        raise HTTPException(status_code=400, detail="No tickers provided")

    today = str(dt_date.today())
    event_queue: queue.Queue = queue.Queue()

    def _run_batch():
        event_queue.put({"type": "batch_start", "total": len(tickers)})
        for i, ticker in enumerate(tickers):
            event_queue.put({
                "type": "ticker_start",
                "ticker": ticker,
                "index": i,
                "total": len(tickers),
            })
            try:
                config = DEFAULT_CONFIG.copy()
                config["deep_think_llm"] = "gpt-5.4-mini"
                config["quick_think_llm"] = "gpt-5.4-mini"
                config["max_debate_rounds"] = 1
                config["data_vendors"] = {
                    "core_stock_apis": "yfinance",
                    "technical_indicators": "yfinance",
                    "fundamental_data": "yfinance",
                    "news_data": "yfinance",
                }

                ta = TradingAgentsGraph(debug=True, config=config)
                ta.ticker = ticker

                seen_reports: set = set()
                final_state = None

                for chunk in ta.graph.stream(
                    ta.propagator.create_initial_state(ticker, today),
                    **ta.propagator.get_graph_args(),
                ):
                    final_state = chunk

                    for field, label in STATE_REPORT_FIELDS:
                        val = chunk.get(field, "")
                        if val and label not in seen_reports:
                            seen_reports.add(label)
                            event_queue.put({
                                "type": "progress",
                                "ticker": ticker,
                                "agent": label,
                                "status": "done",
                            })

                    sender = chunk.get("sender")
                    if sender and sender not in seen_reports:
                        seen_reports.add(sender)
                        event_queue.put({
                            "type": "progress",
                            "ticker": ticker,
                            "agent": sender,
                            "status": "done",
                        })

                if final_state is None:
                    raise ValueError("No state returned from graph")

                ta.curr_state = final_state
                decision = ta.process_signal(final_state.get("final_trade_decision", ""))
                ta._log_state(today, final_state)
                rating = _extract_rating(final_state.get("final_trade_decision", ""))

                event_queue.put({
                    "type": "ticker_result",
                    "ticker": ticker,
                    "index": i,
                    "total": len(tickers),
                    "decision": decision,
                    "rating": rating,
                    "reports": _extract_reports(final_state),
                })

            except Exception as e:
                logging.exception("Batch error on %s", ticker)
                event_queue.put({
                    "type": "ticker_error",
                    "ticker": ticker,
                    "index": i,
                    "error": str(e),
                })

        event_queue.put({"type": "batch_done"})
        event_queue.put(None)  # sentinel

    thread = threading.Thread(target=_run_batch, daemon=True)
    thread.start()

    async def _event_generator():
        while True:
            try:
                event = event_queue.get(timeout=0.5)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Scheduler endpoints
# ---------------------------------------------------------------------------

@app.get("/api/scheduler/status")
async def scheduler_status():
    """Return scheduler state: enabled, next run time, last run summary."""
    return sched.get_status()


@app.get("/api/scheduler/config")
async def get_scheduler_config():
    """Return current scheduler configuration."""
    return sched.load_config()


class SchedulerConfigBody(BaseModel):
    enabled: bool | None = None
    scan_time_ist: str | None = None
    watchlist_source: str | None = None
    index_name: str | None = None
    max_stocks_to_analyse: int | None = None
    pct_threshold: float | None = None
    rsi_oversold: float | None = None
    rsi_overbought: float | None = None
    volume_spike_multiplier: float | None = None
    only_analyse_flagged: bool | None = None


@app.post("/api/scheduler/config")
async def update_scheduler_config(body: SchedulerConfigBody):
    """Update scheduler config and reschedule immediately."""
    cfg = sched.load_config()
    updates = body.model_dump(exclude_none=True)
    cfg.update(updates)
    sched.save_config(cfg)
    sched.reschedule(cfg)
    return cfg


@app.post("/api/scheduler/run-now")
async def run_now():
    """
    Trigger an immediate pre-market scan in a background thread.
    Returns immediately — poll /api/scheduler/status for progress.
    """
    if sched._scan_running:
        raise HTTPException(status_code=409, detail="Scan already running")

    def _bg():
        sched.run_morning_scan(trigger="manual")

    threading.Thread(target=_bg, daemon=True).start()
    return {"message": "Scan started", "trigger": "manual"}


@app.get("/api/morning-report")
async def get_morning_report():
    """Return the most recent morning scan report."""
    from scheduler import REPORT_FILE
    if not REPORT_FILE.exists():
        return {"report": None}
    try:
        data = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        return {"report": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Predictions endpoints
# ---------------------------------------------------------------------------

@app.get("/api/predictions")
async def list_predictions(
    limit: int = Query(100),
    offset: int = Query(0),
    rating: str = Query(None),
):
    """Return all predictions, newest first, optionally filtered by rating."""
    preds = await asyncio.to_thread(db.get_predictions, limit, offset, rating)
    total = await asyncio.to_thread(db.get_total_count, rating)
    return {"predictions": preds, "total": total}


@app.get("/api/predictions/stats")
async def prediction_stats():
    """Return accuracy statistics: win rate, avg return, per-rating breakdown."""
    stats = await asyncio.to_thread(db.get_stats)
    return stats


@app.post("/api/predictions/update-outcomes")
async def trigger_update_outcomes(days: int = Query(3)):
    """
    Check predictions older than `days` days, fetch current price,
    and compute return % + win/loss.
    """
    def _run():
        return db.update_outcomes(days_since=days)
    updated = await asyncio.to_thread(_run)
    return {"updated": updated, "days_since": days}


# ---------------------------------------------------------------------------
# Upstox Market Data endpoints
# ---------------------------------------------------------------------------

def _require_upstox() -> UpstoxClient:
    """Guard: raise 503 if Upstox is not configured."""
    if upstox_client is None or upstox_config is None or not upstox_config.access_token:
        raise HTTPException(
            status_code=503,
            detail="Upstox not configured — set UPSTOX_ACCESS_TOKEN in .env",
        )
    return upstox_client


@app.get("/api/upstox/status")
async def upstox_status():
    """Return Upstox connection status and token validity."""
    if upstox_config is None:
        return {"configured": False}
    return {
        "configured": bool(upstox_config.access_token),
        "valid": upstox_config.is_valid,
        "mode": upstox_config.mode,
        "user": upstox_config.user_name or None,
        "validated_at": upstox_config.validated_at.isoformat() if upstox_config.validated_at else None,
    }


@app.get("/api/upstox/quote/{symbol}")
async def upstox_quote(symbol: str):
    """Get full market quote for a symbol via Upstox."""
    client = _require_upstox()
    quote = await client.get_quote_by_symbol(symbol)
    if quote is None:
        raise HTTPException(status_code=404, detail=f"No quote found for {symbol}")
    return {"symbol": symbol, "quote": quote}


@app.get("/api/upstox/ltp/{symbol}")
async def upstox_ltp(symbol: str):
    """Get last traded price for a symbol via Upstox."""
    client = _require_upstox()
    price = await client.get_ltp_by_symbol(symbol)
    if price is None:
        raise HTTPException(status_code=404, detail=f"No LTP for {symbol}")
    return {"symbol": symbol, "ltp": price}


@app.get("/api/upstox/candles/{symbol}")
async def upstox_candles(
    symbol: str,
    unit: str = Query("days", description="minutes, hours, days, weeks, months"),
    interval: str = Query("1"),
    from_date: str = Query(None),
    to_date: str = Query(None),
):
    """Get historical candle data for a symbol."""
    client = _require_upstox()
    df = await client.get_candles_as_df(symbol, unit, interval, to_date, from_date)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No candle data for {symbol}")
    # Convert to JSON-safe format
    records = df.to_dict(orient="records")
    for r in records:
        if "timestamp" in r:
            r["timestamp"] = str(r["timestamp"])
    return {"symbol": symbol, "candles": records, "count": len(records)}


@app.get("/api/upstox/signals/{symbol}")
async def upstox_signals(
    symbol: str,
    from_date: str = Query(None),
    to_date: str = Query(None),
):
    """
    Get technical indicator signal score for a symbol (Fix #8: dual-timeframe).
    Fetches daily candles for trend indicators + intraday 5-min candles for VWAP/momentum.
    """
    client = _require_upstox()

    # Fetch daily candles (for RSI, MACD, EMA, Bollinger, ATR)
    df = await client.get_candles_as_df(symbol, "days", "1", to_date, from_date)
    if df is None or len(df) < 50:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough candle data for {symbol} (need ≥50 days)",
        )

    # Try to fetch intraday 5-min candles (for VWAP + momentum)
    intraday_df = None
    try:
        intraday_df = await client.get_intraday_candles_as_df(symbol, "5")
    except Exception as exc:
        logger.warning("Could not fetch intraday candles for %s: %s", symbol, exc)

    signal = ta.generate_signal_score(df, intraday_df)
    return {"symbol": symbol, "signal": signal}


@app.get("/api/upstox/instruments")
async def list_instruments():
    """List all supported instrument symbols."""
    return {
        "nifty_50": list(NIFTY_50_INSTRUMENTS.keys()),
        "nifty_bank": list(NIFTY_BANK_INSTRUMENTS.keys()),
        "total": len(ALL_INSTRUMENTS),
    }


@app.get("/api/upstox/ltp/batch")
async def batch_ltp(index: str = Query("NIFTY50")):
    """
    Get LTP for all stocks in an index in a single API call (Fix #7).
    Much faster than 47 individual calls.
    """
    client = _require_upstox()
    if index.upper() in ("NIFTY50", "NIFTY 50"):
        symbols = list(NIFTY_50_INSTRUMENTS.keys())
    elif index.upper() in ("NIFTYBANK", "NIFTY BANK", "NIFTY_BANK"):
        symbols = list(NIFTY_BANK_INSTRUMENTS.keys())
    else:
        symbols = list(ALL_INSTRUMENTS.keys())
    prices = await client.get_batch_ltp(symbols)
    return {"index": index, "count": len(prices), "prices": prices}


@app.get("/api/upstox/movers")
async def market_movers(
    index: str = Query("NIFTY50"),
    threshold: float = Query(0.5, description="Min % change from open"),
):
    """
    Get stocks that moved > threshold% from open (smart API strategy).
    Only these need full signal analysis.
    """
    client = _require_upstox()
    if index.upper() in ("NIFTY50", "NIFTY 50"):
        symbols = list(NIFTY_50_INSTRUMENTS.keys())
    elif index.upper() in ("NIFTYBANK", "NIFTY BANK", "NIFTY_BANK"):
        symbols = list(NIFTY_BANK_INSTRUMENTS.keys())
    else:
        symbols = list(ALL_INSTRUMENTS.keys())
    movers = await client.get_movers(symbols, threshold)
    return {"index": index, "threshold_pct": threshold, "count": len(movers), "movers": movers}


@app.get("/api/market/status")
async def get_market_status():
    """Get current NSE market status (open/closed, holiday check)."""
    from nse_holidays import market_status as ms
    return ms()


# ---------------------------------------------------------------------------
# Paper Trading endpoints
# ---------------------------------------------------------------------------

class PaperTradeEntry(BaseModel):
    symbol: str
    quantity: int
    price: float
    stop_loss: float
    target_price: float
    strategy: str = "manual"


class PaperTradeExit(BaseModel):
    symbol: str
    price: float
    reason: str = "MANUAL"


@app.get("/api/paper/portfolio")
async def paper_portfolio():
    """Get current paper trading portfolio state."""
    if paper_trader is None:
        raise HTTPException(status_code=503, detail="Paper trader not initialised")
    return paper_trader.get_portfolio_state()


@app.post("/api/paper/buy")
async def paper_buy(body: PaperTradeEntry):
    """Enter a paper trade (BUY)."""
    if paper_trader is None:
        raise HTTPException(status_code=503, detail="Paper trader not initialised")
    ikey = symbol_to_instrument_key(body.symbol)
    if not ikey:
        raise HTTPException(status_code=400, detail=f"Unknown symbol: {body.symbol}")
    result = paper_trader.enter_trade(
        symbol=body.symbol,
        instrument_key=ikey,
        quantity=body.quantity,
        price=body.price,
        stop_loss=body.stop_loss,
        target_price=body.target_price,
        strategy=body.strategy,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/paper/sell")
async def paper_sell(body: PaperTradeExit):
    """Exit a paper trade (SELL)."""
    if paper_trader is None:
        raise HTTPException(status_code=503, detail="Paper trader not initialised")
    result = paper_trader.exit_trade(
        symbol=body.symbol,
        price=body.price,
        reason=body.reason,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/paper/history")
async def paper_history(limit: int = Query(50)):
    """Get paper trade history."""
    if paper_trader is None:
        raise HTTPException(status_code=503, detail="Paper trader not initialised")
    trades = paper_trader.get_trade_history(limit)
    return {"trades": trades, "count": len(trades)}


@app.get("/api/paper/performance")
async def paper_performance():
    """Get paper trading performance summary."""
    if paper_trader is None:
        raise HTTPException(status_code=503, detail="Paper trader not initialised")
    return paper_trader.get_performance_summary()


# ---------------------------------------------------------------------------
# Auto-Scanner endpoints (Step 8: Auto Paper Trading Bot)
# ---------------------------------------------------------------------------

@app.post("/api/scanner/start")
async def start_auto_scanner():
    """Start the auto paper trading scanner."""
    if upstox_client is None or paper_trader is None:
        raise HTTPException(
            status_code=503,
            detail="Upstox client or paper trader not initialised",
        )
    result = await scanner.start_scanner(upstox_client, paper_trader)
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@app.post("/api/scanner/stop")
async def stop_auto_scanner():
    """Stop the auto paper trading scanner."""
    result = await scanner.stop_scanner()
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@app.get("/api/scanner/status")
async def scanner_status():
    """Get current auto-scanner status and stats."""
    return scanner.get_scanner_status()


@app.get("/api/scanner/config")
async def get_scanner_config():
    """Get scanner configuration."""
    return scanner.load_scanner_config()


class ScannerConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    interval_minutes: Optional[int] = None
    buy_score_threshold: Optional[float] = None
    sell_score_threshold: Optional[float] = None
    max_auto_positions: Optional[int] = None
    force_close_time: Optional[str] = None
    position_size_pct: Optional[float] = None
    mover_threshold_pct: Optional[float] = None


@app.post("/api/scanner/config")
async def update_scanner_config(body: ScannerConfigUpdate):
    """Update scanner configuration."""
    cfg = scanner.load_scanner_config()
    updates = body.model_dump(exclude_none=True)
    cfg.update(updates)
    scanner.save_scanner_config(cfg)
    return cfg


@app.get("/api/scanner/log")
async def scanner_log(limit: int = Query(20)):
    """Get recent scanner scan logs."""
    log_file = scanner.SCANNER_LOG_FILE
    if not log_file.exists():
        return {"logs": [], "count": 0}
    try:
        logs = json.loads(log_file.read_text(encoding="utf-8"))
        recent = logs[-limit:]
        return {"logs": list(reversed(recent)), "count": len(recent)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/scanner/scan-now")
async def trigger_single_scan():
    """Trigger a single scan immediately (doesn't need scanner running)."""
    if upstox_client is None or paper_trader is None:
        raise HTTPException(
            status_code=503,
            detail="Upstox client or paper trader not initialised",
        )
    result = await scanner.run_signal_scan(upstox_client, paper_trader)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
