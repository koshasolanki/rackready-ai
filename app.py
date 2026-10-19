"""
RackReady AI - data center cost and design model for high-density AI racks.
Built for Nebius x NVIDIA Build Week.

Run:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile

import streamlit as st

# Force-reload local modules so a hot redeploy never mixes old and new code.
import importlib as _il
import platforms as _pl, design as _ds, buildcx as _cx, engine as _engine, report as _rep, llm as _llm, ui_common as _uic, ui_views as _uiv
for _m in (_pl, _ds, _cx, _engine, _rep, _llm, _uic, _uiv):
    _il.reload(_m)

import buildcx as CX
import engine as E
import platforms as PL
import report as R
import ui_views as V
from design import COOLING_TYPES, D2C, D2C_AUTO_KW, HYBRID
from llm import (DEFAULT_BASE_URL, DEFAULT_MODEL, SUGGESTED_MODELS, LLMError,
                 fallback_narrative, resolve_api_key, stream_narrative)
from ui_common import esc_md

st.set_page_config(page_title="RackReady AI", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1400px;}
div[data-testid="stMetric"] {background: #161B22; border: 1px solid #262C36; border-radius: 10px; padding: 10px 14px;}
div[data-testid="stMetricValue"] {font-size: 1.45rem;}
.rr-sub {color: #9AA4B2; margin-top: -0.6rem; font-size: 1.0rem;}
.rr-badge {display:inline-block; background:#1f2a12; color:#76B900; border:1px solid #3d5a14;
  border-radius: 999px; padding: 2px 10px; font-size: 0.8rem; margin: 0 6px 4px 0;}
@media (max-width: 640px) {
  div[data-testid="stMetricValue"] {font-size: 1.15rem;}
  .block-container {padding-left: 0.6rem; padding-right: 0.6rem;}
}
</style>
""", unsafe_allow_html=True)


def esc_stream(gen):
    for chunk in gen:
        yield esc_md(chunk)


def get_secrets():
    try:
        _ = st.secrets.get("NEBIUS_API_KEY")
        return st.secrets
    except Exception:
        return None



# ----------------------------------------------------------------- presets -> widget state
D = E.DEFAULT_INPUTS
PLATFORMS = list(PL.PLATFORMS) + [PL.CUSTOM]


def _load_preset(name: str):
    i = E.merged(E.PRESETS[name])
    ss = st.session_state
    ss["w_type"] = i["project_type"]
    ss["w_name"] = i["project_name"]
    ss["w_size_by"] = i["size_by"]
    ss["w_mw"] = float(i["it_mw"])
    ss["w_racks"] = int(i["racks"])
    ss["w_platform"] = i["platform"]
    ss["w_region"] = i["region"]
    ss["w_res"] = i["resilience"]
    ss["w_horizon"] = i["horizon"]
    ss["w_cool"] = i["cooling"] or HYBRID
    ss["w_cur_kw"] = float(i["current_kw"])
    ss["w_cur_cool"] = i["current_cooling"]
    ss["w_mtp"] = int(i["months_to_power"])
    ss["w_dm"] = int(i["design_months"])
    ss["w_cm"] = int(i["construction_months"] or 0)


def _on_preset():
    name = st.session_state.get("w_preset")
    if name in E.PRESETS:
        _load_preset(name)


if "w_type" not in st.session_state:
    st.session_state["w_preset"] = E.DEFAULT_PRESET
    _load_preset(E.DEFAULT_PRESET)


def cooling_widget(container, label, kw, key, help_):
    """Cooling selector: locked to D2C above 45 kW/rack, user choice at or below."""
    if kw > D2C_AUTO_KW:
        container.selectbox(label, [D2C], index=0, disabled=True, key=key + "_locked",
                            help=f"{E.D2C_NOTE}: air and rear-door cooling cannot remove this much heat.")
        container.caption(f"🔒 {E.D2C_NOTE}")
        return D2C
    if st.session_state.get(key) not in COOLING_TYPES:
        st.session_state[key] = HYBRID
    return container.selectbox(label, COOLING_TYPES, key=key, help=help_ + f" Above {D2C_AUTO_KW:.0f} kW/rack "
                               "the model switches to direct-to-chip liquid automatically.")


