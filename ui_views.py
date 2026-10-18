"""RackReady AI - Streamlit views: summary, tabs and charts."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import engine as E
import platforms as PL
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
    metric(c[0], h["label_total"], R.money(h["total"]), f"+ {R.money(h['it_total'])} IT hardware")
    metric(c[1], h["label_per_mw"], f"{R.money(h['per_mw'])}/MW", f"{h['it_mw']:,.1f} MW IT")
    metric(c[2], "Payback (incl. IT)", R.yrs(h["payback"]), f"NPV {R.money(h['npv'])}")
    metric(c[3], "Ready for service", f"~{h['rfs']:.0f} months", "critical path in Schedule tab")
    _sc(f"**Recommendation: {rec['headline']}.** {rec['detail']}")
    _cp("Key design: " + R.key_design_line(res))


# ------------------------------------------------------------------ costs
def tab_costs(res):
    if res["mode"] == "greenfield":
        d = res["design"]
        _mk(f"**One new build** · {d['platform']['label']} · {d['racks']:,} racks · {d['it_mw']:,.1f} MW IT · "
                    f"{d['cooling']}" + (f" ({E.D2C_NOTE})" if d["cooling_auto"] else ""))
        _df(R.cost_table(res))
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
        _cp(f"Basis: {d['platform']['label']} facility cost {R.money(d['platform']['rate'])}/MW IT "
                   f"(range {R.money(d['platform']['low'])}-{R.money(d['platform']['high'])}) in 2026 dollars, N. Virginia, "
                   f"N+1, including general conditions and 4% contingency; then contingency set to "
                   f"{d['cost']['contingency_pct']:.0%}, location factor {d['cost']['region_factor']:.2f}, owner costs and "
                   "escalation. IT hardware is separate.")
        return
    cur, f, up = res["current"], res["future"], res["upgrade"]
    _mk(f"**Existing building** · {cur['racks']:,} racks · current {cur['kw']:.0f} kW/rack ({cur['cooling']}) "
                f"vs future-ready {f['kw']:.0f} kW/rack ({f['cooling']})")
    _df(R.cost_table(res))
    sysn = list(f["systems"])
    fig = go.Figure([go.Bar(name="Current", x=sysn, y=[cur["systems"][k] / M for k in sysn], marker_color=GREY),
                     go.Bar(name="Future-ready", x=sysn, y=[f["systems"][k] / M for k in sysn], marker_color=GREEN)])
    st.plotly_chart(dark(fig, 340, barmode="group", title="Fit-out cost by system ($M)"), width="stretch")
    _mk(f"**Build current now, retrofit in year {up['year']}?**")
    _df(pd.DataFrame([
        {"Option": "Future-ready fit-out now", "Day one $M": up["day_one_capex"] / M, "Retrofit $M": 0.0,
         "Downtime $M": 0.0, "NPV $M": up["npv_a"] / M},
        {"Option": f"Current now + retrofit in year {up['year']}", "Day one $M": cur["capex"] / M,
         "Retrofit $M": up["retrofit_capex"] / M, "Downtime $M": up["downtime_cost"] / M, "NPV $M": up["npv_b"] / M}]))
    _cp(f"Retrofit priced at 1.35x new work in a live building, 6% demolition, partial reuse of existing "
               f"systems and {up['downtime_months']} months of lost revenue (assumptions). Recommendation: "
               f"**{up['recommended']}**.")
    ca = pd.Series(up["flows_a"]).cumsum() / M
    cb = pd.Series(up["flows_b"]).cumsum() / M
    fig = go.Figure([go.Scatter(y=ca, name="Future-ready now", line_color=GREEN),
                     go.Scatter(y=cb, name="Retrofit later", line_color=AMBER)])
    fig.update_xaxes(title="Year")
    st.plotly_chart(dark(fig, 300, title="Cumulative cash flow incl. IT ($M)"), width="stretch")


# ------------------------------------------------------------------ future-ready
def tab_future(res):
    f = R.horizon(res)
    _mk("Roadmap densities: today's GPU racks 40-60 kW · GB200/GB300 NVL72 about 120-140 kW (shipping) · "
                "Vera Rubin NVL144 about 190-230 kW (announced, 2H 2026) · Rubin Ultra NVL576 Kyber about 600 kW "
                "(announced, 2H 2027, 800 VDC) · 1 MW racks (speculative).")
    if not f.get("active"):
        _in(f["reason"] + " Choose a 5, 10 or 15-year horizon in the sidebar to price future-proofing.")
        return
    _mk(f"**Horizon: {f['horizon']}.** {f['horizon_text']} Target **{f['target_kw']:,.0f} kW/rack** installed in "
                f"**year {f['year']}**, same {f['target_mw']:,.1f} MW IT"
                + (f" (+{f['spare_pct']:.0%} spare utility capacity)" if f["spare_pct"] else "") +
                f", about {f['target_racks']:,.0f} racks, {f['target_cooling']}.")
    t = R.future_table(res)
    _df(t)
    fig = go.Figure(go.Bar(x=t["Path"], y=t["Present cost $M (probability-weighted)"],
                           marker_color=[GREEN if b else GREY for b in t["Best"]],
                           text=[f"${v:,.0f}M" for v in t["Present cost $M (probability-weighted)"]], textposition="auto"))
    st.plotly_chart(dark(fig, 300, title="Present cost of getting to the target ($M)"), width="stretch")
    _cp(f"Facility-only comparison (IT hardware and revenue after the switch are the same on every path). "
               f"Later works escalated at {float(res['inputs'].get('escalation') or 0):.0%}/yr and discounted at 8%; "
               f"weighted by a {f['probability']:.0%} probability that the target is deployed at this site. Retrofit "
               "= 1.35x premium + 6% demolition + 4 months lost margin; provisions = pre-installed share now, the rest "
               "at 1.10x with 1 month lost margin; full build carries 2%/yr upkeep on idle capacity. All are assumptions "
               "you can change in Advanced.")
    _mk("**Day one vs future target: what changes**")
    _df(R.compare_table(res), num_cols=("Day one", "Future target"))
    _mk("**Provisions to build in now**")
    for p in f["provisions"]:
        _mk(f"- **{p['provision']}**: {p['what']} _{p['when']}._")
    with st.expander("Upgrade cost by item and pre-install share"):
        _df(R.future_rows_table(res), pct_cols=("Pre-install share",))


# ------------------------------------------------------------------ design calcs
def tab_design(res):
    options = {}
    if res["mode"] == "greenfield":
        options["Day-one design"] = res["design"]["design"]
    else:
        options["Future-ready fit-out"] = res["future"]["design"]
        options["Current racks"] = res["current"]["design"]
    f = R.horizon(res)
    if f.get("active"):
        options[f"Future target ({f['target_kw']:,.0f} kW/rack)"] = f["design_T"]
    pick = st.radio("Design case", list(options), horizontal=True, key="design_case",
                    help="Choose which design the calculations below describe.")
    dz = options[pick]
    _cp("Step by step: formula, inputs and result, in US units with SI alongside. Standard relations: "
               "I = P / (sqrt3 x V x PF), Q = P / (rho x cp x dT), 1 ton = 3.517 kW, PUE as an annual energy ratio. "
               "Rules: no fixed 'IT x 2' sizing, liquid never captures 100%, air sized only for the residual heat.")
    df = R.design_table(dz)
    for sec, g in df.groupby("Section", sort=False):
        _mk(f"**{sec}**")
        _df(g.drop(columns=["Section"]))


# ------------------------------------------------------------------ operations
def tab_ops(res):
    i = res["inputs"]
    if res["mode"] == "greenfield":
        cases = {"Design": res["design"]}
    else:
        cases = {"Future-ready": res["future"], "Current": res["current"]}
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
    _cp(f"Investment at year 0 = facility + IT hardware. GPU rental price change "
               f"{float(i.get('price_change') or 0):+.0%}/yr between refreshes, IT refresh every 5 years at 70% of the "
               "original cost, 8% discount rate (assumptions). Payback counts from ready-for-service, not from the "
               "start of design.")


# ------------------------------------------------------------------ schedule & risks
def tab_schedule(res):
    sch = res["design"]["schedule"] if res["mode"] == "greenfield" else res["schedule"]
    _mk(f"**Ready for service in about {sch['months_to_rfs']:.0f} months.** Critical path: {sch['critical_path']}.")
    t = R.schedule_table(sch)
    fig = go.Figure(go.Bar(x=t["Months"], y=t["Driver"], orientation="h",
                           marker_color=[GREEN if c else GREY for c in t["Critical"]],
                           text=[f"{m:.0f} mo" for m in t["Months"]], textposition="auto"))
    st.plotly_chart(dark(fig, 260, title="Schedule drivers (months)"), width="stretch")
    _mk("**Long-lead equipment**")
    _df(R.long_lead_table())
    _mk("**Key risks**")
    v = R.main_design(res)["v"]
    risks = ["Utility interconnection: large new loads often wait years; get a committed energization date.",
             "Transformers and generators: reserve factory slots at or before design start.",
             f"Floor loading: about {v['rack_psf']:,.0f} psf on the rack footprint vs a 250 psf typical raised-floor "
             "rating; slab-on-grade or a strengthened structure is needed above that.",
             "Liquid cooling: water quality, leak detection, CDU redundancy and commissioning of the cooling loop.",
             "Roadmap risk: announced rack power, weight and price can change; keep provisions flexible.",
             "Refrigerants: low-GWP (below 700) rules for new chillers in the US from 2027."]
    for r_ in risks + res["warnings"]:
        _mk(f"- {r_}")


# ------------------------------------------------------------------ assumptions & sources
SOURCES = [
    ("JLL, 2026 Global Data Center Outlook", "Average shell & core $11.3M/MW (air-cooled), liquid cooling adds about "
     "10%, AI fit-out can reach $25M/MW; grid waits above 4 years in primary markets"),
    ("Cushman & Wakefield, Data Center Development Cost Guide 2026", "US & Canada greenfield all-in average "
     "$17.6M/MW (excluding IT); costs up about 21% since 2024"),
    ("Turner & Townsend, Data Centre Construction Cost Index 2025-26", "Market cost per watt; AI builds carry a "
     "7-10% premium; about 5.5% annual inflation"),
    ("Uptime Institute, Global Data Center Survey 2025", "Average PUE 1.54; new large sites about 1.44"),
    ("NVIDIA and OEM (HPE, Lenovo, Supermicro) GB300 NVL72 specifications", "132-140 kW operating, up to 155 kW peak, "
     "about 3,300-3,480 lb, about 90% liquid-cooled"),
    ("NVIDIA GTC 2025 / NVIDIA technical blog 2025", "Vera Rubin (2H 2026), Rubin Ultra NVL576 Kyber about 600 kW "
     "(2H 2027), 800 VDC for MW-class racks"),
    ("US EIA, Electric Power Monthly 2026", "US industrial electricity about 9 cents/kWh"),
    ("Wood Mackenzie, 2025 transformer supply study", "Power transformer lead time about 128 weeks"),
    ("Public GPU rental trackers, Oct 2026", "H100 about $2.4-3.6/GPU-hr; B200 $3.7-8.6; GB200/GB300 $6-18"),
    ("ASHRAE TC 9.9 liquid cooling guidance", "Facility and technology cooling loops, warm-water temperatures"),
]


def tab_assumptions(res):
    i = res["inputs"]
    _mk("**Benchmark checks**: each key result against a public range")
    _df(R.checks_table(res))
    _mk("**Main assumptions** (change them in the sidebar under Advanced)")
    x = res["design"] if res["mode"] == "greenfield" else res["future"]
    rows = [("Location factor", f"{E.REGIONS[i['region']]['factor']:.2f} vs N. Virginia", "Market cost indices (JLL, T&T); assumption"),
            ("Contingency", f"{float(i['contingency']):.0%}" if res["mode"] == "greenfield" else "10%", "Planning stage; assumption"),
            ("Escalation", f"{float(i.get('escalation') or 0):.0%}/yr to construction mid-point", "T&T 2025-26 about 5.5%"),
            ("Power price", f"${x['power_cost']:.3f}/kWh", "Regional default; EIA for US"),
            ("GPU rental", f"${x['gpu_price']:.2f}/GPU-hr at {i['utilization']:.0%} utilization", "Contract-rate assumption within public ranges"),
            ("Rental price change", f"{float(i.get('price_change') or 0):+.0%}/yr", "Assumption"),
            ("Land", f"${R._land(i):,.0f}/acre", "Indicative powered-land price; assumption"),
            ("Discount rate", "8%", "Assumption"),
            ("Cooling rule", "Direct-to-chip liquid above 45 kW/rack", "Air about 30 kW, rear-door about 45 kW practical limits")]
    _df(pd.DataFrame(rows, columns=["Item", "Value", "Basis"]))
    _mk("**GPU platforms**")
    _df(R.platform_table())
    _mk("**Public sources**")
    for a, b in SOURCES:
        _mk(f"- **{a}**: {b}")
    _cp(f"{E.DISCLAIMER} Full list of numbers, ranges and sources: docs/VERIFICATION.md.")
