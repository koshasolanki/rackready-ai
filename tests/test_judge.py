"""Judge-feedback items: Start here guide, why-Nemotron line, limitations section, plain wording."""
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from streamlit.testing.v1 import AppTest  # noqa: E402

import guide as G  # noqa: E402
import llm  # noqa: E402

BANNED = re.compile(r"concept|screening|class 5|aace|based on these codes", re.I)


def _read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(autouse=True)
def _no_key(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)


def test_start_here_on_first_screen_and_spinner():
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=120).run()
    assert not at.exception
    body = " ".join(m.value for m in at.markdown)
    assert "Start here:" in body and "pick a preset" in body
    first = [m.value for m in at.main.markdown][:4]
    assert any("Start here:" in v for v in first), first          # sits under the title, above the results
    src = _read("app.py")
    assert 'st.spinner("Calculating design, costs and schedule..."' in src
    assert "_il.reload(_m)" in src                                 # hot-redeploy reload block kept


def test_why_nemotron_line_names_the_real_model():
    line = G.ai_purpose(llm.DEFAULT_MODEL)
    assert llm.DEFAULT_MODEL in line and "Nebius Token Factory" in line
    assert "never to change a number" in line and "rule-based" in line
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=120).run()
    assert any("Why Nemotron:" in c.value and llm.DEFAULT_MODEL in c.value for c in at.caption)
    assert "Why Nemotron." in _read("README.md")


def test_limitations_section():
    readme = _read("README.md")
    assert "## Limitations and what's next" in readme
    for line in G.LIMITATIONS + G.NEXT_STEPS:
        assert line in readme, line
    text = " ".join(G.LIMITATIONS).lower()
    for phrase in ("±30–50%", "not site quotes", "us only", "interconnection", "month ranges", "ahj",
                   "ai text can be wrong", "licensed engineer"):
        assert phrase.lower() in text, phrase
    assert "data center construction cost professional" in readme


def test_new_text_is_plain():
    new = " ".join([G.START_HERE, G.ai_purpose(llm.DEFAULT_MODEL)] + G.LIMITATIONS + G.NEXT_STEPS)
    assert not BANNED.search(new)
    assert not re.search(r"\b20[2-3]\d-\d\d-\d\d\b", new)
    assert not re.search(r"(January|February|March|April|May|June|July|August|September|October|November|"
                         r"December) 20[2-3]\d", new)
    assert not BANNED.search(_read("README.md"))
