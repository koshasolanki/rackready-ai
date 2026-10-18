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
