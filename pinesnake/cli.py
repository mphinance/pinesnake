"""
PineSnake CLI — Convert TradingView Pine Script strategies to Python trading bots.

Commands:
    pinesnake convert  — Convert a Pine Script to a Python algo
    pinesnake validate — Parse-only, show what was detected
    pinesnake supported — List all supported Pine Script functions
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from pinesnake import __version__

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="pinesnake")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose: bool):
    """🐍 PineSnake — Pine Script → Python Algo Trading Converter"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


@cli.command()
@click.argument("pine_file", type=click.Path(exists=True, path_type=Path))
@click.option("--tradier", is_flag=True, required=True, help="Target Tradier API")
@click.option("--timeframe", "-t", default="5min",
              type=click.Choice(["1min", "5min", "15min", "1h", "4h", "1d"]),
              help="Bar interval (default: 5min)")
@click.option("--symbol", "-s", default="SPY", help="Default symbol (default: SPY)")
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None,
              help="Output file path (default: stdout)")
@click.option("--env/--no-env", default=True, help="Also generate .env config file")
def convert(pine_file: Path, tradier: bool, timeframe: str, symbol: str,
            output: Path | None, env: bool):
    """
    Convert a Pine Script strategy to a standalone Python trading bot.

    \b
    Example:
        pinesnake convert my_strategy.pine --tradier --timeframe 5min -o my_algo.py
    """
    from pinesnake.analyzer import analyze
    from pinesnake.codegen.generator import CodeGenerator
    from pinesnake.parser import parse_pine

    click.echo(f"🐍 PineSnake v{__version__}", err=True)
    click.echo(f"📄 Parsing: {pine_file.name}", err=True)

    # Step 1: Parse
    try:
        tree = parse_pine(pine_file)
    except Exception as e:
        click.echo(f"❌ Parse error: {e}", err=True)
        raise SystemExit(1)

    click.echo("✅ Parse successful", err=True)

    # Step 2: Analyze
    try:
        spec = analyze(tree, source_file=str(pine_file))
    except Exception as e:
        click.echo(f"❌ Analysis error: {e}", err=True)
        raise SystemExit(1)

    click.echo(f"✅ Analyzed: {spec.name}", err=True)
    click.echo(f"   {len(spec.inputs)} inputs, {len(spec.indicators)} indicators, "
               f"{len(spec.strategy_calls)} strategy calls", err=True)

    # Step 3: Generate
    gen = CodeGenerator(timeframe=timeframe, symbol=symbol)

    try:
        code = gen.generate(spec)
    except Exception as e:
        click.echo(f"❌ Code generation error: {e}", err=True)
        raise SystemExit(1)

    # Output
    if output:
        output.write_text(code, encoding="utf-8")
        click.echo(f"✅ Written to: {output}", err=True)

        # Generate .env alongside
        if env:
            env_path = output.with_suffix(".env")
            env_content = gen.generate_env(spec)
            env_path.write_text(env_content, encoding="utf-8")
            click.echo(f"✅ Config: {env_path}", err=True)

            # Security: ensure .gitignore includes .env
            _ensure_gitignore(output.parent)
    else:
        click.echo(code)

    click.echo(f"\n🎯 Strategy '{spec.name}' converted successfully!", err=True)
    if output:
        click.echo(f"   Run with: python {output}", err=True)
        click.echo(f"   Config:   Edit {output.with_suffix('.env')}", err=True)


