"""
RackReady AI - end-to-end cost lines with an "Include in total" checklist.

Every project is shown as the same 13 lines. Each line carries its cost, whether it is ticked and the
type of public source behind it. The total and the cost per MW are always the sum of the ticked lines
(tested), and the summary, PDF, exports and narrative all read the same total.

Greenfield: the facility construction cost (platform $/MW basis, see platforms.py) is carved into lines
whose sum equals it exactly, so the per-MW facility benchmark is unchanged. Lines that were not in the
facility basis (spares and first fill, racks for HGX-type platforms, bridging power, GPU hardware and the
AI network) are added on top.
Fit-out: the trade-rate systems, soft cost, contingency and escalation are regrouped the same way.
"""
from __future__ import annotations

import platforms as PL
from design import AIR, D2C, HYBRID

# (key, label, ticked by default, source type shown in the app)
LINES = [
    ("facility", "Facility: shell, power, cooling, fire", True,
     "Public data center cost outlooks ($/MW IT) split by construction division"),
    ("land", "Land and site work", True, "Indicative powered-land price (assumption) + site divisions 31-33"),
    ("interconnect", "Utility interconnect and substation", True,
     "Planning allowance per MW of utility service (assumption) + on-site substation share"),
    ("onsite", "On-site or bridging power", False,
     "US government energy cost study: gas turbine / engine capital cost per kW"),
    ("gpu", "GPU and server hardware", False, "Public system pricing per rack (estimate)"),
    ("fabric", "AI network fabric (switches, NICs, optical transceivers)", False,
     "Public per-GPU network benchmarks: networking about 8-20% of cluster cost"),
    ("fiber", "Fiber and structured cabling (backbone, laterals, rack-to-rack)", True,
     "Communications division 27 of the cost basis; trade unit rates per rack and per GPU"),
    ("racks", "Racks, rack PDUs, CDUs and manifolds", True,
     "CDU unit price and manifold/rack trade rates (assumption, within public ranges)"),
    ("security", "Security and controls", True, "Divisions 25 (controls) and 28 (security) of the cost basis"),
    ("design", "Design, permits and fees", True,
     "Design fee carve (assumption, below published A/E fee guides) + owner costs"),
    ("commissioning", "Commissioning", True,
     "Trade-press guidance about 1.5% of construction (0.75-2%); ask bidders for priced scope"),
    ("contingency", "Owner contingency and escalation", True, "Planning contingency + cost-index escalation"),
    ("spares", "Spares and first-fill", True,
     "1% of electrical + mechanical (assumption) + diesel first fill at the US government weekly diesel price"),
]
KEYS = [k for k, *_ in LINES]
LABEL = {k: lbl for k, lbl, *_ in LINES}
DEFAULT_INCLUDE = {k: on for k, _, on, _ in LINES}
SOURCE = {k: s for k, *_, s in LINES}
IT_KEYS = ("gpu", "fabric")

RATES = {
    "cx_pct": 0.015,                 # commissioning, share of construction
    "design_pct": 0.025,             # design fee carved from general conditions (assumption)
    "substation_share_26": 0.15,     # on-site HV substation share of electrical when service is on-site HV
    "spares_pct": 0.01,              # critical spares, share of electrical + mechanical
    "diesel_per_gal": 6.00,          # US weekly retail diesel about $6.18/gal (12 Oct 2026); bulk lower
    "onsite_per_kw": 2_000.0,        # gas turbine / engine plant, $/kW installed (public cost study range)
    "onsite_margin": 1.10,           # plant sized at 1.1 x facility peak
    "rack_per_rack": 6_000.0,        # rack enclosure, HGX-type platforms (NVL-type prices include the rack)
    "rpdu_per_kw": 120.0,            # rack PDUs per kW
    "manifold_per_rack": {AIR: 0.0, HYBRID: 18_000.0, D2C: 30_000.0},   # same as the fit-out trade rates
}


def include_set(inc: dict | None) -> dict:
    out = dict(DEFAULT_INCLUDE)
    for k, v in (inc or {}).items():
        if k in out:
            out[k] = bool(v)
    return out


def rack_included(p: dict) -> bool:
    """Rack-scale systems (NVL-type) are priced with the rack; HGX-type servers need racks and rack PDUs."""
    return "HGX" not in str(p.get("name", "")) and "HGX" not in str(p.get("label", ""))


def _finish(amounts: dict, inc: dict, it_mw: float) -> dict:
    inc = include_set(inc)
    rows = [{"key": k, "label": LABEL[k], "amount": float(amounts.get(k, 0.0)), "included": inc[k],
             "source": SOURCE[k]} for k in KEYS]
    total = sum(r["amount"] for r in rows if r["included"])
    every = sum(r["amount"] for r in rows)
    return {"rows": rows, "include": inc, "total": total, "total_all": every,
            "per_mw": total / it_mw if it_mw else 0.0, "per_mw_all": every / it_mw if it_mw else 0.0,
            "non_it_total": sum(r["amount"] for r in rows if r["included"] and r["key"] not in IT_KEYS)}


