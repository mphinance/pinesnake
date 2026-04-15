"""
PineSnake Strategy Mappings — strategy.* → Tradier API operations.

Maps Pine Script strategy functions (entry, close, exit, cancel_all)
to their Tradier REST API equivalents for code generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OrderSide(Enum):
    """Tradier order sides."""
    BUY = "buy"
    SELL = "sell"
    BUY_TO_COVER = "buy_to_cover"
    SELL_SHORT = "sell_short"


class OrderType(Enum):
    """Tradier order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class TradierOrder:
    """Represents a Tradier API order call to embed in generated code."""
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    stop_price: str | None = None
    limit_price: str | None = None
    comment: str = ""


# Pine Script strategy function → Tradier API mapping
STRATEGY_MAP = {
    "strategy.entry": {
        "long": TradierOrder(
            side=OrderSide.BUY,
            comment="strategy.entry() → Buy shares (LONG entry)",
        ),
        "short": TradierOrder(
            side=OrderSide.SELL_SHORT,
            comment="strategy.entry() → Sell short (SHORT entry) [V2]",
        ),
    },
    "strategy.close": {
        "long": TradierOrder(
            side=OrderSide.SELL,
            comment="strategy.close() → Sell all shares to flatten position",
        ),
        "short": TradierOrder(
            side=OrderSide.BUY_TO_COVER,
            comment="strategy.close() → Buy to cover short position [V2]",
        ),
    },
}


def get_order_for_strategy_call(
    pine_func: str,
    direction: str = "long",
    stop: str | None = None,
    limit: str | None = None,
) -> TradierOrder:
    """
    Get the appropriate Tradier order config for a Pine Script strategy call.

    Args:
        pine_func: e.g., "strategy.entry"
        direction: "long" or "short"
        stop: Stop price expression (optional)
        limit: Limit price expression (optional)

    Returns:
        TradierOrder with the correct side and order type.
    """
    direction = direction.lower()

    if pine_func == "strategy.exit":
        # Exit with stop/limit becomes a bracket order
        order = TradierOrder(
            side=OrderSide.SELL,
            comment="strategy.exit() → Protective stop/limit order",
        )
        if stop and limit:
            order.order_type = OrderType.STOP_LIMIT
            order.stop_price = stop
            order.limit_price = limit
        elif stop:
            order.order_type = OrderType.STOP
            order.stop_price = stop
        elif limit:
            order.order_type = OrderType.LIMIT
            order.limit_price = limit
        return order

    if pine_func == "strategy.cancel_all":
        return TradierOrder(
            side=OrderSide.SELL,  # placeholder
            comment="strategy.cancel_all() → Cancel all open orders",
        )

    mapping = STRATEGY_MAP.get(pine_func, {})
    order = mapping.get(direction)
    if order is None:
        return TradierOrder(
            side=OrderSide.BUY,
            comment=f"Unknown strategy call: {pine_func}",
        )
    return order
