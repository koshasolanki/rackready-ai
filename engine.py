"""
RackReady AI - deterministic cost engine.

Two project types:
  * Greenfield: ONE new build from scratch, sized by IT MW or racks for a GPU platform. Facility cost
    = platform cost basis ($/MW IT, see platforms.py) x IT MW, split by CSI division, then adjusted
    for resilience (counted from the design calculations), contingency, location, owner costs and
    escalation; land, utility interconnection and IT hardware are added separately.
  * Existing building fit-out: current (legacy) racks vs a future-ready fit-out for the GPU platform
    in the same hall, plus "build current now, retrofit later". Trade unit rates in FITOUT_RATES.

Both modes add a future-proof horizon: a target rack density from the public GPU roadmap, priced
three ways: build for today and retrofit later / build today with pre-installed provisions /
build the full future design on day one.

Rule for every design: above 45 kW/rack the cooling is direct-to-chip (D2C) liquid, set
automatically. All figures are early budget estimates (±30-50%), not a bid.
"""
from __future__ import annotations

import math
from copy import deepcopy

import buildcx as CX
import costlines as CL
import design as DS
import guide as G
import platforms as PL
from design import AIR, COOLING_TYPES, D2C, D2C_AUTO_KW, HYBRID, effective_cooling

D2C_NOTE = "D2C auto-selected above 45 kW/rack"
DISCLAIMER = "Early budget estimate (±30–50%), not a bid."
ESTIMATE_NOTE = ("Early budget estimate (±30–50%), not a bid: built from per-MW benchmarks and design quantities before any "
                 "drawings exist, so the final cost can land well above or below it.")
HOURS = 8760

FITOUT, GREENFIELD = "Existing building fit-out", "Greenfield (new build)"
PROJECT_TYPES = [GREENFIELD, FITOUT]

RESILIENCE = {
    "N": "N (Tier I-style, no redundancy)",
    "N+1": "N+1 (Tier III-style, concurrently maintainable)",
    "N+2": "N+2 generators (Tier III+)",
    "2N": "2N power (Tier IV-style, fault tolerant)",
}

HORIZONS = {
    "Today only": None,
    "5 years": 230.0,     # Vera Rubin NVL144 class (announced; top of the published 130-230 kW range)
    "10 years": 600.0,    # Rubin Ultra NVL576 / Kyber class (announced, about 600 kW, 2H 2027)
    "15 years": 1000.0,   # 1 MW-class racks (industry direction, speculative)
}
HORIZON_TEXT = {
    "Today only": "No future-proofing: design only for the day-one platform.",
    "5 years": "Vera Rubin NVL144 class, about 230 kW/rack (announced by NVIDIA for 2H 2026; estimate).",
    "10 years": "Rubin Ultra NVL576 / Kyber class, about 600 kW/rack with 800 VDC (announced for 2H 2027).",
    "15 years": "1 MW-class racks (NVIDIA 800 VDC roadmap); speculative.",
}
HORIZON_ARRIVAL = {"5 years": 3, "10 years": 5, "15 years": 8}   # year the target racks go in

# Location: construction cost factor (N. Virginia = 1.00) and indicative powered-land price ($/acre)
REGIONS = {
    "US - Northern Virginia": {"factor": 1.00, "land": 2_500_000, "power": 0.085},
    "US - Dallas / Texas": {"factor": 0.92, "land": 500_000, "power": 0.075},
    "US - Phoenix": {"factor": 0.90, "land": 600_000, "power": 0.080},
    "US - New York / New Jersey": {"factor": 1.12, "land": 1_500_000, "power": 0.120},
    "Ireland - Dublin": {"factor": 0.90, "land": 1_500_000, "power": 0.180},
    "Nordics - Stockholm / Oslo": {"factor": 1.07, "land": 250_000, "power": 0.060},
    "Singapore": {"factor": 1.26, "land": 10_000_000, "power": 0.170},
    "India - Mumbai": {"factor": 0.58, "land": 1_500_000, "power": 0.090},
}
REGION_NAMES = list(REGIONS)

# --------------------------------------------------------------------------- fit-out trade rates
FITOUT_RATES = {
    # Div 26 electrical, $ per kW IT (N+1)
    "electrical_per_kw": {"MV service & transformers": 650, "Switchgear & switchboards": 900,
                          "UPS & batteries": 950, "Generators & fuel": 850, "Busway, PDUs & RPPs": 450,
                          "Grounding, lighting & branch power": 250},
    "hd_electrical_premium_per_kw": 600, "hd_threshold_kw": 50,
    # Div 23 mechanical, $ per kW IT by cooling type
    "mechanical_per_kw": {
        AIR: {"Chillers / central plant": 950, "CRAH / fan walls": 850, "Piping & pumps": 350,
              "Cooling towers": 450},
        HYBRID: {"Chillers / central plant": 900, "CRAH / fan walls": 500, "Rear-door heat exchangers": 650,
                 "Piping & pumps": 450, "Cooling towers": 400},
        D2C: {"Trim chillers": 450, "Residual air (fan walls / CRAH)": 350,
              "Piping, headers & pumps (FWS/TCS)": 950, "Dry / adiabatic coolers": 900}},
    "cdu_skid": PL.UNIT_PRICES["cdu_skid"],
    "manifold_per_rack": {AIR: 0, HYBRID: 18_000, D2C: 30_000},
    "controls_per_kw": 250, "white_sf_per_rack": 30, "support_sf_per_mw": 3_000,
    "shell_per_gsf": 300, "fire_per_gsf": 14, "heavy_slab_per_sf": 75, "heavy_per_rack": 2_500,
    "rack_per_rack": 6_000, "rpdu_per_kw": 120, "cabling_per_rack": 12_000, "cabling_per_gpu": 400,
    "soft_pct": 0.14, "contingency_pct": 0.10,
    "redundancy": {"N": (0.85, 0.90), "N+1": (1.00, 1.00), "N+2": (1.06, 1.00), "2N": (1.35, 1.20)},
    "retrofit_premium": 1.35, "retrofit_demo_pct": 0.06, "retrofit_downtime_months": 4, "retrofit_year": 3,
    "retrofit_reuse": {"Electrical (Div 26)": 0.45, "Mechanical (Div 23)": 0.15,
                       "Liquid cooling: CDUs, manifolds (Div 23)": 0.0, "Controls (Div 25)": 0.50,
                       "Structure & architecture (Div 03-09)": 0.80, "Fire protection (Div 21)": 0.60,
                       "Racks, power strips & cabling (Div 27)": 0.40},
    "design_months": 4, "construction_months": 10,
}
FITOUT_SYSTEM_DIVS = {   # map fit-out systems to division codes (for the horizon ratio method)
    "Electrical (Div 26)": ["26"], "Mechanical (Div 23)": ["23"],
    "Liquid cooling: CDUs, manifolds (Div 23)": ["23"], "Controls (Div 25)": ["25"],
    "Structure & architecture (Div 03-09)": ["03", "04", "05", "06", "07", "08", "09"],
    "Fire protection (Div 21)": ["21"], "Racks, power strips & cabling (Div 27)": ["27"],
}

