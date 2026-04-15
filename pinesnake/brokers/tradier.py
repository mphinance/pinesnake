"""
PineSnake Tradier Broker Client — Embedded in generated scripts.

This module is NOT used at transpile-time. Instead, its logic is
embedded into generated Python scripts via the Jinja2 template.
This file serves as the reference implementation and can also be
used for testing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)


@dataclass
class TradierConfig:
    """Tradier API configuration."""
    api_key: str
    account_id: str
    sandbox: bool = True

    @property
    def base_url(self) -> str:
        if self.sandbox:
            return "https://sandbox.tradier.com/v1"
        return "https://api.tradier.com/v1"

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }


class TradierClient:
    """
    Tradier REST API client for trading operations.

    Supports:
        - Market data (OHLCV bars)
        - Order placement (market, limit, stop)
        - Position queries
        - Account balance
        - Market clock (is market open?)
    """

    def __init__(self, config: TradierConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.headers)

    def fetch_bars(
        self,
        symbol: str,
        interval: str = "5min",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV bars from Tradier market data API.

        Args:
            symbol: Ticker symbol (e.g., "SPY")
            interval: Bar interval (1min, 5min, 15min, daily)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        # Map user-friendly intervals to Tradier API values
        interval_map = {
            "1min": "1min", "5min": "5min", "15min": "15min",
            "1h": "60min", "4h": "daily", "1d": "daily",
            "daily": "daily", "weekly": "weekly", "monthly": "monthly",
        }
        tradier_interval = interval_map.get(interval, interval)

        # Use timesales for intraday, history for daily+
        if tradier_interval in ("daily", "weekly", "monthly"):
            url = f"{self.config.base_url}/markets/history"
            params: dict[str, Any] = {
                "symbol": symbol,
                "interval": tradier_interval,
            }
            if start:
                params["start"] = start
            if end:
                params["end"] = end

            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            days = data.get("history", {}).get("day", [])
            if not days:
                logger.warning(f"No historical data returned for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(days)
        else:
            url = f"{self.config.base_url}/markets/timesales"
            params = {
                "symbol": symbol,
                "interval": tradier_interval,
                "session_filter": "open",
            }
            if start:
                params["start"] = start
            if end:
                params["end"] = end

            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            series = data.get("series", {}).get("data", [])
            if not series:
                logger.warning(f"No timesales data returned for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(series)

        # Normalize columns
        for col in ("open", "high", "low", "close", "price"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

        # timesales uses 'price' instead of 'close'
        if "price" in df.columns and "close" not in df.columns:
            df["close"] = df["price"]

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

        return df

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = "market",
        price: float | None = None,
        stop: float | None = None,
        duration: str = "day",
    ) -> dict[str, Any]:
        """
        Place an equity order via Tradier.

        Args:
            symbol: Ticker symbol
            side: "buy", "sell", "buy_to_cover", "sell_short"
            quantity: Number of shares
            order_type: "market", "limit", "stop", "stop_limit"
            price: Limit price (for limit/stop_limit orders)
            stop: Stop price (for stop/stop_limit orders)
            duration: "day" or "gtc"

        Returns:
            Tradier order response dict.
        """
        url = f"{self.config.base_url}/accounts/{self.config.account_id}/orders"
        data: dict[str, Any] = {
            "class": "equity",
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "type": order_type,
            "duration": duration,
        }

        if price is not None and order_type in ("limit", "stop_limit"):
            data["price"] = str(price)
        if stop is not None and order_type in ("stop", "stop_limit"):
            data["stop"] = str(stop)

        logger.info(f"Placing order: {side} {quantity} {symbol} ({order_type})")
        resp = self.session.post(url, data=data)
        resp.raise_for_status()
        return resp.json()

    def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions for the account."""
        url = f"{self.config.base_url}/accounts/{self.config.account_id}/positions"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        positions = data.get("positions", {}).get("position", [])
        if isinstance(positions, dict):
            positions = [positions]
        return positions

    def get_position_qty(self, symbol: str) -> int:
        """Get current quantity held for a symbol."""
        positions = self.get_positions()
        for pos in positions:
            if pos.get("symbol", "").upper() == symbol.upper():
                return int(pos.get("quantity", 0))
        return 0

    def cancel_all_orders(self) -> list[dict[str, Any]]:
        """Cancel all open orders for the account."""
        url = f"{self.config.base_url}/accounts/{self.config.account_id}/orders"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        orders = data.get("orders", {}).get("order", [])
        if isinstance(orders, dict):
            orders = [orders]

        results = []
        for order in orders:
            if order.get("status") in ("pending", "open", "partially_filled"):
                order_id = order["id"]
                cancel_url = f"{url}/{order_id}"
                cancel_resp = self.session.delete(cancel_url)
                results.append({"order_id": order_id, "status": cancel_resp.status_code})
                logger.info(f"Cancelled order {order_id}")

        return results

    def get_balance(self) -> dict[str, Any]:
        """Get account balance/buying power."""
        url = f"{self.config.base_url}/accounts/{self.config.account_id}/balances"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json().get("balances", {})

    def is_market_open(self) -> bool:
        """Check if the market is currently open."""
        url = f"{self.config.base_url}/markets/clock"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            clock = resp.json().get("clock", {})
            state = clock.get("state", "closed")
            return state == "open"
        except Exception as e:
            logger.error(f"Failed to check market clock: {e}")
            return False
