"""
PineSnake Analyzer — Walks a pynescript AST and extracts a StrategySpec.

The StrategySpec is the intermediate representation between Pine Script
and generated Python code. It captures:
  - Strategy metadata (name, overlay, default qty)
  - Input parameters (name, type, default, title)
  - Indicator calls (ta.sma, ta.ema, ta.rsi, etc.)
  - Variable assignments
  - Entry/exit signals and strategy calls

Pynescript AST node types:
  Script(body=[...], annotations=[...])
  Expr(value=Call/Name/...)
  Assign(target=Name, value=Call/..., type=None, mode=None)
  If(test=..., body=[...], orelse=[...])
  Call(func=Name|Attribute, args=[Arg, ...])
  Arg(value=..., name=None|str)  — name=None for positional, str for keyword
  Name(id=str, ctx=Load|Store)
  Attribute(value=Name, attr=str, ctx=Load|Store)
  Constant(value=..., kind=None)
  BinOp(left, op, right), Compare(left, ops, comparators)
  BoolOp(op, values), UnaryOp(op, operand)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pynescript import ast as pine_ast

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════


class InputType(Enum):
    """Pine Script input types."""
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    SOURCE = "source"


class Direction(Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"
    ALL = "all"


class StrategyAction(Enum):
    """Strategy function type."""
    ENTRY = "entry"
    CLOSE = "close"
    EXIT = "exit"
    CANCEL_ALL = "cancel_all"


@dataclass
class InputParam:
    """A strategy input parameter (maps to .env config)."""
    name: str
    title: str
    input_type: InputType
    default_value: Any
    env_key: str = ""

    def __post_init__(self):
        if not self.env_key:
            self.env_key = _to_env_key(self.title or self.name)


@dataclass
class IndicatorCall:
    """A ta.* function call detected in Pine Script."""
    pine_func: str
    args: list[str]
    kwargs: dict[str, Any]
    result_var: str = ""              # Single-variable assignment
    result_vars: list[str] = field(default_factory=list)  # Tuple-unpack assignment
    pandas_ta_func: str = ""

    @property
    def primary_var(self) -> str:
        """The primary result variable name (first in tuple or sole var)."""
        if self.result_vars:
            return self.result_vars[0]
        return self.result_var


@dataclass
class StrategyCall:
    """A strategy.* function call (entry, close, exit)."""
    action: StrategyAction
    trade_id: str = ""
    direction: Direction = Direction.LONG
    condition: str = ""
    stop: str | None = None
    limit: str | None = None
    qty: str | None = None


@dataclass
class Assignment:
    """A variable assignment in Pine Script."""
    name: str
    expression: str
    is_series: bool = False


@dataclass
class StrategySpec:
    """
    Complete intermediate representation of a parsed Pine Script strategy.
    """
    name: str = "Untitled Strategy"
    overlay: bool = True
    default_qty_type: str = "strategy.percent_of_equity"
    default_qty_value: float = 100.0
    currency: str = "USD"
    source_file: str = ""
    pine_version: int = 5

    inputs: list[InputParam] = field(default_factory=list)
    indicators: list[IndicatorCall] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    strategy_calls: list[StrategyCall] = field(default_factory=list)
    conditions: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        """Human-readable summary of the strategy spec."""
        lines = [
            f"Strategy: {self.name}",
            f"  Inputs: {len(self.inputs)}",
            f"  Indicators: {len(self.indicators)}",
            f"  Assignments: {len(self.assignments)}",
            f"  Strategy calls: {len(self.strategy_calls)}",
        ]
        for inp in self.inputs:
            lines.append(f"    input: {inp.name} = {inp.default_value} ({inp.input_type.value})")
        for ind in self.indicators:
            lines.append(f"    indicator: {ind.result_var} = {ind.pine_func}(...)")
        for sc in self.strategy_calls:
            lines.append(f"    {sc.action.value}: {sc.trade_id} ({sc.direction.value})")
        return "\n".join(lines)


# ═══════════════════════════════════════════════
# ANALYZER — adapted to pynescript AST node types
# ═══════════════════════════════════════════════


class Analyzer:
    """
    Walks a pynescript AST and extracts a StrategySpec.
    """

    def __init__(self):
        self.spec = StrategySpec()
        self._current_condition: str | None = None

    def analyze(self, tree: pine_ast.Script, source_file: str = "") -> StrategySpec:
        self.spec = StrategySpec(source_file=source_file)
        self._walk_body(tree.body)
        logger.info(f"Analysis complete:\n{self.spec.summary()}")
        return self.spec

    def _walk_body(self, body: list) -> None:
        """Walk a list of AST statements."""
        if not body:
            return
        for stmt in body:
            self._walk_statement(stmt)

    def _walk_statement(self, stmt: Any) -> None:
        """Dispatch a statement to the appropriate handler."""
        node_type = type(stmt).__name__

        if node_type == "Expr":
            self._handle_expr(stmt)
        elif node_type == "Assign":
            self._handle_assign(stmt)
        elif node_type == "If":
            self._handle_if(stmt)
        elif node_type == "AugAssign":
            self._handle_aug_assign(stmt)
        else:
            logger.debug(f"Skipping statement type: {node_type}")

    # ───────────────────────────────────────
    # STATEMENT HANDLERS
    # ───────────────────────────────────────

    def _handle_expr(self, stmt: Any) -> None:
        """Handle Expr(value=Call/If/...)."""
        value = getattr(stmt, "value", None)
        if value is None:
            return

        value_type = type(value).__name__

        if value_type == "Call":
            func_name = self._get_func_name(value)
            if func_name == "strategy":
                self._extract_strategy_decl(value)
            elif func_name and func_name.startswith("strategy."):
                self._extract_strategy_call(func_name, value)
        elif value_type == "If":
            # pynescript wraps if-blocks as Expr(value=If(...))
            self._handle_if(value)

    def _handle_assign(self, stmt: Any) -> None:
        """Handle Assign(target=Name, value=..., ...)."""
        target = getattr(stmt, "target", None)
        value = getattr(stmt, "value", None)
        if target is None or value is None:
            return

        name = self._get_id(target)
        if not name:
            return

        # Check if RHS is an input() call
        if type(value).__name__ == "Call":
            func_name = self._get_func_name(value)

            if func_name and (func_name == "input" or func_name.startswith("input.")):
                self._extract_input(name, func_name, value)
                return

            if func_name and func_name.startswith("ta."):
                # ta.crossover / ta.crossunder assigned to a variable are boolean
                # conditions, NOT series indicators. Store them as Assignments so
                # the generator can inline them correctly when referenced in conditions.
                if func_name in ("ta.crossover", "ta.crossunder"):
                    expr_str = self._node_to_string(value)
                    self.spec.assignments.append(Assignment(
                        name=name,
                        expression=expr_str,
                        is_series=False,
                    ))
                    return

                # Detect tuple unpacking: "[macd, signal, hist] = ta.macd(...)"
                # _get_id returns comma-separated names for Tuple targets
                result_vars = [v.strip() for v in name.split(",") if v.strip()] if "," in name else []
                self._extract_indicator(name, func_name, value, result_vars=result_vars)
                return

        # Generic assignment
        expr_str = self._node_to_string(value)
        self.spec.assignments.append(Assignment(
            name=name,
            expression=expr_str,
            is_series=self._looks_like_series(expr_str),
        ))

    def _handle_aug_assign(self, stmt: Any) -> None:
        """Handle AugAssign (+=, -=, etc.)."""
        target = getattr(stmt, "target", None)
        value = getattr(stmt, "value", None)
        op = getattr(stmt, "op", None)
        name = self._get_id(target) if target else None
        if name and value and op:
            op_str = self._op_to_string(op)
            self.spec.assignments.append(Assignment(
                name=name,
                expression=f"{name} {op_str} {self._node_to_string(value)}",
            ))

    def _handle_if(self, stmt: Any) -> None:
        """Handle If(test=..., body=[...], orelse=[...])."""
        test = getattr(stmt, "test", None)
        cond_str = self._node_to_string(test) if test else "unknown"

        old_condition = self._current_condition
        self._current_condition = cond_str

        body = getattr(stmt, "body", [])
        if isinstance(body, list):
            self._walk_body(body)
        else:
            self._walk_statement(body)

        # orelse
        orelse = getattr(stmt, "orelse", None)
        if orelse:
            self._current_condition = f"not ({cond_str})"
            if isinstance(orelse, list):
                self._walk_body(orelse)
            else:
                self._walk_statement(orelse)

        self._current_condition = old_condition

    # ───────────────────────────────────────
    # EXTRACTORS
    # ───────────────────────────────────────

    def _extract_strategy_decl(self, call_node: Any) -> None:
        """Extract strategy() declaration metadata."""
        pos_args, kw_args = self._split_args(call_node)

        if pos_args:
            val = self._get_value(pos_args[0])
            if isinstance(val, str):
                self.spec.name = val

        for key, arg_node in kw_args.items():
            val = self._get_value(arg_node)
            if key == "title" and isinstance(val, str):
                self.spec.name = val
            elif key == "overlay":
                self.spec.overlay = bool(val) if val is not None else True
            elif key == "default_qty_type":
                self.spec.default_qty_type = str(val)
            elif key == "default_qty_value":
                self.spec.default_qty_value = float(val) if val else 100.0
            elif key == "currency":
                self.spec.currency = str(val)

    def _extract_input(self, var_name: str, func_name: str, call_node: Any) -> None:
        """Extract an input() / input.int() / etc. call."""
        pos_args, kw_args = self._split_args(call_node)

        type_map = {
            "input": InputType.INT,
            "input.int": InputType.INT,
            "input.float": InputType.FLOAT,
            "input.bool": InputType.BOOL,
            "input.string": InputType.STRING,
            "input.source": InputType.SOURCE,
        }
        input_type = type_map.get(func_name, InputType.INT)

        # Default value: first positional arg or kwarg 'defval'
        default = None
        if "defval" in kw_args:
            default = self._get_value(kw_args["defval"])
        elif pos_args:
            default = self._get_value(pos_args[0])

        # Title: kwarg 'title' or second positional arg
        title = var_name
        if "title" in kw_args:
            t = self._get_value(kw_args["title"])
            if isinstance(t, str):
                title = t
        elif len(pos_args) > 1:
            t = self._get_value(pos_args[1])
            if isinstance(t, str):
                title = t

        # For generic input(), infer type from default
        if func_name == "input" and default is not None:
            if isinstance(default, bool):
                input_type = InputType.BOOL
            elif isinstance(default, float):
                input_type = InputType.FLOAT
            elif isinstance(default, int):
                input_type = InputType.INT

        self.spec.inputs.append(InputParam(
            name=var_name,
            title=title,
            input_type=input_type,
            default_value=default,
        ))

    def _extract_indicator(
        self, result_var: str, func_name: str, call_node: Any, result_vars: list[str] | None = None
    ) -> None:
        """Extract a ta.* indicator call."""
        pos_args, kw_args = self._split_args(call_node)

        args_str = [self._node_to_string(a) for a in pos_args]
        kwargs_str = {k: self._node_to_string(v) for k, v in kw_args.items()}

        # For tuple assignments, result_var is the first variable
        primary = result_vars[0] if result_vars else result_var

        self.spec.indicators.append(IndicatorCall(
            pine_func=func_name,
            args=args_str,
            kwargs=kwargs_str,
            result_var=primary,
            result_vars=result_vars or [],
        ))

    def _extract_strategy_call(self, func_name: str, call_node: Any) -> None:
        """Extract a strategy.entry/close/exit/cancel_all call."""
        action_map = {
            "strategy.entry": StrategyAction.ENTRY,
            "strategy.close": StrategyAction.CLOSE,
            "strategy.exit": StrategyAction.EXIT,
            "strategy.cancel_all": StrategyAction.CANCEL_ALL,
        }
        action = action_map.get(func_name)
        if action is None:
            logger.warning(f"Unknown strategy function: {func_name}")
            return

        pos_args, kw_args = self._split_args(call_node)

        call = StrategyCall(
            action=action,
            condition=self._current_condition or "True",
        )

        # First positional arg is trade ID
        if pos_args:
            val = self._get_value(pos_args[0])
            if isinstance(val, str):
                call.trade_id = val
            else:
                call.trade_id = self._node_to_string(pos_args[0])

        # Second positional arg or 'direction' kwarg
        dir_node = None
        if len(pos_args) > 1:
            dir_node = pos_args[1]
        elif "direction" in kw_args:
            dir_node = kw_args["direction"]

        if dir_node:
            dir_str = self._node_to_string(dir_node)
            if "long" in dir_str.lower():
                call.direction = Direction.LONG
            elif "short" in dir_str.lower():
                call.direction = Direction.SHORT
            elif "all" in dir_str.lower():
                call.direction = Direction.ALL
        elif action in (StrategyAction.CLOSE, StrategyAction.EXIT, StrategyAction.CANCEL_ALL):
            call.direction = Direction.ALL

        # Stop/limit/qty
        if "stop" in kw_args:
            call.stop = self._node_to_string(kw_args["stop"])
        if "limit" in kw_args:
            call.limit = self._node_to_string(kw_args["limit"])
        if "qty" in kw_args:
            call.qty = self._node_to_string(kw_args["qty"])

        self.spec.strategy_calls.append(call)

    # ───────────────────────────────────────
    # AST NAVIGATION HELPERS
    # ───────────────────────────────────────

    def _get_func_name(self, call_node: Any) -> str | None:
        """Get the fully qualified function name from a Call node."""
        func = getattr(call_node, "func", None)
        if func is None:
            return None
        return self._node_to_string(func)

    def _get_id(self, node: Any) -> str | None:
        """Get the 'id' from a Name node."""
        node_type = type(node).__name__
        if node_type == "Name":
            return getattr(node, "id", None)
        # Tuple unpacking — return comma separated list of names
        if node_type == "Tuple":
            elts = getattr(node, "elts", [])
            parts = []
            for e in elts:
                val = self._get_id(e)
                if val:
                    parts.append(val)
            if parts:
                return ", ".join(parts)
        return None

    def _get_value(self, node: Any) -> Any:
        """Extract a Python value from an AST node (Constant, Name, etc.)."""
        node_type = type(node).__name__

        if node_type == "Constant":
            return getattr(node, "value", None)
        if node_type == "Name":
            return getattr(node, "id", None)
        if node_type == "UnaryOp":
            op = getattr(node, "op", None)
            operand = getattr(node, "operand", None)
            if type(op).__name__ == "USub" and operand:
                val = self._get_value(operand)
                if isinstance(val, (int, float)):
                    return -val
        return self._node_to_string(node)

    def _split_args(self, call_node: Any) -> tuple[list[Any], dict[str, Any]]:
        """
        Split Call.args into positional and keyword arguments.

        pynescript Arg nodes: Arg(value=..., name=None|str)
        - name=None → positional
        - name=str  → keyword
        """
        raw_args = getattr(call_node, "args", []) or []
        pos_args = []
        kw_args = {}

        for arg in raw_args:
            if type(arg).__name__ == "Arg":
                name = getattr(arg, "name", None)
                value = getattr(arg, "value", arg)
                if name is not None:
                    kw_args[name] = value
                else:
                    pos_args.append(value)
            else:
                pos_args.append(arg)

        return pos_args, kw_args

    def _node_to_string(self, node: Any) -> str:
        """Convert an AST node to its string representation."""
        if node is None:
            return ""
        if isinstance(node, str):
            return node
        if isinstance(node, (int, float, bool)):
            return str(node)

        node_type = type(node).__name__

        if node_type == "Name":
            return getattr(node, "id", "")

        if node_type == "Attribute":
            value = self._node_to_string(getattr(node, "value", None))
            attr = getattr(node, "attr", "")
            return f"{value}.{attr}" if value else str(attr)

        if node_type == "Constant":
            val = getattr(node, "value", None)
            if isinstance(val, str):
                return val  # return raw string, not repr
            return str(val) if val is not None else ""

        if node_type == "Call":
            func = self._get_func_name(node)
            pos_args, kw_args = self._split_args(node)
            parts = [self._node_to_string(a) for a in pos_args]
            parts += [f"{k}={self._node_to_string(v)}" for k, v in kw_args.items()]
            return f"{func}({', '.join(parts)})"

        if node_type == "BinOp":
            left = self._node_to_string(getattr(node, "left", None))
            right = self._node_to_string(getattr(node, "right", None))
            op = self._op_to_string(getattr(node, "op", None))
            return f"{left} {op} {right}"

        if node_type == "Compare":
            left = self._node_to_string(getattr(node, "left", None))
            ops = getattr(node, "ops", [])
            comparators = getattr(node, "comparators", [])
            if ops and comparators:
                op = self._op_to_string(ops[0])
                right = self._node_to_string(comparators[0])
                return f"{left} {op} {right}"
            return left

        if node_type == "BoolOp":
            op = self._op_to_string(getattr(node, "op", None))
            values = getattr(node, "values", [])
            parts = [self._node_to_string(v) for v in values]
            return f" {op} ".join(parts)

        if node_type == "UnaryOp":
            op = self._op_to_string(getattr(node, "op", None))
            operand = self._node_to_string(getattr(node, "operand", None))
            return f"{op}{operand}"

        if node_type == "IfExp":
            test = self._node_to_string(getattr(node, "test", None))
            body = self._node_to_string(getattr(node, "body", None))
            orelse = self._node_to_string(getattr(node, "orelse", None))
            return f"{body} if {test} else {orelse}"

        if node_type == "Subscript":
            value = self._node_to_string(getattr(node, "value", None))
            slc = self._node_to_string(getattr(node, "slice", None))
            return f"{value}[{slc}]"

        if node_type == "Tuple":
            elts = getattr(node, "elts", [])
            parts = [self._node_to_string(e) for e in elts]
            return f"({', '.join(parts)})"

        if node_type == "Arg":
            return self._node_to_string(getattr(node, "value", None))

        # Fallback
        for attr in ("id", "name", "value", "n", "s"):
            val = getattr(node, attr, None)
            if val is not None and isinstance(val, (str, int, float)):
                return str(val)

        return f"<{node_type}>"

    def _op_to_string(self, op: Any) -> str:
        """Convert an operator node to its string representation."""
        if op is None:
            return "?"
        op_map = {
            "Add": "+", "Sub": "-", "Mult": "*", "Div": "/",
            "Mod": "%", "Pow": "**",
            "Eq": "==", "NotEq": "!=",
            "Lt": "<", "LtE": "<=", "Gt": ">", "GtE": ">=",
            "And": "and", "Or": "or", "Not": "not ",
            "BitAnd": "&", "BitOr": "|", "BitXor": "^",
            "USub": "-", "UAdd": "+", "Invert": "~",
        }
        return op_map.get(type(op).__name__, str(type(op).__name__))

    def _looks_like_series(self, expr_str: str) -> bool:
        """Heuristic: does this expression look like it produces a series?"""
        indicators = ["ta.", "close", "open", "high", "low", "volume", "src"]
        return any(s in expr_str for s in indicators)


# ═══════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════


def _to_env_key(name: str) -> str:
    """
    Convert a Pine Script variable/title name to an ENV key.

    "Fast Length" → "FAST_LENGTH"
    "fastLength"  → "FAST_LENGTH"
    "rsi_period"  → "RSI_PERIOD"
    """
    # camelCase → camel_Case
    key = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    # Replace spaces and special chars with underscores
    key = re.sub(r"[^a-zA-Z0-9_]", "_", key)
    # Collapse multiple underscores
    key = re.sub(r"_+", "_", key)
    return key.upper().strip("_")


def analyze(tree: pine_ast.Script, source_file: str = "") -> StrategySpec:
    """
    Convenience function: analyze a pynescript AST into a StrategySpec.
    """
    return Analyzer().analyze(tree, source_file=source_file)
