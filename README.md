# ⚡ RackReady AI: Data Center Cost and Design Model for AI Racks

**Live demo:** https://rackready-ai.streamlit.app

**Build for 135 kW racks today and 600 kW racks tomorrow? RackReady AI designs the facility, prices it, tests it
against public benchmarks, and NVIDIA Nemotron explains the decision.**

Built for the **Nebius x NVIDIA Build Week** hackathon (2026).

![RackReady AI summary](docs/hero.png)

RackReady AI is a planning tool for owners, developers and contractors of high-density AI data centers. Pick a
project type, a size, a GPU platform, a location and a redundancy level. In seconds you get:

- a **one-screen summary**: total cost, cost per MW, payback, ready-for-service date and a recommendation;
- **design calculations** with formulas and inputs: utility MVA, transformers, generators and fuel, UPS and
  batteries, busway current, cooling tons, CDUs, coolant flows, heat rejection, water, floor loading and land;
- a **future-ready horizon** (5, 10 or 15 years) that prices retrofit later vs provisions now vs full future build;
- **benchmark checks** against public 2025-2026 data (JLL, Cushman & Wakefield, Turner & Townsend, Uptime
  Institute, EIA, Wood Mackenzie, NVIDIA/OEM specs);
- exports: **one-page PDF**, full Markdown report with every calculation, and CSV tables.

> All figures are an **indicative planning estimate, not a bid** (2026 US dollars, Northern Virginia = 1.00).

## Why
NVIDIA GB300 NVL72 racks draw about 135 kW, roughly 10x a traditional rack. Vera Rubin (2H 2026) and Rubin Ultra
"Kyber" (about 600 kW, 2H 2027) push further, and MW-class racks will need 800 VDC power. A hall built for today can
need an expensive live-site retrofit within a few years. Owners have to decide early what to build in now.

## Using the app
**Sidebar (short):** preset · project type · size (IT MW or racks) · GPU platform · location · redundancy (N, N+1,
N+2, 2N with Tier-style labels) · future-proof horizon. Everything else is under **Advanced** (cooling choice up
to 45 kW/rack, the existing hall's racks, GPU rental price, power price, utilization, contingency, escalation, land,
schedule, fuel hours, battery minutes, voltage, liquid-loop temperature rise and horizon settings). Every input
has a tooltip and results update as you type.

**Presets:** 100 MW AI campus (greenfield, GB300 NVL72) · 10 MW edge AI hall (greenfield, H200 HGX) ·
existing-hall fit-out (200 racks, 15 kW to GB300).

**Tabs:** Costs · Future-ready · Design calculations · Operations & ROI · Schedule & risks · Assumptions & sources.

**Project types.**
- *Greenfield* is one new build from scratch, with no "current" case. The facility is priced from a cost per MW of
  IT for the platform, split across 22 construction divisions, then adjusted for redundancy (from the designed
  generator, UPS and transformer counts), contingency, location, owner costs and escalation. Land, utility
  interconnection and IT hardware are shown separately.
- *Existing building fit-out* compares keeping today's racks with a future-ready fit-out in the same hall, and with
  retrofitting later.

**Cooling rule.** Air cooling tops out near 30 kW/rack and rear-door heat exchangers near 45 kW/rack. Above
45 kW/rack every design, in every mode, uses **direct-to-chip (D2C) liquid cooling**, selected automatically.

### Future-ready horizon
| Horizon | Target | Status |
|---|---|---|
| 5 years | 230 kW/rack (Vera Rubin NVL144 class) | announced |
| 10 years | 600 kW/rack (Rubin Ultra NVL576 / Kyber, 800 VDC) | announced |
| 15 years | 1,000 kW/rack | speculative |

The model designs the hall again at the target density (same IT MW plus optional spare utility capacity), works out
the upgrade cost by division, and compares three paths on present cost: **retrofit later** (1.35x live-site premium,
demolition, 4 months of lost margin), **provisions now** (pre-install structure, slab, site, pipe headers, pathways
and pads; finish later at 1.10x with 1 month of lost margin) and **full future build on day one** (with upkeep on idle
capacity). Later works are escalated, discounted and weighted by the probability that the target is deployed. It lists
the provisions to build in (floor loading, liquid headers, busway pathways, rack bay, 800 VDC space at 400 kW and above,
spare utility capacity, heat-rejection yard).

