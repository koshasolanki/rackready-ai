"""
RackReady AI - deterministic cost engine.

Two project types:
  * Existing building fit-out: current vs future-ready density in an existing hall, plus a
    build-current-then-retrofit path. Unit rates in ASSUMPTIONS (indicative, NoVA = 1.00). The
    workbook excludes brownfield (01_ASSUME8 r15), so fit-out keeps RackReady trade rates but uses
    the workbook for D2C CDU sizing/skid price and liquid PUE.
  * Greenfield (new build from scratch): ONE design priced from the user's cost workbook
    (workbook_basis.py): RIGHT facility $/IT MW by GPU platform, 22-division CSI split, N+1
    quantities, change pricing for redundancy/fuel/labor/contingency, plus the scope the
    workbook keeps outside facility $ (land, utility-side interconnect, IT iron, AI fabric).

Rule for every design: above 45 kW/rack the cooling is Direct-to-chip (D2C) liquid,
auto-selected and not overridable. All figures are INDICATIVE PLANNING NUMBERS, not a bid.
"""
from __future__ import annotations

import math
from copy import deepcopy

import workbook_basis as WB

D2C = "Direct-to-chip (D2C) liquid"
D2C_AUTO_KW = 45.0
D2C_NOTE = "D2C auto-selected above 45 kW/rack"

# =============================================================================
# ASSUMPTIONS - fit-out unit rates (indicative, 2026 USD, NoVA = 1.00)
# =============================================================================
ASSUMPTIONS = {
    "d2c_auto_threshold_kw": D2C_AUTO_KW,
    # ---- CSI Division 26 - Electrical, $ per kW of IT load (Tier III, N+1) ----
    "electrical_per_kw": {
        "MV service & transformers": 650,
        "Switchgear & switchboards": 900,
        "UPS & batteries": 950,
        "Generators & fuel systems": 850,
        "Busway, PDUs & RPPs": 450,
        "Grounding, lighting & branch power": 250,
    },
    "hd_electrical_premium_per_kw": 600,
    "hd_threshold_kw_per_rack": 50,

    # ---- CSI Division 23 - Mechanical, $ per kW of IT load by cooling type ----
    # D2C: CDUs are counted with the workbook rule (20_CSI8_MATRIX D20, 12_CHANGE_PRICING F8),
    # dry/adiabatic hybrid reject + residual air share (01_ASSUME8 r49/r54, 25_REDUNDANCY r12).
    "mechanical_per_kw": {
        "Air": {
            "Chillers / central plant": 950, "CRAH / fan walls": 850,
            "Piping & pumps": 350, "Heat rejection": 450},
        "Hybrid (rear-door + air)": {
            "Chillers / central plant": 900, "CRAH / fan walls": 500,
            "Rear-door heat exchangers": 650, "Piping & pumps": 450, "Heat rejection": 400},
        D2C: {
            "Trim chillers / central plant": 450, "Residual air (fan walls / CRAH)": 350,
            "Piping, headers & pumps (W32 / PG25)": 950,
            "Dry / adiabatic hybrid heat rejection": 900},
    },
    "cdu_mw_each": 1.6,                     # 01_ASSUME8 r51 (B200..GB300)
    "cdu_skid_cost": WB.CHANGE_UNITS["cdu_skid"],  # 12_CHANGE_PRICING F8 = $1.05M
    "liquid_per_rack": {"Air": 0, "Hybrid (rear-door + air)": 18_000, D2C: 30_000},
    "pue": {"Air": 1.50, "Hybrid (rear-door + air)": 1.38,
            D2C: WB.PLATFORMS["GB300 NVL72"]["pue"]},   # 1.20, 01_ASSUME8 r33
    "max_kw_per_rack": {"Air": 30, "Hybrid (rear-door + air)": 45, D2C: 250},

    "controls_per_kw": {"BMS": 120, "EPMS / power monitoring": 130},

    "white_space_sf_per_rack": 30,
    "support_sf_per_mw": 3_000,
    "shell_cost_per_gsf": 300,
    "fire_cost_per_gsf": 14,
    "heavy_rack_slab_premium_per_sf": 75,
    "heavy_rack_per_rack": 2_500,

    "rack_enclosure_per_rack": 6_000,
    "rpdu_per_kw": 120,
    "cabling_per_rack": 12_000,
    "cabling_per_gpu": 400,

    "soft_costs_pct": 0.14,
    "contingency_pct": 0.10,

    "redundancy": {
        "N":   {"electrical": 0.85, "mechanical": 0.90},
        "N+1": {"electrical": 1.00, "mechanical": 1.00},
        "2N":  {"electrical": 1.35, "mechanical": 1.20},
    },
    "tier": {"Tier II": 0.90, "Tier III": 1.00, "Tier IV": 1.15},
    "regions": {
        "US - Northern Virginia": 1.00,
        "US - Dallas / Texas": 0.93,
        "US - Phoenix": 0.96,
        "US - NYC / NJ": 1.25,
        "Ireland - Dublin": 1.10,
        "Nordics - Stockholm / Oslo": 1.08,
        "Singapore": 1.15,
        "India - Mumbai": 0.70,
    },
    "retrofit_premium": 1.35,
    "retrofit_demo_pct": 0.06,
    "retrofit_downtime_months": 4,
    "retrofit_year": 3,
    "retrofit_reuse": {
        "Electrical (Div 26)": 0.45, "Mechanical (Div 23)": 0.15,
        "Liquid cooling / CDU / TCS (Div 23)": 0.0, "Controls BMS/EPMS": 0.50,
        "Structural & architectural (Div 03/05/09)": 0.80,
        "Fire protection (Div 21)": 0.60, "Networking & racks (Div 27)": 0.40,
    },

    # ---- OpEx (indicative; the workbook has no OpEx sheet) ----
    "maintenance_pct_of_capex": 0.02,
    "other_opex_pct_of_capex": 0.006,
    "staff_base_fte": 8,
    "staff_fte_per_mw": 0.5,
    "staff_cost_per_fte": 140_000,
    "cooling_share_of_overhead": 0.80,

    # ---- Revenue / IT hardware (fit-out) ----
    "gpu_hw_cost_current": 30_000,
    "gpu_hw_cost_future": WB.PLATFORMS["GB300 NVL72"]["it_per_rack"] / 72,  # 01_ASSUME8 r9 / r8
    "gpu_hw_life_years": 5,
    "gpu_refresh_cost_factor": 0.70,
    "discount_rate": 0.08,

    # ---- Greenfield: only what the workbook does NOT provide (indicative) ----
    "greenfield": {
        "months_to_power": 24,          # inside workbook's 12-48 mo interconnect range
        "design_permit_months": 9,
        "construction_months": 18,
        "procurement_start_month": 3,
        "insurance_pct": 0.003,         # of facility CapEx
        "property_tax_pct": 0.0,        # workbook excludes tax (02_WHAT_RIGHT r6); user input
        # $/GPU-hr rental, indicative only (workbook has no revenue data)
        "gpu_hr_price": {"H100 HGX": 2.25, "H200 HGX": 2.75, "B200 HGX": 3.25, "GB200 NVL72": 3.75,
                         "GB300 NVL72": 4.25, "Vera Rubin": 7.00, "TPU Ironwood": 2.50, "Kyber": 3.50,
                         "Custom": 3.50},
    },
}

