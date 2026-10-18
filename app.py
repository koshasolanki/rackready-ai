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

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import workbook_basis as WB
from engine import (ASSUMPTIONS, COOLING_TYPES, DEFAULT_INPUTS, GREENFIELD, PROJECT_TYPES,
                    REGIONS, run_model, summary_for_llm)
from llm import (DEFAULT_BASE_URL, DEFAULT_MODEL, SUGGESTED_MODELS, LLMError,
                 fallback_narrative, resolve_api_key, stream_narrative)

st.set_page_config(page_title="RackReady AI", page_icon="⚡", layout="wide")

GREEN = "#76B900"
GREY = "#8A8F98"

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


# ----------------------------------------------------------------- helpers
def money(x: float) -> str:
    if x is None:
        return "n/a"
    a = abs(x)
    if a >= 1e9:
        return f"${x/1e9:,.2f}B"
    if a >= 1e6:
        return f"${x/1e6:,.1f}M"
    if a >= 1e3:
        return f"${x/1e3:,.0f}K"
    return f"${x:,.0f}"


def yrs(x):
    return "n/a" if x is None else f"{x:.1f} yrs"


def usd_table(df: pd.DataFrame, cols: list[str]) -> pd.io.formats.style.Styler:
    return df.style.format({c: "${:,.0f}" for c in cols})


def metric(col, label, value, delta=None, delta_color="off"):
    """st.metric with $ escaped (avoid LaTeX) and no arrow on informational deltas."""
    esc = lambda t: None if t is None else str(t).replace("$", "\\$")
    kw = dict(delta=esc(delta), delta_color=delta_color)
    if delta_color == "off":
        kw["delta_arrow"] = "off"
    try:
        col.metric(label, esc(value), **kw)
    except TypeError:  # older Streamlit without delta_arrow
        kw.pop("delta_arrow", None)
        col.metric(label, esc(value), **kw)


def esc_md(t: str) -> str:
    """Escape $ so Streamlit markdown does not render currency as LaTeX."""
    return str(t).replace("\\$", "$").replace("$", "\\$")


def esc_stream(gen):
    for chunk in gen:
        yield esc_md(chunk)


def get_secrets():
    try:
        _ = st.secrets.get("NEBIUS_API_KEY")  # touching it raises if no secrets file
        return st.secrets
    except Exception:
        return None


# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### ⚡ RackReady AI")
    st.caption("Indicative planning model. Defaults = 200-rack AI hall, NoVA.")
    project_type = st.radio(
        "Project type", PROJECT_TYPES, index=0, key="project_type",
        format_func=lambda p: "🏢 Existing building fit-out" if p == PROJECT_TYPES[0]
        else "🏗️ Greenfield: new build from scratch",
        help="Fit-out = MEP/IT into an existing hall. Greenfield = buy land and build everything: "
             "site/civil, shell & core, HV yard, utility interconnection, full MEP/IT, soft costs.")
    is_gf = project_type == GREENFIELD
    G = ASSUMPTIONS["greenfield"]
    with st.form("inputs"):
        st.markdown("**Project**")
        project_name = st.text_input("Project name", DEFAULT_INPUTS["project_name"])
        racks = st.number_input("Number of racks", 10, 5000, DEFAULT_INPUTS["racks"], step=10)
        c1, c2 = st.columns(2)
        current_kw = c1.number_input("Current kW/rack", 5.0, 60.0, DEFAULT_INPUTS["current_kw"], step=1.0)
        future_kw = c2.slider("Future-ready kW/rack", 40, 150, int(DEFAULT_INPUTS["future_kw"]), step=5)
        current_cooling = st.selectbox("Current cooling", COOLING_TYPES,
                                       COOLING_TYPES.index(DEFAULT_INPUTS["current_cooling"]))
        future_cooling = st.selectbox("Future-ready cooling", COOLING_TYPES,
                                      COOLING_TYPES.index(DEFAULT_INPUTS["future_cooling"]))
        region = st.selectbox(
            "Region (indicative location factor)", REGIONS,
            REGIONS.index(DEFAULT_INPUTS["region"]),
            format_func=lambda r: f"{r}  ({ASSUMPTIONS['regions'][r]:.2f})")
        c3, c4 = st.columns(2)
        tier = c3.selectbox("Tier", list(ASSUMPTIONS["tier"]), 1)
        redundancy = c4.selectbox("Redundancy", list(ASSUMPTIONS["redundancy"]), 1)

        gf_in = {}
        if is_gf:
            st.markdown("**Greenfield: land, utility, building, schedule**")
            g1, g2 = st.columns(2)
            gf_in["gf_land_cost_per_acre"] = g1.number_input(
                "Land $/acre", 0, 5_000_000, G["land_cost_per_acre"], step=25_000,
                help="Indicative; DC-zoned US land ranges ~$50k to $3M+/acre.")
            gf_in["gf_site_acres"] = g2.number_input(
                "Site acres (0 = auto)", 0.0, 2000.0, 0.0, step=1.0,
                help=f"Auto = footprint / {G['site_coverage']:.0%} coverage + "
                     f"{G['yard_acres_per_facility_mw']} ac per facility MW for the yard.")
            g3, g4 = st.columns(2)
            gf_in["gf_utility_mw"] = g3.number_input(
                "Utility service MW (0 = auto)", 0.0, 2000.0, 0.0, step=5.0,
                help="Auto = peak facility load (IT MW x PUE) of each scenario.")
            gf_in["gf_months_to_power"] = g4.number_input(
                "Months to utility power", 3, 96, G["months_to_power"],
                help="Interconnection queue + energization. Workbook: 12-48 months.")
            g5, g6 = st.columns(2)
            gf_in["gf_interconnect_fixed"] = g5.number_input(
                "Interconnect fixed $M", 0.0, 500.0, G["interconnect_fixed"] / 1e6, step=0.5) * 1e6
            gf_in["gf_interconnect_per_mw"] = g6.number_input(
                "Interconnect $k per MW", 0.0, 2000.0, G["interconnect_per_mw"] / 1e3, step=5.0) * 1e3
            g7, g8 = st.columns(2)
            gf_in["gf_shell_per_gsf"] = g7.number_input(
                "Shell & core $/gsf (0 = workbook)", 0, 5000, 0, step=25,
                help="0 = derived from your workbook's CSI 03-14 mix at this rack density.")
            gf_in["gf_construction_months"] = g8.number_input(
                "Construction months", 6, 60, G["construction_months"])
            g9, g10, g11 = st.columns(3)
            gf_in["gf_design_fees_pct"] = g9.number_input(
                "Design/permits %", 0.0, 30.0, G["design_fees_pct"] * 100, step=0.5) / 100
            gf_in["gf_contingency_pct"] = g10.number_input(
                "Contingency %", 0.0, 40.0, G["contingency_pct"] * 100, step=0.5) / 100
            gf_in["gf_escalation_per_year"] = g11.number_input(
                "Escalation %/yr", 0.0, 20.0, G["escalation_per_year"] * 100, step=0.5) / 100

        st.markdown("**Operations**")
        c5, c6 = st.columns(2)
        power_cost = c5.number_input("Power $/kWh", 0.02, 0.40, DEFAULT_INPUTS["power_cost"],
                                     step=0.005, format="%.3f")
        utilization = c6.slider("Utilization %", 30, 100, int(DEFAULT_INPUTS["utilization"] * 100)) / 100
        horizon = st.slider("Analysis horizon (years)", 3, 20, DEFAULT_INPUTS["horizon_years"])

        st.markdown("**Revenue (GPU rental)**")
        c7, c8 = st.columns(2)
        gpr_c = c7.number_input("GPUs/rack (current)", 0, 144, DEFAULT_INPUTS["gpus_per_rack_current"])
        gpr_f = c8.number_input("GPUs/rack (future)", 0, 144, DEFAULT_INPUTS["gpus_per_rack_future"])
        c9, c10 = st.columns(2)
        price_c = c9.number_input("$/GPU-hr (current)", 0.0, 20.0, DEFAULT_INPUTS["gpu_price_current"], step=0.25)
        price_f = c10.number_input("$/GPU-hr (future)", 0.0, 20.0, DEFAULT_INPUTS["gpu_price_future"], step=0.25)
        include_hw = st.checkbox("Include GPU hardware in ROI", DEFAULT_INPUTS["include_gpu_hw"])

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

