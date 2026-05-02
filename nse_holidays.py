"""nse_holidays.py — NSE market calendar for TradeBotX.

Provides market-aware time checks:
  - Weekend detection
  - NSE holiday calendar (2025-2026)
  - Combined is_market_open() for trading decisions
"""

from datetime import date, datetime, time

import pytz

IST = pytz.timezone("Asia/Kolkata")

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(15, 20)  # Buffer before 15:30

# NSE holidays — source: https://www.nseindia.com/resources/exchange-communication-holidays
# Updated for 2025-2026
NSE_HOLIDAYS: set[date] = {
    # 2025
    date(2025, 2, 26),   # Mahashivratri
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Id-Ul-Fitr (Ramadan)
    date(2025, 4, 10),   # Shri Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 6, 7),    # Bakri Id
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Ganesh Chaturthi
    date(2025, 10, 2),   # Mahatma Gandhi Jayanti / Dussehra
    date(2025, 10, 21),  # Diwali (Laxmi Puja)
    date(2025, 10, 22),  # Diwali (Balipratipada)
    date(2025, 11, 5),   # Gurunanak Jayanti
    date(2025, 12, 25),  # Christmas
    # 2026
    date(2026, 1, 26),   # Republic Day
    date(2026, 2, 17),   # Mahashivratri
    date(2026, 3, 3),    # Holi
    date(2026, 3, 20),   # Id-Ul-Fitr (Ramadan)
    date(2026, 3, 25),   # Shri Mahavir Jayanti
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 5, 28),   # Bakri Id
    date(2026, 7, 17),   # Muharram
    date(2026, 8, 15),   # Independence Day
    date(2026, 8, 17),   # Ganesh Chaturthi
    date(2026, 9, 16),   # Milad-Un-Nabi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 15),  # Dussehra
    date(2026, 11, 9),   # Diwali (Laxmi Puja)
    date(2026, 11, 10),  # Diwali (Balipratipada)
    date(2026, 11, 25),  # Gurunanak Jayanti
    date(2026, 12, 25),  # Christmas
}


def is_trading_day(d: date = None) -> bool:
    """Check if a given date is a valid NSE trading day (weekday + not a holiday)."""
    if d is None:
        d = datetime.now(IST).date()
    # Weekday check: Monday=0 ... Sunday=6
    if d.weekday() >= 5:  # Saturday or Sunday
        return False
    if d in NSE_HOLIDAYS:
        return False
    return True


def is_market_open() -> bool:
    """Check if the NSE market is currently open (trading day + within hours)."""
    now = datetime.now(IST)
    if not is_trading_day(now.date()):
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def next_trading_day(from_date: date = None) -> date:
    """Get the next valid NSE trading day from a given date."""
    from datetime import timedelta
    if from_date is None:
        from_date = datetime.now(IST).date()
    d = from_date + timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d


def market_status() -> dict:
    """Get detailed market status for display."""
    now = datetime.now(IST)
    today = now.date()
    trading_day = is_trading_day(today)
    open_now = is_market_open()

    if not trading_day:
        if today.weekday() >= 5:
            reason = "Weekend"
        else:
            reason = "NSE Holiday"
        status = "CLOSED"
    elif now.time() < MARKET_OPEN:
        reason = "Pre-market"
        status = "PRE_MARKET"
    elif now.time() > MARKET_CLOSE:
        reason = "Post-market"
        status = "POST_MARKET"
    else:
        reason = "Trading hours"
        status = "OPEN"

    return {
        "status": status,
        "is_open": open_now,
        "reason": reason,
        "time": now.strftime("%H:%M:%S IST"),
        "next_trading_day": next_trading_day(today).isoformat() if not open_now else today.isoformat(),
    }
