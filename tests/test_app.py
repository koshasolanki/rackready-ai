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
TABS = ["Costs", "Future-ready", "Design calculations", "Operations & ROI", "Schedule & risks", "Build & commission",
        "Assumptions & sources"]


@pytest.fixture(autouse=True)
def _no_key(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)


def _run(**widgets):
    at = AppTest.from_file(APP, default_timeout=120).run()
    for key, value in widgets.items():
        at.sidebar.selectbox(key=key).set_value(value) if key in ("w_preset", "w_platform", "w_region", "w_res",
                                                                  "w_horizon") else None
        if key in ("w_type", "w_size_by"):
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
    for t in TABS:
        assert any(t in lbl for lbl in labels), (t, labels)
    body = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    assert "not a bid" in body
    for word in ("workbook", "Method A", "RIGHT"):
        assert word not in body
    return body


@pytest.mark.parametrize("preset", list(E.PRESETS))
def test_presets(preset):
    at = _run(w_preset=preset)
    _ok(at)
    assert any("Recommendation" in s.value for s in at.success)


@pytest.mark.parametrize("ptype", E.PROJECT_TYPES)
@pytest.mark.parametrize("plat", list(PL.PLATFORMS))
def test_every_platform_both_modes(ptype, plat):
    at = _run(w_type=ptype, w_platform=plat)
    _ok(at)


@pytest.mark.parametrize("ptype", E.PROJECT_TYPES)
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


def test_build_tab_and_estimate_class():
    at = _run()
    body = _ok(at)
    assert "Class 5" in body
    assert any("Hard stop" in e.value for e in at.error)
    assert "Order-by dates" in body and "Commissioning levels L1-L5" in body


def test_schedule_factors_and_auto_build():
    at = _run()
    at.number_input(key="w_cm").set_value(30).run()
    _ok(at)
    at.selectbox(key="w_ot").set_value(60).run()
    _ok(at)
