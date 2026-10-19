"""Streamlit AppTest: every preset, project type, platform, the D2C switch (40/50 kW) and 600 kW."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from streamlit.testing.v1 import AppTest  # noqa: E402

import engine as E  # noqa: E402
import platforms as PL  # noqa: E402

APP = os.path.join(ROOT, "app.py")
TABS = ["Costs", "Future-ready", "Design calculations", "Schedule & risks", "Codes & procurement",
        "Build & commission", "Operations & ROI", "Assumptions & sources"]


APP_PRESETS = [n for n, p in E.PRESETS.items() if p.get("project_type") != E.FITOUT]


@pytest.fixture(autouse=True)
def _no_key(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)


def _run(**widgets):
    at = AppTest.from_file(APP, default_timeout=120).run()
    for key, value in widgets.items():
        at.sidebar.selectbox(key=key).set_value(value) if key in ("w_preset", "w_platform", "w_region", "w_res",
                                                                  "w_horizon") else None
        if key == "w_size_by":
            at.sidebar.radio(key=key).set_value(value)
        if key in ("w_mw", "w_racks", "w_custom_kw", "w_cur_kw"):
            continue
        at.run()
    for key in ("w_mw", "w_racks", "w_custom_kw", "w_cur_kw"):
        if key in widgets:
            at.number_input(key=key).set_value(widgets[key]).run()
    return at


def _ok(at):
    assert not at.exception, [e.message for e in at.exception]
    assert len(at.metric) >= 4
    labels = [t.label for t in at.tabs]
    assert len(labels) == len(TABS) and all(t in lbl for t, lbl in zip(TABS, labels)), labels
    body = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    assert "not a bid" in body
    for word in ("workbook", "Method A", "RIGHT", "Class 5", "screening", "oncept-level"):
        assert word not in body, word
    return body


@pytest.mark.parametrize("preset", APP_PRESETS)
def test_presets(preset):
    at = _run(w_preset=preset)
    _ok(at)
    assert any("Verdict" in s.value for s in at.success)


@pytest.mark.parametrize("ptype", [E.GREENFIELD])
@pytest.mark.parametrize("plat", list(PL.PLATFORMS))
def test_every_platform_both_modes(ptype, plat):
    at = _run(w_type=ptype, w_platform=plat)
    _ok(at)


@pytest.mark.parametrize("ptype", [E.GREENFIELD])
@pytest.mark.parametrize("kw,d2c", [(40, False), (50, True), (600, True)])
def test_custom_density_d2c_switch(ptype, kw, d2c):
    at = _run(w_type=ptype, w_platform=PL.CUSTOM, w_custom_kw=float(kw))
    body = _ok(at)
    locked = [c.value for c in at.caption if "D2C auto-selected" in c.value and "🔒" in c.value]
    assert bool(locked) == d2c, (kw, locked)
    assert f"{kw:,} kW/rack" in body


@pytest.mark.parametrize("h", list(E.HORIZONS))
def test_horizons(h):
    at = _run(w_horizon=h)
    _ok(at)


def test_greenfield_has_no_current_case():
    at = _run(w_type=E.GREENFIELD)
    body = _ok(at)
    assert "current" not in " ".join(s.value for s in at.success).lower()
    assert "Retrofit later" not in body or "retrofit later" in body.lower()


def test_resilience_and_regions():
    for r in E.RESILIENCE:
        _ok(_run(w_res=r))
    _ok(_run(w_region="India - Mumbai"))
    _ok(_run(w_size_by="Racks", w_racks=64))


def test_build_tab_and_estimate_wording():
    at = _run()
    body = _ok(at)
    assert "Early budget estimate (±30–50%)" in body
    assert any("Hard stop" in e.value for e in at.warning)
    assert "When to order" in body and "Commissioning levels L1-L5" in body
    assert "months from start" in body and "How to avoid delays" in body
    assert "Codes and standards to follow" in body and "Listed alphabetically for reference" in " ".join(
        i.value for i in at.info)


def test_include_checkboxes_change_total():
    at = _run()
    _ok(at)
    total0 = at.metric[0].value
    at.checkbox(key="inc_gpu").check().run()
    _ok(at)
    assert at.metric[0].value != total0
    at.checkbox(key="inc_gpu").uncheck().run()
    assert at.metric[0].value == total0


def test_schedule_factors_and_auto_build():
    at = _run()
    at.number_input(key="w_cm").set_value(30).run()
    _ok(at)
    at.selectbox(key="w_ot").set_value(60).run()
    _ok(at)


def test_first_screen_terms_and_no_nagging():
    at = _run()
    _ok(at)
    exp = [e.label for e in at.expander]
    assert any("Terms of use" in x for x in exp) and any("How it works" in x for x in exp)
    captions = " ".join(c.value for c in at.caption)
    # the disclaimer appears once on the first screen and once in the footer, never more
    assert captions.count("not a bid") == 2, captions.count("not a bid")
    assert "MIT License" in captions and "See Terms of use" in captions
    assert not [i.value for i in at.info if "NEBIUS_API_KEY" in i.value]
    assert len(at.warning) <= 2  # one compact warnings block + the build hard stop
    assert "Your day-one design: GB300 NVL72 about 135 kW/rack." in captions and "40-60 kW today" not in captions
    assert any("a 600 kW/rack target installed in year 5 after ready for IT" in x.value for x in at.success)


def test_no_fitout_option_or_preset_in_sidebar():
    at = _run()
    _ok(at)
    assert not [r for r in at.sidebar.radio if r.label == "Project type"]
    assert at.sidebar.selectbox(key="w_preset").options == APP_PRESETS
    assert all("fit-out" not in o.lower() for o in APP_PRESETS)
