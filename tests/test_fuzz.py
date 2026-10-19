"""Fuzz test: every project type x platform x redundancy x horizon, plus seeded random edge inputs (min/max
sizes, densities, prices, schedule factors, random tick-box choices). No exceptions, no NaN/inf, no negative
cost lines, ticked lines add up to the total, schedule range brackets the central case, one-page PDF stays
one page."""
import itertools
import math
import os
import random
import re
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import costlines as CL  # noqa: E402
import engine as E  # noqa: E402
import llm  # noqa: E402
import platforms as PL  # noqa: E402
import report as R  # noqa: E402

PLATS = list(PL.PLATFORMS) + [PL.CUSTOM]


def _floats(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _floats(v, f"{path}.{k}")
    elif isinstance(x, (list, tuple)):
        for n, v in enumerate(x):
            yield from _floats(v, f"{path}[{n}]")
    elif isinstance(x, float):
        yield path, x


def _check(inp, deep=False):
    r = E.run_model(inp)
    bad = [p for p, v in _floats(r) if not math.isfinite(v)]
    assert not bad, (bad[:5], inp)
    cl = R.cost_lines(r)
    assert all(row["amount"] >= 0 for row in cl["rows"]), inp
    ticked = sum(row["amount"] for row in cl["rows"] if cl["include"][row["key"]])
    assert abs(ticked - cl["total"]) <= 1, inp
    h = R.headline(r)
    assert h["it_mw"] > 0 and h["total"] >= 0 and h["total_all"] >= h["total"] - 1, inp
    S = r["cx"]["schedule"]
    assert S["sc_low"] <= S["sc"] + 1e-9 <= S["sc_high"] + 1e-6, inp
    assert all(ph["dur"] >= -1e-9 for ph in S["phases"]), inp
    if deep:
        for k, df in R.all_tables(r).items():
            if k == "design":
                continue
            for c in df.columns:
                assert not (pd.api.types.is_numeric_dtype(df[c]) and df[c].isna().any()), (k, c, inp)
        md = R.markdown_report(r)
        assert " nan " not in md and "| nan" not in md
        pdf = R.pdf_report(r)
        assert len(re.findall(rb"/Type\s*/Page[^s]", pdf)) == 1, inp
        assert R.checklist_pdf(r)[:4] == b"%PDF"
        assert "nan" not in llm.fallback_narrative(r).lower().split()
        E.summary_for_llm(r)


@pytest.mark.parametrize("ptype", E.PROJECT_TYPES)
def test_every_platform_mode_redundancy_horizon(ptype):
    for n, (plat, res_, hz) in enumerate(itertools.product(PLATS, list(E.RESILIENCE), list(E.HORIZONS))):
        _check({"project_type": ptype, "platform": plat, "resilience": res_, "horizon": hz}, deep=(n % 9 == 0))


def test_random_edge_inputs():
    rng = random.Random(1)
    for n in range(150):
        inp = {"project_type": rng.choice(E.PROJECT_TYPES), "platform": rng.choice(PLATS),
               "resilience": rng.choice(list(E.RESILIENCE)), "horizon": rng.choice(list(E.HORIZONS)),
               "region": rng.choice(E.REGION_NAMES), "size_by": rng.choice(["IT MW", "Racks"]),
               "it_mw": rng.choice([0.5, 1, 3.3, 50, 250, 999, 2000]), "racks": rng.choice([1, 2, 7, 200, 5000, 50000]),
               "custom_kw": rng.choice([5, 30, 45, 45.1, 46, 300, 1500]),
               "cooling": rng.choice(["Air", "Hybrid (rear-door + air)", "Direct-to-chip (D2C) liquid", None]),
               "current_kw": rng.choice([3, 15, 45, 60]),
               "current_cooling": rng.choice(["Air", "Hybrid (rear-door + air)"]),
               "utilization": rng.choice([0.3, 1.0]), "years": rng.choice([3, 20]),
               "gpu_price": rng.choice([None, 0.25, 60]), "power_cost": rng.choice([None, 0.005, 0.5]),
               "price_change": rng.choice([-0.25, 0.05]), "contingency": rng.choice([0, 0.25]),
               "owner_pct": rng.choice([0, 0.1]), "escalation": rng.choice([0, 0.12]),
               "land_per_acre": rng.choice([None, 50e6]), "months_to_power": rng.choice([6, 120]),
               "design_months": rng.choice([2, 36]), "construction_months": rng.choice([None, 1, 60]),
               "fitout_build_months": rng.choice([None, 1, 36]), "overtime_hours": rng.choice([40, 70]),
               "weather_factor": rng.choice([0, 0.3]), "congestion_factor": rng.choice([0, 0.3]),
               "fuel_hours": rng.choice([4, 168]), "battery_min": rng.choice([1, 30]),
               "voltage": rng.choice([415.0, 480.0]), "tcs_dT": rng.choice([5, 20]),
               "future_kw": rng.choice([None, 10, 2000]), "future_year": rng.choice([None, 1, 20]),
               "future_probability": rng.choice([0.1, 1.0]), "spare_utility_pct": rng.choice([0, 1.0]),
               "overhead_pct": rng.choice([0, 0.4]), "include_it": rng.choice([True, False]),
               "include": {k: rng.random() < 0.5 for k in CL.KEYS},
               "current_gpus": rng.choice([0, 72]), "current_gpu_price": rng.choice([0.0, 20.0])}
        _check(inp, deep=(n % 6 == 0))
