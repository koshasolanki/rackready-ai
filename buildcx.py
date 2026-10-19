"""
RackReady AI - build, procurement, commissioning and readiness planning.

Everything here is generic, planning-level and tied to public codes and practice (see docs/VERIFICATION.md):
  * Phase-level schedule (pre-construction and build) that scales with MW, with overtime, weather and
    congestion productivity factors, and constrained by utility power and long-lead deliveries.
  * Reverse-scheduled order-by dates for long-lead equipment from public 2026 lead-time ranges.
  * Commissioning Levels 1-5, the liquid-loop hard stop, load-bank sizing and IST failure scenarios.
  * Construction-to-IT handoff table (10 feeds), a 30-step IT-readiness sequence and QA/field checklists.
  * Structured risk register (no probabilities, impact in months) with proven ways to avoid common delays,
    stage gates 0-7, the estimate accuracy label, a specification quick-reference, operations readiness
    and a glossary.
No cost values are used in this module.
"""
from __future__ import annotations

import math

WEEKS_PER_MONTH = 4.345

# --------------------------------------------------------------------------- estimate accuracy
# Plain-language label shown to users. The classification behind it is documented in docs/VERIFICATION.md.
ESTIMATE_LABEL = ("Early budget estimate (±30–50%), not a bid: built from per-MW benchmarks and design quantities before any "
                  "drawings exist, so the final cost can land well above or below it.")

# --------------------------------------------------------------------------- long-lead equipment
# (key, name, low wk, high wk, typical wk, basis). Quoted lead = released for manufacture (approved
# submittals) to delivery, including factory test and shipping. Public 2026 procurement surveys and
# the 2025 transformer supply study; confirm with the market at order time.
LEAD_TIMES = [
    ("main_tx", "Large power transformers (HV/MV, >50 MVA)", 100, 160, 128,
     "2025 industry study: power transformers average about 128 weeks (about 2.5 years); 2026 quotes 100-150+ weeks"),
    ("sub_tx", "Substation transformers (5-50 MVA, service upgrade)", 65, 110, 88,
     "2026 procurement surveys: substation-class transformers about 65-110 weeks"),
    ("mv_swgr_38", "MV switchgear, 38 kV class", 78, 104, 91, "2026 procurement surveys: 78-104 weeks"),
    ("mv_swgr_15", "MV switchgear, 15 kV class", 52, 80, 66, "2026 procurement surveys: 52-80 weeks"),
    ("unit_sub", "Unit-substation transformers (2.5-5 MVA)", 40, 65, 52, "2026 procurement surveys: 40-65 weeks (0-5 MVA)"),
    ("lv_swbd", "LV switchgear and switchboards", 18, 54, 36, "2026 manufacturer schedules and surveys: about 18-54 weeks"),
    ("gens", "Standby diesel generators (2.5-3.5 MW)", 62, 110, 82,
     "2026 procurement surveys: 62-82 weeks at 2.5-3.5 MW, 90-110 weeks above 3 MW"),
    ("ups", "UPS modules and batteries", 30, 60, 44, "2026 procurement surveys: 30-48 weeks (500-1,500 kVA), 40-60 modular"),
    ("chillers", "Chillers / dry or adiabatic coolers", 40, 70, 55, "2026 consultant survey: chillers 40-70 weeks"),
    ("cdus", "Coolant distribution units (CDUs)", 30, 50, 40, "2026 consultant survey: 30-50 weeks"),
    ("busway", "High-amp busway and tap-off units", 16, 40, 26, "2026 manufacturer schedules: about 6-40 weeks; high-amp runs and tap-offs at the long end (16-40 used)"),
    ("fire", "Fire pumps and pre-action valve assemblies", 20, 36, 28, "Typical 2026 quotes: fire pumps 20-36 weeks, valves 14-24"),
    ("fiber", "Telecom fiber laterals and carrier services", 26, 78, 52, "Typical carrier lateral builds 6-18 months; order 18+ months ahead"),
]
TURBINE_NOTE = ("Gas turbines for on-site or bridging power: aeroderivative units about 40 months; heavy-duty "
                "frame units largely sold out to about 2030, with some slots quoted for 2031-2032 (public 2026 "
                "reporting). Reciprocating gas engines are typically quoted for 2028-2029 delivery.")

# Reverse-schedule components (weeks), mid-points of the usual public procurement ranges
PROCUREMENT = {"spec_rfq": 6, "bids": 6, "po": 3, "submittal_prep": 5, "submittal_review": 8, "staging": 1.5,
               "buffer_pct": 0.15}
PRE_PO_WEEKS = PROCUREMENT["spec_rfq"] + PROCUREMENT["bids"] + PROCUREMENT["po"]           # 15
SUBMITTAL_WEEKS = PROCUREMENT["submittal_prep"] + PROCUREMENT["submittal_review"]          # 13

# Overtime: productivity per hour from published overtime-productivity studies (sustained schedules);
# duration factor = 40 h / (hours x productivity).
OVERTIME = {40: 1.00, 50: 0.965, 60: 0.875, 70: 0.80}


def overtime_factor(hours: int) -> float:
    h = min(OVERTIME, key=lambda x: abs(x - int(hours or 40)))
    return 40.0 / (h * OVERTIME[h])


def auto_build_months(it_mw: float, greenfield: bool) -> float:
    """NTP to substantial completion (including commissioning), scaled with MW. Planning assumption."""
    if greenfield:
        return min(max(12.0 + 12.0 * math.sqrt(max(it_mw, 0.1) / 100.0), 12.0), 40.0)
    return min(max(8.0 + 6.0 * math.sqrt(max(it_mw, 0.1) / 100.0), 8.0), 24.0)


def _wk(m):
    return m * WEEKS_PER_MONTH


def _mo(w):
    return w / WEEKS_PER_MONTH


