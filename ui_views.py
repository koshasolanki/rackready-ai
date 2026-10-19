"""RackReady AI - Streamlit views: summary, tabs and charts."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import buildcx as CX
import codes as CD
import costlines as CL
import engine as E
import guide as G
import procurement as PR
import report as R
from ui_common import AMBER, GREEN, GREY, dark, esc_md, metric

M = 1e6


def _mk(t, **kw):
    return st.markdown(esc_md(t), **kw)


def _cp(t, **kw):
    return st.caption(esc_md(t), **kw)


def _sc(t, **kw):
    return st.success(esc_md(t), **kw)


def _in(t, **kw):
    return st.info(esc_md(t), **kw)


def _df(df: pd.DataFrame, money_cols=None, pct_cols=(), num_cols=(), height=None):
    def safe(pattern):
        return lambda v: pattern.format(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v

    fmt = {}
    for c in df.columns:
        if c in pct_cols:
            fmt[c] = safe("{:.0%}")
        elif "per MW" in str(c) and "$M" in str(c):
            fmt[c] = safe("{:,.2f}")
        elif "$M" in str(c) or (money_cols and c in money_cols):
            fmt[c] = safe("{:,.1f}")
        elif c in num_cols:
            fmt[c] = safe("{:,.0f}")
        elif pd.api.types.is_float_dtype(df[c]):
            fmt[c] = (lambda v: (f"{v:,.0f}" if abs(v) >= 100 or float(v).is_integer() else f"{v:,.2f}")
                      if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else v)
    kw = {"hide_index": True, "width": "stretch"}
    if height:
        kw["height"] = height
    st.dataframe(df.style.format(fmt, na_rep=""), **kw)


# ------------------------------------------------------------------ summary
def summary(res):
    h = R.headline(res)
    rec = res["recommendation"]
    c = st.columns(4)
    off = len(h["excluded"])
    metric(c[0], h["label_total"], R.money(h["total"]),
           f"{off} line{'s' if off != 1 else ''} not ticked · all {R.money(h['total_all'])}")
    metric(c[1], h["label_per_mw"], f"{R.money(h['per_mw'])}/MW", f"{h['it_mw']:,.1f} MW IT")
    metric(c[2], "Payback (incl. IT)", R.yrs(h["payback"]), f"NPV {R.money(h['npv'])}")
    metric(c[3], "Ready for IT (months)", h["rfs_text"].replace("about ", "").replace(" months from start", ""),
           "months from start (approx.)")
    _sc(f"**Verdict: {rec['headline']}.** {rec['detail']}")
    _cp(f"{E.DISCLAIMER} 2026 US dollars. Key design: {R.key_design_line(res)}.")


def init_include_state():
    """Checkbox state for the 'Include in total' list (read by the app before the engine runs)."""
    for k in CL.KEYS:
        st.session_state.setdefault(f"inc_{k}", CL.DEFAULT_INCLUDE[k])


def include_from_state() -> dict:
    return {k: bool(st.session_state.get(f"inc_{k}", CL.DEFAULT_INCLUDE[k])) for k in CL.KEYS}


def cost_checklist(res):
    cl = R.cost_lines(res)
    mw = R.headline(res)["it_mw"]
    _mk("**Tick a line to include it.** Every total in the app, the PDFs, the exports and the narrative is the sum "
        "of the ticked lines.")
    hdr = st.columns([5, 1.4, 1.4, 4])
    for col, t in zip(hdr, ("Include in total", "$M", "$M / MW", "Source type")):
        col.caption(t)
    for r in cl["rows"]:
        c = st.columns([5, 1.4, 1.4, 4])
        c[0].checkbox(r["label"], key=f"inc_{r['key']}")
        c[1].markdown(f"{r['amount'] / M:,.1f}")
        c[2].markdown(f"{r['amount'] / M / mw:,.2f}")
        c[3].caption(esc_md(r["source"]))
    c = st.columns([5, 1.4, 1.4, 4])
    c[0].markdown("**Total project cost (ticked lines)**")
    c[1].markdown(f"**{cl['total'] / M:,.1f}**")
    c[2].markdown(f"**{cl['per_mw'] / M:,.2f}**")
    c[3].caption(esc_md(f"Every line ticked: {R.money(cl['total_all'])} ({R.money(cl['per_mw_all'])}/MW)"))
    _cp("Unticked by default: on-site/bridging power, GPU and server hardware and the AI network fabric (often "
        "bought by the IT owner). Payback still counts IT hardware unless you switch it off in Advanced.")


# ------------------------------------------------------------------ costs
def tab_costs(res):
    d = res["design"]
    _mk(f"**One new build** · {d['platform']['label']} · {d['racks']:,} racks · {d['it_mw']:,.1f} MW IT · "
                f"{d['cooling']}" + (f" ({E.D2C_NOTE})" if d["cooling_auto"] else ""))
    cost_checklist(res)
    g = R.group_table(res)
    fig = go.Figure(go.Bar(x=g["$M"], y=g["Group"], orientation="h", marker_color=GREEN,
                           text=[f"${v:,.0f}M ({s:.0%})" for v, s in zip(g["$M"], g["Share"])],
                           textposition="auto"))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(dark(fig, 340, title="Facility construction by trade group ($M)"), width="stretch")
    with st.expander("All 22 construction divisions"):
        _df(R.division_table(res), pct_cols=("Share",))
    if d["cost"]["changes"]:
        _mk("**Changes from the N+1, 48-hour-fuel basis** (priced from the design counts, +13% soft cost)")
        _df(pd.DataFrame([{"Change": a, "$M": c / M} for a, _, c in d["cost"]["changes"]]))
    with st.expander("How the facility cost is built"):
        _cp(f"Basis: {d['platform']['label']} facility cost {R.money(d['platform']['rate'])}/MW IT "
               f"(range {R.money(d['platform']['low'])}-{R.money(d['platform']['high'])}) in 2026 dollars, N. Virginia, "
               f"N+1, including general conditions and 4% contingency; then contingency set to "
               f"{d['cost']['contingency_pct']:.0%}, location factor {d['cost']['region_factor']:.2f}, owner costs and "
               "escalation. The cost lines above split this facility cost (they add back to it exactly) and add "
               "spares, racks where the platform price excludes them, bridging power and IT.")


# ------------------------------------------------------------------ future-ready
def tab_future(res):
    f = R.horizon(res)
    _cp(f"Your day-one design: {R.day_one_density(res)}. " + R.ROADMAP_TEXT)
    if not f.get("active"):
        _in(f["reason"] + " Choose a 5, 10 or 15-year horizon in the sidebar to price future-proofing.")
        return
    _mk(f"**Horizon: {f['horizon']}.** {f['horizon_text']} **{E.target_sentence(f)}**, same {f['target_mw']:,.1f} MW IT"
                + (f" (+{f['spare_pct']:.0%} spare utility capacity)" if f["spare_pct"] else "") +
                f", about {f['target_racks']:,.0f} racks, {f['target_cooling']}.")
    t = R.future_table(res)
    _df(t)
    fig = go.Figure(go.Bar(x=t["Path"], y=t["Present cost $M (probability-weighted)"],
                           marker_color=[GREEN if b else GREY for b in t["Best"]],
                           text=[f"${v:,.0f}M" for v in t["Present cost $M (probability-weighted)"]], textposition="auto"))
    st.plotly_chart(dark(fig, 300, title="Present cost of getting to the target ($M)"), width="stretch")
    with st.expander("Method and assumptions"):
        _cp(f"Facility-only comparison (IT hardware and revenue after the switch are the same on every path). "
               f"Later works escalated at {float(res['inputs'].get('escalation') or 0):.0%}/yr and discounted at 8%; "
               f"weighted by a {f['probability']:.0%} probability that the target is deployed at this site. Retrofit "
               "= 1.35x premium + 6% demolition + 4 months lost margin; provisions = pre-installed share now, the rest "
               "at 1.10x with 1 month lost margin; full build carries 2%/yr upkeep on idle capacity. All are assumptions "
               "you can change in Advanced.")
    _mk("**Day one vs future target: what changes**")
    _df(R.compare_table(res), num_cols=("Day one", "Future target"))
    _mk(f"**Provisions to build in now ({len(f['provisions'])})**")
    _df(pd.DataFrame([{"Provision": p["provision"], "What": p["what"], "When": p["when"], "Why": p["why"]}
                      for p in f["provisions"]]))
    with st.expander("Upgrade cost by item and pre-install share"):
        _df(R.future_rows_table(res), pct_cols=("Pre-install share",))


# ------------------------------------------------------------------ design calcs
def tab_design(res):
    options = {"Day-one design": res["design"]["design"]}
    f = R.horizon(res)
    if f.get("active"):
        options[f"Future target ({f['target_kw']:,.0f} kW/rack)"] = f["design_T"]
    pick = st.radio("Design case", list(options), horizontal=True, key="design_case",
                    help="Choose which design the calculations below describe.")
    dz = options[pick]
    _cp("Formula, inputs and result for each step, US units with SI alongside. Standard relations: "
               "I = P / (sqrt3 x V x PF), Q = P / (rho x cp x dT), 1 ton = 3.517 kW, PUE as an annual energy ratio. "
               "Rules: no fixed 'IT x 2' sizing, liquid never captures 100%, air sized only for the residual heat.")
    df = R.design_table(dz)
    for sec, g in df.groupby("Section", sort=False):
        _mk(f"**{sec}**")
        _df(g.drop(columns=["Section"]))


# ------------------------------------------------------------------ operations
def tab_ops(res):
    i = res["inputs"]
    cases = {"Design": res["design"]}
    cols = st.columns(len(cases))
    for col, (name, x) in zip(cols, cases.items()):
        with col:
            _mk(f"**{name}**")
            _df(R.opex_table(x))
            _mk(f"Revenue year 1 **{R.money(x['revenue'])}** = {x['gpus']:,} GPUs x ${x['gpu_price']:.2f}/GPU-hr x "
                        f"{i['utilization']:.0%} x 8,760 h · Net year 1 **{R.money(x['revenue'] - x['opex'])}** · "
                        f"NPV **{R.money(x['npv'])}** · payback **{R.yrs(x['payback'])}**")
    fig = go.Figure()
    for (name, x), colr in zip(cases.items(), (GREEN, GREY)):
        fig.add_trace(go.Scatter(y=pd.Series(x["cash_flows"]).cumsum() / M, name=name, line_color=colr))
    fig.update_xaxes(title="Year")
    st.plotly_chart(dark(fig, 300, title="Cumulative cash flow incl. IT hardware ($M)"), width="stretch")
    with st.expander("Operations readiness: handover, change control, incident levels, metrics"):
        for k, items in CX.OPS_READINESS.items():
            _mk(f"**{k}**")
            for x in items:
                _mk(f"- {x}")
    _cp(f"Investment at year 0 = facility + IT hardware. GPU rental price change "
               f"{float(i.get('price_change') or 0):+.0%}/yr between refreshes, IT refresh every 5 years at 70% of the "
               "original cost, 8% discount rate (assumptions). Payback counts from ready-for-service, not from the "
               "start of design.")


# ------------------------------------------------------------------ schedule & risks
TRACK_COLOR = {"Pre-construction": GREY, "Build": GREEN, "Waiting": "#E5484D", "Commissioning": AMBER,
               "Closeout": "#5B8DEF"}


def _gantt(S):
    ph = [p for p in S["phases"] if p["kind"] != "milestone"]
    fig = go.Figure()
    for tr, col in TRACK_COLOR.items():
        rows = [p for p in ph if p["track"] == tr]
        if rows:
            fig.add_trace(go.Bar(y=[p["phase"][:60] for p in rows], x=[max(p["dur"], 0.15) for p in rows],
                                 base=[p["start"] for p in rows], orientation="h", name=tr, marker_color=col,
                                 hovertext=[f"months {p['start']:.1f}-{p['end']:.1f}. {p['note']}" for p in rows]))
    for p in S["phases"]:
        if p["kind"] == "milestone":
            fig.add_vline(x=p["start"], line_dash="dot", line_color="#DDDDDD")
            fig.add_annotation(x=p["start"], y=1.02, yref="paper", text=p["phase"].split(" (")[0].split(" /")[0],
                               showarrow=False, font_size=10)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Months from project start")
    return dark(fig, 120 + 26 * len(ph), title="Phase schedule", barmode="overlay")


def tab_schedule(res):
    S = res["cx"]["schedule"]
    _mk(f"**Ready for IT (substantial completion): {S['range_text']}.** "
        f"Critical path: {S['critical_path']}. Notice to proceed about month {S['ntp']:.0f}; build "
        f"{S['build_months']:.1f} months{' (auto from MW)' if S['build_months_auto'] else ''}; energization starts "
        f"about month {S['energization']:.0f}; commissioning about month {S['cx_start']:.0f}.")
    st.plotly_chart(_gantt(S), width="stretch")
    with st.expander("Schedule basis"):
        _cp("Months count from the start (go decision). Range: shortest published lead times with no weather "
            "allowance, to the longest lead times with 10% more weather and productivity allowance. "
            f"Work week {S['overtime_hours']} h (field-work factor {S['overtime_factor']:.2f}), weather "
        f"+{S['weather']:.0%} on exterior work, congestion +{S['congestion']:.0%} on interior work and commissioning. "
        "Overtime does not compress commissioning. Build duration auto-scales with MW when Build months = 0.")
    t = R.schedule_table(res["design"]["schedule"])
    fig = go.Figure(go.Bar(x=t["Months"], y=t["Driver"], orientation="h",
                           marker_color=[GREEN if c else GREY for c in t["Critical"]],
                           text=[f"{m:.0f} mo" for m in t["Months"]], textposition="auto"))
    st.plotly_chart(dark(fig, 240, title="What sets the finish: completion month if each constraint acted alone"),
                    width="stretch")
    _mk("**When to order** (reverse schedule from when each item is needed on site)")
    _df(R.order_by_table(res))
    with st.expander("How the order months are worked out"):
        _cp(f"Chain per item: specification and RFQ {CX.PROCUREMENT['spec_rfq']} wk + bids {CX.PROCUREMENT['bids']} wk + "
        f"award/PO {CX.PROCUREMENT['po']} wk + submittals {CX.SUBMITTAL_WEEKS} wk + quoted lead + "
        f"{CX.PROCUREMENT['staging']} wk staging, plus a {CX.PROCUREMENT['buffer_pct']:.0%} buffer on submittals and lead. "
        "'Order before NTP' means the PO must be placed before construction starts (owner-direct purchase or an "
        "early-release package). " + CX.TURBINE_NOTE)
    _mk("**Risk register** (auto-enabled from your inputs; impact in months, no probabilities)")
    show_all = st.toggle("Show inactive risks too", False, key="risk_all")
    _df(R.risk_table(res, active_only=not show_all))
    _mk("**How to avoid delays**")
    for x in G.HOW_TO_AVOID:
        _mk(f"- {x}")
    with st.expander("Common causes of delay and proven fixes (public reporting)"):
        _df(R.delays_table())
    with st.expander("Long-lead equipment, 2026 ranges"):
        _df(R.long_lead_table())


# ------------------------------------------------------------------ build & commission
def tab_build(res):
    cx = res["cx"]
    T = R.cx_tables(res)
    st.warning(esc_md("🛑 " + CX.HARD_STOP))
    _mk("**Commissioning levels L1-L5**")
    _df(T["cx_levels"])
    lb = cx["load_banks"]
    c = st.columns(4)
    metric(c[0], "Halls for IST", f"{lb['halls']}", f"{lb['hall_mw']:,.1f} MW each")
    metric(c[1], "Liquid load banks / hall", f"{lb['liquid_units_250kw']}", f"{lb['liquid_mw']:,.1f} MW (250 kW units)")
    metric(c[2], "Air load banks / hall", f"{lb['air_units_1mw']}", f"{lb['air_mw']:,.1f} MW (1 MW units)")
    metric(c[3], "Generator test", "2 h", "NFPA 110: 30% / 50% / 100%")
    for n in lb["notes"]:
        _mk(f"- {n}")
    _mk("**Integrated systems test: failure scenarios**")
    _df(T["ist_scenarios"])
    _mk("**Handoff feeds**: scope boundary, spec, test, common failure and prevention")
    _df(T["handoff_feeds"])
    with st.expander("IT-readiness sequence (30 steps, in order)"):
        _df(T["it_readiness"], height=420)
    _mk("**QA checklists**")
    for k, items in CX.CHECKLISTS.items():
        with st.expander(k):
            for x in items:
                _mk(f"- [ ] {x}")
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇ Checklists (PDF)", R.checklist_pdf(res), file_name="rackready_build_checklists.pdf",
                       mime="application/pdf", width="stretch", key="dl_cx_pdf",
                       help="Multi-page field checklist: hard stop, order-by months, L1-L5, IST, feeds, QA lists.")
    md = "\n\n".join([f"# Build & commission: {res['inputs']['project_name']}", CX.HARD_STOP] +
                       [f"## {k.replace('_', ' ').title()}\n\n{v.to_markdown(index=False)}" for k, v in T.items()])
    c2.download_button("⬇ Build & commission (Markdown)", md, file_name="rackready_build_commission.md",
                       mime="text/markdown", width="stretch", key="dl_cx_md")
    c3.download_button("⬇ Checklists (CSV)", T["checklists"].to_csv(index=False), file_name="rackready_checklists.csv",
                       mime="text/csv", width="stretch", key="dl_cx_csv")


# ------------------------------------------------------------------ assumptions & sources
SOURCES = [
    ("Global data center cost outlooks, 2026 (commercial real-estate advisors)", "Average shell & core about "
     "$11.3M/MW (air-cooled), liquid cooling adds about 10%, AI interiors can reach $25M/MW; US & Canada greenfield "
     "all-in about $17.6M/MW excluding IT; grid waits above 4 years in primary markets"),
    ("Data center construction cost index, 2025-26 (cost consultancy)", "AI builds carry a 7-10% premium; about "
     "5.5% annual construction inflation"),
    ("Global data center industry survey, 2025", "Average PUE 1.54; new large sites about 1.44"),
    ("GB300 NVL72 published specifications (platform and system makers)", "132-140 kW operating, up to 155 kW peak, "
     "about 3,300-3,480 lb, about 90% liquid-cooled"),
    ("Public GPU roadmap, 2025", "Vera Rubin (2H 2026), Rubin Ultra NVL576 Kyber about 600 kW (2H 2027), 800 VDC "
     "for MW-class racks"),
    ("US government energy statistics, 2026", "US industrial electricity about 9 cents/kWh"),
    ("2025 transformer supply-chain study and 2026 procurement surveys", "Large power transformers about 128 weeks; "
     "MV switchgear 52-104 weeks; large diesel gensets 62-110 weeks"),
    ("Public GPU rental trackers, Oct 2026", "H100 about $2.4-3.6/GPU-hr; B200 $3.7-8.6; GB200/GB300 $6-18"),
    ("ASHRAE TC 9.9 thermal and liquid cooling guidance", "Recommended inlet 18-27 C for all air classes with "
     "dew-point limits; liquid classes W17-W45 and W+"),
    ("US codes and standards (NFPA, ICC, ASHRAE, TIA, BICSI, IEEE, UL, OSHA, EPA)",
     "Latest editions listed in the Codes & procurement tab; the design calculations follow their rules"),
]


def tab_assumptions(res):
    i = res["inputs"]
    _mk("**Benchmark checks**: each key result against a public range")
    _df(R.checks_table(res))
    _mk("**Main assumptions** (change them in the sidebar under Advanced)")
    x = res["design"]
    rows = [("Location factor", f"{E.REGIONS[i['region']]['factor']:.2f} vs N. Virginia", "Market cost indices; assumption"),
            ("Contingency", f"{float(i['contingency']):.0%}", "Planning stage; assumption"),
            ("Escalation", f"{float(i.get('escalation') or 0):.0%}/yr to construction mid-point", "Cost index 2025-26 about 5.5%"),
            ("Power price", f"${x['power_cost']:.3f}/kWh", "Regional default; US government energy statistics"),
            ("GPU rental", f"${x['gpu_price']:.2f}/GPU-hr at {i['utilization']:.0%} utilization", "Contract-rate assumption within public ranges"),
            ("Rental price change", f"{float(i.get('price_change') or 0):+.0%}/yr", "Assumption"),
            ("Land", f"${R._land(i):,.0f}/acre", "Indicative powered-land price; assumption"),
            ("Discount rate", "8%", "Assumption"),
            ("Cooling rule", "Direct-to-chip liquid above 45 kW/rack", "Air about 30 kW, rear-door about 45 kW practical limits")]
    _df(pd.DataFrame(rows, columns=["Item", "Value", "Basis"]))
    _mk("**Estimate accuracy**")
    _cp("±30–50%: " + CX.ESTIMATE_LABEL.split(": ", 1)[1])
    _mk("**Stage gates 0-7**")
    _df(R.cx_tables(res)["stage_gates"])
    _mk("**Specification quick reference** (current codes and standards)")
    _df(R.cx_tables(res)["spec_reference"], height=420)
    for k, items in CX.PLANNING_NOTES.items():
        with st.expander(k):
            for x in items:
                _mk(f"- {x}")
    _mk("**GPU platforms**")
    _df(R.platform_table())
    _mk("**Public sources**")
    for a, b in SOURCES:
        _mk(f"- **{a}**: {b}")
    _cp("Every number, range and source link: docs/VERIFICATION.md in the repository.")


# ------------------------------------------------------------------ codes & procurement
def tab_codes(res):
    _mk("**Codes and standards to follow** (latest US editions, each checked on the publisher's site)")
    _cp(CD.CODES_NOTE)
    df = R.codes_table()
    for g, grp in df.groupby("Group", sort=False):
        _mk(f"**{g}**")
        _df(grp.drop(columns=["Group"]))
    _mk("**Confirm locally**")
    for x in CD.CONFIRM_LOCALLY:
        _mk(f"- [ ] {x}")
    st.divider()
    _mk("**US procurement: long-lead packages**")
    _cp(PR.TARIFF_2026)
    _df(R.procurement_table())
    _mk("**Verified suppliers** (each backed by a public source; full links in docs/VERIFICATION.md)")
    _in(PR.DISCLAIMER)
    _df(R.supplier_table().drop(columns=["URL"]))

