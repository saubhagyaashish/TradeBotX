"""paper_trader.py — Paper trading engine for TradeBotX.

Simulates trades with real market data but no real orders.
Tracks positions, P&L, win/loss rate, and enforces risk rules.

Risk Rules (from ROADMAP):
  - Max daily loss: -2% of capital
  - Max concurrent positions: 5
  - Max position size: 5% of capital per trade
  - Trading hours only: 9:30 - 15:20 IST
  - Mandatory stop-loss on every trade
  - Time-based exit: force close at 15:20
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Optional

import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")
DB_FILE = Path("predictions.db")

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(15, 20)  # Exit buffer before 15:30


@dataclass
class Position:
    """An active paper trading position."""
    symbol: str
    instrument_key: str
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_loss: float
    target_price: float
    strategy: str = "manual"
    signal_context: dict = field(default_factory=dict)
    trailing_stop: Optional[float] = None
    highest_since_entry: Optional[float] = None

    @property
    def pnl(self) -> float:
        """Unrealized P&L (not useful without current price)."""
        return 0.0

    def unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L given current market price."""
        return (current_price - self.entry_price) * self.quantity

    def unrealized_pnl_pct(self, current_price: float) -> float:
        """Calculate unrealized P&L as percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((current_price - self.entry_price) / self.entry_price) * 100

    def should_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss has been hit."""
        return current_price <= self.stop_loss

    def should_take_profit(self, current_price: float) -> bool:
        """Check if target price has been hit."""
        return current_price >= self.target_price

    def update_trailing_stop(self, current_price: float, trail_pct: float = 1.5):
        """Update trailing stop-loss based on highest price."""
        if self.highest_since_entry is None:
            self.highest_since_entry = self.entry_price

        if current_price > self.highest_since_entry:
            self.highest_since_entry = current_price
            new_stop = current_price * (1 - trail_pct / 100)
            if self.trailing_stop is None or new_stop > self.trailing_stop:
                self.trailing_stop = new_stop