def schedule(*, it_mw: float, greenfield: bool, design_months: float, build_months: float | None,
             months_to_power: float | None, onsite_hv: bool, d2c: bool, needs_new_service: bool = True,
             overtime_hours: int = 40, weather: float = 0.0, congestion: float = 0.0,
             lead_pick: str = "typ") -> dict:
    """Phase-level schedule in months from the start (month 0). lead_pick = typ | low | high lead times."""
    B0 = float(build_months) if build_months else auto_build_months(it_mw, greenfield)
    ot = overtime_factor(overtime_hours)
    wx, cg = 1.0 + float(weather or 0), 1.0 + float(congestion or 0)
    dm = float(design_months or (9 if greenfield else 4))
    phases = []

    def add(name, track, s, d, kind="task", note=""):
        phases.append({"phase": name, "track": track, "start": s, "dur": d, "end": s + d, "kind": kind, "note": note})
        return s + d

    # ---------------------------------------------------------------- pre-construction
    if greenfield:
        add("Site studies (Phase I ESA, geotech, survey, title, wetlands)", "Pre-construction", 0.0, 4.0,
            note="ESA 4-6 wk, geotech 6-10 wk, survey and title 4-8 wk, wetlands 8-16 wk, run in parallel")
        add("Utility application and agreement", "Pre-construction", 0.0, 10.0,
            note="Application review 3-6 months plus agreement 3-9 months; firm MW and date in writing")
    else:
        add("Existing-conditions survey (structure, power, cooling, roof)", "Pre-construction", 0.0, 2.0)
        if needs_new_service:
            add("Utility service-upgrade application", "Pre-construction", 0.0, 6.0)
    d_end = add("Design: schematic, 30%, 60%, 90%, issued for construction", "Pre-construction", 1.0 if greenfield else 0.5, dm,
                note="Long-lead orders are released between about 30% and 60-80% design")
    d0 = d_end - dm
    p_end = add("Permits (building, site, generator air permit)", "Pre-construction", d0 + 0.6 * dm, 4.0,
                note="Review typically 8-24 weeks; air permits for generators can take longer")
    gc_end = add("Contractor selection and GMP / contract", "Pre-construction", d0 + 0.3 * dm, 3.0,
                 note="8-16 weeks")
    ntp = max(p_end, gc_end, 4.0 if greenfield else 2.0)
    phases.append({"phase": "Notice to proceed (NTP)", "track": "Milestone", "start": ntp, "dur": 0.0, "end": ntp,
                   "kind": "milestone", "note": "Permit, GMP, insurance and site safety plan in place"})

    # ---------------------------------------------------------------- build (planned, unconstrained)
    B = B0

    def ext(share):
        return share * B * ot * wx

    def inte(share):
        return share * B * ot * cg

    if greenfield:
        add("Site work, grading, underground utilities, stormwater", "Build", ntp, ext(0.20))
        st_s = ntp + ext(0.10)
        add("Foundations and structure", "Build", st_s, ext(0.30))
        dry_s = st_s + ext(0.20)
        dry_e = add("Dry-in (roof, envelope)", "Build", dry_s, ext(0.20))
        mep_s = dry_s + ext(0.10)
    else:
        add("Strip-out and make-safe", "Build", ntp, inte(0.15))
        add("Structural upgrades (slab, supports, openings)", "Build", ntp + inte(0.05), inte(0.25))
        mep_s = ntp + inte(0.15)
        dry_e = mep_s
    mep_d = inte(0.38 if greenfield else 0.55)
    add("MEP rough-in and equipment set", "Build", mep_s, mep_d,
        note="Top-down overhead install: supports, sprinkler, tray, busway, piping and hoses, then floor coating")
    energ_planned = max(mep_s + 0.80 * mep_d, dry_e)
    energ_d = inte(0.16)
    cx_d = 0.16 * B * cg            # testing is sequence-limited: overtime does not shorten it
    cx_planned = energ_planned + 0.5 * energ_d

    # ---------------------------------------------------------------- long-lead items and need dates
    tx = ("main_tx" if onsite_hv else "sub_tx") if (onsite_hv or (not greenfield and needs_new_service)) else None
    keys = ([tx] if tx else []) + \
        ["mv_swgr_38" if onsite_hv else "mv_swgr_15", "unit_sub", "lv_swbd", "gens", "ups", "busway",
         "chillers", "fire", "fiber"] + (["cdus"] if d2c else [])
    group = {"main_tx": "power", "sub_tx": "power", "mv_swgr_38": "power", "mv_swgr_15": "power", "unit_sub": "power", "lv_swbd": "power",
             "gens": "power", "ups": "power", "busway": "power", "chillers": "cooling", "cdus": "cooling",
             "fire": "life safety", "fiber": "network"}
    lt = {k: (n, lo, hi, typ, src) for k, n, lo, hi, typ, src in LEAD_TIMES}

    def needs(en, cxs, ms):
        return {"main_tx": en - 1.0, "sub_tx": en - 1.0, "mv_swgr_38": en - 3.0, "mv_swgr_15": en - 3.0, "unit_sub": en - 2.5,
                "lv_swbd": en - 2.5, "gens": en - 1.5, "ups": en, "busway": ms + 0.5 * mep_d, "chillers": en - 1.0,
                "cdus": en + 0.25 * energ_d, "fire": ms + 0.4 * mep_d, "fiber": cxs}

    def chain(k):
        typ = {"low": lt[k][1], "high": lt[k][2]}.get(lead_pick, lt[k][3])
        nb = PRE_PO_WEEKS + SUBMITTAL_WEEKS + typ + PROCUREMENT["staging"]
        return nb, PROCUREMENT["buffer_pct"] * (SUBMITTAL_WEEKS + typ)

    # pass 1: planned need dates -> how far each item would slip if the RFQ went out today (month 0)
    n0 = needs(energ_planned, cx_planned, mep_s)
    slips = {k: max(0.0, _mo(chain(k)[0]) - n0[k]) for k in keys}
    power_m = float(months_to_power) if (greenfield and months_to_power) else 0.0
    slip_power = max([slips[k] for k in keys if group[k] == "power"] or [0.0])
    slip_cool = max([slips[k] for k in keys if group[k] == "cooling"] or [0.0])
    cands = {"Design, permits and construction (planned)": energ_planned,
             "Utility power available": power_m,
             "Power-chain equipment delivery": energ_planned + slip_power}
    energ = max(cands.values())
    cx = max(energ + 0.5 * energ_d, cx_planned + slip_cool)
    sc = cx + cx_d
    # pass 2: order-by dates against the achievable schedule
    n1 = needs(energ, cx, mep_s)
    items = []
    for k in keys:
        name, lo, hi, typ, src = lt[k]
        nb, buf = chain(k)
        need = n1[k]
        rfq = need - _mo(nb + buf)
        po = rfq + _mo(PRE_PO_WEEKS)
        drive = slip_power if group[k] == "power" else slip_cool if group[k] == "cooling" else -1
        drives = (energ > max(energ_planned, power_m) + 1e-6 if group[k] == "power" else
                  cx_planned + slip_cool > energ + 0.5 * energ_d + 1e-6 if group[k] == "cooling" else False)
        if slips[k] > 0.05 and abs(slips[k] - drive) < 1e-6 and drives:
            flag = f"Critical: sets the schedule (+{slips[k]:,.1f} months); order now and reserve a factory slot"
        elif rfq < 0:
            flag = "Order now (inside the buffer)"
        elif po < ntp:
            flag = "Order before NTP"
        else:
            flag = "After NTP"
        items.append({"key": k, "item": name, "group": group[k], "lead_low": lo, "lead_high": hi, "lead_typ": typ,
                      "need": need, "rfq": rfq, "po": po, "earliest": _mo(nb), "slip": slips[k],
                      "flag": flag, "basis": src, "order_ahead": need - max(rfq, 0.0)})
    if energ > energ_planned + 0.05:
        add("Waiting for power-chain equipment or utility power", "Waiting", energ_planned, energ - energ_planned,
            kind="wait", note="Field work is ready before the equipment or the utility: order earlier or reserve slots")
    add("Energization: insulation tests, relay settings, MV, unit substations, generators, UPS", "Build",
        energ, energ_d, note="Megger 4-6 wk, relay settings 3-4 wk, unit substations 5-8 wk, generators 4-6 wk, UPS 6-8 wk")
    add("Commissioning L3-L5: loop flush, start-up, functional tests, IST, reliability run", "Commissioning",
        cx, cx_d, note="Flush 2-3 wk; IST 1-2 wk per hall; reliability run 1-4 wk. Hard stop before IT power-on")
    phases.append({"phase": "Substantial completion / ready for IT", "track": "Milestone", "start": sc, "dur": 0.0,
                   "end": sc, "kind": "milestone", "note": "Follows a passed IST; warranty periods usually start here"})
    add("Punch list, closeout and final completion", "Closeout", sc, 2.0)

    # drivers: SC month if each constraint acted alone
    tail = sc - energ
    drivers = {
        "Design, permits and construction": energ_planned + tail,
        "Utility power + energization + commissioning": (power_m + tail) if power_m else 0.0,
        "Power-chain long-lead equipment (transformers, switchgear, generators)": energ_planned + slip_power + tail,
    }
    if slip_cool:
        drivers["Cooling equipment (chillers, CDUs)"] = cx_planned + slip_cool + cx_d
    drivers = {k: v for k, v in drivers.items() if v > 0}
    crit = max(drivers, key=drivers.get)
    for x in items:
        x["float_note"] = (f"{x['rfq']:,.1f} months of float before the RFQ must go out" if x["rfq"] >= 0 else
                           f"{-x['rfq']:,.1f} months short (needs a slot reservation or a later need month)")
    return {"phases": phases, "items": items, "ntp": ntp, "energization": energ, "cx_start": cx, "sc": sc,
            "final": sc + 2.0, "build_months": B, "build_months_auto": not build_months, "design_months": dm,
            "overtime_hours": int(overtime_hours or 40), "overtime_factor": ot, "weather": float(weather or 0),
            "congestion": float(congestion or 0), "power_month": power_m, "drivers": drivers, "critical_path": crit,
            "months_to_rfs": sc, "mid_point_months": ntp + B / 2}


