"""RackReady AI tests: physics consistency, public sanity ranges, rules and exports."""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import design as DS
import engine as E
import llm
import platforms as PL
import report as R
from design import AIR, D2C, HYBRID

ALL_PLATFORMS = list(PL.PLATFORMS)


def gf(**kw):
    return E.run_model(kw)


# ----------------------------------------------------------------- internal consistency (physics)
@pytest.mark.parametrize("name", ALL_PLATFORMS)
def test_design_physics(name):
    r = gf(platform=name)
    dz = r["design"]["design"]
    v, p = dz["v"], dz["params"]
    pf, V = p["pf_service"], p["voltage"]
    # MVA >= MW / PF, transformers cover it
    assert v["service_mva"] >= v["service_mw"] / pf - 1e-6
    assert v["service_mw"] >= v["fac_peak_kw"] / 1000 - 1e-6
    if dz["onsite_hv"]:
        assert v["main_tx"] * p["main_tx_mva"] >= v["service_mva"]
    # tons = kW / 3.517
    assert v["cool_tons"] == pytest.approx(v["cool_kw"] / 3.517, rel=1e-9)
    # Q = P / (rho cp dT) for both liquid loops
    if v["liquid_kw"]:
        assert v["tcs_lps"] == pytest.approx(v["liquid_kw"] / (p["tcs_rho"] * p["tcs_cp"] * p["tcs_dT"]) * 1000, rel=1e-9)
        assert v["fws_lps"] == pytest.approx(v["liquid_kw"] / (p["w_rho"] * p["w_cp"] * p["fws_dT"]) * 1000, rel=1e-9)
        assert v["liquid_kw"] + v["air_kw"] == pytest.approx(v["cool_kw"], rel=1e-9)
    # I = P / (sqrt3 V PF)
    rack_i = r["design"]["platform"]["kw_peak"] * 1000 / (math.sqrt(3) * V * p["pf_rack"])
    assert v["rack_amps"] == pytest.approx(rack_i, rel=1e-9)
    assert v["busway_rating"] >= 1.25 * v["busway_amps"] or v["busway_rating"] == 0
    assert v["busway_rating"] > 0 or v["rack_amps"] * 1.25 > 5000
    # heat rejection >= cooling load; PUE is an energy ratio >= 1
    assert v["reject_kw"] >= v["cool_kw"]
    assert v["fac_mwh"] == pytest.approx(v["it_mwh"] * v["pue"], rel=1e-9)
    # generators carry the facility peak with redundancy
    assert v["gens"] * p["gen_mw"] >= v["fac_peak_kw"] / 1000
    # floor pressure = weight / footprint
    plat = r["design"]["platform"]
    psf = plat["weight_lb"] / (plat["rack_w_m"] * plat["rack_d_m"] * DS.SF_PER_M2)
    assert v["rack_psf"] == pytest.approx(psf, rel=1e-6)
    # every step has formula, inputs and a numeric result
    for s in dz["steps"]:
        assert s["formula"] and s["inputs"] is not None and s["unit"] is not None


def test_worked_examples_from_engineering_references():
    """Hand-checkable examples."""
    assert 120_000 / (math.sqrt(3) * 415 * 0.98) == pytest.approx(170.4, abs=0.5)
    # 18 MW of liquid at 10 K with water -> about 431 L/s (6,800 gpm)
    q = 18_000 / (997 * 4.18 * 10) * 1000
    assert q == pytest.approx(431.9, abs=1) and q * DS.GPM_PER_LPS == pytest.approx(6846, abs=15)
    # 2 MW x 10 min = 333 kWh before losses
    assert 2000 * 10 / 60 == pytest.approx(333.3, abs=0.1)
    assert DS.KW_PER_TON == 3.517


