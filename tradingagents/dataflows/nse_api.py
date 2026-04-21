"""Indian market index screener using yfinance.

Since the NSE India API blocks programmatic requests, we use yfinance
(which works reliably for .NS tickers) combined with hardcoded index
constituent lists that are updated periodically.
"""

import math
import yfinance as yf
import logging
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# ── Index Constituents (updated periodically) ─────────────────────────────
# These are the current Nifty 50 and Bank Nifty constituents.
# Update this list when SEBI/NSE reconstitutes the indices.

NIFTY_50 = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BPCL",
    "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK",
    "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK",
    "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK",
    "LT", "M&M", "MARUTI", "NESTLEIND", "NTPC",
    "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN",
    "SHRIRAMFIN", "SUNPHARMA", "TATAMOTORS", "TATASTEEL", "TCS",
    "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO",
]

NIFTY_BANK = [
    "AUBANK", "AXISBANK", "BANDHANBNK", "BANKBARODA", "CANBK",
    "FEDERALBNK", "HDFCBANK", "ICICIBANK", "IDFCFIRSTB", "INDUSINDBK",
    "KOTAKBANK", "PNB",
]

NIFTY_IT = [
    "COFORGE", "HCLTECH", "INFY", "LTIM", "LTTS",
    "MPHASIS", "NIITLTD", "PERSISTENT", "TCS", "TECHM", "WIPRO",
]

NIFTY_PHARMA = [
    "ABBOTINDIA", "ALKEM", "AUROPHARMA", "BIOCON", "CIPLA",
    "DIVISLAB", "DRREDDY", "GLENMARK", "GRANULES", "IPCALAB",
    "LAURUSLABS", "LUPIN", "SUNPHARMA", "TORNTPHARM",
]

NIFTY_AUTO = [
    "ASHOKLEY", "BAJAJ-AUTO", "BHARATFORG", "BOSCHLTD", "EICHERMOT",
    "EXIDEIND", "HEROMOTOCO", "M&M", "MARUTI", "MOTHERSON",
    "TATAMOTORS", "TVSMOTOR",
]

SUPPORTED_INDICES: Dict[str, List[str]] = {
    "NIFTY 50": NIFTY_50,
    "NIFTY BANK": NIFTY_BANK,
    "NIFTY IT": NIFTY_IT,
    "NIFTY PHARMA": NIFTY_PHARMA,
    "NIFTY AUTO": NIFTY_AUTO,
}


def _clean(val, default: float = 0.0) -> float:
    """Return val as float, replacing NaN/Inf with default."""
    try:
        v = float(val)
        return default if (math.isnan(v) or math.isinf(v)) else v
    except (TypeError, ValueError):
        return default


def _fetch_single_stock(symbol: str) -> Dict:
    """Fetch live data for a single NSE stock via yfinance."""
    ticker_str = f"{symbol}.NS"
    try:
        tk = yf.Ticker(ticker_str)
        info = tk.fast_info

        ltp = getattr(info, "last_price", 0) or 0
        prev_close = getattr(info, "previous_close", 0) or 0
        change = round(ltp - prev_close, 2) if ltp and prev_close else 0
        pct_change = round((change / prev_close) * 100, 2) if prev_close else 0
        day_high = getattr(info, "day_high", 0) or 0
        day_low = getattr(info, "day_low", 0) or 0
        year_high = getattr(info, "year_high", 0) or 0
        year_low = getattr(info, "year_low", 0) or 0
        volume = getattr(info, "last_volume", 0) or 0
        open_price = getattr(info, "open", 0) or 0

        return {
            "symbol": symbol,
            "name": symbol,
            "ticker": ticker_str,
            "open": round(_clean(open_price), 2),
            "high": round(_clean(day_high), 2),
            "low": round(_clean(day_low), 2),
            "ltp": round(_clean(ltp), 2),
            "prev_close": round(_clean(prev_close), 2),
            "change": round(_clean(change), 2),
            "pct_change": round(_clean(pct_change), 2),
            "volume": int(_clean(volume)),
            "year_high": round(_clean(year_high), 2),
            "year_low": round(_clean(year_low), 2),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch {ticker_str}: {e}")
        return {
            "symbol": symbol,
            "name": symbol,
            "ticker": ticker_str,
            "open": 0, "high": 0, "low": 0, "ltp": 0,
            "prev_close": 0, "change": 0, "pct_change": 0,
            "volume": 0, "year_high": 0, "year_low": 0,
        }


def get_index_stocks(index_name: str = "NIFTY 50") -> Dict:
    """
    Fetch live market data for all stocks in an index.
    Uses yfinance with parallel requests for speed.
    """
    symbols = SUPPORTED_INDICES.get(index_name.upper())
    if not symbols:
        raise ValueError(
            f"Unsupported index: {index_name}. "
            f"Supported: {list(SUPPORTED_INDICES.keys())}"
        )

    stocks = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_single_stock, sym): sym for sym in symbols}
        for future in as_completed(futures):
            stocks.append(future.result())

    # Sort by symbol
    stocks.sort(key=lambda s: s["symbol"])

    return {
        "index_name": index_name,
        "last_updated": "Live",
        "stocks": stocks,
        "total_count": len(stocks),
    }


def screen_stocks(
    index_name: str = "NIFTY 50",
    pct_change_threshold: float = 2.0,
    near_52w_pct: float = 5.0,
) -> Dict:
    """
    Fetch index stocks and flag 'interesting' ones for deep analysis.

    Screening rules:
    1. Big movers: |% change| >= pct_change_threshold
    2. Near 52-week high: price within near_52w_pct% of year_high
    3. Near 52-week low: price within near_52w_pct% of year_low
    """
    result = get_index_stocks(index_name)
    stocks = result["stocks"]

    flagged = []
    for stock in stocks:
        reasons = []
        ltp = stock["ltp"] or 0
        pct = stock["pct_change"] or 0
        y_high = stock["year_high"] or 0
        y_low = stock["year_low"] or 0

        # Rule 1: Big movers
        if abs(pct) >= pct_change_threshold:
            direction = "up" if pct > 0 else "down"
            reasons.append(f"Big mover: {pct:+.2f}% {direction}")

        # Rule 2: Near 52-week high
        if y_high > 0 and ltp > 0:
            dist_from_high = ((y_high - ltp) / y_high) * 100
            if dist_from_high <= near_52w_pct:
                reasons.append(f"Near 52W high ({dist_from_high:.1f}% away)")

        # Rule 3: Near 52-week low
        if y_low > 0 and ltp > 0:
            dist_from_low = ((ltp - y_low) / y_low) * 100
            if dist_from_low <= near_52w_pct:
                reasons.append(f"Near 52W low ({dist_from_low:.1f}% above)")

        stock["flagged"] = len(reasons) > 0
        stock["flag_reasons"] = reasons

        if reasons:
            flagged.append(stock)

    result["flagged"] = flagged
    result["flagged_count"] = len(flagged)

    return result