# --------------------------------------------------------------------------- commissioning
CX_LEVELS = [
    {"level": "L1", "name": "Factory witness test (FWT/FAT)",
     "proves": "Major equipment meets the approved submittal before it ships (switchgear, transformers, UPS, "
               "generators, chillers, CDUs, busway).",
     "entry": "Approved submittals and test procedures; calibrated test equipment; witness plan issued.",
     "exit": "Signed factory test records; punch items closed or dated; as-built matches the submittal.",
     "witness": "Manufacturer, engineer of record, commissioning agent (CxA), owner"},
    {"level": "L2", "name": "Delivery and installation check",
     "proves": "Equipment arrived undamaged and complete and is installed per drawings and manufacturer instructions.",
     "entry": "Receiving plan; impact/tilt recorders on transformers and skids; nameplate data list.",
     "exit": "Delivery inspection signed; nameplates recorded in the asset register; installation checklists done.",
     "witness": "Contractor QA, CxA, owner's representative"},
    {"level": "L3", "name": "Start-up and pre-functional checks",
     "proves": "Each component is correctly connected and starts safely: insulation resistance, torque, "
               "rotation, point-to-point controls, flush and fill.",
     "entry": "L2 complete; LOTO and energization plan approved; manufacturer start-up technician on site.",
     "exit": "Start-up reports; insulation-resistance and torque records; pre-functional checklists signed.",
     "witness": "Installing trade, manufacturer, CxA"},
    {"level": "L4", "name": "Functional performance test (FPT)",
     "proves": "Each system performs its sequences across its full operating range: transfers, alarms, "
               "redundancy, capacity at design load with load banks.",
     "entry": "All L3 items closed; readiness review held (open L3 items consume the test window); load banks on site.",
     "exit": "Each system passes its scripted tests at design load; thermographic scan under load; issues retested.",
     "witness": "CxA, owner, operations staff; authority having jurisdiction (AHJ) for life-safety systems"},
    {"level": "L5", "name": "Integrated systems test (IST)",
     "proves": "All systems work together under failure scenarios at full simulated IT load, proving the "
               "redundancy claim (N+1 or 2N) end to end.",
     "entry": "All L4 complete; liquid-loop hard stop passed; load banks at design IT load; time-synchronised "
              "instruments; abort and recovery plan.",
     "exit": "Every scenario passed or retested; transfer and restart times recorded; owner acceptance. "
             "Substantial completion follows a passed IST.",
     "witness": "CxA (leads), owner, operations team, insurer where required"},
]

HARD_STOP = ("Hard stop: no IT power-on and no connection of IT cold plates until the liquid loop has passed (1) "
             "hydrostatic or pneumatic leak test at the specified pressure and hold, (2) flushing to the specified "
             "cleanliness (particle count and filter inspection), (3) water chemistry and coolant concentration "
             "per the CDU/IT vendor fluid specification, and (4) leak-detection functional test, with signed "
             "certificates.")

IST_SCENARIOS = [
    ("Utility failure at full load", "Generators start and take load within 10 s (NFPA 110 Type 10); UPS rides "
     "through; no rack loses power; timed retransfer to utility."),
    ("Generator fails to start or trips during an outage", "Remaining sets carry the load (N+1); load-shed logic "
     "works if designed in."),
    ("Loss of one UPS module or one UPS system", "Redundant modules or the other path carry the critical load; "
     "bypass operation verified."),
    ("A-path (or B-path) shutdown under full load", "Every rack stays up on the other path; no single-corded "
     "equipment; A and B never share an upstream board or breaker."),
    ("CDU pump failure and loss of a whole CDU", "Redundant pump or CDU maintains flow and supply temperature "
     "within the IT vendor envelope; alarms reach the monitoring system."),
    ("Loss of a chiller or dry cooler", "Cooling redundancy holds; thermal storage or loop mass covers chiller "
     "restart; no inlet temperature exceeds the limit."),
    ("Leak alarm at a manifold or CDU", "Detection, alarm and isolation logic work; response procedure followed."),
    ("Controls and monitoring failure (BMS/EPMS controller or network)", "Plant fails safe and keeps running; "
     "alarms annunciate; recovery documented."),
    ("Black start (total facility restart from cold)", "Sequenced restart of power, pumps, CDUs and cooling "
     "without manual workarounds."),
    ("Design-day high ambient at full IT load", "Heat rejection holds at the design wet-bulb or dry-bulb; "
     "economizer changeover sequences verified."),
    ("Fire alarm interface", "Damper, pre-action and clean-agent sequences operate as designed; no unintended "
     "power-off of IT."),
]


def load_banks(*, it_mw: float, liquid: float, d2c: bool, hall_mw: float = 25.0, gen_mw: float = 3.0) -> dict:
    halls = max(1, math.ceil(it_mw / hall_mw - 1e-9))
    per_hall = it_mw / halls
    liq = per_hall * (liquid if d2c else 0.0)
    air = per_hall - liq
    return {"halls": halls, "hall_mw": per_hall, "liquid_mw": liq, "air_mw": air,
            "liquid_units_250kw": math.ceil(liq * 1000 / 250 - 1e-9) if liq else 0,
            "air_units_1mw": math.ceil(air - 1e-9) if air > 0 else 0, "gen_bank_mw": gen_mw,
            "notes": [
                f"IST on each hall at its design IT load: {per_hall:,.1f} MW per hall x {halls} hall(s).",
                (f"Liquid-cooled load banks for {liq:,.1f} MW per hall connected to the technology loop (so the CDUs "
                 f"and heat rejection are proven), plus {air:,.1f} MW of air load banks for the residual air heat."
                 if d2c else f"Air load banks for {air:,.1f} MW per hall in the hot aisles."),
                f"Generator acceptance per NFPA 110: 2-hour full-load test (30% for 30 min, 50% for 30 min, 100% for "
                f"60 min) on each {gen_mw:.1f} MW set, using building load plus a load bank.",
                "Design load-bank connection points into the switchboards; book load banks and thermal cameras 4-8 "
                "weeks ahead; plan where the heat goes.",
                "Indicative unit counts assume 250 kW liquid-cooled and 1 MW air units (assumption; sizes vary).",
            ]}