# ----------------------------------------------------------------- sidebar
inputs: dict = {}
with st.sidebar:
    st.markdown("### ⚡ RackReady AI")
    st.caption("Indicative planning estimate, not a bid. Results update as you type.")
    st.selectbox("Start from a preset", list(E.PRESETS), key="w_preset", on_change=_on_preset,
                 help="Loads a typical project. You can then change any input.")
    inputs["project_type"] = st.radio(
        "Project type", E.PROJECT_TYPES, key="w_type",
        format_func=lambda p: "🏗️ Greenfield: new build" if p == E.GREENFIELD else "🏢 Existing building fit-out",
        help="Greenfield = one new campus built from scratch. Fit-out = new racks in an existing building, "
             "compared with keeping today's racks.")
    gf = inputs["project_type"] == E.GREENFIELD
    inputs["size_by"] = st.radio("Size by", ["IT MW", "Racks"], key="w_size_by", horizontal=True,
                                 help="IT MW = critical IT load (GPU racks), not utility MW.")
    if inputs["size_by"] == "IT MW":
        inputs["it_mw"] = float(st.number_input("IT load (MW)", 0.5, 2000.0, step=5.0, key="w_mw",
                                                help="Critical IT load of the GPU racks in MW."))
    else:
        inputs["racks"] = int(st.number_input("Number of racks", 1, 50000, step=10, key="w_racks",
                                              help="GPU rack positions."))
    inputs["platform"] = st.selectbox(
        "GPU platform", PLATFORMS, key="w_platform",
        format_func=lambda n: n if n == PL.CUSTOM else f"{n} · {PL.PLATFORMS[n]['kw']:,.0f} kW/rack"
        + ("" if PL.PLATFORMS[n]["status"] == "shipping" else f" ({PL.PLATFORMS[n]['status']})"),
        help="Sets rack power, weight, GPUs per rack, liquid share and the facility cost basis. Roadmap "
             "platforms are labelled announced or estimated.")
    if inputs["platform"] == PL.CUSTOM:
        inputs["custom_kw"] = float(st.number_input("Custom density (kW/rack)", 5.0, 1500.0, 135.0, step=5.0,
                                                    key="w_custom_kw", help="Average operating power per rack."))
        kw_now = inputs["custom_kw"]
    else:
        kw_now = PL.PLATFORMS[inputs["platform"]]["kw"]
    inputs["region"] = st.selectbox("Location", E.REGION_NAMES, key="w_region",
                                    help="Sets the construction cost factor, land price and power price defaults.")
    inputs["resilience"] = st.selectbox("Redundancy (tier)", list(E.RESILIENCE), key="w_res",
                                        format_func=lambda k: E.RESILIENCE[k],
                                        help="Generators, UPS and power paths. " + CX.GLOSSARY["N, N+1, 2N"] +
                                             " Tier wording is indicative, not a certification.")
    inputs["horizon"] = st.selectbox("Future-proof horizon", list(E.HORIZONS), key="w_horizon",
                                     format_func=lambda h: h if h == "Today only" else
                                     f"{h} · {E.HORIZONS[h]:,.0f} kW/rack",
                                     help="Target rack density to be ready for. The model prices retrofit later, "
                                          "provisions now, or full future build on day one.")

    with st.expander("Advanced", expanded=False):
        inputs["project_name"] = st.text_input("Project name", key="w_name", help="Shown on reports.")
        st.markdown("**Cooling**")
        if gf:
            inputs["cooling"] = cooling_widget(st, "Cooling", kw_now, "w_cool",
                                               "At or below 45 kW/rack choose air or rear-door (hybrid).")
        else:
            inputs["cooling"] = cooling_widget(st, "Future-ready cooling", kw_now, "w_cool",
                                               "Cooling for the new racks.")
            st.markdown("**Existing hall today**")
            inputs["current_kw"] = float(st.number_input("Current kW/rack", 3.0, 60.0, step=1.0, key="w_cur_kw",
                                                         help="Average power of today's racks."))
            inputs["current_cooling"] = cooling_widget(st, "Current cooling", inputs["current_kw"], "w_cur_cool",
                                                       "Today's cooling system.")
            c1, c2 = st.columns(2)
            inputs["current_gpus"] = int(c1.number_input("Current GPUs/rack", 0, 72, D["current_gpus"],
                                                         help="GPUs in each of today's racks."))
            inputs["current_gpu_price"] = float(c2.number_input("Current $/GPU-hr", 0.0, 20.0, D["current_gpu_price"],
                                                                step=0.25, help="Rental rate for today's GPUs."))
        st.markdown("**Revenue and operations**")
        gp = float(st.number_input("GPU rental $/GPU-hr (0 = platform default)", 0.0, 60.0, 0.0, step=0.25,
                                   help="Contract rate for the new GPUs. Defaults sit inside public market ranges."))
        inputs["gpu_price"] = gp or None
        inputs["utilization"] = st.slider("Utilization", 0.3, 1.0, D["utilization"], 0.05,
                                          help="Share of hours the GPUs are sold.")
        pc = float(st.number_input("Power price $/kWh (0 = location default)", 0.0, 0.5, 0.0, step=0.005,
                                   format="%.3f", help="All-in electricity price."))
        inputs["power_cost"] = pc or None
        inputs["price_change"] = st.slider("GPU rental price change per year", -0.25, 0.05, D["price_change"], 0.01,
                                           help="Rental prices usually fall as newer GPUs ship (assumption).")
        inputs["years"] = int(st.slider("Analysis period (years)", 3, 20, D["years"],
                                        help="Years of operation in NPV and payback."))
        inputs["include_it"] = st.checkbox("Include GPU / IT hardware in ROI", True,
                                           help="Adds GPU racks and the AI network to the investment.")
        inputs["overhead_pct"] = st.slider("Cloud operations overhead (% of revenue)", 0.0, 0.4, D["overhead_pct"], 0.01,
                                           help="Software, sales, network transit and support (assumption).")
        st.markdown("**Cost and schedule**")
        if gf:
            inputs["contingency"] = st.slider("Contingency", 0.0, 0.25, D["contingency"], 0.01,
                                              help="Design and pricing contingency at planning stage.")
            inputs["owner_pct"] = st.slider("Owner costs", 0.0, 0.10, D["owner_pct"], 0.005,
                                            help="Permits, owner's team, builder's risk insurance.")
            land = float(st.number_input("Land $/acre (0 = location default)", 0.0, 50e6, 0.0, step=50_000.0,
                                         help="Powered-land price. Indicative defaults by location."))
            inputs["land_per_acre"] = land or None
            inputs["months_to_power"] = int(st.number_input("Months to utility power", 6, 120, key="w_mtp",
                                                            help="Utility's committed energization date."))
            c1, c2 = st.columns(2)
            inputs["design_months"] = int(c1.number_input("Design months", 2, 36, key="w_dm",
                                                          help="Design and permits."))
            cm = int(c2.number_input("Build months (0 = auto)", 0, 60, key="w_cm",
                                     help="Construction from notice to proceed to energization start. "
                                          "0 = scales with MW: 12 + 12 x sqrt(MW/100), 12-40 months."))
            inputs["construction_months"] = cm or None
        else:
            fb = int(st.number_input("Fit-out build months (0 = auto)", 0, 36, 0,
                                     help="0 = scales with MW: 8 + 6 x sqrt(MW/100), 8-24 months."))
            inputs["fitout_build_months"] = fb or None
        st.markdown("**Schedule factors**")
        inputs["project_start"] = st.date_input("Project start (go decision)", help="Month 0 for order-by dates.")
        c1, c2 = st.columns(2)
        inputs["overtime_hours"] = int(c1.selectbox("Work week (hours)", [40, 50, 60, 70], 0, key="w_ot",
                                                    help="Overtime shortens field work but loses productivity "
                                                         "(about 0.97 at 50 h, 0.88 at 60 h, 0.80 at 70 h). "
                                                         "Commissioning does not compress."))
        inputs["weather_factor"] = float(c2.slider("Weather allowance", 0.0, 0.30, 0.05, 0.01,
                                                   help="Extra time on exterior work (site, structure, dry-in)."))
        inputs["congestion_factor"] = float(st.slider("Congestion / stacking of trades", 0.0, 0.30, 0.0, 0.01,
                                                      help="Extra time on interior MEP, energization and "
                                                           "commissioning when trades share space."))
        inputs["escalation"] = st.slider("Escalation per year", 0.0, 0.12, D["escalation"], 0.005,
                                         help="Construction cost inflation to the mid-point of construction.")
        st.markdown("**Engineering**")
        c1, c2 = st.columns(2)
        inputs["fuel_hours"] = float(c1.number_input("Fuel storage (hours)", 4.0, 168.0, D["fuel_hours"], step=4.0,
                                                     help="On-site diesel at full load."))
        inputs["battery_min"] = float(c2.number_input("UPS battery (minutes)", 1.0, 30.0, D["battery_min"], step=1.0,
                                                      help="Ride-through until generators take the load."))
        c1, c2 = st.columns(2)
        inputs["voltage"] = float(c1.selectbox("Distribution voltage (V)", [415.0, 480.0], 0,
                                               help="Low-voltage three-phase distribution to the racks."))
        inputs["tcs_dT"] = float(c2.number_input("Liquid loop dT (K)", 5.0, 20.0, D["tcs_dT"], step=1.0,
                                                 help="Supply-to-return rise in the rack liquid loop."))
        st.markdown("**Future-proof horizon**")
        fk = float(st.number_input("Target kW/rack (0 = horizon default)", 0.0, 2000.0, 0.0, step=10.0,
                                   help="Override the horizon's target density."))
        inputs["future_kw"] = fk or None
        fy = int(st.number_input("Year the target racks arrive (0 = default)", 0, 20, 0,
                                 help="Years after ready-for-service. Defaults: 3, 5 or 8 years."))
        inputs["future_year"] = fy or None
        inputs["future_probability"] = st.slider("Probability the target is deployed", 0.1, 1.0, 0.7, 0.05,
                                                 help="Weights the later works (assumption).")
        inputs["spare_utility_pct"] = st.slider("Spare utility capacity", 0.0, 1.0, 0.0, 0.05,
                                                help="Extra MW to reserve for the future target.")

    with st.expander("🤖 AI narrative settings", expanded=False):
        use_ai = st.toggle("Use Nemotron narrative", value=True,
                           help="NVIDIA Nemotron on Nebius Token Factory writes the narrative; numbers come from the model.")
        base_url = st.text_input("Base URL", os.environ.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL),
                                 help="OpenAI-compatible endpoint.")
        model_choice = st.selectbox("Model", SUGGESTED_MODELS + ["Custom..."],
                                    0 if os.environ.get("NEBIUS_MODEL") is None else len(SUGGESTED_MODELS),
                                    help="Nemotron model id.")
        model = (st.text_input("Custom model id", os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL), help="Model id.")
                 if model_choice == "Custom..." else model_choice)
        secrets = get_secrets()
        env_or_secret = resolve_api_key(None, secrets)
        sidebar_key = ""
        if env_or_secret:
            st.success("API key loaded from environment / secrets.")
        else:
            sidebar_key = st.text_input("NEBIUS_API_KEY", type="password",
                                        help="Or set env NEBIUS_API_KEY / .streamlit/secrets.toml")
        api_key = resolve_api_key(sidebar_key, secrets)
        regen = st.button("↻ Regenerate narrative", width="stretch", help="Ask the model again.")

