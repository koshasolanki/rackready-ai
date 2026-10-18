"""
RackReady AI - deterministic cost engine.

Every unit rate the model uses lives in the ASSUMPTIONS dict below so a cost
manager can review, challenge and tune it in one place. All figures are
INDICATIVE PLANNING RATES (US Northern Virginia = 1.00 baseline, Tier III,
N+1, 2026 USD). They are not a quote, a bid or an estimate of record.
"""
from __future__ import annotations

import math
from copy import deepcopy

# =============================================================================
# ASSUMPTIONS - every unit rate in one place (indicative, 2026 USD, NoVA = 1.00)
# =============================================================================
ASSUMPTIONS = {
    # ---- CSI Division 26 - Electrical, $ per kW of IT load (Tier III, N+1) ----
    "electrical_per_kw": {
        "MV service & transformers": 650,
        "Switchgear & switchboards": 900,
        "UPS & batteries": 950,
        "Generators & fuel systems": 850,
        "Busway, PDUs & RPPs": 450,
        "Grounding, lighting & branch power": 250,
    },
    # Extra $/kW when racks exceed the high-density threshold: 415/240V
    # distribution, high-amp overhead busway, larger rPDUs, more tap-offs.
    "hd_electrical_premium_per_kw": 600,
    "hd_threshold_kw_per_rack": 50,

    # ---- CSI Division 23 - Mechanical, $ per kW of IT load by cooling type ----
    "mechanical_per_kw": {
        "Air": {
            "Chillers / central plant": 950, "CRAH / fan walls": 850,
            "CDUs / RDHx": 0, "Piping & pumps": 350, "Heat rejection": 450},
        "Hybrid (rear-door + air)": {
            "Chillers / central plant": 900, "CRAH / fan walls": 500,
            "CDUs / RDHx": 650, "Piping & pumps": 450, "Heat rejection": 400},
        "Direct-to-chip liquid": {
            "Chillers / central plant": 800, "CRAH / fan walls": 350,
            "CDUs / RDHx": 1000, "Piping & pumps": 950, "Heat rejection": 550},
        "Closed-loop full liquid": {
            "Chillers / central plant": 650, "CRAH / fan walls": 150,
            "CDUs / RDHx": 1350, "Piping & pumps": 1300, "Heat rejection": 850},
    },
    # Per-rack liquid items: rack manifolds, secondary loop (TCS) drops,
    # quick-disconnects, leak detection. Rear-door HX units for hybrid.
    "liquid_per_rack": {
        "Air": 0,
        "Hybrid (rear-door + air)": 18_000,
        "Direct-to-chip liquid": 30_000,
        "Closed-loop full liquid": 35_000,
    },
    # Design PUE (annualised, temperate climate) by cooling type
    "pue": {
        "Air": 1.50,
        "Hybrid (rear-door + air)": 1.38,
        "Direct-to-chip liquid": 1.25,
        "Closed-loop full liquid": 1.15,
    },
    # Practical max rack density each cooling approach supports (kW/rack)
    "max_kw_per_rack": {
        "Air": 30,
        "Hybrid (rear-door + air)": 50,
        "Direct-to-chip liquid": 150,
        "Closed-loop full liquid": 200,
    },

    # ---- Controls - BMS / EPMS, $ per kW IT ----
    "controls_per_kw": {"BMS": 120, "EPMS / power monitoring": 130},

    # ---- Building: CSI Div 03/05/09 structure, envelope, architectural ----
    "white_space_sf_per_rack": 30,      # rack + hot/cold aisle share
    "support_sf_per_mw": 3_000,         # electrical rooms, mech gallery, MDF/support
    "shell_cost_per_gsf": 300,          # structure, envelope, finishes
    "fire_cost_per_gsf": 14,            # CSI Div 21 pre-action / clean agent
    "heavy_rack_slab_premium_per_sf": 75,  # thickened slab for 3,000+ lb liquid racks
    "heavy_rack_per_rack": 2_500,       # plinths, seismic bracing, anchoring

    # ---- CSI Div 27 - Networking / IT racks & cabling (fixed per rack) ----
    "rack_enclosure_per_rack": 6_000,
    "rpdu_per_kw": 120,                 # intelligent rPDUs scale with rack kW
    "cabling_per_rack": 12_000,         # structured cabling, fiber trunks, cable tray
    "cabling_per_gpu": 400,             # extra optics / fabric cabling per GPU

    # ---- Indirects ----
    "soft_costs_pct": 0.14,             # design, permits, PM/CM, commissioning L1-L5, GC fee
    "contingency_pct": 0.10,

    # ---- Redundancy multipliers (applied to Div 26 / Div 23) ----
    "redundancy": {
        "N":   {"electrical": 0.85, "mechanical": 0.90},
        "N+1": {"electrical": 1.00, "mechanical": 1.00},
        "2N":  {"electrical": 1.35, "mechanical": 1.20},
    },
    # ---- Uptime tier multiplier (applied to all direct costs) ----
    "tier": {"Tier II": 0.90, "Tier III": 1.00, "Tier IV": 1.15},

    # ---- Location factors (indicative construction cost index, NoVA = 1.00) ----
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

    # ---- Retrofit (build current now, upgrade later) ----
    "retrofit_premium": 1.35,           # live-site working, phasing, temp power/cooling
    "retrofit_demo_pct": 0.06,          # demo/rework as % of current direct cost
    "retrofit_downtime_months": 4,      # revenue lost during cut-over
    "retrofit_year": 3,
    # Share of each current-build system that survives into the future build
    "retrofit_reuse": {
        "Electrical (Div 26)": 0.45, "Mechanical (Div 23)": 0.15,
        "Liquid cooling / TCS (Div 23)": 0.0, "Controls BMS/EPMS": 0.50,
        "Structural & architectural (Div 03/05/09)": 0.80,
        "Fire protection (Div 21)": 0.60, "Networking & racks (Div 27)": 0.40,
    },

    # ---- OpEx ----
    "maintenance_pct_of_capex": 0.02,   # MEP PPM + spares, per year
    "other_opex_pct_of_capex": 0.006,   # insurance, property tax
    "staff_base_fte": 8,
    "staff_fte_per_mw": 0.5,
    "staff_cost_per_fte": 140_000,
    "cooling_share_of_overhead": 0.80,  # share of (PUE-1) energy that is cooling

    # ---- Revenue / IT hardware ----
    "gpu_hw_cost_current": 30_000,      # $/GPU, HGX H100/H200-class servers
    "gpu_hw_cost_future": 45_000,       # $/GPU, GB200/GB300 NVL72-class racks
    "gpu_hw_life_years": 5,
    "gpu_refresh_cost_factor": 0.70,    # refresh price vs original
    "discount_rate": 0.08,
}

