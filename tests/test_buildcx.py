"""Build & commission, schedule and the round-2 design calculations: hand-checked against the codes."""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import buildcx as CX
import design as DS
import engine as E
import llm
import procurement as PR
import report as R

GB = E.PRESETS[E.DEFAULT_PRESET]


@pytest.fixture(scope="module")
def res():
    return E.run_model(GB)


@pytest.fixture(scope="module")
def v(res):
    return res["design"]["design"]["v"]


@pytest.fixture(scope="module")
def p(res):
    return res["design"]["design"]["params"]


# ----------------------------------------------------------------- fire protection (NFPA 13 / 20 / 22 / 2001)
def test_sprinkler_demand_oh1_double_interlock(v):
    assert v["spk_area_sf"] == pytest.approx(1950)               # 1,500 sf + 30% (double-interlock pre-action)
    assert v["spk_gpm"] == pytest.approx(292.5)                  # 0.15 gpm/sf x 1,950 sf
    assert v["fire_total_gpm"] == pytest.approx(542.5)           # + 250 gpm hose
    assert v["fire_pump_gpm"] == 750                             # next NFPA 20 rating above 542.5
    assert v["fire_tank_gal"] == pytest.approx(542.5 * 60)       # 60 min supervised
    assert v["spk_heads"] == math.ceil(v["white_sf"] / 130)


def test_clean_agent_nfpa2001(v, p):
    s = 0.9856 + 0.002441 * 70
    assert s == pytest.approx(1.1565, abs=1e-4)
    vol = p["agent_room_sf"] * p["agent_room_ft"]
    assert v["agent_lb"] == pytest.approx(vol / s * 4.2 / (100 - 4.2), rel=1e-9)
    # hand example: 10,000 ft3 at 4.2% and 70 F -> about 379 lb
    assert 10_000 / s * 4.2 / 95.8 == pytest.approx(379.1, abs=0.5)


# ----------------------------------------------------------------- electrical
def test_mv_current_and_switchgear(v, p):
    i_svc = v["service_mva"] * 1e6 / (math.sqrt(3) * 34.5e3)
    assert v["mv_amps"] == pytest.approx(i_svc, rel=1e-9)
    i_tx = p["main_tx_mva"] * 1e6 / (math.sqrt(3) * 34.5e3)     # 80 MVA at 34.5 kV = 1,339 A
    assert i_tx == pytest.approx(1339, abs=1)
    assert v["mv_bus_a"] == 2000                                  # 1.25 x 1,339 = 1,674 -> 2,000 A
    small = E.run_model({"it_mw": 10.0, "platform": "H200 HGX"})["design"]["design"]
    assert not small["onsite_hv"] and "15 kV" in next(s for s in small["steps"] if s["key"] == "mv_bus_a")["si"]


def test_ab_rack_each_side_carries_whole_rack(v, p, res):
    kw_peak = res["design"]["platform"]["kw_peak"]
    assert v["ab_side_kva"] == pytest.approx(kw_peak / p["pf_rack"])
    assert 2 * 45 / 2 < 50 / 0.99                                 # two 45 kVA feeds cannot carry a 50 kW rack alone
    step = next(s for s in res["design"]["design"]["steps"] if s["key"] == "ab_side_kva")
    brk = int(re.search(r"-> (\d+) A", step["si"]).group(1))
    assert brk in DS.BRANCH_A and brk >= 1.25 * v["rack_amps"]


def test_busway_loading_at_most_80_percent():
    for name in E.PRESETS:
        r = E.run_model(E.PRESETS[name])
        dz = r["design"]["design"] if r["mode"] == "greenfield" else r["future"]["design"]
        if dz["v"]["busway_rating"]:
            assert dz["v"]["busway_loading"] <= 80.0 + 1e-6


def test_generator_and_fuel_notes(res):
    steps = {s["key"]: s for s in res["design"]["design"]["steps"]}
    assert "Sized on kW" in steps["gens"]["note"]
    assert "2N+1" in steps["main_tx"]["note"] and "N+1" in steps["main_tx"]["note"]   # names the correction
    assert "100,000 gal lasts about" in steps["fuel_gal"]["note"]