# ----------------------------------------------------------------- engine
try:
    res = E.run_model(inputs)
    payload = E.summary_for_llm(res)
except Exception as e:  # clear error, never a stack trace
    st.error(f"Could not compute this case: {type(e).__name__}: {e}. Check the inputs (size above zero, "
             "density within 5-1,500 kW/rack) or reload a preset.")
    st.stop()

h = R.headline(res)
st.markdown("# ⚡ RackReady AI")
st.markdown('<div class="rr-sub">Cost and design model for high-density AI data centers. '
            '<b>Built for Nebius x NVIDIA Build Week.</b></div>', unsafe_allow_html=True)
badges = [("🏗️ Greenfield new build" if gf else "🏢 Existing building fit-out"), h["platform"],
          f"{h['kw']:,.0f} kW/rack", f"{h['racks']:,} racks", f"{h['it_mw']:,.1f} MW IT", h["cooling"],
          inputs["region"], E.RESILIENCE[inputs["resilience"]].split(" (")[0],
          f"Horizon: {inputs['horizon']}"]
st.markdown("".join(f'<span class="rr-badge">{b}</span>' for b in badges), unsafe_allow_html=True)
st.caption(f"{E.DISCLAIMER} 2026 US dollars. {E.D2C_NOTE}.")
for w in res["warnings"]:
    st.warning(w)
