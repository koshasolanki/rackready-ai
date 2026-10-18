"""
Greenfield benchmark basis extracted from the user-supplied workbook
"AI RACK RESEARCH - THE RIGHT ESTIMATE - EIGHT PLATFORMS" (xlsx, 22 sheets).

Sources (sheet / rows):
  01_ASSUME8 rows 6, 12, 33 (kW/rack design, GSF per IT MW, PUE planning),
             rows 63-64 (GC 9%, contingency 4%), 78-79 (interconnect $8M, land $5M once / 100 MW)
  03_SIDE8   rows 8, 12, 13 (RIGHT, LOW Method A, HIGH Method B facility $/IT MW)
  20_CSI8_MATRIX rows 6-27, cols O-V (22-division CSI mix % of RIGHT $/IT MW)
  02_WHAT_RIGHT row 6 / 11_SPEC_MOVES row 22 (what facility $ excludes: IT racks, AI fabric,
             land, utility-side interconnect, owner staff, financing)
Basis: US greenfield, open shop, spread footings + SOG, N+1 block-redundant, 2026 GMP screen.
Indicative planning numbers only, not a bid.
"""
from __future__ import annotations

SOURCE_NAME = "User workbook: AI Rack Research - The Right Estimate (8 platforms)"
GC_PCT = 0.09  # 01_ASSUME8 row 63
CONTINGENCY_PCT = 0.04  # 01_ASSUME8 row 64 (GMP screen; 60% CD argue 7-10%)
INTERCONNECT_ONCE_100MW = 8000000  # 01_ASSUME8 row 78 (live often $2-20M+, 12-48 months)
LAND_ONCE_100MW = 5000000  # 01_ASSUME8 row 79