![Future-ready tab](docs/future_ready.png)

### Design calculations (default 100 MW GB300 NVL72 campus, N+1)
| Step | Formula | Result |
|---|---|---|
| IT load | 741 racks x 135 kW | 100.0 MW |
| Facility peak | IT / UPS efficiency + losses + design-day cooling + house | 129.1 MW |
| Annual PUE | 1/0.97 + 0.015 + 0.13 + 0.025 (energy ratio) | 1.20 |
| Utility service | 129.1 MW x 1.15 reserve / PF 0.95 | 156 MVA, 3 x 80 MVA transformers (N+1) |
| Generators and fuel | ceil(129.1 / 3 MW) = 44, +6 (N+1); 48 h x 0.070 gal/kWh | 50 x 3 MW; 434,000 gal (1,642 m3) |
| UPS and battery | 103 MW critical load; 5 min / 0.96 / 0.80 | 129 x 1 MW modules; 11,176 kWh |
| Rack feed | I = 155 kW / (sqrt3 x 415 V x 0.99) | 218 A |
| Row busway | 10 racks: 2,178 A x 1.25 | 3,000 A busway |
| Cooling | 105.6 MW / 3.517 | 30,024 tons; 90 MW to liquid, 67 CDUs (1.6 MW, N+1) |
| Liquid flow | Q = 90 MW / (1017 x 3.93 x 10 K) | 2,252 L/s (35,691 gpm) |
| Heat rejection | Q + compressor work | 108.2 MW |
| Water | WUE 0.20 L/kWh (dry/adiabatic) | 140,160 m3/yr (37 M gal) |
| Floor | 3,500 lb on a 0.6 x 1.068 m rack | 507 psf (24.3 kPa) on the footprint |
| Building and land | 2,600 sf per MW; 35% site coverage | 260,000 sf; 26.2 acres |

![Design calculations tab](docs/design_calcs.png)

### Example results (presets, default inputs)
| Preset | Design | Total cost | Per MW IT | IT hardware | Payback | Recommendation |
|---|---|---|---|---|---|---|
| 100 MW AI campus | GB300 NVL72, 741 racks, D2C, PUE 1.20 | $2.28B | $22.8M | $3.46B | 3.1 years | Build today + future-ready provisions (10-year horizon) |
| 10 MW edge AI hall | H200 HGX, 239 racks, rear-door hybrid, PUE 1.35 | $181.3M | $18.1M | $340.7M | 6.7 years | Build today + future-ready provisions (5-year horizon) |
| Existing-hall fit-out | 200 racks, 15 kW air to GB300 D2C | $352.1M | $13.0M | $800.0M | 2.2 years | Fit out future-ready now |