V.summary(res)

# ----------------------------------------------------------------- narrative (cached per input)
key_fp = hashlib.sha1((api_key or "").encode()).hexdigest()[:8]
key_hash = hashlib.sha1(json.dumps([payload, use_ai, base_url, model, key_fp], sort_keys=True,
                                   default=str).encode()).hexdigest()
cache = st.session_state.setdefault("narratives", {})
if regen:
    cache.pop(key_hash, None)


def render_narrative():
    if key_hash in cache:
        src, text = cache[key_hash]
        st.caption(src)
        st.markdown(esc_md(text))
        return
    text, src = None, None
    if use_ai and api_key:
        try:
            with st.spinner(f"Asking {model} on Nebius Token Factory..."):
                gen = stream_narrative(payload, api_key, base_url, model)
            text = st.write_stream(esc_stream(gen))
            if isinstance(text, list):
                text = "".join(str(t) for t in text)
            if not text or not str(text).strip():
                raise LLMError("The model returned an empty response.")
            text = str(text).replace("\\$", "$")
            src = f"AI narrative · {model} via Nebius Token Factory"
            st.caption(src)
        except LLMError as e:
            st.warning(f"{e} Showing the built-in rule-based narrative instead.")
            text = None
        except Exception as e:  # never break the demo
            st.warning(f"AI narrative unavailable ({type(e).__name__}). Showing the built-in narrative instead.")
            text = None
    elif use_ai:
        st.info("No NEBIUS_API_KEY found, so this is the built-in rule-based narrative. "
                "Add a key under 🤖 AI narrative settings for the Nemotron narrative.")
    if text is None:
        text = fallback_narrative(res)
        src = "Rule-based narrative (offline fallback)"
        st.caption(src)
        st.markdown(esc_md(text))
    cache[key_hash] = (src, text)


