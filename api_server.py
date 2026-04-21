import json
from pathlib import Path
import asyncio
import logging
import queue
import threading

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.nse_api import get_index_stocks, screen_stocks, SUPPORTED_INDICES

app = FastAPI()

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
