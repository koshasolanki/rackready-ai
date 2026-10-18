"""
RackReady AI - Data Center Cost Modeling Agent
Built for Nebius x NVIDIA Build Week.

Run:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from datetime import date

import streamlit as st

import ui_fitout
import ui_greenfield
import workbook_basis as WB
from engine import (ASSUMPTIONS, COOLING_TYPES, D2C, D2C_AUTO_KW, D2C_NOTE, DEFAULT_INPUTS,
                    GF_REDUNDANCY, GREENFIELD, PLATFORM_CHOICES, PROJECT_TYPES, REGIONS,
                    run_model, summary_for_llm)
from llm import (DEFAULT_BASE_URL, DEFAULT_MODEL, SUGGESTED_MODELS, LLMError,
                 fallback_narrative, resolve_api_key, stream_narrative)
from ui_common import esc_md

st.set_page_config(page_title="RackReady AI", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
div[data-testid="stMetric"] {background: #161B22; border: 1px solid #262C36;
  border-radius: 10px; padding: 12px 16px;}
div[data-testid="stMetricValue"] {font-size: 1.55rem;}
.rr-sub {color: #9AA4B2; margin-top: -0.6rem; font-size: 1.02rem;}
.rr-badge {display:inline-block; background:#1f2a12; color:#76B900; border:1px solid #3d5a14;
  border-radius: 999px; padding: 2px 10px; font-size: 0.8rem; margin-right: 6px;}
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


def cooling_widget(container, label, kw, default, key):
    """Cooling selector: locked to D2C above 45 kW/rack, user choice at or below."""
    if kw > D2C_AUTO_KW:
        container.selectbox(label, [D2C], index=0, disabled=True, key=key + "_locked",
                            help=D2C_NOTE)
        container.caption(f"🔒 {D2C_NOTE}")
        return D2C
    opts = COOLING_TYPES
    return container.selectbox(label, opts, opts.index(default) if default in opts else 0,
                               key=key, help=f"Your choice at ≤{D2C_AUTO_KW:.0f} kW/rack. {D2C_NOTE}.")


# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### ⚡ RackReady AI")
    st.caption("Indicative planning model, not a bid.")
    project_type = st.radio(
        "Project type", PROJECT_TYPES, index=0, key="project_type",
        format_func=lambda p: "🏢 Existing building fit-out" if p == PROJECT_TYPES[0]
        else "🏗️ Greenfield: new build from scratch",
        help="Fit-out = current vs future-ready in an existing hall. Greenfield = ONE new design "
             "priced from scratch from your cost workbook.")
    is_gf = project_type == GREENFIELD
    D = DEFAULT_INPUTS
    inputs = {"project_type": project_type}
    with st.form("inputs"):
        st.markdown("**Project**")
        inputs["project_name"] = st.text_input(
            "Project name", "AI Campus - greenfield" if is_gf else D["project_name"])
        if not is_gf:
            inputs["racks"] = int(st.number_input("Number of racks", 10, 5000, D["racks"], step=10))
            c1, c2 = st.columns(2)
            inputs["current_kw"] = float(c1.number_input("Current kW/rack", 5.0, 60.0, D["current_kw"], step=1.0))
            inputs["future_kw"] = float(c2.slider("Future-ready kW/rack", 40, 150, int(D["future_kw"]), step=5))
            inputs["current_cooling"] = cooling_widget(st, "Current cooling", inputs["current_kw"],
                                                       D["current_cooling"], "cur_cool")
            inputs["future_cooling"] = cooling_widget(st, "Future-ready cooling", inputs["future_kw"],
                                                      D["future_cooling"], "fut_cool")
        else:
            st.markdown("**Greenfield design (one build)**")
            plat = st.selectbox("GPU platform (workbook)", PLATFORM_CHOICES,
                                PLATFORM_CHOICES.index(D["gf_platform"]), key="gf_platform",
                                format_func=lambda n: n if n == "Custom" else
                                f"{n} · {WB.PLATFORMS[n]['kw']} kW · {WB.PLATFORMS[n]['gpus']} GPUs/rack")
            inputs["gf_platform"] = plat
            if plat == "Custom":
                c1, c2, c3 = st.columns(3)
                inputs["gf_custom_kw"] = float(c1.number_input("kW/rack", 5.0, 800.0, D["gf_custom_kw"], step=5.0))
                nb = WB.custom_basis(inputs["gf_custom_kw"])
                inputs["gf_custom_gpus"] = int(c2.number_input("GPUs/rack", 1, 1000, int(round(nb["gpus"]))))
                inputs["gf_custom_it_per_rack"] = c3.number_input(
                    "IT $M/rack", 0.0, 100.0, round(nb["it_per_rack"] / 1e6, 2), step=0.1) * 1e6
                kw = inputs["gf_custom_kw"]
                st.caption(f"Custom basis interpolated on the workbook ladder ({nb['bracket']}).")
            else:
                kw = WB.PLATFORMS[plat]["kw"]
            size_by = st.radio("Size the build by", ["IT MW", "Racks"], horizontal=True, key="gf_size_by")
            inputs["gf_size_by"] = size_by
            if size_by == "IT MW":
                inputs["gf_it_mw"] = float(st.number_input("Campus IT MW (workbook B77 = 100)", 1.0, 5000.0,
                                                           D["gf_it_mw"], step=5.0))
            else:
                inputs["gf_racks"] = int(st.number_input("Number of racks", 1, 50000, D["gf_racks"], step=10))
            inputs["gf_cooling"] = cooling_widget(st, "Cooling (workbook basis at ≤45 kW: Air or RDHx)", kw,
                                                  "Hybrid (rear-door + air)", "gf_cool")
            inputs["gf_redundancy"] = st.selectbox("Redundancy (12_CHANGE_PRICING)", GF_REDUNDANCY, 0)
            g1, g2 = st.columns(2)
            inputs["gf_fuel_96h"] = g1.checkbox("Fuel 96 h (C10)", False)
            inputs["gf_union_seismic_piles"] = g2.checkbox("Union / seismic D / piles (C11)", False)
            g3, g4 = st.columns(2)
            inputs["gf_it_fitout"] = g3.checkbox("IT fit-out ON (C14)", False, help="01_ASSUME8 r81, workbook default OFF")
            inputs["gf_include_fabric"] = g4.checkbox("AI fabric in ROI", False, help="14_EIGHT_DEEP r47, excluded from facility $")
            inputs["gf_contingency_pct"] = st.number_input(
                "Contingency % (workbook 4%; 7-10% at 60% CD)", 0.0, 30.0, 4.0, step=0.5) / 100
            g5, g6 = st.columns(2)
            inputs["gf_land"] = g5.number_input("Land $M (r79)", 0.0, 2000.0, 5.0, step=0.5) * 1e6
            inputs["gf_interconnect"] = g6.number_input("Utility-side IC $M (r78)", 0.0, 2000.0, 8.0, step=0.5) * 1e6
            g7, g8 = st.columns(2)
            inputs["gf_months_to_power"] = int(g7.number_input("Months to power (12-48)", 3, 96,
                                                               ASSUMPTIONS["greenfield"]["months_to_power"]))
            inputs["gf_construction_months"] = int(g8.number_input("Construction months", 6, 60,
                                                                   ASSUMPTIONS["greenfield"]["construction_months"]))
            g9, g10, g11 = st.columns(3)
            inputs["gf_owner_costs_pct"] = g9.number_input("Owner costs %", 0.0, 30.0, 0.0, step=0.5,
                                                           help="Owner staff, A/E, permits: excluded by the workbook") / 100
            inputs["gf_escalation_pct"] = g10.number_input("Escalation %/yr", 0.0, 20.0, 0.0, step=0.5,
                                                           help="Workbook is a 2026 basis") / 100
            inputs["gf_property_tax_pct"] = g11.number_input("Property tax %", 0.0, 5.0, 0.0, step=0.1) / 100

        inputs["region"] = st.selectbox(
            "Region (indicative location factor)", REGIONS, REGIONS.index(D["region"]),
            format_func=lambda r: f"{r}  ({ASSUMPTIONS['regions'][r]:.2f})")
        if not is_gf:
            c3, c4 = st.columns(2)
            inputs["tier"] = c3.selectbox("Tier", list(ASSUMPTIONS["tier"]), 1)
            inputs["redundancy"] = c4.selectbox("Redundancy", list(ASSUMPTIONS["redundancy"]), 1)

        st.markdown("**Operations**")
        c5, c6 = st.columns(2)
        inputs["power_cost"] = float(c5.number_input("Power $/kWh", 0.02, 0.40, D["power_cost"],
                                                     step=0.005, format="%.3f"))
        inputs["utilization"] = c6.slider("Utilization %", 30, 100, int(D["utilization"] * 100)) / 100
        inputs["horizon_years"] = int(st.slider("Analysis horizon (years)", 3, 20, D["horizon_years"]))

        st.markdown("**Revenue (GPU rental)**")
        if not is_gf:
            c7, c8 = st.columns(2)
            inputs["gpus_per_rack_current"] = int(c7.number_input("GPUs/rack (current)", 0, 144, D["gpus_per_rack_current"]))
            inputs["gpus_per_rack_future"] = int(c8.number_input("GPUs/rack (future)", 0, 144, D["gpus_per_rack_future"]))
            c9, c10 = st.columns(2)
            inputs["gpu_price_current"] = float(c9.number_input("$/GPU-hr (current)", 0.0, 20.0, D["gpu_price_current"], step=0.25))
            inputs["gpu_price_future"] = float(c10.number_input("$/GPU-hr (future)", 0.0, 20.0, D["gpu_price_future"], step=0.25))
        else:
            p = float(st.number_input("$/GPU-hr (0 = indicative for platform)", 0.0, 50.0, 0.0, step=0.25))
            inputs["gf_gpu_price"] = p or None
        inputs["include_gpu_hw"] = st.checkbox(
            "Include GPU / IT hardware in ROI" + (" (workbook IT $/rack)" if is_gf else ""), True)
        st.form_submit_button("▶ Run cost model", type="primary", width="stretch")

    with st.expander("🤖 AI settings (Nebius Token Factory)", expanded=False):
        use_ai = st.toggle("Use LLM narrative", value=True)
        base_url = st.text_input("Base URL", os.environ.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL))
        model_choice = st.selectbox("Model", SUGGESTED_MODELS + ["Custom..."],
                                    0 if os.environ.get("NEBIUS_MODEL") is None else len(SUGGESTED_MODELS))
        model = (st.text_input("Custom model id", os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL))
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
        regen = st.button("↻ Regenerate narrative", width="stretch")

# ----------------------------------------------------------------- engine
res = run_model(inputs)
payload = summary_for_llm(res)
UI = ui_greenfield if is_gf else ui_fitout

# ----------------------------------------------------------------- header
st.markdown("# ⚡ RackReady AI")
st.markdown('<div class="rr-sub">Data Center Cost Modeling Agent for high-density AI racks. '
            '<b>Built for Nebius x NVIDIA Build Week.</b></div>', unsafe_allow_html=True)
if is_gf:
    d = res["design"]
    badges = ["🏗️ Greenfield new build", d["platform"], f"{d['kw_per_rack']:.0f} kW/rack",
              f"{d['racks']:,.0f} racks", f"{d['it_mw']:.1f} MW IT", d["cooling"], inputs["region"],
              inputs["gf_redundancy"]]
else:
    cur, fut = res["current"], res["future"]
    badges = ["🏢 Existing-building fit-out", f"{inputs['racks']} racks",
              f"{cur['kw_per_rack']:.0f} → {fut['kw_per_rack']:.0f} kW/rack", fut["cooling"],
              inputs["region"], f"{inputs['tier']} · {inputs['redundancy']}"]
st.markdown("".join(f'<span class="rr-badge">{b}</span>' for b in badges), unsafe_allow_html=True)
st.caption("All figures are indicative planning numbers (2026 USD) for early-stage decisions, "
           f"not a bid or estimate of record. {D2C_NOTE}.")
for w in res["warnings"]:
    st.warning(w)
UI.headline(res)

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
            src = f"AI narrative · {model} via {base_url}"
            st.caption(src)
        except LLMError as e:
            st.warning(f"{e} Showing the built-in rule-based narrative instead.")
            text = None
        except Exception as e:  # never break the demo
            st.warning(f"LLM error ({type(e).__name__}). Showing the built-in narrative instead.")
            text = None
    elif use_ai:
        st.warning("No NEBIUS_API_KEY found. Showing the built-in rule-based narrative. "
                   "Add a key in 🤖 AI settings for the Nemotron narrative.")
    if text is None:
        text = fallback_narrative(res)
        src = "Rule-based narrative (offline fallback)"
        st.caption(src)
        st.markdown(esc_md(text))
    cache[key_hash] = (src, text)


T = UI.render(res, inputs, render_narrative)
narrative_src, narrative = cache.get(key_hash, ("", ""))

# ----------------------------------------------------------------- export
report_md = "\n\n".join([
    f"# RackReady AI report: {inputs['project_name']}",
    f"_Generated {date.today().isoformat()} · Built for Nebius x NVIDIA Build Week · "
    "Indicative planning figures, not a bid._",
    *UI.report_parts(res, inputs, T),
    f"_{narrative_src}_", narrative or "",
])
zbuf = io.BytesIO()
with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
    for name, df in UI.csv_tables(T).items():
        z.writestr(f"{name}.csv", df.to_csv(index=False))

st.markdown("---")
d1, d2, _ = st.columns([1, 1, 2])
d1.download_button("⬇ Report (Markdown)", report_md, file_name="rackready_report.md",
                   mime="text/markdown", width="stretch")
d2.download_button("⬇ Tables (CSV zip)", zbuf.getvalue(), file_name="rackready_tables.zip",
                   mime="application/zip", width="stretch")

with st.expander("📘 How it works: the domain in plain language"):
    st.markdown("""