PLATFORMS = {
    'H100 HGX': {"kw": 41, "gsf_per_mw": 4200, "pue": 1.28,
        "right": 17000000, "low": 15500000, "high": 21000000,
        "csi_mix": {'01 GC/BIM/Cx': 0.09, '02 Existing': 0.006, '03 Concrete': 0.06, '04 Masonry': 0.008, '05 Metals': 0.042, '06 Woods': 0.002, '07 Envelope': 0.058, '08 Openings': 0.012, '09 Finishes': 0.016, '10-12 Specialties': 0.008, '13 Phoenix modules': 0.028, '14 Conveying': 0.003, '21 Fire': 0.018, '22 Plumbing/fuel': 0.02, '23 HVAC/liquid': 0.175, '25 BMS/EPMS': 0.015, '26 Electrical': 0.33, '27 Comms backbone': 0.022, '28 Security/FA': 0.015, '31 Earthwork': 0.026, '32 Exterior': 0.024, '33 On-site util': 0.022}},
    'H200 HGX': {"kw": 42, "gsf_per_mw": 4100, "pue": 1.26,
        "right": 17300000, "low": 15800000, "high": 21500000,
        "csi_mix": {'01 GC/BIM/Cx': 0.09, '02 Existing': 0.006, '03 Concrete': 0.06, '04 Masonry': 0.008, '05 Metals': 0.042, '06 Woods': 0.002, '07 Envelope': 0.055, '08 Openings': 0.012, '09 Finishes': 0.015, '10-12 Specialties': 0.008, '13 Phoenix modules': 0.03, '14 Conveying': 0.003, '21 Fire': 0.018, '22 Plumbing/fuel': 0.02, '23 HVAC/liquid': 0.18, '25 BMS/EPMS': 0.015, '26 Electrical': 0.33, '27 Comms backbone': 0.022, '28 Security/FA': 0.015, '31 Earthwork': 0.025, '32 Exterior': 0.022, '33 On-site util': 0.022}},
    'B200 HGX': {"kw": 55, "gsf_per_mw": 3400, "pue": 1.22,
        "right": 18300000, "low": 16800000, "high": 23000000,
        "csi_mix": {'01 GC/BIM/Cx': 0.084577, '02 Existing': 0.004975, '03 Concrete': 0.061692, '04 Masonry': 0.00796, '05 Metals': 0.045771, '06 Woods': 0.00199, '07 Envelope': 0.049751, '08 Openings': 0.01194, '09 Finishes': 0.01194, '10-12 Specialties': 0.00796, '13 Phoenix modules': 0.035821, '14 Conveying': 0.002985, '21 Fire': 0.01791, '22 Plumbing/fuel': 0.0199, '23 HVAC/liquid': 0.20398, '25 BMS/EPMS': 0.014925, '26 Electrical': 0.318408, '27 Comms backbone': 0.021891, '28 Security/FA': 0.014925, '31 Earthwork': 0.021891, '32 Exterior': 0.018905, '33 On-site util': 0.0199}},
    'GB200 NVL72': {"kw": 120, "gsf_per_mw": 2700, "pue": 1.2,
        "right": 19000000, "low": 17800000, "high": 24000000,
        "csi_mix": {'01 GC/BIM/Cx': 0.081918, '02 Existing': 0.004995, '03 Concrete': 0.067932, '04 Masonry': 0.007992, '05 Metals': 0.047952, '06 Woods': 0.001998, '07 Envelope': 0.045954, '08 Openings': 0.011988, '09 Finishes': 0.011988, '10-12 Specialties': 0.007992, '13 Phoenix modules': 0.037962, '14 Conveying': 0.002997, '21 Fire': 0.017982, '22 Plumbing/fuel': 0.01998, '23 HVAC/liquid': 0.214785, '25 BMS/EPMS': 0.014985, '26 Electrical': 0.307692, '27 Comms backbone': 0.021978, '28 Security/FA': 0.014985, '31 Earthwork': 0.01998, '32 Exterior': 0.017982, '33 On-site util': 0.017982}},
    'GB300 NVL72': {"kw": 135, "gsf_per_mw": 2600, "pue": 1.2,
        "right": 19162800, "low": 18325599, "high": 25000000,
        "csi_mix": {'01 GC/BIM/Cx': 0.078973, '02 Existing': 0.004936, '03 Concrete': 0.069102, '04 Masonry': 0.007897, '05 Metals': 0.049358, '06 Woods': 0.001974, '07 Envelope': 0.044423, '08 Openings': 0.011846, '09 Finishes': 0.011846, '10-12 Specialties': 0.007897, '13 Phoenix modules': 0.039487, '14 Conveying': 0.002962, '21 Fire': 0.017769, '22 Plumbing/fuel': 0.019743, '23 HVAC/liquid': 0.217177, '25 BMS/EPMS': 0.014808, '26 Electrical': 0.308983, '27 Comms backbone': 0.021718, '28 Security/FA': 0.014808, '31 Earthwork': 0.019743, '32 Exterior': 0.017769, '33 On-site util': 0.016782}},
    'Vera Rubin': {"kw": 220, "gsf_per_mw": 2000, "pue": 1.22,
        "right": 21631297, "low": 19262594, "high": 28000000,
        "csi_mix": {'01 GC/BIM/Cx': 0.077451, '02 Existing': 0.004902, '03 Concrete': 0.068627, '04 Masonry': 0.007843, '05 Metals': 0.04902, '06 Woods': 0.001961, '07 Envelope': 0.039216, '08 Openings': 0.011765, '09 Finishes': 0.009804, '10-12 Specialties': 0.006863, '13 Phoenix modules': 0.04902, '14 Conveying': 0.002941, '21 Fire': 0.017647, '22 Plumbing/fuel': 0.019608, '23 HVAC/liquid': 0.223529, '25 BMS/EPMS': 0.014706, '26 Electrical': 0.309804, '27 Comms backbone': 0.021569, '28 Security/FA': 0.014706, '31 Earthwork': 0.017647, '32 Exterior': 0.015686, '33 On-site util': 0.015686}},
    'TPU Ironwood': {"kw": 100, "gsf_per_mw": 2900, "pue": 1.18,
        "right": 19000000, "low": 17500000, "high": 25000000,
        "csi_mix": {'01 GC/BIM/Cx': 0.081755, '02 Existing': 0.004985, '03 Concrete': 0.065803, '04 Masonry': 0.007976, '05 Metals': 0.047856, '06 Woods': 0.001994, '07 Envelope': 0.044865, '08 Openings': 0.011964, '09 Finishes': 0.011964, '10-12 Specialties': 0.007976, '13 Phoenix modules': 0.03988, '14 Conveying': 0.002991, '21 Fire': 0.017946, '22 Plumbing/fuel': 0.01994, '23 HVAC/liquid': 0.219342, '25 BMS/EPMS': 0.014955, '26 Electrical': 0.302094, '27 Comms backbone': 0.024925, '28 Security/FA': 0.014955, '31 Earthwork': 0.01994, '32 Exterior': 0.017946, '33 On-site util': 0.017946}},
    'Kyber': {"kw": 600, "gsf_per_mw": 1400, "pue": 1.25,
        "right": 30316594, "low": 26633187, "high": 40000000,
        "csi_mix": {'01 GC/BIM/Cx': 0.08563, '02 Existing': 0.004921, '03 Concrete': 0.076772, '04 Masonry': 0.007874, '05 Metals': 0.052165, '06 Woods': 0.001969, '07 Envelope': 0.033465, '08 Openings': 0.011811, '09 Finishes': 0.007874, '10-12 Specialties': 0.004921, '13 Phoenix modules': 0.057087, '14 Conveying': 0.002953, '21 Fire': 0.016732, '22 Plumbing/fuel': 0.018701, '23 HVAC/liquid': 0.224409, '25 BMS/EPMS': 0.014764, '26 Electrical': 0.309055, '27 Comms backbone': 0.018701, '28 Security/FA': 0.011811, '31 Earthwork': 0.014764, '32 Exterior': 0.011811, '33 On-site util': 0.011811}},
}

