"""
RackReady AI - tables and exports (Markdown, CSV, one-page PDF) built from the engine result.
Used by the Streamlit UI and by the downloads so the app and the files always agree.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

import engine as E
import platforms as PL

M = 1e6


def money(x) -> str:
    if x is None:
        return "n/a"
    a = abs(x)
    if a >= 1e9:
        return f"${x / 1e9:,.2f}B"
    if a >= 1e6:
        return f"${x / 1e6:,.1f}M"
    if a >= 1e3:
        return f"${x / 1e3:,.0f}K"
    return f"${x:,.0f}"


def yrs(x) -> str:
    return "not within period" if x is None else f"{x:.1f} years"


def val(step) -> str:
    v, u = step["value"], step["unit"]
    if isinstance(v, str):
        return v
    if u in ("units", "racks", "units per row", "taps", "modules", "CDUs", "gal", "sf", "A"):
        d = 0
    elif u in ("", "x"):
        d = 2 if abs(v) < 10 else 0
    elif abs(v) < 10:
        d = 2
    elif abs(v) < 100:
        d = 1
    else:
        d = 0
    return f"{v:,.{d}f} {u}".strip()


# ------------------------------------------------------------------ views over the result
def main_design(res):
    return res["design"]["design"] if res["mode"] == "greenfield" else res["future"]["design"]


def horizon(res):
    return res["future"] if res["mode"] == "greenfield" else res["future_paths"]


def headline(res) -> dict:
    """Numbers for the one-screen summary."""
    i = res["inputs"]
    if res["mode"] == "greenfield":
        d = res["design"]
        return {"total": d["capex"], "per_mw": d["capex_per_mw"], "payback": d["payback"],
                "npv": d["npv"], "it_total": d["it_total"], "it_mw": d["it_mw"], "racks": d["racks"],
                "kw": d["kw"], "cooling": d["cooling"], "platform": d["platform"]["label"],
                "rfs": d["schedule"]["months_to_rfs"], "label_total": "Total project cost (facility)",
                "label_per_mw": "Cost per MW IT (all-in facility)"}
    f = res["future"]
    return {"total": f["capex"], "per_mw": f["capex_per_mw"], "payback": f["payback"], "npv": f["npv"],
            "it_total": f["it_total"], "it_mw": f["it_mw"], "racks": f["racks"], "kw": f["kw"],
            "cooling": f["cooling"], "platform": res["platform"]["label"],
            "rfs": res["schedule"]["months_to_rfs"], "label_total": "Future-ready fit-out cost",
            "label_per_mw": "Fit-out cost per MW IT"}


def key_design_line(res) -> str:
    v = main_design(res)["v"]
    return (f"{v['service_mva']:,.0f} MVA utility service · {v['gens']:,.0f} x 3 MW generators · "
            f"{v['ups_modules']:,.0f} x 1 MW UPS modules · {v['cool_tons']:,.0f} tons cooling "
            f"({v['cdus']:,.0f} CDUs) · {v['gross_sf']:,.0f} sf building · PUE {v['pue']:.2f}")


def _land(i):
    return E._land_price(i)


# ------------------------------------------------------------------ tables
def design_table(dz) -> pd.DataFrame:
    return pd.DataFrame([{"Section": s["section"], "Item": s["item"], "Result": val(s), "SI / also": s["si"],
                          "Formula": s["formula"], "Inputs": s["inputs"], "Note": s["note"]}
                         for s in dz["steps"]])


def cost_table(res) -> pd.DataFrame:
    if res["mode"] == "greenfield":
        d = res["design"]
        rows = [{"Cost line": k, "$M": v / M, "$M per MW IT": v / M / d["it_mw"]} for k, v in d["lines"].items()]
        rows.append({"Cost line": "Total project cost (facility)", "$M": d["capex"] / M,
                     "$M per MW IT": d["capex_per_mw"] / M})
        rows.append({"Cost line": "IT hardware: GPU racks + AI network (separate)", "$M": d["it_total"] / M,
                     "$M per MW IT": d["it_total"] / M / d["it_mw"]})
        return pd.DataFrame(rows)
    cur, f = res["current"], res["future"]
    rows = []
    for k in f["systems"]:
        rows.append({"Cost line": k, "Current $M": cur["systems"][k] / M, "Future-ready $M": f["systems"][k] / M})
    for lbl, key in (("Soft costs (design, permits, Cx) 14%", "soft"), ("Contingency 10%", "contingency"),
                     ("Escalation to mid-point", "escalation"), ("Total fit-out cost", "capex")):
        rows.append({"Cost line": lbl, "Current $M": cur[key] / M, "Future-ready $M": f[key] / M})
    rows.append({"Cost line": "Cost per MW IT", "Current $M": cur["capex_per_mw"] / M,
                 "Future-ready $M": f["capex_per_mw"] / M})
    rows.append({"Cost line": "IT hardware (separate)", "Current $M": cur["it_total"] / M,
                 "Future-ready $M": f["it_total"] / M})
    return pd.DataFrame(rows)


def division_table(res) -> pd.DataFrame:
    d = res["design"]
    rows = [{"Group": PL.group_of(k), "Division": k, "$M": v / M,
             "Share": v / sum(d["cost"]["divisions"].values())} for k, v in d["cost"]["divisions"].items()]
    return pd.DataFrame(rows)


def group_table(res) -> pd.DataFrame:
    df = division_table(res)
    g = df.groupby("Group", sort=False)[["$M", "Share"]].sum().reset_index()
    return g


def future_table(res) -> pd.DataFrame:
    f = horizon(res)
    if not f.get("active"):
        return pd.DataFrame()
    return pd.DataFrame([{"Path": x["path"], "Day one $M": x["day1"] / M,
                          f"Year {f['year']} works $M (escalated)": x["later_nominal"] / M,
                          "Downtime (months)": x["downtime_months"], "Lost margin $M": x["downtime_cost"] / M,
                          "Idle-capacity carrying $M (PV)": x["idle_carry"] / M,
                          "Present cost $M (probability-weighted)": x["pv_total"] / M,
                          "Best": "✓" if x["path"] == f["best"] else ""} for x in f["paths"]])


def future_rows_table(res) -> pd.DataFrame:
    f = horizon(res)
    if not f.get("active"):
        return pd.DataFrame()
    return pd.DataFrame([{"Item": r["item"], "Today $M": r["today"] / M, "At target $M": r["future"] / M,
                          "Upgrade $M": r["delta"] / M, "Pre-install share": r["share"],
                          "Provision now $M": r["delta"] * r["share"] / M} for r in f["rows"] if r["delta"] > 0])


def compare_table(res) -> pd.DataFrame:
    """Day-one vs future-target design values side by side."""
    f = horizon(res)
    if not f.get("active"):
        return pd.DataFrame()
    v0, vT = main_design(res)["v"], f["design_T"]["v"]
    rows = [("Rack density", "kW/rack", headline(res)["kw"], f["target_kw"]),
            ("Racks", "racks", v0["taps"] / 2, vT["taps"] / 2),
            ("Utility service", "MVA", v0["service_mva"], vT["service_mva"]),
            ("Generators (3 MW)", "units", v0["gens"], vT["gens"]),
            ("Rack feed current", "A", v0["rack_amps"], vT["rack_amps"]),
            ("Busway runs per 10-rack row", "runs", v0["busway_runs"], vT["busway_runs"]),
            ("Busway rating per run", "A", v0["busway_rating"], vT["busway_rating"]),
            ("CDUs", "units", v0["cdus"], vT["cdus"]),
            ("Liquid flow (TCS)", "L/s", v0["tcs_lps"], vT["tcs_lps"]),
            ("Heat rejection", "kW", v0["reject_kw"], vT["reject_kw"]),
            ("Floor load on rack footprint", "psf", v0["rack_psf"], vT["rack_psf"]),
            ("White space", "sf", v0["white_sf"], vT["white_sf"])]
    return pd.DataFrame([{"Item": a, "Unit": u, "Day one": b, "Future target": c} for a, u, b, c in rows])


def opex_table(x) -> pd.DataFrame:
    return pd.DataFrame([{"Item": k, "$M per year": v / M} for k, v in x["opex_items"].items()] +
                        [{"Item": "Total operating cost", "$M per year": x["opex"] / M}])


def cash_table(x, years) -> pd.DataFrame:
    flows = x["cash_flows"]
    cum, rows = 0.0, []
    for t, cf in enumerate(flows):
        cum += cf
        rows.append({"Year": t, "Cash flow $M": cf / M, "Cumulative $M": cum / M})
    return pd.DataFrame(rows)


def schedule_table(sch) -> pd.DataFrame:
    return pd.DataFrame([{"Driver": k, "Months": v, "Critical": "✓" if k == sch["critical_path"] else ""}
                         for k, v in sch["drivers"].items()])


def long_lead_table() -> pd.DataFrame:
    return pd.DataFrame([{"Equipment": a, "Weeks (low)": b, "Weeks (high)": c, "Source": d}
                         for a, b, c, d in E.LONG_LEAD])


def checks_table(res) -> pd.DataFrame:
    names = {"facility_per_mw_air": "Facility $M per MW (air)", "facility_per_mw_hd": "Facility $M per MW (high density)",
             "fitout_per_mw": "Fit-out $M per MW", "pue": "PUE", "power_cost": "Power price $/kWh",
             "transformer_weeks": "Transformer lead (weeks)", "wue": "WUE L/kWh", "gpu_price": "GPU rental $/GPU-hr"}
    rows = []
    for c in res["checks"]:
        scale = M if "per_mw" in c["check"] else 1
        rows.append({"Check": names.get(c["check"], c["check"]), "Value": c["value"] / scale,
                     "Range": f"{c['low'] / scale:,.2f} - {c['high'] / scale:,.2f}",
                     "Status": "✓ in range" if c["ok"] else "⚠ outside range", "Basis": c["source"]})
    return pd.DataFrame(rows)


def platform_table() -> pd.DataFrame:
    rows = []
    for n, p in PL.PLATFORMS.items():
        rows.append({"Platform": p["label"], "Status": p["status"], "kW/rack (peak)": f"{p['kw']:,.0f} ({p['kw_peak']:,.0f})",
                     "GPUs/rack": p["gpus"], "Liquid share": f"{p['liquid']:.0%}",
                     "Facility $M/MW (low-high)": f"{p['rate'] / M:,.1f} ({p['low'] / M:,.1f}-{p['high'] / M:,.1f})",
                     "IT $M/rack": p["it_per_rack"] / M, "$/GPU-hr": p["gpu_hr"], "Public spec": p["spec_note"]})
    return pd.DataFrame(rows)


def all_tables(res) -> dict[str, pd.DataFrame]:
    t = {"summary_costs": cost_table(res), "design_calculations": design_table(main_design(res)),
         "benchmark_checks": checks_table(res), "schedule": schedule_table(
             res["design"]["schedule"] if res["mode"] == "greenfield" else res["schedule"]),
         "long_lead": long_lead_table(), "platforms": platform_table()}
    if res["mode"] == "greenfield":
        t["divisions"] = division_table(res)
        t["opex"] = opex_table(res["design"])
        t["cash_flow"] = cash_table(res["design"], res["inputs"]["years"])
    else:
        t["design_calculations_current"] = design_table(res["current"]["design"])
        t["opex_future_ready"] = opex_table(res["future"])
        t["opex_current"] = opex_table(res["current"])
        t["cash_flow_future_ready"] = cash_table(res["future"], res["inputs"]["years"])
    if horizon(res).get("active"):
        t["future_paths"] = future_table(res)
        t["future_upgrade_items"] = future_rows_table(res)
        t["future_design_compare"] = compare_table(res)
        t["future_design_calculations"] = design_table(horizon(res)["design_T"])
    return t


# ------------------------------------------------------------------ markdown report
def _md(df, money_cols=(), pct_cols=(), num_cols=()):
    d = df.copy()
    for c in d.columns:
        if c in pct_cols:
            d[c] = d[c].map(lambda v: f"{v:.0%}")
        elif c in money_cols or "$M" in str(c):
            d[c] = d[c].map(lambda v: f"{v:,.1f}" if isinstance(v, (int, float)) else v)
        elif c in num_cols:
            d[c] = d[c].map(lambda v: f"{v:,.0f}" if isinstance(v, (int, float)) else v)
    return d.to_markdown(index=False)


def markdown_report(res, narrative: str = "", narrative_src: str = "") -> str:
    i, h = res["inputs"], headline(res)
    rec = res["recommendation"]
    out = [f"# RackReady AI report: {i['project_name']}",
           f"_Generated {date.today().isoformat()} · {E.DISCLAIMER} 2026 US dollars._",
           "## Summary",
           f"- **Project:** {i['project_type']}, {i['region']}, {E.RESILIENCE[i['resilience']]}",
           f"- **Design:** {h['platform']}, {h['kw']:,.0f} kW/rack, {h['racks']:,} racks, {h['it_mw']:,.1f} MW IT, {h['cooling']}",
           f"- **{h['label_total']}:** {money(h['total'])} ({money(h['per_mw'])} per MW IT)",
           f"- **IT hardware (separate):** {money(h['it_total'])}",
           f"- **Payback (incl. IT, from ready-for-service):** {yrs(h['payback'])}; NPV {money(h['npv'])}",
           f"- **Ready for service:** about {h['rfs']:.0f} months",
           f"- **Recommendation:** {rec['headline']}. {rec['detail']}",
           f"- **Key design:** {key_design_line(res)}"]
    if res["warnings"]:
        out.append("**Warnings**\n\n" + "\n".join(f"- {w}" for w in res["warnings"]))
    out += ["## Costs", _md(cost_table(res))]
    if res["mode"] == "greenfield":
        out += ["### By trade group", _md(group_table(res), pct_cols=("Share",))]
    f = horizon(res)
    out.append("## Future-ready horizon")
    if f.get("active"):
        out += [f"Horizon **{f['horizon']}**: {f['horizon_text']} Target {f['target_kw']:,.0f} kW/rack installed in "
                f"year {f['year']}; probability it is deployed here {f['probability']:.0%} (assumption). "
                f"Best path: **{f['best']}**.",
                _md(future_table(res)), "### Day one vs target design", _md(compare_table(res), num_cols=("Day one", "Future target")),
                "### Provisions", pd.DataFrame(f["provisions"]).rename(columns=str.title).to_markdown(index=False)]
    else:
        out.append(f["reason"])
    out += ["## Design calculations",
            "US units with SI in brackets. Formulas use standard engineering relations "
            "(three-phase current, heat-transfer flow, refrigeration tons).",
            design_table(main_design(res)).drop(columns=["Section"]).to_markdown(index=False)]
    x = res["design"] if res["mode"] == "greenfield" else res["future"]
    out += ["## Operations & ROI", _md(opex_table(x)),
            f"Revenue year 1: {money(x['revenue'])} at ${x['gpu_price']:.2f}/GPU-hr and {i['utilization']:.0%} "
            f"utilization; rental price change {float(i.get('price_change') or 0):+.0%}/yr, reset at hardware refresh "
            "(assumption)."]
    sch = res["design"]["schedule"] if res["mode"] == "greenfield" else res["schedule"]
    out += ["## Schedule & long-lead equipment", _md(schedule_table(sch), num_cols=("Months",)),
            _md(long_lead_table())]
    out += ["## Benchmark checks", _md(checks_table(res))]
    if narrative:
        out += ["## Narrative", f"_{narrative_src}_", narrative]
    out.append(f"_{E.DISCLAIMER} Sources and ranges: docs/VERIFICATION.md in the project repository._")
    return "\n\n".join(out)


# ------------------------------------------------------------------ one-page PDF
def _latin(s: str) -> str:
    rep = {"≤": "<=", "≥": ">=", "→": "->", "·": "-", "✓": "ok", "⚠": "!", "√": "sqrt", "–": "-", "—": "-",
           "’": "'", "“": '"', "”": '"', "×": "x", "°": " deg", "³": "3", "²": "2", "ρ": "rho", "Δ": "d"}
    for a, b in rep.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def pdf_report(res) -> bytes:
    from fpdf import FPDF

    i, h = res["inputs"], headline(res)
    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(False)
    pdf.set_margins(12, 10, 12)
    pdf.add_page()
    W = pdf.w - 24

    def text(s, size=8, style="", h_=3.8, color=(30, 30, 30)):
        pdf.set_font("Helvetica", style, size)
        pdf.set_text_color(*color)
        pdf.multi_cell(W, h_, _latin(s), new_x="LMARGIN", new_y="NEXT")

    def head(s):
        pdf.ln(1.2)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(70, 120, 0)
        pdf.cell(W, 4.8, _latin(s), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(118, 185, 0)
        pdf.line(12, pdf.get_y(), 12 + W, pdf.get_y())
        pdf.ln(0.8)

    def table(rows, widths, size=7.2, bold_first=True):
        pdf.set_text_color(30, 30, 30)
        for r_i, r in enumerate(rows):
            pdf.set_font("Helvetica", "B" if (bold_first and r_i == 0) else "", size)
            for c_i, (cell, w) in enumerate(zip(r, widths)):
                pdf.cell(w, 3.7, _latin(str(cell))[:int(w * 0.62)], border=0, align="L" if c_i == 0 else "R")
            pdf.ln(3.7)

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(W, 7, _latin(f"RackReady AI - {i['project_name']}"), new_x="LMARGIN", new_y="NEXT")
    text(f"{i['project_type']} | {i['region']} | {E.RESILIENCE[i['resilience']]} | {date.today().isoformat()} | "
         f"{E.DISCLAIMER}", 7.5, color=(90, 90, 90))
    head("Summary")
    rec = res["recommendation"]
    table([["Total cost", "Per MW IT", "IT hardware", "Payback", "Ready for service"],
           [money(h["total"]), money(h["per_mw"]), money(h["it_total"]), yrs(h["payback"]), f"{h['rfs']:.0f} months"]],
          [W / 5] * 5, size=8.5)
    text(f"Design: {h['platform']}, {h['kw']:,.0f} kW/rack, {h['racks']:,} racks, {h['it_mw']:,.1f} MW IT, {h['cooling']}.")
    text(f"Recommendation: {rec['headline']}. {rec['detail']}", style="B")
    head("Costs ($M)")
    ct = cost_table(res)
    cols = list(ct.columns)
    rows = [cols] + [[r[cols[0]]] + [f"{r[c]:,.1f}" for c in cols[1:]] for _, r in ct.iterrows()]
    table(rows, [W * 0.58] + [W * 0.42 / (len(cols) - 1)] * (len(cols) - 1))
    f = horizon(res)
    head("Future-ready horizon")
    if f.get("active"):
        text(f"{f['horizon']}: {f['horizon_text']} Target {f['target_kw']:,.0f} kW/rack in year {f['year']} "
             f"(probability {f['probability']:.0%}, assumption).", 7.5)
        rows = [["Path", "Day one $M", "Later $M", "Downtime mo", "Present cost $M"]] + [
            [("> " if x["path"] == f["best"] else "") + x["path"], f"{x['day1'] / M:,.0f}", f"{x['later_nominal'] / M:,.0f}",
             f"{x['downtime_months']:.0f}", f"{x['pv_total'] / M:,.0f}"] for x in f["paths"]]
        table(rows, [W * 0.44, W * 0.14, W * 0.14, W * 0.13, W * 0.15])
    else:
        text(f["reason"], 7.5)
    head("Key design calculations")
    v = main_design(res)["v"]
    keys = ["it_kw", "fac_peak_kw", "pue", "service_mva", "main_tx", "gens", "fuel_gal", "ups_modules", "battery_kwh",
            "rack_amps", "busway_rating", "cool_tons", "cdus", "tcs_lps", "reject_kw", "wue", "gross_sf", "rack_psf",
            "land_acres"]
    steps = {s["key"]: s for s in main_design(res)["steps"]}
    items = [steps[k] for k in keys if k in steps]
    half = (len(items) + 1) // 2
    pdf.set_font("Helvetica", "", 7)
    for a, b in zip(items[:half], items[half:] + [None]):
        for s in (a, b):
            if s is None:
                continue
            pdf.set_font("Helvetica", "", 7)
            pdf.cell(W * 0.30, 3.6, _latin(s["item"])[:52])
            pdf.set_font("Helvetica", "B", 7)
            pdf.cell(W * 0.20, 3.6, _latin(val(s))[:30], align="R")
        pdf.ln(3.6)
    x = res["design"] if res["mode"] == "greenfield" else res["future"]
    head("Operations & schedule")
    sch = res["design"]["schedule"] if res["mode"] == "greenfield" else res["schedule"]
    text(f"Operating cost {money(x['opex'])}/yr; revenue year 1 {money(x['revenue'])} at ${x['gpu_price']:.2f}/GPU-hr, "
         f"{i['utilization']:.0%} utilization; NPV {money(x['npv'])} over {i['years']} years at 8%. "
         f"Critical path: {sch['critical_path']} (~{sch['months_to_rfs']:.0f} months).", 7.5)
    head("Checks & warnings")
    ok = sum(c["ok"] for c in res["checks"])
    text(f"{ok}/{len(res['checks'])} benchmark checks in range (JLL, Cushman & Wakefield, Uptime Institute, EIA, "
         f"Wood Mackenzie, NVIDIA/OEM specs). " + " ".join(res["warnings"][:3]), 7.2)
    pdf.set_y(-12)
    text(f"{E.DISCLAIMER} Generated by RackReady AI. Above 45 kW/rack the design uses direct-to-chip liquid cooling.",
         6.5, color=(110, 110, 110))
    return bytes(pdf.output())
