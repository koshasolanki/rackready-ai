# RackReady AI: compliance check

Final check of the repository and the live app, October 2026. ✅ = pass, ⚠️ = pass with an action for the
submitter. Re-run the commands below before each release.

## 1. Hackathon rules (Nebius x NVIDIA Global AI Hackathon, Devpost rules page)

| Rule | Status | Evidence |
|---|---|---|
| Runtime calls to Nebius Token Factory | ✅ | `llm.py`: OpenAI SDK, base URL `https://api.tokenfactory.nebius.com/v1/`, streamed chat completion on every narrative request |
| Uses an NVIDIA open model | ✅ | Default `nvidia/Nemotron-3.5-Super-VL`; other Nemotron models selectable (`SUGGESTED_MODELS`) |
| Live app has the key configured | ⚠️ | The narrative header reads "Rule-based narrative (add a Nebius key...)" when no key is set. Keep `NEBIUS_API_KEY` in the Streamlit Cloud secrets until judging ends |
| Original work, built for the event | ✅ | All code and text in this repository; no copied code. Open-source libraries used under their licenses (section 3) |
| Public repository with an open-source license | ✅ | Public on GitHub; `LICENSE` is MIT and GitHub detects it |
| README with setup and Nemotron / Token Factory usage | ✅ | README: "Try it" (setup) and "How it works" (Nemotron and Token Factory) |
| Free to test until judging ends | ✅ | Live app needs no login; the rule-based narrative works without a key |
| Demo video under 3 minutes, no third-party trademarks or copyrighted music without permission | ⚠️ | Not in this repo. Use no music or royalty-free music you have rights to, show no third-party logos, and keep the supplier table off screen (supplier names are third-party trademarks) |
| Submission deadline 30 Oct 2026, 10:00 am PT | ⚠️ | Submitted on Devpost by the submitter |

## 2. Trademarks

| Check | Status |
|---|---|
| NVIDIA, Nebius, GB300, Vera Rubin, Nemotron and supplier names used only to identify products (nominative use) | ✅ |
| Trademark notice in the app footer, Terms of use, README, PDFs and Markdown report | ✅ |
| "Not affiliated with or endorsed by" stated | ✅ |
| No logos, brand colours copied as logos, or "official" wording | ✅ (the green accent is a theme colour, no logo is drawn) |
| Suppliers listed alphabetically, no ranking, no "top/best" wording, disclaimer shown with the table | ✅ |

## 3. Dependency licenses

| Package | License | Use | Status |
|---|---|---|---|
| streamlit | Apache-2.0 | UI | ✅ |
| openai (Python SDK) | Apache-2.0 | Token Factory client | ✅ |
| pandas | BSD-3-Clause | tables | ✅ |
| numpy (via pandas) | BSD-3-Clause | maths | ✅ |
| plotly | MIT | charts | ✅ |
| tabulate | MIT | Markdown tables | ✅ |
| fpdf2 | LGPL-3.0-or-later | PDF export; installed from PyPI unmodified, not bundled or vendored | ✅ |

All are permissive or used as unmodified, separately installed libraries, compatible with the MIT license of this code.

## 4. Images, logos and fonts

| Check | Status |
|---|---|
| Images in the repo: four screenshots of this app (`docs/*.png`) | ✅ own work |
| Third-party images, logos or icons | ✅ none (emoji are Unicode characters rendered by the user's system) |
| Font files | ✅ none; the app uses the browser's sans-serif font and the PDFs use the PDF core Helvetica (not embedded) |

## 5. Privacy

| Check | Status |
|---|---|
| Personal data collected | ✅ none; no accounts, no forms beyond the model inputs |
| Analytics or tracking | ✅ none in the code; `browser.gatherUsageStats = false` in `.streamlit/config.toml` |
| Storage | ✅ inputs and narratives live only in the session's memory; nothing is written to disk or a database |
| Data sent to third parties | ✅ only when a key is configured: project inputs and computed results go to Token Factory for the narrative (stated in the Terms of use) |
| Users' or third parties' private files in the repo | ✅ none; research notes stay in a gitignored folder that has never been committed |

## 6. Accessibility

| Check | Status |
|---|---|
| Text contrast (WCAG 2.1 AA needs 4.5:1) | ✅ body #E6EDF3 on #0E1117 = 16.0:1; accent #76B900 on #0E1117 = 7.8:1; badges #76B900 on #1F2A12 = 6.2:1; sub-title #9AA4B2 = 7.5:1; chart grey #8A8F98 = 5.8:1 |
| Every input has a visible label and a tooltip | ✅ native Streamlit widgets; checkboxes use their cost-line name as the label |
| Images in the README have alt text | ✅ |
| Colour is never the only signal | ✅ the best future path is also marked "Best" / "›"; critical drivers show a ✓ |
| Works on mobile | ✅ checked at 390 px wide |

## 7. Security

| Check | Status | How |
|---|---|---|
| No secrets in the working tree | ✅ | only `.streamlit/secrets.toml.example` with a placeholder |
| No secrets anywhere in the git history | ✅ | `git log -p --all` scanned for API-key assignments, `sk-`, JWT, GitHub, AWS and Slack token patterns and private-key headers: only the placeholder `your-key-here` matched |
| Secret files ignored | ✅ | `.gitignore`: `secrets.toml`, `.streamlit/secrets.toml`, `.env` |
| The key is never displayed or logged | ✅ | sidebar field is a password input; errors are mapped to plain messages without the key |
| Model output cannot inject HTML | ✅ | narrative rendered as Markdown with HTML escaped |

Re-run the history scan (prints counts only, never values):

```bash
for p in 'sk-[A-Za-z0-9]{20,}' 'ghp_[A-Za-z0-9]{20,}' 'AKIA[0-9A-Z]{16}' 'BEGIN (RSA|OPENSSH|EC|PRIVATE)'; do
  printf '%s: ' "$p"; git log -p --all | grep -cE "$p"; done
```

## 8. Citations and claims

| Check | Status |
|---|---|
| Every number has a value, a range and a source or an "assumption" label | ✅ `docs/VERIFICATION.md` |
| The app cites sources by type (e.g. "2026 procurement surveys"); full links are in VERIFICATION.md | ✅ |
| Company names appear only in the US procurement supplier table, each backed by a public source | ✅ |
| No people's names in the app or its outputs | ✅ (the copyright line in LICENSE names the author, as the MIT license requires) |
| Roadmap platforms marked announced, estimate or speculative | ✅ |
| No calendar completion dates; timing is in months from start | ✅ |
| Estimate described as an early budget estimate (±30–50%), not a bid, with a licensed engineer and AHJ review | ✅ once on the first screen, in the footer, the Terms and every export |

## 9. Terms of use

`TERMS.md` (also in the app under **📄 Terms of use**, linked from the footer): as-is with no warranty; not
engineering, legal or financial advice; licensed engineer and AHJ review; estimates have a range; no liability;
data handling; trademarks; supplier list for reference only; MIT license; governing law. A test keeps TERMS.md
identical to the in-app text.

## Open items for the submitter

1. Keep `NEBIUS_API_KEY` set in the Streamlit Cloud secrets until judging ends, so judges see Nemotron output.
2. Demo video: no copyrighted music, no third-party logos, keep the supplier table off screen, stay under 3 minutes.
3. Submit on Devpost before 30 Oct 2026, 10:00 am PT.
