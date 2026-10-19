"""
RackReady AI - design calculations (preliminary engineering sizing).

Every step returns the formula, the inputs and the result, so the UI and exports can show the working.
These are early-feasibility calculations. Final design must use vendor data, load-flow / fault /
protection studies, pump and fan curves, and the adopted codes (NEC, NFPA 110/855, IBC, ASHRAE).

Constants and conventions (public references in docs/VERIFICATION.md):
  * Three-phase power  P = sqrt(3) x V_LL x I x PF;  apparent power S = P / PF
  * Sensible heat      Q = m_dot x cp x dT  ->  volumetric flow V = Q / (rho x cp x dT)
  * 1 refrigeration ton = 12,000 Btu/h = 3.517 kW;  1 L/s = 15.85 US gpm;  1 m3/s = 2,118.9 CFM
  * Water cp 4.18 kJ/kg.K, rho 997 kg/m3; PG25 cp 3.93 kJ/kg.K, rho 1,017 kg/m3 (about 30-40 C)
  * Air rho 1.2 kg/m3, cp 1.006 kJ/kg.K; latent heat of evaporation about 2,430 kJ/kg (warm water)
  * Continuous loads: conductors and protective devices sized at 125% (NEC 215.2 / 230.42)
  * Diesel fuel about 0.070 gal per kWh at high load (2,000 kVA genset spec sheet: about 114 gal/h at
    1,600 ekW)
"""
from __future__ import annotations

import math

SQRT3 = math.sqrt(3)
KW_PER_TON = 3.517
GPM_PER_LPS = 15.850
CFM_PER_M3S = 2118.88
LB_TO_KN = 4.448222 / 1000
PSF_TO_KPA = 0.04788
SF_PER_M2 = 10.7639
SF_PER_ACRE = 43_560
L_PER_GAL = 3.78541
HOURS = 8760

AIR, HYBRID, D2C = "Air", "Hybrid (rear-door + air)", "Direct-to-chip (D2C) liquid"
COOLING_TYPES = [AIR, HYBRID, D2C]
D2C_AUTO_KW = 45.0
MAX_KW = {AIR: 30.0, HYBRID: 45.0, D2C: 1_000.0}

# Engineering assumptions (editable in Advanced where marked).  Each is stated, not hidden.
DEFAULTS = {
    "ups_eff": 0.97,            # double-conversion UPS at typical load (vendor curves 96-97.5%)
    "dist_loss": 0.015,         # transformer + cable losses, fraction of IT
    "house": 0.025,             # lighting, offices, controls, security, support spaces, fraction of IT
    "cool_avg": {AIR: 0.38, HYBRID: 0.28, D2C: 0.13},   # annual-average cooling kW per kW IT
    "cool_peak": {AIR: 0.55, HYBRID: 0.42, D2C: 0.22},  # design-day cooling kW per kW IT
    "crit_mech": {AIR: 0.02, HYBRID: 0.02, D2C: 0.03},  # cooling on UPS (CDU/TCS pumps, fans)
    "diversity": 1.0,           # AI training load is coincident: no diversity credit by default
    "reserve": 0.15,            # utility planning reserve on coincident demand
    "pf_service": 0.95,         # power factor for transformer / generator kVA
    "pf_rack": 0.99,            # rack power-shelf input power factor
    "voltage": 415.0,           # LV distribution, V line-to-line
    "racks_per_row": 10,        # racks per busway run (A and B busways each sized for the full row)
    "unit_sub_kva": 3_000,      # MV/LV unit substation transformer size
    "unit_sub_loading": 0.80,   # maximum planned loading
    "main_tx_mva": 80.0,        # HV/MV main transformer size when an on-site substation is needed
    "onsite_hv_above_mva": 40.0,
    "gen_mw": 3.0,              # standby generator rating (data-centre continuous)
    "gen_group": 8,             # N+1 = one spare per group of up to 8 running sets
    "ups_module_mw": 1.0,
    "ups_group": 4,             # N+1 = one spare per group of up to 4 modules
    "cdu_group": 6,             # N+1 = one spare CDU per group of up to 6
    "battery_min": 5.0,         # minutes at full UPS load (assumption; no universal value)
    "battery_dis_eff": 0.96,
    "battery_ageing": 0.80,
    "fuel_hours": 48.0,
    "fuel_gal_per_kwh": 0.070,
    "tcs_dT": 10.0, "tcs_cp": 3.93, "tcs_rho": 1017.0, "tcs_dp_kpa": 150.0, "pump_eff": 0.65,
    "fws_dT": 10.0, "w_cp": 4.18, "w_rho": 997.0,
    "chw_dT": 6.7, "cw_dT": 5.6, "cop": 6.0,
    "air_dT": 12.0, "air_rho": 1.2, "air_cp": 1.006,
    "h_fg": 2430.0, "coc": 5.0,
    "wue_dry": 0.20,            # L/kWh, dry/adiabatic coolers with spray on hot hours
    "aisle_m": 1.2,             # aisle depth attributed to each rack (half cold + half hot aisle)
    "stories": 1,
    "site_coverage": 0.35,      # building + yards as share of site (setbacks, roads, stormwater)
    "yard_sf_per_gen": 1_200, "yard_sf_per_mva": 300, "yard_sf_per_mw_reject": 300,
    "floor_rating_psf": 250,    # TIA-942 recommended computer-room floor loading (12 kPa)
    # MV distribution
    "mv_kv_onsite": 34.5,       # on-site substation secondary (35 kV class, 38 kV switchgear)
    "mv_kv_utility": 13.8,      # utility medium-voltage service (15 kV class)
    # fire protection (NFPA 13 / 20 / 22 / 2001); hazard class is set by the engineer, AHJ and insurer
    "spk_density": 0.15, "spk_density_oh2": 0.20, "spk_area_sf": 1500.0, "spk_dry_factor": 1.30,
    "hose_gpm": 250.0, "fire_minutes": 60.0, "head_sf": 130.0,
    "agent_C": 4.2, "agent_k1": 0.9856, "agent_k2": 0.002441, "agent_T_F": 70.0,
    "agent_room_sf": 4_500.0, "agent_room_ft": 12.0,   # entrance rooms + main distribution area (assumption)
    # thermal storage and towers
    "ride_through_min": 10.0, "tes_fom": 0.90, "drift_pct": 0.00002,
    # site water
    "c_pre": 0.30, "c_imp": 0.95, "impervious": 0.60, "storm_in_hr": 3.0,
    # network
    "front_end_share": 0.25, "fiber_trunk": 144, "entrance_sep_m": 20.0,
}

