"""Round 3: end-to-end cost checklist (ticked lines = total), wording, codes list, US procurement, delays."""
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import buildcx as CX
import codes as CD
import costlines as CL
import engine as E
import guide as G
import llm
import platforms as PL
import procurement as PR
import report as R

PRESETS = list(E.PRESETS)


def _cl(res):
    return R.cost_lines(res)


# ----------------------------------------------------------------- cost checklist
def test_defaults():
    off = {k for k, v in CL.DEFAULT_INCLUDE.items() if not v}
    assert off == {"onsite", "gpu", "fabric"}
    assert len(CL.KEYS) == 13


@pytest.mark.parametrize("pre", PRESETS)
def test_ticked_lines_always_sum_to_total(pre):
    rng = random.Random(7)
    for _ in range(25):
        inc = {k: rng.random() < 0.5 for k in CL.KEYS}
        res = E.run_model({**E.PRESETS[pre], "include": inc})
        cl = _cl(res)
        want = sum(r["amount"] for r in cl["rows"] if inc[r["key"]])
        assert cl["total"] == pytest.approx(want, abs=1e-6)
        h = R.headline(res)
        assert h["total"] == pytest.approx(want, abs=1e-6)
        assert h["per_mw"] == pytest.approx(want / h["it_mw"], rel=1e-12)
        if res["mode"] == "greenfield":
            d = res["design"]
            assert d["capex"] == pytest.approx(want) and abs(sum(d["lines"].values()) - d["capex"]) < 1


@pytest.mark.parametrize("pre", PRESETS)
def test_every_output_uses_the_checked_total(pre):
    inc = dict(CL.DEFAULT_INCLUDE, gpu=True, spares=False)
    res = E.run_model({**E.PRESETS[pre], "include": inc})
    total = _cl(res)["total"]
    assert E.summary_for_llm(res)["total_capex_usd"] == round(total)
    md = R.markdown_report(res)
    assert R.money(total) in md
    assert R.money(total) in llm.fallback_narrative(res)
    ct = R.cost_table(res)
    assert ct.loc[ct["Cost line"] == "Total project cost (ticked lines)", "$M"].iloc[0] == pytest.approx(total / 1e6)
    pdf = R.pdf_report(res)
    assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1


def test_greenfield_carve_adds_back_to_facility():
    for pre in PRESETS[:2]:
        res = E.run_model(E.PRESETS[pre])
        d = res["design"]
        cv = d["cost_lines"]["carve"]
        carved = sum(cv[k] for k in ("site", "fiber", "security", "commissioning", "design", "racks", "substation",
                                     "contingency", "core"))
        assert carved == pytest.approx(d["cost"]["facility"], rel=1e-12)
        assert all(cv[k] >= 0 for k in cv)
        # default total = previous facility-based total + new lines (spares; racks only for HGX-type platforms)
        amt = {r["key"]: r["amount"] for r in d["cost_lines"]["rows"]}
        assert d["capex"] == pytest.approx(d["construction_basis"] + amt["spares"] + cv["racks_new"], rel=1e-12)


def test_fitout_regroup_adds_back_to_construction():
    res = E.run_model(E.PRESETS[PRESETS[2]])
    f = res["future"]
    amt = {r["key"]: r["amount"] for r in res["cost_lines"]["rows"]}
    regrouped = sum(amt[k] for k in ("facility", "fiber", "racks", "security", "design", "commissioning", "contingency"))
    assert regrouped == pytest.approx(f["construction_cost"], rel=1e-9)
    assert amt["land"] == 0


@pytest.mark.parametrize("name", list(PL.PLATFORMS))
def test_network_fabric_and_fiber_priced_within_public_ranges(name):
    p = PL.platform(name)
    assert 0.08 <= CL.fabric_share(p) <= 0.20          # networking about 8-20% of cluster cost
    assert 2_000 <= CL.fabric_per_gpu(p) <= 20_000      # several optics at about $1,000 each plus switches/NICs


def test_lines_present_and_positive():
    for pre in PRESETS:
        cl = _cl(E.run_model(E.PRESETS[pre]))
        amt = {r["key"]: r["amount"] for r in cl["rows"]}
        for k in ("facility", "interconnect", "onsite", "gpu", "fabric", "fiber", "racks", "security", "design",
                  "commissioning", "contingency", "spares"):
            assert amt[k] > 0, (pre, k)


def test_roi_counts_ticked_it():
    base = E.run_model({**E.PRESETS[PRESETS[0]], "include_it": False})
    ticked = E.run_model({**E.PRESETS[PRESETS[0]], "include_it": False, "include": {"gpu": True}})
    assert base["design"]["it_total"] == 0
    assert ticked["design"]["it_total"] == pytest.approx(ticked["design"]["it_hw"])


# ----------------------------------------------------------------- wording and dates
WORDS = re.compile(r"concept|screening|class 5|aace|based on these codes", re.I)


@pytest.mark.parametrize("pre", PRESETS)
def test_no_banned_wording_or_calendar_dates(pre):
    res = E.run_model(E.PRESETS[pre])
    S = res["cx"]["schedule"]
    for k in ("sc_date", "ntp_date", "start"):
        assert k not in S
    for x in S["items"]:
        assert not any(k.endswith("_date") for k in x)
    ob = R.order_by_table(res)
    assert not any("date" in c.lower() for c in ob.columns)
    assert all(re.fullmatch(r"Order it \d[\d,]* months before you need it", v) for v in ob["Order ahead"])
    assert re.fullmatch(r"about \d+(–\d+)? months from start", S["range_text"])
    assert S["sc_low"] <= S["sc"] <= S["sc_high"]
    text = "\n".join([R.markdown_report(res), llm.fallback_narrative(res), CX.ESTIMATE_LABEL, str(E.summary_for_llm(res))]
                     + [p["phase"] for p in S["phases"]] + [c for _g, _n, c in CX.STAGE_GATES])
    m = WORDS.search(text)
    assert m is None, text[max(0, m.start() - 60): m.end() + 60]
    md = re.sub(r"Generated 20\d\d-\d\d-\d\d", "", R.markdown_report(res))   # report stamp only
    assert not re.search(r"\b20[2-3]\d-\d\d-\d\d\b", md)
    assert not re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|"
                         r"December) 20[2-3]\d\b", "\n".join(r["Basis"] for _, r in ob.iterrows()))


def test_official_event_name():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in ("app.py", "README.md", "report.py", "llm.py", "ui_views.py", "guide.py", "SAMPLE_INPUTS.md",
              "docs/VERIFICATION.md"):
        assert "Build Week" not in open(os.path.join(root, f), encoding="utf-8").read(), f
    assert "Nebius x NVIDIA Global AI Hackathon" in open(os.path.join(root, "app.py"), encoding="utf-8").read()
