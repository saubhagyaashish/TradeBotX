"""upstox_ws.py — Upstox WebSocket V3 market data feed manager.

Provides real-time price streaming for subscribed instruments.
Uses the V3 WebSocket API with JSON message format.

Flow:
  1. Get authorized WebSocket URL via REST API
  2. Connect to WebSocket endpoint
  3. Subscribe to instrument keys with desired mode
  4. Receive and dispatch tick data via callbacks
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Optional

import websockets

from upstox_client import UpstoxClient

logger = logging.getLogger(__name__)

# ── Subscription modes ────────────────────────────────────────────────────────
# ltpc  — Last Traded Price + Change only (lightest)
# full  — LTP + OHLC + depth (5 bid/ask levels) + volume

MODE_LTPC = "ltpc"
MODE_FULL = "full"


class UpstoxWebSocket:
    """
    Manages a persistent WebSocket connection to Upstox V3 market data feed.

    Usage:
        ws = UpstoxWebSocket(upstox_client)
        ws.on_tick(my_tick_handler)
        await ws.connect()
        await ws.subscribe(["NSE_EQ|INE002A01018"], mode="ltpc")
        # ... ticks flow to my_tick_handler
        await ws.disconnect()
    """

    def __init__(self, client: UpstoxClient):
        self.client = client
        self._ws: Optional[Any] = None
        self._connected = False
        self._subscriptions: dict[str, str] = {}  # instrument_key → mode
        self._tick_callbacks: list[Callable] = []
        self._order_callbacks: list[Callable] = []
        self._reconnect_attempts = 0
        self._max_reconnects = 5
        self._reconnect_delay = 5  # seconds
        self._listen_task: Optional[asyncio.Task] = None
        self._should_run = False

    # ── Callback registration ─────────────────────────────────────────────

    def on_tick(self, callback: Callable[[dict], None]):
        """Register a callback for market data ticks."""
        self._tick_callbacks.append(callback)

    def on_order_update(self, callback: Callable[[dict], None]):
        """Register a callback for order status updates."""
        self._order_callbacks.append(callback)

    # ── Connection management ─────────────────────────────────────────────

    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        Returns True if connected successfully.
        """
        ws_url = await self.client.get_ws_feed_url()
        if not ws_url:
            logger.error("Failed to get WebSocket feed URL")
            return False

        try:
            self._ws = await websockets.connect(
                ws_url,
                additional_headers={
                    "Authorization": f"Bearer {self.client.config.access_token}",
                    "Accept": "application/json",
                },
            )
            self._connected = True
            self._reconnect_attempts = 0
            self._should_run = True
            logger.info("🔌 WebSocket connected to Upstox feed")

            # Start the listener loop
            self._listen_task = asyncio.create_task(self._listen_loop())
            return True

        except Exception as exc:
            logger.error("WebSocket connection failed: %s", exc)
            self._connected = False
            return False

    async def disconnect(self):
        """Gracefully disconnect the WebSocket."""
        self._should_run = False

        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass

        if self._ws:
            await self._ws.close()
            self._ws = None

        self._connected = False
        logger.info("🔌 WebSocket disconnected")

    async def _reconnect(self):
        """Attempt to reconnect after a disconnect."""
        if self._reconnect_attempts >= self._max_reconnects:
            logger.error(
                "Max reconnect attempts (%d) reached — giving up",
                self._max_reconnects,
            )
            return

        self._reconnect_attempts += 1
        delay = self._reconnect_delay * self._reconnect_attempts
        logger.warning(
            "Reconnecting in %ds (attempt %d/%d)...",
            delay,
            self._reconnect_attempts,
            self._max_reconnects,
        )
        await asyncio.sleep(delay)

        if await self.connect():
            # Re-subscribe to all previous instruments
            if self._subscriptions:
                # Group by mode
                by_mode: dict[str, list[str]] = {}
                for ikey, mode in self._subscriptions.items():
                    by_mode.setdefault(mode, []).append(ikey)
                for mode, keys in by_mode.items():
                    await self.subscribe(keys, mode=mode)

    # ── Subscription management ───────────────────────────────────────────

    async def subscribe(
        self, instrument_keys: list[str], mode: str = MODE_LTPC
    ) -> bool:
        """
        Subscribe to market data for instruments.

        Args:
            instrument_keys: List of instrument keys
            mode: "ltpc" or "full"
        """
        if not self._connected or not self._ws:
            logger.error("Cannot subscribe — WebSocket not connected")
            return False

        msg = {
            "guid": f"sub_{int(time.time())}",
            "method": "sub",
            "data": {
                "mode": mode,
                "instrumentKeys": instrument_keys,
            },
        }

        try:
            await self._ws.send(json.dumps(msg))
            for key in instrument_keys:
                self._subscriptions[key] = mode
            logger.info(
                "📡 Subscribed to %d instruments (mode: %s)",
                len(instrument_keys),
                mode,
            )
            return True
        except Exception as exc:
            logger.error("Subscribe failed: %s", exc)
            return False

    async def unsubscribe(self, instrument_keys: list[str]) -> bool:
        """Unsubscribe from market data for instruments."""
        if not self._connected or not self._ws:
            return False

        msg = {
            "guid": f"unsub_{int(time.time())}",
            "method": "unsub",
            "data": {
                "instrumentKeys": instrument_keys,
            },
        }

        try:
            await self._ws.send(json.dumps(msg))
            for key in instrument_keys:
                self._subscriptions.pop(key, None)
            logger.info("📡 Unsubscribed from %d instruments", len(instrument_keys))
            return True
        except Exception as exc:
            logger.error("Unsubscribe failed: %s", exc)
            return False

    async def change_mode(self, instrument_keys: list[str], mode: str) -> bool:
        """Change subscription mode for instruments."""
        msg = {
            "guid": f"mode_{int(time.time())}",
            "method": "change_mode",
            "data": {
                "mode": mode,
                "instrumentKeys": instrument_keys,
            },
        }

        try:
            await self._ws.send(json.dumps(msg))
            for key in instrument_keys:
                if key in self._subscriptions:
                    self._subscriptions[key] = mode
            return True
        except Exception as exc:
            logger.error("Mode change failed: %s", exc)
            return False

    # ── Internal listener ─────────────────────────────────────────────────

    async def _listen_loop(self):
        """Main listener loop — receives and dispatches messages."""
        try:
            async for raw_message in self._ws:
                try:
                    # V3 feed sends JSON messages
                    if isinstance(raw_message, bytes):
                        message = json.loads(raw_message.decode("utf-8"))
                    else:
                        message = json.loads(raw_message)

                    msg_type = message.get("type", "")

                    if msg_type == "market_info":
                        # Market status update
                        logger.debug("Market info: %s", message)

                    elif msg_type == "live_feed":
                        # Market data tick
                        feeds = message.get("feeds", {})
                        timestamp = message.get("currentTs")
                        self._dispatch_ticks(feeds, timestamp)

                    else:
                        logger.debug("Unknown message type: %s", msg_type)

                except json.JSONDecodeError:
                    logger.warning("Non-JSON message received")
                except Exception as exc:
                    logger.error("Error processing message: %s", exc)

        except websockets.exceptions.ConnectionClosed as exc:
            logger.warning("WebSocket connection closed: %s", exc)
            self._connected = False
            if self._should_run:
                await self._reconnect()

        except asyncio.CancelledError:
            logger.debug("WebSocket listener cancelled")

        except Exception as exc:
            logger.error("WebSocket listener error: %s", exc)
            self._connected = False
            if self._should_run:
                await self._reconnect()

    def _dispatch_ticks(self, feeds: dict, timestamp: str):
        """Dispatch tick data to all registered callbacks."""
        for instrument_key, feed_data in feeds.items():
            tick = {
                "instrument_key": instrument_key,
                "timestamp": timestamp,
                "data": feed_data,
            }

            # Extract LTP from different feed formats
            if "ltpc" in feed_data:
                tick["ltp"] = feed_data["ltpc"].get("ltp")
                tick["close"] = feed_data["ltpc"].get("cp")
                tick["change"] = (
                    tick["ltp"] - tick["close"] if tick["ltp"] and tick["close"] else 0
                )
            elif "fullFeed" in feed_data:
                market_ff = feed_data["fullFeed"].get("marketFF", {})
                ltpc = market_ff.get("ltpc", {})
                tick["ltp"] = ltpc.get("ltp")
                tick["close"] = ltpc.get("cp")
                tick["change"] = (
                    tick["ltp"] - tick["close"] if tick["ltp"] and tick["close"] else 0
                )
                # Also extract depth and OHLC
                tick["ohlc"] = market_ff.get("marketOHLC", {}).get("ohlc", [])
                tick["depth"] = market_ff.get("marketLevel", {})
                tick["volume"] = market_ff.get("vtt")
                tick["oi"] = market_ff.get("oi")
            elif "firstLevelWithGreeks" in feed_data:
                fg = feed_data["firstLevelWithGreeks"]
                ltpc = fg.get("ltpc", {})
                tick["ltp"] = ltpc.get("ltp")
                tick["close"] = ltpc.get("cp")
                tick["greeks"] = fg.get("optionGreeks", {})
                tick["iv"] = fg.get("iv")

            # Dispatch to callbacks
            for cb in self._tick_callbacks:
                try:
                    cb(tick)
                except Exception as exc:
                    logger.error("Tick callback error: %s", exc)

    # ── State queries ─────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def subscription_count(self) -> int:
        return len(self._subscriptions)

    @property
    def subscribed_instruments(self) -> list[str]:
        return list(self._subscriptions.keys())

    def get_status(self) -> dict:
        """Return current WebSocket status."""
        return {
            "connected": self._connected,
            "subscriptions": len(self._subscriptions),
            "instruments": list(self._subscriptions.keys()),
            "reconnect_attempts": self._reconnect_attempts,
        }