inputs = {
    "project_name": project_name, "racks": int(racks), "current_kw": float(current_kw),
    "future_kw": float(future_kw), "current_cooling": current_cooling,
    "future_cooling": future_cooling, "region": region, "power_cost": float(power_cost),
    "utilization": float(utilization), "tier": tier, "redundancy": redundancy,
    "gpus_per_rack_current": int(gpr_c), "gpus_per_rack_future": int(gpr_f),
    "gpu_price_current": float(price_c), "gpu_price_future": float(price_f),
    "horizon_years": int(horizon), "include_gpu_hw": bool(include_hw),
    "project_type": project_type, **gf_in,
}

# ----------------------------------------------------------------- engine
res = run_model(inputs)
cur, fut, up = res["current"], res["future"], res["upgrade"]
gfc, gff = cur["greenfield"], fut["greenfield"]
PT_LABEL = "Greenfield new build" if is_gf else "Existing building fit-out"
payload = summary_for_llm(res)

# ----------------------------------------------------------------- header
st.markdown("# ⚡ RackReady AI")
st.markdown('<div class="rr-sub">Data Center Cost Modeling Agent for high-density AI racks: '
            'current vs future-ready. <b>Built for Nebius x NVIDIA Build Week.</b></div>',
            unsafe_allow_html=True)
st.markdown(
    f'<span class="rr-badge">{"🏗️ Greenfield new build" if is_gf else "🏢 Existing-building fit-out"}</span>'
    f'<span class="rr-badge">{inputs["racks"]} racks</span>'
    f'<span class="rr-badge">{cur["kw_per_rack"]:.0f} → {fut["kw_per_rack"]:.0f} kW/rack</span>'
    f'<span class="rr-badge">{fut["cooling"]}</span>'
    f'<span class="rr-badge">{region}</span>'
    f'<span class="rr-badge">{tier} · {redundancy}</span>', unsafe_allow_html=True)
st.caption("All figures are indicative planning numbers (2026 USD) for early-stage decisions, "
           "not a bid or estimate of record.")

for w in res["warnings"]:
    st.warning(w)

m = st.columns(4)
metric(m[0], ("Greenfield CapEx incl. land: current → future" if is_gf
             else "Total CapEx: current → future"),
       f"{money(cur['capex'])} → {money(fut['capex'])}",
       f"{cur['it_mw']:.1f} → {fut['it_mw']:.1f} MW IT"
       + (f" · {gff['acres']:.0f} ac · ~{gff['schedule']['months_to_rfs']:.0f} mo to RFS" if is_gf else ""))
metric(m[1], "CapEx per MW IT", f"{money(cur['capex_per_mw'])} → {money(fut['capex_per_mw'])}",
            f"{(fut['capex_per_mw']/cur['capex_per_mw']-1)*100:+.0f}% density premium")