def test_default_worked_example_numbers():
    r = gf()
    d = r["design"]
    v = d["design"]["v"]
    assert d["racks"] == 741 and d["it_mw"] == 100
    assert v["pue"] == pytest.approx(1.20, abs=0.01)
    assert v["service_mva"] == pytest.approx(156.3, abs=0.5)
    assert v["gens"] == 50 and v["ups_modules"] == 129 and v["cdus"] == 67
    assert v["cool_tons"] == pytest.approx(30_024, abs=5)
    assert v["tcs_lps"] == pytest.approx(2252, abs=3)
    assert v["busway_rating"] == 3000
    assert d["facility_per_mw"] == pytest.approx(19.84e6, rel=0.005)
    assert abs(sum(d["lines"].values()) - d["capex"]) < 1


# ----------------------------------------------------------------- public sanity ranges
@pytest.mark.parametrize("name", ALL_PLATFORMS)
def test_greenfield_ranges(name):
    r = gf(platform=name)
    d = r["design"]
    lo, hi, _ = E.RANGES["facility_per_mw_hd"]
    assert lo <= d["facility_per_mw"] <= hi
    assert 1.10 <= d["design"]["v"]["pue"] <= 1.50
    assert 0.0 <= d["design"]["v"]["wue"] <= 2.6
    assert all(c["ok"] for c in r["checks"]), [c for c in r["checks"] if not c["ok"]]


def test_air_cooled_range():
    r = gf(platform=PL.CUSTOM, custom_kw=15, cooling=AIR)
    d = r["design"]
    assert d["cooling"] == AIR
    assert 10e6 <= d["facility_per_mw"] <= 15e6        # ~$10-15M/MW for air
    assert 1.35 <= d["design"]["v"]["pue"] <= 1.50
    assert 1.5 <= d["design"]["v"]["wue"] <= 2.6        # evaporative towers


def test_power_prices_and_lead_times():
    for reg in E.REGIONS.values():
        assert 0.05 <= reg["power"] <= 0.20
    us = [v["power"] for k, v in E.REGIONS.items() if k.startswith("US")]
    assert all(0.06 <= p <= 0.12 for p in us)
    assert 104 <= E.TRANSFORMER_WEEKS <= 156               # 1-2+ years
    gen = next(x for x in E.LONG_LEAD if x[0].startswith("Standby diesel generators"))
    assert 52 <= gen[1] <= gen[2] <= 110                     # about 1.5-2 years


def test_gpu_rates_inside_public_ranges():
    for name, (lo, hi) in E.GPU_MARKET.items():
        assert lo <= PL.PLATFORMS[name]["gpu_hr"] <= hi
    assert 2.0 <= PL.PLATFORMS["H100 HGX"]["gpu_hr"] <= 4.0   # Hopper-class $2-4


# ----------------------------------------------------------------- the D2C rule
@pytest.mark.parametrize("kw,expect", [(40, HYBRID), (45, HYBRID), (46, D2C), (50, D2C), (600, D2C)])
def test_d2c_rule_greenfield(kw, expect):
    r = gf(platform=PL.CUSTOM, custom_kw=kw, cooling=HYBRID)
    assert r["design"]["cooling"] == expect
    assert r["design"]["cooling_auto"] == (expect == D2C)


def test_600kw_case():
    r = gf(platform=PL.CUSTOM, custom_kw=600)
    d = r["design"]
    v = d["design"]["v"]
    assert d["cooling"] == D2C and v["pue"] < 1.25
    assert v["rack_amps"] > 800                          # why 800 VDC
    assert v["dc800_amps"] < v["busbar54_amps"]
    assert d["facility_per_mw"] > 25e6
    k = gf(platform="Rubin Ultra NVL576 (Kyber)")
    assert k["design"]["kw"] == 600


# ----------------------------------------------------------------- greenfield = single build
def test_greenfield_single_build():
    r = gf()
    assert "current" not in r and "upgrade" not in r and not hasattr(E, "FITOUT")
    p = E.summary_for_llm(r)
    assert "current" not in p and "retrofit_comparison" not in p
    text = llm.fallback_narrative(r).lower()
    assert "current build" not in text and "upgrade path" not in text


