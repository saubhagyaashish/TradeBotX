"""signal_scanner.py — Auto Paper Trading Bot for TradeBotX.

Automated signal scanning and paper trade execution engine.
Runs every 5 minutes during market hours:

  1. Batch LTP (1 API call) → get all NIFTY 50 prices
  2. Filter movers (stocks that moved > 0.5% from open)
  3. Compute dual-timeframe signals only for movers
  4. Auto-enter paper trades if score ≥ 0.65
  5. Auto-exit paper trades if score ≤ 0.35
  6. Monitor open positions for SL/TP triggers
  7. Force-close all positions at 15:20 IST

Designed for zero human intervention during market hours.
"""

import asyncio
import json
import logging
import threading
from datetime import datetime, time
from pathlib import Path
from typing import Optional

import pytz

from nse_holidays import is_market_open, is_trading_day
from upstox_client import (
    UpstoxClient,
    NIFTY_50_INSTRUMENTS,
    symbol_to_instrument_key,
)
import technical as ta

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")
SCANNER_LOG_FILE = Path("scanner_log.json")

# ── Scanner Configuration ────────────────────────────────────────────────────

DEFAULT_SCANNER_CONFIG = {
    "enabled": False,                  # Start disabled — user must opt in
    "interval_minutes": 5,             # Scan every 5 minutes
    "index": "NIFTY50",                # Which index to scan
    "mover_threshold_pct": 0.5,        # Min % change from open to be a "mover"
    "buy_score_threshold": 0.65,       # Minimum signal score to auto-buy
    "sell_score_threshold": 0.35,      # Maximum signal score to auto-sell
    "max_auto_positions": 3,           # Max simultaneous auto positions
    "force_close_time": "15:20",       # Force-close all positions IST
    "position_size_pct": 3.0,          # % of capital per auto-trade
    "strategy_tag": "auto_scanner",    # Tag for all auto-trades
}

CONFIG_FILE = Path("config.json")


def load_scanner_config() -> dict:
    """Load scanner config from config.json, merged with defaults."""
    cfg = DEFAULT_SCANNER_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update(raw.get("scanner", {}))
        except Exception as exc:
            logger.warning("Failed to load scanner config: %s", exc)
    return cfg


def save_scanner_config(cfg: dict) -> None:
    """Persist scanner config to config.json."""
    full: dict = {}
    if CONFIG_FILE.exists():
        try:
            full = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    full["scanner"] = cfg
    CONFIG_FILE.write_text(json.dumps(full, indent=2), encoding="utf-8")


# ── Scanner State ────────────────────────────────────────────────────────────

class ScannerState:
    """Mutable state for the scanner — persists across scans within a session."""

    def __init__(self):
        self.is_running = False
        self.last_scan_time: Optional[str] = None
        self.last_scan_results: dict = {}
        self.scans_today = 0
        self.auto_trades_today = 0
        self.auto_exits_today = 0
        self.errors: list[str] = []
        self._scan_lock = threading.Lock()

    def to_dict(self) -> dict:
        return {
            "is_running": self.is_running,
            "last_scan_time": self.last_scan_time,
            "last_scan_results": self.last_scan_results,
            "scans_today": self.scans_today,
            "auto_trades_today": self.auto_trades_today,
            "auto_exits_today": self.auto_exits_today,
            "errors": self.errors[-10:],  # Last 10 errors only
        }


scanner_state = ScannerState()


# ── Core Scan Function ───────────────────────────────────────────────────────