# --------------------------------------------------------------------------- handoff feeds
FEEDS = [
    {"feed": "Power", "scope": "Construction ends at the busway tap-off or branch breaker; IT starts at the rack PDU plug.",
     "spec": "Each of A and B rated for the full rack load; continuous load <= 80% of breaker/busway rating; phase "
             "rotation and labels per the as-built schedule.",
     "test": "Insulation resistance (NETA ATS), torque check, phase rotation, voltage at the tap-off, A/B origin "
             "traced to separate upstream boards.",
     "failure": "A and B traced to the same board; tap-off in the wrong place; plug type mismatch.",
     "prevention": "Freeze the rack layout before busway release; trace every A/B pair; whip schedule with origins."},
    {"feed": "Cooling (liquid and air)", "scope": "Construction ends at the CDU secondary isolation valves or the rack "
     "manifold quick-disconnect (document which); IT owns the cold plates.",
     "spec": "Supply temperature, flow per rack, pressure and coolant chemistry per the CDU/IT vendor; rack inlet air "
             "within the ASHRAE recommended envelope.",
     "test": "Hydrostatic test, flush to cleanliness, chemistry certificate, per-rack flow verification, thermal "
             "soak at design load with load banks.",
     "failure": "Particles clogging cold plates; low-pressure test only; flow imbalance; condensation on rear-door coils.",
     "prevention": "Capped pipe ends, flush with temporary strainers, test at design pressure, dew-point checks."},
    {"feed": "Network pathways", "scope": "Construction ends at tray, conduit and backbone patch panels; IT patches "
     "and installs active equipment.",
     "spec": "Two entrance rooms and diverse entrance routes about 20 m (66 ft) apart (TIA-942 / BICSI 002); tray "
             "fill within limits; bend radius 10x cable OD unloaded and 20x under pull tension.",
     "test": "Link certification (TIA-568), bidirectional OTDR on fiber, polarity check, label audit (TIA-606).",
     "failure": "Telecom carrier laterals late; sharp tray edges; bend radius violations; tray already full.",
     "prevention": "Order carriers 18+ months ahead; deburred fittings; plan tray at about 2x day-one need."},
    {"feed": "Space and structure", "scope": "Construction ends at the finished, sealed slab, rack anchors and floor "
     "markings; IT sets and bolts racks.",
     "spec": "Floor flatness and levelness per ASTM E1155 (for example FF50/FL35, measured within 72 h); slab rated "
             "for the rack weight; clear height for racks plus overhead services.",
     "test": "F-number survey, anchor pull tests, survey of rack positions, rolling-load check of the delivery path.",
     "failure": "Racks rock or cannot align; anchors do not match the rack base; cracking under heavy racks.",
     "prevention": "Use the rack vendor template; measure F-numbers on pour day; design for the future rack weight."},
    {"feed": "Environment", "scope": "Construction delivers the hall within the design envelope; IT monitors at the "
     "rack inlet.",
     "spec": "ASHRAE recommended 18-27 C inlet; dew point -9 C to 15 C and <= 70% RH (<= 50% RH where corrosive "
             "gases are present); MERV 13 minimum filtration; slight positive pressure (about +0.02 to +0.10 in. w.c.).",
     "test": "Thermal mapping at load, sensor calibration, pressure measurement at openings, particle count after "
             "the technical clean.",
     "failure": "Uncalibrated sensors; filters loaded with construction dust; negative pressure pulling in dust.",
     "prevention": "Dust control, pre-occupancy filter change, technical clean, no dusty trades after the clean."},
    {"feed": "Fire and life safety", "scope": "Construction delivers detection, suppression and EPO accepted by the "
     "AHJ; operations owns monitoring.",
     "spec": "NFPA 72 detection (aspirating where specified), NFPA 13 pre-action, NFPA 2001 clean agent where used, "
             "NFPA 75/76 for IT and telecom spaces, NFPA 70 Article 645 disconnect where that article is applied.",
     "test": "NFPA 13 hydro 200 psi for 2 h; pre-action air test 40 psi for 24 h with <= 1.5 psi loss; NFPA 2001 "
             "room-integrity (door-fan) test for a 10-minute hold; AHJ acceptance.",
     "failure": "Wrong cross-zoning; unsealed penetrations; low cylinder pressure; EPO not actually shutting down.",
     "prevention": "Firestop register with photos; full sequence tests; cylinder weights checked on receipt."},
    {"feed": "Security", "scope": "Construction installs readers, locks, cameras and intrusion sensors; the owner "
     "manages credentials and monitoring.",
     "spec": "Layered zones (perimeter, building, hall, cabinet); two-factor entry at halls; egress doors fail-safe "
             "on fire alarm per code; video retention per policy.",
     "test": "Per-door function test (unlock, held, forced), anti-passback and interlock tests, fire-alarm release "
             "test, camera coverage at night, recording playback.",
     "failure": "Fail-secure doors on egress routes; storage too small for the retention period; coverage gaps.",
     "prevention": "Door-by-door function schedule agreed with the fire authority; size storage from the policy."},
    {"feed": "Monitoring and controls", "scope": "Construction delivers BMS/EPMS points and asset data; operations "
     "configures dashboards and DCIM.",
     "spec": "Open protocols (BACnet, ASHRAE 135; Modbus); written sequences of operation (ASHRAE Guideline 36 where "
             "applicable); OT network segmentation per IEC 62443; network sized for 5-10x points.",
     "test": "Point-to-point verification of every input and output, sequence tests, alarm routing, trend checks, "
             "alarm rationalisation with operations.",
     "failure": "Sequences demonstrated for the first time at witness testing; nuisance alarms; poor asset data.",
     "prevention": "Review sequences with operations before programming; capture asset data at delivery."},
    {"feed": "Grounding and bonding", "scope": "Construction delivers the electrode system, bonding network and "
     "rack ground bars; IT bonds equipment to the rack.",
     "spec": "NEC Article 250 grounding; TIA-607 telecom bonding; lightning protection per NFPA 780; surge "
             "protective devices Type 1/2/3 per UL 1449.",
     "test": "Ground resistance per IEEE 81 (fall-of-potential), continuity of bonds, inspection before backfill.",
     "failure": "High ground impedance; bonds missing across tray joints; electrode damaged by later civil work.",
     "prevention": "Hold point before backfill; photograph buried work; re-test after nearby excavation."},
    {"feed": "Logistics", "scope": "Construction delivers docks, staging and a clear path to every rack position.",
     "spec": "Equipment path about 8 ft wide x 10 ft high or larger for integrated racks and CDU skids; staging "
             "about 10-25% of hall area; floor rated for the rolling load of a loaded rack.",
     "test": "Walk the path with a rack-size template or a mock-up; rolling-load check; door clear sizes measured.",
     "failure": "Rack or skid does not fit a door, ramp or elevator; staging spills into the hall.",
     "prevention": "Check the largest item dimensions before ordering doors; keep the heavy-haul route open."},
]

