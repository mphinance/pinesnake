"""
PineSnake Web UI -- Streamlit interface for Pine Script -> Python conversion.

Launch:
    streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure the package is importable when running from the repo root
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from pinesnake import __version__
from pinesnake.codegen.indicators import INDICATOR_MAP

# ════════════════════════════════════════════════════════════════
# EXAMPLES
# ════════════════════════════════════════════════════════════════

EXAMPLES_DIR = Path(__file__).parent / "examples"

EXAMPLES: dict[str, str] = {}
for p in sorted(EXAMPLES_DIR.glob("*.pine")):
    EXAMPLES[p.stem.replace("_", " ").title()] = p.read_text(encoding="utf-8")


# ════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="PineSnake",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ════════════════════════════════════════════════════════════════
# CUSTOM CSS
# ════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Header gradient */
    .pinesnake-header {
        background: linear-gradient(135deg, #0e1117 0%, #1a2332 50%, #0e1117 100%);
        border: 1px solid rgba(0, 212, 170, 0.2);
        border-radius: 12px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .pinesnake-header::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00d4aa, transparent);
    }
    .pinesnake-header h1 {
        margin: 0 0 0.3rem 0;
        font-size: 2rem;
        color: #ffffff;
        letter-spacing: -0.5px;
    }
    .pinesnake-header p {
        margin: 0;
        color: #8899aa;
        font-size: 1rem;
    }

    /* Metric cards */
    .metric-row {
        display: flex;
        gap: 1rem;
        margin: 1rem 0;
    }
    .metric-card {
        flex: 1;
        background: linear-gradient(135deg, #1a1f2e, #141820);
        border: 1px solid rgba(0, 212, 170, 0.15);
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #00d4aa;
        line-height: 1;
    }
    .metric-card .label {
        font-size: 0.8rem;
        color: #8899aa;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.4rem;
    }

    /* Pipeline step badges */
    .pipeline-step {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(0, 212, 170, 0.08);
        border: 1px solid rgba(0, 212, 170, 0.2);
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.9rem;
        color: #e0e0e0;
    }
    .pipeline-step.success {
        border-color: rgba(0, 212, 170, 0.5);
        background: rgba(0, 212, 170, 0.1);
    }
    .pipeline-step.error {
        border-color: rgba(255, 75, 75, 0.5);
        background: rgba(255, 75, 75, 0.1);
    }

    /* Analysis detail tables */
    .detail-table {
        width: 100%;
        border-collapse: collapse;
        margin: 0.5rem 0;
    }
    .detail-table th {
        text-align: left;
        padding: 0.5rem 0.8rem;
        color: #00d4aa;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 1px solid rgba(0, 212, 170, 0.2);
    }
    .detail-table td {
        padding: 0.5rem 0.8rem;
        color: #c8d0d8;
        font-size: 0.85rem;
        border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .detail-table tr:hover td {
        background: rgba(0, 212, 170, 0.04);
    }
    .detail-table code {
        background: rgba(0,0,0,0.3);
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-size: 0.8rem;
        color: #7dd3c0;
    }

    /* Download buttons area */
    .download-area {
        background: linear-gradient(135deg, #1a1f2e, #141820);
        border: 1px solid rgba(0, 212, 170, 0.15);
        border-radius: 10px;
        padding: 1.5rem;
        margin-top: 1rem;
    }

    /* Hide default streamlit footer */
    footer { visibility: hidden; }

    /* Sidebar polish */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1117 0%, #141820 100%);
    }

    /* Make text_area code-like */
    .stTextArea textarea {
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace !important;
        font-size: 0.85rem !important;
        line-height: 1.5 !important;
    }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🐍 PineSnake")
    st.caption(f"v{__version__}")

    st.divider()

    st.markdown("### Configuration")

    timeframe = st.selectbox(
        "Timeframe",
        options=["1min", "5min", "15min", "1h", "4h", "1d"],
        index=1,
        help="Bar interval for the generated trading bot",
    )

    symbol = st.text_input(
        "Default Symbol",
        value="SPY",
        help="Ticker symbol the bot will trade by default",
    )

    st.divider()

    st.markdown("### Target Broker")
    st.radio(
        "Broker API",
        options=["Tradier"],
        index=0,
        disabled=True,
        help="More brokers coming soon",
    )

    st.divider()

    # Supported functions reference
    with st.expander("Supported Pine Functions", expanded=False):
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
        for cat, funcs in categories.items():
            st.markdown(f"**{cat}**")
            for fn in funcs:
                mapping = INDICATOR_MAP.get(fn)
                if mapping:
                    st.markdown(f"- `{fn}` {mapping.notes}")

    st.divider()
    st.caption("Built with Streamlit")


# ════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════

st.markdown("""
<div class="pinesnake-header">
    <h1>🐍 PineSnake</h1>
    <p>Convert TradingView Pine Script strategies into standalone Python trading bots</p>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# STAGE 1: INPUT
