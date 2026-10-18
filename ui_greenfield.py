"""Greenfield views: ONE new build from scratch, priced from the user's workbook."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import workbook_basis as WB
from engine import ASSUMPTIONS, D2C_NOTE, platform_table
from ui_common import AMBER, GREEN, GREY, dark, df_md, metric, money, usd_table, yrs

TABS = ["1 · Assumptions", "2 · CapEx", "3 · Platform benchmark & scope", "4 · OpEx",
        "5 · Revenue & ROI", "6 · Workbook comparison", "7 · Risks & schedule"]

REGISTER = [  # (label, field, sheet/row, fmt)
    ("IT kW / rack design", "kw", "01_ASSUME8 r6", "{:,.0f}"),
    ("IT kW / rack infra", "kw_infra", "01_ASSUME8 r7", "{:,.0f}"),
    ("GPUs or chips / rack", "gpus", "01_ASSUME8 r8", "{:,.0f}"),
    ("IT $ / rack mid (outside facility $)", "it_per_rack", "01_ASSUME8 r9", "${:,.0f}"),
    ("Weight lb / rack", "weight_lb", "01_ASSUME8 r10", "{:,.0f}"),
    ("White + aisle SF / rack", "white_sf_per_rack", "01_ASSUME8 r11", "{:,.0f}"),
    ("GSF / IT MW", "gsf_per_mw", "01_ASSUME8 r12", "{:,.0f}"),
    ("SOG thickness (in)", "sog_in", "01_ASSUME8 r20", "{}"),
    ("Path to rack", "path_to_rack", "01_ASSUME8 r30", "{}"),
    ("PUE planning", "pue", "01_ASSUME8 r33", "{:.2f}"),
    ("Standby MW @ 100 MW IT", "standby_mw_100", "01_ASSUME8 r34", "{:,.0f}"),
    ("On-site HV yard", "onsite_hv", "01_ASSUME8 r39", "{}"),
    ("Busway / PDU class", "busway", "01_ASSUME8 r40", "{}"),
    ("800V $ at 100 MW (inside Method A)", "v800_100mw", "01_ASSUME8 r43", "${:,.0f}"),
    ("Cooling mode", "cooling_mode", "01_ASSUME8 r46", "{}"),
    ("Heat rejection", "heat_rejection", "01_ASSUME8 r49", "{}"),
    ("CDU architecture", "cdu_arch", "01_ASSUME8 r50", "{}"),
    ("CDU MW each", "cdu_mw", "01_ASSUME8 r51", "{}"),
    ("Residual air share", "air_share", "01_ASSUME8 r54", "{}"),
    ("GC %", "gc_pct", "01_ASSUME8 r63", "{:.0%}"),
    ("Contingency %", "cont_pct", "01_ASSUME8 r64", "{:.0%}"),
    ("BIM + CxA + loadbank $ / 100 MW", "bim_cxa_100mw", "01_ASSUME8 r65", "${:,.0f}"),
    ("Method A $ / 100 MW (bottoms-up)", "method_a_100mw", "01_ASSUME8 r69", "${:,.0f}"),
    ("Method B mid $ / MW", "method_b_mid", "01_ASSUME8 r70", "${:,.0f}"),
    ("RIGHT facility $ / IT MW", "right", "03_SIDE8 r8", "${:,.0f}"),
    ("LOW (Method A) $ / IT MW", "low", "03_SIDE8 r12", "${:,.0f}"),
    ("HIGH (Method B high) $ / IT MW", "high", "03_SIDE8 r13", "${:,.0f}"),
    ("Interconnect adder (once)", "interconnect_once", "01_ASSUME8 r78", "${:,.0f}"),
    ("Land adder (once)", "land_once", "01_ASSUME8 r79", "${:,.0f}"),
    ("IT fit-out $ / MW (not GPU, default OFF)", "it_fitout_per_mw", "01_ASSUME8 r81", "${:,.0f}"),
    ("Fuel visible $ / 100 MW (inside facility)", "fuel_100mw", "01_ASSUME8 r82", "${:,.0f}"),
    ("IT $ / IT MW", "it_per_mw", "03_SIDE8 r14", "${:,.0f}"),
    ("AI fabric $ / MW (excluded)", "fabric_per_mw", "14_EIGHT_DEEP r47", "${:,.0f}"),
]


def _fmt(fmt, v):
    try:
        return fmt.format(v)
    except Exception:
        return str(v)


def headline(res):
    d = res["design"]
    b = d["basis"]
    m = st.columns(4)
    metric(m[0], "Greenfield CapEx (facility + land + utility)", money(d["capex"]),
           f"{d['it_mw']:.1f} MW IT · {d['racks']:,.0f} racks · {d['platform']}")
    metric(m[1], "Facility $ per MW IT", money(d["facility_per_mw"]),
           f"workbook RIGHT {money(b['right'])} · {d['band_check']}")
    metric(m[2], "Annual OpEx", money(d["opex"]), f"PUE {d['pue']:.2f} · {d['cooling'].split(' (')[0]}")
    metric(m[3], "Simple payback", yrs(d["simple_payback"]),
           f"~{d['schedule']['months_to_rfs']:.0f} months to ready-for-service")


def build_tables(res, inputs):
    d = res["design"]
    b, q = d["basis"], d["quantities"]
    G = ASSUMPTIONS["greenfield"]
    T = {}
    T["design"] = pd.DataFrame([
        ("Workbook platform", d["platform"] + ("" if d["platform"] != "Custom" else f" (interpolated {b['bracket']})")),
        ("kW per rack", f"{d['kw_per_rack']:,.0f}"),
        ("Racks", f"{d['racks']:,.1f}"),
        ("GPUs / chips per rack", f"{d['gpus_per_rack']:,.0f}"),
        ("GPUs / chips", f"{d['gpus']:,.0f}"),
        ("IT load", f"{d['it_mw']:,.2f} MW"),
        ("Cooling", d["cooling"] + (f"  ({D2C_NOTE})" if d["cooling_auto"] else "  (user choice, ≤45 kW/rack)")),
        ("PUE", f"{d['pue']:.3f}"),
        ("Standby / running plant (IT × PUE)", f"{q['standby_mw']:,.1f} MW"),
        ("Gross building area (GSF / IT MW × MW)", f"{d['gsf']:,.0f} sf"),
        ("Generators (3 MW): N / N+1 base", f"{q['gens_n']} / {q['gens_n1']}"),
        ("UPS 1 MW modules, A/B N+1 (~1.1 × IT MW)", f"{q['ups_n1']}"),
        ("CDUs = ROUNDUP(IT MW / CDU MW) + 1", f"{q['cdus']}"),
        ("Taps A/B (2 × racks)", f"{q['taps']:,.0f}"),
        ("Redundancy", inputs["gf_redundancy"]),
        ("Location factor", f"{ASSUMPTIONS['regions'][inputs['region']]:.2f} ({inputs['region']})"),
    ], columns=["Design parameter", "Value"])
    T["register"] = pd.DataFrame([(lab, _fmt(fmt, b.get(f)), src) for lab, f, src, fmt in REGISTER],
                                 columns=[f"Workbook driver ({b['bracket']})", "Value", "Source"])
    T["indicative"] = pd.DataFrame([
        ("Months to utility power", f"{d['schedule']['months_to_power']}",
         "Indicative, inside workbook 12-48 mo range (11_SPEC_MOVES r15/r22)"),
        ("Design + permits / construction months",
         f"{G['design_permit_months']} / {inputs.get('gf_construction_months') or G['construction_months']}",
         "Indicative (workbook has no schedule sheet)"),
        ("$ / GPU-hr rental", f"${d['gpu_price']:.2f}", "Indicative (workbook has no revenue data)"),
        ("Maintenance / insurance", f"{ASSUMPTIONS['maintenance_pct_of_capex']:.1%} / {G['insurance_pct']:.1%} of facility",
         "Indicative (no OpEx sheet in workbook)"),
        ("Staffing", f"{ASSUMPTIONS['staff_base_fte']} + {ASSUMPTIONS['staff_fte_per_mw']}/MW FTE × "
                     f"${ASSUMPTIONS['staff_cost_per_fte']:,.0f}", "Indicative"),
        ("Property tax", f"{(inputs.get('gf_property_tax_pct') if inputs.get('gf_property_tax_pct') is not None else G['property_tax_pct']):.2%}",
         "Input; workbook excludes tax (02_WHAT_RIGHT r6)"),
        ("Owner costs / escalation", f"{inputs.get('gf_owner_costs_pct', 0):.1%} / {inputs.get('gf_escalation_pct', 0):.1%} per yr",
         "Input, default 0: workbook excludes owner staff and escalation past 2026"),
        ("Location factors", "NoVA = 1.00", "Indicative RackReady index; workbook = US open-shop basis"),
    ], columns=["Not in workbook", "Value", "Basis"])
    # CapEx by CSI division
    rows = []
    for div, v in d["csi"].items():
        rows.append((div, b["csi_mix"][div], v, v / d["it_mw"], WB.CSI_TEXT[div]["included"]))
    csi = pd.DataFrame(rows, columns=["CSI division", "Mix %", "Facility $", "$ / IT MW", "What's IN (20_CSI8_MATRIX)"])
    T["csi"] = csi
    T["changes"] = pd.DataFrame([(n, a, w) for n, a, w in d["changes"]] or [("None (workbook N+1 base)", 0.0, 0.0)],
                                columns=["Change (12_CHANGE_PRICING)", "Delta before soft", "Delta with soft"])
    summ = [("Workbook facility (22 CSI divisions)", d["wb_facility"])]
    summ += [(n, w) for n, _, w in d["changes"]]
    if d["region_adj"]:
        summ.append(("Location factor adjustment", d["region_adj"]))
    summ.append(("FACILITY $ (shell → commissioning)", d["facility"]))
    summ += list(d["adders"].items())
    summ.append(("TOTAL GREENFIELD CapEx", d["capex"]))
    summ.append(("IT iron (racks × IT $/rack), outside CapEx", d["it_hw"]))
    if d["fabric"]:
        summ.append(("AI fabric (14_EIGHT_DEEP r47), outside CapEx", d["fabric"]))
    T["summary"] = pd.DataFrame(summ, columns=["CapEx line", "USD"])
    T["summary"]["$ / IT MW"] = T["summary"]["USD"] / d["it_mw"]
    T["recon"] = pd.DataFrame(d["reconciliation"], columns=["Line", "Workbook", "App", "Difference", "Explanation"])
    pt = pd.DataFrame(platform_table(d["it_mw"]))
    pt.insert(0, "Selected", pt["platform"].map(lambda n: "◀" if n == d["platform"] else ""))
    T["platforms"] = pt.rename(columns={
        "platform": "Platform", "kw": "kW/rack", "cooling": "Cooling (r46)", "pue": "PUE",
        "low": "LOW $/MW", "right": "RIGHT $/MW", "high": "HIGH $/MW", "facility": f"Facility $ @ {d['it_mw']:.0f} MW",
        "racks": "Racks", "gpus": "GPUs/chips", "gsf": "GSF", "per_sf": "$/SF", "per_kw": "$/IT kW",
        "per_rack": "Facility $/rack", "it": "IT $", "all_in": "Facility + IT $"})
    T["scope"] = pd.DataFrame(WB.SPEC_MOVES, columns=["Package", "In recommended $?", "Spec assumed",
                                                      "NOT included", "What moves the $", "How you reprice",
                                                      "Likely swing"])
    names = list(d["opex_items"])
    T["opex"] = pd.DataFrame({"Annual OpEx line": names + ["TOTAL annual OpEx"],
                              "USD / yr": [d["opex_items"][k] for k in names] + [d["opex"]]})
    T["roi"] = pd.DataFrame([
        ("GPUs / chips", d["gpus"]),
        ("Annual revenue", d["revenue"]), ("Annual OpEx", d["opex"]),
        ("Annual net operating cash", d["net_annual"]),
        ("Greenfield CapEx (facility + land + utility)", d["capex"]),
        ("IT iron (01_ASSUME8 r9 × racks)" + ("" if inputs.get("include_gpu_hw", True) else " (excluded)"), d["gpu_hw"]),
        ("AI fabric (14_EIGHT_DEEP r47)", d["fabric"]),
        ("Total investment", d["total_invest"]),
        (f"NPV @ {ASSUMPTIONS['discount_rate']*100:.0f}%, {inputs['horizon_years']} yrs", d["npv"]),
    ], columns=["Metric", "Value"])
    trio = [("Facility $ / IT MW", d["facility_per_mw"], b["right"]),
            ("Facility $ / GSF", d["facility_per_gsf"], b["right"] / b["gsf_per_mw"]),
            ("Facility $ / IT kW", d["facility_per_kw"], b["right"] / 1000),
            ("Facility $ / rack", d["facility_per_rack"], b["right"] * d["kw_per_rack"] / 1000)]
    T["trio"] = pd.DataFrame([(n, a, w, a - w) for n, a, w in trio],
                             columns=["Benchmark (03_SIDE8 r8/r10/r19/r20)", "App", "Workbook RIGHT", "Difference"])
    T["band"] = pd.DataFrame([
        ("Workbook band LOW (Method A bottoms-up, 03_SIDE8 r12)", b["low"]),
        ("Workbook WK band low (01_ASSUME8 r73)", b["wk_low"]),
        ("Workbook RIGHT = avg(A, B mid) (03_SIDE8 r8)", b["right"]),
        ("Workbook Method B mix mid (01_ASSUME8 r70)", b["method_b_mid"]),
        ("Workbook WK band high (01_ASSUME8 r74)", b["wk_high"]),
        ("Workbook band HIGH (Method B high, 03_SIDE8 r13)", b["high"]),
        ("App facility $ / IT MW", d["facility_per_mw"]),
        ("App greenfield CapEx $ / IT MW (incl. land + utility)", d["capex_per_mw"]),
    ], columns=["$ per IT MW", "Value"])
    s = d["schedule"]
    T["schedule"] = pd.DataFrame([(k, round(v, 1), "◀ critical path" if k == s["critical_path"] else "")
                                  for k, v in s["drivers"].items()], columns=["Schedule driver", "Months", ""])
    T["risks"] = pd.DataFrame([
        ("Power availability / interconnection queue", f"{s['months_to_power']} months to power; "
         f"{d['facility_mw']:.0f} MW running plant", "Utility-side IC excluded from facility $; live often "
         "$2-20M+ and 12-48 mo (11_SPEC_MOVES r22). Never present land without months-to-power."),
        ("Long-lead transformers / switchgear / gens", f"{WB.TRANSFORMER_WEEKS}-week transformer; "
         f"{d['quantities']['gens_n1']} × 3 MW gens", "Reserve slots; you cannot crash a 90-week transformer "
         "(12_CHANGE_PRICING H40)."),
        ("Phoenix module freeze", f"{b['module']}", "Wrong-gen module = missed slot; FAT before ship (01_ASSUME8 r60-61)."),
        ("CDU MW ladder", f"{d['quantities']['cdus']} CDUs @ {b['cdu_mw']} MW", "Most attackable Method A number (02_WHAT_RIGHT r10)."),
        ("Contingency", f"{b['cont_pct']:.0%} screen", "7-10% at 60% CD (01_ASSUME8 r64); use C12."),
        ("Site / geotech", "Greenfield, no rock, spread + SOG", "Piles / over-ex are 03/31 changes (11_SPEC_MOVES r6)."),
        ("Entitlement & permitting", "Zoning, generator air permits, water", "Start before land closes (indicative)."),
        ("Redundancy wording", "N+1 block in base", "2N is a change sheet, not a smile (25_REDUNDANCY)."),
    ], columns=["Risk", "Exposure", "Workbook guidance / mitigation"])
    T["lead"] = pd.DataFrame(res["long_lead"], columns=["Equipment", "CSI", "Lead time min (wks)", "Lead time max (wks)"])
    return T


def render(res, inputs, render_narrative):
    d = res["design"]
    b = d["basis"]
    T = build_tables(res, inputs)
    tabs = st.tabs(TABS)
    with tabs[0]:
        st.subheader("1. Assumptions: one greenfield design, priced from your workbook")
        st.info(f"Greenfield new build from scratch: a single design, no 'current' case. Basis: "
                f"*{WB.SOURCE_NAME}* (US greenfield, open shop, N+1 block, 2026 GMP screen). "
                f"Cooling rule: **{D2C_NOTE}**.")
        a, c = st.columns([1, 1])
        a.markdown("**Design**")
        a.dataframe(T["design"], hide_index=True, width="stretch", height=600)
        c.markdown("**Workbook register used (sheet / row)**")
        c.dataframe(T["register"], hide_index=True, width="stretch", height=600)
        st.markdown("**Indicative inputs (only where the workbook has no value)**")
        st.dataframe(T["indicative"], hide_index=True, width="stretch")
    with tabs[1]:
        st.subheader("2. Greenfield CapEx (build from scratch)")
        k = st.columns(4)
        metric(k[0], "Facility $ (workbook scope)", money(d["facility"]), f"{money(d['facility_per_mw'])}/MW IT")
        metric(k[1], "Land + utility interconnect", money(sum(v for n, v in d["adders"].items()
                                                             if "Land" in n or "interconnect" in n)), "workbook adders")
        metric(k[2], "Facility $ / GSF", money(d["facility_per_gsf"]), f"{d['gsf']:,.0f} gsf")
        metric(k[3], "Band check", d["band_check"], f"{money(b['low'])} – {money(b['high'])}/MW")
        fig = go.Figure()
        fig.add_bar(x=list(d["csi"]), y=list(d["csi"].values()), marker_color=GREEN, name="CSI division")
        st.plotly_chart(dark(fig, 360, yaxis_title="USD"), width="stretch")
        st.dataframe(usd_table(T["summary"], ["USD", "$ / IT MW"]), hide_index=True, width="stretch")
        st.markdown("**Reconciliation to the workbook's own totals (same IT MW)**")
        st.dataframe(usd_table(T["recon"], ["Workbook", "App", "Difference"]), hide_index=True, width="stretch")
        with st.expander("22 CSI divisions (20_CSI8_MATRIX mix × RIGHT $/IT MW)", expanded=False):
            st.dataframe(T["csi"].style.format({"Mix %": "{:.2%}", "Facility $": "${:,.0f}", "$ / IT MW": "${:,.0f}"}),
                         hide_index=True, width="stretch")
        with st.expander("Change pricing applied (12_CHANGE_PRICING: machines × unit, soft 13% on delta)"):
            st.dataframe(usd_table(T["changes"], ["Delta before soft", "Delta with soft"]), hide_index=True, width="stretch")
    with tabs[2]:
        st.subheader(f"3. Platform benchmark & scope: the workbook's 8 platforms at {d['it_mw']:.0f} MW IT")
        fig = go.Figure()
        pt = T["platforms"]
        fig.add_bar(x=pt["Platform"], y=pt["LOW $/MW"], name="LOW", marker_color=GREY)
        fig.add_bar(x=pt["Platform"], y=pt["RIGHT $/MW"], name="RIGHT", marker_color=GREEN)
        fig.add_bar(x=pt["Platform"], y=pt["HIGH $/MW"], name="HIGH", marker_color="#3a4048")
        fig.add_scatter(x=[d["platform"] if d["platform"] in WB.PLATFORMS else b["nearest"]],
                        y=[d["facility_per_mw"]], mode="markers", name="This design",
                        marker=dict(color=AMBER, size=16, symbol="diamond"))
        st.plotly_chart(dark(fig, 360, barmode="group", yaxis_title="Facility $ / IT MW"), width="stretch")
        money_cols = [c for c in pt.columns if "$" in c]
        st.dataframe(pt.style.format({**{c: "${:,.0f}" for c in money_cols}, "Racks": "{:,.0f}",
                                      "GPUs/chips": "{:,.0f}", "GSF": "{:,.0f}", "PUE": "{:.2f}"}),
                     hide_index=True, width="stretch")
        st.markdown("**What is in the price, what moves it (11_SPEC_MOVES)**")
        st.dataframe(T["scope"], hide_index=True, width="stretch")
    with tabs[3]:
        st.subheader("4. Operational OpEx (single design)")
        k = st.columns(3)
        metric(k[0], "Annual OpEx", money(d["opex"]))
        metric(k[1], "Annual energy", money(sum(v for n, v in d["opex_items"].items() if "energy" in n)),
               f"PUE {d['pue']:.2f} (01_ASSUME8 r33)")
        metric(k[2], "OpEx per MW IT", money(d["opex"] / d["it_mw"]) + "/yr")
        st.dataframe(usd_table(T["opex"], ["USD / yr"]), hide_index=True, width="stretch")
        st.caption("Energy = IT kW × utilization × PUE × 8,760 h × $/kWh. Maintenance, staffing and insurance "
                   "are indicative (the workbook has no OpEx sheet); property tax is an input because the "
                   "workbook excludes tax.")
    with tabs[4]:
        st.subheader("5. Revenue & ROI (full greenfield investment)")
        k = st.columns(4)
        metric(k[0], "Annual revenue", money(d["revenue"]), f"${d['gpu_price']:.2f}/GPU-hr (indicative)")
        metric(k[1], "Net operating cash / yr", money(d["net_annual"]))
        metric(k[2], "Simple payback", yrs(d["simple_payback"]))
        metric(k[3], f"NPV @ 8%, {inputs['horizon_years']} yrs", money(d["npv"]))
        st.dataframe(T["roi"].style.format({"Value": "${:,.0f}"}), hide_index=True, width="stretch")
        fig = go.Figure()
        fig.add_scatter(y=pd.Series(d["cash_flows"]).cumsum(), name="Cumulative cash", line=dict(color=GREEN, width=3))
        st.plotly_chart(dark(fig, 300, xaxis_title="Year", yaxis_title="USD"), width="stretch")
        st.caption("Investment = greenfield CapEx + IT iron (racks × workbook IT $/rack) + AI fabric if included. "
                   f"IT refreshed every {ASSUMPTIONS['gpu_hw_life_years']} yrs at "
                   f"{ASSUMPTIONS['gpu_refresh_cost_factor']:.0%}. Revenue starts year 1; the "
                   f"~{d['schedule']['months_to_rfs']:.0f}-month build and financing are not modelled.")
    with tabs[5]:
        st.subheader("6. Workbook comparison: this design vs the LOW / RIGHT / HIGH band")
        fig = go.Figure()
        bt = T["band"]
        fig.add_bar(y=bt["$ per IT MW"], x=bt["Value"], orientation="h",
                    marker_color=[GREY] * 6 + [AMBER, GREEN])
        st.plotly_chart(dark(fig, 380, xaxis_title="$ per IT MW"), width="stretch")
        st.dataframe(bt.style.format({"Value": "${:,.0f}"}), hide_index=True, width="stretch")
        st.markdown(f"**Band check: {d['band_check']}** · benchmark trio")
        st.dataframe(usd_table(T["trio"], ["App", "Workbook RIGHT", "Difference"]), hide_index=True, width="stretch")
    with tabs[6]:
        st.subheader("7. Risks & schedule")
        st.markdown(f"**Schedule to ready-for-service: ~{d['schedule']['months_to_rfs']:.0f} months**")
        st.dataframe(T["schedule"], hide_index=True, width="stretch")
        st.markdown("**Greenfield risk register**")
        st.dataframe(T["risks"], hide_index=True, width="stretch")
        st.markdown("**Long-lead equipment (indicative lead times)**")
        st.dataframe(T["lead"], hide_index=True, width="stretch")
        st.markdown("---")
        render_narrative()
    return T


def report_parts(res, inputs, T):
    d = res["design"]
    return [
        "**Project type:** Greenfield new build from scratch (single design)",
        "## Headline",
        f"- Platform {d['platform']}, {d['kw_per_rack']:.0f} kW/rack, {d['racks']:,.0f} racks, {d['it_mw']:.1f} MW IT, "
        f"{d['cooling']}\n- Greenfield CapEx {money(d['capex'])} (facility {money(d['facility'])}, "
        f"{money(d['facility_per_mw'])}/MW IT, {d['band_check']})\n- Annual OpEx {money(d['opex'])}; "
        f"simple payback {yrs(d['simple_payback'])}; ~{d['schedule']['months_to_rfs']:.0f} months to RFS",
        "## 1. Assumptions", T["design"].to_markdown(index=False), T["register"].to_markdown(index=False),
        T["indicative"].to_markdown(index=False),
        "## 2. Greenfield CapEx", df_md(T["summary"], ["USD", "$ / IT MW"]),
        "### Reconciliation to workbook", df_md(T["recon"], ["Workbook", "App", "Difference"]),
        "## 3. Platform benchmark", T["platforms"].to_markdown(index=False),
        "## 4. OpEx", df_md(T["opex"], ["USD / yr"]),
        "## 5. Revenue & ROI", df_md(T["roi"], ["Value"]),
        "## 6. Workbook comparison", df_md(T["band"], ["Value"]),
        df_md(T["trio"], ["App", "Workbook RIGHT", "Difference"]),
        "## 7. Risks & schedule", T["schedule"].to_markdown(index=False), T["risks"].to_markdown(index=False),
    ]


def csv_tables(T):
    return {k: T[k] for k in ("design", "register", "indicative", "summary", "csi", "changes", "recon",
                              "platforms", "scope", "opex", "roi", "band", "trio", "schedule", "risks", "lead")}