# Share of the future upgrade that is worth pre-installing on day one ("provisions"): things that
# are cheap now and very expensive later (structure, slab, site, pathways, oversized headers, pads).
PROVISION_SHARE = {"01": None, "02": 1.0, "03": 1.0, "04": 0.5, "05": 1.0, "06": 0.5, "07": 1.0,
                   "08": 0.5, "09": 0.5, "10-12": 0.5, "13": 0.0, "14": 0.5, "21": 0.25, "22": 0.5,
                   "23": 0.40, "25": 0.25, "26": 0.25, "27": 0.25, "28": 0.25, "31": 1.0, "32": 1.0,
                   "33": 1.0}
FUTURE = {"retrofit_premium": 1.35, "phased_premium": 1.10, "demo_pct": 0.06,
          "retrofit_downtime_months": 4.0, "provision_downtime_months": 1.0,
          "probability": 0.70, "idle_carry_pct": 0.02}

OPEX = {"maintenance_pct": 0.02, "insurance_pct": 0.003, "property_tax_pct": 0.005,
        "staff_base_fte": 8, "staff_fte_per_mw": 0.5, "staff_cost": 140_000, "water_per_m3": 2.00,
        "hw_life_years": 5, "refresh_factor": 0.70, "discount_rate": 0.08}

# Long-lead equipment (weeks), current 2026 ranges: see buildcx.LEAD_TIMES (single source of truth).
LONG_LEAD = [(name, lo, hi, basis) for _k, name, lo, hi, _t, basis in CX.LEAD_TIMES]
TRANSFORMER_WEEKS = 128

DEFAULT_INPUTS = {
    "project_type": GREENFIELD, "project_name": "AI campus - 100 MW",
    "size_by": "IT MW", "it_mw": 100.0, "racks": 200,
    "platform": PL.DEFAULT_PLATFORM, "custom_kw": 135.0, "custom_gpus": None, "custom_it_per_rack": None,
    "region": "US - Northern Virginia", "resilience": "N+1", "horizon": "10 years", "cooling": None,
    # fit-out: the existing hall today
    "current_kw": 15.0, "current_cooling": AIR, "current_gpus": 8, "current_gpu_price": 2.50,
    "current_gpu_hw": 30_000,
    # operations & revenue
    "power_cost": None, "utilization": 0.80, "years": 10, "gpu_price": None, "price_change": -0.08,
    "include_it": True, "include_fabric": True,
    # cost options
    "contingency": 0.08, "owner_pct": 0.03, "escalation": 0.05, "land_per_acre": None,
    "interconnect": None, "months_to_power": 36, "design_months": 9, "construction_months": None,
    # schedule (None / 0 = auto from MW)
    "fitout_build_months": None, "overtime_hours": 40, "weather_factor": 0.05,
    "congestion_factor": 0.0,
    # engineering
    "fuel_hours": 48.0, "battery_min": 5.0, "voltage": 415.0, "tcs_dT": 10.0,
    # future-proof horizon
    "future_kw": None, "future_year": None, "spare_utility_pct": 0.0, "future_probability": 0.70,
    "overhead_pct": 0.15,
    # "Include in total" checklist (see costlines.py); None = defaults
    "include": None,
}

PRESETS = {
    "100 MW AI campus (greenfield, GB300 NVL72)": {
        "project_type": GREENFIELD, "project_name": "AI campus - 100 MW", "size_by": "IT MW", "it_mw": 100.0,
        "platform": "GB300 NVL72", "region": "US - Northern Virginia", "resilience": "N+1",
        "horizon": "10 years"},
    "10 MW edge AI hall (greenfield, H200 HGX)": {
        "project_type": GREENFIELD, "project_name": "Edge AI hall - 10 MW", "size_by": "IT MW", "it_mw": 10.0,
        "platform": "H200 HGX", "region": "US - Dallas / Texas", "resilience": "N+1", "horizon": "5 years",
        "cooling": HYBRID, "months_to_power": 18, "design_months": 6},
    "Existing-hall fit-out (200 racks, 15 kW -> GB300)": {
        "project_type": FITOUT, "project_name": "Existing hall - 200 racks", "size_by": "Racks", "racks": 200,
        "platform": "GB300 NVL72", "region": "US - Northern Virginia", "resilience": "N+1",
        "horizon": "5 years", "current_kw": 15.0, "current_cooling": AIR},
}
DEFAULT_PRESET = next(iter(PRESETS))


def merged(inp: dict | None) -> dict:
    i = deepcopy(DEFAULT_INPUTS)
    i.update({k: v for k, v in (inp or {}).items()})
    return i


def is_greenfield(i: dict) -> bool:
    return str(i.get("project_type", "")).lower().startswith("greenfield")


def _npv(rate, flows):
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))


def _payback(flows):
    cum = 0.0
    for t, cf in enumerate(flows):
        prev = cum
        cum += cf
        if t > 0 and cum >= 0 > prev:
            return t - 1 + (-prev / cf if cf else 0)
    return None


def _platform(i: dict) -> dict:
    p = PL.platform(i["platform"], i.get("custom_kw"))
    if i["platform"] not in PL.PLATFORMS:
        if i.get("custom_gpus"):
            p["gpus"] = int(i["custom_gpus"])
        if i.get("custom_it_per_rack"):
            p["it_per_rack"] = float(i["custom_it_per_rack"])
    return p


def _gpu_price(i, p):
    return float(i["gpu_price"]) if i.get("gpu_price") else float(p["gpu_hr"])


def _power_cost(i):
    return float(i["power_cost"]) if i.get("power_cost") else REGIONS[i["region"]]["power"]


def _land_price(i):
    return float(i["land_per_acre"]) if i.get("land_per_acre") is not None else REGIONS[i["region"]]["land"]


def _design(p: dict, racks: float, cooling: str, i: dict, land_per_acre=0.0, gsf_per_mw=None):
    params = {"fuel_hours": i.get("fuel_hours"), "battery_min": i.get("battery_min"),
              "voltage": i.get("voltage"), "tcs_dT": i.get("tcs_dT")}
    return DS.design(racks=racks, kw=p["kw"], kw_peak=p["kw_peak"], cooling=cooling, liquid=p["liquid"],
                     weight_lb=p["weight_lb"], rack_w_m=p["rack_w_m"], rack_d_m=p["rack_d_m"],
                     white_sf=p["white_sf"], gsf_per_mw=gsf_per_mw or p["gsf_per_mw"], cdu_mw=p["cdu_mw"],
                     resilience=i["resilience"], utilization=i["utilization"], land_per_acre=land_per_acre,
                     params=params, gpus=int(p.get("gpus") or 0))


def _revenue_flows(invest, year1_rev, opex, hw, years, change, refresh_factor, life):
    """Cash flows: year 0 = -invest; rental price changes by `change`/yr and resets at a refresh."""
    flows, revs, age = [-invest], [], 0
    for y in range(1, years + 1):
        rev = year1_rev * (1 + change) ** age
        cf = rev - opex
        if hw and y % life == 0 and y < years:
            cf -= hw * refresh_factor
            age = -1
        age += 1
        flows.append(cf)
        revs.append(rev)
    return flows, revs