IT_READINESS = [
    "Utility agreement signed with firm MW and an energization date",
    "Long-lead orders released (transformers, switchgear, generators, UPS, CDUs, chillers, busway)",
    "Telecom carrier fiber laterals ordered (18+ months ahead) on diverse routes",
    "Permits issued; notice to proceed",
    "Site work, underground duct banks and grounding grid inspected before backfill",
    "Foundations and slab poured; F-numbers measured within 72 hours",
    "Structure complete; anchor bolts and column positions surveyed",
    "Dry-in: roof and envelope watertight, temporary humidity control before electrical gear arrives",
    "Overhead supports and seismic bracing installed (top-down sequence)",
    "Sprinkler mains, cable tray and busway installed per the coordinated model",
    "Liquid headers, manifolds and hoses installed with capped ends; firestopping as each trade finishes",
    "Prototype row installed and signed off by the owner before the layout is repeated",
    "MV switchgear, transformers and unit substations set; insulation resistance and torque checks done",
    "Generators, fuel system and UPS installed; battery room ventilated and at temperature",
    "Chillers or dry coolers, pumps and CDUs installed; piping hydrostatically tested",
    "Utility energization and MV energization (witnessed, under lockout/tagout control)",
    "LV distribution, busway and tap-offs energized; A/B origins traced and labelled",
    "Generator acceptance (NFPA 110) and UPS functional tests",
    "Liquid loop flushed, cleaned, filled, chemistry certified, leak-tested (hard stop)",
    "Controls: BMS/EPMS point-to-point, sequences and alarms verified",
    "Fire alarm, pre-action and clean agent accepted by the AHJ; EPO tested",
    "Security systems commissioned (access control, video, intrusion)",
    "Floor coating, then a technical clean with particle count; no dusty trades afterwards",
    "Level 4 functional tests at design load with load banks; thermographic scan",
    "Level 5 integrated systems test with all failure scenarios",
    "Substantial completion; handover documents, training and spares in place",
    "Racks delivered, set, anchored and connected (power whips and quick-disconnects)",
    "Per-rack flow verified and IT cold plates connected after the loop is certified",
    "Network provisioning: carrier services live, fabric and management networks patched and tested",
    "IT burn-in and acceptance; production ready",
]

CHECKLISTS = {
    "Inspection and test plan (ITP) hold and witness points": [
        "Hold: grounding grid and duct banks inspected and photographed before backfill",
        "Hold: rebar, embeds and anchor bolts inspected before each pour",
        "Hold: concealed MEP inspected and pressure-tested before ceilings or insulation",
        "Hold: liquid loop hard stop (leak, flush, chemistry, leak detection) before IT power-on",
        "Witness: factory tests (L1) for switchgear, transformers, UPS, generators, chillers, CDUs",
        "Witness: insulation resistance, relay settings and first energization of each MV section",
        "Witness: NFPA 13 hydro and pre-action air tests; NFPA 2001 door-fan test; AHJ acceptance",
        "Witness: L4 functional tests and the L5 IST with operations staff present",
    ],
    "Liquid-loop cleanliness": [
        "Pipe, fittings and hoses delivered capped and stored off the ground; caps kept on until connection",
        "Welding and joining procedures qualified; internal inspection (borescope) of sample joints",
        "Hydrostatic test at the specified pressure (piping commonly 1.5x design per ASME B31.9) with no pressure loss",
        "Flush with temporary strainers at the specified velocity until filters and particle counts pass",
        "Fill with the specified fluid; chemistry and glycol concentration certified per the CDU/IT vendor",
        "Inert-gas or pressure leak test of rack manifolds and quick-disconnects before IT connection",
        "Leak detection tested by simulated leak at each zone; alarms reach the monitoring system",
        "Per-rack flow verified; filters on site for the first change; chemistry limits handed to operations",
    ],
    "Torque marking and terminations": [
        "Calibrated torque tools with certificates; torque values from the manufacturer's data",
        "Every bolted electrical joint torqued, then marked with a torque-seal stripe across bolt and surface",
        "Second-person check on MV terminations; terminators qualified for the cable type",
        "Busway joints torqued and recorded run by run",
        "Thermographic scan at or near full load during L4; hot spots retorqued and re-scanned",
    ],
    "Insulation resistance (megger) before energization": [
        "Test per NETA ATS: for example 1,000 VDC for 600 V-class equipment and 2,500 VDC for 5-15 kV-class, "
        "with minimum values from the NETA table or the manufacturer",
        "Record readings with temperature; correct to 20 C where the procedure requires",
        "Test MV cable (and VLF withstand where specified) after termination",
        "Transformers: insulation resistance, turns ratio and winding resistance; oil sample and dissolved-gas baseline",
        "Review transformer impact and tilt recorders on delivery before any test",
    ],
    "Dry-in and temporary protection": [
        "Roof and envelope watertight; openings closed or protected",
        "Temporary heat and dehumidification so electrical rooms stay dry (commonly above 50 F and below about 60% RH)",
        "No electrical gear or batteries delivered into an unconditioned or wet room",
        "Temporary power and lighting inspected; humidity logged where equipment is stored",
    ],
    "Concrete pour day": [
        "Pre-pour inspection signed: rebar, embeds, sleeves, anchor templates, vapor retarder, grounding",
        "Mix ticket checked against the approved design; slump (ASTM C143) and air tested on site",
        "Cylinders cast (ASTM C31) at the specified frequency, for example one set per 150 cubic yards and per day",
        "Finishing and curing plan; hot or cold weather protection",
        "Floor flatness and levelness measured per ASTM E1155 within 72 hours",
    ],
    "Room readiness (MV room, battery room, generator yard, hall)": [
        "MV room: clear working space per NEC 110.26/110.34, arc-flash labels from the IEEE 1584 study, dry and lit",
        "Battery room: ventilation for hydrogen where required (lead-acid), detection, eyewash, spill control, "
        "temperature about 20-25 C (68-77 F); lithium-ion per NFPA 855 and UL 9540A data",
        "Generator yard: exhaust does not recirculate to intakes with all sets running; fuel containment and leak "
        "detection; load-bank connection; noise per permit",
        "Data hall: overhead work complete, floor coated, technical clean done, containment fitted, labels applied",
    ],
    "Critical lifts and heavy equipment": [
        "Engineered lift plan where the lift exceeds about 75% of the crane chart, uses two cranes, or lifts over "
        "occupied or energized areas (common program definition)",
        "Ground bearing verified; outriggers on mats; exclusion zone set",
        "Wind and weather limits from the crane manufacturer; stop when exceeded",
        "Heavy-haul route surveyed; transformer pads and rails complete before arrival",
        "Trenches 5 ft or deeper protected per OSHA 1926.652; competent person on site",
    ],
    "Firestopping and closeout": [
        "Firestop installed to a tested system detail as each trade finishes, not at the end",
        "Penetration register with ID tag and photograph per penetration",
        "Hot work under permit; fire watch during and at least 1 hour after hot work (NFPA 51B, 2019 edition onward)",
        "Incident reporting: fatality to OSHA within 8 hours; in-patient hospitalization, amputation or loss of an "
        "eye within 24 hours (29 CFR 1904.39)",
        "As-builts include field changes made during commissioning; asset register imported to the CMMS",
    ],
}