with st.expander("📝 Narrative: what this means", expanded=False):
    render_narrative()
narrative_src, narrative = cache.get(key_hash, ("", ""))

# ----------------------------------------------------------------- exports
try:
    pdf_bytes = R.pdf_report(res)
    pdf_err = None
except Exception as e:  # pragma: no cover
    pdf_bytes, pdf_err = b"", f"{type(e).__name__}: {e}"
report_md = R.markdown_report(res, narrative, narrative_src)
zbuf = io.BytesIO()
with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
    for name, df in R.all_tables(res).items():
        z.writestr(f"{name}.csv", df.to_csv(index=False))
d1, d2, d3 = st.columns(3)
if pdf_bytes:
    d1.download_button("⬇ One-page PDF", pdf_bytes, file_name="rackready_summary.pdf", mime="application/pdf",
                       width="stretch", help="Summary, costs, future-ready paths and key design calculations.")
else:
    d1.error(f"PDF export failed ({pdf_err}). Use the Markdown report.")
d2.download_button("⬇ Full report (Markdown)", report_md, file_name="rackready_report.md", mime="text/markdown",
                   width="stretch", help="Everything, including every design calculation step.")
d3.download_button("⬇ Tables (CSV zip)", zbuf.getvalue(), file_name="rackready_tables.zip", mime="application/zip",
                   width="stretch", help="All tables for Excel.")

# ----------------------------------------------------------------- tabs
tabs = st.tabs(["💰 Costs", "🔮 Future-ready", "📐 Design calculations", "📈 Operations & ROI",
                "🗓️ Schedule & risks", "🏗️ Build & commission", "📚 Assumptions & sources"])
with tabs[0]:
    V.tab_costs(res)
with tabs[1]:
    V.tab_future(res)
with tabs[2]:
    V.tab_design(res)
with tabs[3]:
    V.tab_ops(res)
with tabs[4]:
    V.tab_schedule(res)
with tabs[5]:
    V.tab_build(res)
with tabs[6]:
    V.tab_assumptions(res)

with st.expander("📘 How it works"):
    st.markdown("""
**Two project types.** *Greenfield* is one new campus built from scratch: pick a GPU platform, size it in MW or
racks, and the model designs and prices it. *Existing building fit-out* compares keeping today's racks with a
future-ready fit-out in the same hall, and with retrofitting later.

**Design first, then cost.** The model sizes the utility service, transformers, generators, UPS, busway,
cooling, CDUs, coolant flows, floor loading, water and land with standard engineering formulas (see Design
calculations), then prices the build from a per-MW cost basis for the platform, adjusted for redundancy,
contingency, location, owner costs and escalation.

**Direct-to-chip liquid above 45 kW/rack.** Air tops out near 30 kW/rack and rear-door coolers near 45 kW.
Above 45 kW/rack every design uses direct-to-chip liquid cooling, set automatically.

**Future-proof horizon.** Choose 5, 10 or 15 years (Vera Rubin, Kyber, 1 MW-class racks). The model prices
retrofit later vs provisions now vs full future build on day one and recommends the lowest present cost.

**AI.** Every number comes from the deterministic model. NVIDIA Nemotron on Nebius Token Factory writes the
narrative from the model's output; without a key a rule-based narrative is shown.
""")
st.caption("RackReady AI · Built for Nebius x NVIDIA Build Week · " + E.DISCLAIMER)
