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

import workbook_basis as WB

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

    # ---- GREENFIELD (build from scratch) ----
    # Facility benchmarks, shell $/gsf and site/civil $/MW come from the user's workbook
    # (see workbook_basis.py for sheet/row citations). Land, utility, schedule and
    # owner soft-cost rates below are indicative 2026 planning inputs, editable in the app.
    "greenfield": {
        "land_cost_per_acre": 400_000,       # indicative US DC-zoned land; varies $50k-$3M+/acre
        "site_coverage": 0.35,               # building footprint / site (01_ASSUME8 r19 pad share 22-40%)
        "yard_acres_per_facility_mw": 0.25,  # gens, TX, HV yard, dry coolers, fuel, setbacks
        "min_site_acres": 5.0,
        "site_civil_min_per_acre": 250_000,  # floor for grading, paving, fence, storm on small sites
        "hv_yard_per_facility_kw": 350,      # owner-side HV substation/yard (11_SPEC_MOVES r15: 115-230 kV AIS)
        "hv_yard_threshold_mw": 20,          # below this, utility MV service (already in Div 26 MV line)
        "interconnect_fixed": 3_000_000,     # utility-side: studies, line extension, sub contribution
        "interconnect_per_mw": 50_000,       # -> ~$9M at 120 MW vs workbook $8M once (01_ASSUME8 r78)
        "months_to_power": 24,               # utility queue / energization (workbook: 12-48 months)
        "design_permit_months": 9,
        "construction_months": 18,
        "procurement_start_month": 3,        # long-lead POs released after SD
        "gc_pct": WB.GC_PCT,                 # 9%, 01_ASSUME8 r63
        "design_fees_pct": 0.07,             # A/E, permits & impact fees, owner PM/CM, CxA (indicative)
        "contingency_pct": 0.08,             # workbook 4% GMP screen; early-stage 7-10% (01_ASSUME8 r64 note)
        "escalation_per_year": 0.04,         # applied to hard + soft to construction mid-point
        "property_tax_pct": 0.008,           # of land + building + site (before abatements)
        "insurance_pct": 0.003,              # of depreciable CapEx
        "grounds_per_acre_year": 12_000,     # landscaping, roads, snow, perimeter security patrol
        # share of each current-build greenfield item that survives a later density upgrade
        "retrofit_reuse": {
            "Shell & core - new build (Div 03-14)": 0.85,
            "Site work & civil (Div 02/31/32/33)": 0.90,
            "On-site HV substation & yard (Div 26)": 0.30,
        },
        "owner_retrofit_reuse": {"Land acquisition": 1.0, "Utility interconnection (utility-side)": 0.5},
    },
}

PROJECT_TYPES = ["Existing building fit-out", "Greenfield - new build from scratch"]
GREENFIELD = PROJECT_TYPES[1]

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
    "project_type": PROJECT_TYPES[0],
    # greenfield inputs (0 / None = auto)
    "gf_land_cost_per_acre": None,
    "gf_site_acres": 0.0,
    "gf_utility_mw": 0.0,
    "gf_interconnect_fixed": None,
    "gf_interconnect_per_mw": None,
    "gf_shell_per_gsf": 0.0,
    "gf_months_to_power": None,
    "gf_construction_months": None,
    "gf_design_fees_pct": None,
    "gf_contingency_pct": None,
    "gf_escalation_per_year": None,
}


def is_greenfield(inp: dict) -> bool:
    return str(inp.get("project_type", "")).lower().startswith("greenfield")


