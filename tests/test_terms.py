"""Terms of use: TERMS.md matches the in-app text and covers every required point."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import guide as G  # noqa: E402


def test_terms_md_matches_app():
    with open(os.path.join(ROOT, "TERMS.md"), encoding="utf-8") as f:
        assert f.read() == G.terms_markdown()


def test_terms_cover_required_points():
    t = G.terms_markdown().lower()
    for phrase in ("as is", "without warranty", "not engineering, legal, financial", "licensed professional engineer",
                   "authority having jurisdiction", "±30–50%", "not liable", "not saved", "only if an api key",
                   "no analytics", "trademarks", "no affiliation", "alphabetically", "reference only", "mit license",
                   "governed by"):
        assert phrase in t, phrase
    assert "inc." not in t and "llc" not in t and "ltd" not in t  # no invented company entity