# ----------------------------------------------------------------- mechanical
def test_us_unit_airflow_and_chw(v, p):
    q_air = v["air_kw"]
    assert v["air_cfm_us"] == pytest.approx(q_air * 3412.14 / (1.08 * p["air_dT"] * 1.8), rel=1e-9)
    # SI and US agree within 2% (1.08 is standard air)
    si_cfm = q_air / (1.2 * 1.006 * p["air_dT"]) * 2118.88
    assert v["air_cfm_us"] == pytest.approx(si_cfm, rel=0.02)
    assert v["chw_gpm_us"] == pytest.approx(v["chw_lps"] * DS.GPM_PER_LPS, rel=0.01)
    # textbook: 500 tons at 10 F -> 1,200 gpm
    assert 500 * 24 / 10 == 1200


def test_thermal_storage(v, p):
    q_chw = v["chw_lps"] / 1000 * p["w_rho"] * p["w_cp"] * p["chw_dT"]
    assert v["tes_m3"] == pytest.approx(q_chw * 600 / (p["w_rho"] * p["w_cp"] * p["chw_dT"] * 0.9), rel=1e-6)


def test_tower_make_up(v, p):
    tons = v["reject_kw"] / DS.KW_PER_TON
    per100 = v["tower_evap_gpm"] / (tons / 100)
    assert 2.2 <= per100 <= 2.5                                    # physics: about 2.3-2.4 gpm / 100 tons rejected
    assert v["tower_makeup_gpm"] == pytest.approx(v["tower_evap_gpm"] * 5 / 4)   # CoC 5
    assert 2.8 <= v["tower_makeup_gpm"] / (tons / 100) <= 3.1


# ----------------------------------------------------------------- water and site
def test_domestic_water_hunter():
    assert DS.hunter_gpm(30) == pytest.approx(23.3)
    assert DS.hunter_gpm(100) == pytest.approx(43.5)
    assert DS.hunter_gpm(25) < DS.hunter_gpm(26) < DS.hunter_gpm(30)


def test_stormwater_rational(v, p):
    a = v["land_acres"]
    c_post = 0.95 * 0.60 + 0.30 * 0.40
    assert c_post == pytest.approx(0.69)
    assert v["storm_q_cfs"] == pytest.approx(c_post * 3.0 * a, rel=1e-9)
    det = (c_post - 0.30) * 3.0 * a * 3600 / 43_560
    assert v["detention_acft"] == pytest.approx(det, rel=1e-9)


def test_fiber_counts(v, res):
    racks = res["design"]["racks"]
    assert v["fiber_per_rack"] == pytest.approx(72 * 16 * 1.25)
    assert v["fiber_backbone"] == racks * 72 * 16
    assert v["entrance_diversity"] == 2


# ----------------------------------------------------------------- schedule and order-by dates
def test_auto_build_months():
    assert CX.auto_build_months(100, True) == pytest.approx(24)
    assert CX.auto_build_months(10, True) == pytest.approx(12 + 12 * math.sqrt(0.1))
    assert CX.auto_build_months(5000, True) == 40 and 12 <= CX.auto_build_months(0.1, True) < 12.5
    assert CX.auto_build_months(100, False) == pytest.approx(14)


def test_overtime_factor():
    assert CX.overtime_factor(40) == 1.0
    assert CX.overtime_factor(60) == pytest.approx(40 / (60 * 0.875))
    assert CX.overtime_factor(70) < CX.overtime_factor(60) < CX.overtime_factor(50) < 1


def test_schedule_consistency(res):
    S = res["cx"]["schedule"]
    assert 0 < S["ntp"] < S["energization"] < S["cx_start"] < S["sc"] < S["final"]
    assert res["design"]["schedule"] is S and S["months_to_rfs"] == S["sc"]
    assert S["mid_point_months"] == pytest.approx(S["ntp"] + S["build_months"] / 2)
    assert S["critical_path"] in S["drivers"] and max(S["drivers"].values()) == pytest.approx(S["sc"], abs=0.01)
    assert R.headline(res)["rfs"] == S["sc"]
    assert any("Site" in p["phase"] for p in S["phases"])


