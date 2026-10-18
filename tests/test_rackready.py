import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import run_model, ASSUMPTIONS, COOLING_TYPES, REGIONS
import llm


def test_defaults_believable():
    r = run_model()
    c, f = r["current"], r["future"]
    assert abs(c["it_mw"] - 3.0) < 1e-9 and abs(f["it_mw"] - 28.0) < 1e-9
    assert 10e6 <= c["capex_per_mw"] <= 15e6, c["capex_per_mw"]
    assert f["capex_per_mw"] > c["capex_per_mw"]
    assert 12e6 <= f["capex_per_mw"] <= 18e6
    # totals reconcile
    for s in (c, f):
        assert abs(s["capex"] - (s["direct"] + s["soft"] + s["contingency"])) < 1
        assert abs(sum(s["systems"].values()) - s["direct"]) < 1
        assert abs(sum(s["opex_items"].values()) - s["opex"]) < 1
        assert abs(sum(v for _, _, v in s["detail"]) - s["direct"]) < 1
    # energy formula
    e = 28000 * 0.8 * 1.15 * 8760 * 0.08
    fo = f["opex_items"]
    assert abs(fo["IT energy"] + fo["Cooling energy"] + fo["Other facility energy (losses, lighting)"] - e) < 1
    assert abs(f["revenue"] - 200 * 72 * 3.5 * 0.8 * 8760) < 1
    assert f["simple_payback"] and 1 < f["simple_payback"] < 10
    assert r["warnings"] == []
    assert r["upgrade"]["recommended"].startswith("Build future-ready")


def test_all_options_run():
    for cool in COOLING_TYPES:
        for reg in REGIONS:
            for red in ASSUMPTIONS["redundancy"]:
                for tier in ASSUMPTIONS["tier"]:
                    r = run_model({"future_cooling": cool, "region": reg,
                                   "redundancy": red, "tier": tier})
                    assert r["future"]["capex"] > 0


def test_cooling_warning():
    r = run_model({"future_cooling": "Air"})
    assert any("exceeds" in w for w in r["warnings"])


def test_multipliers_direction():
    base = run_model()["future"]["capex"]
    assert run_model({"redundancy": "2N"})["future"]["capex"] > base
    assert run_model({"tier": "Tier IV"})["future"]["capex"] > base
    assert run_model({"region": "India - Mumbai"})["future"]["capex"] < base


def test_fallback_no_key():
    r = run_model()
    txt = llm.fallback_narrative(r)
    for h in ["## Executive summary", "## Upgrade path recommendation", "## Key risks"]:
        assert h in txt
    try:
        llm.stream_narrative({}, api_key="")
        assert False, "should raise"
    except llm.LLMError:
        pass
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


# ----------------------------------------------------------------- greenfield
from engine import GREENFIELD, PROJECT_TYPES, summary_for_llm
import workbook_basis as WB


def _gf(**kw):
    return run_model({"project_type": GREENFIELD, **kw})


def test_fitout_default_unchanged():
    r = run_model()
    assert r["inputs"]["project_type"] == PROJECT_TYPES[0]
    assert r["future"]["greenfield"] is None and r["future"]["owner_costs"] == {}
    assert abs(r["future"]["capex"] / 1e6 - 384.4) < 0.1


def test_greenfield_reconciles_and_exceeds_fitout():
    fit, gf = run_model(), _gf()
    for key in ("current", "future"):
        s = gf[key]
        assert s["capex"] > fit[key]["capex"]
        assert abs(s["capex"] - (s["direct"] + s["soft"] + s["contingency"] + s["escalation"]
                                 + sum(s["owner_costs"].values()))) < 1
        assert abs(sum(s["systems"].values()) - s["direct"]) < 1
        assert abs(sum(v for _, _, v in s["detail"]) - s["direct"]) < 1
        assert abs(sum(s["opex_items"].values()) - s["opex"]) < 1
        for k in ("Site work & civil (Div 02/31/32/33)", "Shell & core - new build (Div 03-14)"):
            assert s["systems"][k] > 0
        assert "Structural & architectural (Div 03/05/09)" not in s["systems"]
        assert s["owner_costs"]["Land acquisition"] > 0
        assert "Property tax (owned land & building)" in s["opex_items"]
    f = gf["future"]
    assert f["greenfield"]["hv_yard_on"] and not gf["current"]["greenfield"]["hv_yard_on"]
    # future-ready greenfield lands inside the workbook band
    assert f["greenfield"]["band_check"] == "IN BAND", f["greenfield"]
    assert 15e6 < f["capex_per_mw"] < 30e6
    assert f["simple_payback"] and 1 < f["simple_payback"] < 10
    assert gf["upgrade"]["recommended"].startswith("Build future-ready")
    assert gf["upgrade"]["retrofit_owner_costs"] > 0
    assert gf["warnings"] == []


def test_greenfield_inputs_move_cost():
    base = _gf()["future"]["capex"]
    assert _gf(gf_land_cost_per_acre=2_000_000)["future"]["capex"] > base
    assert _gf(gf_contingency_pct=0.15)["future"]["capex"] > base
    assert _gf(gf_shell_per_gsf=500)["future"]["capex"] < base
    r = _gf(gf_utility_mw=10.0)
    assert any("utility service" in w for w in r["warnings"])
    r = _gf(gf_months_to_power=48)
    assert r["future"]["greenfield"]["schedule"]["critical_path"].startswith("Utility power")


def test_greenfield_all_options_and_payload():
    for cool in COOLING_TYPES:
        for reg in REGIONS:
            assert _gf(future_cooling=cool, region=reg)["future"]["capex"] > 0
    p = summary_for_llm(_gf())
    assert p["project_type"] == GREENFIELD
    assert "owner_costs_usd" in p["future_ready"] and "workbook_band_check" in p["future_ready"]
    txt = llm.fallback_narrative(_gf())
    for w in ["greenfield", "Interconnection queue", "Workbook benchmark check", "permitting"]:
        assert w in txt
    assert "Greenfield" in llm.SYSTEM_PROMPT


def test_workbook_basis():
    assert WB.benchmark(135)["right"] == WB.PLATFORMS["GB300 NVL72"]["right"]
    assert not WB.benchmark(15)["in_range"]
    for p in WB.PLATFORMS.values():
        assert abs(sum(p["csi_mix"].values()) - 1) < 1e-3