MV_BUS_A = [1200, 2000, 3000, 4000]
BRANCH_A = [100, 125, 150, 175, 200, 225, 250, 300, 350, 400, 450, 500, 600, 700, 800, 1000, 1200]   # NEC 240.6(A)
FIRE_PUMP_GPM = [250, 300, 400, 450, 500, 750, 1000, 1250, 1500, 2000, 2500, 3000]                  # NFPA 20 ratings
BTU_PER_KW = 3412.14
# Hunter's curve, flush-tank systems (IPC Appendix E, Table E103.3(3)): (WSFU, gpm)
HUNTER = [(1, 3.0), (2, 5.0), (3, 6.5), (4, 8.0), (5, 9.4), (6, 10.7), (8, 12.8), (10, 14.6), (12, 16.0), (14, 17.0),
          (16, 18.0), (18, 18.8), (20, 19.6), (25, 21.5), (30, 23.3), (35, 24.9), (40, 26.3), (45, 27.7), (50, 29.1),
          (60, 32.0), (70, 35.0), (80, 38.0), (90, 41.0), (100, 43.5), (120, 48.0), (140, 52.5), (160, 57.0),
          (180, 61.0), (200, 65.0), (225, 70.0), (250, 75.0), (300, 85.0), (400, 105.0), (500, 124.0)]


def hunter_gpm(wsfu: float) -> float:
    pts = HUNTER
    if wsfu <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if wsfu <= x1:
            return y0 + (y1 - y0) * (wsfu - x0) / (x1 - x0)
    return pts[-1][1] * wsfu / pts[-1][0]

BUSWAY_A = [800, 1000, 1200, 1600, 2000, 2500, 3000, 4000, 5000]
BREAKER_A = [800, 1200, 1600, 2000, 2500, 3000, 4000, 5000, 6000]


def effective_cooling(kw: float, chosen: str | None) -> tuple[str, bool]:
    """Above 45 kW/rack every design is D2C liquid (locked). At or below, the user's choice."""
    if kw > D2C_AUTO_KW:
        return D2C, True
    return (chosen if chosen in COOLING_TYPES else HYBRID), False


def spares(n_run: int, resilience: str, group: int) -> int:
    if resilience == "2N":
        return n_run
    if resilience == "N":
        return 0
    if resilience == "N+2":
        return 2 * math.ceil(n_run / group)
    return math.ceil(n_run / group)                       # N+1 per group


def pick(value: float, sizes: list[int]) -> int | None:
    for s in sizes:
        if s >= value:
            return s
    return None


class Calc:
    def __init__(self):
        self.steps: list[dict] = []
        self.v: dict = {}

    def add(self, key, section, item, formula, inputs, value, unit, si=None, note=""):
        self.v[key] = value
        self.steps.append({"key": key, "section": section, "item": item, "formula": formula,
                           "inputs": inputs, "value": value, "unit": unit, "si": si or "", "note": note})
        return value


def fmt(x, d=0):
    if x is None:
        return "-"
    return f"{x:,.{d}f}"