def test_order_by_reverse_schedule(res):
    S = res["cx"]["schedule"]
    for x in S["items"]:
        chain = CX.PRE_PO_WEEKS + CX.SUBMITTAL_WEEKS + x["lead_typ"] + CX.PROCUREMENT["staging"]
        buf = CX.PROCUREMENT["buffer_pct"] * (CX.SUBMITTAL_WEEKS + x["lead_typ"])
        assert x["rfq"] == pytest.approx(x["need"] - (chain + buf) / CX.WEEKS_PER_MONTH, abs=1e-9)
        assert x["po"] == pytest.approx(x["rfq"] + CX.PRE_PO_WEEKS / CX.WEEKS_PER_MONTH)
        if x["rfq"] < 0:
            assert not x["flag"].startswith(("After", "Order before"))
        elif x["po"] < S["ntp"]:
            assert x["flag"] == "Order before NTP"
    tx = next(x for x in S["items"] if x["key"] == "main_tx")
    assert tx["flag"].startswith("Critical")                       # 100 MW: transformers set the date


def test_fitout_skips_site_work_and_factors_move_dates():
    f = E.run_model(E.PRESETS["Existing-hall fit-out (200 racks, 15 kW -> GB300)"])["cx"]["schedule"]
    assert not any(p["phase"].startswith("Site") for p in f["phases"])
    base = CX.schedule(it_mw=100, greenfield=True, design_months=9, build_months=None, months_to_power=None,
                       onsite_hv=False, d2c=True)
    wet = CX.schedule(it_mw=100, greenfield=True, design_months=9, build_months=None, months_to_power=None,
                      onsite_hv=False, d2c=True, weather=0.2, congestion=0.2)
    ot = CX.schedule(it_mw=100, greenfield=True, design_months=9, build_months=None, months_to_power=None,
                     onsite_hv=False, d2c=True, overtime_hours=60)

    def dur(s, name):
        return next(p["dur"] for p in s["phases"] if p["phase"].startswith(name))
    assert dur(wet, "Commissioning") > dur(base, "Commissioning")
    assert dur(ot, "Commissioning") == pytest.approx(dur(base, "Commissioning"))   # Cx does not compress
    assert dur(ot, "MEP") < dur(base, "MEP")
    big = CX.schedule(it_mw=300, greenfield=True, design_months=9, build_months=None, months_to_power=None,
                      onsite_hv=True, d2c=True)
    assert big["build_months"] > base["build_months"]


def test_lead_times_current():
    lt = {k: (lo, hi, t) for k, _n, lo, hi, t, _b in CX.LEAD_TIMES}
    assert lt["main_tx"][2] == 128 and lt["main_tx"][0] >= 100
    assert 62 <= lt["gens"][0] and lt["gens"][1] <= 110
    assert lt["mv_swgr_38"] [:2] == (78, 104) and lt["mv_swgr_15"][:2] == (52, 80)
    for lo, hi, t in lt.values():
        assert lo <= t <= hi


def test_risk_register_auto_enabled(res):
    act = {r["category"] for r in res["cx"]["risks"] if r["active"]}
    assert {"Liquid-loop leaks and cleanliness", "Long-lead equipment", "Utility interconnection"} <= act
    assert "Bridging power availability" not in act                  # 36 months to power
    late = E.run_model({**GB, "months_to_power": 60})
    assert "Bridging power availability" in {r["category"] for r in late["cx"]["risks"] if r["active"]}
    for r in res["cx"]["risks"]:
        assert 0 <= r["impact_low"] <= r["impact_high"] and r["owner"] and r["mitigation"]
        assert "probab" not in str(r).lower()


# ----------------------------------------------------------------- commissioning content
def test_commissioning_content(res):
    assert [c["level"] for c in CX.CX_LEVELS] == ["L1", "L2", "L3", "L4", "L5"]
    assert "Substantial completion follows a passed IST" in CX.CX_LEVELS[-1]["exit"]
    assert len(CX.FEEDS) == 10 and len(CX.IT_READINESS) == 30
    for f in CX.FEEDS:
        assert all(f[k] for k in ("scope", "spec", "test", "failure", "prevention"))
    lb = res["cx"]["load_banks"]
    assert lb["halls"] == 4 and lb["liquid_mw"] == pytest.approx(25 * 0.9)
    assert any("2-hour full-load test" in n for n in lb["notes"])
    assert [g for g, _n, _c in CX.STAGE_GATES] == [f"G{n}" for n in range(8)]
    spec = " ".join(" ".join(r) for r in CX.SPEC_REFERENCE)
    assert "at least 1 h after hot work" in spec and "8 h" in spec and "24 h" in spec
    assert "N+1, not '2N+1'" in CX.GLOSSARY["N, N+1, 2N"]