class PaperTrader:
    """
    Paper trading engine with risk management.

    Modes:
      - paper: Pure simulation (default)
      - sandbox: Uses Upstox sandbox API for orders
    """

    def __init__(
        self,
        initial_capital: float = 100_000,
        max_daily_loss_pct: float = 2.0,
        max_positions: int = 5,
        max_position_size_pct: float = 5.0,
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_positions = max_positions
        self.max_position_size_pct = max_position_size_pct

        # Active positions
        self.positions: dict[str, Position] = {}

        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_wins = 0
        self.daily_losses = 0
        self._last_reset_date: Optional[str] = None

        # Session tracking
        self.total_trades = 0
        self.total_wins = 0
        self.total_pnl = 0.0

        # Ensure DB tables exist
        self._init_db()

    # ── Database ──────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(DB_FILE, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self):
        """Create paper trading tables if they don't exist."""
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol          TEXT    NOT NULL,
                    instrument_key  TEXT    NOT NULL,
                    side            TEXT    NOT NULL,      -- BUY or SELL
                    quantity        INTEGER NOT NULL,
                    entry_price     REAL    NOT NULL,
                    exit_price      REAL,
                    entry_time      TEXT    NOT NULL,
                    exit_time       TEXT,
                    stop_loss       REAL,
                    target_price    REAL,
                    pnl             REAL,
                    pnl_pct         REAL,
                    is_win          INTEGER,
                    exit_reason     TEXT,                  -- STOP_LOSS, TARGET, MANUAL, TIME_EXIT
                    strategy        TEXT    DEFAULT 'manual',
                    signal_context  TEXT,                  -- JSON
                    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS paper_portfolio (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    date            TEXT    NOT NULL,
                    capital         REAL    NOT NULL,
                    daily_pnl       REAL    NOT NULL,
                    total_pnl       REAL    NOT NULL,
                    open_positions  INTEGER NOT NULL,
                    daily_trades    INTEGER NOT NULL,
                    daily_wins      INTEGER NOT NULL,
                    daily_losses    INTEGER NOT NULL,
                    win_rate        REAL,
                    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(date)
                )
            """)
            c.commit()
        logger.info("Paper trading tables initialised")

    # ── Risk checks ───────────────────────────────────────────────────────

    def _reset_daily_if_needed(self):
        """Reset daily counters at the start of a new trading day."""
        today = datetime.now(IST).date().isoformat()
        if self._last_reset_date != today:
            # Save yesterday's snapshot before resetting
            if self._last_reset_date and self.daily_trades > 0:
                self._save_daily_snapshot(self._last_reset_date)

            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.daily_wins = 0
            self.daily_losses = 0
            self._last_reset_date = today

    def check_daily_loss_limit(self) -> bool:
        """Returns True if daily loss limit has been breached."""
        self._reset_daily_if_needed()
        max_loss = self.capital * (self.max_daily_loss_pct / 100)
        if self.daily_pnl <= -max_loss:
            logger.warning(
                "🛑 Daily loss limit breached: ₹%.2f (limit: -₹%.2f)",
                self.daily_pnl,
                max_loss,
            )
            return True
        return False

    def check_max_positions(self) -> bool:
        """Returns True if max positions limit reached."""
        if len(self.positions) >= self.max_positions:
            logger.warning(
                "🛑 Max positions limit: %d/%d", len(self.positions), self.max_positions
            )
            return True
        return False

    def check_market_hours(self) -> bool:
        """Returns True if within trading hours."""
        now = datetime.now(IST).time()
        return MARKET_OPEN <= now <= MARKET_CLOSE

    def check_position_size(self, price: float) -> int:
        """
        Calculate max quantity allowed for given price.
        Returns max shares that can be bought within position size limit.
        """
        max_value = self.capital * (self.max_position_size_pct / 100)
        if price <= 0:
            return 0
        return int(max_value // price)

    # ── Trade execution ───────────────────────────────────────────────────

    def enter_trade(
        self,
        symbol: str,
        instrument_key: str,
        quantity: int,
        price: float,
        stop_loss: float,
        target_price: float,
        strategy: str = "manual",
        signal_context: dict = None,
    ) -> dict:
        """
        Enter a new paper trade.

        Returns:
            dict with trade result or error
        """
        self._reset_daily_if_needed()

        # ── Pre-flight checks ──
        if self.check_daily_loss_limit():
            return {"error": "Daily loss limit breached — no new trades allowed"}

        if self.check_max_positions():
            return {"error": f"Max positions ({self.max_positions}) reached"}

        if symbol in self.positions:
            return {"error": f"Already have an open position in {symbol}"}

        max_qty = self.check_position_size(price)
        if quantity > max_qty:
            return {
                "error": f"Position too large: {quantity} shares (max: {max_qty} at ₹{price})",
                "max_quantity": max_qty,
            }

        if stop_loss >= price:
            return {"error": "Stop loss must be below entry price"}

        if target_price <= price:
            return {"error": "Target price must be above entry price"}

        # ── Execute paper trade ──
        position = Position(
            symbol=symbol,
            instrument_key=instrument_key,
            quantity=quantity,
            entry_price=price,
            entry_time=datetime.now(IST),
            stop_loss=stop_loss,
            target_price=target_price,
            strategy=strategy,
            signal_context=signal_context or {},
            highest_since_entry=price,
        )

        self.positions[symbol] = position
        self.capital -= price * quantity  # Reserve capital

        # Save to DB
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO paper_trades
                    (symbol, instrument_key, side, quantity, entry_price,
                     entry_time, stop_loss, target_price, strategy, signal_context)
                VALUES (?, ?, 'BUY', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol, instrument_key, quantity, price,
                    position.entry_time.isoformat(),
                    stop_loss, target_price, strategy,
                    json.dumps(signal_context) if signal_context else None,
                ),
            )
            c.commit()

        logger.info(
            "📈 PAPER BUY: %s × %d @ ₹%.2f (SL: ₹%.2f, TP: ₹%.2f)",
            symbol, quantity, price, stop_loss, target_price,
        )

        return {
            "status": "success",
            "action": "BUY",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "capital_remaining": round(self.capital, 2),
        }

    def exit_trade(
        self,
        symbol: str,
        price: float,
        reason: str = "MANUAL",
    ) -> dict:
        """
        Exit a paper trade.

        Args:
            symbol: Stock symbol
            price: Exit price
            reason: STOP_LOSS, TARGET, MANUAL, TIME_EXIT

        Returns:
            dict with trade result
        """
        if symbol not in self.positions:
            return {"error": f"No open position in {symbol}"}

        position = self.positions[symbol]
        pnl = (price - position.entry_price) * position.quantity
        pnl_pct = ((price - position.entry_price) / position.entry_price) * 100
        is_win = 1 if pnl > 0 else 0

        # Update capital
        self.capital += price * position.quantity
        self.daily_pnl += pnl
        self.total_pnl += pnl
        self.daily_trades += 1
        self.total_trades += 1

        if is_win:
            self.daily_wins += 1
            self.total_wins += 1
        else:
            self.daily_losses += 1

        # Remove position
        del self.positions[symbol]

        # Update DB
        exit_time = datetime.now(IST).isoformat()
        with self._conn() as c:
            c.execute(
                """
                UPDATE paper_trades
                SET exit_price = ?, exit_time = ?, pnl = ?, pnl_pct = ?,
                    is_win = ?, exit_reason = ?
                WHERE symbol = ? AND exit_time IS NULL
                ORDER BY id DESC LIMIT 1
                """,
                (price, exit_time, round(pnl, 2), round(pnl_pct, 2),
                 is_win, reason, symbol),
            )
            c.commit()

        emoji = "✅" if is_win else "❌"
        logger.info(
            "%s PAPER SELL: %s × %d @ ₹%.2f → P&L: ₹%.2f (%.2f%%) [%s]",
            emoji, symbol, position.quantity, price, pnl, pnl_pct, reason,
        )

        return {
            "status": "success",
            "action": "SELL",
            "symbol": symbol,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "exit_price": price,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "is_win": bool(is_win),
            "reason": reason,
            "capital": round(self.capital, 2),
        }

    # ── Tick handler (for WebSocket integration) ──────────────────────────

    def on_price_update(self, symbol: str, current_price: float) -> Optional[dict]:
        """
        Called on each price tick for monitored positions.
        Checks stop-loss, target, and trailing stop conditions.

        Returns exit result if a trade is closed, None otherwise.
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        # Update trailing stop
        position.update_trailing_stop(current_price)

        # Check stop-loss
        if position.should_stop_loss(current_price):
            return self.exit_trade(symbol, current_price, "STOP_LOSS")

        # Check trailing stop
        if position.trailing_stop and current_price <= position.trailing_stop:
            return self.exit_trade(symbol, current_price, "TRAILING_STOP")

        # Check target
        if position.should_take_profit(current_price):
            return self.exit_trade(symbol, current_price, "TARGET")

        return None

    def force_close_all(self, prices: dict[str, float], reason: str = "TIME_EXIT"):
        """Force close all positions (e.g., at market close)."""
        results = []
        for symbol in list(self.positions.keys()):
            price = prices.get(symbol, self.positions[symbol].entry_price)
            result = self.exit_trade(symbol, price, reason)
            results.append(result)
        return results

    # ── State queries ─────────────────────────────────────────────────────

    def get_portfolio_state(self) -> dict:
        """Get current portfolio state."""
        self._reset_daily_if_needed()
        positions_list = []
        for sym, pos in self.positions.items():
            positions_list.append({
                "symbol": sym,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "entry_time": pos.entry_time.isoformat(),
                "stop_loss": pos.stop_loss,
                "target_price": pos.target_price,
                "trailing_stop": pos.trailing_stop,
                "strategy": pos.strategy,
            })

        total_win_rate = (
            round((self.total_wins / self.total_trades) * 100, 1)
            if self.total_trades > 0
            else None
        )

        return {
            "capital": round(self.capital, 2),
            "initial_capital": self.initial_capital,
            "total_pnl": round(self.total_pnl, 2),
            "total_pnl_pct": round(
                (self.total_pnl / self.initial_capital) * 100, 2
            ),
            "daily_pnl": round(self.daily_pnl, 2),
            "open_positions": positions_list,
            "position_count": len(self.positions),
            "daily_trades": self.daily_trades,
            "daily_wins": self.daily_wins,
            "daily_losses": self.daily_losses,
            "total_trades": self.total_trades,
            "total_wins": self.total_wins,
            "total_win_rate": total_win_rate,
            "daily_loss_limit_active": self.check_daily_loss_limit(),
        }

    def get_trade_history(self, limit: int = 50) -> list[dict]:
        """Get completed paper trades from DB."""
        with self._conn() as c:
            rows = c.execute(
                """
                SELECT * FROM paper_trades
                WHERE exit_time IS NOT NULL
                ORDER BY exit_time DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_performance_summary(self) -> dict:
        """Get overall performance metrics from DB."""
        with self._conn() as c:
            total = c.execute(
                "SELECT COUNT(*) FROM paper_trades WHERE exit_time IS NOT NULL"
            ).fetchone()[0]

            if total == 0:
                return {"total_trades": 0, "message": "No completed trades yet"}

            wins = c.execute(
                "SELECT COUNT(*) FROM paper_trades WHERE is_win = 1"
            ).fetchone()[0]

            total_pnl_row = c.execute(
                "SELECT SUM(pnl) FROM paper_trades WHERE pnl IS NOT NULL"
            ).fetchone()[0]

            avg_win = c.execute(
                "SELECT AVG(pnl) FROM paper_trades WHERE is_win = 1 AND pnl IS NOT NULL"
            ).fetchone()[0]

            avg_loss = c.execute(
                "SELECT AVG(pnl) FROM paper_trades WHERE is_win = 0 AND pnl IS NOT NULL"
            ).fetchone()[0]

            by_strategy = {}
            for r in c.execute(
                """
                SELECT strategy, COUNT(*) as cnt, SUM(is_win) as wins,
                       SUM(pnl) as total_pnl, AVG(pnl_pct) as avg_ret
                FROM paper_trades
                WHERE exit_time IS NOT NULL
                GROUP BY strategy
                """
            ).fetchall():
                by_strategy[r["strategy"] or "manual"] = {
                    "trades": r["cnt"],
                    "wins": r["wins"] or 0,
                    "win_rate": round((r["wins"] / r["cnt"]) * 100, 1) if r["cnt"] else 0,
                    "total_pnl": round(r["total_pnl"] or 0, 2),
                    "avg_return_pct": round(r["avg_ret"] or 0, 2),
                }

        return {
            "total_trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": round((wins / total) * 100, 1),
            "total_pnl": round(total_pnl_row or 0, 2),
            "avg_win": round(avg_win or 0, 2),
            "avg_loss": round(avg_loss or 0, 2),
            "profit_factor": round(
                abs(avg_win / avg_loss), 2
            ) if avg_loss and avg_loss != 0 else None,
            "by_strategy": by_strategy,
        }

    def _save_daily_snapshot(self, date_str: str):
        """Save end-of-day portfolio snapshot."""
        win_rate = (
            round((self.daily_wins / self.daily_trades) * 100, 1)
            if self.daily_trades > 0
            else None
        )
        with self._conn() as c:
            c.execute(
                """
                INSERT OR REPLACE INTO paper_portfolio
                    (date, capital, daily_pnl, total_pnl, open_positions,
                     daily_trades, daily_wins, daily_losses, win_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    date_str, round(self.capital, 2),
                    round(self.daily_pnl, 2), round(self.total_pnl, 2),
                    len(self.positions), self.daily_trades,
                    self.daily_wins, self.daily_losses, win_rate,
                ),
            )
            c.commit()
