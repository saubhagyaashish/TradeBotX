"""upstox_client.py — Upstox REST API wrapper for TradeBotX.

Covers:
  - Full Market Quotes (LTP, OHLC, depth)
  - Historical Candle Data V3 (minutes/hours/days/weeks/months)
  - Intraday Candle Data V3
  - Order placement/modification/cancellation
  - Portfolio (positions, holdings)
  - Option Chain
  - Instrument key mapping (symbol → instrument_key)
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional

import httpx
import pandas as pd

from upstox_auth import UpstoxConfig

logger = logging.getLogger(__name__)

# ── Instrument key mapping ────────────────────────────────────────────────────
# Maps common symbol names to Upstox instrument keys.
# This is a subset — full list downloaded from Upstox BOD instruments CSV.

NIFTY_50_INSTRUMENTS: dict[str, str] = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "INFY": "NSE_EQ|INE009A01021",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "ITC": "NSE_EQ|INE154A01025",
    "SBIN": "NSE_EQ|INE062A01020",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "LT": "NSE_EQ|INE018A01030",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "WIPRO": "NSE_EQ|INE075A01022",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "MARUTI": "NSE_EQ|INE585B01010",
    "TITAN": "NSE_EQ|INE280A01028",
    "SUNPHARMA": "NSE_EQ|INE044A01036",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "BAJAJFINSV": "NSE_EQ|INE918I01018",
    "HCLTECH": "NSE_EQ|INE860A01027",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "NTPC": "NSE_EQ|INE733E01010",
    "POWERGRID": "NSE_EQ|INE752E01010",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "ONGC": "NSE_EQ|INE213A01029",
    "TATASTEEL": "NSE_EQ|INE081A01020",
    "M&M": "NSE_EQ|INE101A01026",
    "JSWSTEEL": "NSE_EQ|INE019A01038",
    "ADANIENT": "NSE_EQ|INE423A01024",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "COALINDIA": "NSE_EQ|INE522F01014",
    "BPCL": "NSE_EQ|INE541A01028",
    "GRASIM": "NSE_EQ|INE047A01021",
    "TECHM": "NSE_EQ|INE669C01036",
    "INDUSINDBK": "NSE_EQ|INE095A01012",
    "HINDALCO": "NSE_EQ|INE038A01020",
    "DRREDDY": "NSE_EQ|INE089A01023",
    "CIPLA": "NSE_EQ|INE059A01026",
    "DIVISLAB": "NSE_EQ|INE361B01024",
    "BRITANNIA": "NSE_EQ|INE216A01030",
    "EICHERMOT": "NSE_EQ|INE066A01021",
    "APOLLOHOSP": "NSE_EQ|INE437A01024",
    "NESTLEIND": "NSE_EQ|INE239A01016",
    "SBILIFE": "NSE_EQ|INE123W01016",
    "HDFCLIFE": "NSE_EQ|INE795G01014",
    "TATACONSUM": "NSE_EQ|INE192A01025",
    "HEROMOTOCO": "NSE_EQ|INE158A01026",
    "BAJAJ-AUTO": "NSE_EQ|INE917I01010",
    "SHRIRAMFIN": "NSE_EQ|INE721A01013",
    "BEL": "NSE_EQ|INE263A01024",
}

# NIFTY BANK additional stocks
NIFTY_BANK_INSTRUMENTS: dict[str, str] = {
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "SBIN": "NSE_EQ|INE062A01020",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "INDUSINDBK": "NSE_EQ|INE095A01012",
    "BANKBARODA": "NSE_EQ|INE028A01039",
    "AUBANK": "NSE_EQ|INE949L01017",
    "BANDHANBNK": "NSE_EQ|INE545U01014",
    "FEDERALBNK": "NSE_EQ|INE171A01029",
    "IDFCFIRSTB": "NSE_EQ|INE092T01019",
    "PNB": "NSE_EQ|INE160A01022",
}

# Index instrument keys
INDEX_INSTRUMENTS: dict[str, str] = {
    "NIFTY 50": "NSE_INDEX|Nifty 50",
    "NIFTY BANK": "NSE_INDEX|Nifty Bank",
    "NIFTY IT": "NSE_INDEX|Nifty IT",
    "NIFTY MIDCAP 50": "NSE_INDEX|NIFTY Midcap 50",
}

# Combined map
ALL_INSTRUMENTS: dict[str, str] = {
    **NIFTY_50_INSTRUMENTS,
    **NIFTY_BANK_INSTRUMENTS,
    **INDEX_INSTRUMENTS,
}


def symbol_to_instrument_key(symbol: str) -> Optional[str]:
    """Convert a common symbol name to an Upstox instrument_key."""
    # Clean up symbol — remove .NS suffix if present (from yfinance)
    clean = symbol.replace(".NS", "").replace(".BO", "").upper().strip()
    return ALL_INSTRUMENTS.get(clean)


def instrument_key_to_symbol(instrument_key: str) -> str:
    """Reverse lookup: instrument_key → symbol."""
    for sym, ikey in ALL_INSTRUMENTS.items():
        if ikey == instrument_key:
            return sym
    # Fallback: return the key itself
    return instrument_key


# ── Main API Client ───────────────────────────────────────────────────────────


class UpstoxClient:
    """Async wrapper around the Upstox REST API v2/v3."""

    BASE_URL = "https://api.upstox.com"
    HFT_URL = "https://api-hft.upstox.com"  # For order placement (faster routing)

    def __init__(self, config: UpstoxConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create and return a persistent httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=15.0,
                headers=self.config.headers,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── Internal request helpers ──────────────────────────────────────────────

    async def _get(self, url: str, params: dict = None) -> dict:
        """Make a GET request, return parsed JSON."""
        client = await self._ensure_client()
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _post(self, url: str, json_data: dict = None) -> dict:
        """Make a POST request (for orders — uses HFT URL)."""
        client = await self._ensure_client()
        resp = await client.post(url, json=json_data)
        resp.raise_for_status()
        return resp.json()

    async def _put(self, url: str, json_data: dict = None) -> dict:
        """Make a PUT request."""
        client = await self._ensure_client()
        resp = await client.put(url, json=json_data)
        resp.raise_for_status()
        return resp.json()

    async def _delete(self, url: str, params: dict = None) -> dict:
        """Make a DELETE request."""
        client = await self._ensure_client()
        resp = await client.delete(url, params=params)
        resp.raise_for_status()
        return resp.json()

    # ══════════════════════════════════════════════════════════════════════════
    # MARKET DATA — Quotes
    # ══════════════════════════════════════════════════════════════════════════

    async def get_full_quote(self, instrument_keys: list[str]) -> dict:
        """
        Get full market quotes for up to 500 instruments.
        Returns OHLC, depth, volume, circuit limits, etc.

        Args:
            instrument_keys: e.g. ["NSE_EQ|INE002A01018", "NSE_EQ|INE009A01021"]

        Returns:
            dict with instrument data keyed by "NSE_EQ:SYMBOL"
        """
        keys_str = ",".join(instrument_keys)
        data = await self._get(
            f"{self.BASE_URL}/v2/market-quote/quotes",
            params={"instrument_key": keys_str},
        )
        return data.get("data", {})

    async def get_ltp(self, instrument_keys: list[str]) -> dict:
        """Get Last Traded Price for instruments."""
        keys_str = ",".join(instrument_keys)
        data = await self._get(
            f"{self.BASE_URL}/v2/market-quote/ltp",
            params={"instrument_key": keys_str},
        )
        return data.get("data", {})

    async def get_ohlc(self, instrument_keys: list[str]) -> dict:
        """Get OHLC data for instruments."""
        keys_str = ",".join(instrument_keys)
        data = await self._get(
            f"{self.BASE_URL}/v2/market-quote/ohlc",
            params={"instrument_key": keys_str},
        )
        return data.get("data", {})

    # ══════════════════════════════════════════════════════════════════════════
    # MARKET DATA — Quotes (by symbol name)
    # ══════════════════════════════════════════════════════════════════════════

    async def get_quote_by_symbol(self, symbol: str) -> Optional[dict]:
        """
        Convenience: get full quote for a symbol by name.
        Returns the quote dict or None.
        """
        ikey = symbol_to_instrument_key(symbol)
        if not ikey:
            logger.warning("Unknown symbol: %s", symbol)
            return None

        quotes = await self.get_full_quote([ikey])
        # Keys in response use colon format: "NSE_EQ:SYMBOL"
        for key, value in quotes.items():
            return value  # Return first (and only) result
        return None

    async def get_ltp_by_symbol(self, symbol: str) -> Optional[float]:
        """Get LTP for a symbol by name. Returns price or None."""
        ikey = symbol_to_instrument_key(symbol)
        if not ikey:
            return None
        data = await self.get_ltp([ikey])
        for key, value in data.items():
            return value.get("last_price")
        return None

    async def get_batch_ltp(self, symbols: list[str]) -> dict[str, float]:
        """
        Get LTP for all symbols in a single API call (Fix #7).
        Upstox supports up to 500 instrument keys per request.

        Returns: {symbol: ltp, ...}
        """
        ikeys = []
        key_to_symbol = {}
        for sym in symbols:
            ikey = symbol_to_instrument_key(sym)
            if ikey:
                ikeys.append(ikey)
                key_to_symbol[ikey] = sym

        if not ikeys:
            return {}

        # Upstox returns keys in "NSE_EQ:SYMBOL" format
        data = await self.get_ltp(ikeys)
        result = {}
        for resp_key, value in data.items():
            ltp = value.get("last_price")
            if ltp is not None:
                # Map back: response key "NSE_EQ:RELIANCE" → find matching instrument
                for ikey, sym in key_to_symbol.items():
                    if ikey.split("|")[0] in resp_key:
                        # Check if symbol matches by looking up the ISIN
                        check_key = resp_key.replace(":", "|")
                        if check_key in key_to_symbol or sym.upper() in resp_key.upper():
                            result[sym] = ltp
                            break
                else:
                    # Fallback: extract symbol from response key
                    parts = resp_key.split(":")
                    if len(parts) >= 2:
                        result[parts[-1]] = ltp

        return result

    async def get_batch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """
        Get full quotes (LTP + OHLC + volume) for all symbols in one call.
        Returns: {symbol: {ltp, open, high, low, close, volume, ...}, ...}
        """
        ikeys = []
        for sym in symbols:
            ikey = symbol_to_instrument_key(sym)
            if ikey:
                ikeys.append(ikey)

        if not ikeys:
            return {}

        data = await self.get_full_quote(ikeys)
        result = {}
        for resp_key, value in data.items():
            parts = resp_key.split(":")
            sym = parts[-1] if len(parts) >= 2 else resp_key
            ohlc = value.get("ohlc", {})
            result[sym] = {
                "ltp": value.get("last_price"),
                "open": ohlc.get("open"),
                "high": ohlc.get("high"),
                "low": ohlc.get("low"),
                "close": ohlc.get("close"),
                "volume": value.get("volume"),
                "change": value.get("net_change"),
                "pct_change": value.get("percentage_change"),
            }
        return result

    async def get_movers(
        self, symbols: list[str], threshold_pct: float = 0.5
    ) -> list[dict]:
        """
        Get stocks that moved > threshold_pct from open (Fix #7: smart API strategy).
        Only these stocks need full signal analysis.

        Returns: sorted list of movers by absolute % change (largest first)
        """
        quotes = await self.get_batch_quotes(symbols)
        movers = []
        for sym, q in quotes.items():
            ltp = q.get("ltp")
            open_price = q.get("open")
            if ltp and open_price and open_price > 0:
                pct = ((ltp - open_price) / open_price) * 100
                if abs(pct) >= threshold_pct:
                    movers.append({
                        "symbol": sym,
                        "ltp": ltp,
                        "open": open_price,
                        "pct_change": round(pct, 2),
                        "volume": q.get("volume"),
                    })
        movers.sort(key=lambda m: abs(m["pct_change"]), reverse=True)
        return movers

    # ══════════════════════════════════════════════════════════════════════════
    # HISTORICAL DATA — V3 Candles
    # ══════════════════════════════════════════════════════════════════════════

    async def get_historical_candles(
        self,
        instrument_key: str,
        unit: str = "days",
        interval: str = "1",
        to_date: str = None,
        from_date: str = None,
    ) -> list[list]:
        """
        Fetch historical OHLC candle data (V3 API).

        Args:
            instrument_key: e.g. "NSE_EQ|INE002A01018"
            unit: "minutes", "hours", "days", "weeks", "months"
            interval: "1", "3", "5", "15", "30" etc.
            to_date: "YYYY-MM-DD" (inclusive end)
            from_date: "YYYY-MM-DD" (inclusive start)

        Returns:
            List of candles: [[timestamp, open, high, low, close, volume, oi], ...]
        """
        if to_date is None:
            to_date = date.today().isoformat()
        if from_date is None:
            from_date = (date.today() - timedelta(days=100)).isoformat()

        # URL-encode the pipe character in instrument_key
        encoded_key = instrument_key.replace("|", "%7C")
        url = (
            f"{self.BASE_URL}/v3/historical-candle"
            f"/{encoded_key}/{unit}/{interval}/{to_date}/{from_date}"
        )

        data = await self._get(url)
        return data.get("data", {}).get("candles", [])

    async def get_intraday_candles(
        self,
        instrument_key: str,
        unit: str = "minutes",
        interval: str = "1",
    ) -> list[list]:
        """
        Fetch today's intraday candle data (V3 API).

        Args:
            instrument_key: e.g. "NSE_EQ|INE002A01018"
            unit: "minutes" or "hours"
            interval: "1", "3", "5", "15", "30" etc.

        Returns:
            List of candles: [[timestamp, open, high, low, close, volume, oi], ...]
        """
        encoded_key = instrument_key.replace("|", "%7C")
        url = (
            f"{self.BASE_URL}/v3/intraday-candle"
            f"/{encoded_key}/{unit}/{interval}"
        )

        data = await self._get(url)
        return data.get("data", {}).get("candles", [])

    async def get_candles_as_df(
        self,
        symbol: str,
        unit: str = "days",
        interval: str = "1",
        to_date: str = None,
        from_date: str = None,
    ) -> Optional[pd.DataFrame]:
        """
        Convenience: get historical candles as a pandas DataFrame.

        Returns DataFrame with columns: [timestamp, open, high, low, close, volume, oi]
        """
        ikey = symbol_to_instrument_key(symbol)
        if not ikey:
            logger.warning("Unknown symbol for candles: %s", symbol)
            return None

        candles = await self.get_historical_candles(
            ikey, unit, interval, to_date, from_date
        )

        if not candles:
            return None

        df = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume", "oi"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    async def get_intraday_candles_as_df(
        self,
        symbol: str,
        interval: str = "5",
    ) -> Optional[pd.DataFrame]:
        """
        Get today's intraday candles as a DataFrame (Fix #8: dual-timeframe).

        Args:
            symbol: e.g. "RELIANCE"
            interval: "1", "5", "15", "30" (minutes)

        Returns:
            DataFrame with columns: [timestamp, open, high, low, close, volume, oi]
        """
        ikey = symbol_to_instrument_key(symbol)
        if not ikey:
            logger.warning("Unknown symbol for intraday candles: %s", symbol)
            return None

        candles = await self.get_intraday_candles(ikey, "minutes", interval)
        if not candles:
            return None

        df = pd.DataFrame(
            candles,
            columns=["timestamp", "open", "high", "low", "close", "volume", "oi"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    # ══════════════════════════════════════════════════════════════════════════
    # ORDERS
    # ══════════════════════════════════════════════════════════════════════════

    async def place_order(
        self,
        instrument_token: str,
        quantity: int,
        order_type: str = "MARKET",
        transaction_type: str = "BUY",
        product: str = "D",
        validity: str = "DAY",
        price: float = 0,
        trigger_price: float = 0,
        disclosed_quantity: int = 0,
        is_amo: bool = False,
        tag: str = "TradeBotX",
    ) -> Optional[str]:
        """
        Place an order via the Upstox HFT endpoint.

        Args:
            instrument_token: e.g. "NSE_EQ|INE002A01018"
            quantity: Number of shares
            order_type: "MARKET", "LIMIT", "SL", "SL-M"
            transaction_type: "BUY" or "SELL"
            product: "D" (Delivery), "I" (Intraday), "MTF" (Margin)
            validity: "DAY" or "IOC"
            price: Limit price (0 for MARKET)
            trigger_price: Stop-loss trigger price
            tag: Order tag for identification

        Returns:
            order_id string on success, None on failure
        """
        payload = {
            "quantity": quantity,
            "product": product,
            "validity": validity,
            "price": price,
            "tag": tag,
            "instrument_token": instrument_token,
            "order_type": order_type,
            "transaction_type": transaction_type,
            "disclosed_quantity": disclosed_quantity,
            "trigger_price": trigger_price,
            "is_amo": is_amo,
        }

        try:
            data = await self._post(
                f"{self.HFT_URL}/v2/order/place", json_data=payload
            )
            order_id = data.get("data", {}).get("order_id")
            logger.info(
                "Order placed: %s %s %d x %s → %s",
                transaction_type, order_type, quantity, instrument_token, order_id,
            )
            return order_id
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Order placement failed (HTTP %d): %s",
                exc.response.status_code,
                exc.response.text,
            )
            return None
        except Exception as exc:
            logger.error("Order placement error: %s", exc)
            return None

    async def modify_order(
        self,
        order_id: str,
        quantity: int = None,
        price: float = None,
        trigger_price: float = None,
        order_type: str = None,
        validity: str = None,
    ) -> Optional[dict]:
        """Modify an existing order."""
        payload: dict[str, Any] = {"order_id": order_id}
        if quantity is not None:
            payload["quantity"] = quantity
        if price is not None:
            payload["price"] = price
        if trigger_price is not None:
            payload["trigger_price"] = trigger_price
        if order_type is not None:
            payload["order_type"] = order_type
        if validity is not None:
            payload["validity"] = validity

        try:
            data = await self._put(
                f"{self.HFT_URL}/v2/order/modify", json_data=payload
            )
            logger.info("Order modified: %s", order_id)
            return data.get("data")
        except Exception as exc:
            logger.error("Order modify failed for %s: %s", order_id, exc)
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID. Returns True on success."""
        try:
            await self._delete(
                f"{self.HFT_URL}/v2/order/cancel",
                params={"order_id": order_id},
            )
            logger.info("Order cancelled: %s", order_id)
            return True
        except Exception as exc:
            logger.error("Order cancel failed for %s: %s", order_id, exc)
            return False

    async def get_order_book(self) -> list:
        """Get all orders for the day."""
        data = await self._get(f"{self.BASE_URL}/v2/order/retrieve-all")
        return data.get("data", [])

    async def get_order_history(self, order_id: str) -> list:
        """Get order modification history."""
        data = await self._get(
            f"{self.BASE_URL}/v2/order/history",
            params={"order_id": order_id},
        )
        return data.get("data", [])

    async def get_trades(self) -> list:
        """Get all trades for the day."""
        data = await self._get(f"{self.BASE_URL}/v2/order/trades/get-trades-for-day")
        return data.get("data", [])

    # ══════════════════════════════════════════════════════════════════════════
    # PORTFOLIO
    # ══════════════════════════════════════════════════════════════════════════

    async def get_positions(self) -> list:
        """Get current day positions."""
        data = await self._get(f"{self.BASE_URL}/v2/portfolio/short-term-positions")
        return data.get("data", [])

    async def get_holdings(self) -> list:
        """Get long-term holdings."""
        data = await self._get(f"{self.BASE_URL}/v2/portfolio/long-term-holdings")
        return data.get("data", [])

    # ══════════════════════════════════════════════════════════════════════════
    # OPTION CHAIN
    # ══════════════════════════════════════════════════════════════════════════

    async def get_option_chain(
        self, instrument_key: str, expiry_date: str
    ) -> Optional[dict]:
        """
        Get option chain data for an instrument.

        Args:
            instrument_key: e.g. "NSE_INDEX|Nifty 50"
            expiry_date: "YYYY-MM-DD"

        Returns:
            Option chain data dict
        """
        try:
            data = await self._get(
                f"{self.BASE_URL}/v2/option/chain",
                params={
                    "instrument_key": instrument_key,
                    "expiry_date": expiry_date,
                },
            )
            return data.get("data")
        except Exception as exc:
            logger.error("Option chain fetch failed: %s", exc)
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # WEBSOCKET AUTH
    # ══════════════════════════════════════════════════════════════════════════

    async def get_ws_feed_url(self) -> Optional[str]:
        """
        Get the authorized WebSocket URL for market data feed V3.
        This URL is used to establish the WebSocket connection.
        """
        try:
            data = await self._get(
                f"{self.BASE_URL}/v3/feed/market-data-feed/authorize"
            )
            url = data.get("data", {}).get("authorized_redirect_uri")
            if url:
                logger.info("WebSocket feed URL obtained")
            return url
        except Exception as exc:
            logger.error("WebSocket auth failed: %s", exc)
            return None

    async def get_portfolio_feed_url(self) -> Optional[str]:
        """Get the authorized WebSocket URL for portfolio stream feed."""
        try:
            data = await self._get(
                f"{self.BASE_URL}/v2/feed/portfolio-stream-feed/authorize"
            )
            return data.get("data", {}).get("authorized_redirect_uri")
        except Exception as exc:
            logger.error("Portfolio feed auth failed: %s", exc)
            return None