# Long-lead equipment (indicative 2026 manufacturing lead times, weeks)
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

DEFAULT_INPUTS = {
    "project_name": "AI Hall 1 - 200 racks",
    "racks": 200,
    "current_kw": 15.0,
    "future_kw": 140.0,
    "current_cooling": "Air",
    "future_cooling": "Closed-loop full liquid",
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
}

HOURS = 8760


def _npv(rate: float, flows: list[float]) -> float:
    return sum(cf / (1 + rate) ** t for t, cf in enumerate(flows))


def _payback(flows: list[float]) -> float | None:
    """Payback in years from a cash-flow list (year 0 = investment)."""
    cum = 0.0
    for t, cf in enumerate(flows):
        prev = cum
        cum += cf
        if t > 0 and cum >= 0 > prev and cf > 0:
            return round(t - 1 + (-prev / cf), 2)
    return None


def scenario(name, racks, kw, cooling, gpus_per_rack, gpu_price, gpu_hw_cost,
             inp, A=ASSUMPTIONS) -> dict:
    """Cost one scenario (current or future-ready)."""
    region_f = A["regions"][inp["region"]]
    red = A["redundancy"][inp["redundancy"]]
    tier_f = A["tier"][inp["tier"]]
    it_kw = racks * kw
    it_mw = it_kw / 1000
    pue = A["pue"][cooling]
    high_density = kw > A["hd_threshold_kw_per_rack"]

    # --- Electrical Div 26
    elec_items = {k: v * it_kw for k, v in A["electrical_per_kw"].items()}
    if high_density:
        elec_items["High-density distribution premium"] = A["hd_electrical_premium_per_kw"] * it_kw
    elec_items = {k: v * red["electrical"] for k, v in elec_items.items()}

    # --- Mechanical Div 23
    mech_items = {k: v * it_kw * red["mechanical"]
                  for k, v in A["mechanical_per_kw"][cooling].items() if v}
    liquid = A["liquid_per_rack"][cooling] * racks

    # --- Controls
    controls = sum(A["controls_per_kw"].values()) * it_kw

    # --- Building
    white_sf = A["white_space_sf_per_rack"] * racks
    gsf = white_sf + A["support_sf_per_mw"] * it_mw
    shell = A["shell_cost_per_gsf"] * gsf
    slab = 0.0
    if high_density:
        slab = A["heavy_rack_slab_premium_per_sf"] * white_sf + A["heavy_rack_per_rack"] * racks
    fire = A["fire_cost_per_gsf"] * gsf

    # --- Networking Div 27
    network = racks * (A["rack_enclosure_per_rack"] + A["rpdu_per_kw"] * kw
                       + A["cabling_per_rack"] + A["cabling_per_gpu"] * gpus_per_rack)

    systems = {
        "Electrical (Div 26)": sum(elec_items.values()),
        "Mechanical (Div 23)": sum(mech_items.values()),
        "Liquid cooling / TCS (Div 23)": liquid,
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
    if liquid:
        detail.append(("Mechanical (Div 23)", "Rack manifolds / TCS / RDHx", liquid * f))
    detail.append(("Controls", "BMS + EPMS", controls * f))
    detail.append(("Structural & arch", f"Shell & fit-out ({gsf:,.0f} gsf)", shell * f))
    if slab:
        detail.append(("Structural & arch", "Heavy-rack slab & bracing", slab * f))
    detail.append(("Fire protection (Div 21)", "Pre-action / clean agent", fire * f))
    detail.append(("Networking & racks (Div 27)", "Racks, rPDUs, cabling, fiber", network * f))

    # --- OpEx
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
    # PUE impact vs air-cooled baseline at same load
    air_pue = A["pue"]["Air"]
    pue_saving = avg_it_kw * (air_pue - pue) * HOURS * inp["power_cost"]

    # --- Revenue & ROI
    gpus = racks * gpus_per_rack
    revenue = gpus * gpu_price * inp["utilization"] * HOURS
    gpu_hw = gpus * gpu_hw_cost if inp.get("include_gpu_hw", True) else 0.0
    total_invest = capex + gpu_hw
    net = revenue - opex
    H = int(inp["horizon_years"])
    flows = [-total_invest]
    for y in range(1, H + 1):
        cf = net
        if gpu_hw and y % A["gpu_hw_life_years"] == 0 and y < H:
            cf -= gpu_hw * A["gpu_refresh_cost_factor"]
        flows.append(cf)
    npv = _npv(A["discount_rate"], flows)
    simple_payback = total_invest / net if net > 0 else None
    roi = (sum(flows[1:]) - total_invest) / total_invest if total_invest else 0

    return {
        "name": name, "racks": racks, "kw_per_rack": kw, "cooling": cooling,
        "it_kw": it_kw, "it_mw": it_mw, "pue": pue,
        "facility_mw": it_mw * pue, "avg_facility_mw": it_mw * pue * inp["utilization"],
        "gsf": gsf, "high_density": high_density,
        "systems": systems, "detail": detail, "direct": direct, "soft": soft,
        "contingency": contingency, "capex": capex, "capex_per_mw": capex / it_mw,
        "capex_per_rack": capex / racks,
        "opex_items": opex_items, "opex": opex, "pue_saving_vs_air": pue_saving,
        "gpus": gpus, "gpu_price": gpu_price, "revenue": revenue, "gpu_hw": gpu_hw,
        "total_invest": total_invest, "net_annual": net, "cash_flows": flows,
        "npv": npv, "simple_payback": simple_payback, "roi_horizon": roi,
        "cooling_ok": kw <= A["max_kw_per_rack"][cooling],
        "cooling_max": A["max_kw_per_rack"][cooling],
    }


def run_model(inp: dict | None = None, A: dict = ASSUMPTIONS) -> dict:
    """Run current vs future-ready and the two upgrade paths. Pure Python."""
    i = deepcopy(DEFAULT_INPUTS)
    i.update(inp or {})
    cur = scenario("Current", i["racks"], i["current_kw"], i["current_cooling"],
                   i["gpus_per_rack_current"], i["gpu_price_current"],
                   A["gpu_hw_cost_current"], i, A)
    fut = scenario("Future-ready", i["racks"], i["future_kw"], i["future_cooling"],
                   i["gpus_per_rack_future"], i["gpu_price_future"],
                   A["gpu_hw_cost_future"], i, A)

    # ---- Path A: build future-ready on day one
    # ---- Path B: build current now, retrofit in year Y
    Y = min(int(A["retrofit_year"]), int(i["horizon_years"]))
    reuse = A["retrofit_reuse"]
    retro_rows = []
    retro_direct = 0.0
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

    H = int(i["horizon_years"])
    r = A["discount_rate"]
    # Path A cash flows are the future scenario
    flows_a = fut["cash_flows"]
    # Path B
    flows_b = [-cur["total_invest"]]
    for y in range(1, H + 1):
        if y < Y:
            cf = cur["net_annual"]
        elif y == Y:
            # half a year of current ops minus downtime, then future ramp
            cf = cur["net_annual"] - downtime_cost - retrofit_capex - fut["gpu_hw"]
        else:
            cf = fut["net_annual"]
            yrs_since = y - Y
            if fut["gpu_hw"] and yrs_since % A["gpu_hw_life_years"] == 0 and y < H:
                cf -= fut["gpu_hw"] * A["gpu_refresh_cost_factor"]
        flows_b.append(cf)
    path_a_capex = fut["capex"]
    path_b_capex = cur["capex"] + retrofit_capex
    upgrade = {
        "retrofit_year": Y,
        "rows": retro_rows,
        "demo": demo,
        "retrofit_capex": retrofit_capex,
        "downtime_cost": downtime_cost,
        "downtime_months": A["retrofit_downtime_months"],
        "path_a_capex": path_a_capex,
        "path_b_capex": path_b_capex,
        "path_b_total_with_downtime": path_b_capex + downtime_cost,
        "day_one_premium": fut["capex"] - cur["capex"],
        "retrofit_penalty": path_b_capex + downtime_cost - path_a_capex,
        "npv_a": _npv(r, flows_a),
        "npv_b": _npv(r, flows_b),
        "flows_a": flows_a,
        "flows_b": flows_b,
    }
    upgrade["recommended"] = ("Build future-ready on day one"
                              if upgrade["npv_a"] >= upgrade["npv_b"]
                              else "Build current, retrofit later")

    warnings = []
    for s in (cur, fut):
        if not s["cooling_ok"]:
            warnings.append(
                f"{s['name']}: {s['kw_per_rack']:.0f} kW/rack exceeds the practical limit of "
                f"{s['cooling']} (~{s['cooling_max']} kW/rack). Choose a liquid cooling option.")
    if i["future_kw"] <= i["current_kw"]:
        warnings.append("Future-ready kW/rack is not higher than current; upgrade analysis is trivial.")

    return {"inputs": i, "current": cur, "future": fut, "upgrade": upgrade,
            "warnings": warnings, "long_lead": LONG_LEAD}


def summary_for_llm(res: dict) -> dict:
    """Compact, rounded JSON payload the LLM narrates from."""
    def s(x):
        return {
            "racks": x["racks"], "kw_per_rack": x["kw_per_rack"], "cooling": x["cooling"],
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
    i = res["inputs"]
    return {
        "inputs": {k: i[k] for k in ("project_name", "racks", "region", "tier", "redundancy",
                                      "power_cost", "utilization", "horizon_years")},
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
    r = run_model()
    print(json.dumps(summary_for_llm(r), indent=2))