def _plan(i, p, it_mw, racks, dz, gf=True, needs_new_service=True, horizon_active=False):
    """Schedule, order-by dates, commissioning and risks (buildcx). months_to_rfs = substantial completion."""
    cx = CX.plan(it_mw=it_mw, racks=racks, kw=p["kw"], cooling_d2c=dz["cooling"] == D2C, liquid=dz["liquid"],
                 onsite_hv=bool(dz.get("onsite_hv")), greenfield=gf, i=i, platform_status=p.get("status", "shipping"),
                 horizon_active=horizon_active, needs_new_service=needs_new_service,
                 gen_mw=float(dz["params"].get("gen_mw", 3.0)))
    return cx["schedule"], cx


def _esc(i, months):
    return (1 + float(i.get("escalation") or 0)) ** (months / 12) - 1


# =============================================================================== GREENFIELD
def greenfield_cost(p: dict, it_mw: float, design: dict, i: dict, include_land=True) -> dict:
    """Facility cost for one design point (today's dollars before escalation)."""
    reg = REGIONS[i["region"]]["factor"]
    base = p["rate"] * it_mw
    div = {d: base * s for d, s in p["mix"].items()}
    U = PL.UNIT_PRICES
    soft = 1 + U["soft_on_change"]
    v = design["v"]
    # resilience changes priced from the design counts vs the N+1 basis
    changes = []
    if i["resilience"] != "N+1":
        ref = DS.design(**{**design["_args"], "resilience": "N+1"})["v"]
        g = v["gens"] - ref["gens"]
        mult = {"N+2": U["generator_multiplier_n2"], "2N": U["generator_multiplier_2n"]}.get(i["resilience"], 1.0)
        if g:
            changes.append((f"Generators {ref['gens']:,.0f} -> {v['gens']:,.0f}", "26", g * U["generator_3mw"] * mult * soft))
        u = v["ups_modules"] - ref["ups_modules"]
        if u:
            m = U["ups_multiplier_2n"] if i["resilience"] == "2N" else 1.0
            changes.append((f"UPS modules {ref['ups_modules']:,.0f} -> {v['ups_modules']:,.0f}", "26",
                            u * U["ups_module_1mw"] * m * soft))
        t = (v["unit_subs_it"] + v["unit_subs_mech"]) - (ref["unit_subs_it"] + ref["unit_subs_mech"])
        if t:
            changes.append((f"MV/LV transformers + switchboards {t:+,.0f}", "26", t * 450_000 * soft))
        cd = v["cdus"] - ref["cdus"]
        if cd:
            changes.append((f"CDUs {ref['cdus']:,.0f} -> {v['cdus']:,.0f}", "23", cd * U["cdu_skid"] * soft))
    fh = float(i.get("fuel_hours") or 48)
    if abs(fh - 48) > 1e-9:
        changes.append((f"Fuel storage 48 h -> {fh:.0f} h", "22", PL.FUEL_COST_PER_MW_HOUR * it_mw * (fh - 48) * soft))
    cont = float(i.get("contingency") if i.get("contingency") is not None else PL.BASE_CONTINGENCY)
    cont_adj = base / PL.GC_AND_CONTINGENCY_DIVISOR * (cont - PL.BASE_CONTINGENCY)
    capped = []
    for name, d, amt in changes:
        key = next(k for k in div if k.startswith(d))
        # a reduction cannot remove more than half of its division (tiny sites: one fewer 3 MW unit
        # would otherwise make the division negative)
        amt = max(amt, -0.5 * div[key])
        div[key] += amt
        capped.append((name, d, amt))
    changes = capped
    hard = sum(div.values())
    region_adj = (hard + cont_adj) * (reg - 1)
    facility = hard + cont_adj + region_adj
    owner = facility * float(i.get("owner_pct") or 0)
    land = design["v"]["land_acres"] * _land_price(i) if include_land else 0.0
    inter = (float(i["interconnect"]) if i.get("interconnect") is not None
             else 80_000 * design["v"]["service_mw"])
    return {"base": base, "divisions": div, "changes": changes, "contingency_pct": cont,
            "contingency_adj": cont_adj, "region_factor": reg, "region_adj": region_adj, "facility": facility,
            "owner": owner, "land": land, "interconnect": inter}


def run_greenfield(i: dict) -> dict:
    p = _platform(i)
    kw = p["kw"]
    cooling, auto = effective_cooling(kw, i.get("cooling"))
    if i.get("size_by") == "Racks":
        racks = int(i["racks"])
        it_mw = racks * kw / 1000
    else:
        it_mw = float(i["it_mw"])
        racks = math.ceil(it_mw * 1000 / kw - 1e-9)
    land_price = _land_price(i)
    # IT MW is kept exact; the design uses the exact (fractional) rack count, positions are whole racks
    dz = _design(p, it_mw * 1000 / kw, cooling, i, land_price)
    dz["_args"] = dict(racks=it_mw * 1000 / kw, kw=p["kw"], kw_peak=p["kw_peak"], cooling=cooling, liquid=p["liquid"],
                       weight_lb=p["weight_lb"], rack_w_m=p["rack_w_m"], rack_d_m=p["rack_d_m"],
                       white_sf=p["white_sf"], gsf_per_mw=p["gsf_per_mw"], cdu_mw=p["cdu_mw"],
                       resilience=i["resilience"], utilization=i["utilization"], land_per_acre=land_price,
                       params={"fuel_hours": i.get("fuel_hours"), "battery_min": i.get("battery_min"),
                               "voltage": i.get("voltage"), "tcs_dT": i.get("tcs_dT")})
    c = greenfield_cost(p, it_mw, dz, i)
    h = i.get("horizon") or "Today only"
    sch, cx = _plan(i, p, it_mw, racks, dz, gf=True,
                    horizon_active=bool((i.get("future_kw") or HORIZONS.get(h) or 0) > p["kw"]))
    esc = (c["facility"] + c["owner"]) * _esc(i, sch["mid_point_months"])
    construction = c["facility"] + c["owner"] + esc + c["land"] + c["interconnect"]
    # IT and economics
    gpus = racks * p["gpus"]
    it_hw = racks * p["it_per_rack"]
    fabric = p["fabric_per_mw"] * it_mw
    cl = CL.greenfield_lines(c, dz, p, it_mw, it_mw * 1000 / kw, esc, it_hw, fabric, i.get("include"))
    capex = cl["total"]
    lines = {r["label"]: r["amount"] for r in cl["rows"] if r["included"]}
    it_total = _it_total(i, cl, it_hw, fabric)
    eco = _economics(i, it_mw, dz, cl["non_it_total"], c["facility"], gpus, _gpu_price(i, p), it_total)
    fut = future_paths(i, p, it_mw, cooling, dz, mode="greenfield", day1_cost=c, eco=eco)
    d = {"platform": p, "kw": kw, "racks": racks, "it_mw": it_mw, "cooling": cooling, "cooling_auto": auto,
         "design": dz, "cost": c, "lines": lines, "escalation": esc, "capex": capex, "cost_lines": cl,
         "construction_basis": construction, "capex_all": cl["total_all"],
         "facility_per_mw": c["facility"] / it_mw, "capex_per_mw": capex / it_mw,
         "gsf": dz["v"]["gross_sf"], "facility_per_gsf": c["facility"] / dz["v"]["gross_sf"],
         "gpus": gpus, "it_hw": it_hw, "fabric": fabric, "schedule": sch, **eco}
    res = {"mode": "greenfield", "inputs": i, "design": d, "future": fut, "long_lead": LONG_LEAD, "cx": cx}
    res["warnings"] = _warnings(res)
    res["checks"] = benchmark_checks(res)
    res["recommendation"] = recommendation(res)
    return res


