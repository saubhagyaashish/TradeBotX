"""scheduler.py — Background pre-market scanner for TradeBotX.

Runs a full screener + agent pipeline at a configured IST time each day.
Results are written to morning_report.json and the results/ directory.
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from tradingagents.dataflows.nse_api import (
    screen_stocks,
    SUPPORTED_INDICES,
)

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")
CONFIG_FILE = Path("config.json")
REPORT_FILE = Path("morning_report.json")
WATCHLISTS_FILE = Path("watchlists.json")

DEFAULT_CONFIG: dict = {
    "enabled": True,
    "scan_time_ist": "08:30",
    "watchlist_source": "custom",   # "custom" | "index"
    "index_name": "NIFTY 50",
    "max_stocks_to_analyse": 5,
    "pct_threshold": 2.0,
    "rsi_oversold": 32.0,
    "rsi_overbought": 68.0,
    "volume_spike_multiplier": 2.0,
    "only_analyse_flagged": True,
}

# ── Rating extraction (no import from api_server to avoid circular deps) ─────
_RATING_KEYWORDS = ["STRONG BUY", "OVERWEIGHT", "UNDERWEIGHT", "STRONG SELL",
                    "BUY", "SELL", "HOLD"]


def _extract_rating(text: str) -> str:
    upper = text.upper()
    for kw in _RATING_KEYWORDS:
        if kw in upper:
            return kw
    return "HOLD"


# ── Config helpers ────────────────────────────────────────────────────────────

def load_config() -> dict:
    """Load scheduler config from config.json, merged with defaults."""
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update(raw.get("scheduler", {}))
        except Exception as exc:
            logger.warning("Failed to load config.json: %s", exc)
    return cfg


def save_config(cfg: dict) -> None:
    """Persist scheduler config back to config.json."""
    full: dict = {}
    if CONFIG_FILE.exists():
        try:
            full = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    full["scheduler"] = cfg
    CONFIG_FILE.write_text(json.dumps(full, indent=2), encoding="utf-8")


# ── Watchlist loading ─────────────────────────────────────────────────────────

def _load_tickers(cfg: dict) -> list[str]:
    """Return a flat list of ticker strings based on config source."""
    if cfg["watchlist_source"] == "custom":
        try:
            data = json.loads(WATCHLISTS_FILE.read_text(encoding="utf-8"))
            return [t.strip() for t in data.get("tickers", []) if t.strip()]
        except Exception:
            return []
    else:
        index = cfg.get("index_name", "NIFTY 50")
        syms = SUPPORTED_INDICES.get(index.upper(), [])
        return [f"{s}.NS" for s in syms]


# ── Core scan function ────────────────────────────────────────────────────────

_scan_lock = threading.Lock()
_scan_running = False


def run_morning_scan(trigger: str = "scheduled") -> dict:
    """
    Execute the pre-market scan:
      1. Load tickers from configured source.
      2. Screen for interesting stocks (index source only).
      3. Run full 13-agent pipeline on top N tickers.
      4. Write morning_report.json.
    """
    global _scan_running

    if not _scan_lock.acquire(blocking=False):
        logger.warning("Scan already running — skipping duplicate trigger")
        return {"error": "Scan already running"}

    _scan_running = True
    now_ist = datetime.now(IST)

    report: dict = {
        "trigger": trigger,
        "started_at": now_ist.isoformat(),
        "finished_at": None,
        "config_snapshot": load_config(),
        "screened_count": 0,
        "flagged_count": 0,
        "analysed_count": 0,
        "results": [],
        "errors": [],
    }

    try:
        logger.info("Morning scan started (trigger=%s)", trigger)
        cfg = report["config_snapshot"]

        # Step 1 — load tickers
        tickers = _load_tickers(cfg)
        if not tickers:
            report["errors"].append("No tickers in watchlist — add tickers via the Watchlist tab")
            return report

        report["screened_count"] = len(tickers)
        today = now_ist.strftime("%Y-%m-%d")

        # Step 2 — screen (index source) or use all (custom watchlist)
        if cfg["watchlist_source"] == "index":
            logger.info("Screening index %s for flagged stocks…", cfg["index_name"])
            screen_result = screen_stocks(
                index_name=cfg["index_name"],
                pct_change_threshold=cfg["pct_threshold"],
                near_52w_pct=5.0,
                rsi_oversold=cfg["rsi_oversold"],
                rsi_overbought=cfg["rsi_overbought"],
                volume_spike_multiplier=cfg["volume_spike_multiplier"],
            )
            flagged = screen_result.get("flagged", [])
            report["flagged_count"] = len(flagged)
            if cfg["only_analyse_flagged"]:
                tickers_to_analyse = [s["ticker"] for s in flagged[: cfg["max_stocks_to_analyse"]]]
            else:
                tickers_to_analyse = [s["ticker"] for s in screen_result.get("stocks", [])[: cfg["max_stocks_to_analyse"]]]
        else:
            # Custom watchlist — treat every ticker as worth analysing
            report["flagged_count"] = len(tickers)
            tickers_to_analyse = tickers[: cfg["max_stocks_to_analyse"]]

        logger.info("Will analyse %d ticker(s): %s", len(tickers_to_analyse), tickers_to_analyse)

        # Step 3 — run agent pipeline
        # Lazy import to avoid slow startup when module is loaded
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG as AGENT_DEFAULT

        for ticker in tickers_to_analyse:
            try:
                logger.info("  → Running pipeline for %s", ticker)
                agent_cfg = AGENT_DEFAULT.copy()
                agent_cfg["deep_think_llm"] = "gpt-5.4-mini"
                agent_cfg["quick_think_llm"] = "gpt-5.4-mini"
                agent_cfg["max_debate_rounds"] = 1
                agent_cfg["data_vendors"] = {
                    "core_stock_apis": "yfinance",
                    "technical_indicators": "yfinance",
                    "fundamental_data": "yfinance",
                    "news_data": "yfinance",
                }

                ta = TradingAgentsGraph(debug=True, config=agent_cfg)
                ta.ticker = ticker
                final_state: Optional[dict] = None

                for chunk in ta.graph.stream(
                    ta.propagator.create_initial_state(ticker, today),
                    **ta.propagator.get_graph_args(),
                ):
                    final_state = chunk

                if final_state:
                    decision = ta.process_signal(final_state.get("final_trade_decision", ""))
                    ta._log_state(today, final_state)
                    rating = _extract_rating(final_state.get("final_trade_decision", ""))
                    report["results"].append({
                        "ticker": ticker,
                        "rating": rating,
                        "decision": decision,
                    })
                    report["analysed_count"] += 1
                    logger.info("    %s → %s", ticker, rating)

                    # Persist to predictions database
                    try:
                        import database as db
                        price = db.fetch_price(ticker)
                        db.save_prediction(
                            ticker=ticker,
                            trade_date=today,
                            decision=decision,
                            rating=rating,
                            price_at_prediction=price,
                        )
                    except Exception as _dbe:
                        logger.warning("Failed to save prediction for %s: %s", ticker, _dbe)


            except Exception as exc:
                logger.exception("Pipeline error for %s", ticker)
                report["errors"].append(f"{ticker}: {exc}")

    except Exception as exc:
        logger.exception("Morning scan top-level failure")
        report["errors"].append(str(exc))

    finally:
        report["finished_at"] = datetime.now(IST).isoformat()
        REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
        _scan_running = False
        _scan_lock.release()
        logger.info(
            "Morning scan complete — analysed %d, errors %d",
            report["analysed_count"], len(report["errors"]),
        )

    return report


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

_scheduler: Optional[BackgroundScheduler] = None


def _build_trigger(scan_time_ist: str) -> CronTrigger:
    """Parse 'HH:MM' string into a CronTrigger in IST timezone."""
    parts = scan_time_ist.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return CronTrigger(hour=hour, minute=minute, timezone=IST)


def start_scheduler() -> None:
    """Start the background scheduler. Called once at FastAPI startup."""
    global _scheduler

    cfg = load_config()
    _scheduler = BackgroundScheduler(timezone=IST)

    if cfg.get("enabled", True):
        trigger = _build_trigger(cfg.get("scan_time_ist", "08:30"))
        _scheduler.add_job(
            run_morning_scan,
            trigger=trigger,
            id="morning_scan",
            name="Pre-market scan",
            replace_existing=True,
            kwargs={"trigger": "scheduled"},
        )
        logger.info(
            "Scheduler started — next scan at %s IST", cfg.get("scan_time_ist", "08:30")
        )
    else:
        logger.info("Scheduler started but DISABLED in config")

    _scheduler.start()


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def reschedule(cfg: dict) -> None:
    """Apply updated config to the running scheduler."""
    global _scheduler
    if not _scheduler:
        return

    _scheduler.remove_all_jobs()
    if cfg.get("enabled", True):
        trigger = _build_trigger(cfg.get("scan_time_ist", "08:30"))
        _scheduler.add_job(
            run_morning_scan,
            trigger=trigger,
            id="morning_scan",
            name="Pre-market scan",
            replace_existing=True,
            kwargs={"trigger": "scheduled"},
        )


def get_status() -> dict:
    """Return current scheduler state as a JSON-serialisable dict."""
    cfg = load_config()
    job = _scheduler.get_job("morning_scan") if _scheduler else None

    next_run: Optional[str] = None
    if job and job.next_run_time:
        next_run = job.next_run_time.astimezone(IST).isoformat()

    # Last run from report file
    last_report: dict = {}
    if REPORT_FILE.exists():
        try:
            last_report = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "enabled": cfg.get("enabled", True),
        "running": _scan_running,
        "scheduler_active": _scheduler.running if _scheduler else False,
        "scan_time_ist": cfg.get("scan_time_ist", "08:30"),
        "next_run": next_run,
        "last_run": last_report.get("started_at"),
        "last_finished": last_report.get("finished_at"),
        "last_analysed_count": last_report.get("analysed_count", 0),
        "last_results": last_report.get("results", []),
        "last_errors": last_report.get("errors", []),
        "config": cfg,
    }
