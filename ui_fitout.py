"""Existing-building fit-out views: current vs future-ready (+ retrofit path)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from engine import ASSUMPTIONS, COOLING_TYPES, D2C, D2C_NOTE
from ui_common import GREEN, GREY, dark, df_md, metric, money, usd_table, yrs

TABS = ["1 · Assumptions", "2 · CapEx", "3 · Future-ready upgrade", "4 · OpEx",
        "5 · Revenue & ROI", "6 · Comparison", "7 · Risks & recommendations"]


def cooling_label(s):
    return f"{s['cooling']} (auto: >45 kW)" if s["cooling_auto"] else s["cooling"]


def headline(res):
    cur, fut = res["current"], res["future"]
    m = st.columns(4)
    metric(m[0], "Total CapEx: current → future", f"{money(cur['capex'])} → {money(fut['capex'])}",
           f"{cur['it_mw']:.1f} → {fut['it_mw']:.1f} MW IT")
    metric(m[1], "CapEx per MW IT", f"{money(cur['capex_per_mw'])} → {money(fut['capex_per_mw'])}",
           f"{(fut['capex_per_mw']/cur['capex_per_mw']-1)*100:+.0f}% density premium")
    metric(m[2], "Annual OpEx (future-ready)", money(fut["opex"]), f"PUE {fut['pue']:.2f} vs {cur['pue']:.2f}")
    metric(m[3], "Simple payback (future-ready)", yrs(fut["simple_payback"]),
           f"current {yrs(cur['simple_payback'])}")


def build_tables(res, inputs):
    cur, fut, up = res["current"], res["future"], res["upgrade"]
    T = {}
    rows = []
    for k, v in ASSUMPTIONS.items():
        if k == "greenfield":
            continue
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, dict):
                    for k3, v3 in v2.items():
                        rows.append({"Group": f"{k} / {k2}", "Item": k3, "Value": v3})
                else:
                    rows.append({"Group": k, "Item": k2, "Value": v2})
        else:
            rows.append({"Group": "general", "Item": k, "Value": v})
    T["assumptions"] = pd.DataFrame(rows).astype(str)
    T["inputs"] = pd.DataFrame([
        ("Racks", inputs["racks"], inputs["racks"]),
        ("kW per rack", cur["kw_per_rack"], fut["kw_per_rack"]),
        ("Cooling (chosen)", inputs["current_cooling"], inputs["future_cooling"]),
        ("Cooling (applied)", cooling_label(cur), cooling_label(fut)),
        ("IT load (MW)", round(cur["it_mw"], 2), round(fut["it_mw"], 2)),
        ("Design PUE", cur["pue"], fut["pue"]),
        ("Facility load (MW)", round(cur["facility_mw"], 2), round(fut["facility_mw"], 2)),
        ("CDUs (N+1, 1.6 MW skids)", cur["cdus"], fut["cdus"]),
        ("Gross building area (sf)", f"{cur['gsf']:,.0f}", f"{fut['gsf']:,.0f}"),
        ("GPUs", cur["gpus"], fut["gpus"]),
    ], columns=["Parameter", "Current", "Future-ready"]).astype(str)
    sys_names = list(fut["systems"])
    T["sys_names"] = sys_names
    capex = pd.DataFrame({
        "System": sys_names + ["Soft costs (design, PM, Cx)", "Contingency", "TOTAL CapEx"],
        "Current": [cur["systems"][s] for s in sys_names] + [cur["soft"], cur["contingency"], cur["capex"]],
        "Future-ready": [fut["systems"][s] for s in sys_names] + [fut["soft"], fut["contingency"], fut["capex"]],
    })
    capex["Δ"] = capex["Future-ready"] - capex["Current"]
    capex["Future $/kW IT"] = capex["Future-ready"] / fut["it_kw"]
    T["capex"] = capex
    T["detail"] = pd.DataFrame(fut["detail"], columns=["System", "Line item", "Future-ready"])
    T["detail_cur"] = pd.DataFrame(cur["detail"], columns=["System", "Line item", "Current"])
    T["retro"] = pd.DataFrame(up["rows"], columns=["System", "Current build", "Future-ready need",
                                                   "Reused from current", "Retrofit new work (incl. premium)"])
    T["paths"] = pd.DataFrame([
        ("Year-0 facility CapEx", up["path_a_capex"], cur["capex"]),
        (f"Retrofit CapEx (year {up['retrofit_year']})", 0.0, up["retrofit_capex"]),
        (f"Lost revenue ({up['downtime_months']} mo downtime)", 0.0, up["downtime_cost"]),
        ("Total facility cost", up["path_a_capex"], up["path_b_total_with_downtime"]),
        (f"NPV @ {ASSUMPTIONS['discount_rate']*100:.0f}% over {inputs['horizon_years']} yrs (incl. revenue)",
         up["npv_a"], up["npv_b"]),
    ], columns=["Item", "A: Future-ready day one", "B: Build current + retrofit"])
    names = list(fut["opex_items"])
    T["opex"] = pd.DataFrame({
        "Annual OpEx line": names + ["TOTAL annual OpEx"],
        "Current": [cur["opex_items"][k] for k in names] + [cur["opex"]],
        "Future-ready": [fut["opex_items"][k] for k in names] + [fut["opex"]],
    })
    T["roi"] = pd.DataFrame([
        ("Annual revenue", cur["revenue"], fut["revenue"]),
        ("Annual OpEx", cur["opex"], fut["opex"]),
        ("Annual net operating cash", cur["net_annual"], fut["net_annual"]),
        ("Facility CapEx", cur["capex"], fut["capex"]),
        ("GPU hardware", cur["gpu_hw"], fut["gpu_hw"]),
        ("Total investment", cur["total_invest"], fut["total_invest"]),
        (f"NPV @ {ASSUMPTIONS['discount_rate']*100:.0f}%", cur["npv"], fut["npv"]),
    ], columns=["Metric", "Current", "Future-ready"])
    T["compare"] = pd.DataFrame([
        ("kW per rack", f"{cur['kw_per_rack']:.0f}", f"{fut['kw_per_rack']:.0f}"),
        ("Cooling", cooling_label(cur), cooling_label(fut)),
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
    ], columns=["Metric", "Current", "Future-ready"])
    T["lead"] = pd.DataFrame(res["long_lead"], columns=["Equipment", "CSI", "Lead time min (wks)",
                                                        "Lead time max (wks)"])
    return T


def render(res, inputs, render_narrative):
    cur, fut, up = res["current"], res["future"], res["upgrade"]
    T = build_tables(res, inputs)
    tabs = st.tabs(TABS)
    region, tier, red = inputs["region"], inputs["tier"], inputs["redundancy"]
    with tabs[0]:
        st.subheader("1. Assumptions")
        st.info("Existing-building fit-out. Indicative planning rates: NoVA = 1.00, Tier III, N+1, 2026 USD. "
                f"Cooling rule: **{D2C_NOTE}** (not overridable). The workbook excludes brownfield "
                "(01_ASSUME8 r15), so fit-out keeps RackReady trade rates; D2C CDU sizing "
                "(ROUNDUP(IT MW / 1.6) + 1 skids at $1.05M, 20_CSI8_MATRIX D20 / 12_CHANGE_PRICING F8) "
                "and D2C PUE 1.20 (01_ASSUME8 r33) come from the workbook.")
        a, b = st.columns(2)
        with a:
            st.markdown("**Scenario parameters**")
            st.dataframe(T["inputs"], hide_index=True, width="stretch")
            st.markdown("**Multipliers applied**")
            st.dataframe(pd.DataFrame([
                ("Location factor", ASSUMPTIONS["regions"][region]),
                ("Tier factor", ASSUMPTIONS["tier"][tier]),
                ("Redundancy: electrical", ASSUMPTIONS["redundancy"][red]["electrical"]),
                ("Redundancy: mechanical", ASSUMPTIONS["redundancy"][red]["mechanical"]),
                ("Soft costs", f"{ASSUMPTIONS['soft_costs_pct']*100:.0f}%"),
                ("Contingency", f"{ASSUMPTIONS['contingency_pct']*100:.0f}%"),
            ], columns=["Multiplier", "Value"]).astype(str), hide_index=True, width="stretch")
        with b:
            st.markdown("**Unit rates (ASSUMPTIONS dict)**")
            st.dataframe(T["assumptions"], hide_index=True, width="stretch", height=420)
    with tabs[1]:
        st.subheader("2. Construction CapEx breakdown")
        sn = T["sys_names"]
        fig = go.Figure()
        fig.add_bar(name="Current", x=sn, y=[cur["systems"][s] for s in sn], marker_color=GREY)
        fig.add_bar(name="Future-ready", x=sn, y=[fut["systems"][s] for s in sn], marker_color=GREEN)
        st.plotly_chart(dark(fig, 380, barmode="group", yaxis_title="USD"), width="stretch")
        st.dataframe(usd_table(T["capex"], ["Current", "Future-ready", "Δ", "Future $/kW IT"]),
                     hide_index=True, width="stretch")
        with st.expander("Line-item detail by CSI division"):
            x, y = st.columns(2)
            x.markdown("**Current**")
            x.dataframe(usd_table(T["detail_cur"], ["Current"]), hide_index=True, width="stretch")
            y.markdown("**Future-ready**")
            y.dataframe(usd_table(T["detail"], ["Future-ready"]), hide_index=True, width="stretch")
    with tabs[2]:
        st.subheader("3. Reconstruction / future-ready upgrade costs")
        k = st.columns(3)
        metric(k[0], "A: Future-ready day one", money(up["path_a_capex"]))
        metric(k[1], f"B: Current + retrofit yr {up['retrofit_year']}", money(up["path_b_total_with_downtime"]),
               f"{'+' if up['retrofit_penalty'] >= 0 else '-'}{money(abs(up['retrofit_penalty']))} vs A",
               delta_color="inverse")
        metric(k[2], "Engine recommendation", "Day one" if up["recommended"].startswith("Build future")
               else "Retrofit later", up["recommended"])
        st.dataframe(usd_table(T["paths"], ["A: Future-ready day one", "B: Build current + retrofit"]),
                     hide_index=True, width="stretch")
        st.caption(f"Retrofit premium {ASSUMPTIONS['retrofit_premium']:.2f}x for live-site work, "
                   f"demolition/rework {ASSUMPTIONS['retrofit_demo_pct']*100:.0f}% of current direct cost "
                   f"({money(up['demo'])}), {up['downtime_months']} months downtime.")
        fig2 = go.Figure()
        fig2.add_scatter(y=pd.Series(up["flows_a"]).cumsum(), name="A: Future-ready day one",
                         line=dict(color=GREEN, width=3))
        fig2.add_scatter(y=pd.Series(up["flows_b"]).cumsum(), name="B: Current + retrofit",
                         line=dict(color=GREY, width=3, dash="dash"))
        st.plotly_chart(dark(fig2, 320, xaxis_title="Year", yaxis_title="Cumulative cash (USD)"), width="stretch")
        with st.expander("Retrofit build-up by system"):
            st.dataframe(usd_table(T["retro"], list(T["retro"].columns[1:])), hide_index=True, width="stretch")
    with tabs[3]:
        st.subheader("4. Operational OpEx")
        k = st.columns(3)
        metric(k[0], "Annual OpEx: current", money(cur["opex"]))
        metric(k[1], "Annual OpEx: future-ready", money(fut["opex"]))
        metric(k[2], "PUE energy saving vs air", money(fut["pue_saving_vs_air"]) + "/yr",
               f"PUE {fut['pue']:.2f} vs {ASSUMPTIONS['pue']['Air']:.2f}")
        st.dataframe(usd_table(T["opex"], ["Current", "Future-ready"]), hide_index=True, width="stretch")
        avg_kw = fut["it_kw"] * inputs["utilization"]
        st.markdown("**PUE impact: annual energy cost of the future-ready IT load by cooling type**")
        st.bar_chart(pd.DataFrame({"Cooling": COOLING_TYPES, "Annual energy cost": [
            avg_kw * ASSUMPTIONS["pue"][c] * 8760 * inputs["power_cost"] for c in COOLING_TYPES]})
            .set_index("Cooling")["Annual energy cost"], color=GREEN, height=260)
        st.caption("Energy = IT kW × utilization × PUE × 8,760 h × $/kWh. Above 45 kW/rack only D2C is "
                   "allowed; the other bars are shown for reference. Maintenance "
                   f"{ASSUMPTIONS['maintenance_pct_of_capex']*100:.1f}% of CapEx/yr (indicative).")
    with tabs[4]:
        st.subheader("5. Revenue & ROI")
        k = st.columns(4)
        metric(k[0], "Annual revenue (future)", money(fut["revenue"]))
        metric(k[1], "Net operating cash / yr", money(fut["net_annual"]))
        metric(k[2], "Simple payback", yrs(fut["simple_payback"]))
        metric(k[3], f"NPV @ 8%, {inputs['horizon_years']} yrs", money(fut["npv"]))
        st.dataframe(usd_table(T["roi"], ["Current", "Future-ready"]), hide_index=True, width="stretch")
        st.caption("Revenue = GPUs × $/GPU-hr × utilization × 8,760 h. Future GPU hardware "
                   f"${ASSUMPTIONS['gpu_hw_cost_future']:,.0f}/GPU = workbook GB300 IT $/rack ÷ 72 "
                   "(01_ASSUME8 r9/r8). Simple payback = total investment / annual net operating cash.")
    with tabs[5]:
        st.subheader("6. Current vs future-ready comparison")
        st.dataframe(T["compare"], hide_index=True, width="stretch", height=530)
    with tabs[6]:
        st.subheader("7. Key risks & recommendations")
        st.markdown("**Long-lead equipment (indicative lead times)**")
        st.dataframe(T["lead"], hide_index=True, width="stretch")
        st.markdown("---")
        render_narrative()
    return T


def report_parts(res, inputs, T):
    cur, fut = res["current"], res["future"]
    return [
        "**Project type:** Existing building fit-out",
        "## Headline",
        f"- Total CapEx: {money(cur['capex'])} (current) vs {money(fut['capex'])} (future-ready)\n"
        f"- CapEx per MW IT: {money(cur['capex_per_mw'])} vs {money(fut['capex_per_mw'])}\n"
        f"- Annual OpEx: {money(cur['opex'])} vs {money(fut['opex'])}\n"
        f"- Simple payback: {yrs(cur['simple_payback'])} vs {yrs(fut['simple_payback'])}\n"
        f"- Cooling rule: {D2C_NOTE}",
        "## 1. Assumptions", T["inputs"].to_markdown(index=False),
        "## 2. Construction CapEx breakdown",
        df_md(T["capex"], ["Current", "Future-ready", "Δ", "Future $/kW IT"]),
        "## 3. Future-ready upgrade: day one vs retrofit",
        df_md(T["paths"], ["A: Future-ready day one", "B: Build current + retrofit"]),
        "## 4. OpEx", df_md(T["opex"], ["Current", "Future-ready"]),
        "## 5. Revenue & ROI", df_md(T["roi"], ["Current", "Future-ready"]),
        "## 6. Current vs future-ready", T["compare"].to_markdown(index=False),
        "## 7. Key risks & recommendations", T["lead"].to_markdown(index=False),
    ]


def csv_tables(T):
    return {"capex": T["capex"], "capex_detail_future": T["detail"], "upgrade_paths": T["paths"],
            "retrofit_buildup": T["retro"], "opex": T["opex"], "revenue_roi": T["roi"],
            "comparison": T["compare"], "long_lead": T["lead"], "assumptions": T["assumptions"]}