LONG_LEAD = [
    ("MV / power transformers", "Div 26", 80, 130),
    ("MV switchgear & switchboards", "Div 26", 52, 80),
    ("Diesel generators", "Div 26", 52, 78),
    ("UPS modules & batteries", "Div 26", 30, 52),
    ("Busway (high-amp overhead)", "Div 26", 16, 30),
    ("Chillers / dry coolers", "Div 23", 30, 50),
    ("CDUs (liquid-to-liquid)", "Div 23", 20, 40),
    ("Rear-door heat exchangers", "Div 23", 16, 26),
]

COOLING_TYPES = list(ASSUMPTIONS["pue"].keys())
REGIONS = list(ASSUMPTIONS["regions"].keys())
PROJECT_TYPES = ["Existing building fit-out", "Greenfield - new build from scratch"]
FITOUT, GREENFIELD = PROJECT_TYPES
PLATFORM_CHOICES = WB.PLATFORM_NAMES + ["Custom"]
GF_REDUNDANCY = ["N+1 (workbook base)", "N+2 generators (C1)", "2N generators (C2)",
                 "2N generators + 2N UPS (C2+C3)"]

DEFAULT_INPUTS = {
    "project_name": "AI Hall 1 - 200 racks",
    "racks": 200,
    "current_kw": 15.0,
    "future_kw": 140.0,
    "current_cooling": "Air",
    "future_cooling": D2C,
    "region": "US - Northern Virginia",
    "power_cost": 0.08,
    "utilization": 0.80,
    "tier": "Tier III",
    "redundancy": "N+1",
    "gpus_per_rack_current": 8,
    "gpus_per_rack_future": 72,
    "gpu_price_current": 2.50,
    "gpu_price_future": 3.50,
    "horizon_years": 10,
    "include_gpu_hw": True,
    "project_type": FITOUT,
    # ---- greenfield (single design) ----
    "gf_platform": WB.DEFAULT_PLATFORM,
    "gf_size_by": "IT MW",
    "gf_it_mw": float(WB.CAMPUS_MW),
    "gf_racks": 200,
    "gf_custom_kw": 135.0,
    "gf_custom_gpus": None,
    "gf_custom_it_per_rack": None,
    "gf_cooling": None,               # None = workbook basis; only a choice at <= 45 kW/rack
    "gf_redundancy": GF_REDUNDANCY[0],
    "gf_fuel_96h": False,
    "gf_union_seismic_piles": False,
    "gf_contingency_pct": None,       # None = workbook 4%
    "gf_it_fitout": False,            # 01_ASSUME8 r81, workbook default OFF
    "gf_land": None,                  # None = workbook $5M once
    "gf_interconnect": None,          # None = workbook $8M once
    "gf_include_fabric": False,       # 14_EIGHT_DEEP r47, excluded from facility $
    "gf_owner_costs_pct": 0.0,        # owner staff / A-E / permits (excluded by workbook)
    "gf_escalation_pct": 0.0,         # workbook basis is 2026; escalation past 2026 excluded
    "gf_months_to_power": None,
    "gf_construction_months": None,
    "gf_gpu_price": None,             # None = indicative by platform
    "gf_property_tax_pct": None,
}

HOURS = 8760


def is_greenfield(inp: dict) -> bool:
    return str(inp.get("project_type", "")).lower().startswith("greenfield")


def effective_cooling(kw: float, chosen: str, A=ASSUMPTIONS) -> tuple[str, bool]:
    """Above the threshold (45 kW/rack) the cooling is always D2C. Returns (cooling, auto)."""
    if kw > A["d2c_auto_threshold_kw"]:
        return D2C, True
    if chosen not in A["pue"]:
        chosen = "Air"
    return chosen, False