@cli.command()
@click.argument("pine_file", type=click.Path(exists=True, path_type=Path))
def validate(pine_file: Path):
    """
    Parse a Pine Script and show what was detected (no code generation).

    \b
    Example:
        pinesnake validate my_strategy.pine
    """
    from pinesnake.analyzer import analyze
    from pinesnake.parser import dump_ast, parse_pine

    click.echo(f"🐍 PineSnake v{__version__} — Validate Mode")
    click.echo(f"📄 Parsing: {pine_file.name}")

    # Parse
    try:
        tree = parse_pine(pine_file)
    except Exception as e:
        click.echo(f"❌ Parse error: {e}")
        raise SystemExit(1)

    click.echo("✅ Parse successful\n")

    # Analyze
    try:
        spec = analyze(tree, source_file=str(pine_file))
    except Exception as e:
        click.echo(f"❌ Analysis error: {e}")
        raise SystemExit(1)

    # Display results
    click.echo("═" * 50)
    click.echo(f"Strategy: {spec.name}")
    click.echo("═" * 50)

    if spec.inputs:
        click.echo(f"\n📋 Inputs ({len(spec.inputs)}):")
        for inp in spec.inputs:
            click.echo(f"  • {inp.name} ({inp.input_type.value}) = {inp.default_value}"
                       f"  →  {inp.env_key}")

    if spec.indicators:
        click.echo(f"\n📊 Indicators ({len(spec.indicators)}):")
        for ind in spec.indicators:
            click.echo(f"  • {ind.result_var} = {ind.pine_func}({', '.join(ind.args)})")

    if spec.assignments:
        click.echo(f"\n📝 Assignments ({len(spec.assignments)}):")
        for assign in spec.assignments:
            click.echo(f"  • {assign.name} = {assign.expression[:60]}")

    if spec.strategy_calls:
        click.echo(f"\n🎯 Strategy Calls ({len(spec.strategy_calls)}):")
        for sc in spec.strategy_calls:
            click.echo(f"  • {sc.action.value}('{sc.trade_id}', {sc.direction.value})")
            if sc.condition:
                click.echo(f"    condition: {sc.condition[:60]}")

    click.echo(f"\n{'═' * 50}")
    click.echo("✅ Validation complete — ready for conversion")


@cli.command()
def supported():
    """
    List all supported Pine Script functions and their Python equivalents.

    \b
    Example:
        pinesnake supported
    """
    from pinesnake.codegen.indicators import INDICATOR_MAP

    click.echo(f"🐍 PineSnake v{__version__} — Supported Functions")
    click.echo("═" * 60)

    categories = {
        "Moving Averages": ["ta.sma", "ta.ema", "ta.wma", "ta.hma", "ta.vwma"],
        "Oscillators": ["ta.rsi", "ta.macd", "ta.stoch", "ta.cci", "ta.mfi", "ta.adx"],
        "Volatility": ["ta.atr", "ta.bb", "ta.bbands"],
        "Volume": ["ta.obv"],
        "Cross Detection": ["ta.crossover", "ta.crossunder"],
        "Rolling": ["ta.highest", "ta.lowest"],
        "Transforms": ["ta.change", "ta.cum"],
        "Utilities": ["na", "nz"],
    }

    for category, funcs in categories.items():
        click.echo(f"\n{category}:")
        for func_name in funcs:
            mapping = INDICATOR_MAP.get(func_name)
            if mapping:
                ohlc = " [needs OHLC]" if mapping.needs_ohlc else ""
                click.echo(f"  ✅ {func_name:<20} — {mapping.notes}{ohlc}")
            else:
                click.echo(f"  ❌ {func_name:<20} — not mapped")

    click.echo(f"\n{'═' * 60}")
    click.echo(f"Total: {len(INDICATOR_MAP)} supported functions")


def _ensure_gitignore(directory: Path) -> None:
    """Ensure .gitignore in directory excludes .env files and log files."""
    gitignore = directory / ".gitignore"
    env_patterns = {"*.env", "*.log", ".env"}

    existing_lines = set()
    if gitignore.exists():
        existing_lines = set(gitignore.read_text().splitlines())

    to_add = env_patterns - existing_lines
    if to_add:
        with open(gitignore, "a") as f:
            if existing_lines:
                f.write("\n")
            f.write("# PineSnake — protect credentials and logs\n")
            for pattern in sorted(to_add):
                f.write(f"{pattern}\n")


if __name__ == "__main__":
    cli()