async def run_signal_scan(
    client: UpstoxClient,
    paper_trader,
    config: dict = None,
) -> dict:
    """
    Execute one full signal scan cycle:
      1. Batch LTP (1 API call)
      2. Filter movers
      3. Compute signals for movers
      4. Auto-enter/exit paper trades
      5. Check SL/TP on open positions

    Returns: scan result dict
    """
    if config is None:
        config = load_scanner_config()

    now = datetime.now(IST)
    scan_result = {
        "timestamp": now.isoformat(),
        "status": "ok",
        "movers_found": 0,
        "signals_computed": 0,
        "auto_buys": [],
        "auto_sells": [],
        "position_exits": [],
        "errors": [],
    }

    try:
        # ── Step 0: Pre-flight checks ──
        if not is_market_open():
            scan_result["status"] = "market_closed"
            logger.info("⏸ Scanner: Market is closed, skipping scan")
            return scan_result

        if paper_trader.check_daily_loss_limit():
            scan_result["status"] = "daily_loss_limit"
            logger.warning("🛑 Scanner: Daily loss limit reached, skipping scan")
            return scan_result

        if paper_trader.check_circuit_breaker():
            scan_result["status"] = "circuit_breaker"
            logger.warning("⏸ Scanner: Circuit breaker active, skipping scan")
            return scan_result

        # ── Step 1: Batch LTP (1 API call for all stocks) ──
        symbols = list(NIFTY_50_INSTRUMENTS.keys())
        logger.info("📡 Scanner: Fetching batch LTP for %d stocks...", len(symbols))

        try:
            quotes = await client.get_batch_quotes(symbols)
        except Exception as exc:
            scan_result["errors"].append(f"Batch quotes failed: {exc}")
            scan_result["status"] = "api_error"
            logger.error("Scanner: Batch quotes failed: %s", exc)
            return scan_result

        # ── Step 2: Check SL/TP on existing positions ──
        for sym in list(paper_trader.positions.keys()):
            if sym in quotes:
                ltp = quotes[sym].get("ltp")
                if ltp:
                    exit_result = paper_trader.on_price_update(sym, ltp)
                    if exit_result:
                        scan_result["position_exits"].append(exit_result)
                        scanner_state.auto_exits_today += 1
                        logger.info(
                            "🔔 Auto-exit: %s @ ₹%.2f (%s)",
                            sym, ltp, exit_result.get("reason"),
                        )

        # ── Step 3: Filter movers ──
        threshold = config.get("mover_threshold_pct", 0.5)
        movers = []
        for sym, q in quotes.items():
            ltp = q.get("ltp")
            open_price = q.get("open")
            if ltp and open_price and open_price > 0:
                pct = ((ltp - open_price) / open_price) * 100
                if abs(pct) >= threshold:
                    movers.append({
                        "symbol": sym,
                        "ltp": ltp,
                        "open": open_price,
                        "pct_change": round(pct, 2),
                        "volume": q.get("volume"),
                    })
        movers.sort(key=lambda m: abs(m["pct_change"]), reverse=True)
        scan_result["movers_found"] = len(movers)
        logger.info("📊 Scanner: Found %d movers (>%.1f%%)", len(movers), threshold)

        # Limit to top 15 movers
        movers = movers[:15]

        # ── Step 4: Compute signals for movers ──
        buy_threshold = config.get("buy_score_threshold", 0.65)
        sell_threshold = config.get("sell_score_threshold", 0.35)
        max_auto = config.get("max_auto_positions", 3)
        auto_position_count = sum(
            1 for pos in paper_trader.positions.values()
            if pos.strategy == config.get("strategy_tag", "auto_scanner")
        )

        for mover in movers:
            sym = mover["symbol"]
            try:
                # Fetch daily candles (for trend indicators)
                daily_df = await client.get_candles_as_df(sym, "days", "1")
                if daily_df is None or len(daily_df) < 50:
                    continue

                # Fetch intraday 5-min candles (for VWAP + momentum)
                intraday_df = None
                try:
                    intraday_df = await client.get_intraday_candles_as_df(sym, "5")
                except Exception:
                    pass  # Graceful fallback to daily-only

                signal = ta.generate_signal_score(daily_df, intraday_df)
                if signal is None:
                    continue

                scan_result["signals_computed"] += 1
                score = signal["score"]

                # ── Auto-BUY logic ──
                if (
                    score >= buy_threshold
                    and sym not in paper_trader.positions
                    and auto_position_count < max_auto
                    and not paper_trader.check_max_positions()
                    and mover["pct_change"] > 0  # Only buy stocks moving UP
                ):
                    ltp = mover["ltp"]
                    atr = signal["signals"].get("atr", ltp * 0.02)

                    # ATR-based stop-loss and target
                    stop_loss = round(ltp - (atr * 1.5), 2)
                    target = round(ltp + (atr * 2.5), 2)

                    # Position sizing: X% of capital
                    size_pct = config.get("position_size_pct", 3.0)
                    max_value = paper_trader.capital * (size_pct / 100)
                    quantity = max(1, int(max_value / ltp))

                    ikey = symbol_to_instrument_key(sym) or ""
                    trade_result = paper_trader.enter_trade(
                        symbol=sym,
                        instrument_key=ikey,
                        quantity=quantity,
                        price=ltp,
                        stop_loss=stop_loss,
                        target_price=target,
                        strategy=config.get("strategy_tag", "auto_scanner"),
                        signal_context={
                            "score": score,
                            "trend": signal["trend"],
                            "recommendation": signal["recommendation"],
                            "component_scores": signal.get("component_scores", {}),
                            "signals": signal.get("signals", {}),
                            "pct_change_from_open": mover["pct_change"],
                            "scan_time": now.isoformat(),
                        },
                    )

                    if trade_result.get("status") == "success":
                        scan_result["auto_buys"].append({
                            "symbol": sym,
                            "quantity": quantity,
                            "price": trade_result["price"],
                            "stop_loss": stop_loss,
                            "target": target,
                            "score": score,
                            "trend": signal["trend"],
                        })
                        scanner_state.auto_trades_today += 1
                        auto_position_count += 1
                        logger.info(
                            "🤖 AUTO BUY: %s × %d @ ₹%.2f (score: %.3f, SL: ₹%.2f, TP: ₹%.2f)",
                            sym, quantity, ltp, score, stop_loss, target,
                        )

                # ── Auto-SELL logic ──
                elif (
                    score <= sell_threshold
                    and sym in paper_trader.positions
                    and paper_trader.positions[sym].strategy == config.get("strategy_tag", "auto_scanner")
                ):
                    ltp = mover["ltp"]
                    exit_result = paper_trader.exit_trade(sym, ltp, "SIGNAL_WEAK")
                    if exit_result.get("status") == "success":
                        scan_result["auto_sells"].append({
                            "symbol": sym,
                            "exit_price": exit_result["exit_price"],
                            "pnl": exit_result["pnl"],
                            "score": score,
                            "reason": "SIGNAL_WEAK",
                        })
                        scanner_state.auto_exits_today += 1
                        logger.info(
                            "🤖 AUTO SELL: %s @ ₹%.2f (score: %.3f → P&L: ₹%.2f)",
                            sym, ltp, score, exit_result["pnl"],
                        )

            except Exception as exc:
                scan_result["errors"].append(f"{sym}: {exc}")
                logger.warning("Scanner: Error processing %s: %s", sym, exc)

        # ── Step 5: Force close check ──
        force_close_time = config.get("force_close_time", "15:20")
        fc_parts = force_close_time.split(":")
        fc_time = time(int(fc_parts[0]), int(fc_parts[1]))

        if now.time() >= fc_time:
            open_auto = {
                sym: pos for sym, pos in paper_trader.positions.items()
                if pos.strategy == config.get("strategy_tag", "auto_scanner")
            }
            if open_auto:
                logger.warning(
                    "⏰ Force-closing %d auto positions at %s IST",
                    len(open_auto), force_close_time,
                )
                prices = {}
                for sym in open_auto:
                    if sym in quotes:
                        prices[sym] = quotes[sym].get("ltp", open_auto[sym].entry_price)
                    else:
                        prices[sym] = open_auto[sym].entry_price

                for sym in list(open_auto.keys()):
                    exit_result = paper_trader.exit_trade(
                        sym, prices.get(sym, open_auto[sym].entry_price), "TIME_EXIT"
                    )
                    if exit_result.get("status") == "success":
                        scan_result["position_exits"].append(exit_result)
                        scanner_state.auto_exits_today += 1

    except Exception as exc:
        scan_result["status"] = "error"
        scan_result["errors"].append(str(exc))
        logger.exception("Scanner: Top-level scan error")

    # ── Update scanner state ──
    scanner_state.last_scan_time = now.isoformat()
    scanner_state.last_scan_results = scan_result
    scanner_state.scans_today += 1

    if scan_result["errors"]:
        scanner_state.errors.extend(scan_result["errors"])

    # ── Save scan log ──
    _append_scan_log(scan_result)

    total_actions = len(scan_result["auto_buys"]) + len(scan_result["auto_sells"]) + len(scan_result["position_exits"])
    logger.info(
        "✅ Scan #%d complete — %d movers, %d signals, %d actions",
        scanner_state.scans_today,
        scan_result["movers_found"],
        scan_result["signals_computed"],
        total_actions,
    )

    return scan_result