def _npv(rate: float, flows: list[float]) -> float:
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))


def _flows(invest, net, gpu_hw, H, A):
    flows = [-invest]
    for y in range(1, H + 1):
        cf = net
        if gpu_hw and y % A["gpu_hw_life_years"] == 0 and y < H:
            cf -= gpu_hw * A["gpu_refresh_cost_factor"]
        flows.append(cf)
    return flows


def mech_items_for(cooling: str, it_kw: float, A=ASSUMPTIONS) -> dict:
    items = {k: v * it_kw for k, v in A["mechanical_per_kw"][cooling].items() if v}
    return items


def cdu_cost(cooling: str, it_mw: float, A=ASSUMPTIONS) -> tuple[int, float]:
    if cooling != D2C:
        return 0, 0.0
    n = math.ceil(round(it_mw / A["cdu_mw_each"], 9)) + 1
    return n, n * A["cdu_skid_cost"]


# =============================================================================
# FIT-OUT: one scenario (current or future-ready)
# =============================================================================
def scenario(name, racks, kw, cooling_chosen, gpus_per_rack, gpu_price, gpu_hw_cost,
             inp, A=ASSUMPTIONS) -> dict:
    cooling, auto = effective_cooling(kw, cooling_chosen, A)
    auto = kw > A["d2c_auto_threshold_kw"]
    region_f = A["regions"][inp["region"]]
    red = A["redundancy"][inp["redundancy"]]
    tier_f = A["tier"][inp["tier"]]
    it_kw = racks * kw
    it_mw = it_kw / 1000
    pue = A["pue"][cooling]
    high_density = kw > A["hd_threshold_kw_per_rack"]

    elec_items = {k: v * it_kw for k, v in A["electrical_per_kw"].items()}
    if high_density:
        elec_items["High-density distribution premium"] = A["hd_electrical_premium_per_kw"] * it_kw
    elec_items = {k: v * red["electrical"] for k, v in elec_items.items()}

    mech_items = {k: v * red["mechanical"] for k, v in mech_items_for(cooling, it_kw, A).items()}
    n_cdu, cdus = cdu_cost(cooling, it_mw, A)
    cdus *= red["mechanical"]
    manifolds = A["liquid_per_rack"][cooling] * racks
    liquid = cdus + manifolds
    controls = sum(A["controls_per_kw"].values()) * it_kw

    white_sf = A["white_space_sf_per_rack"] * racks
    gsf = white_sf + A["support_sf_per_mw"] * it_mw
    shell = A["shell_cost_per_gsf"] * gsf
    slab = 0.0
    if high_density:
        slab = A["heavy_rack_slab_premium_per_sf"] * white_sf + A["heavy_rack_per_rack"] * racks
    fire = A["fire_cost_per_gsf"] * gsf
    network = racks * (A["rack_enclosure_per_rack"] + A["rpdu_per_kw"] * kw
                       + A["cabling_per_rack"] + A["cabling_per_gpu"] * gpus_per_rack)

    systems = {
        "Electrical (Div 26)": sum(elec_items.values()),
        "Mechanical (Div 23)": sum(mech_items.values()),
        "Liquid cooling / CDU / TCS (Div 23)": liquid,
        "Controls BMS/EPMS": controls,
        "Structural & architectural (Div 03/05/09)": shell + slab,
        "Fire protection (Div 21)": fire,
        "Networking & racks (Div 27)": network,
    }
    f = region_f * tier_f
    systems = {k: v * f for k, v in systems.items()}
    direct = sum(systems.values())
    soft = direct * A["soft_costs_pct"]
    contingency = (direct + soft) * A["contingency_pct"]
    capex = direct + soft + contingency

    detail = []
    for k, v in elec_items.items():
        detail.append(("Electrical (Div 26)", k, v * f))
    for k, v in mech_items.items():
        detail.append(("Mechanical (Div 23)", k, v * f))
    if cdus:
        detail.append(("Mechanical (Div 23)", f"CDUs: {n_cdu} x 1.6 MW L2L skids, N+1 (workbook rule)", cdus * f))
    if manifolds:
        detail.append(("Mechanical (Div 23)", "Rack manifolds / TCS / RDHx", manifolds * f))
    detail.append(("Controls", "BMS + EPMS", controls * f))
    detail.append(("Structural & arch", f"Shell & fit-out ({gsf:,.0f} gsf)", shell * f))
    if slab:
        detail.append(("Structural & arch", "Heavy-rack slab & bracing", slab * f))
    detail.append(("Fire protection (Div 21)", "Pre-action / clean agent", fire * f))
    detail.append(("Networking & racks (Div 27)", "Racks, rPDUs, cabling, fiber", network * f))

    avg_it_kw = it_kw * inp["utilization"]
    it_energy = avg_it_kw * HOURS * inp["power_cost"]
    overhead_energy = avg_it_kw * (pue - 1) * HOURS * inp["power_cost"]
    cooling_energy = overhead_energy * A["cooling_share_of_overhead"]
    other_fac_energy = overhead_energy - cooling_energy
    maintenance = capex * A["maintenance_pct_of_capex"]
    other = capex * A["other_opex_pct_of_capex"]
    fte = A["staff_base_fte"] + A["staff_fte_per_mw"] * it_mw
    staffing = fte * A["staff_cost_per_fte"] * region_f
    opex_items = {
        "IT energy": it_energy,
        "Cooling energy": cooling_energy,
        "Other facility energy (losses, lighting)": other_fac_energy,
        "Maintenance (MEP PPM, spares)": maintenance,
        "Staffing": staffing,
        "Insurance & property tax": other,
    }
    opex = sum(opex_items.values())
    pue_saving = avg_it_kw * (A["pue"]["Air"] - pue) * HOURS * inp["power_cost"]

    gpus = racks * gpus_per_rack
    revenue = gpus * gpu_price * inp["utilization"] * HOURS
    gpu_hw = gpus * gpu_hw_cost if inp.get("include_gpu_hw", True) else 0.0
    total_invest = capex + gpu_hw
    net = revenue - opex
    H = int(inp["horizon_years"])
    flows = _flows(total_invest, net, gpu_hw, H, A)
    return {
        "name": name, "racks": racks, "kw_per_rack": kw, "cooling": cooling,
        "cooling_chosen": cooling_chosen, "cooling_auto": auto,
        "it_kw": it_kw, "it_mw": it_mw, "pue": pue,
        "facility_mw": it_mw * pue, "avg_facility_mw": it_mw * pue * inp["utilization"],
        "gsf": gsf, "high_density": high_density, "cdus": n_cdu,
        "systems": systems, "detail": detail, "direct": direct, "soft": soft,
        "contingency": contingency, "capex": capex, "capex_per_mw": capex / it_mw,
        "capex_per_rack": capex / racks,
        "opex_items": opex_items, "opex": opex, "pue_saving_vs_air": pue_saving,
        "gpus": gpus, "gpu_price": gpu_price, "revenue": revenue, "gpu_hw": gpu_hw,
        "total_invest": total_invest, "net_annual": net, "cash_flows": flows,
        "npv": _npv(A["discount_rate"], flows),
        "simple_payback": total_invest / net if net > 0 else None,
        "roi_horizon": (sum(flows[1:]) - total_invest) / total_invest if total_invest else 0,
        "cooling_ok": kw <= A["max_kw_per_rack"][cooling],
        "cooling_max": A["max_kw_per_rack"][cooling],
    }