def _it_total(i, cl, it_hw, fabric):
    """IT in the ROI: ticked IT lines always count; 'Include GPU / IT hardware in ROI' adds them too."""
    inc = cl["include"]
    roi = bool(i.get("include_it", True))
    return ((it_hw if (roi or inc["gpu"]) else 0.0) +
            (fabric if ((roi and i.get("include_fabric", True)) or inc["fabric"]) else 0.0))


def _economics(i, it_mw, dz, capex, facility, gpus, price, it_total):
    v = dz["v"]
    pc = _power_cost(i)
    reg = REGIONS[i["region"]]["factor"]
    it_energy = v["it_mwh"] * 1000 * pc
    fac_energy = v["fac_mwh"] * 1000 * pc
    over = fac_energy - it_energy
    cool_share = dz["params"]["cool_avg"][dz["cooling"]] / max(v["pue"] - 1, 1e-9)
    fte = OPEX["staff_base_fte"] + OPEX["staff_fte_per_mw"] * it_mw
    opex_items = {"IT energy": it_energy, "Cooling energy": over * cool_share,
                  "Other facility energy (UPS losses, lighting)": over * (1 - cool_share),
                  "Maintenance (2% of facility cost)": facility * OPEX["maintenance_pct"],
                  f"Staffing ({fte:,.0f} FTE)": fte * OPEX["staff_cost"] * reg,
                  "Insurance (0.3%)": facility * OPEX["insurance_pct"],
                  "Property tax (0.5%)": facility * OPEX["property_tax_pct"],
                  "Water & sewer": v["water_m3"] * OPEX["water_per_m3"]}
    util = i["utilization"]
    rev1 = gpus * price * util * HOURS
    oh = float(i.get("overhead_pct") if i.get("overhead_pct") is not None else 0.15)
    opex_items[f"Cloud operations overhead ({oh:.0%} of revenue: software, sales, network)"] = rev1 * oh
    opex = sum(opex_items.values())
    invest = capex + it_total
    years = int(i["years"])
    flows, revs = _revenue_flows(invest, rev1, opex, it_total, years, float(i.get("price_change") or 0),
                                 OPEX["refresh_factor"], OPEX["hw_life_years"])
    return {"opex_items": opex_items, "opex": opex, "power_cost": pc, "gpu_price": price, "revenue": rev1,
            "revenues": revs, "it_total": it_total, "total_invest": invest, "net_year1": rev1 - opex,
            "cash_flows": flows, "npv": _npv(OPEX["discount_rate"], flows), "payback": _payback(flows)}


# =============================================================================== FUTURE PATHS
def _target_platform(T: float) -> dict:
    for n in PL.LADDER:
        if abs(PL.PLATFORMS[n]["kw"] - T) < 1e-9:
            return dict(PL.PLATFORMS[n])
    return PL.custom_platform(T)


def future_paths(i, p0, it_mw, cooling0, dz0, mode, day1_cost=None, eco=None, fit=None):
    h = i.get("horizon") or "Today only"
    T = i.get("future_kw") or HORIZONS.get(h)
    if not T or T <= p0["kw"] + 1e-9:
        return {"active": False, "horizon": h, "target_kw": T,
                "reason": ("No future-proof horizon selected." if not T else
                           f"The day-one platform ({p0['kw']:.0f} kW/rack) already meets the {h} target.")}
    T = float(T)
    pT = _target_platform(T)
    spare = float(i.get("spare_utility_pct") or 0)
    mw_T = it_mw * (1 + spare)
    racks_T = mw_T * 1000 / T
    cool_T, _ = effective_cooling(T, D2C)
    dzT = _design(pT, racks_T, cool_T, i, 0.0)
    years = int(i["years"])
    Y = int(i.get("future_year") or HORIZON_ARRIVAL.get(h, 5))
    Y = max(1, min(Y, years))
    reg = REGIONS[i["region"]]["factor"]
    # ---- division deltas (positive part), today's dollars
    if mode == "greenfield":
        mult = (1 + day1_cost["contingency_adj"] / day1_cost["base"]) * reg * (1 + float(i.get("owner_pct") or 0))
        c0 = {d: p0["rate"] * it_mw * s * mult for d, s in p0["mix"].items()}
        cT = {d: pT["rate"] * mw_T * s * mult for d, s in pT["mix"].items()}
        rows = []
        for d in PL.DIVISIONS:
            delta = max(cT[d] - c0[d], 0.0)
            code = d.split(" ")[0]
            rows.append({"item": d, "group": PL.group_of(d), "today": c0[d], "future": cT[d], "delta": delta,
                         "code": code})
        nonzero = [r for r in rows if r["code"] != "01"]
        tot = sum(r["delta"] for r in nonzero) or 1.0
        gc_share = sum(r["delta"] * PROVISION_SHARE[r["code"]] for r in nonzero) / tot
        for r in rows:
            r["share"] = gc_share if r["code"] == "01" else PROVISION_SHARE[r["code"]]
        replaced_base = sum(c0[d] for d in PL.DIVISIONS if d.split(" ")[0] in ("13", "23", "26"))
        monthly_rev = _margin_in_year(eco, Y) / 12
    else:
        rows = []
        f_soft = (1 + FITOUT_RATES["soft_pct"]) * (1 + FITOUT_RATES["contingency_pct"])
        for sysname, cost in fit["systems"].items():
            codes = FITOUT_SYSTEM_DIVS[sysname]
            g0 = p0["rate"] * sum(s for d, s in p0["mix"].items() if d.split(" ")[0] in codes)
            gT = pT["rate"] * sum(s for d, s in pT["mix"].items() if d.split(" ")[0] in codes)
            ratio = (gT * mw_T) / (g0 * it_mw) if g0 else 1.0
            delta = max(cost * (ratio - 1), 0.0) * f_soft
            share = {"Structure & architecture (Div 03-09)": 1.0, "Mechanical (Div 23)": 0.40,
                     "Liquid cooling: CDUs, manifolds (Div 23)": 0.40}.get(sysname, 0.25)
            rows.append({"item": sysname, "group": sysname, "today": cost * f_soft, "future": cost * f_soft + delta,
                         "delta": delta, "share": share, "code": sysname})
        replaced_base = sum(v * f_soft for k, v in fit["systems"].items()
                            if k.startswith(("Electrical", "Mechanical", "Liquid")))
        monthly_rev = _margin_in_year(fit, Y) / 12
    delta = sum(r["delta"] for r in rows)
    prov = sum(r["delta"] * r["share"] for r in rows)
    F = FUTURE
    esc_y = (1 + float(i.get("escalation") or 0)) ** Y
    disc = (1 + OPEX["discount_rate"]) ** Y
    A_later = delta * F["retrofit_premium"] + replaced_base * F["demo_pct"]
    B_later = (delta - prov) * F["phased_premium"]
    paths = [
        {"path": "Build for today, retrofit later", "day1": 0.0, "later": A_later,
         "downtime_months": F["retrofit_downtime_months"]},
        {"path": "Build today + future-ready provisions", "day1": prov, "later": B_later,
         "downtime_months": F["provision_downtime_months"]},
        {"path": "Full future build on day one", "day1": delta, "later": 0.0, "downtime_months": 0.0},
    ]
    prob = float(i.get("future_probability") if i.get("future_probability") is not None else F["probability"])
    carry_pv = sum(F["idle_carry_pct"] / (1 + OPEX["discount_rate"]) ** t for t in range(1, Y + 1))
    for x in paths:
        x["later_nominal"] = x["later"] * esc_y
        x["downtime_cost"] = x["downtime_months"] * monthly_rev
        x["idle_carry"] = (x["day1"] - prov if x["path"].startswith("Full") else 0.0) * carry_pv
        x["nominal_total"] = x["day1"] + x["later_nominal"] + x["downtime_cost"]
        x["pv_total"] = x["day1"] + x["idle_carry"] + prob * (x["later_nominal"] + x["downtime_cost"]) / disc
    best = min(paths, key=lambda x: x["pv_total"])
    provisions = provision_list(p0, pT, dz0, dzT, T, spare, mode)
    return {"active": True, "horizon": h, "horizon_text": HORIZON_TEXT.get(h, f"Target {T:,.0f} kW/rack"),
            "target_kw": T, "target_platform": pT, "target_mw": mw_T, "target_racks": racks_T,
            "target_cooling": cool_T, "design_T": dzT, "year": Y, "rows": rows, "delta": delta,
            "provisions_cost": prov, "paths": paths, "best": best["path"], "spare_pct": spare,
            "provisions": provisions, "probability": prob, "monthly_margin": monthly_rev}