# --------------------------------------------------------------------------- risks
def risk_register(*, greenfield: bool, kw: float, d2c: bool, it_mw: float, months_to_power: float | None,
                  items: list, platform_status: str = "shipping", horizon_active: bool = False,
                  needs_new_service: bool = True) -> list[dict]:
    late = [x["item"] for x in items if x["flag"].startswith(("Critical", "Order now"))]
    pre = [x["item"] for x in items if x["flag"] == "Order before NTP"]
    R = []

    def add(cat, trigger, mitigation, owner, phase, lo, hi, on, why):
        R.append({"category": cat, "trigger": trigger, "mitigation": mitigation, "owner": owner, "phase": phase,
                  "impact_low": lo, "impact_high": hi, "active": bool(on), "why": why})

    add("Utility interconnection", "No signed agreement with firm MW and date by Gate 1; study results delayed",
        "Early utility load study; phased energization; flexible (curtailable) load agreement; on-site bridging power",
        "Owner", "Pre-construction", 6, 24, greenfield or needs_new_service,
        "Greenfield or new service" if greenfield or needs_new_service else "Existing service is enough")
    add("Long-lead equipment", "Order-by month before NTP or less than 8 weeks of float",
        "Early equipment reservations with slot deposits before design is complete; frame agreements; factory inspection",
        "Owner / contractor", "Pre-construction to build", 3, 9, True,
        ("Late now: " + ", ".join(late)) if late else ("Order before NTP: " + ", ".join(pre)) if pre else "All orders after NTP")
    add("Permits and environmental (air, stormwater, wetlands)", "Generator air permit or wetland delineation not filed by 30% design",
        "Early environmental review at site selection; pre-application meetings; design to the permit limits",
        "Owner / designer", "Pre-construction", 3, 6, greenfield, "Greenfield site")
    add("Geotechnical and contamination", "Unexpected rock, soft soil or contamination in the Phase I/II findings",
        "Complete geotech and ESA before design freeze; carry a ground allowance in the schedule",
        "Owner", "Pre-construction / site work", 1, 4, greenfield, "Greenfield site")
    add("Labor availability", "Electricians, pipefitters or commissioning technicians short in the look-ahead",
        "Labor agreement and workforce plan; modular prefabrication; realistic overtime (productivity falls above about 50 h/week)",
        "Contractor", "Build", 2, 6, True, f"{it_mw:,.0f} MW build")
    add("Density or scope change", "Rack platform or kW/rack changes after long-lead release",
        "Freeze the design basis in writing at Gate 2; design provisions for the future rack",
        "Owner", "Design", 2, 6, kw >= 100 or horizon_active, "High density or a future-proof horizon")
    add("Design coordination", "Clashes in the ceiling zone (sprinkler, tray, busway, piping) found in the field",
        "Coordinated 3D model; prototype row signed off before repetition", "Designer / contractor", "Design to build",
        1, 3, True, "All projects")
    add("Slab flatness and floor loading", "F-numbers below spec; rack point loads above the slab design",
        "Measure F-numbers on pour day; design for the future rack weight; check the delivery path",
        "Structural engineer / contractor", "Build", 1, 2, kw >= 100, "Racks at 100 kW or more are heavy")
    add("Liquid-loop leaks and cleanliness", "Failed pressure, flush or chemistry test; particles at the filters",
        "Clean-build protocol, capped ends, test at design pressure, hard stop before IT power-on",
        "Mechanical contractor / CxA", "Commissioning", 1, 3, d2c, "Direct-to-chip liquid cooling")
    add("CDU redundancy and coolant supply", "CDU deliveries late; coolant or filters not on site for the flush",
        "Order CDUs and consumables early; N+1 CDUs per zone; fluid spec agreed with the IT vendor",
        "Owner / mechanical contractor", "Build / commissioning", 1, 3, d2c, "Direct-to-chip liquid cooling")
    add("IST failure or load-bank availability", "Open L3/L4 items at the IST readiness review; load banks not booked",
        "Readiness review before L4 and L5; book load banks 4-8 weeks ahead; protect the IST window",
        "CxA / contractor", "Commissioning", 1, 3, True, "All projects")
    add("Weather", "Exterior work in the wet or freezing season; lift wind limits", "Season-aware sequencing; "
        "winter protection; dry-in before electrical gear", "Contractor", "Build", 1, 3, greenfield, "Greenfield site")
    add("OT cybersecurity", "BMS/EPMS on flat networks; default passwords; remote access not controlled",
        "IEC 62443 zones and conduits; vendor access control; testing before handover", "Owner / controls contractor",
        "Design to operations", 0, 2, True, "All projects")
    add("Trade policy and supply shocks", "Tariff or sourcing restriction on transformers, switchgear or steel",
        "Dual-source where possible; price and delivery protection in purchase orders", "Owner", "Pre-construction to build",
        1, 4, True, "All projects")
    add("Safety incident", "Energization, work at height, critical lifts, liquid near live gear",
        "Permit-to-work and LOTO, lift plans, daily briefings; tighten controls as systems energize", "Contractor",
        "Build to commissioning", 0, 2, True, "All projects")
    add("Clean-agent supply", "Agent or cylinder deliveries constrained", "Confirm FK-5-1-12 supply (one major "
        "producer stopped making it at the end of 2025) or design for an inert-gas system", "Designer / fire contractor",
        "Design", 1, 3, True, "Clean agent in network and electrical rooms")
    add("Roadmap uncertainty", "Announced rack power, weight or coolant spec changes before delivery",
        "Get OEM data in writing; keep provisions flexible", "Owner", "Design to IT install", 1, 4,
        platform_status in ("announced", "estimated", "speculative", "custom") or horizon_active,
        "Roadmap platform or future horizon")
    add("Community opposition", "Organised objections at zoning hearings (noise, water, power bills, traffic, views)",
        "Engage the community before filing; community benefit agreement; design to noise and water limits; "
        "publish the water and power plan", "Owner", "Pre-construction", 3, 18, greenfield, "New site needs zoning approval")
    add("Water supply and wastewater", "Utility cannot commit water or discharge capacity; drought restrictions",
        "Dry or closed-loop cooling (little or no evaporative water); reclaimed water; on-site treatment",
        "Owner / designer", "Pre-construction", 2, 12, greenfield, "New site needs water and discharge permits")
    add("Transmission constraints", "Utility study shows network upgrades before full MW can be served",
        "Phased energization (MW in steps as upgrades finish); flexible-load agreement; site near existing capacity",
        "Owner / utility", "Pre-construction to energization", 6, 36, greenfield and it_mw >= 50,
        "50 MW or more usually needs transmission-level service")
    add("Gas supply for on-site power", "No firm gas pipeline capacity for bridging or on-site generation",
        "Confirm pipeline capacity and lateral timing before committing to gas; consider batteries or fuel cells",
        "Owner", "Pre-construction", 3, 18, bool(greenfield and (months_to_power or 0) > 36),
        "Bridging power is likely when the utility wait is above 36 months")
    add("Financing", "Funding not closed before long-lead deposits or NTP; lender requires firm power",
        "Phase the capital with the energization steps; secure the power agreement first; early lender engagement",
        "Owner", "Pre-construction", 2, 9, greenfield, "Large new build")
    add("Bridging power availability", "Utility date later than the IT need; turbines or engines not available",
        "Plan for multi-year turbine backlogs; consider engines, fuel cells or batteries; verify permits",
        "Owner", "Pre-construction", 3, 12, bool(greenfield and (months_to_power or 0) > 36),
        "Utility wait above 36 months")
    return R


# --------------------------------------------------------------------------- governance and references
STAGE_GATES = [
    ("G0", "Opportunity", "Business case and site criteria agreed; power, water and fiber checks started."),
    ("G1", "Site and power", "Power, water and fiber availability confirmed in writing; site control; updated budget estimate (about ±20–30%)."),
    ("G2", "Basis of design", "Basis of design signed; about 30% design; control budget (about ±10–20%); long-lead orders placed; "
                              "contractor and CxA selected."),
    ("G3", "Issued for construction", "Sealed drawings and calculations; coordinated model; GMP or fixed price."),
    ("G4", "Notice to proceed", "Permits, contract, insurance and bonds, site safety plan in place."),
    ("G5", "Commissioning start", "Building dried in, major equipment set, punch list under control, CxA and "
                                  "utility ready. (Substantial completion is later, after the IST.)"),
    ("G6", "Handover", "All Cx levels passed including IST; substantial completion; O&M manuals, as-builts, "
                       "training, spares and warranties accepted."),
    ("G7", "Warranty close", "Defects closed at the end of the warranty period (commonly about 12 months); "
                             "post-occupancy performance verified."),
]