metric(m[2], "Annual OpEx (future-ready)", money(fut["opex"]),
            f"PUE {fut['pue']:.2f} vs {cur['pue']:.2f}")
metric(m[3], "Simple payback (future-ready)", yrs(fut["simple_payback"]),
            f"current {yrs(cur['simple_payback'])}")

# ----------------------------------------------------------------- tables
assump_rows = []
for k, v in ASSUMPTIONS.items():
    if isinstance(v, dict):
        for k2, v2 in v.items():
            if isinstance(v2, dict):
                for k3, v3 in v2.items():
                    assump_rows.append({"Group": f"{k} / {k2}", "Item": k3, "Value": v3})
            else:
                assump_rows.append({"Group": k, "Item": k2, "Value": v2})
    else:
        assump_rows.append({"Group": "general", "Item": k, "Value": v})
df_assump = pd.DataFrame(assump_rows)
df_assump["Value"] = df_assump["Value"].astype(str)

df_inputs = pd.DataFrame([
    ("Racks", inputs["racks"], inputs["racks"]),
    ("kW per rack", cur["kw_per_rack"], fut["kw_per_rack"]),
    ("Cooling", cur["cooling"], fut["cooling"]),
    ("IT load (MW)", round(cur["it_mw"], 2), round(fut["it_mw"], 2)),
    ("Design PUE", cur["pue"], fut["pue"]),
    ("Facility load (MW)", round(cur["facility_mw"], 2), round(fut["facility_mw"], 2)),
    ("Gross building area (sf)", f"{cur['gsf']:,.0f}", f"{fut['gsf']:,.0f}"),
    ("GPUs", cur["gpus"], fut["gpus"]),
] + ([
    ("Site area (acres)", f"{gfc['acres']:,.1f}", f"{gff['acres']:,.1f}"),
    ("Utility service (MW)", f"{gfc['utility_mw']:,.1f}", f"{gff['utility_mw']:,.1f}"),
    ("On-site HV substation", "Yes" if gfc["hv_yard_on"] else "No (utility MV service)",
     "Yes" if gff["hv_yard_on"] else "No (utility MV service)"),
    ("Shell & core $/gsf", f"${gfc['shell_per_gsf']:,.0f}", f"${gff['shell_per_gsf']:,.0f}"),
    ("Months to ready-for-service", f"{gfc['schedule']['months_to_rfs']:.0f}",
     f"{gff['schedule']['months_to_rfs']:.0f}"),
] if is_gf else []), columns=["Parameter", "Current", "Future-ready"]).astype(str)

sys_names = list(fut["systems"])
owner_names = list(fut["owner_costs"])
soft_label = ("Soft costs (GC 9% + design, permits, fees, PM, CxA)" if is_gf
              else "Soft costs (design, PM, Cx)")
extra_names = [soft_label, "Contingency"] + (["Escalation to construction mid-point"] if is_gf else [])
def _extras(s):
    return [s["soft"], s["contingency"]] + ([s["escalation"]] if is_gf else [])
df_capex = pd.DataFrame({
    "System": sys_names + extra_names + owner_names
              + ["TOTAL greenfield CapEx (incl. land)" if is_gf else "TOTAL CapEx"],
    "Current": [cur["systems"][s] for s in sys_names] + _extras(cur)
               + [cur["owner_costs"][k] for k in owner_names] + [cur["capex"]],
    "Future-ready": [fut["systems"][s] for s in sys_names] + _extras(fut)
                    + [fut["owner_costs"][k] for k in owner_names] + [fut["capex"]],
})
df_capex["Δ"] = df_capex["Future-ready"] - df_capex["Current"]
df_capex["Future $/kW IT"] = df_capex["Future-ready"] / fut["it_kw"]

df_detail = pd.DataFrame(fut["detail"], columns=["System", "Line item", "Future-ready"])
df_detail_cur = pd.DataFrame(cur["detail"], columns=["System", "Line item", "Current"])

df_retro = pd.DataFrame(up["rows"], columns=["System", "Current build", "Future-ready need",
                                             "Reused from current", "Retrofit new work (incl. premium)"])
df_paths = pd.DataFrame([
    ("Year-0 facility CapEx", up["path_a_capex"], cur["capex"]),
    (f"Retrofit CapEx (year {up['retrofit_year']})", 0.0, up["retrofit_capex"]),
    (f"Lost revenue ({up['downtime_months']} mo downtime)", 0.0, up["downtime_cost"]),
    ("Total facility cost", up["path_a_capex"], up["path_b_total_with_downtime"]),
    (f"NPV @ {ASSUMPTIONS['discount_rate']*100:.0f}% over {inputs['horizon_years']} yrs (incl. revenue)",
     up["npv_a"], up["npv_b"]),
], columns=["Item", "A: Future-ready day one", "B: Build current + retrofit"])

opex_names = list(fut["opex_items"])
df_opex = pd.DataFrame({
    "Annual OpEx line": opex_names + ["TOTAL annual OpEx"],
    "Current": [cur["opex_items"][k] for k in opex_names] + [cur["opex"]],
    "Future-ready": [fut["opex_items"][k] for k in opex_names] + [fut["opex"]],
})

df_roi = pd.DataFrame([
    ("GPUs", cur["gpus"], fut["gpus"]),
    ("Annual revenue", cur["revenue"], fut["revenue"]),
    ("Annual OpEx", cur["opex"], fut["opex"]),
    ("Annual net operating cash", cur["net_annual"], fut["net_annual"]),
    ("Facility CapEx", cur["capex"], fut["capex"]),
    ("GPU hardware", cur["gpu_hw"], fut["gpu_hw"]),
    ("Total investment", cur["total_invest"], fut["total_invest"]),
    (f"NPV @ {ASSUMPTIONS['discount_rate']*100:.0f}%", cur["npv"], fut["npv"]),
], columns=["Metric", "Current", "Future-ready"])