def _margin_in_year(eco, Y):
    revs = eco["revenues"]
    rev = revs[min(Y, len(revs)) - 1] if revs else eco["revenue"]
    return max(rev - eco["opex"], 0.0)


def provision_list(p0, pT, dz0, dzT, T, spare, mode):
    """Future-ready provisions: what to build in now, when to buy the rest, and why it pays."""
    v0, vT = dz0["v"], dzT["v"]
    gf = mode == "greenfield"
    items = [
        ("Structure and floor load", f"Design the slab/structure for {pT['weight_lb']:,.0f} lb racks "
         f"({vT['rack_psf']:,.0f} psf on the footprint, {vT['caster_kn']:.1f} kN per caster) vs "
         f"{v0['rack_psf']:,.0f} psf today; reserve overhead hanger capacity for liquid headers.",
         "Pre-install (cheap now, near-impossible later)",
         "Rack weight rises every generation; strengthening a live hall means shutdowns, shoring and coring."),
        ("Clear height", "Keep about 18-20 ft clear under structure in the data halls (slab-on-grade, overhead "
         "busway, tray and liquid headers stacked in tiers).", "Structure now" if gf else "Check the existing hall",
         "Overhead services multiply with density; height cannot be added to a finished building."),
        ("Liquid cooling", f"Size headers and pipe galleries for {vT['tcs_lps'] / max(vT['taps'] / 2, 1) * 60:,.0f} L/min "
         f"per rack (today {v0['tcs_lps'] / max(v0['taps'] / 2, 1) * 60:,.0f}); valved taps for future CDUs.",
         "Oversize pipework now; add CDUs later",
         "Hot-tapping a live coolant loop risks the IT; pipe is a small share of cooling cost."),
        ("CDU space", f"Reserve floor space, power and valved connections for {vT['cdus']:,.0f} CDUs at the target "
         f"(today {v0['cdus']:,.0f}).", "Reserve space; buy later",
         "CDUs are long-lead (30-50 weeks) and need floor area next to the halls."),
        ("Power distribution", f"Busway pathways and tap-off space for {vT['rack_amps']:,.0f} A per rack feed "
         f"(today {v0['rack_amps']:,.0f} A); {vT['busway_rating']:,.0f} A row busway.",
         "Pathways and supports now; busway later",
         "Supports, penetrations and firestopping are cheap during construction and disruptive later."),
        ("Pathways at 2x", "Cable tray, conduit and duct-bank capacity at about twice day-one fill, with "
         "fire-rated sleeves left spare.", "Build the pathways now",
         "Fabric fiber counts grow with every GPU generation; pathways are the hard part to add."),
        ("800 VDC readiness", f"Reserve space and pathways for 800 VDC power conversion (sidecars or central "
         f"rectifiers); a {T:,.0f} kW rack draws {T * 1000 / 54:,.0f} A at 54 VDC vs {T * 1000 / 800:,.0f} A at 800 VDC.",
         "Reserve space and pathways; buy later",
         "Announced MW-class racks move to 800 VDC distribution; at 54 VDC the copper becomes impractical."),
        ("Rack bay", f"Rack position {pT['rack_w_m'] * 1000:,.0f} x {pT['rack_d_m'] * 1000:,.0f} mm at the target "
         f"(today {p0['rack_w_m'] * 1000:,.0f} x {p0['rack_d_m'] * 1000:,.0f} mm); plan rows for "
         f"{dzT['v']['taps'] / 2:,.0f} racks.", "Lay out rows and containment for both",
         "Row pitch fixes the white space; changing it later moves every pipe and busway."),
        ("Power headroom", f"Utility service {vT['service_mva']:,.0f} MVA at the target vs {v0['service_mva']:,.0f} MVA "
         "today; spare transformer and switchgear bays, duct banks and pads.", "Contract the MW and build pads now",
         "Utility capacity and large transformers are the longest leads (years); a bay is cheap."),
        ("Heat rejection and warm water", f"Yard space for {vT['reject_kw'] / 1000:,.1f} MW of heat rejection "
         f"(today {v0['reject_kw'] / 1000:,.1f} MW); warm-water design (facility supply about 30-45 C) for dry "
         "coolers and future heat reuse.", "Reserve yard; add units later",
         "Warm water allows dry coolers with little or no water use and makes heat export possible."),
        ("Generators and on-site power", "Multi-fuel-capable generator plant (renewable diesel; gas-ready "
         "pads) and yard space for on-site generation or battery storage.", "Reserve space and connections",
         "Grid waits are long; bridging or on-site power may be needed later and needs space and permits."),
    ]
    return [{"provision": a, "what": b, "when": c, "why": w} for a, b, c, w in items]


