import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from engine import (run_model, ASSUMPTIONS, COOLING_TYPES, REGIONS, D2C, GREENFIELD, GF_REDUNDANCY,
                    PLATFORM_CHOICES, summary_for_llm, effective_cooling)
import workbook_basis as WB
import llm


# ----------------------------------------------------------------- fit-out
def test_fitout_defaults_believable():
    r = run_model()
    assert r["mode"] == "fitout"
    c, f = r["current"], r["future"]
    assert abs(c["it_mw"] - 3.0) < 1e-9 and abs(f["it_mw"] - 28.0) < 1e-9
    assert 10e6 <= c["capex_per_mw"] <= 15e6
    assert 10e6 <= f["capex_per_mw"] <= 18e6
    assert f["cooling"] == D2C and f["cooling_auto"] and c["cooling"] == "Air"
    assert f["cdus"] == 19  # ROUNDUP(28 / 1.6) + 1
    for s in (c, f):
        assert abs(s["capex"] - (s["direct"] + s["soft"] + s["contingency"])) < 1
        assert abs(sum(s["systems"].values()) - s["direct"]) < 1
        assert abs(sum(s["opex_items"].values()) - s["opex"]) < 1
        assert abs(sum(v for _, _, v in s["detail"]) - s["direct"]) < 1
    e = 28000 * 0.8 * 1.20 * 8760 * 0.08
    fo = f["opex_items"]
    assert abs(fo["IT energy"] + fo["Cooling energy"] + fo["Other facility energy (losses, lighting)"] - e) < 1
    assert abs(f["revenue"] - 200 * 72 * 3.5 * 0.8 * 8760) < 1
    assert f["simple_payback"] and 1 < f["simple_payback"] < 10
    assert r["warnings"] == []
    assert r["upgrade"]["recommended"].startswith("Build future-ready")


def test_fitout_all_options_run():
    for cool in COOLING_TYPES:
        for reg in REGIONS:
            for red in ASSUMPTIONS["redundancy"]:
                for tier in ASSUMPTIONS["tier"]:
                    r = run_model({"future_cooling": cool, "region": reg, "redundancy": red, "tier": tier})
                    assert r["future"]["capex"] > 0 and r["future"]["cooling"] == D2C


def test_multipliers_direction():
    base = run_model()["future"]["capex"]
    assert run_model({"redundancy": "2N"})["future"]["capex"] > base
    assert run_model({"tier": "Tier IV"})["future"]["capex"] > base
    assert run_model({"region": "India - Mumbai"})["future"]["capex"] < base


# ----------------------------------------------------------------- D2C rule
@pytest.mark.parametrize("kw,chosen,expect", [
    (40, "Air", "Air"), (45, "Hybrid (rear-door + air)", "Hybrid (rear-door + air)"),
    (45.1, "Air", D2C), (50, "Hybrid (rear-door + air)", D2C), (140, "Air", D2C), (600, D2C, D2C)])
def test_d2c_rule(kw, chosen, expect):
    assert effective_cooling(kw, chosen)[0] == expect


def test_d2c_rule_fitout_current_and_warning():
    r = run_model({"current_kw": 50.0, "current_cooling": "Air", "future_cooling": "Air"})
    assert r["current"]["cooling"] == D2C and r["future"]["cooling"] == D2C
    assert sum("auto-selected" in w for w in r["warnings"]) == 2
    r = run_model({"current_kw": 40.0, "current_cooling": "Air"})
    assert r["current"]["cooling"] == "Air"
    assert any("exceeds the practical limit of Air" in w for w in r["warnings"])


def test_d2c_rule_greenfield_custom():
    lo = run_model({"project_type": GREENFIELD, "gf_platform": "Custom", "gf_custom_kw": 40.0,
                    "gf_cooling": "Air"})["design"]
    hi = run_model({"project_type": GREENFIELD, "gf_platform": "Custom", "gf_custom_kw": 50.0,
                    "gf_cooling": "Air"})["design"]
    assert lo["cooling"] == "Air" and not lo["cooling_auto"]
    assert hi["cooling"] == D2C and hi["cooling_auto"]


# ----------------------------------------------------------------- greenfield
def _gf(**kw):
    return run_model({"project_type": GREENFIELD, **kw})


def test_greenfield_single_design_no_current():
    r = _gf()
    assert r["mode"] == "greenfield"
    assert "current" not in r and "upgrade" not in r
    p = summary_for_llm(r)
    assert "current" not in p and "upgrade_paths" not in p
    txt = llm.fallback_narrative(r)
    assert "Current build" not in txt and "retrofit" not in txt.lower()
    assert "## Design & scope recommendation" in txt
    assert r["warnings"] == []