df_compare = pd.DataFrame([
    ("kW per rack", f"{cur['kw_per_rack']:.0f}", f"{fut['kw_per_rack']:.0f}"),
    ("Cooling", cur["cooling"], fut["cooling"]),
    ("IT load", f"{cur['it_mw']:.1f} MW", f"{fut['it_mw']:.1f} MW"),
    ("Facility load (peak)", f"{cur['facility_mw']:.1f} MW", f"{fut['facility_mw']:.1f} MW"),
    ("Design PUE", f"{cur['pue']:.2f}", f"{fut['pue']:.2f}"),
    ("Total CapEx", money(cur["capex"]), money(fut["capex"])),
    ("CapEx per MW IT", money(cur["capex_per_mw"]), money(fut["capex_per_mw"])),
    ("CapEx per rack", money(cur["capex_per_rack"]), money(fut["capex_per_rack"])),
    ("Annual OpEx", money(cur["opex"]), money(fut["opex"])),
    ("Annual energy cost", money(sum(v for k, v in cur["opex_items"].items() if "energy" in k)),
     money(sum(v for k, v in fut["opex_items"].items() if "energy" in k))),
    ("Annual revenue", money(cur["revenue"]), money(fut["revenue"])),
    ("Simple payback", yrs(cur["simple_payback"]), yrs(fut["simple_payback"])),
    (f"NPV @ 8% ({inputs['horizon_years']} yrs)", money(cur["npv"]), money(fut["npv"])),
    ("Cooling within practical limit", "Yes" if cur["cooling_ok"] else "NO",
     "Yes" if fut["cooling_ok"] else "NO"),
] + ([
    ("Project type", "Greenfield new build", "Greenfield new build"),
    ("Land + utility interconnection", money(sum(cur["owner_costs"].values())),
     money(sum(fut["owner_costs"].values()))),
    ("Site area", f"{gfc['acres']:,.1f} acres", f"{gff['acres']:,.1f} acres"),
    ("CapEx per gross sf", money(cur["capex"] / cur["gsf"]), money(fut["capex"] / fut["gsf"])),
    ("Workbook-comparable facility $/MW IT", money(gfc["workbook_comparable_per_mw"]),
     money(gff["workbook_comparable_per_mw"])),
    ("Workbook band check", gfc["band_check"], gff["band_check"]),
    ("Months to ready-for-service", f"{gfc['schedule']['months_to_rfs']:.0f}",
     f"{gff['schedule']['months_to_rfs']:.0f}"),
    ("Critical path", gfc["schedule"]["critical_path"], gff["schedule"]["critical_path"]),
] if is_gf else []), columns=["Metric", "Current", "Future-ready"])

df_gf_rates = df_bench = df_sched = df_csi = None
if is_gf:
    gp = gff["params"]
    df_gf_rates = pd.DataFrame([
        ("Land $/acre", f"${gp['land_cost_per_acre']:,.0f}", "Input (indicative). Workbook screen: $5M land once per 100 MW campus (01_ASSUME8 r79)"),
        ("Site coverage (footprint / site)", f"{gp['site_coverage']:.0%}", "Indicative; workbook pad acres share 22-40% (01_ASSUME8 r19)"),
        ("Yard acres per facility MW", gp["yard_acres_per_facility_mw"], "Indicative: gens, TX, HV yard, dry coolers, fuel, setbacks"),
        ("Site & civil $/MW IT (current / future)",
         f"${gfc['benchmark']['site_civil_per_mw']:,.0f} / ${gff['benchmark']['site_civil_per_mw']:,.0f}",
         "Workbook 20_CSI8_MATRIX rows 7, 25-27 (Div 02/31/32/33 mix x RIGHT $/MW, net of 4% cont.)"),
        ("Site & civil floor $/acre", f"${gp['site_civil_min_per_acre']:,.0f}", "Indicative minimum for small sites"),
        ("Shell & core $/gsf (current / future)", f"${gfc['shell_per_gsf']:,.0f} / ${gff['shell_per_gsf']:,.0f}",
         "Workbook 20_CSI8_MATRIX rows 8-15, 17 (Div 03-12, 14) / 01_ASSUME8 r12 GSF per IT MW"
         if not gp["shell_per_gsf_override"] else "Input override"),
        ("On-site HV substation & yard $/kW facility", f"${gp['hv_yard_per_facility_kw']:,.0f}",
         f"Indicative; only above {gp['hv_yard_threshold_mw']} MW (11_SPEC_MOVES r15: 115-230 kV AIS yard)"),
        ("Utility interconnection", f"${gp['interconnect_fixed']/1e6:,.1f}M + ${gp['interconnect_per_mw']:,.0f}/MW",
         "Utility-side; workbook screen $8M once per 100 MW (01_ASSUME8 r78), live often $2-20M+"),
        ("GC / general conditions", f"{gp['gc_pct']:.0%}", "Workbook 01_ASSUME8 r63"),
        ("Design, permits, fees, PM, CxA", f"{gp['design_fees_pct']:.1%}", "Indicative owner soft costs (workbook excludes these)"),
        ("Contingency", f"{gp['contingency_pct']:.1%}", "Workbook 4% GMP screen; early stage 7-10% (01_ASSUME8 r64)"),
        ("Escalation", f"{gp['escalation_per_year']:.1%}/yr to mid-point", "Indicative 2026 planning"),
        ("Months to power / design+permit / construction",
         f"{gp['months_to_power']} / {gp['design_permit_months']} / {gp['construction_months']}",
         "Workbook: interconnect 12-48 months (11_SPEC_MOVES r22)"),
        ("Property tax / insurance", f"{gp['property_tax_pct']:.1%} / {gp['insurance_pct']:.1%}",
         "Indicative, before abatements"),
    ], columns=["Greenfield rate", "Value", "Source"]).astype(str)
    df_bench = pd.DataFrame([
        (n, p["kw"], p["gsf_per_mw"], p["low"], p["right"], p["high"])
        for n, p in sorted(WB.PLATFORMS.items(), key=lambda kv: kv[1]["kw"])
    ], columns=["Workbook platform", "kW/rack", "GSF / IT MW", "LOW $/IT MW", "RIGHT $/IT MW",
                "HIGH $/IT MW"])
    df_sched = pd.DataFrame([(k, round(gfc["schedule"]["drivers"][k], 1), round(v, 1))
                             for k, v in gff["schedule"]["drivers"].items()],
                            columns=["Schedule driver", "Current (months)", "Future-ready (months)"])
    df_csi = pd.DataFrame([(d, v) for d, v in gff["csi_crosscheck"].items()],
                          columns=["CSI division (workbook mix)", "Top-down $"])