def design(*, racks: float, kw: float, kw_peak: float, cooling: str, liquid: float, weight_lb: float,
           rack_w_m: float, rack_d_m: float, white_sf: float, gsf_per_mw: float, cdu_mw: float,
           resilience: str = "N+1", utilization: float = 0.8, land_per_acre: float = 0.0,
           params: dict | None = None, gpus: int = 0) -> dict:
    p = dict(DEFAULTS)
    for k, val in (params or {}).items():
        if val is not None:
            p[k] = val
    c = Calc()
    is_d2c = cooling == D2C
    lf = liquid if is_d2c else (0.0)
    V = p["voltage"]

    # ---------------------------------------------------------------- 1. load
    S = "1. IT and facility load"
    it_kw = c.add("it_kw", S, "IT load", "P_IT = racks x kW/rack", f"{fmt(racks)} x {fmt(kw, 1)} kW",
                  racks * kw, "kW", f"{racks * kw / 1000:,.2f} MW")
    it_mw = it_kw / 1000
    ups_load = c.add("ups_load_kw", S, "Critical (UPS) load", "P_UPS = P_IT + cooling on UPS (CDU pumps, fans)",
                     f"{fmt(it_kw)} + {p['crit_mech'][cooling]:.0%} x {fmt(it_kw)}",
                     it_kw * (1 + p["crit_mech"][cooling]), "kW",
                     note="Cooling pumps need the same ride-through as the GPUs.")
    ups_in = it_kw * p["diversity"] / p["ups_eff"]
    cool_pk = it_kw * p["cool_peak"][cooling]
    dist = it_kw * p["dist_loss"]
    house = it_kw * p["house"]
    fac_pk = c.add("fac_peak_kw", S, "Facility peak demand (design day)",
                   "P_fac = P_IT x diversity / eta_UPS + losses + cooling(peak) + house",
                   f"{fmt(it_kw)} x {p['diversity']:.2f} / {p['ups_eff']:.3f} + {fmt(dist)} + {fmt(cool_pk)} + {fmt(house)}",
                   ups_in + dist + cool_pk + house, "kW",
                   note="Component load model; no fixed IT x 2 rule. Cooling power is design-day peak.")
    pue = c.add("pue", S, "Annual PUE (energy)", "PUE = 1/eta_UPS + losses + cooling(avg) + house",
                f"1/{p['ups_eff']:.3f} + {p['dist_loss']:.3f} + {p['cool_avg'][cooling]:.3f} + {p['house']:.3f}",
                1 / p["ups_eff"] + p["dist_loss"] + p["cool_avg"][cooling] + p["house"], "",
                note="PUE is an annual energy ratio (ISO/IEC 30134-2), not a peak multiplier.")
    it_mwh = c.add("it_mwh", S, "Annual IT energy", "E_IT = P_IT x utilization x 8,760 h",
                   f"{it_mw:,.2f} MW x {utilization:.0%} x 8,760", it_mw * utilization * HOURS, "MWh/yr")
    c.add("fac_mwh", S, "Annual facility energy", "E_fac = E_IT x PUE", f"{fmt(it_mwh)} x {pue:.3f}",
          it_mwh * pue, "MWh/yr")

    # ---------------------------------------------------------------- 2. utility & transformers
    S = "2. Utility service and transformers"
    svc_mw = c.add("service_mw", S, "Utility service capacity (planning)", "P_svc = P_fac x (1 + reserve)",
                   f"{fmt(fac_pk)} kW x (1 + {p['reserve']:.0%})", fac_pk * (1 + p["reserve"]) / 1000, "MW",
                   note="Planning reserve on coincident demand; confirm firm MW and date with the utility.")
    svc_mva = c.add("service_mva", S, "Utility service apparent power", "S = P / PF",
                    f"{svc_mw:,.1f} MW / {p['pf_service']:.2f}", svc_mw / p["pf_service"], "MVA")
    onsite = svc_mva > p["onsite_hv_above_mva"]
    if onsite:
        n = math.ceil(svc_mva / p["main_tx_mva"] - 1e-9)
        sp = n if resilience == "2N" else (0 if resilience == "N" else 1)
        c.add("main_tx", S, "On-site HV/MV main transformers", f"N = ceil(S / {p['main_tx_mva']:.0f} MVA) + redundancy",
              f"ceil({svc_mva:,.1f} / {p['main_tx_mva']:.0f}) = {n}; +{sp} ({resilience})", n + sp, "units",
              f"{p['main_tx_mva']:.0f} MVA each",
              note=("Typical 60-100 MVA units; lead time about 2.5 years. Units needed + one spare is N+1 "
                    "(not '2N+1'); 2N = two full sets." if resilience != "2N" else
                    "2N: two complete sets, each able to carry the full load; lead time about 2.5 years."))
    else:
        c.add("main_tx", S, "On-site HV substation", "Needed when S > 40 MVA (planning rule)",
              f"{svc_mva:,.1f} MVA", 0, "units", note="Medium-voltage utility service; no on-site HV yard.")
    v_mv = p["mv_kv_onsite"] if onsite else p["mv_kv_utility"]
    i_svc = svc_mva * 1e6 / (SQRT3 * v_mv * 1000)
    c.add("mv_amps", S, "MV current, whole service", "I = S / (sqrt3 x V_MV)",
          f"{svc_mva:,.1f} MVA / (1.732 x {v_mv:.1f} kV)", i_svc, "A",
          note=f"{'On-site substation secondary' if onsite else 'Utility MV service'} at {v_mv:.1f} kV.")
    i_feed = (p["main_tx_mva"] * 1e6 / (SQRT3 * v_mv * 1000)) if onsite else i_svc
    bus = pick(1.25 * i_feed, MV_BUS_A)
    n_line = math.ceil(1.25 * i_feed / MV_BUS_A[-1] - 1e-9) if not bus else 1
    c.add("mv_bus_a", S, "MV switchgear main bus rating (per lineup)",
          "I_feed = S_source / (sqrt3 x V); bus >= 1.25 x I_feed",
          f"{(p['main_tx_mva'] if onsite else svc_mva):,.1f} MVA / (1.732 x {v_mv:.1f} kV) = {i_feed:,.0f} A x 1.25",
          bus or MV_BUS_A[-1], "A",
          f"{'38' if onsite else '15'} kV class; {'one lineup per main transformer, A/B with tie' if onsite else f'{n_line} main(s), main-tie-main'}",
          note="Interrupting rating (commonly 25-40 kA) comes from the fault study; arc-resistant Type 2B "
               "(IEEE C37.20.7) where specified." + ("" if bus else " Feed exceeds 4,000 A: split into more lineups."))
    unit_cap_kva = p["unit_sub_kva"] * p["unit_sub_loading"]
    n_it = math.ceil((ups_in + dist) / p["pf_service"] / unit_cap_kva - 1e-9)
    sp_it = spares(n_it, resilience, 4)
    c.add("unit_subs_it", S, "MV/LV transformers, IT path", "N = ceil(UPS input kVA / (kVA x loading)) + spares",
          f"ceil({fmt((ups_in + dist) / p['pf_service'])} / ({p['unit_sub_kva']:,} x {p['unit_sub_loading']:.0%})) = {n_it}; +{sp_it}",
          n_it + sp_it, "units", f"{p['unit_sub_kva']:,} kVA each",
          note="N+1 = one reserve unit per 4 (block/catcher redundant); 2N = A and B.")
    n_m = math.ceil((cool_pk + house) / p["pf_service"] / unit_cap_kva - 1e-9)
    sp_m = spares(n_m, resilience, 4)
    c.add("unit_subs_mech", S, "MV/LV transformers, mechanical + house", "N = ceil(kVA / (kVA x loading)) + spares",
          f"ceil({fmt((cool_pk + house) / p['pf_service'])} / {fmt(unit_cap_kva)}) = {n_m}; +{sp_m}", n_m + sp_m,
          "units", f"{p['unit_sub_kva']:,} kVA each")
    i_main = p["unit_sub_kva"] * 1000 / (SQRT3 * V)
    c.add("swbd_amps", S, "LV switchboard main current (per transformer)", "I = S / (sqrt3 x V)",
          f"{p['unit_sub_kva']:,} kVA / (1.732 x {V:.0f} V)", i_main, "A",
          f"main breaker {pick(i_main, BREAKER_A) or '>6000'} A frame",
          note="Transformer secondary full-load current; main device per NEC 450.3.")

    # ---------------------------------------------------------------- 3. backup power
    S = "3. Generators, UPS and batteries"
    g_run = math.ceil(fac_pk / 1000 / p["gen_mw"] - 1e-9)
    g_sp = spares(g_run, resilience, p["gen_group"])
    gens = c.add("gens", S, "Standby generators", f"N = ceil(P_fac / {p['gen_mw']:.1f} MW) + spares",
                 f"ceil({fac_pk / 1000:,.1f} / {p['gen_mw']:.1f}) = {g_run}; +{g_sp} ({resilience})", g_run + g_sp,
                 "units", f"{p['gen_mw']:.1f} MW each",
                 note=f"Sized on kW: genset kW ratings already assume 0.8 PF, so dividing by 0.8 first would "
                      f"double-count it. N+1 = one spare per group of up to {p['gen_group']} running sets; "
                      "2N = full duplicate plant.")
    c.v["gens_run"] = g_run
    c.add("gen_kva", S, "Generator kVA rating (each)", "S = P / PF", f"{p['gen_mw'] * 1000:,.0f} kW / 0.80",
          p["gen_mw"] * 1000 / 0.8, "kVA", note="Gensets are rated at 0.8 PF.")
    fuel = c.add("fuel_gal", S, "Fuel storage", "Fuel = P_fac x gal/kWh x hours",
                 f"{fmt(fac_pk)} kW x {p['fuel_gal_per_kwh']:.3f} x {p['fuel_hours']:.0f} h",
                 fac_pk * p["fuel_gal_per_kwh"] * p["fuel_hours"], "gal",
                 f"{fac_pk * p['fuel_gal_per_kwh'] * p['fuel_hours'] * L_PER_GAL / 1000:,.0f} m3",
                 note=f"Usable fuel at design load (burn {fac_pk * p['fuel_gal_per_kwh']:,.0f} gal/h, so each "
                      f"100,000 gal lasts about {100_000 / max(fac_pk * p['fuel_gal_per_kwh'], 1e-9):,.0f} h). Add "
                      "unusable volume and any code or insurer reserve; Tier topology needs at least 12 h.")
    u_run = math.ceil(ups_load / 1000 / p["ups_module_mw"] - 1e-9)
    u_sp = spares(u_run, resilience, p["ups_group"])
    c.add("ups_modules", S, "UPS modules", f"N = ceil(P_UPS / {p['ups_module_mw']:.1f} MW) + spares",
          f"ceil({ups_load / 1000:,.1f} / {p['ups_module_mw']:.1f}) = {u_run}; +{u_sp} ({resilience})",
          u_run + u_sp, "units", f"{p['ups_module_mw'] * 1000:,.0f} kW each",
          note=f"N+1 = one spare per group of up to {p['ups_group']} modules.")
    c.v["ups_run"] = u_run
    c.add("battery_kwh", S, "Battery energy (nameplate)", "E = P_UPS x t / eta_discharge / ageing",
          f"{fmt(ups_load)} kW x {p['battery_min']:.0f}/60 h / {p['battery_dis_eff']:.2f} / {p['battery_ageing']:.2f}",
          ups_load * p["battery_min"] / 60 / p["battery_dis_eff"] / p["battery_ageing"], "kWh",
          note="Minutes are an owner choice. Size from the maker's constant-power data at end of life.")

    # ---------------------------------------------------------------- 4. distribution
    S = "4. Power distribution to the rack"
    i_rack = c.add("rack_amps", S, "Current per rack feed (each of A and B)", "I = P / (sqrt3 x V x PF)",
                   f"{kw_peak * 1000:,.0f} W / (1.732 x {V:.0f} V x {p['pf_rack']:.2f})",
                   kw_peak * 1000 / (SQRT3 * V * p["pf_rack"]), "A",
                   note="Each feed must carry the whole rack if the other fails. Uses peak electrical design power.")
    n_row = int(p["racks_per_row"])
    n_run = max(1, min(n_row, int(BUSWAY_A[-1] / (1.25 * i_rack)))) if i_rack else n_row
    runs = math.ceil(n_row / n_run)
    i_bw = kw_peak * n_run * 1000 / (SQRT3 * V * p["pf_rack"])
    bw = pick(i_bw * 1.25, BUSWAY_A)
    c.add("busway_runs", S, "Busway runs per row of 10 racks (A and B each)",
          "racks per run = floor(5,000 A / (1.25 x I_rack))",
          f"floor(5,000 / (1.25 x {i_rack:,.0f} A)) = {n_run} racks per run", runs, "units",
          note="Largest standard busway is 5,000 A; denser racks need more runs per row." if runs > 1 else
               "One busway run per row.")
    c.add("busway_amps", S, "Busway current per run", "I = n x P_rack / (sqrt3 x V x PF); rating >= 1.25 x I",
          f"{n_run} x {kw_peak:,.0f} kW at {V:.0f} V -> {i_bw:,.0f} A x 1.25 = {i_bw * 1.25:,.0f} A",
          i_bw, "A", f"select {bw} A busway" if bw else "exceeds 5,000 A",
          note="Rated per NEC continuous-load rule (125%)." + ("" if bw else " Use dedicated feeders or 800 VDC."))
    c.add("busway_rating", S, "Selected busway rating", "smallest standard size >= 1.25 x I",
          f"{i_bw * 1.25:,.0f} A", bw or 0, "A",
          note="Dedicated feeder per rack required." if not bw else "")
    side_kva = kw_peak / p["pf_rack"]
    brk = pick(1.25 * i_rack, BRANCH_A)
    c.add("ab_side_kva", S, "A/B check: capacity needed on EACH side", "S_side >= P_rack / PF (one side carries it all)",
          f"{kw_peak:,.0f} kW / {p['pf_rack']:.2f}", side_kva, "kVA",
          f"each side breaker >= 1.25 x {i_rack:,.0f} A -> {brk or '>1,200'} A",
          note="PASS only if each feed alone carries the whole rack. Failing example: two 45 kVA feeds for a "
               "50 kW rack (45 kVA < 50.5 kVA).")
    c.add("busway_loading", S, "Busway continuous loading", "loading = I_run / rating (must be <= 80%)",
          f"{i_bw:,.0f} A / {bw or 0:,} A", (i_bw / bw * 100) if bw else 100.0, "%",
          note=("PASS: within the 80% continuous-load limit (NEC 210.19 / 215.2)." if bw and i_bw / bw <= 0.8 + 1e-9
                else "FAIL: above 80% of rating; add runs or use a larger rating."))
    c.add("busbar54_amps", S, "In-rack 54 VDC busbar current", "I = P_rack / 54 V",
          f"{kw_peak * 1000:,.0f} W / 54 V", kw_peak * 1000 / 54, "A",
          note="Why MW-class racks move to 800 VDC: at 54 V the copper becomes impractical.")
    c.add("dc800_amps", S, "Same row at 800 VDC (for comparison)", "I = P / V_dc",
          f"{n_row} x {kw_peak * 1000:,.0f} W / 800 V", kw_peak * n_row * 1000 / 800, "A",
          note="Two conductors instead of 3 phases + neutral; NVIDIA cites >150% more power through the "
               "same copper. Emerging (NVIDIA/OCP 2025-26), not yet a listed standard: reserve space, "
               "don't buy speculatively.")
    c.add("taps", S, "Busway tap-off units", "taps = racks x 2 (A + B)", f"{fmt(racks)} x 2", racks * 2, "units")

    # ---------------------------------------------------------------- 5. cooling
    S = "5. Cooling"
    q_total = c.add("cool_kw", S, "Heat to remove (IT + indoor losses)", "Q = P_IT x (1 + UPS loss + house)",
                    f"{fmt(it_kw)} x (1 + {1 / p['ups_eff'] - 1:.3f} + {p['house']:.3f})",
                    it_kw * (1 / p["ups_eff"] + p["house"]), "kW",
                    f"{it_kw * (1 / p['ups_eff'] + p['house']) / KW_PER_TON:,.0f} tons",
                    note="Virtually all electrical power ends as heat.")
    c.add("cool_tons", S, "Cooling load in tons", "tons = Q / 3.517", f"{fmt(q_total)} / 3.517",
          q_total / KW_PER_TON, "tons", note="1 ton = 12,000 Btu/h = 3.517 kW.")
    q_liq = c.add("liquid_kw", S, "Heat to liquid (D2C capture)", "Q_liq = P_IT x liquid fraction",
                  f"{fmt(it_kw)} x {lf:.0%}", it_kw * lf, "kW",
                  note="Vendor capture fraction; never assume 100%." if is_d2c else "Not a D2C design.")
    q_air = c.add("air_kw", S, "Heat to air (residual + room gains)", "Q_air = Q - Q_liq",
                  f"{fmt(q_total)} - {fmt(q_liq)}", q_total - q_liq, "kW", f"{(q_total - q_liq) / KW_PER_TON:,.0f} tons",
                  note="Size the air system only for this, not the full IT load.")
    rack_air_kw = kw * (1 - lf)
    rack_cfm = rack_air_kw / (p["air_rho"] * p["air_cp"] * p["air_dT"]) * CFM_PER_M3S
    c.add("rack_air_cfm", S, "Air per rack (rack heat not on liquid)", "V = P_rack x (1 - liquid) / (rho x cp x dT)",
          f"{rack_air_kw:,.1f} kW / (1.2 x 1.006 x {p['air_dT']:.0f} K)", rack_cfm, "CFM",
          f"{rack_cfm / CFM_PER_M3S:,.2f} m3/s",
          note="If the liquid loop fails, the air system cannot carry the full rack." if is_d2c else "")
    cfm = q_air / (p["air_rho"] * p["air_cp"] * p["air_dT"]) * CFM_PER_M3S
    c.add("air_cfm", S, "Total airflow for the air load", "V = Q_air / (rho x cp x dT)",
          f"{fmt(q_air)} / (1.2 x 1.006 x {p['air_dT']:.0f} K)", cfm, "CFM", f"{cfm / CFM_PER_M3S:,.1f} m3/s",
          note="White-space residual air plus UPS-room and support-space gains.")
    if is_d2c:
        n_c = math.ceil(q_liq / 1000 / cdu_mw - 1e-9)
        sp_c = spares(n_c, resilience, p["cdu_group"])
        c.add("cdus", S, "Coolant distribution units (CDUs)", f"N = ceil(Q_liq / {cdu_mw:.1f} MW) + spares",
              f"ceil({q_liq / 1000:,.1f} / {cdu_mw:.1f}) = {n_c}; +{sp_c} ({resilience})", n_c + sp_c, "units",
              f"{cdu_mw:.1f} MW each", note=f"N+1 = one spare per group of up to {p['cdu_group']} (per hall/zone).")
        tcs = q_liq / (p["tcs_rho"] * p["tcs_cp"] * p["tcs_dT"])         # m3/s
        c.add("tcs_lps", S, "TCS coolant flow (rack loop, PG25)", "V = Q_liq / (rho x cp x dT)",
              f"{fmt(q_liq)} / ({p['tcs_rho']:.0f} x {p['tcs_cp']:.2f} x {p['tcs_dT']:.0f} K)", tcs * 1000, "L/s",
              f"{tcs * 1000 * GPM_PER_LPS:,.0f} gpm; {tcs * 1000 / racks * 60 if racks else 0:,.0f} L/min per rack",
              note=f"About {tcs * 1000 * 60 / q_liq if q_liq else 0:.2f} L/min per kW.")
        fws = q_liq / (p["w_rho"] * p["w_cp"] * p["fws_dT"])
        c.add("fws_lps", S, "Facility water flow (to dry coolers)", "V = Q_liq / (rho x cp x dT)",
              f"{fmt(q_liq)} / ({p['w_rho']:.0f} x {p['w_cp']:.2f} x {p['fws_dT']:.0f} K)", fws * 1000, "L/s",
              f"{fws * 1000 * GPM_PER_LPS:,.0f} gpm", note="Warm-water loop (W32-W45 class) for dry/adiabatic coolers.")
        pump = c.add("tcs_pump_kw", S, "TCS pump power", "P = dP x V / eta",
                     f"{p['tcs_dp_kpa']:.0f} kPa x {tcs:,.3f} m3/s / {p['pump_eff']:.2f}",
                     p["tcs_dp_kpa"] * 1000 * tcs / p["pump_eff"] / 1000, "kW")
    else:
        c.add("cdus", S, "Coolant distribution units (CDUs)", "Not used without D2C", "-", 0, "units")
        c.v["tcs_lps"] = c.v["fws_lps"] = c.v["tcs_pump_kw"] = 0.0
    q_chw = q_air
    chw = q_chw / (p["w_rho"] * p["w_cp"] * p["chw_dT"])
    c.add("chw_lps", S, "Chilled-water flow (air side)", "V = Q_air / (rho x cp x dT)",
          f"{fmt(q_chw)} / ({p['w_rho']:.0f} x {p['w_cp']:.2f} x {p['chw_dT']:.1f} K)", chw * 1000, "L/s",
          f"{chw * 1000 * GPM_PER_LPS:,.0f} gpm", note="12 F (6.7 K) chilled-water rise.")
    w_comp = q_chw / p["cop"]
    q_rej = c.add("reject_kw", S, "Heat rejection (design day)", "Q_reject = Q + W_compressor;  W = Q_chillers / COP",
                  f"{fmt(q_total)} + {fmt(q_chw)} / {p['cop']:.1f}", q_total + w_comp, "kW",
                  f"{(q_total + w_comp) / KW_PER_TON:,.0f} tons",
                  note=("Liquid heat to dry/adiabatic coolers; air-side heat via chillers." if is_d2c else
                        "Water-cooled chillers and cooling towers."))
    dT_air_F = p["air_dT"] * 1.8
    c.add("air_cfm_us", S, "Airflow check in US units", "CFM = BTU/h / (1.08 x dT_F)",
          f"{q_air * BTU_PER_KW:,.0f} BTU/h / (1.08 x {dT_air_F:.1f} F)", q_air * BTU_PER_KW / (1.08 * dT_air_F),
          "CFM", note="Standard-air constant 1.08 = 60 min x 0.075 lb/ft3 x 0.24 BTU/lb.F; agrees with the SI line.")
    dT_chw_F = p["chw_dT"] * 1.8
    c.add("chw_gpm_us", S, "Chilled-water check in US units", "GPM = tons x 24 / dT_F  (= BTU/h / (500 x dT_F))",
          f"{q_chw / KW_PER_TON:,.0f} tons x 24 / {dT_chw_F:.1f} F", q_chw / KW_PER_TON * 24 / dT_chw_F, "gpm",
          note="500 = 8.33 lb/gal x 60 min x 1 BTU/lb.F.")
    tes = q_chw * p["ride_through_min"] * 60 / (p["w_rho"] * p["w_cp"] * p["chw_dT"] * p["tes_fom"])   # m3
    c.add("tes_m3", S, "Thermal storage for chiller restart", "V = Q_chw x t / (rho x cp x dT x FOM)",
          f"{fmt(q_chw)} kW x {p['ride_through_min']:.0f} min / (997 x 4.18 x {p['chw_dT']:.1f} K x {p['tes_fom']:.2f})",
          tes, "m3", f"{tes * 1000 / L_PER_GAL:,.0f} gal",
          note="Covers chilled-water load while chillers restart on generator power (assumption: 10 min to full "
               "capacity). Warm-water dry-cooler loops ride through on UPS-backed pumps and fans instead.")
    if not is_d2c:
        cw = (q_chw + w_comp) / (p["w_rho"] * p["w_cp"] * p["cw_dT"])
        c.add("cw_lps", S, "Condenser-water flow (towers)", "V = Q_reject / (rho x cp x dT)",
              f"{fmt(q_chw + w_comp)} / ({p['w_rho']:.0f} x {p['w_cp']:.2f} x {p['cw_dT']:.1f} K)", cw * 1000, "L/s",
              f"{cw * 1000 * GPM_PER_LPS:,.0f} gpm", note="10 F (5.6 K) condenser-water rise.")
    else:
        c.v["cw_lps"] = 0.0

    # ---------------------------------------------------------------- 6. water
    S = "6. Water use"
    if is_d2c:
        wue = c.add("wue", S, "Water use effectiveness (WUE)", "assumed for dry/adiabatic coolers",
                    "spray only on hot hours", p["wue_dry"], "L/kWh",
                    note="Closed liquid loops circulate; they do not consume water.")
        c.v["evap_m3h"] = 0.0
    else:
        evap = q_rej / p["h_fg"]                      # kg/s
        c.add("evap_m3h", S, "Tower evaporation (design day)", "E = Q_reject / h_fg",
              f"{fmt(q_rej)} kW / {p['h_fg']:.0f} kJ/kg", evap * 3.6, "m3/h", f"{evap:,.1f} kg/s")
        wue = c.add("wue", S, "Water use effectiveness (WUE)",
                    "WUE = (3,600/h_fg) x (1 + 1/(CoC-1)) x Q_reject/P_IT",
                    f"(3,600/{p['h_fg']:.0f}) x (1 + 1/{p['coc'] - 1:.0f}) x {q_rej / it_kw:.3f}",
                    3600 / p["h_fg"] * (1 + 1 / (p["coc"] - 1)) * q_rej / it_kw, "L/kWh",
                    note=f"Evaporation plus blowdown at {p['coc']:.0f} cycles of concentration; full-tower basis.")
    ev_kgs = q_rej / p["h_fg"]
    ev_gpm = ev_kgs / p["w_rho"] * 1000 / L_PER_GAL * 60
    rej_tons = q_rej / KW_PER_TON
    mk_gpm = ev_gpm * p["coc"] / (p["coc"] - 1)
    c.add("tower_evap_gpm", S, "Cooling-tower evaporation (design day)" + (" if towers were used" if is_d2c else ""),
          "E = Q_reject / h_fg", f"{fmt(q_rej)} kW / {p['h_fg']:.0f} kJ/kg = {ev_kgs:,.1f} kg/s", ev_gpm, "gpm",
          f"{ev_gpm / max(rej_tons / 100, 1e-9):,.2f} gpm per 100 tons rejected",
          note="Physics gives about 2.3-2.4 gpm per 100 tons of heat rejected (about 3 per 100 evaporator tons "
               "with compressor heat). Values near 1.5 understate it.")
    c.add("tower_makeup_gpm", S, "Cooling-tower make-up (evaporation + blowdown + drift)",
          "M = E x CoC / (CoC - 1); blowdown incl. drift = E / (CoC - 1)",
          f"{ev_gpm:,.0f} gpm x {p['coc']:.0f} / {p['coc'] - 1:.0f}", mk_gpm, "gpm",
          f"{mk_gpm / max(rej_tons / 100, 1e-9):,.2f} gpm per 100 tons; drift about 0.0005-0.002% of circulation",
          note=("Dry/adiabatic coolers (this design) avoid most of this; closed loops do not consume water." if is_d2c
                else f"At {p['coc']:.0f} cycles of concentration. A Legionella water management program (ASHRAE 188) is required."))
    water_m3 = c.add("water_m3", S, "Annual site water", "W = WUE x E_IT", f"{wue:.2f} L/kWh x {fmt(it_mwh)} MWh",
                     wue * it_mwh, "m3/yr", f"{wue * it_mwh * 1000 / L_PER_GAL / 1e6:,.1f} million gal/yr")

    # ---------------------------------------------------------------- 7. space, structure, land
    S = "7. Space, floor loading and land"
    bay = rack_w_m * (rack_d_m + p["aisle_m"])
    c.add("bay_m2", S, "Rack bay (rack + aisle share)", "A_bay = W x (D + aisle)",
          f"{rack_w_m:.2f} m x ({rack_d_m:.2f} + {p['aisle_m']:.1f}) m", bay, "m2", f"{bay * SF_PER_M2:,.1f} sf",
          note=f"Planning white space per rack {white_sf:.0f} sf includes CDUs, row ends and circulation "
               f"({white_sf / (bay * SF_PER_M2):.1f}x the bay).")
    white = c.add("white_sf", S, "White space (data hall)", "A_white = racks x area per rack",
                  f"{fmt(racks)} x {white_sf:.0f} sf", racks * white_sf, "sf", f"{racks * white_sf / SF_PER_M2:,.0f} m2")
    gross = max(it_mw * gsf_per_mw, white * 1.6)
    c.add("gross_sf", S, "Gross building area", "A_gross = IT MW x gross sf per MW (min 1.6 x white)",
          f"{it_mw:,.2f} MW x {gsf_per_mw:,.0f} sf/MW", gross, "sf", f"{gross / SF_PER_M2:,.0f} m2",
          note="Includes electrical rooms, CDU/pipe galleries, mechanical, docks, offices.")
    c.add("support_sf", S, "Support (gray) space", "A_support = A_gross - A_white", f"{fmt(gross)} - {fmt(white)}",
          gross - white, "sf")
    fp_sf = rack_w_m * rack_d_m * SF_PER_M2
    psf = weight_lb / fp_sf
    c.add("rack_psf", S, "Rack footprint pressure", "q = W / A_footprint",
          f"{weight_lb:,.0f} lb / {fp_sf:,.1f} sf", psf, "psf", f"{psf * PSF_TO_KPA:,.1f} kPa",
          note=("Above the 250 psf (12 kPa) floor rating TIA-942 recommends: use a slab-on-grade or a "
                "heavy structural slab; raised floor only with rated panels." if psf > p["floor_rating_psf"]
                else "Within a 250 psf (12 kPa) rated floor."))
    c.add("caster_kn", S, "Load per caster (4 equal)", "R = W / 4", f"{weight_lb:,.0f} lb / 4",
          weight_lb / 4 * LB_TO_KN, "kN", f"{weight_lb / 4:,.0f} lb", note="Real reactions are unequal; check the wheel.")
    c.add("bay_psf", S, "Average over the rack position", "q = W / white sf per rack",
          f"{weight_lb:,.0f} lb / {white_sf:.0f} sf", weight_lb / white_sf, "psf")
    yard = gens * p["yard_sf_per_gen"] + (svc_mva * p["yard_sf_per_mva"] if onsite else 0) \
        + (q_rej / 1000) * p["yard_sf_per_mw_reject"]
    footprint = gross / p["stories"]
    site_sf = (footprint + yard) / p["site_coverage"]
    acres = c.add("land_acres", S, "Land area", "A_site = (building footprint + yards) / coverage",
                  f"({fmt(footprint)} + {fmt(yard)}) sf / {p['site_coverage']:.0%}", site_sf / SF_PER_ACRE, "acres",
                  f"{site_sf / SF_PER_M2 / 10_000:,.1f} ha",
                  note="Yards: generators, HV substation, heat rejection. Coverage covers setbacks, roads, stormwater.")
    c.add("land_cost", S, "Land cost", "C = acres x $/acre", f"{acres:,.1f} x ${land_per_acre:,.0f}",
          acres * land_per_acre, "$")
    # ---------------------------------------------------------------- 8. fire protection
    S = "8. Fire protection"
    area = p["spk_area_sf"] * p["spk_dry_factor"]
    c.add("spk_area_sf", S, "Sprinkler design area (double-interlock pre-action)", "A = 1,500 sf x 1.30",
          f"{p['spk_area_sf']:,.0f} sf x {p['spk_dry_factor']:.2f}", area, "sf",
          note="NFPA 13 (2022/2025): dry and double-interlock pre-action systems add 30% to the design area.")
    q_spk = c.add("spk_gpm", S, "Sprinkler demand", "Q = density x area",
                  f"{p['spk_density']:.2f} gpm/sf (OH-1) x {area:,.0f} sf", p["spk_density"] * area, "gpm",
                  note=f"OH-2 at {p['spk_density_oh2']:.2f} gpm/sf gives {p['spk_density_oh2'] * area:,.0f} gpm. The "
                       "hazard class is set by the engineer, AHJ and insurer: show it as a range.")
    q_tot = c.add("fire_total_gpm", S, "Total fire water demand", "Q_total = Q_sprinkler + hose allowance",
                  f"{q_spk:,.1f} + {p['hose_gpm']:.0f} gpm", q_spk + p["hose_gpm"], "gpm",
                  note="Hose allowance 250 gpm (inside + outside) for ordinary hazard; hydraulic calc adds friction "
                       "and elevation.")
    fp = pick(q_tot, FIRE_PUMP_GPM)
    c.add("fire_pump_gpm", S, "Fire pump rating", "smallest NFPA 20 rating >= demand", f"{q_tot:,.1f} gpm", fp or 0,
          "gpm", note="Must deliver >= 65% of rated pressure at 150% of rated flow (NFPA 20). Electric plus diesel "
                      "where the water-supply reliability requires; confirm whether hose demand comes from the city main.")
    c.add("fire_tank_gal", S, "Fire water storage", "V = Q_total x duration",
          f"{q_tot:,.1f} gpm x {p['fire_minutes']:.0f} min", q_tot * p["fire_minutes"], "gal",
          f"{q_tot * p['fire_minutes'] * L_PER_GAL / 1000:,.0f} m3; 90 min: {q_tot * 90:,.0f} gal",
          note="60 min where waterflow and supervisory alarms are monitored at a constantly attended location, "
               "otherwise 90 min (NFPA 13); tank per NFPA 22.")
    c.add("spk_heads", S, "Sprinkler heads in the data halls", "n = white space / 130 sf per head",
          f"{fmt(white)} sf / {p['head_sf']:.0f} sf", math.ceil(white / p["head_sf"]), "units",
          note="Maximum coverage per standard-spray head in ordinary hazard; coordinate with containment.")
    vol = p["agent_room_sf"] * p["agent_room_ft"]
    sv = p["agent_k1"] + p["agent_k2"] * p["agent_T_F"]
    C = p["agent_C"]
    c.add("agent_lb", S, "Clean agent FK-5-1-12 (entrance rooms + MDA)", "W = (V / S) x C / (100 - C);  S = 0.9856 + 0.002441 T",
          f"({vol:,.0f} ft3 / {sv:.4f} ft3/lb) x {C:.1f} / {100 - C:.1f}", vol / sv * C / (100 - C), "lb",
          note=f"NFPA 2001 total-flooding formula at {p['agent_T_F']:.0f} F; {C:.1f}% is a typical listed Class C design "
               "concentration (use the listed system manual). Hold for 10 min; door-fan test. One major producer stopped "
               "making FK-5-1-12 at the end of 2025: confirm supply or consider an inert-gas system.")

    # ---------------------------------------------------------------- 9. site water and stormwater
    S = "9. Domestic water and stormwater"
    occ = 8 + 0.5 * it_mw
    wc = math.ceil(min(occ, 50) / 25) + max(0, math.ceil((occ - 50) / 50))
    lav = math.ceil(min(occ, 80) / 40) + max(0, math.ceil((occ - 80) / 80))
    df = math.ceil(occ / 100)
    wsfu = wc * 5 + lav * 2 + df * 0.25 + 3 + 2 * 4          # + service sink + 2 showers
    c.add("fixtures", S, "Plumbing fixtures (business occupancy)", "IPC Table 2902.1: WC 1/25 (first 50) then 1/50; lav 1/40 then 1/80",
          f"{occ:,.0f} occupants -> {wc} WC, {lav} lav, {df} drinking fountain, 1 service sink, 2 showers",
          wc + lav + df + 3, "units", note="Occupants = operations staff estimate (8 + 0.5 per MW); confirm with the AHJ.")
    c.add("domestic_gpm", S, "Domestic water peak demand", "WSFU (IPC Table E103.3(2)) -> gpm (Hunter's curve, E103.3(3))",
          f"{wsfu:,.1f} WSFU (WC 5, lav 2, shower 4, sink 3, fountain 0.25)", hunter_gpm(wsfu), "gpm",
          note="Domestic only; process make-up for cooling is separate (see 6).")
    area_ac = acres
    c_post = p["c_imp"] * p["impervious"] + p["c_pre"] * (1 - p["impervious"])
    q_pre = p["c_pre"] * p["storm_in_hr"] * area_ac
    q_post = c_post * p["storm_in_hr"] * area_ac
    c.add("storm_q_cfs", S, "Stormwater peak runoff after development", "Q = C x i x A (rational method)",
          f"{c_post:.2f} x {p['storm_in_hr']:.1f} in/h x {area_ac:,.1f} ac (before: C = {p['c_pre']:.2f})", q_post, "cfs",
          f"before development {q_pre:,.0f} cfs",
          note=f"C = {p['c_imp']:.2f} on {p['impervious']:.0%} impervious, {p['c_pre']:.2f} elsewhere; i = design-storm "
               "intensity (assumption; use local IDF data, e.g. NOAA Atlas 14).")
    vdet = (q_post - q_pre) * 3600
    c.add("detention_acft", S, "Detention volume (first-pass)", "V = (Q_post - Q_pre) x storm duration (1 h)",
          f"({q_post:,.0f} - {q_pre:,.0f}) cfs x 3,600 s = {vdet:,.0f} ft3", vdet / SF_PER_ACRE, "acre-ft",
          f"{vdet * 0.0283168:,.0f} m3",
          note="First-pass sizing by the modified rational method; the local ordinance sets the storms (often 2/10/100-year) "
               "and method (e.g. NRCS TR-55).")

    # ---------------------------------------------------------------- 10. network
    S = "10. Network fiber and diversity"
    fpg = 16 if kw >= 100 else 8
    n_g = int(gpus or 0)
    f_rack = n_g * fpg * (1 + p["front_end_share"])
    c.add("fiber_per_rack", S, "Fibers per rack", "n = GPUs x fibers per GPU port x (1 + front-end/storage/mgmt)",
          f"{n_g} x {fpg} x (1 + {p['front_end_share']:.0%})", f_rack, "fibers",
          note=f"{'800G (16 fibers, 2 x 400G-DR4 or DR8)' if fpg == 16 else '400G (8 fibers, DR4/SR4)'} per GPU on the "
               "compute fabric (planning assumption); confirm with the network design.")
    n_r = math.ceil(racks - 1e-9)
    c.add("fiber_backbone", S, "Backbone fibers (leaf to spine, non-blocking)", "n = racks x GPUs x fibers per port",
          f"{n_r:,} x {n_g} x {fpg}", n_r * n_g * fpg, "fibers",
          f"about {math.ceil(n_r * n_g * fpg / p['fiber_trunk']):,} x {p['fiber_trunk']}-fiber trunks",
          note="Plan pathways at about 2x day-one fill for growth.")
    c.add("entrance_diversity", S, "Entrance diversity", "2 entrance rooms, 2+ carriers, routes >= 20 m apart",
          f"separation {p['entrance_sep_m']:.0f} m (66 ft)", 2, "units",
          note="TIA-942-B / BICSI 002 recommendation for higher ratings: diverse entrances on different sides, "
               "separate fire zones, no shared PDUs or cooling between the two entrance rooms.")
    return {"steps": c.steps, "v": c.v, "params": p, "cooling": cooling, "liquid": lf, "onsite_hv": onsite}