@pytest.mark.parametrize("plat", WB.PLATFORM_NAMES)
def test_greenfield_reconciles_to_workbook(plat):
    d = _gf(gf_platform=plat)["design"]
    b = WB.PLATFORMS[plat]
    assert abs(d["facility"] - b["right"] * 100) < 1          # 03_SIDE8 r9
    assert abs(sum(d["csi"].values()) - d["facility"]) < 1
    assert abs(d["it_hw"] - b["it_per_mw"] * 100) < 100          # 03_SIDE8 r14 x 100
    all_in = d["facility"] + d["it_hw"] + 5e6 + 8e6
    assert abs(all_in - b["all_in_100mw"]) < 100                 # 03_SIDE8 r16
    assert abs(d["capex"] - (d["facility"] + 13e6)) < 1
    assert d["band_check"] == "IN BAND"
    assert abs(d["racks"] - 100_000 / b["kw"]) < 1e-6
    for row in d["reconciliation"]:
        if row[0].startswith("ALL-IN") or row[0].startswith("= Facility"):
            assert abs(row[3]) < 100
    if b["kw"] > 45:
        assert d["cooling"] == D2C
    assert d["quantities"]["gens_n1"] == b["gens_n1_100mw"]   # 03_SIDE8 r22


def test_greenfield_change_pricing_worked_example():
    # 12_CHANGE_PRICING A57: GB300 100 MW, N+2 = +1 x $3.5M x 1.15 ~ $4.0M before soft
    d = _gf(gf_redundancy=GF_REDUNDANCY[1])["design"]
    assert abs(d["changes"][0][1] - 4.025e6) < 1
    d = _gf(gf_redundancy=GF_REDUNDANCY[2])["design"]
    assert abs(d["changes"][0][1] - 39 * 3.5e6 * 1.30) < 1     # ~ $177M
    base = _gf()["design"]["capex"]
    assert _gf(gf_fuel_96h=True)["design"]["capex"] > base
    assert _gf(gf_union_seismic_piles=True)["design"]["capex"] > base
    assert _gf(gf_contingency_pct=0.08)["design"]["capex"] > base
    assert abs(_gf(gf_it_fitout=True)["design"]["facility"] - 2_036_279_950) < 5   # 03_SIDE8 r37 x 100


def test_greenfield_sizing_options_and_payload():
    d = _gf(gf_size_by="Racks", gf_racks=200)["design"]
    assert abs(d["it_mw"] - 27.0) < 1e-9
    for plat in PLATFORM_CHOICES:
        for reg in REGIONS[:3]:
            r = _gf(gf_platform=plat, region=reg)
            assert r["design"]["capex"] > 0 and r["design"]["simple_payback"]
    p = summary_for_llm(_gf())
    assert p["project_type"] == GREENFIELD and p["capex"]["band_check"] == "IN BAND"
    assert "Greenfield" in llm.SYSTEM_PROMPT and "45 kW" in llm.SYSTEM_PROMPT


def test_workbook_basis():
    for p in WB.PLATFORMS.values():
        assert abs(sum(p["csi_mix"].values()) - 1) < 1e-3
    b = WB.custom_basis(135)
    assert abs(b["right"] - WB.PLATFORMS["GB300 NVL72"]["right"]) < 1
    assert not WB.custom_basis(15)["in_range"]


# ----------------------------------------------------------------- llm plumbing
def test_fallback_no_key():
    txt = llm.fallback_narrative(run_model())
    for h in ["## Executive summary", "## Upgrade path recommendation", "## Key risks"]:
        assert h in txt
    with pytest.raises(llm.LLMError):
        llm.stream_narrative({}, api_key="")
    assert llm.resolve_api_key(None, None) in (None, os.environ.get("NEBIUS_API_KEY"))


def test_think_strip(monkeypatch):
    def mk(t):
        return types.SimpleNamespace(choices=[types.SimpleNamespace(delta=types.SimpleNamespace(content=t))])
    pieces = ["<thi", "nk>secret reasoning</th", "ink>\n## Executive", " summary\nHello world."]

    class FakeClient:
        def __init__(self, **kw):
            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(
                create=lambda **k: iter([mk(p) for p in pieces])))
    import openai
    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    out = "".join(llm.stream_narrative({"x": 1}, api_key="k"))
    assert "secret" not in out and out.startswith("## Executive summary"), out