def gf_params(inp: dict, A=ASSUMPTIONS) -> dict:
    """Greenfield parameters: app inputs override the ASSUMPTIONS defaults."""
    g = dict(A["greenfield"])
    for k_in, k_a in [("gf_land_cost_per_acre", "land_cost_per_acre"),
                      ("gf_interconnect_fixed", "interconnect_fixed"),
                      ("gf_interconnect_per_mw", "interconnect_per_mw"),
                      ("gf_months_to_power", "months_to_power"),
                      ("gf_construction_months", "construction_months"),
                      ("gf_design_fees_pct", "design_fees_pct"),
                      ("gf_contingency_pct", "contingency_pct"),
                      ("gf_escalation_per_year", "escalation_per_year")]:
        if inp.get(k_in) is not None:
            g[k_a] = inp[k_in]
    g["site_acres_override"] = float(inp.get("gf_site_acres") or 0)
    g["utility_mw_override"] = float(inp.get("gf_utility_mw") or 0)
    g["shell_per_gsf_override"] = float(inp.get("gf_shell_per_gsf") or 0)
    return g

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

    gf = is_greenfield(inp)
    facility_mw = it_mw * pue
    f = region_f * tier_f
    systems = {
        "Electrical (Div 26)": sum(elec_items.values()),
        "Mechanical (Div 23)": sum(mech_items.values()),
        "Liquid cooling / TCS (Div 23)": liquid,
        "Controls BMS/EPMS": controls,
        "Structural & architectural (Div 03/05/09)": shell + slab,
        "Fire protection (Div 21)": fire,
        "Networking & racks (Div 27)": network,
    }
    owner = {}          # owner costs outside soft costs / contingency (land, utility-side)
    greenfield = None
    if gf:
        g = gf_params(inp, A)
        bm = WB.benchmark(kw)
        shell_rate = g["shell_per_gsf_override"] or bm["shell_per_gsf"]
        # site sizing: single-storey footprint / coverage + equipment yard
        auto_acres = max(g["min_site_acres"],
                         gsf / 43_560 / g["site_coverage"]
                         + g["yard_acres_per_facility_mw"] * facility_mw)
        acres = g["site_acres_override"] or auto_acres
        utility_mw = g["utility_mw_override"] or facility_mw
        gf_shell = shell_rate * gsf
        site_civil = max(bm["site_civil_per_mw"] * it_mw, g["site_civil_min_per_acre"] * acres)
        hv_yard = (g["hv_yard_per_facility_kw"] * utility_mw * 1000
                   if utility_mw >= g["hv_yard_threshold_mw"] else 0.0)
        # greenfield replaces the fit-out structural line with a new-build shell & core
        systems.pop("Structural & architectural (Div 03/05/09)")
        systems = {"Site work & civil (Div 02/31/32/33)": site_civil,
                   "Shell & core - new build (Div 03-14)": gf_shell,
                   "On-site HV substation & yard (Div 26)": hv_yard, **systems}
        land = acres * g["land_cost_per_acre"]
        interconnect = g["interconnect_fixed"] + g["interconnect_per_mw"] * utility_mw
        owner = {"Land acquisition": land, "Utility interconnection (utility-side)": interconnect}
        greenfield = {"acres": acres, "auto_acres": auto_acres, "utility_mw": utility_mw,
                      "shell_per_gsf": shell_rate, "benchmark": bm, "params": g,
                      "hv_yard_on": hv_yard > 0,
                      "utility_short": utility_mw + 1e-9 < facility_mw}
    systems = {k: v * f for k, v in systems.items()}
    direct = sum(systems.values())
    if gf:
        soft_pct = g["gc_pct"] + g["design_fees_pct"]
        cont_pct = g["contingency_pct"]
    else:
        soft_pct, cont_pct = A["soft_costs_pct"], A["contingency_pct"]
    soft = direct * soft_pct
    contingency = (direct + soft) * cont_pct
    escalation = 0.0
    if gf:
        mid_years = (g["design_permit_months"] + g["construction_months"] / 2) / 12
        escalation = (direct + soft) * ((1 + g["escalation_per_year"]) ** mid_years - 1)
    owner_total = sum(owner.values())
    capex = direct + soft + contingency + escalation + owner_total

    detail = []
    if gf:
        detail.append(("Site work & civil", f"Grade, haul road, paving, fence, on-site utilities "
                       f"({greenfield['acres']:,.1f} ac)", systems["Site work & civil (Div 02/31/32/33)"]))
        detail.append(("Shell & core (new build)", f"Foundations, SOG, steel, envelope, roof, finishes "
                       f"({gsf:,.0f} gsf @ ${shell_rate:,.0f}/gsf)", systems["Shell & core - new build (Div 03-14)"]))
        if hv_yard:
            detail.append(("Electrical (Div 26)", f"On-site HV substation & yard ({utility_mw:,.1f} MW)",
                           systems["On-site HV substation & yard (Div 26)"]))
    for k, v in elec_items.items():
        detail.append(("Electrical (Div 26)", k, v * f))
    for k, v in mech_items.items():
        detail.append(("Mechanical (Div 23)", k, v * f))
    if liquid:
        detail.append(("Mechanical (Div 23)", "Rack manifolds / TCS / RDHx", liquid * f))
    detail.append(("Controls", "BMS + EPMS", controls * f))
    if not gf:
        detail.append(("Structural & arch", f"Shell & fit-out ({gsf:,.0f} gsf)", shell * f))
        if slab:
            detail.append(("Structural & arch", "Heavy-rack slab & bracing", slab * f))
    detail.append(("Fire protection (Div 21)", "Pre-action / clean agent", fire * f))
    detail.append(("Networking & racks (Div 27)", "Racks, rPDUs, cabling, fiber", network * f))

    schedule = None
    if gf:
        lead_wks = max(hi for _, _, lo, hi in LONG_LEAD)
        lead_mid = sum((lo + hi) / 2 for _, _, lo, hi in LONG_LEAD[:1])
        build = g["design_permit_months"] + g["construction_months"]
        equip = g["procurement_start_month"] + lead_mid / 4.345 + 3  # +3 mo install & L1-L5 Cx
        drivers = {"Utility power (queue + energization)": g["months_to_power"],
                   "Design, permits & construction": build,
                   "Long-lead transformers (PO + delivery + Cx)": equip}
        crit = max(drivers, key=drivers.get)
        schedule = {"drivers": drivers, "critical_path": crit, "months_to_rfs": drivers[crit],
                    "transformer_lead_max_wks": lead_wks}
        # workbook-comparable facility $/IT MW: shell->Cx incl. GC + contingency; excludes land,
        # utility-side interconnect, IT racks/cabling (Div 27 here), owner design fees, escalation
        comp_direct = direct - systems["Networking & racks (Div 27)"]
        comparable = comp_direct * (1 + g["gc_pct"]) * (1 + cont_pct)
        greenfield["workbook_comparable_per_mw"] = comparable / it_mw
        greenfield["band_check"] = WB.band_check(comparable / it_mw, kw)
        greenfield["schedule"] = schedule
        greenfield["csi_crosscheck"] = {d: share * bm["right"] * it_mw
                                        for d, share in bm["csi_mix"].items()}

    # --- OpEx
    avg_it_kw = it_kw * inp["utilization"]
    it_energy = avg_it_kw * HOURS * inp["power_cost"]
    overhead_energy = avg_it_kw * (pue - 1) * HOURS * inp["power_cost"]
    cooling_energy = overhead_energy * A["cooling_share_of_overhead"]
    other_fac_energy = overhead_energy - cooling_energy
    depreciable = capex - owner.get("Land acquisition", 0.0)
    maintenance = (capex - owner_total) * A["maintenance_pct_of_capex"]
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
    if gf:
        opex_items.pop("Insurance & property tax")
        assessed = (owner["Land acquisition"] + systems["Shell & core - new build (Div 03-14)"]
                    + systems["Site work & civil (Div 02/31/32/33)"])
        opex_items["Insurance (owned asset)"] = depreciable * g["insurance_pct"]
        opex_items["Property tax (owned land & building)"] = assessed * g["property_tax_pct"]
        opex_items["Site & grounds upkeep"] = greenfield["acres"] * g["grounds_per_acre_year"]
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
        "facility_mw": facility_mw, "project_type": inp.get("project_type"),
        "greenfield": greenfield, "owner_costs": owner, "escalation": escalation,
        "soft_pct": soft_pct, "contingency_pct": cont_pct, "avg_facility_mw": it_mw * pue * inp["utilization"],
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
    gf = is_greenfield(i)
    reuse = dict(A["retrofit_reuse"])
    if gf:
        reuse.update(A["greenfield"]["retrofit_reuse"])
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
    retro_soft = retro_direct * fut["soft_pct"]
    retro_cont = (retro_direct + retro_soft) * fut["contingency_pct"]
    retro_owner = 0.0
    retro_escalation = 0.0
    if gf:
        # more land and a bigger utility service: bought at market, no live-site premium
        for name, fut_cost in fut["owner_costs"].items():
            cur_cost = cur["owner_costs"].get(name, 0.0)
            reused = cur_cost * A["greenfield"]["owner_retrofit_reuse"].get(name, 0.0)
            new_work = max(fut_cost - reused, 0.0)
            retro_owner += new_work
            retro_rows.append((name, cur_cost, fut_cost, reused, new_work))
        g = fut["greenfield"]["params"]
        retro_escalation = (retro_direct + retro_soft) * ((1 + g["escalation_per_year"]) ** Y - 1)
    retrofit_capex = retro_direct + retro_soft + retro_cont + retro_owner + retro_escalation
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
        "retrofit_owner_costs": retro_owner,
        "retrofit_escalation": retro_escalation,
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
    if gf:
        for s in (cur, fut):
            gfs = s["greenfield"]
            if gfs["utility_short"]:
                warnings.append(
                    f"{s['name']}: utility service of {gfs['utility_mw']:.1f} MW is below the "
                    f"{s['facility_mw']:.1f} MW peak facility load. Increase the utility MW.")
            if gfs["acres"] + 1e-9 < gfs["auto_acres"]:
                warnings.append(
                    f"{s['name']}: site of {gfs['acres']:.1f} acres is smaller than the "
                    f"~{gfs['auto_acres']:.1f} acres the building + yard need at "
                    f"{A['greenfield']['site_coverage']*100:.0f}% coverage (multi-storey or off-site yard assumed).")
    if i["future_kw"] <= i["current_kw"]:
        warnings.append("Future-ready kW/rack is not higher than current; upgrade analysis is trivial.")

    return {"inputs": i, "current": cur, "future": fut, "upgrade": upgrade,
            "warnings": warnings, "long_lead": LONG_LEAD}