SPEC_REFERENCE = [
    ("Concrete floor flatness", "FF50 / FL35 typical for rolling racks, measured within 72 h", "ASTM E1155, ACI 117"),
    ("Concrete testing", "Slump and cylinders at the specified frequency", "ASTM C143, ASTM C31 / C39, ACI 301"),
    ("Sprinkler hydrostatic test", "200 psi for 2 h (or 50 psi above working pressure if higher)", "NFPA 13"),
    ("Dry / pre-action air test", "40 psi for 24 h, loss <= 1.5 psi", "NFPA 13"),
    ("Sprinkler design (data hall)", "OH-1 0.15 gpm/sf or OH-2 0.20 gpm/sf over 1,500 sf; +30% area for double-"
     "interlock pre-action; 250 gpm hose; 60-90 min", "NFPA 13 (2022/2025); hazard class set by the engineer, AHJ and insurer"),
    ("Clean agent", "W = (V/S) x C/(100 - C); hold >= 85% of design concentration for 10 min; door-fan test",
     "NFPA 2001"),
    ("Fire pump", "Rated flow >= demand; >= 65% of rated pressure at 150% of rated flow", "NFPA 20, tanks NFPA 22"),
    ("Hot work", "Fire watch during and at least 1 h after hot work", "NFPA 51B (2019 edition onward)"),
    ("Hydronic piping test", "Hydrostatic at 1.5x design pressure, no leakage", "ASME B31.9"),
    ("Generators", "Type 10 (power within 10 s), Level 1; 2-h full-load acceptance test", "NFPA 110"),
    ("Fuel storage", "Hours at full load are an owner choice; Tier topology requires at least 12 h on site",
     "NFPA 110 class designation; Tier topology standard"),
    ("UPS", "Double conversion VFI classification", "IEC 62040-3"),
    ("Battery energy storage", "Fire and separation requirements; large-scale fire test data", "NFPA 855, UL 9540 / 9540A"),
    ("Battery temperature", "About 25 C; lead-acid life roughly halves for each 8-10 C above that", "IEEE 1188 / IEEE 450 practice"),
    ("MV switchgear", "Arc-resistant Type 2B where specified; acceptance tests", "IEEE C37.20.7, NETA ATS"),
    ("Arc flash", "Incident-energy study and labels", "IEEE 1584-2018, NFPA 70E"),
    ("Insulation resistance", "For example 1,000 VDC on 600 V-class, 2,500 VDC on 5-15 kV-class; minimums per table",
     "NETA ATS"),
    ("Harmonics", "Voltage and current distortion limits at the point of common coupling", "IEEE 519"),
    ("Continuous loads", "Conductors and devices at 125% of continuous load (load <= 80% of rating)", "NEC 210.19, 215.2, 230.42"),
    ("Voltage drop", "About 3% feeder or branch, 5% total (informational notes)", "NEC 210.19(A) and 215.2(A) informational notes"),
    ("IT space disconnect", "Disconnecting means for IT equipment where Article 645 is applied", "NFPA 70 Article 645"),
    ("Surge protection", "Type 1 at service, Type 2 at distribution, Type 3 at equipment", "UL 1449"),
    ("Grounding", "Ground resistance by fall-of-potential; lightning protection", "IEEE 81, NFPA 780, TIA-607"),
    ("Cabling", "Link certification; bidirectional OTDR on fiber; bend radius 10x OD (20x under pull)",
     "TIA-568, TIA-942, TIA-606"),
    ("Entrance diversity", "Two entrance rooms and routes about 20 m (66 ft) apart for higher ratings", "TIA-942-B, BICSI 002"),
    ("Thermal envelope", "Recommended 18-27 C inlet; dew point -9 C to 15 C and <= 70% RH (<= 50% with corrosive gases)",
     "ASHRAE TC 9.9 Thermal Guidelines (5th ed.)"),
    ("Liquid cooling water classes", "Facility water W17, W27, W32, W40, W45, W+ (supply temperature classes, C)",
     "ASHRAE TC 9.9 liquid cooling guidance"),
    ("Filtration", "MERV 13 minimum for recirculated and outdoor air (data halls)", "ASHRAE 52.2"),
    ("Controls", "BACnet open protocol; high-performance sequences; OT security", "ASHRAE 135, Guideline 36, IEC 62443"),
    ("Commissioning process", "Owner's project requirements, Cx plan, L1-L5", "ASHRAE Guideline 0 / Standard 202"),
    ("Efficiency metrics", "PUE, CUE, WUE definitions", "ISO/IEC 30134-2, -8, -9"),
    ("Data center standards", "Design and operations", "TIA-942, EN 50600, ISO/IEC 27001 (information security)"),
    ("Cooling towers", "Legionella water management program", "ASHRAE 188"),
    ("Incident reporting", "Fatality 8 h; in-patient hospitalization, amputation, eye loss 24 h", "OSHA 29 CFR 1904.39"),
    ("Excavation", "Protective system at 5 ft and deeper; engineer design at 20 ft", "OSHA 29 CFR 1926.652"),
]

OPS_READINESS = {
    "Handover package": ["Commissioning reports for L1-L5 with retests", "As-built drawings including field changes",
                         "O&M manuals and spare-parts lists", "Warranties with start dates (usually substantial completion)",
                         "Asset register imported into the CMMS", "Controls configuration and point lists",
                         "Training records and competency sign-off", "Critical spares on site at handover"],
    "Change control": ["Every change in the live facility has a written method of procedure (MOP)",
                       "Change advisory review approves risk, timing and back-out plan",
                       "Standard operating procedures (SOP) for routine work; emergency operating procedures (EOP) "
                       "rehearsed", "Isolation under permit-to-work and lockout/tagout",
                       "Post-change verification and document update"],
    "Incident levels (generic)": ["Level 1: customer-impacting outage or life-safety event: immediate escalation",
                                  "Level 2: redundancy lost (running on N): restore within hours",
                                  "Level 3: degraded component, redundancy intact: next maintenance window",
                                  "Level 4: observation or nuisance alarm: track and trend",
                                  "Every Level 1-2 event gets a blameless root-cause analysis"],
    "Efficiency metrics": ["PUE = total facility energy / IT energy (annual, ISO/IEC 30134-2)",
                           "WUE = site water (L) / IT energy (kWh) (ISO/IEC 30134-9)",
                           "CUE = CO2-equivalent emissions (kg) / IT energy (kWh) (ISO/IEC 30134-8)",
                           "Agree the metering boundary before meters are installed"],
    "First 90 days": ["Intense monitoring and trending to learn what normal looks like",
                      "Close remaining punch items; capture early failures under warranty",
                      "Refine procedures; repeat key switching rehearsals"],
}

