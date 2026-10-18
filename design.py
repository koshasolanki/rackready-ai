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
}

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
           params: dict | None = None) -> dict:
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
              f"{p['main_tx_mva']:.0f} MVA each", note="Typical 60-100 MVA units; lead time 2+ years.")
    else:
        c.add("main_tx", S, "On-site HV substation", "Needed when S > 40 MVA (planning rule)",
              f"{svc_mva:,.1f} MVA", 0, "units", note="Medium-voltage utility service; no on-site HV yard.")
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
                 note=f"N+1 = one spare per group of up to {p['gen_group']} running sets; 2N = full duplicate plant.")
    c.v["gens_run"] = g_run
    c.add("gen_kva", S, "Generator kVA rating (each)", "S = P / PF", f"{p['gen_mw'] * 1000:,.0f} kW / 0.80",
          p["gen_mw"] * 1000 / 0.8, "kVA", note="Gensets are rated at 0.8 PF.")
    fuel = c.add("fuel_gal", S, "Fuel storage", "Fuel = P_fac x gal/kWh x hours",
                 f"{fmt(fac_pk)} kW x {p['fuel_gal_per_kwh']:.3f} x {p['fuel_hours']:.0f} h",
                 fac_pk * p["fuel_gal_per_kwh"] * p["fuel_hours"], "gal",
                 f"{fac_pk * p['fuel_gal_per_kwh'] * p['fuel_hours'] * L_PER_GAL / 1000:,.0f} m3",
                 note="Usable fuel at design load; add unusable volume and code/insurer reserve.")
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
    return {"steps": c.steps, "v": c.v, "params": p, "cooling": cooling, "liquid": lf, "onsite_hv": onsite}