# ----------------------------------------------------------------- future-ready horizon
@pytest.mark.parametrize("h,kw", [("5 years", 230), ("10 years", 600), ("15 years", 1000)])
def test_horizons(h, kw):
    r = gf(horizon=h)
    f = r["future"]
    assert f["active"] and f["target_kw"] == kw
    names = [x["path"] for x in f["paths"]]
    assert len(names) == 3 and f["best"] in names
    best = min(f["paths"], key=lambda x: x["pv_total"])
    assert best["path"] == f["best"]
    full = next(x for x in f["paths"] if x["path"].startswith("Full"))
    prov = next(x for x in f["paths"] if "provisions" in x["path"])
    assert full["day1"] >= prov["day1"] >= 0
    assert f["design_T"]["cooling"] == D2C
    if kw >= 400:
        assert any(p["provision"] == "800 VDC readiness" for p in f["provisions"])


def test_horizon_none_and_already_ready():
    assert not gf(horizon="Today only")["future"]["active"]
    assert not gf(platform="Rubin Ultra NVL576 (Kyber)", horizon="10 years")["future"]["active"]


def test_spare_utility_increases_target():
    a = gf(spare_utility_pct=0.0)["future"]
    b = gf(spare_utility_pct=0.25)["future"]
    assert b["target_mw"] == pytest.approx(a["target_mw"] * 1.25)
    assert b["delta"] > a["delta"]


# ----------------------------------------------------------------- resilience and options
def test_resilience_ordering():
    costs = {k: gf(resilience=k, horizon="Today only")["design"]["capex"] for k in E.RESILIENCE}
    assert costs["N"] < costs["N+1"] < costs["N+2"] < costs["2N"]
    g = {k: gf(resilience=k)["design"]["design"]["v"]["gens"] for k in E.RESILIENCE}
    assert g["N"] < g["N+1"] < g["N+2"] < g["2N"]


def test_contingency_and_fuel_move_cost():
    base = gf()["design"]["capex"]
    assert gf(contingency=0.15)["design"]["capex"] > base
    assert gf(fuel_hours=96)["design"]["capex"] > base


def test_regions_and_presets():
    for reg in E.REGION_NAMES:
        r = gf(region=reg)
        assert r["design"]["capex"] > 0
    for name, pre in E.PRESETS.items():
        r = E.run_model(pre)
        assert r["recommendation"]["headline"]
        assert all(c["ok"] for c in r["checks"]), (name, [c for c in r["checks"] if not c["ok"]])


def test_size_by_racks():
    r = gf(size_by="Racks", racks=100)
    assert r["design"]["racks"] == 100 and r["design"]["it_mw"] == pytest.approx(13.5)


# ----------------------------------------------------------------- exports and wording
def _public_text(r):
    parts = [R.markdown_report(r), llm.fallback_narrative(r), llm.SYSTEM_PROMPT]
    for df in R.all_tables(r).values():
        parts.append(df.to_csv(index=False))
    return "\n".join(parts)


BANNED = re.compile(r"workbook|spreadsheet|\bsheet\b|\brow \d|\bcells? [A-Z]{1,2}\d+|Method A|Method B|(?-i:RIGHT)|\.xlsx|\.docx",
                    re.IGNORECASE)


@pytest.mark.parametrize("pre", list(E.PRESETS))
def test_no_internal_references(pre):
    r = E.run_model(E.PRESETS[pre])
    text = _public_text(r)
    m = BANNED.search(text.replace("NVL72", ""))
    assert m is None, m and text[max(0, m.start() - 80): m.end() + 80]
    md = R.markdown_report(r)
    assert "Early budget estimate (±30–50%), not a bid" in md and "TERMS.md" in md


@pytest.mark.parametrize("pre", list(E.PRESETS))
def test_pdf_one_page(pre):
    b = R.pdf_report(E.run_model(E.PRESETS[pre]))
    assert b[:4] == b"%PDF"
    assert len(re.findall(rb"/Type\s*/Page[^s]", b)) == 1


def test_llm_payload_has_design_calcs():
    p = E.summary_for_llm(gf())
    assert "design_calculations" in p and p["design_calculations"]["service_mva"] > 0
    assert p["future_ready"]["best"]


def test_api_key_never_in_payload(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "sk-test-secret")
    p = E.summary_for_llm(gf())
    assert "sk-test-secret" not in str(p)
    assert llm.resolve_api_key() == "sk-test-secret"