def _append_scan_log(result: dict) -> None:
    """Append scan result to the daily log file."""
    try:
        logs = []
        if SCANNER_LOG_FILE.exists():
            try:
                logs = json.loads(SCANNER_LOG_FILE.read_text(encoding="utf-8"))
            except Exception:
                logs = []
        # Keep only last 100 scans
        logs.append(result)
        logs = logs[-100:]
        SCANNER_LOG_FILE.write_text(json.dumps(logs, indent=2, default=str), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to write scanner log: %s", exc)


# ── Scanner Loop (APScheduler Integration) ───────────────────────────────────

_scanner_task: Optional[asyncio.Task] = None
_scanner_stop_event = asyncio.Event()


async def _scanner_loop(client: UpstoxClient, paper_trader, config: dict):
    """
    Main scanner loop — runs continuously during market hours.
    Uses asyncio.sleep instead of APScheduler for sub-minute flexibility.
    """
    interval = config.get("interval_minutes", 5) * 60  # Convert to seconds
    scanner_state.is_running = True

    logger.info(
        "🤖 Auto-scanner STARTED — scanning every %d minutes",
        config.get("interval_minutes", 5),
    )

    try:
        while not _scanner_stop_event.is_set():
            # Only scan during market hours
            if is_market_open():
                try:
                    await run_signal_scan(client, paper_trader, config)
                except Exception as exc:
                    logger.exception("Scanner loop error: %s", exc)
                    scanner_state.errors.append(f"Loop error: {exc}")
            else:
                logger.debug("Scanner: Market closed, sleeping...")

            # Wait for next interval or stop signal
            try:
                await asyncio.wait_for(
                    _scanner_stop_event.wait(),
                    timeout=interval,
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                continue  # Timeout = time to scan again

    finally:
        scanner_state.is_running = False
        logger.info("🤖 Auto-scanner STOPPED")


async def start_scanner(client: UpstoxClient, paper_trader) -> dict:
    """Start the auto-scanner background task."""
    global _scanner_task

    if scanner_state.is_running:
        return {"error": "Scanner is already running"}

    config = load_scanner_config()
    if not config.get("enabled", False):
        # Auto-enable on explicit start
        config["enabled"] = True
        save_scanner_config(config)

    _scanner_stop_event.clear()

    # Reset daily counters
    scanner_state.scans_today = 0
    scanner_state.auto_trades_today = 0
    scanner_state.auto_exits_today = 0
    scanner_state.errors = []

    _scanner_task = asyncio.create_task(
        _scanner_loop(client, paper_trader, config)
    )

    return {
        "status": "started",
        "config": config,
        "message": f"Auto-scanner started — scanning every {config['interval_minutes']} minutes",
    }


async def stop_scanner() -> dict:
    """Stop the auto-scanner background task."""
    global _scanner_task

    if not scanner_state.is_running:
        return {"error": "Scanner is not running"}

    _scanner_stop_event.set()

    if _scanner_task:
        try:
            await asyncio.wait_for(_scanner_task, timeout=5.0)
        except asyncio.TimeoutError:
            _scanner_task.cancel()
        _scanner_task = None

    config = load_scanner_config()
    config["enabled"] = False
    save_scanner_config(config)

    return {
        "status": "stopped",
        "summary": {
            "scans_completed": scanner_state.scans_today,
            "auto_trades": scanner_state.auto_trades_today,
            "auto_exits": scanner_state.auto_exits_today,
        },
    }


def get_scanner_status() -> dict:
    """Return current scanner state for the API."""
    config = load_scanner_config()
    return {
        "enabled": config.get("enabled", False),
        "config": config,
        **scanner_state.to_dict(),
    }