def _cooling_warnings(s, A=ASSUMPTIONS):
    w = []
    if s.get("cooling_auto") and s.get("cooling_chosen") not in (None, D2C):
        w.append(f"{s['name']}: {s['kw_per_rack']:.0f} kW/rack is above 45 kW/rack, so "
                 f"{D2C} was auto-selected (the {s['cooling_chosen']} choice is not allowed).")
    if not s["cooling_ok"]:
        if s["cooling"] == D2C:
            w.append(f"{s['name']}: {s['kw_per_rack']:.0f} kW/rack is beyond typical D2C cold-plate "
                     f"range (~{s['cooling_max']} kW); the workbook prices Kyber-class as D2C + sidecar.")
        else:
            w.append(f"{s['name']}: {s['kw_per_rack']:.0f} kW/rack exceeds the practical limit of "
                     f"{s['cooling']} (~{s['cooling_max']} kW/rack). Choose Hybrid (RDHx) or D2C.")
    return w


def run_fitout(i: dict, A=ASSUMPTIONS) -> dict:
    cur = scenario("Current", i["racks"], i["current_kw"], i["current_cooling"],
                   i["gpus_per_rack_current"], i["gpu_price_current"], A["gpu_hw_cost_current"], i, A)
    fut = scenario("Future-ready", i["racks"], i["future_kw"], i["future_cooling"],
                   i["gpus_per_rack_future"], i["gpu_price_future"], A["gpu_hw_cost_future"], i, A)
    Y = min(int(A["retrofit_year"]), int(i["horizon_years"]))
    reuse = A["retrofit_reuse"]
    retro_rows, retro_direct = [], 0.0
    for sysname, fut_cost in fut["systems"].items():
        cur_cost = cur["systems"].get(sysname, 0.0)
        reused = cur_cost * reuse.get(sysname, 0.0)
        new_work = max(fut_cost - reused, 0.0) * A["retrofit_premium"]
        retro_direct += new_work
        retro_rows.append((sysname, cur_cost, fut_cost, reused, new_work))
    demo = cur["direct"] * A["retrofit_demo_pct"]
    retro_direct += demo
    retro_soft = retro_direct * A["soft_costs_pct"]
    retro_cont = (retro_direct + retro_soft) * A["contingency_pct"]
    retrofit_capex = retro_direct + retro_soft + retro_cont
    downtime_cost = cur["revenue"] / 12 * A["retrofit_downtime_months"]
    H, r = int(i["horizon_years"]), A["discount_rate"]
    flows_a = fut["cash_flows"]
    flows_b = [-cur["total_invest"]]
    for y in range(1, H + 1):
        if y < Y:
            cf = cur["net_annual"]
        elif y == Y:
            cf = cur["net_annual"] - downtime_cost - retrofit_capex - fut["gpu_hw"]
        else:
            cf = fut["net_annual"]
            if fut["gpu_hw"] and (y - Y) % A["gpu_hw_life_years"] == 0 and y < H:
                cf -= fut["gpu_hw"] * A["gpu_refresh_cost_factor"]
        flows_b.append(cf)
    up = {
        "retrofit_year": Y, "rows": retro_rows, "demo": demo, "retrofit_capex": retrofit_capex,
        "downtime_cost": downtime_cost, "downtime_months": A["retrofit_downtime_months"],
        "path_a_capex": fut["capex"], "path_b_capex": cur["capex"] + retrofit_capex,
        "path_b_total_with_downtime": cur["capex"] + retrofit_capex + downtime_cost,
        "day_one_premium": fut["capex"] - cur["capex"],
        "retrofit_penalty": cur["capex"] + retrofit_capex + downtime_cost - fut["capex"],
        "npv_a": _npv(r, flows_a), "npv_b": _npv(r, flows_b),
        "flows_a": flows_a, "flows_b": flows_b,
    }
    up["recommended"] = ("Build future-ready on day one" if up["npv_a"] >= up["npv_b"]
                         else "Build current, retrofit later")
    warnings = _cooling_warnings(cur, A) + _cooling_warnings(fut, A)
    if i["future_kw"] <= i["current_kw"]:
        warnings.append("Future-ready kW/rack is not higher than current; upgrade analysis is trivial.")
    return {"mode": "fitout", "inputs": i, "current": cur, "future": fut, "upgrade": up,
            "warnings": warnings, "long_lead": LONG_LEAD}