# ════════════════════════════════════════════════════════════════

col_input, col_config = st.columns([3, 1])

with col_config:
    st.markdown("#### Load Example")
    example_choice = st.selectbox(
        "Example strategy",
        options=["-- Paste your own --"] + list(EXAMPLES.keys()),
        label_visibility="collapsed",
    )

    uploaded = st.file_uploader(
        "Or upload a .pine file",
        type=["pine", "txt"],
        help="Upload a Pine Script v5 file",
    )

with col_input:
    # Determine the initial code to show
    if uploaded is not None:
        initial_code = uploaded.getvalue().decode("utf-8")
    elif example_choice != "-- Paste your own --":
        initial_code = EXAMPLES.get(example_choice, "")
    else:
        # Default to RSI example on first load
        initial_code = list(EXAMPLES.values())[0] if EXAMPLES else ""

    pine_source = st.text_area(
        "Pine Script Source",
        value=initial_code,
        height=320,
        placeholder="// Paste your Pine Script v5 strategy here...",
        label_visibility="collapsed",
    )

st.divider()


# ════════════════════════════════════════════════════════════════
# TRANSPILE BUTTON
# ════════════════════════════════════════════════════════════════

transpile_clicked = st.button(
    "🔄 Transpile to Python",
    type="primary",
    use_container_width=True,
)


# ════════════════════════════════════════════════════════════════
# STAGE 2 + 3: ANALYSIS & OUTPUT
# ════════════════════════════════════════════════════════════════

