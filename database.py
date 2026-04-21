"""database.py — SQLite prediction tracking for TradeBotX.

Schema: predictions(id, ticker, trade_date, decision, rating,
                    price_at_prediction, current_price, return_pct,
                    outcome_checked_at, reports_json, created_at)

Win logic:
  BUY / OVERWEIGHT / STRONG BUY  → price went UP   = win
  SELL / UNDERWEIGHT / STRONG SELL → price went DOWN = win
  HOLD                            → always neutral   = win
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytz
import yfinance as yf

logger = logging.getLogger(__name__)

DB_FILE = Path("predictions.db")
IST = pytz.timezone("Asia/Kolkata")

_BULLISH = {"BUY", "OVERWEIGHT", "STRONG BUY"}
_BEARISH = {"SELL", "UNDERWEIGHT", "STRONG SELL"}


# ── Connection ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_FILE, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


# ── Initialise ────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker              TEXT    NOT NULL,
                trade_date          TEXT    NOT NULL,
                decision            TEXT    NOT NULL,
                rating              TEXT    NOT NULL,
                price_at_prediction REAL,
                current_price       REAL,
                return_pct          REAL,
                is_win              INTEGER,
                outcome_checked_at  TEXT,
                reports_json        TEXT,
                created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(ticker, trade_date)
            )
        """)
        c.commit()
    logger.info("Database initialised at %s", DB_FILE)


# ── Price helper ──────────────────────────────────────────────────────────────

def fetch_price(ticker: str) -> Optional[float]:
    """Return the latest market price for a ticker, or None on error."""
    try:
        info = yf.Ticker(ticker).fast_info
        price = getattr(info, "last_price", None)
        return float(price) if price else None
    except Exception as exc:
        logger.warning("Price fetch failed for %s: %s", ticker, exc)
        return None


# ── Write ─────────────────────────────────────────────────────────────────────

def save_prediction(
    ticker: str,
    trade_date: str,
    decision: str,
    rating: str,
    price_at_prediction: Optional[float] = None,
    reports: Optional[dict] = None,
) -> int:
    """Upsert a prediction row. Returns the row id."""
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO predictions
                (ticker, trade_date, decision, rating,
                 price_at_prediction, reports_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(ticker, trade_date) DO UPDATE SET
                decision            = excluded.decision,
                rating              = excluded.rating,
                price_at_prediction = COALESCE(excluded.price_at_prediction, price_at_prediction),
                reports_json        = COALESCE(excluded.reports_json, reports_json)
            """,
            (
                ticker, trade_date, decision, rating,
                price_at_prediction,
                json.dumps(reports) if reports else None,
            ),
        )
        c.commit()
        return cur.lastrowid or 0


# ── Read ──────────────────────────────────────────────────────────────────────

def get_predictions(
    limit: int = 100,
    offset: int = 0,
    rating: Optional[str] = None,
) -> list[dict]:
    """Return predictions newest-first, optionally filtered by rating."""
    with _conn() as c:
        if rating:
            rows = c.execute(
                "SELECT * FROM predictions WHERE rating = ? ORDER BY trade_date DESC LIMIT ? OFFSET ?",
                (rating.upper(), limit, offset),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM predictions ORDER BY trade_date DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]


def get_total_count(rating: Optional[str] = None) -> int:
    with _conn() as c:
        if rating:
            return c.execute(
                "SELECT COUNT(*) FROM predictions WHERE rating = ?", (rating.upper(),)
            ).fetchone()[0]
        return c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]


# ── Outcome tracker ───────────────────────────────────────────────────────────

def update_outcomes(days_since: int = 3) -> int:
    """
    For predictions older than `days_since` days with no outcome yet,
    fetch current price, compute return %, and determine win/loss.
    Returns number of rows updated.
    """
    cutoff = (datetime.now(IST).date() - timedelta(days=days_since)).isoformat()
    with _conn() as c:
        pending = c.execute(
            """
            SELECT id, ticker, rating, price_at_prediction
            FROM predictions
            WHERE trade_date <= ?
              AND outcome_checked_at IS NULL
              AND price_at_prediction IS NOT NULL
              AND price_at_prediction > 0
            """,
            (cutoff,),
        ).fetchall()

    updated = 0
    for row in pending:
        current = fetch_price(row["ticker"])
        if current is None:
            continue

        ret = round(
            ((current - row["price_at_prediction"]) / row["price_at_prediction"]) * 100, 2
        )
        rating = (row["rating"] or "").upper()
        if rating in _BULLISH:
            is_win = 1 if ret > 0 else 0
        elif rating in _BEARISH:
            is_win = 1 if ret < 0 else 0
        else:  # HOLD — always neutral win
            is_win = 1

        with _conn() as c:
            c.execute(
                """
                UPDATE predictions
                SET current_price = ?, return_pct = ?, is_win = ?,
                    outcome_checked_at = datetime('now')
                WHERE id = ?
                """,
                (current, ret, is_win, row["id"]),
            )
            c.commit()
        updated += 1
        logger.info("Outcome updated: %s → %.2f%% (%s)", row["ticker"], ret, "WIN" if is_win else "LOSS")

    return updated


# ── Accuracy stats ────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Return overall + per-rating accuracy statistics."""
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        settled = c.execute(
            "SELECT COUNT(*) FROM predictions WHERE outcome_checked_at IS NOT NULL"
        ).fetchone()[0]

        if settled == 0:
            return {
                "total": total, "settled": 0,
                "win_rate": None, "avg_return": None,
                "by_rating": {},
            }

        wins = c.execute(
            "SELECT COUNT(*) FROM predictions WHERE is_win = 1 AND outcome_checked_at IS NOT NULL"
        ).fetchone()[0]

        avg_ret_row = c.execute(
            "SELECT AVG(return_pct) FROM predictions WHERE return_pct IS NOT NULL"
        ).fetchone()[0]

        by_rating: dict = {}
        for r in c.execute(
            """
            SELECT rating,
                   COUNT(*) as cnt,
                   SUM(is_win) as wins,
                   AVG(return_pct) as avg_ret
            FROM predictions
            WHERE outcome_checked_at IS NOT NULL
            GROUP BY rating
            ORDER BY cnt DESC
            """
        ).fetchall():
            by_rating[r["rating"]] = {
                "count":      r["cnt"],
                "wins":       r["wins"] or 0,
                "win_rate":   round((r["wins"] / r["cnt"]) * 100, 1) if r["cnt"] else None,
                "avg_return": round(r["avg_ret"], 2) if r["avg_ret"] is not None else None,
            }

    return {
        "total":      total,
        "settled":    settled,
        "pending":    total - settled,
        "win_rate":   round((wins / settled) * 100, 1) if settled else None,
        "avg_return": round(avg_ret_row, 2) if avg_ret_row is not None else None,
        "by_rating":  by_rating,
    }