# =============================================================================
# GREENFIELD: one new build from scratch, priced from the workbook
# =============================================================================
def run_greenfield(i: dict, A=ASSUMPTIONS) -> dict:
    G = A["greenfield"]
    plat = i["gf_platform"] if i["gf_platform"] in WB.PLATFORMS else "Custom"
    b = WB.basis(plat, i.get("gf_custom_kw"))
    kw = float(b["kw"])
    gpus_per_rack = (i.get("gf_custom_gpus") or b["gpus"]) if plat == "Custom" else b["gpus"]
    it_per_rack = (i.get("gf_custom_it_per_rack") or b["it_per_rack"]) if plat == "Custom" else b["it_per_rack"]
    if i.get("gf_size_by") == "Racks":
        racks = float(i["gf_racks"])
        it_mw = racks * kw / 1000
    else:
        it_mw = float(i["gf_it_mw"])
        racks = it_mw * 1000 / kw
    # cooling: workbook basis is DLC above ~45 kW; at <= 45 kW the user's choice stands
    base_cooling = D2C if kw > D2C_AUTO_KW else "Hybrid (rear-door + air)"  # 01_ASSUME8 r46 "Air or RDHx"
    cooling, _ = effective_cooling(kw, i.get("gf_cooling") or base_cooling, A)
    auto = kw > D2C_AUTO_KW
    pue = b["pue"] + (A["pue"][cooling] - A["pue"][base_cooling])
    cdu_mw = b["cdu_mw"] if cooling == D2C else 0
    if cooling == D2C and not cdu_mw:
        cdu_mw = A["cdu_mw_each"]
    q = WB.quantities(it_mw, racks, pue, cdu_mw)
    region_f = A["regions"][i["region"]]

    # ---- 1. workbook facility base: RIGHT $/IT MW x IT MW, split by the 22-division CSI mix
    right = b["right"]
    wb_facility = right * it_mw
    csi = {d: share * wb_facility for d, share in b["csi_mix"].items()}
    mix_total = sum(b["csi_mix"].values())
    csi = {d: v / mix_total for d, v in csi.items()}          # mix sums to 1.000 +/- rounding
    # cooling-choice adjustment (only possible at <= 45 kW/rack): reprice Div 23 by the
    # ratio of RackReady mechanical $/kW for the chosen vs the workbook's cooling basis
    cool_adj = 0.0
    if cooling != base_cooling:
        def mech_rate(c):
            it_kw = it_mw * 1000
            return (sum(mech_items_for(c, it_kw, A).values()) + cdu_cost(c, it_mw, A)[1]
                    + A["liquid_per_rack"][c] * racks) / it_kw
        cool_adj = csi["23 HVAC/liquid"] * (mech_rate(cooling) / mech_rate(base_cooling) - 1)
    # ---- 2. change pricing (12_CHANGE_PRICING): machines x unit, soft 13% on delta only
    CU = WB.CHANGE_UNITS
    soft_d = 1 + CU["soft_on_delta"]
    changes = []
    red = i.get("gf_redundancy", GF_REDUNDANCY[0])
    if red == GF_REDUNDANCY[1]:
        d = (q["gens_n2"] - q["gens_n1"]) * CU["gen_set"] * 1.15
        changes.append(("C1 Gens N+1 -> N+2", d, d * soft_d))
    if red in GF_REDUNDANCY[2:]:
        d = (q["gens_2n"] - q["gens_n1"]) * CU["gen_set"] * 1.30
        changes.append(("C2 Gens N+1 -> 2N isolated", d, d * soft_d))
    if red == GF_REDUNDANCY[3]:
        d = max(q["ups_2n"] - q["ups_n1"], 0) * CU["ups_module"] * 1.20
        changes.append(("C3 UPS N+1 -> 2N isolated", d, d * soft_d))
    if i.get("gf_fuel_96h"):
        d = b["fuel_100mw"] / WB.CAMPUS_MW * it_mw
        changes.append(("C10 Fuel 48 h -> 96 h", d, d * soft_d))
    if i.get("gf_union_seismic_piles"):
        d = wb_facility * 0.18 * CU["union_extra_factor"]
        changes.append(("C11 Union / seismic D / piles", d, d * soft_d))
    cont = i.get("gf_contingency_pct")
    if cont is not None and abs(cont - b["cont_pct"]) > 1e-9:
        d = wb_facility / WB.HARD_DIVISOR * (cont - b["cont_pct"])
        changes.append((f"C12 Contingency {b['cont_pct']:.0%} -> {cont:.1%}", d, d))
    if i.get("gf_it_fitout"):
        d = b["it_fitout_per_mw"] * it_mw
        changes.append(("C14 IT fit-out ON (not GPUs)", d, d))
    if cool_adj:
        changes.append((f"Cooling choice: {cooling} vs workbook {base_cooling} (Div 23)", cool_adj, cool_adj))
    change_total = sum(c[2] for c in changes)
    facility_pre_region = wb_facility + change_total
    region_adj = facility_pre_region * (region_f - 1)
    facility = facility_pre_region + region_adj

    # ---- 3. scope the workbook keeps OUTSIDE facility $ (02_WHAT_RIGHT r6)
    land = b["land_once"] if i.get("gf_land") is None else float(i["gf_land"])
    interconnect = b["interconnect_once"] if i.get("gf_interconnect") is None else float(i["gf_interconnect"])
    owner_pct = float(i.get("gf_owner_costs_pct") or 0)
    esc_pct = float(i.get("gf_escalation_pct") or 0)
    owner = facility * owner_pct
    months_build = G["design_permit_months"] + (i.get("gf_construction_months") or G["construction_months"])
    escalation = (facility + owner) * ((1 + esc_pct) ** (months_build / 2 / 12) - 1)
    adders = {"Land (workbook adder, once)": land,
              "Utility-side interconnect (workbook adder, once)": interconnect}
    if owner:
        adders["Owner costs: staff, A/E, permits (input %)"] = owner
    if escalation:
        adders["Escalation past 2026 (input %/yr to mid-point)"] = escalation
    capex = facility + sum(adders.values())

    # ---- 4. IT iron + fabric (outside facility $; in ROI)
    gpus = racks * gpus_per_rack
    it_hw = racks * it_per_rack
    fabric = b["fabric_per_mw"] * it_mw if i.get("gf_include_fabric") else 0.0
    gsf = b["gsf_per_mw"] * it_mw

    # ---- 5. schedule
    m_power = i.get("gf_months_to_power") or G["months_to_power"]
    drivers = {
        "Utility power-real + ~6 mo module clock (01_ASSUME8 r62)": m_power + WB.POWER_TO_RFS_MONTHS,
        "Design, permits & construction": months_build,
        f"Long-lead transformers ({WB.TRANSFORMER_WEEKS} wk, 12_CHANGE_PRICING H40) + install/Cx":
            G["procurement_start_month"] + WB.TRANSFORMER_WEEKS / 4.345 + 3,
    }
    crit = max(drivers, key=drivers.get)

    # ---- 6. OpEx
    util, pc = i["utilization"], i["power_cost"]
    avg_kw = it_mw * 1000 * util
    overhead = avg_kw * (pue - 1) * HOURS * pc
    tax_pct = G["property_tax_pct"] if i.get("gf_property_tax_pct") is None else i["gf_property_tax_pct"]
    fte = A["staff_base_fte"] + A["staff_fte_per_mw"] * it_mw
    opex_items = {
        "IT energy": avg_kw * HOURS * pc,
        "Cooling energy": overhead * A["cooling_share_of_overhead"],
        "Other facility energy (losses, lighting)": overhead * (1 - A["cooling_share_of_overhead"]),
        "Maintenance (MEP PPM, spares)": facility * A["maintenance_pct_of_capex"],
        "Staffing": fte * A["staff_cost_per_fte"] * region_f,
        "Insurance (owned asset)": facility * G["insurance_pct"],
        "Property tax (owned land & building)": (facility + land) * tax_pct,
    }
    opex = sum(opex_items.values())

    # ---- 7. revenue & ROI
    price = i.get("gf_gpu_price") or G["gpu_hr_price"].get(plat, G["gpu_hr_price"]["Custom"])
    revenue = gpus * price * util * HOURS
    hw = it_hw if i.get("include_gpu_hw", True) else 0.0
    invest = capex + hw + fabric
    net = revenue - opex
    flows = _flows(invest, net, hw, int(i["horizon_years"]), A)

    # ---- 8. reconciliation to the workbook's own totals at the same IT MW
    scale = it_mw / WB.CAMPUS_MW
    # 03_SIDE8 r16 ALL-IN campus = r15 (fac + IT $/MW) x MW + land adder + interconnect adder
    wb_all_in = (b["right"] + b["it_per_mw"]) * it_mw + b["land_once"] + b["interconnect_once"]
    recon = [
        ("Workbook RIGHT facility $ (03_SIDE8 r8 x IT MW)", wb_facility, wb_facility, 0.0,
         "App base = workbook RIGHT $/IT MW x IT MW, split by the 22-division CSI mix"),
    ]
    for name, _, with_soft in changes:
        recon.append((name, 0.0, with_soft, with_soft, "12_CHANGE_PRICING delta (soft 13% on delta)"))
    if region_adj:
        recon.append((f"Location factor {region_f:.2f} ({i['region']})", 0.0, region_adj, region_adj,
                      "Workbook is a US open-shop basis = 1.00"))
    recon.append(("= Facility $ (workbook scope)", wb_facility, facility, facility - wb_facility,
                  "Equal to the workbook when options are at workbook defaults"))
    wb_adders = {"Land (workbook adder, once)": (b["land_once"], "01_ASSUME8 r79; outside facility $/MW"),
                 "Utility-side interconnect (workbook adder, once)":
                     (b["interconnect_once"], "01_ASSUME8 r78; live often $2-20M+, 12-48 mo")}
    for k, v in adders.items():
        wbv, note = wb_adders.get(k, (0.0, "Not in workbook (02_WHAT_RIGHT r6 excludes owner staff, "
                                           "tax, escalation past 2026)"))
        recon.append((k, wbv, v, v - wbv, note))
    wb_capex = wb_facility + b["land_once"] + b["interconnect_once"]
    recon.append(("= Greenfield CapEx (facility + adders)", wb_capex, capex, capex - wb_capex,
                  "Workbook facility + its land and interconnect screens"))
    recon.append(("IT iron (03_SIDE8 r14 x IT MW)", b["it_per_mw"] * it_mw, it_hw,
                  it_hw - b["it_per_mw"] * it_mw, "Racks x IT $/rack (01_ASSUME8 r9); outside facility $"))
    app_all_in = facility + it_hw + land + interconnect
    recon.append(("ALL-IN campus: facility + IT + land + interconnect (03_SIDE8 r16)", wb_all_in,
                  app_all_in, app_all_in - wb_all_in,
                  "Workbook ALL-IN excludes AI fabric, owner costs and escalation"))

    d = {
        "name": "Greenfield", "platform": plat, "basis": b, "kw_per_rack": kw, "racks": racks,
        "gpus_per_rack": gpus_per_rack, "it_per_rack": it_per_rack, "gpus": gpus,
        "it_mw": it_mw, "it_kw": it_mw * 1000, "pue": pue, "facility_mw": it_mw * pue,
        "cooling": cooling, "cooling_chosen": i.get("gf_cooling"), "cooling_auto": auto,
        "base_cooling": base_cooling, "gsf": gsf, "quantities": q,
        "csi": csi, "changes": changes, "change_total": change_total, "region_adj": region_adj,
        "wb_facility": wb_facility, "facility": facility, "adders": adders, "capex": capex,
        "facility_per_mw": facility / it_mw, "capex_per_mw": capex / it_mw,
        "facility_per_gsf": facility / gsf, "facility_per_kw": facility / (it_mw * 1000),
        "facility_per_rack": facility / racks,
        "band_check": WB.band_check(facility / it_mw, b),
        "it_hw": it_hw, "gpu_hw": hw, "fabric": fabric, "total_invest": invest,
        "opex_items": opex_items, "opex": opex, "gpu_price": price, "revenue": revenue,
        "net_annual": net, "cash_flows": flows, "npv": _npv(A["discount_rate"], flows),
        "simple_payback": invest / net if net > 0 else None,
        "schedule": {"drivers": drivers, "critical_path": crit, "months_to_rfs": drivers[crit],
                     "months_to_power": m_power},
        "reconciliation": recon, "scale_to_campus": scale,
        "cooling_ok": kw <= A["max_kw_per_rack"][cooling], "cooling_max": A["max_kw_per_rack"][cooling],
    }
    warnings = _cooling_warnings(d, A)
    if not b["in_range"]:
        warnings.append(f"{kw:.0f} kW/rack is outside the workbook ladder (41-600 kW); the "
                        f"{b['bracket']} basis is held flat.")
    if plat == "TPU Ironwood":
        warnings.append("TPU Ironwood is an ICD hold in the workbook (02_WHAT_RIGHT r9): price from the Google ICD.")
    if plat == "Kyber":
        warnings.append("Kyber is 2H 2027 in the workbook: do not GMP it (02_WHAT_RIGHT r9).")
    if m_power < WB.INTERCONNECT_MONTHS_RANGE[0]:
        warnings.append("Months to power is below the workbook's 12-48 month interconnect range.")
    return {"mode": "greenfield", "inputs": i, "design": d, "warnings": warnings,
            "long_lead": LONG_LEAD}