def _dv(div: dict, *codes) -> float:
    return sum(v for k, v in div.items() if k.split(" ")[0] in codes)


def greenfield_lines(c: dict, dz: dict, p: dict, it_mw: float, racks: float, esc: float, it_hw: float,
                     fabric: float, inc: dict | None = None) -> dict:
    """Carve the facility into lines (sum = facility exactly) and add the extra lines."""
    v = dz["v"]
    div = c["divisions"]
    reg = c["region_factor"]
    hard = sum(div.values())
    emb = c["base"] / PL.GC_AND_CONTINGENCY_DIVISOR * PL.BASE_CONTINGENCY      # contingency inside the $/MW basis
    k = (1 - emb / hard) * reg if hard else reg

    def net(*codes):
        return _dv(div, *codes) * k

    n01, n23, n26 = net("01"), net("23"), net("26")
    site = net("31", "32", "33")
    fiber = net("27")
    security = net("25", "28")
    cx = min(RATES["cx_pct"] * c["facility"], 0.40 * n01)
    design_carve = min(RATES["design_pct"] * hard * reg, max(n01 - cx, 0.0) * 0.5)
    cooling = dz["cooling"]
    cdu = v.get("cdus", 0) * PL.UNIT_PRICES["cdu_skid"] * reg
    manifolds = RATES["manifold_per_rack"].get(cooling, 0.0) * racks * reg
    racks_carved = min(cdu + manifolds, 0.6 * n23)
    substation = RATES["substation_share_26"] * n26 if dz.get("onsite_hv") else 0.0
    cont = (emb + c["contingency_adj"]) * reg
    carved = site + fiber + security + cx + design_carve + racks_carved + substation + cont
    core = c["facility"] - carved
    racks_new = 0.0 if rack_included(p) else racks * (RATES["rack_per_rack"] + RATES["rpdu_per_kw"] * p["kw"]) * reg
    spares = RATES["spares_pct"] * (n23 + n26) + v.get("fuel_gal", 0.0) * RATES["diesel_per_gal"]
    onsite = v["fac_peak_kw"] * RATES["onsite_margin"] * RATES["onsite_per_kw"]
    amounts = {"facility": core, "land": c["land"] + site, "interconnect": c["interconnect"] + substation,
               "onsite": onsite, "gpu": it_hw, "fabric": fabric, "fiber": fiber,
               "racks": racks_carved + racks_new, "security": security, "design": design_carve + c["owner"],
               "commissioning": cx, "contingency": cont + esc, "spares": spares}
    out = _finish(amounts, inc, it_mw)
    out["carve"] = {"site": site, "fiber": fiber, "security": security, "commissioning": cx, "design": design_carve,
                    "racks": racks_carved, "substation": substation, "contingency": cont, "core": core,
                    "racks_new": racks_new}
    return out


def fitout_lines(f: dict, p: dict, i: dict, rates: dict, reg: float, interconnect: float,
                 inc: dict | None = None) -> dict:
    """Regroup the future-ready fit-out into the same lines (sum of the regrouped lines = fit-out cost)."""
    S = f["systems"]
    racks, kw, gpus = f["racks"], f["kw"], p.get("gpus", 0)
    rk = racks * (rates["rack_per_rack"] + rates["rpdu_per_kw"] * kw) * reg
    cab = racks * (rates["cabling_per_rack"] + rates["cabling_per_gpu"] * gpus) * reg
    facility = sum(v for k_, v in S.items() if k_.startswith(("Electrical", "Mechanical", "Structure", "Fire")))
    liquid = S.get("Liquid cooling: CDUs, manifolds (Div 23)", 0.0)
    controls = S.get("Controls (Div 25)", 0.0)
    cx = RATES["cx_pct"] * f["direct"]
    v = f["design"]["v"]
    elec = S.get("Electrical (Div 26)", 0.0)
    mech = S.get("Mechanical (Div 23)", 0.0) + liquid
    amounts = {"facility": facility, "land": 0.0, "interconnect": interconnect,
               "onsite": v["fac_peak_kw"] * RATES["onsite_margin"] * RATES["onsite_per_kw"],
               "gpu": racks * p["it_per_rack"], "fabric": p["fabric_per_mw"] * f["it_mw"], "fiber": cab,
               "racks": rk + liquid, "security": controls, "design": f["soft"] - cx, "commissioning": cx,
               "contingency": f["contingency"] + f["escalation"],
               "spares": RATES["spares_pct"] * (elec + mech) + v.get("fuel_gal", 0.0) * RATES["diesel_per_gal"]}
    return _finish(amounts, inc, f["it_mw"])


def fabric_share(p: dict) -> float:
    """AI network share of the cluster (servers + network), used by the benchmark test (8-20%)."""
    per_rack = p["fabric_per_mw"] * p["kw"] / 1000
    return per_rack / (per_rack + p["it_per_rack"])


def fabric_per_gpu(p: dict) -> float:
    return p["fabric_per_mw"] * p["kw"] / 1000 / max(p.get("gpus") or 1, 1)