df_lead = pd.DataFrame(res["long_lead"], columns=["Equipment", "CSI", "Lead time min (wks)",
                                                  "Lead time max (wks)"])

# ----------------------------------------------------------------- narrative (cached per input)
key_fp = hashlib.sha1((api_key or "").encode()).hexdigest()[:8]
key_hash = hashlib.sha1(json.dumps([payload, use_ai, base_url, model, key_fp], sort_keys=True,
                                   default=str).encode()).hexdigest()
cache = st.session_state.setdefault("narratives", {})
if regen:
    cache.pop(key_hash, None)

# ----------------------------------------------------------------- report tabs
tabs = st.tabs(["1 · Assumptions", "2 · CapEx", "3 · Future-ready upgrade", "4 · OpEx",
                "5 · Revenue & ROI", "6 · Comparison", "7 · Risks & recommendations"])

with tabs[0]:
    st.subheader("1. Assumptions")
    st.info(f"Project type: **{PT_LABEL}**. Indicative planning rates: NoVA = 1.00 location baseline, "
            "Tier III, N+1, 2026 USD. Edit the ASSUMPTIONS dict in engine.py to tune.")
    a, b = st.columns([1, 1])
    with a:
        st.markdown("**Scenario parameters**")
        st.dataframe(df_inputs, hide_index=True, width="stretch")
        st.markdown("**Multipliers applied**")
        st.dataframe(pd.DataFrame([
            ("Location factor", ASSUMPTIONS["regions"][region]),
            ("Tier factor", ASSUMPTIONS["tier"][tier]),
            ("Redundancy: electrical", ASSUMPTIONS["redundancy"][redundancy]["electrical"]),
            ("Redundancy: mechanical", ASSUMPTIONS["redundancy"][redundancy]["mechanical"]),
            ("Soft costs", f"{fut['soft_pct']*100:.0f}%"),
            ("Contingency", f"{fut['contingency_pct']*100:.0f}%"),
        ], columns=["Multiplier", "Value"]).astype(str), hide_index=True, width="stretch")
    with b:
        st.markdown("**Unit rates (ASSUMPTIONS dict)**")
        st.dataframe(df_assump, hide_index=True, width="stretch", height=420)
    if is_gf:
        st.markdown("**Greenfield (build from scratch) rates and sources**")
        st.caption(f"Source workbook: *{WB.SOURCE_NAME}*, sheets 01_ASSUME8, 03_SIDE8, "
                   "20_CSI8_MATRIX, 02_WHAT_RIGHT, 11_SPEC_MOVES. Basis: US greenfield, open shop, "
                   "N+1 block-redundant, 2026 GMP screen. Rates without a sheet/row are indicative "
                   "RackReady planning inputs.")
        st.dataframe(df_gf_rates, hide_index=True, width="stretch")
        st.markdown("**Workbook facility benchmark band ($/IT MW, 03_SIDE8 rows 8, 12, 13)**")
        st.dataframe(usd_table(df_bench, ["LOW $/IT MW", "RIGHT $/IT MW", "HIGH $/IT MW"]),
                     hide_index=True, width="stretch")
        st.caption("Workbook facility $ = shell through commissioning incl. on-site HV yard, gens, "
                   "fuel, UPS, cooling and site; excludes IT racks, AI fabric, land, utility-side "
                   "interconnect, owner staff and financing (02_WHAT_RIGHT row 6). Densities below "
                   "41 kW/rack are outside the workbook and use the H100 basis.")

