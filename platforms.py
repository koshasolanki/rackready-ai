"""
RackReady AI - GPU platforms and the facility cost basis.

All money is 2026 US dollars, early budget estimate level (not a bid).

Facility cost basis ("rate", $ per MW of IT load): a calibrated benchmark for a US greenfield AI
facility, open-shop labour, N+1 block redundancy, including the general contractor's fee (about 9%)
and a 4% construction contingency. It EXCLUDES land, the utility-side interconnection, IT hardware
(servers, GPUs, network fabric), owner costs, financing, taxes and escalation after 2026. The app adds
those separately. Public cross-checks are in docs/VERIFICATION.md:
  * 2026 global data center outlook (real-estate advisor): $11.3M/MW shell and core (air-cooled, excludes technical interiors);
    liquid cooling adds about 10%; AI tenant interiors can add up to $25M/MW.
  * 2026 development cost guide (real-estate advisor): $17.6M/MW all-in greenfield (US/Canada,
    excluding chips/GPUs).
  * Data centre construction cost index 2025-26 (cost consultancy): AI/liquid-cooled builds cost
    7-10% more than comparable air-cooled builds.

Rack data: published platform and system-maker specs. Roadmap platforms
are marked "announced" with estimated values; check them with the vendor before committing money.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- CSI divisions
DIVISIONS = ["01 General conditions, design & commissioning", "02 Existing conditions & geotech",
             "03 Concrete", "04 Masonry", "05 Metals", "06 Wood & plastics", "07 Envelope & roofing",
             "08 Openings", "09 Finishes", "10-12 Specialties & furnishings",
             "13 Special construction (prefab power/cooling modules)", "14 Conveying",
             "21 Fire suppression", "22 Plumbing & fuel", "23 HVAC & liquid cooling",
             "25 Controls (BMS / EPMS)", "26 Electrical", "27 Communications backbone",
             "28 Security & fire alarm", "31 Earthwork", "32 Exterior improvements",
             "33 Site utilities"]

# Plain-language groups shown to users (CSI division numbers kept for cost managers)
GROUPS = {
    "Electrical power (Div 26)": ["26"],
    "Cooling: HVAC & liquid (Div 23)": ["23"],
    "Structure, shell & interiors (Div 02-14)": ["02", "03", "04", "05", "06", "07", "08", "09", "10-12", "13", "14"],
    "Site works & utilities (Div 31-33)": ["31", "32", "33"],
    "Plumbing & fuel (Div 22)": ["22"],
    "Fire, security & controls (Div 21, 25, 28)": ["21", "25", "28"],
    "Communications backbone (Div 27)": ["27"],
    "General conditions, design & commissioning (Div 01)": ["01"],
}


def group_of(division: str) -> str:
    code = division.split(" ")[0]
    for g, codes in GROUPS.items():
        if code in codes:
            return g
    raise KeyError(division)


def _mix(vals):
    s = sum(vals)
    return {d: v / s for d, v in zip(DIVISIONS, vals)}


_MIX = {
    "H100": [0.09, 0.006, 0.06, 0.008, 0.042, 0.002, 0.058, 0.012, 0.016, 0.008, 0.028, 0.003, 0.018,
             0.02, 0.175, 0.015, 0.33, 0.022, 0.015, 0.026, 0.024, 0.022],
    "H200": [0.09, 0.006, 0.06, 0.008, 0.042, 0.002, 0.055, 0.012, 0.015, 0.008, 0.03, 0.003, 0.018,
             0.02, 0.18, 0.015, 0.33, 0.022, 0.015, 0.025, 0.022, 0.022],
    "B200": [0.084577, 0.004975, 0.061692, 0.00796, 0.045771, 0.00199, 0.049751, 0.01194, 0.01194,
             0.00796, 0.035821, 0.002985, 0.01791, 0.0199, 0.20398, 0.014925, 0.318408, 0.021891,
             0.014925, 0.021891, 0.018905, 0.0199],
    "GB200": [0.081918, 0.004995, 0.067932, 0.007992, 0.047952, 0.001998, 0.045954, 0.011988,
              0.011988, 0.007992, 0.037962, 0.002997, 0.017982, 0.01998, 0.214785, 0.014985, 0.307692,
              0.021978, 0.014985, 0.01998, 0.017982, 0.017982],
    "GB300": [0.078973, 0.004936, 0.069102, 0.007897, 0.049358, 0.001974, 0.044423, 0.011846,
              0.011846, 0.007897, 0.039487, 0.002962, 0.017769, 0.019743, 0.217177, 0.014808, 0.308983,
              0.021718, 0.014808, 0.019743, 0.017769, 0.016782],
    "RUBIN": [0.077451, 0.004902, 0.068627, 0.007843, 0.04902, 0.001961, 0.039216, 0.011765, 0.009804,
              0.006863, 0.04902, 0.002941, 0.017647, 0.019608, 0.223529, 0.014706, 0.309804, 0.021569,
              0.014706, 0.017647, 0.015686, 0.015686],
    "ASIC": [0.081755, 0.004985, 0.065803, 0.007976, 0.047856, 0.001994, 0.044865, 0.011964, 0.011964,
            0.007976, 0.03988, 0.002991, 0.017946, 0.01994, 0.219342, 0.014955, 0.302094, 0.024925,
            0.014955, 0.01994, 0.017946, 0.017946],
    "KYBER": [0.08563, 0.004921, 0.076772, 0.007874, 0.052165, 0.001969, 0.033465, 0.011811, 0.007874,
              0.004921, 0.057087, 0.002953, 0.016732, 0.018701, 0.224409, 0.014764, 0.309055, 0.018701,
              0.011811, 0.014764, 0.011811, 0.011811],
}

# --------------------------------------------------------------------------- platforms
# kw        = rack IT load used for capacity (vendor TDP / typical operating power)
# kw_peak   = electrical design power per rack (provision busway/branch circuits for this)
# liquid    = share of rack heat captured by liquid when D2C-cooled (vendor data where public)
# rate/low/high = facility $ per MW IT (see module docstring); gsf_per_mw = gross building area
# white_sf  = white-space area per rack position (rack + aisle share + CDU/row-end/circulation)
# gpu_hr    = indicative multi-year contract rental $/GPU-hour (below on-demand list prices)
# status    = shipping | announced (roadmap; values estimated) | estimated
P = {
    "H100 HGX": dict(
        label="NVIDIA H100 HGX (4 x 8-GPU servers)", status="shipping", year=2023,
        kw=41.0, kw_peak=41.0, gpus=32, it_per_rack=1_000_000, weight_lb=1_800, rack_w_m=0.6, rack_d_m=1.2,
        liquid=0.70, cdu_mw=1.6, rate=17_000_000, low=15_500_000, high=21_000_000, gsf_per_mw=4_200,
        white_sf=36, fabric_per_mw=3_000_000, gpu_hr=2.50, mix=_MIX["H100"],
        spec_note="DGX H100 max 10.2 kW per 8-GPU server x 4 per rack (NVIDIA DGX H100 user guide)."),
    "H200 HGX": dict(
        label="NVIDIA H200 HGX (4 x 8-GPU servers)", status="shipping", year=2024,
        kw=42.0, kw_peak=42.0, gpus=32, it_per_rack=1_300_000, weight_lb=1_900, rack_w_m=0.6, rack_d_m=1.2,
        liquid=0.70, cdu_mw=1.6, rate=17_300_000, low=15_800_000, high=21_500_000, gsf_per_mw=4_100,
        white_sf=36, fabric_per_mw=3_000_000, gpu_hr=3.25, mix=_MIX["H200"],
        spec_note="Same server power envelope as H100 HGX (about 10.2 kW per 8-GPU server)."),
    "B200 HGX": dict(
        label="NVIDIA B200 HGX (4 x 8-GPU servers)", status="shipping", year=2025,
        kw=57.0, kw_peak=57.0, gpus=32, it_per_rack=2_000_000, weight_lb=2_400, rack_w_m=0.6, rack_d_m=1.2,
        liquid=0.80, cdu_mw=1.6, rate=18_300_000, low=16_800_000, high=23_000_000, gsf_per_mw=3_400,
        white_sf=34, fabric_per_mw=4_000_000, gpu_hr=4.50, mix=_MIX["B200"],
        spec_note="DGX B200 max about 14.3 kW per 8-GPU server x 4 per rack (NVIDIA DGX B200 datasheet)."),
    "GB200 NVL72": dict(
        label="NVIDIA GB200 NVL72", status="shipping", year=2024,
        kw=120.0, kw_peak=132.0, gpus=72, it_per_rack=3_200_000, weight_lb=3_000, rack_w_m=0.6, rack_d_m=1.068,
        liquid=0.85, cdu_mw=1.6, rate=19_000_000, low=17_800_000, high=24_000_000, gsf_per_mw=2_700,
        white_sf=30, fabric_per_mw=5_000_000, gpu_hr=6.00, mix=_MIX["GB200"],
        spec_note="About 120 kW typical, up to about 132 kW; about 1,360 kg (3,000 lb); about 85% to liquid."),
    "GB300 NVL72": dict(
        label="NVIDIA GB300 NVL72", status="shipping", year=2025,
        kw=135.0, kw_peak=155.0, gpus=72, it_per_rack=4_000_000, weight_lb=3_500, rack_w_m=0.6, rack_d_m=1.068,
        liquid=0.90, cdu_mw=1.6, rate=19_162_800, low=18_325_600, high=25_000_000, gsf_per_mw=2_600,
        white_sf=28, fabric_per_mw=5_000_000, gpu_hr=7.00, mix=_MIX["GB300"],
        spec_note="132-140 kW operating, 135 kW TDP and up to 155 kW peak (system-maker specs); "
                  "eight 33 kW power shelves; 3,300-3,480 lb; about 90% liquid / 10% air."),
    "Vera Rubin NVL144": dict(
        label="NVIDIA Vera Rubin NVL144 (announced)", status="announced", year=2026,
        kw=220.0, kw_peak=230.0, gpus=72, it_per_rack=8_500_000, weight_lb=4_200, rack_w_m=0.6, rack_d_m=1.068,
        liquid=0.95, cdu_mw=1.3, rate=21_631_300, low=19_262_600, high=28_000_000, gsf_per_mw=2_000,
        white_sf=30, fabric_per_mw=6_000_000, gpu_hr=9.00, mix=_MIX["RUBIN"],
        spec_note="NVIDIA: in production, shipping 2H 2026; 72 GPU packages (144 dies). Published rack "
                  "power figures disagree (about 130-230 kW); designed here at the top of the range. "
                  "Weight, price and rental rate are estimates."),
    "Rubin Ultra NVL576 (Kyber)": dict(
        label="NVIDIA Rubin Ultra NVL576 / Kyber rack (announced)", status="announced", year=2027,
        kw=600.0, kw_peak=660.0, gpus=576, it_per_rack=21_000_000, weight_lb=8_000, rack_w_m=1.2, rack_d_m=1.2,
        liquid=0.95, cdu_mw=1.0, rate=30_316_600, low=26_633_200, high=40_000_000, gsf_per_mw=1_400,
        white_sf=40, fabric_per_mw=8_000_000, gpu_hr=3.00, mix=_MIX["KYBER"],
        spec_note="NVIDIA GTC 2025: about 600 kW per rack, 2H 2027, 576 GPU dies, 800 VDC power with a "
                  "sidecar. Rack width (rack + power sidecar), weight, price and rental rate are estimates."),
    "ASIC rack (estimated)": dict(
        label="Custom AI accelerator (ASIC) rack (estimated)", status="estimated", year=2025,
        kw=100.0, kw_peak=110.0, gpus=64, it_per_rack=1_600_000, weight_lb=2_800, rack_w_m=0.6, rack_d_m=1.2,
        liquid=0.90, cdu_mw=1.5, rate=19_000_000, low=17_500_000, high=25_000_000, gsf_per_mw=2_900,
        white_sf=32, fabric_per_mw=3_500_000, gpu_hr=3.00, mix=_MIX["ASIC"],
        spec_note="Accelerator-maker-specified liquid-cooled racks; the facility interface follows that spec. kW, "
                  "price and rental rate are estimates (no public per-rack spec)."),
}
for _k, _v in P.items():
    _v["name"] = _k
    _v["mix"] = _mix(_v["mix"])

PLATFORMS = P
PLATFORM_NAMES = list(P)
CUSTOM = "Custom density"
DEFAULT_PLATFORM = "GB300 NVL72"

# Air-cooled anchor for densities below the GPU ladder (enterprise/cloud halls):
# 2026 market shell & core $11.3M/MW (air, excl. interiors) + light interiors -> $12.0M/MW at 15 kW/rack.
AIR_ANCHOR_KW = 15.0
AIR_ANCHOR_RATE = 12_000_000

# NVIDIA ladder used for custom densities (custom ASIC racks excluded: maker-specific)
LADDER = ["H100 HGX", "H200 HGX", "B200 HGX", "GB200 NVL72", "GB300 NVL72", "Vera Rubin NVL144",
          "Rubin Ultra NVL576 (Kyber)"]

# ---------------------------------------------------------------- unit prices for redundancy changes
# Installed unit prices (2026 USD), incl. paralleling switchgear share; multipliers cover the extra
# isolation, controls and space that a higher-redundancy topology needs.
UNIT_PRICES = {
    "generator_3mw": 3_500_000, "generator_multiplier_n2": 1.15, "generator_multiplier_2n": 1.30,
    "ups_module_1mw": 600_000, "ups_multiplier_2n": 1.20, "cdu_skid": 1_050_000,
    "soft_on_change": 0.13,
}
GC_AND_CONTINGENCY_DIVISOR = 1.13       # rate includes ~9% GC + 4% contingency on hard cost
BASE_CONTINGENCY = 0.04
FUEL_COST_PER_MW_HOUR = 18_000_000 / (100 * 48)   # extra fuel storage: $18M per 100 MW per 48 h


def _interp(x, xs, ys):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + (ys[i + 1] - ys[i]) * t
    return ys[-1]


def custom_platform(kw: float) -> dict:
    """A platform record for any kW/rack, interpolated on the NVIDIA ladder.

    Below the ladder: interpolate to the air-cooled anchor (15 kW). Above 600 kW (1 MW-class racks,
    speculative): the Kyber basis +10% per extra 400 kW, flagged as speculative."""
    kw = float(kw)
    xs = [AIR_ANCHOR_KW] + [P[n]["kw"] for n in LADDER]
    out = {"name": CUSTOM, "label": f"Custom {kw:,.0f} kW/rack", "status": "custom", "year": 2026,
           "kw": kw, "kw_peak": kw * 1.10, "spec_note": "Interpolated between published platforms."}
    num = ["rate", "low", "high", "gsf_per_mw", "white_sf", "fabric_per_mw", "liquid", "cdu_mw",
           "weight_lb", "gpu_hr", "rack_w_m", "rack_d_m"]
    anchor = dict(P["H100 HGX"], rate=AIR_ANCHOR_RATE, low=AIR_ANCHOR_RATE * 0.85, high=AIR_ANCHOR_RATE * 1.25,
                  gsf_per_mw=6_000, white_sf=30, weight_lb=1_500, liquid=0.6)
    recs = [anchor] + [P[n] for n in LADDER]
    for f in num:
        out[f] = _interp(kw, xs, [r[f] for r in recs])
    # GPUs/rack and IT $/rack scale with power on the nearest platform
    near = min(LADDER, key=lambda n: abs(P[n]["kw"] - kw))
    out["gpus"] = max(1, round(P[near]["gpus"] * kw / P[near]["kw"]))
    out["it_per_rack"] = P[near]["it_per_rack"] * kw / P[near]["kw"]
    out["nearest"] = near
    lo = max([n for n in LADDER if P[n]["kw"] <= kw] or [LADDER[0]], key=lambda n: P[n]["kw"])
    hi = min([n for n in LADDER if P[n]["kw"] >= kw] or [LADDER[-1]], key=lambda n: P[n]["kw"])
    wlo = 0.0 if lo == hi or P[hi]["kw"] == P[lo]["kw"] else (kw - P[lo]["kw"]) / (P[hi]["kw"] - P[lo]["kw"])
    out["mix"] = _mix([P[lo]["mix"][d] * (1 - wlo) + P[hi]["mix"][d] * wlo for d in DIVISIONS])
    out["speculative"] = kw > P[LADDER[-1]]["kw"]
    if out["speculative"]:
        f = 1 + 0.10 * (kw - 600) / 400
        for k in ("rate", "low", "high"):
            out[k] = P[LADDER[-1]][k] * f
        out["status"] = "speculative"
        out["spec_note"] = ("Beyond announced products (1 MW-class racks are an industry direction, e.g. "
                            "NVIDIA 800 VDC roadmap). Cost = Kyber-class basis +10% per extra 400 kW; speculative.")
    out["below_ladder"] = kw < P[LADDER[0]]["kw"]
    return out


def platform(name: str, custom_kw: float | None = None) -> dict:
    if name in P:
        return dict(P[name])
    return custom_platform(custom_kw or 135.0)


def rate_for_kw(kw: float) -> float:
    return custom_platform(kw)["rate"]