### Verification
Every number, its range and its source is listed in [docs/VERIFICATION.md](docs/VERIFICATION.md). The tests check the
physics (MVA >= MW/PF, tons = kW/3.517, Q = P/(rho cp dT), I = P/(sqrt3 V PF), rejection >= load), the public ranges
($10-15M/MW air, $15-25M+/MW high density, PUE 1.1-1.5, US power $0.06-0.12/kWh, transformer lead time 1-2+ years,
GPU rental within each platform's market range), the D2C switch at 40/50 kW and a 600 kW case. Anything without a
public source is labelled as an assumption in the app.

## How NVIDIA Nemotron and Nebius Token Factory are used
- **Model.** The default model is **`nvidia/Nemotron-3.5-Super-VL`**, called through **Nebius Token Factory's
  OpenAI-compatible endpoint** `https://api.tokenfactory.nebius.com/v1/` with the standard OpenAI Python SDK.
  Other selectable Nemotron models are listed in `SUGGESTED_MODELS` in [`llm.py`](llm.py)
  (`nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/Nemotron-3_5-Lightning`, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`),
  and any other model id can be typed in the sidebar.
- **Division of labour.** The deterministic engine (`engine.py`) owns every number. Nemotron receives the
  engine output as JSON and writes only the narrative (executive summary, assumptions commentary, design and upgrade
  recommendation, key risks, next steps). The system prompt casts it as a senior data center cost manager and
  forbids it from inventing, recomputing or changing any figure.
- **Streaming.** Output is streamed (`stream=True`) so the report appears as it is written.
- **Reasoning stripped.** Nemotron is a reasoning model; any `<think>...</think>` block is removed from the
  stream before display, so users only see the final answer.
- **Rule-based fallback.** With no key, or on an auth, rate-limit, timeout or network error, a rule-based
  narrative built from the same engine numbers is shown, so the app never breaks.
- **What we learned about `max_tokens`.** A reasoning model spends tokens thinking before it answers. With a
  small limit, the first live run came back blank because the budget ran out during reasoning. Raising
  `max_tokens` to **16000** fixed it; the live run for the default case then took **about 11 seconds**.
- **Where Token Factory sped up the workflow.** Serverless, pay-per-token access meant no GPU instances to
  provision, no model hosting and no new SDK: one API key and a base URL change gave us several Nemotron sizes
  to try from the same code path.
- **Other Nebius tools.** None beyond Token Factory; no Nebius GPU instances or fine-tuning were used.

#
## Setup (quick start)
Requires Python 3.10+ (tested on 3.13).
```bash
git clone https://github.com/koshasolanki/rackready-ai.git rackready_ai && cd rackready_ai
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# Optional, for the Nemotron narrative (otherwise the rule-based narrative is used)
export NEBIUS_API_KEY="your-key-here"
# or: cp .streamlit/secrets.toml.example .streamlit/secrets.toml  and edit it

streamlit run app.py
```
The app opens at http://localhost:8501. You can also paste a key into **🤖 AI narrative settings** in the sidebar.
Get a key from Nebius Token Factory: **API keys → Create API key**.

The key is looked up in this order: env `NEBIUS_API_KEY`, then `st.secrets["NEBIUS_API_KEY"]`, then the sidebar field.
Never commit `.streamlit/secrets.toml`; it is in `.gitignore`.

## Switching endpoint / model
- **Sidebar → 🤖 AI settings**: edit *Base URL* and pick a model, or choose *Custom...* and type any model id.
- Or set env vars before launching:
  ```bash
  export NEBIUS_BASE_URL="https://api.tokenfactory.nebius.com/v1/"
  export NEBIUS_MODEL="nvidia/Nemotron-3-Ultra-550b-a55b"
  ```
- Defaults: base URL `https://api.tokenfactory.nebius.com/v1/`, model `nvidia/Nemotron-3.5-Super-VL`.
  To list the Nemotron models your account can use:
  ```bash
  curl -s https://api.tokenfactory.nebius.com/v1/models -H "Authorization: Bearer $NEBIUS_API_KEY" \
    | python3 -m json.tool | grep '"id"' | grep -i nemotron
  ```
- Any OpenAI-compatible endpoint works (e.g. NVIDIA NIM `https://integrate.api.nvidia.com/v1`).


## Project structure
```
rackready_ai/
├── app.py            # Streamlit UI: sidebar, summary, tabs, downloads
├── platforms.py      # GPU platform specs, cost basis per MW, division mix
├── design.py         # step-by-step design calculations (power, cooling, water, space)
├── engine.py         # costs, future-ready paths, OpEx/ROI, schedule, checks, presets
├── report.py         # tables, Markdown report, one-page PDF (fpdf2)
├── llm.py            # Nebius / Nemotron client, prompt, rule-based fallback
├── ui_views.py       # tab layouts;  ui_common.py  # shared helpers
├── docs/VERIFICATION.md  # numbers, ranges, public sources
├── SAMPLE_INPUTS.md  # demo scenarios and expected results
└── tests/            # pytest: engine + physics + ranges, and Streamlit AppTest for every mode
```

## Tests
```bash
pip install pytest
python -m pytest -q tests
```

## Tech stack
Python · Streamlit · pandas · Plotly · fpdf2 · OpenAI Python SDK · Nebius Token Factory · NVIDIA Nemotron · pytest

## Disclaimer
RackReady AI is an early-stage planning tool. Rates are indicative 2026 benchmarks, not quotes. Roadmap platforms
(Vera Rubin, Kyber, 1 MW racks) are estimates. Validate against local pricing, OEM data and a qualified estimator and
engineer before making investment decisions.

## License
[MIT](LICENSE) © 2026 Kosha Solanki