with tabs[1]:
    st.subheader("2. Construction CapEx breakdown" + (" (greenfield, from scratch)" if is_gf else ""))
    if is_gf:
        k = st.columns(4)
        metric(k[0], "Land + utility interconnection", money(sum(fut["owner_costs"].values())),
               f"{gff['acres']:.1f} ac · {gff['utility_mw']:.1f} MW service")
        metric(k[1], "Site + shell + HV yard",
               money(fut["systems"]["Site work & civil (Div 02/31/32/33)"]
                     + fut["systems"]["Shell & core - new build (Div 03-14)"]
                     + fut["systems"]["On-site HV substation & yard (Div 26)"]),
               f"{fut['gsf']:,.0f} gsf")
        metric(k[2], "CapEx per gsf (future)", money(fut["capex"] / fut["gsf"]))
        metric(k[3], "Workbook check (future)", money(gff["workbook_comparable_per_mw"]) + "/MW",
               gff["band_check"])
    chart_names = sys_names + (["Soft + contingency + escalation"] + owner_names if is_gf else [])
    def _chart_vals(s):
        v = [s["systems"][n] for n in sys_names]
        if is_gf:
            v += [s["soft"] + s["contingency"] + s["escalation"]] + [s["owner_costs"][n] for n in owner_names]
        return v
    fig = go.Figure()
    fig.add_bar(name="Current", x=chart_names, y=_chart_vals(cur), marker_color=GREY)
    fig.add_bar(name="Future-ready", x=chart_names, y=_chart_vals(fut), marker_color=GREEN)
    fig.update_layout(barmode="group", template="plotly_dark", height=380,
                      margin=dict(l=10, r=10, t=30, b=10), yaxis_title="USD",
                      legend=dict(orientation="h", y=1.1), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(usd_table(df_capex, ["Current", "Future-ready", "Δ", "Future $/kW IT"]),
                 hide_index=True, width="stretch")
    with st.expander("Line-item detail by CSI division"):
        x, y = st.columns(2)
        x.markdown("**Current**")
        x.dataframe(usd_table(df_detail_cur, ["Current"]), hide_index=True, width="stretch")
        y.markdown("**Future-ready**")
        y.dataframe(usd_table(df_detail, ["Future-ready"]), hide_index=True, width="stretch")
    if is_gf:
        with st.expander("Top-down cross-check: your workbook's 22-division CSI mix (future-ready)"):
            st.caption(f"Workbook RIGHT {money(gff['benchmark']['right'])}/IT MW at "
                       f"{fut['kw_per_rack']:.0f} kW ({gff['benchmark']['bracket']}) x {fut['it_mw']:.1f} MW, "
                       f"split by the {gff['benchmark']['nearest_platform']} mix in 20_CSI8_MATRIX. "
                       "Excludes land, utility-side interconnect, IT racks, owner soft costs, escalation.")
            st.dataframe(usd_table(df_csi, ["Top-down $"]), hide_index=True, width="stretch")

with tabs[2]:
    st.subheader("3. Reconstruction / future-ready upgrade costs")
    k = st.columns(3)
    metric(k[0], "A: Future-ready day one", money(up["path_a_capex"]))
    metric(k[1], f"B: Current + retrofit yr {up['retrofit_year']}", money(up["path_b_total_with_downtime"]),
                f"{'+' if up['retrofit_penalty'] >= 0 else '-'}{money(abs(up['retrofit_penalty']))} vs A",
                delta_color="inverse")
    metric(k[2], "Engine recommendation", "Day one" if up["recommended"].startswith("Build future")
                else "Retrofit later", up["recommended"])
    st.dataframe(usd_table(df_paths, ["A: Future-ready day one", "B: Build current + retrofit"]),
                 hide_index=True, width="stretch")
    st.caption(f"Retrofit premium {ASSUMPTIONS['retrofit_premium']:.2f}x for live-site work, "
               f"demolition/rework {ASSUMPTIONS['retrofit_demo_pct']*100:.0f}% of current direct cost "
               f"({money(up['demo'])}), {up['downtime_months']} months downtime."
               + (f" Greenfield: the current-density building, site and utility service are extended "
                  f"later; extra land + utility upgrade {money(up['retrofit_owner_costs'])}, escalation "
                  f"to year {up['retrofit_year']} {money(up['retrofit_escalation'])}." if is_gf else ""))
    fig2 = go.Figure()
    cum_a = pd.Series(up["flows_a"]).cumsum()
    cum_b = pd.Series(up["flows_b"]).cumsum()
    fig2.add_scatter(y=cum_a, name="A: Future-ready day one", line=dict(color=GREEN, width=3))
    fig2.add_scatter(y=cum_b, name="B: Current + retrofit", line=dict(color=GREY, width=3, dash="dash"))
    fig2.update_layout(template="plotly_dark", height=320, xaxis_title="Year",
                       yaxis_title="Cumulative cash (USD)", margin=dict(l=10, r=10, t=30, b=10),
                       legend=dict(orientation="h", y=1.12), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, width="stretch")
    with st.expander("Retrofit build-up by system"):
        st.dataframe(usd_table(df_retro, list(df_retro.columns[1:])), hide_index=True,
                     width="stretch")

with tabs[3]:
    st.subheader("4. Operational OpEx")
    k = st.columns(3)
    metric(k[0], "Annual OpEx: current", money(cur["opex"]))
    metric(k[1], "Annual OpEx: future-ready", money(fut["opex"]))
    metric(k[2], "PUE energy saving vs air", money(fut["pue_saving_vs_air"]) + "/yr",
                f"PUE {fut['pue']:.2f} vs {ASSUMPTIONS['pue']['Air']:.2f}")
    st.dataframe(usd_table(df_opex, ["Current", "Future-ready"]), hide_index=True, width="stretch")
    st.markdown("**PUE impact: annual energy cost of the future-ready IT load under each cooling type**")
    avg_kw = fut["it_kw"] * inputs["utilization"]
    pue_df = pd.DataFrame({
        "Cooling": COOLING_TYPES,
        "PUE": [ASSUMPTIONS["pue"][c] for c in COOLING_TYPES],
        "Annual energy cost": [avg_kw * ASSUMPTIONS["pue"][c] * 8760 * inputs["power_cost"]
                               for c in COOLING_TYPES],
    })
    st.bar_chart(pue_df.set_index("Cooling")["Annual energy cost"], color=GREEN, height=260)
    st.caption("Energy = IT kW × utilization × PUE × 8,760 h × $/kWh. Maintenance "
               f"{ASSUMPTIONS['maintenance_pct_of_capex']*100:.1f}% of CapEx/yr; staffing "
               f"{ASSUMPTIONS['staff_base_fte']} FTE + {ASSUMPTIONS['staff_fte_per_mw']} FTE/MW."
               + (f" Greenfield owned asset: property tax {gff['params']['property_tax_pct']:.1%} of land + "
                  f"building + site, insurance {gff['params']['insurance_pct']:.1%} of depreciable CapEx, "
                  f"grounds ${gff['params']['grounds_per_acre_year']:,.0f}/acre/yr; maintenance excludes "
                  "land and utility-side cost." if is_gf else ""))

with tabs[4]:
    st.subheader("5. Revenue & ROI")
    k = st.columns(4)
    metric(k[0], "Annual revenue (future)", money(fut["revenue"]))
    metric(k[1], "Net operating cash / yr", money(fut["net_annual"]))
    metric(k[2], "Simple payback", yrs(fut["simple_payback"]))
    metric(k[3], f"NPV @ 8%, {inputs['horizon_years']} yrs", money(fut["npv"]))
    st.dataframe(usd_table(df_roi.iloc[1:], ["Current", "Future-ready"]), hide_index=True,
                 width="stretch")
    st.caption(f"Revenue = GPUs × $/GPU-hr × utilization × 8,760 h. GPU hardware "
               f"{'included' if include_hw else 'excluded'}; refreshed every "
               f"{ASSUMPTIONS['gpu_hw_life_years']} yrs at {ASSUMPTIONS['gpu_refresh_cost_factor']*100:.0f}% "
               "of original cost. Simple payback = total investment / annual net operating cash."
               + (" Greenfield: facility CapEx includes land, site, shell, utility interconnection, soft "
                  "costs, contingency and escalation. Revenue starts year 1 (construction period of "
                  f"~{gff['schedule']['months_to_rfs']:.0f} months and financing not modelled)." if is_gf else ""))

with tabs[5]:
    st.subheader("6. Current vs future-ready comparison" + (" (greenfield)" if is_gf else ""))
    st.dataframe(df_compare, hide_index=True, width="stretch", height=530 + (300 if is_gf else 0))

with tabs[6]:
    st.subheader("7. Key risks & recommendations")
    if is_gf:
        st.markdown(f"**Greenfield schedule to ready-for-service (critical path: "
                    f"{gff['schedule']['critical_path']})**")
        st.dataframe(df_sched, hide_index=True, width="stretch")
        st.markdown("**Greenfield risk register**")
        st.dataframe(pd.DataFrame([
            ("Power availability / interconnection queue", f"{gff['params']['months_to_power']} months to power assumed; "
             f"{gff['utility_mw']:.0f} MW request", "File for the full future MW now; consider bridge power"),
            ("Entitlement & permitting", "Zoning, generator air permits, noise, water, community",
             "Start before land closes; pre-application meetings"),
            ("Long-lead transformers / switchgear / generators", "80-130 / 52-80 / 52-78 weeks",
             "Reservation agreements and early release packages"),
            ("Site & geotech", "Rock, soils, water table, heavy-haul road", "Borings + ALTA before close"),
            ("Schedule & escalation", f"{gff['params']['escalation_per_year']:.1%}/yr escalation; "
             f"~{gff['schedule']['months_to_rfs']:.0f} months to RFS", "Lock GMP with bid units"),
        ], columns=["Risk", "Exposure", "Mitigation"]), hide_index=True, width="stretch")
    st.markdown("**Long-lead equipment (indicative lead times)**")
    st.dataframe(df_lead, hide_index=True, width="stretch")
    st.markdown("---")
    if key_hash in cache:
        src, text = cache[key_hash]
        st.caption(src)
        st.markdown(esc_md(text))
    else:
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
                text = str(text).replace("\\$", "$")  # store raw for export
                src = f"AI narrative · {model} via {base_url}"
                st.caption(src)
            except LLMError as e:
                st.warning(f"{e} Showing the built-in rule-based narrative instead.")
            except Exception as e:  # never break the demo
                st.warning(f"LLM error ({type(e).__name__}). Showing the built-in narrative instead.")
        elif use_ai:
            st.warning("No NEBIUS_API_KEY found. Showing the built-in rule-based narrative. "
                       "Add a key in 🤖 AI settings for the Nemotron narrative.")
        if text is None:
            text = fallback_narrative(res)
            src = "Rule-based narrative (offline fallback)"
            st.caption(src)
            st.markdown(esc_md(text))
        cache[key_hash] = (src, text)

narrative_src, narrative = cache.get(key_hash, ("", ""))

# ----------------------------------------------------------------- export
def df_md(df: pd.DataFrame, money_cols=()) -> str:
    d = df.copy()
    for c in money_cols:
        d[c] = d[c].map(lambda v: f"${v:,.0f}")
    return d.to_markdown(index=False)


report_md = "\n\n".join([
    f"# RackReady AI report: {inputs['project_name']}",
    f"**Project type:** {PT_LABEL}",
    f"_Generated {date.today().isoformat()} · Built for Nebius x NVIDIA Build Week · "
    "Indicative planning figures, not a bid._",
    "## Headline",
    f"- Total CapEx: {money(cur['capex'])} (current) vs {money(fut['capex'])} (future-ready)\n"
    f"- CapEx per MW IT: {money(cur['capex_per_mw'])} vs {money(fut['capex_per_mw'])}\n"
    f"- Annual OpEx: {money(cur['opex'])} vs {money(fut['opex'])}\n"
    f"- Simple payback: {yrs(cur['simple_payback'])} vs {yrs(fut['simple_payback'])}",
    "## 1. Assumptions", df_inputs.to_markdown(index=False),
    *([("### Greenfield rates & sources\n\n" + df_gf_rates.to_markdown(index=False)),
       ("### Greenfield schedule\n\n" + df_sched.to_markdown(index=False))] if is_gf else []),
    "## 2. Construction CapEx breakdown",
    df_md(df_capex, ["Current", "Future-ready", "Δ", "Future $/kW IT"]),
    "## 3. Future-ready upgrade: day one vs retrofit",
    df_md(df_paths, ["A: Future-ready day one", "B: Build current + retrofit"]),
    "## 4. OpEx", df_md(df_opex, ["Current", "Future-ready"]),
    "## 5. Revenue & ROI", df_md(df_roi.iloc[1:], ["Current", "Future-ready"]),
    "## 6. Current vs future-ready", df_compare.to_markdown(index=False),
    "## 7. Key risks & recommendations",
    df_lead.to_markdown(index=False),
    f"_{narrative_src}_", narrative or "",
])

zbuf = io.BytesIO()
with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
    for name, df in [("capex", df_capex), ("capex_detail_future", df_detail),
                     ("upgrade_paths", df_paths), ("retrofit_buildup", df_retro),
                     ("opex", df_opex), ("revenue_roi", df_roi), ("comparison", df_compare),
                     ("long_lead", df_lead), ("assumptions", df_assump),
                     ("greenfield_rates", df_gf_rates), ("greenfield_schedule", df_sched),
                     ("greenfield_csi_crosscheck", df_csi), ("workbook_benchmarks", df_bench)]:
        if df is not None:
            z.writestr(f"{name}.csv", df.to_csv(index=False))

st.markdown("---")
d1, d2, d3 = st.columns([1, 1, 2])
d1.download_button("⬇ Report (Markdown)", report_md, file_name="rackready_report.md",
                   mime="text/markdown", width="stretch")
d2.download_button("⬇ Tables (CSV zip)", zbuf.getvalue(), file_name="rackready_tables.zip",
                   mime="application/zip", width="stretch")

# ----------------------------------------------------------------- how it works
with st.expander("📘 How it works: the domain in plain language"):
    st.markdown("""
**High-density AI racks.** A traditional enterprise rack draws 5-15 kW. GPU racks for AI training
(e.g. NVIDIA GB200/GB300 NVL72) draw roughly 120-140 kW, and roadmaps go higher. Same floor, ~10x the power and heat.

**Why 140 kW needs liquid cooling.** Air can practically remove ~30 kW per rack. Rear-door heat
exchangers push that to ~50 kW. Beyond that, liquid must go to the chip: **direct-to-chip** cold plates,
or a **closed-loop full liquid** design where nearly all heat leaves in warm water, so dry coolers can
reject it most of the year with only trim chillers. That is why PUE drops from ~1.5 to ~1.15.

**CDUs (coolant distribution units).** Heat exchangers and pumps that separate the facility water loop
from the clean technology cooling loop (TCS) that runs to rack manifolds. They are new, long-lead,
and need careful commissioning (flushing, water quality, leak detection).

**Busway vs whips.** Old halls feed racks with individual cables ("whips") from PDUs under the floor.
High-density halls use overhead high-amp **busway** with plug-in tap-off boxes: faster to install,
easier to re-feed when rack power grows.

**CSI divisions.** Estimators organise cost by MasterFormat: Div 03/05/09 concrete, steel, finishes
(including thicker slabs for 3,000-4,000 lb liquid racks), Div 21 fire suppression, Div 23 HVAC /
mechanical, Div 26 electrical, Div 27 communications. Electrical and mechanical are 60-70% of a data center.

**Long-lead equipment.** Transformers (80-130 weeks), MV switchgear and generators (~1-1.5 years),
UPS, chillers and CDUs. Procurement, not construction, often sets the schedule.

**PUE.** Power Usage Effectiveness = total facility power / IT power. 1.5 means 50% overhead for
cooling and losses. Every 0.1 of PUE on a 28 MW hall is millions of dollars a year.

**Tiers and redundancy.** Uptime Tier III = concurrently maintainable; Tier IV = fault tolerant.
N+1 adds one spare unit; 2N duplicates the whole system. More redundancy, more cost.

**How this app works.** (1) A deterministic Python engine costs both scenarios from the
`ASSUMPTIONS` unit rates ($/kW IT by system + per-rack items × location × tier × redundancy,
plus soft costs and contingency), then OpEx, revenue, payback and NPV. (2) The numbers go as JSON to an
NVIDIA Nemotron model on Nebius Token Factory, prompted as a senior data center cost manager, which writes
the narrative without changing any totals. (3) No key? A rule-based narrative keeps the demo running.

**Greenfield (build from scratch).** Pick *Greenfield* as the project type to cost a new campus:
land ($/acre x acres sized from the building footprint and equipment yard), site work & civil
(CSI 02/31/32/33), a new shell & core (CSI 03-14, $/gsf from your workbook's CSI mix), an owner-side
HV substation above 20 MW, utility-side interconnection, the full MEP/IT fit-out, GC + design/permit
soft costs, contingency and escalation. The facility $/IT MW is checked against the workbook's
LOW / RIGHT / HIGH band, and the schedule shows whether power, construction or transformers set
the date. Ownership OpEx adds property tax, insurance and grounds.

**Construction phases.** Design (SD/DD/CD) → procurement → shell & core → MEP fit-out →
commissioning L1 (factory tests) to L5 (integrated systems test with load banks).
""")

st.caption("RackReady AI · Built for Nebius x NVIDIA Build Week · Indicative planning model.")