# =============================================================================== FIT-OUT
def fitout_scenario(name, racks, kw, cooling_chosen, gpus_per_rack, gpu_price, gpu_hw_each, i, p=None):
    R = FITOUT_RATES
    cooling, auto = effective_cooling(kw, cooling_chosen)
    reg = REGIONS[i["region"]]["factor"]
    fe, fm = R["redundancy"][i["resilience"]]
    it_kw = racks * kw
    it_mw = it_kw / 1000
    hd = kw > R["hd_threshold_kw"]
    elec = {k: v * it_kw * fe for k, v in R["electrical_per_kw"].items()}
    if hd:
        elec["High-density distribution premium"] = R["hd_electrical_premium_per_kw"] * it_kw * fe
    mech = {k: v * it_kw * fm for k, v in R["mechanical_per_kw"][cooling].items()}
    liquid = {}
    if cooling == D2C:
        lf = (p or {}).get("liquid", 0.85)
        n_cdu = math.ceil(it_mw * lf / 1.6 - 1e-9)
        n_cdu += DS.spares(n_cdu, i["resilience"], DS.DEFAULTS["cdu_group"])
        liquid[f"CDUs ({n_cdu} x 1.6 MW)"] = n_cdu * R["cdu_skid"]
    if R["manifold_per_rack"][cooling]:
        liquid["Rack manifolds / rear doors"] = R["manifold_per_rack"][cooling] * racks
    white = R["white_sf_per_rack"] * racks
    gsf = white + R["support_sf_per_mw"] * it_mw
    struct = {"Shell refurbishment & architectural fit-out": R["shell_per_gsf"] * gsf}
    if hd:
        struct["Heavy-rack slab strengthening & bracing"] = R["heavy_slab_per_sf"] * white + R["heavy_per_rack"] * racks
    systems_detail = {
        "Electrical (Div 26)": elec, "Mechanical (Div 23)": mech,
        "Liquid cooling: CDUs, manifolds (Div 23)": liquid,
        "Controls (Div 25)": {"BMS + EPMS": R["controls_per_kw"] * it_kw},
        "Structure & architecture (Div 03-09)": struct,
        "Fire protection (Div 21)": {"Pre-action sprinklers, VESDA, clean agent": R["fire_per_gsf"] * gsf},
        "Racks, power strips & cabling (Div 27)": {"Racks, rPDUs, cabling, fibre": racks * (
            R["rack_per_rack"] + R["rpdu_per_kw"] * kw + R["cabling_per_rack"] + R["cabling_per_gpu"] * gpus_per_rack)},
    }
    systems = {k: sum(v.values()) * reg for k, v in systems_detail.items()}
    direct = sum(systems.values())
    soft = direct * R["soft_pct"]
    cont = (direct + soft) * R["contingency_pct"]
    months_mid = R["design_months"] + R["construction_months"] / 2
    esc = (direct + soft + cont) * _esc(i, months_mid)
    capex = direct + soft + cont + esc
    gpus = racks * gpus_per_rack
    return {"name": name, "racks": racks, "kw": kw, "cooling": cooling, "cooling_chosen": cooling_chosen,
            "cooling_auto": auto, "it_kw": it_kw, "it_mw": it_mw, "gsf": gsf, "systems": systems,
            "systems_detail": {k: {a: b * reg for a, b in v.items()} for k, v in systems_detail.items()},
            "direct": direct, "soft": soft, "contingency": cont, "escalation": esc, "capex": capex,
            "capex_per_mw": capex / it_mw if it_mw else 0, "gpus": gpus, "gpu_price": gpu_price,
            "gpu_hw": gpus * gpu_hw_each if i.get("include_it", True) else 0.0,
            "cooling_ok": kw <= DS.MAX_KW[cooling], "cooling_max": DS.MAX_KW[cooling]}


def run_fitout(i: dict) -> dict:
    p = _platform(i)
    if i.get("size_by") == "IT MW":
        racks = math.ceil(float(i["it_mw"]) * 1000 / p["kw"] - 1e-9)
    else:
        racks = int(i["racks"])
    cur_p = dict(PL.custom_platform(float(i["current_kw"])), weight_lb=1_200, rack_w_m=0.6, rack_d_m=1.2,
                 white_sf=FITOUT_RATES["white_sf_per_rack"])
    cur = fitout_scenario("Current", racks, float(i["current_kw"]), i.get("current_cooling") or AIR,
                          int(i["current_gpus"]), float(i["current_gpu_price"]), float(i["current_gpu_hw"]), i, cur_p)
    fut_cool_choice = i.get("cooling")
    fut = fitout_scenario("Future-ready", racks, p["kw"], fut_cool_choice, p["gpus"], _gpu_price(i, p),
                          p["it_per_rack"] / max(p["gpus"], 1), i, p)
    for s, pp in ((cur, cur_p), (fut, p)):
        dz = _design(pp, s["racks"], s["cooling"], i, 0.0, gsf_per_mw=s["gsf"] / max(s["it_mw"], 1e-9))
        s["design"] = dz
    new_service = fut["design"]["v"]["service_mva"] > cur["design"]["v"]["service_mva"] * 1.1
    inter = (float(i["interconnect"]) if i.get("interconnect") is not None
             else 80_000 * fut["design"]["v"]["service_mw"] if new_service else 0.0)
    cl = CL.fitout_lines(fut, p, i, FITOUT_RATES, REGIONS[i["region"]]["factor"], inter, i.get("include"))
    fut["cost_lines"] = cl
    fut["construction_cost"] = fut["capex"]
    fut["checked_total"] = cl["total"]
    fut_it = _it_total(i, cl, cl["rows"][CL.KEYS.index("gpu")]["amount"], cl["rows"][CL.KEYS.index("fabric")]["amount"])
    for s in (cur, fut):
        if s is fut:
            eco = _economics(i, s["it_mw"], s["design"], cl["non_it_total"], s["capex"], s["gpus"], s["gpu_price"], fut_it)
        else:
            eco = _economics(i, s["it_mw"], s["design"], s["capex"], s["capex"], s["gpus"], s["gpu_price"], s["gpu_hw"])
        s.update(eco)
    up = _retrofit(cur, fut, i)
    fut_paths = future_paths(i, p, fut["it_mw"], fut["cooling"], fut["design"], mode="fitout", fit=fut)
    sch, cx = _plan(i, p, fut["it_mw"], fut["racks"], fut["design"], gf=False,
                    needs_new_service=new_service, horizon_active=bool(fut_paths.get("active")))
    res = {"mode": "fitout", "inputs": i, "platform": p, "current": cur, "future": fut, "upgrade": up, "cost_lines": cl,
           "future_paths": fut_paths, "long_lead": LONG_LEAD, "schedule": sch, "cx": cx}
    res["warnings"] = _warnings(res)
    res["checks"] = benchmark_checks(res)
    res["recommendation"] = recommendation(res)
    return res


def _retrofit(cur, fut, i):
    R = FITOUT_RATES
    Y = min(R["retrofit_year"], int(i["years"]))
    rows, direct = [], 0.0
    for sysname, fcost in fut["systems"].items():
        ccost = cur["systems"].get(sysname, 0.0)
        reused = ccost * R["retrofit_reuse"].get(sysname, 0.0)
        new = max(fcost - reused, 0.0) * R["retrofit_premium"]
        direct += new
        rows.append((sysname, ccost, fcost, reused, new))
    demo = cur["direct"] * R["retrofit_demo_pct"]
    direct += demo
    soft = direct * R["soft_pct"]
    cont = (direct + soft) * R["contingency_pct"]
    retro = (direct + soft + cont) * (1 + float(i.get("escalation") or 0)) ** Y
    downtime = cur["revenue"] / 12 * R["retrofit_downtime_months"]
    H, r = int(i["years"]), OPEX["discount_rate"]
    fa = fut["cash_flows"]
    fb = [-(cur["capex"] + cur["it_total"])]
    for y in range(1, H + 1):
        if y < Y:
            cf = cur["cash_flows"][y]
        elif y == Y:
            cf = cur["cash_flows"][y] - downtime - retro - fut["it_total"]
        else:
            cf = fut["cash_flows"][min(y - Y, len(fut["cash_flows"]) - 1)]
        fb.append(cf)
    up = {"year": Y, "rows": rows, "demo": demo, "retrofit_capex": retro, "downtime_cost": downtime,
          "downtime_months": R["retrofit_downtime_months"], "day_one_capex": fut["capex"],
          "path_b_total": cur["capex"] + retro + downtime, "day_one_premium": fut["capex"] - cur["capex"],
          "penalty": cur["capex"] + retro + downtime - fut["capex"], "npv_a": _npv(r, fa), "npv_b": _npv(r, fb),
          "flows_a": fa, "flows_b": fb}
    up["recommended"] = ("Fit out future-ready now" if up["npv_a"] >= up["npv_b"]
                         else "Keep the current design, retrofit later")
    return up