def platform_table(it_mw: float) -> list[dict]:
    """The workbook's 8 platforms at the same IT MW (03_SIDE8 / 14_EIGHT_DEEP)."""
    rows = []
    for n, p in WB.PLATFORMS.items():
        racks = it_mw * 1000 / p["kw"]
        rows.append({"platform": n, "kw": p["kw"], "cooling": p["cooling_mode"], "pue": p["pue"],
                     "low": p["low"], "right": p["right"], "high": p["high"],
                     "facility": p["right"] * it_mw, "racks": racks, "gpus": racks * p["gpus"],
                     "gsf": p["gsf_per_mw"] * it_mw, "per_sf": p["right"] / p["gsf_per_mw"],
                     "per_kw": p["right"] / 1000, "per_rack": p["right"] * p["kw"] / 1000,
                     "it": p["it_per_mw"] * it_mw, "all_in": (p["right"] + p["it_per_mw"]) * it_mw})
    return rows


def run_model(inp: dict | None = None, A: dict = ASSUMPTIONS) -> dict:
    i = deepcopy(DEFAULT_INPUTS)
    i.update({k: v for k, v in (inp or {}).items()})
    return run_greenfield(i, A) if is_greenfield(i) else run_fitout(i, A)


def summary_for_llm(res: dict) -> dict:
    i = res["inputs"]
    common = {k: i[k] for k in ("project_name", "region", "power_cost", "utilization", "horizon_years")}
    if res["mode"] == "greenfield":
        d = res["design"]
        b = d["basis"]
        return {
            "project_type": GREENFIELD,
            "note": "Single new build from scratch. No current-vs-future comparison.",
            "inputs": common,
            "design": {
                "platform": d["platform"], "workbook_bracket": b["bracket"],
                "kw_per_rack": round(d["kw_per_rack"], 1), "racks": round(d["racks"], 1),
                "gpus_per_rack": d["gpus_per_rack"], "gpus": round(d["gpus"]),
                "it_mw": round(d["it_mw"], 2), "pue": round(d["pue"], 3), "cooling": d["cooling"],
                "cooling_rule": D2C_NOTE if d["cooling_auto"] else "user choice (<= 45 kW/rack)",
                "gross_sf": round(d["gsf"]),
                "quantities": {k: round(v, 1) for k, v in d["quantities"].items()},
                "redundancy": i["gf_redundancy"],
            },
            "capex": {
                "workbook_right_facility_usd": round(d["wb_facility"]),
                "csi_divisions_usd": {k: round(v) for k, v in d["csi"].items()},
                "change_pricing_usd": {n: round(w) for n, _, w in d["changes"]},
                "location_adjustment_usd": round(d["region_adj"]),
                "facility_usd": round(d["facility"]),
                "facility_usd_per_mw_it": round(d["facility_per_mw"]),
                "facility_usd_per_gsf": round(d["facility_per_gsf"]),
                "facility_usd_per_kw": round(d["facility_per_kw"]),
                "adders_outside_facility_usd": {k: round(v) for k, v in d["adders"].items()},
                "total_greenfield_capex_usd": round(d["capex"]),
                "workbook_band_usd_per_mw_it": {"low": b["low"], "right": b["right"], "high": b["high"]},
                "band_check": d["band_check"],
            },
            "it_and_fabric": {"it_iron_usd": round(d["it_hw"]), "fabric_usd": round(d["fabric"]),
                              "it_in_roi": bool(i.get("include_gpu_hw", True))},
            "opex": {"annual_opex_usd": round(d["opex"]),
                     "breakdown_usd": {k: round(v) for k, v in d["opex_items"].items()}},
            "roi": {"gpu_price_per_hr": d["gpu_price"], "annual_revenue_usd": round(d["revenue"]),
                    "total_investment_usd": round(d["total_invest"]),
                    "simple_payback_years": None if d["simple_payback"] is None else round(d["simple_payback"], 2),
                    "npv_8pct_usd": round(d["npv"])},
            "schedule": {"drivers_months": {k: round(v, 1) for k, v in d["schedule"]["drivers"].items()},
                         "critical_path": d["schedule"]["critical_path"],
                         "months_to_ready_for_service": round(d["schedule"]["months_to_rfs"], 1)},
            "workbook_holds": "Attack first: CDU MW ladder, 800V $ placeholder (Rubin/Kyber), Kyber mass/slab, "
                              "TPU ICD, N+1 vs 2N, interconnect excluded, 4% contingency vs 7-10% at 60% CD "
                              "(02_WHAT_RIGHT r10).",
            "warnings": res["warnings"],
        }

    def s(x):
        return {
            "racks": x["racks"], "kw_per_rack": x["kw_per_rack"], "cooling": x["cooling"],
            "cooling_rule": D2C_NOTE if x["cooling_auto"] else "user choice (<= 45 kW/rack)",
            "it_mw": round(x["it_mw"], 2), "design_pue": x["pue"],
            "facility_mw": round(x["facility_mw"], 2), "gross_sf": round(x["gsf"]),
            "capex_usd": round(x["capex"]), "capex_per_mw_it_usd": round(x["capex_per_mw"]),
            "capex_by_system_usd": {k: round(v) for k, v in x["systems"].items()},
            "soft_costs_usd": round(x["soft"]), "contingency_usd": round(x["contingency"]),
            "annual_opex_usd": round(x["opex"]),
            "opex_breakdown_usd": {k: round(v) for k, v in x["opex_items"].items()},
            "annual_energy_saving_vs_air_pue_usd": round(x["pue_saving_vs_air"]),
            "gpus": x["gpus"], "gpu_price_per_hr": x["gpu_price"],
            "annual_revenue_usd": round(x["revenue"]), "gpu_hardware_usd": round(x["gpu_hw"]),
            "simple_payback_years": None if x["simple_payback"] is None else round(x["simple_payback"], 2),
            "npv_8pct_usd": round(x["npv"]),
            "cooling_within_practical_limit": x["cooling_ok"],
        }
    u = res["upgrade"]
    return {
        "project_type": FITOUT,
        "inputs": {**common, **{k: i[k] for k in ("racks", "tier", "redundancy")}},
        "region_factor": ASSUMPTIONS["regions"][i["region"]],
        "current": s(res["current"]),
        "future_ready": s(res["future"]),
        "upgrade_paths": {
            "A_build_future_ready_day_one_capex_usd": round(u["path_a_capex"]),
            "B_build_current_then_retrofit_year": u["retrofit_year"],
            "B_retrofit_capex_usd": round(u["retrofit_capex"]),
            "B_total_capex_usd": round(u["path_b_capex"]),
            "B_downtime_months": u["downtime_months"],
            "B_lost_revenue_usd": round(u["downtime_cost"]),
            "retrofit_penalty_vs_day_one_usd": round(u["retrofit_penalty"]),
            "npv_path_a_usd": round(u["npv_a"]), "npv_path_b_usd": round(u["npv_b"]),
            "engine_recommendation": u["recommended"],
        },
        "warnings": res["warnings"],
        "long_lead_weeks": {n: f"{lo}-{hi}" for n, _, lo, hi in LONG_LEAD},
    }


if __name__ == "__main__":
    import json
    print(json.dumps(summary_for_llm(run_model()), indent=2))