def test_provisions_have_reasons(res):
    prov = res["future"]["provisions"]
    assert len(prov) >= 10 and all(x["why"] for x in prov)
    assert any(x["provision"] == "800 VDC readiness" for x in prov)


def test_estimate_wording_and_labels(res):
    assert CX.ESTIMATE_LABEL.startswith("Early budget estimate (±30–50%)")
    assert not hasattr(CX, "AACE_CLASSES")
    assert E.RESILIENCE["N"].startswith("N (Tier I-style")


# ----------------------------------------------------------------- exports and wording
@pytest.mark.parametrize("pre", list(E.PRESETS))
def test_exports_include_build_tables(pre):
    r = E.run_model(E.PRESETS[pre])
    t = R.all_tables(r)
    for k in ("order_by", "gantt", "risks", "cx_levels", "ist_scenarios", "handoff_feeds", "it_readiness",
              "checklists", "stage_gates", "spec_reference", "codes_and_standards", "confirm_locally",
              "us_procurement", "procurement_suppliers", "delays_and_fixes", "how_it_works"):
        assert k in t and len(t[k]) > 0, k
    pdf = R.checklist_pdf(r)
    assert pdf[:4] == b"%PDF" and len(re.findall(rb"/Type\s*/Page[^s]", pdf)) >= 3
    md = R.markdown_report(r)
    assert "## Build & commission" in md and "When to order" in md and "Early budget estimate" in md
    for banned in ("Class 5", "AACE", "concept", "screening", "based on these codes"):
        assert banned.lower() not in md.lower(), banned


NAMES = re.compile(r"\b(JLL|Cushman|Wakefield|Turner & Townsend|Uptime Institute|Wood Mackenzie|Schneider|Vertiv|"
                   r"Eaton|Caterpillar|Cummins|Siemens|ABB|Supermicro|Lenovo|HPE|Novec|FM-200|Chemours|CBRE|Trane|"
                   r"Kohler|Mitsubishi|Hitachi|Procore|Primavera|P6)\b")


PROC_TABLES = ("us_procurement", "procurement_suppliers")


def _strip_procurement(md: str) -> str:
    """Supplier names are allowed only in the US procurement section."""
    a = md.find("## US procurement")
    b = md.find("\n## ", a + 5)
    return md if a < 0 else md[:a] + (md[b:] if b > 0 else "")


@pytest.mark.parametrize("pre", list(E.PRESETS))
def test_no_company_names_in_outputs(pre):
    r = E.run_model(E.PRESETS[pre])
    parts = [_strip_procurement(R.markdown_report(r)), llm.fallback_narrative(r), llm.SYSTEM_PROMPT,
             str(E.summary_for_llm(r))]
    parts += [df.to_csv(index=False) for k, df in R.all_tables(r).items() if k not in PROC_TABLES]
    text = "\n".join(parts)
    m = NAMES.search(text)
    assert m is None, text[max(0, m.start() - 80): m.end() + 80]
    supplier_names = re.compile("|".join(r"\b" + re.escape(n) + r"(?![\w])" for n in PR.S))
    m = supplier_names.search(text)
    assert m is None, text[max(0, m.start() - 80): m.end() + 80]


def test_names_only_in_procurement():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    supplier_names = re.compile("|".join(r"\b" + re.escape(n) + r"(?![\w])" for n in PR.S))
    for f in ("README.md", "SAMPLE_INPUTS.md", "docs/VERIFICATION.md", "buildcx.py", "design.py", "engine.py",
              "platforms.py", "ui_views.py", "report.py", "llm.py", "app.py", "codes.py", "costlines.py", "guide.py"):
        text = open(os.path.join(root, f), encoding="utf-8").read()
        if f == "docs/VERIFICATION.md":
            text = _strip_procurement(text)
        for rx in (NAMES, supplier_names):
            m = rx.search(text)
            assert m is None, (f, m.group(0))


def test_llm_payload_has_schedule_and_risks(res):
    pl = E.summary_for_llm(res)
    assert pl["schedule"]["substantial_completion_month"] == pytest.approx(res["cx"]["schedule"]["sc"], abs=0.05)
    assert pl["schedule"]["order_by"] and pl["risk_register"] and "±30–50%" in pl["estimate_accuracy"]
    assert pl["schedule"]["ready_for_it"].endswith("months from start")
    import json
    json.dumps(pl)