SHELL_DIVS = ("03 Concrete", "04 Masonry", "05 Metals", "06 Woods", "07 Envelope",
              "08 Openings", "09 Finishes", "10-12 Specialties", "14 Conveying")
SITE_DIVS = ("02 Existing", "31 Earthwork", "32 Exterior", "33 On-site util")

# NVIDIA density ladder used for interpolation (TPU kept in the table, not on the curve:
# its facility basis depends on a Google ICD).
CURVE = sorted((p for n, p in PLATFORMS.items() if n != "TPU Ironwood"), key=lambda p: p["kw"])
CURVE_NAMES = [n for n, p in sorted(PLATFORMS.items(), key=lambda kv: kv[1]["kw"])
               if n != "TPU Ironwood"]


def _derived(p: dict) -> dict:
    right = p["right"]
    shell_mw = sum(p["csi_mix"][d] for d in SHELL_DIVS) * right / (1 + CONTINGENCY_PCT)
    site_mw = sum(p["csi_mix"][d] for d in SITE_DIVS) * right / (1 + CONTINGENCY_PCT)
    return {"right": right, "low": p["low"], "high": p["high"], "gsf_per_mw": p["gsf_per_mw"],
            "shell_per_gsf": shell_mw / p["gsf_per_mw"], "site_civil_per_mw": site_mw}


def _lerp(a, b, t):
    return a + (b - a) * t


def benchmark(kw: float) -> dict:
    """Interpolate the workbook's facility benchmarks at a rack density (kW/rack).

    Below 41 kW (H100) the workbook has no data: values are held flat at H100 and
    flagged `in_range=False`."""
    pts = [(p["kw"], _derived(p)) for p in CURVE]
    if kw <= pts[0][0]:
        d, lo_name, hi_name, t = pts[0][1], CURVE_NAMES[0], CURVE_NAMES[0], 0.0
        out = dict(d)
    elif kw >= pts[-1][0]:
        out, lo_name, hi_name = dict(pts[-1][1]), CURVE_NAMES[-1], CURVE_NAMES[-1]
    else:
        for j in range(len(pts) - 1):
            k0, d0 = pts[j]
            k1, d1 = pts[j + 1]
            if k0 <= kw <= k1:
                t = (kw - k0) / (k1 - k0)
                out = {k: _lerp(d0[k], d1[k], t) for k in d0}
                lo_name, hi_name = CURVE_NAMES[j], CURVE_NAMES[j + 1]
                break
    out["in_range"] = pts[0][0] <= kw <= pts[-1][0]
    out["bracket"] = lo_name if lo_name == hi_name else f"{lo_name} - {hi_name}"
    nearest = min(PLATFORMS.items(), key=lambda kv: abs(kv[1]["kw"] - kw))
    out["nearest_platform"] = nearest[0]
    out["csi_mix"] = nearest[1]["csi_mix"]
    return out


def band_check(value_per_mw: float, kw: float) -> str:
    b = benchmark(kw)
    if value_per_mw < b["low"]:
        s = "BELOW BAND"
    elif value_per_mw > b["high"]:
        s = "ABOVE BAND"
    else:
        s = "IN BAND"
    return s if b["in_range"] else s + " (density below workbook range, H100 basis)"