**Two project types.** *Existing building fit-out* compares a current build (e.g. 15 kW/rack air)
with a future-ready build (e.g. 140 kW/rack liquid) in the same hall, plus a build-current-then-retrofit
path. *Greenfield* is ONE new build from scratch: pick a GPU platform from your cost workbook
(H100 ... Kyber) or a custom density, size it by IT MW or racks, and the app prices it from the workbook:
RIGHT facility $/IT MW × IT MW, split into 22 CSI divisions, N+1 quantities (gens, UPS, CDUs, taps),
change pricing for N+2 / 2N / 96 h fuel / union-seismic-piles / contingency, then adds what the workbook
keeps outside facility $: land, utility-side interconnect, IT iron and AI fabric. A reconciliation table
ties the result back to the workbook's own totals.

**D2C above 45 kW/rack.** Air tops out near 30 kW/rack and rear-door heat exchangers near 45 kW. Above
45 kW/rack every design uses **direct-to-chip (D2C) liquid**: cold plates fed by CDUs (N+1, on UPS)
through a technology cooling loop, with dry/adiabatic heat rejection and a small residual-air share.
The app sets this automatically.

**CSI divisions.** Div 03/05/07 concrete, steel, envelope; Div 21 fire; Div 22 plumbing & fuel; Div 23
HVAC/liquid; Div 26 electrical (HV yard, gens, UPS, busway); Div 27 comms; Div 31-33 site.

**Long-lead equipment.** Transformers (the workbook's "90-week transformer"), MV switchgear and
generators set the schedule more than construction does. Never present land without months-to-power.

**How the AI is used.** The deterministic engine computes every number. The JSON goes to an NVIDIA
Nemotron model on Nebius Token Factory, prompted as a senior data center cost manager, which writes the
narrative without changing totals. No key? A rule-based narrative keeps the demo running.
""")

st.caption("RackReady AI · Built for Nebius x NVIDIA Build Week · Indicative planning model.")