# =============================================================================== checks
def _warnings(res):
    w = []
    i = res["inputs"]
    designs = ([("Design", res["design"])] if res["mode"] == "greenfield"
               else [("Current", res["current"]), ("Future-ready", res["future"])])
    for name, d in designs:
        kw = d["kw"]
        chosen = i.get("current_cooling") if name == "Current" else i.get("cooling")
        if d["cooling_auto"] and chosen and chosen != D2C:
            w.append(f"{name}: {kw:.0f} kW/rack is above 45 kW/rack, so direct-to-chip (D2C) liquid cooling was "
                     f"selected automatically ({chosen} cannot cool this density).")
        if kw > DS.MAX_KW[d["cooling"]]:
            w.append(f"{name}: {kw:.0f} kW/rack is above what {d['cooling']} can practically cool "
                     f"(about {DS.MAX_KW[d['cooling']]:.0f} kW/rack). Choose rear-door (Hybrid) or D2C.")
    p = res["design"]["platform"] if res["mode"] == "greenfield" else res["platform"]
    if p.get("status") == "announced":
        w.append(f"{p['label']}: announced roadmap product. Rack power, weight, price and rental rate are estimates; "
                 "confirm with the platform and system makers before committing budget.")
    if p.get("status") == "speculative":
        w.append(f"{p['kw']:,.0f} kW/rack is beyond announced products: the cost basis is speculative.")
    if p.get("status") == "estimated":
        w.append(f"{p['label']}: values are estimates (no public per-rack spec).")
    if res["mode"] == "greenfield":
        if float(i.get("months_to_power") or 36) < 18:
            w.append("Months to utility power below 18 is optimistic for new large loads; 2026 market reports show average "
                     "grid-connection waits above 4 years in primary markets. Use the utility's committed timing.")
        if res["design"]["design"]["v"]["service_mva"] > 300:
            w.append("Utility service above 300 MVA usually needs a dedicated transmission-level substation and "
                     "multi-year interconnection studies.")
    else:
        if res["future"]["it_mw"] > 60:
            w.append(f"The future-ready hall needs {res['future']['it_mw']:,.0f} MW of IT power: existing buildings "
                     "rarely have this much utility capacity. Confirm firm MW with the utility.")
        if i["current_kw"] >= res["future"]["kw"]:
            w.append("The GPU platform is not denser than the current racks; the upgrade comparison is trivial.")
    return w


# Documented sanity ranges (see docs/VERIFICATION.md). Used by tests and shown in the app.
RANGES = {
    "facility_per_mw_air": (9e6, 16e6, "Air-cooled (<=30 kW/rack) facility $/MW IT: 2026 market outlooks $11.3M/MW shell & core, "
                                       "$17.6M/MW all-in"),
    "fitout_per_mw": (7e6, 30e6, "Fit-out of an existing shell $/MW IT (no land, site or new shell): "
                                 "assumption, below the all-in new-build ranges above"),
    "facility_per_mw_hd": (14e6, 40e6, "High-density / liquid facility $/MW IT: $15-25M+/MW (AI fit-out up to $25M/MW; "
                                       "Kyber-class above)"),
    "pue": (1.10, 1.55, "PUE: 2025 industry survey average 1.54; new >=20 MW sites 1.44; liquid-cooled about 1.1-1.25"),
    "power_cost": (0.05, 0.20, "Power $/kWh: US government data, industrial 2026 YTD about $0.09/kWh; Europe/Asia higher"),
    "transformer_weeks": (100, 160, "Large power transformer lead time: 2025 industry supply-chain study average "
                                    "128 weeks; 2026 quotes 100-150+ weeks"),
    "wue": (0.0, 2.6, "WUE L/kWh: dry/closed loop about 0-0.5; evaporative towers about 1.8-2.4"),
}
GPU_MARKET = {   # Oct 2026 public trackers: (low, high) $/GPU-hr across spot, reserved and on-demand
    "H100 HGX": (1.30, 4.50), "H200 HGX": (2.09, 5.40), "B200 HGX": (3.69, 8.60), "GB200 NVL72": (6.00, 16.00),
    "GB300 NVL72": (6.00, 17.80),
}


def benchmark_checks(res):
    out = []
    i = res["inputs"]
    if res["mode"] == "greenfield":
        d = res["design"]
        fpm, kw, pue = d["facility_per_mw"], d["kw"], d["design"]["v"]["pue"]
        wue = d["design"]["v"]["wue"]
        price, pc, name = d["gpu_price"], d["power_cost"], d["platform"]["name"]
    else:
        f = res["future"]
        fpm, kw, pue = f["capex_per_mw"], f["kw"], f["design"]["v"]["pue"]
        wue = f["design"]["v"]["wue"]
        price, pc, name = f["gpu_price"], f["power_cost"], res["platform"]["name"]
    key = ("fitout_per_mw" if res["mode"] == "fitout" else
           "facility_per_mw_air" if kw <= 30 else "facility_per_mw_hd")
    for k, val in ((key, fpm), ("pue", pue), ("power_cost", pc), ("transformer_weeks", TRANSFORMER_WEEKS),
                   ("wue", wue)):
        lo, hi, src = RANGES[k]
        out.append({"check": k, "value": val, "low": lo, "high": hi, "ok": lo <= val <= hi, "source": src})
    if name in GPU_MARKET:
        lo, hi = GPU_MARKET[name]
        out.append({"check": "gpu_price", "value": price, "low": lo, "high": hi, "ok": lo <= price <= hi,
                    "source": f"{name} rental $/GPU-hr, public trackers Oct 2026 (spot to on-demand)"})
    return out


def _money(x):
    return f"${x / 1e9:,.2f}B" if abs(x) >= 1e9 else f"${x / 1e6:,.1f}M"


def _hz(h):
    return h.replace(" years", "-year") if h and h[0].isdigit() else h


def target_phrase(f) -> str:
    """The future target in words. The horizon is the planning window; the target racks go in earlier, in year
    f['year'] after ready for IT (defaults 3, 5, 8), e.g. 10-year horizon -> 600 kW/rack installed in year 5."""
    return f"a {f['target_kw']:,.0f} kW/rack target installed in year {f['year']} after ready for IT"


def target_sentence(f) -> str:
    t = target_phrase(f)
    return t[0].upper() + t[1:]