if transpile_clicked and pine_source.strip():
    from pinesnake.analyzer import analyze
    from pinesnake.codegen.generator import CodeGenerator
    from pinesnake.parser import parse_pine_string, ParseError

    spec = None
    code = None
    env_content = None

    # ── Pipeline ──────────────────────────────────────────────
    with st.status("Transpiling...", expanded=True) as pipeline:

        # Step 1: Parse
        st.write("**Step 1/3** -- Parsing Pine Script...")
        try:
            tree = parse_pine_string(pine_source, source_file="web_input.pine")
            st.write("✅ Parse successful")
        except ParseError as e:
            st.error(f"Parse failed: {e}")
            pipeline.update(label="Transpile failed", state="error")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected parse error: {e}")
            pipeline.update(label="Transpile failed", state="error")
            st.stop()

        # Step 2: Analyze
        st.write("**Step 2/3** -- Analyzing strategy...")
        try:
            spec = analyze(tree, source_file="web_input.pine")
            st.write(f'✅ Strategy: "{spec.name}"')
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            pipeline.update(label="Transpile failed", state="error")
            st.stop()

        # Step 3: Generate
        st.write("**Step 3/3** -- Generating Python bot...")
        try:
            gen = CodeGenerator(timeframe=timeframe, symbol=symbol)
            code = gen.generate(spec)
            env_content = gen.generate_env(spec)
            st.write(f"✅ Generated {len(code):,} characters")
        except ValueError as e:
            st.error(f"Code generation failed: {e}")
            pipeline.update(label="Transpile failed", state="error")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected generation error: {e}")
            pipeline.update(label="Transpile failed", state="error")
            st.stop()

        pipeline.update(label="Transpile complete!", state="complete")

    st.divider()

    # ── Analysis Dashboard ────────────────────────────────────
    if spec is not None:
        st.markdown("### Analysis Results")

        # Metric cards
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="value">{len(spec.inputs)}</div>
                <div class="label">Inputs</div>
            </div>
            <div class="metric-card">
                <div class="value">{len(spec.indicators)}</div>
                <div class="label">Indicators</div>
            </div>
            <div class="metric-card">
                <div class="value">{len(spec.strategy_calls)}</div>
                <div class="label">Signals</div>
            </div>
            <div class="metric-card">
                <div class="value">{len(spec.assignments)}</div>
                <div class="label">Variables</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Detail expanders
        detail_col1, detail_col2 = st.columns(2)

        with detail_col1:
            with st.expander("📋 Detected Inputs", expanded=True):
                if spec.inputs:
                    rows = ""
                    for inp in spec.inputs:
                        rows += f"""<tr>
                            <td><code>{inp.name}</code></td>
                            <td>{inp.input_type.value}</td>
                            <td><code>{inp.default_value}</code></td>
                            <td><code>{inp.env_key}</code></td>
                        </tr>"""
                    st.markdown(f"""
                    <table class="detail-table">
                        <tr><th>Name</th><th>Type</th><th>Default</th><th>.env Key</th></tr>
                        {rows}
                    </table>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No inputs detected")

            with st.expander("📊 Detected Indicators", expanded=True):
                if spec.indicators:
                    rows = ""
                    for ind in spec.indicators:
                        args_str = ", ".join(ind.args[:3])
                        if len(ind.args) > 3:
                            args_str += ", ..."
                        rows += f"""<tr>
                            <td><code>{ind.result_var}</code></td>
                            <td><code>{ind.pine_func}</code></td>
                            <td><code>{args_str}</code></td>
                        </tr>"""
                    st.markdown(f"""
                    <table class="detail-table">
                        <tr><th>Variable</th><th>Function</th><th>Arguments</th></tr>
                        {rows}
                    </table>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No indicators detected")

        with detail_col2:
            with st.expander("🎯 Strategy Signals", expanded=True):
                if spec.strategy_calls:
                    rows = ""
                    for sc in spec.strategy_calls:
                        cond_preview = (sc.condition[:50] + "...") if len(sc.condition) > 50 else (sc.condition or "always")
                        direction_badge = "🟢 LONG" if sc.direction.value == "long" else "🔴 SHORT"
                        rows += f"""<tr>
                            <td><code>{sc.trade_id}</code></td>
                            <td>{sc.action.value.upper()}</td>
                            <td>{direction_badge}</td>
                            <td><code>{cond_preview}</code></td>
                        </tr>"""
                    st.markdown(f"""
                    <table class="detail-table">
                        <tr><th>Trade ID</th><th>Action</th><th>Direction</th><th>Condition</th></tr>
                        {rows}
                    </table>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No strategy calls detected")

            with st.expander("📝 Variable Assignments", expanded=False):
                if spec.assignments:
                    rows = ""
                    for a in spec.assignments:
                        expr_preview = (a.expression[:60] + "...") if len(a.expression) > 60 else a.expression
                        rows += f"""<tr>
                            <td><code>{a.name}</code></td>
                            <td><code>{expr_preview}</code></td>
                        </tr>"""
                    st.markdown(f"""
                    <table class="detail-table">
                        <tr><th>Variable</th><th>Expression</th></tr>
                        {rows}
                    </table>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No assignments detected")

        st.divider()

    # ── Generated Output ──────────────────────────────────────
    if code is not None:
        st.markdown("### Generated Output")

        tab_py, tab_env = st.tabs(["🐍 Python Bot", "⚙️ .env Config"])

        with tab_py:
            st.code(code, language="python", line_numbers=True)

        with tab_env:
            st.code(env_content, language="bash", line_numbers=True)

        # Download buttons
        safe_name = spec.name.replace(" ", "_").lower() if spec else "strategy"

        dl_col1, dl_col2, dl_col3 = st.columns([1, 1, 2])

        with dl_col1:
            st.download_button(
                label="⬇️ Download Python Bot",
                data=code,
                file_name=f"{safe_name}_algo.py",
                mime="text/x-python",
                type="primary",
                use_container_width=True,
            )

        with dl_col2:
            st.download_button(
                label="⬇️ Download .env Config",
                data=env_content,
                file_name=f"{safe_name}.env",
                mime="text/plain",
                use_container_width=True,
            )

        with dl_col3:
            st.markdown(f"""
            <div style="padding: 0.5rem 0; color: #8899aa; font-size: 0.85rem;">
                <strong>Next steps:</strong> Place both files in the same directory, fill in your
                <code>TRADIER_API_KEY</code> and <code>TRADIER_ACCOUNT_ID</code> in the .env file,
                then run <code>python {safe_name}_algo.py</code>
            </div>
            """, unsafe_allow_html=True)

elif transpile_clicked:
    st.warning("Please paste or upload a Pine Script strategy first.")
