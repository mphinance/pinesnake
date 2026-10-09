"""Generate a bot from each example, import it, and run its real indicator and
signal code on synthetic bars. Guards the whole pipeline, not just string output."""

import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pinesnake.analyzer import analyze
from pinesnake.codegen.generator import CodeGenerator
from pinesnake.parser import parse_pine

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.pine"))


def _bars(n=400):
    rng = np.random.default_rng(3)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    return pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c,
                         "volume": rng.integers(1000, 5000, n).astype(float)})


@pytest.mark.parametrize("pine", EXAMPLES, ids=lambda p: p.stem)
def test_generated_bot_runs_and_trades(pine, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # generated bots open a log file in the cwd
    for k in ("TRADIER_API_KEY", "TRADIER_ACCOUNT_ID"):
        monkeypatch.setenv(k, "test")
    monkeypatch.setenv("DRY_RUN", "true")

    spec = analyze(parse_pine(pine), source_file=str(pine))
    out = tmp_path / f"{pine.stem}.py"
    out.write_text(CodeGenerator(symbol="SPY", timeframe="5min").generate(spec))

    mod_spec = importlib.util.spec_from_file_location(pine.stem, out)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)

    df = mod.calculate_indicators(_bars())
    signals = {mod.check_signals(df.iloc[:i]) for i in range(60, len(df))}
    assert signals & {"BUY", "SELL"}, "strategy never fired on 400 random-walk bars"


def test_strategy_name_with_path_chars_does_not_break_the_bot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "s.pine"
    src.write_text(Path(EXAMPLES[0]).read_text().replace(
        'strategy("', 'strategy("A/B \\"quoted\\" {x} ', 1))
    spec = analyze(parse_pine(src), source_file=str(src))
    code = CodeGenerator(symbol="SPY", timeframe="5min").generate(spec)
    compile(code, "bot.py", "exec")
    assert 'FileHandler("a_b_quoted_x' in code