def summary_for_llm(res: dict) -> dict:
    """Compact, rounded JSON payload the LLM narrates from."""
    def s(x):
        d = {
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
        if x["greenfield"]:
            g = x["greenfield"]
            d.update({
                "owner_costs_usd": {k: round(v) for k, v in x["owner_costs"].items()},
                "escalation_usd": round(x["escalation"]),
                "site_acres": round(g["acres"], 1),
                "utility_service_mw": round(g["utility_mw"], 1),
                "onsite_hv_substation": g["hv_yard_on"],
                "shell_core_usd_per_gsf": round(g["shell_per_gsf"]),
                "workbook_comparable_facility_usd_per_mw_it": round(g["workbook_comparable_per_mw"]),
                "workbook_band_usd_per_mw_it": [round(g["benchmark"]["low"]), round(g["benchmark"]["right"]),
                                                round(g["benchmark"]["high"])],
                "workbook_band_check": g["band_check"],
                "schedule_months": {k: round(v, 1) for k, v in g["schedule"]["drivers"].items()},
                "critical_path": g["schedule"]["critical_path"],
                "months_to_ready_for_service": round(g["schedule"]["months_to_rfs"], 1),
            })
        return d
    u = res["upgrade"]
    i = res["inputs"]
    return {
        "project_type": i.get("project_type"),
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
            "B_retrofit_land_and_utility_upgrade_usd": round(u.get("retrofit_owner_costs", 0)),
            "engine_recommendation": u["recommended"],
        },
        "warnings": res["warnings"],
        "long_lead_weeks": {n: f"{lo}-{hi}" for n, _, lo, hi in LONG_LEAD},
    }


if __name__ == "__main__":
    import json
    r = run_model()
    print(json.dumps(summary_for_llm(r), indent=2))