GLOSSARY = {
    "AHJ": "Authority having jurisdiction: the code official or fire marshal who accepts the work.",
    "ATS / STS": "Automatic transfer switch (utility to generator) / static transfer switch (sub-cycle, between sources).",
    "BESS": "Battery energy storage system.",
    "BMS / EPMS / DCIM": "Building management, electrical power monitoring and data center infrastructure management systems.",
    "CDU": "Coolant distribution unit: pumps and a heat exchanger separating facility water from the rack (technology) loop.",
    "Cx / CxA": "Commissioning / commissioning agent (authority) that plans and witnesses tests.",
    "D2C": "Direct-to-chip liquid cooling with cold plates on GPUs and CPUs.",
    "FWT / FAT": "Factory witness test / factory acceptance test (Commissioning Level 1).",
    "GMP": "Guaranteed maximum price contract.",
    "IST": "Integrated systems test (Commissioning Level 5): all systems together under failure scenarios.",
    "ITP": "Inspection and test plan with hold and witness points.",
    "LOTO": "Lockout/tagout: isolating and locking energy sources before work.",
    "MOP / SOP / EOP": "Method of procedure / standard operating procedure / emergency operating procedure.",
    "MMR": "Meet-me room (entrance room) where carriers hand off fiber.",
    "N, N+1, 2N": "Base capacity; one spare unit per group; two complete independent paths. Three units where two "
                  "carry the load is N+1, not '2N+1'.",
    "NTP": "Notice to proceed with construction.",
    "PUE / WUE / CUE": "Power, water and carbon usage effectiveness (annual ratios).",
    "SC": "Substantial completion: the facility is usable for its purpose; follows a passed IST.",
    "TCS / FWS": "Technology cooling system (rack loop) / facility water system.",
    "Tier": "Tier I-IV topology classes of a proprietary rating system (III concurrently maintainable, IV fault tolerant). Availability "
            "percentages such as 99.982% are legacy figures, no longer in the standard: historical only.",
    "Water heat capacity": "Water carries about 3,500x more heat than the same volume of air, which is why "
                           "dense racks move heat as liquid.",
}

PLANNING_NOTES = {
    "Training vs inference (considerations, not rules)": [
        "Training clusters: very large, tightly coupled halls with coincident load (no diversity credit), the "
        "highest densities and long fabric runs; jobs checkpoint, so some owners choose leaner redundancy per hall.",
        "Inference: closer to users for latency, more variable load, often colocated; usually full concurrent "
        "maintainability or fault tolerance.",
        "Many campuses offer different redundancy in different halls. The availability target is a business "
        "decision; design and test against it.",
    ],
    "Bridging and on-site power (realistic availability)": [
        "Reciprocating gas engines: modular and fast to build, but 2026 orders are typically quoted for 2028-2029 delivery.",
        "Gas turbines: aeroderivatives about 40 months; heavy-duty frames largely sold out to about 2030.",
        "Fuel cells and battery storage: shorter supply chains; batteries add firming and ride-through, not long-duration energy.",
        "All options need air permits, fuel supply and interconnection studies; plan them in parallel with the utility.",
    ],
}


def tables(cx: dict) -> dict:
    """Plain lists of dicts for export."""
    return {
        "order_by": [{"Item": x["item"], "Send RFQ (months after start)": round(max(x["rfq"], 0.0), 1),
                      "Place PO (months after start)": round(max(x["po"], 0.0), 1),
                      "Needed on site (months after start)": round(x["need"], 1),
                      "Order ahead": f"Order it {x['order_ahead']:,.0f} months before you need it",
                      "Typical lead (wk)": x["lead_typ"], "Lead range (wk)": f"{x['lead_low']}-{x['lead_high']}",
                      "Flag": x["flag"], "Basis": x["basis"]}
                     for x in cx["schedule"]["items"]],
        "gantt": [{"Phase": p["phase"], "Track": p["track"], "Start (month)": round(p["start"], 1),
                   "Duration (months)": round(p["dur"], 1), "End (month)": round(p["end"], 1), "Note": p["note"]}
                  for p in cx["schedule"]["phases"]],
        "risks": [{"Category": r["category"], "Active": "Yes" if r["active"] else "No", "Why": r["why"],
                   "Trigger": r["trigger"], "Mitigation": r["mitigation"], "Owner": r["owner"], "Phase": r["phase"],
                   "Impact (months)": f"{r['impact_low']}-{r['impact_high']}"} for r in cx["risks"]],
        "cx_levels": [{"Level": c["level"], "Name": c["name"], "Proves": c["proves"], "Entry": c["entry"],
                       "Exit": c["exit"], "Witnesses": c["witness"]} for c in CX_LEVELS],
        "ist_scenarios": [{"Scenario": a, "Pass criteria": b} for a, b in IST_SCENARIOS],
        "handoff_feeds": [{"Feed": f["feed"], "Scope boundary": f["scope"], "Spec": f["spec"], "Test": f["test"],
                           "Common failure": f["failure"], "Prevention": f["prevention"]} for f in FEEDS],
        "it_readiness": [{"Step": n + 1, "Activity": s} for n, s in enumerate(IT_READINESS)],
        "checklists": [{"Checklist": k, "Item": it, "Done": ""} for k, v in CHECKLISTS.items() for it in v],
        "stage_gates": [{"Gate": g, "Name": n, "Criteria": c} for g, n, c in STAGE_GATES],
        "spec_reference": [{"Item": a, "Value": b, "Standard": c} for a, b, c in SPEC_REFERENCE],
    }


def plan(*, it_mw, racks, kw, cooling_d2c, liquid, onsite_hv, greenfield, i, platform_status="shipping",
         horizon_active=False, needs_new_service=True, gen_mw=3.0) -> dict:
    args = dict(it_mw=it_mw, greenfield=greenfield, design_months=i.get("design_months") if greenfield else None,
                build_months=i.get("construction_months") if greenfield else i.get("fitout_build_months"),
                months_to_power=i.get("months_to_power") if greenfield else None, onsite_hv=onsite_hv, d2c=cooling_d2c,
                needs_new_service=needs_new_service, overtime_hours=int(i.get("overtime_hours") or 40),
                weather=float(i.get("weather_factor") or 0), congestion=float(i.get("congestion_factor") or 0))
    sch = schedule(**args)
    # Range: shortest published lead times and no weather allowance, to the longest lead times plus 10% more
    # weather/productivity allowance on field work.
    lo = schedule(**{**args, "weather": 0.0, "lead_pick": "low"})["sc"]
    hi = schedule(**{**args, "weather": args["weather"] + 0.10, "lead_pick": "high"})["sc"]
    sch["sc_low"], sch["sc_high"] = min(lo, sch["sc"]), max(hi, sch["sc"])
    sch["range_text"] = range_text(sch["sc_low"], sch["sc_high"])
    lb = load_banks(it_mw=it_mw, liquid=liquid, d2c=cooling_d2c, gen_mw=gen_mw)
    risks = risk_register(greenfield=greenfield, kw=kw, d2c=cooling_d2c, it_mw=it_mw,
                          months_to_power=i.get("months_to_power") if greenfield else None, items=sch["items"],
                          platform_status=platform_status, horizon_active=horizon_active,
                          needs_new_service=needs_new_service)
    out = {"schedule": sch, "load_banks": lb, "risks": risks, "estimate_label": ESTIMATE_LABEL}
    out["tables"] = tables(out)
    return out


def range_text(lo: float, hi: float) -> str:
    a, b = math.floor(lo), math.ceil(hi)
    return f"about {a} months from start" if b <= a else f"about {a}–{b} months from start"