def recommendation(res):
    if res["mode"] == "greenfield":
        d, f = res["design"], res["future"]
        pb = d["payback"]
        econ = "" if pb is not None else " It does not pay back within the analysis period."
        if f["active"]:
            return {"headline": f["best"], "detail": f"Lowest present cost over the {_hz(f['horizon'])} horizon, "
                    f"with {target_phrase(f)}.{econ}"}
        return {"headline": "Build as designed", "detail": f"{f['reason']}{econ}"}
    up, f = res["upgrade"], res["future_paths"]
    head = up["recommended"]
    det = (f"NPV {_money(up['npv_a'])} vs {_money(up['npv_b'])} for keeping {res['current']['kw']:.0f} kW racks and "
           f"retrofitting in year {up['year']}.")
    if f["active"]:
        det += f" For the {_hz(f['horizon'])} horizon ({target_phrase(f)}): {f['best'].lower()}."
    return {"headline": head, "detail": det}


def run_model(inp: dict | None = None) -> dict:
    i = merged(inp)
    return run_greenfield(i) if is_greenfield(i) else run_fitout(i)


# =============================================================================== LLM payload
def key_design(dz):
    v = dz["v"]
    keys = ["it_kw", "fac_peak_kw", "pue", "service_mva", "main_tx", "unit_subs_it", "gens", "fuel_gal",
            "ups_modules", "battery_kwh", "rack_amps", "busway_rating", "cool_tons", "liquid_kw", "air_kw",
            "cdus", "tcs_lps", "fws_lps", "chw_lps", "reject_kw", "wue", "water_m3", "white_sf", "gross_sf",
            "rack_psf", "land_acres"]
    return {k: (round(v.get(k, 0)) if abs(v.get(k, 0)) >= 100 else round(v.get(k, 0), 2)) for k in keys}


def summary_for_llm(res: dict) -> dict:
    i = res["inputs"]
    base = {"project": i["project_name"], "project_type": i["project_type"], "location": i["region"],
            "resilience": RESILIENCE[i["resilience"]], "disclaimer": DISCLAIMER,
            "warnings": res["warnings"], "recommendation": res["recommendation"],
            "benchmark_checks": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items()}
                                 for c in res["checks"]]}
    S = res["cx"]["schedule"]
    base["schedule"] = {
        "notice_to_proceed_month": round(S["ntp"], 1), "build_months": round(S["build_months"], 1),
        "energization_start_month": round(S["energization"], 1), "commissioning_start_month": round(S["cx_start"], 1),
        "substantial_completion_month": round(S["sc"], 1), "critical_path": S["critical_path"],
        "ready_for_it": S["range_text"], "ready_for_it_months_low": round(S["sc_low"], 1),
        "ready_for_it_months_high": round(S["sc_high"], 1),
        "order_by": [{"item": x["item"], "send_rfq_months_after_start": round(max(x["rfq"], 0.0), 1),
                      "place_po_months_after_start": round(max(x["po"], 0.0), 1),
                      "needed_months_after_start": round(x["need"], 1),
                      "order_months_before_needed": round(x["order_ahead"]), "flag": x["flag"]} for x in S["items"]]}
    base["risk_register"] = [{"category": r["category"], "mitigation": r["mitigation"], "owner": r["owner"],
                              "impact_months": f"{r['impact_low']}-{r['impact_high']}"}
                             for r in res["cx"]["risks"] if r["active"]]
    base["estimate_accuracy"] = CX.ESTIMATE_LABEL
    cl = res["design"]["cost_lines"] if res["mode"] == "greenfield" else res["cost_lines"]
    base["cost_lines"] = [{"line": r["label"], "usd": round(r["amount"]), "included": r["included"]} for r in cl["rows"]]
    base["total_capex_usd"] = round(cl["total"])
    base["total_capex_usd_per_mw_it"] = round(cl["per_mw"])
    base["total_if_every_line_ticked_usd"] = round(cl["total_all"])
    base["how_to_avoid_delays"] = G.HOW_TO_AVOID
    base["legal"] = G.LEGAL
    base["commissioning"] = {"levels": [c["level"] + " " + c["name"] for c in CX.CX_LEVELS], "hard_stop": CX.HARD_STOP,
                             "load_banks": res["cx"]["load_banks"]["notes"][:2]}
    fut = res["future"] if res["mode"] == "greenfield" else res["future_paths"]
    fp = None
    if fut.get("active"):
        fp = {"horizon": fut["horizon"], "target_kw_per_rack": fut["target_kw"], "target_year": fut["year"],
              "target_in_words": target_phrase(fut),
              "paths_usd": [{"path": x["path"], "day_one": round(x["day1"]), "later_nominal": round(x["later_nominal"]),
                             "downtime_months": x["downtime_months"], "present_cost": round(x["pv_total"])}
                            for x in fut["paths"]],
              "best": fut["best"], "provisions": fut["provisions"]}
    if res["mode"] == "greenfield":
        d = res["design"]
        return {**base, "single_build": "Greenfield is ONE new build: there is no current-vs-future comparison.",
                "platform": d["platform"]["label"], "kw_per_rack": d["kw"], "racks": d["racks"],
                "it_mw": round(d["it_mw"], 2), "cooling": d["cooling"],
                "cooling_rule": D2C_NOTE if d["cooling_auto"] else "user choice (<= 45 kW/rack)",
                "design_calculations": key_design(d["design"]),
                "facility_usd_per_mw_it": round(d["facility_per_mw"]),
                "it_hardware_usd": round(d["it_total"]),
                "opex_usd_per_year": round(d["opex"]), "revenue_year1_usd": round(d["revenue"]),
                "gpu_price_per_hr": d["gpu_price"], "npv_usd": round(d["npv"]),
                "payback_years": None if d["payback"] is None else round(d["payback"], 1),
                "schedule_months": {k: round(v, 1) for k, v in d["schedule"]["drivers"].items()},
                "critical_path": d["schedule"]["critical_path"], "future_ready": fp}
    cur, f, up = res["current"], res["future"], res["upgrade"]

    def s(x):
        return {"racks": x["racks"], "kw_per_rack": x["kw"], "cooling": x["cooling"], "it_mw": round(x["it_mw"], 2),
                "construction_cost_like_for_like_usd": round(x["capex"]), "construction_per_mw_usd": round(x["capex_per_mw"]),
                "opex_usd": round(x["opex"]), "revenue_usd": round(x["revenue"]),
                "payback_years": None if x["payback"] is None else round(x["payback"], 1),
                "design_calculations": key_design(x["design"])}
    return {**base, "platform": res["platform"]["label"], "current": s(cur), "future_ready": s(f),
            "retrofit_comparison": {"retrofit_year": up["year"], "retrofit_capex_usd": round(up["retrofit_capex"]),
                                    "downtime_cost_usd": round(up["downtime_cost"]),
                                    "penalty_vs_day_one_usd": round(up["penalty"]),
                                    "npv_day_one_usd": round(up["npv_a"]), "npv_retrofit_usd": round(up["npv_b"]),
                                    "engine_recommendation": up["recommended"]},
            "future_proof_horizon": fp}


if __name__ == "__main__":
    import json
    print(json.dumps(summary_for_llm(run_model()), indent=1, default=str)[:4000])
