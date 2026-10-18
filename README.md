# ⚡ RackReady AI: Data Center Cost Modeling Agent

**Live demo:** https://rackready-ai.streamlit.app


**Build for 15 kW racks today or 140 kW racks tomorrow? RackReady AI prices both, and NVIDIA Nemotron explains the decision.**

Built for the **Nebius x NVIDIA Build Week** hackathon (2026).

![RackReady AI headline cards](docs/hero.png)

RackReady AI models construction CapEx, the future-ready upgrade path, OpEx and ROI for
high-density AI data center halls. It compares a **current** build (e.g. 15 kW/rack, air) with a
**future-ready** build (e.g. 140 kW/rack, D2C liquid) for the same hall, or prices **one greenfield
new build from scratch** calibrated to the owner's 8-platform cost workbook.

> All figures are **indicative planning numbers** (2026 USD, Northern Virginia = 1.00), not a bid or estimate of record.

## Why
GPU racks like NVIDIA GB200/GB300 NVL72 draw roughly 120-140 kW, about 10x a traditional rack.
Air cooling tops out near 30 kW/rack, so a hall built for today can need an expensive live-site
retrofit within a few years. Owners, developers and contractors have to make that call early,
with little data. RackReady AI gives them transparent numbers in seconds.

## How it works
1. **Deterministic cost engine** (`engine.py`). This always runs, even without an API key. Unit rates live in one
   commented `ASSUMPTIONS` dict: $/kW IT by CSI division (Div 26 electrical, Div 23 mechanical,
   Div 21 fire, Div 27 networking, Div 03/05/09 structure), plus per-rack items and location, tier and
   redundancy multipliers, soft costs and contingency. From these it computes OpEx (energy via PUE,
   maintenance, staffing), GPU rental revenue, simple payback, NPV, and a
   *future-ready day one* vs *build current + retrofit* comparison.
2. **AI narrative** (`llm.py`). The engine output goes as JSON to an **NVIDIA Nemotron** model on
   **Nebius Token Factory**, using the OpenAI-compatible API with streaming. A domain system prompt casts the model as a
   senior data center cost manager. It writes the executive summary, assumptions commentary,
   upgrade-path recommendation, key risks and next steps, and it is told **never to change the engine's numbers**.
   Reasoning blocks are stripped from the stream.
3. **Graceful fallback.** If the key is missing or the call fails (auth, rate limit, network), a
   rule-based narrative is shown instead, so the app never breaks.

## How NVIDIA Nemotron and Nebius Token Factory are used
- **Model.** The default model is **`nvidia/Nemotron-3.5-Super-VL`**, called through **Nebius Token Factory's
  OpenAI-compatible endpoint** `https://api.tokenfactory.nebius.com/v1/` with the standard OpenAI Python SDK.
  Other selectable Nemotron models are listed in `SUGGESTED_MODELS` in [`llm.py`](llm.py)
  (`nvidia/Nemotron-3-Ultra-550b-a55b`, `nvidia/Nemotron-3_5-Lightning`, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`),
  and any other model id can be typed in the sidebar.
- **Division of labour.** The deterministic engine (`engine.py`) owns every number. Nemotron receives the
  engine output as JSON and writes only the narrative (executive summary, assumptions commentary, upgrade-path
  recommendation, key risks, next steps). The system prompt casts it as a senior data center cost manager and
  forbids it from inventing, recomputing or changing any figure.
- **Streaming.** Output is streamed (`stream=True`) so the report appears as it is written.
- **Reasoning stripped.** Nemotron is a reasoning model; any `<think>...</think>` block is removed from the
  stream before display, so users only see the final answer.
- **Rule-based fallback.** With no key, or on an auth, rate-limit, timeout or network error, a rule-based
  narrative built from the same engine numbers is shown, so the app never breaks.
- **What we learned about `max_tokens`.** A reasoning model spends tokens thinking before it answers. With a
  small limit, the first live run came back blank because the budget ran out during reasoning. Raising
  `max_tokens` to **16000** fixed it; the live run for the default 200-rack hall then took **about 11 seconds**.
- **Where Token Factory sped up the workflow.** Serverless, pay-per-token access meant no GPU instances to
  provision, no model hosting and no new SDK: one API key and a base URL change gave us several Nemotron sizes
  to try from the same code path.
- **Other Nebius tools.** None beyond Token Factory; no Nebius GPU instances or fine-tuning were used.

### Example result: existing-building fit-out (defaults)
200 racks · Northern Virginia · 15 → 140 kW/rack · Air → **D2C liquid (auto above 45 kW/rack)** · Tier III · N+1 · $0.08/kWh · 80% utilization

| Metric | Current | Future-ready |
|---|---|---|
| IT load | 3.0 MW | 28.0 MW |
| Cooling | Air | Direct-to-chip (D2C), 19 CDUs (N+1, 1.6 MW) |
| Total CapEx | $37.6M | $350.2M |
| CapEx per MW IT | $12.5M | $12.5M |
| Annual OpEx | $4.8M | $31.0M |
| Simple payback | 3.7 yrs | 3.6 yrs |

Building current now and retrofitting in year 3 costs **$500.7M** including 4 months of downtime,
a **$150.5M penalty**, so the engine recommends building future-ready on day one
(NPV $630.5M over 10 years at 8%). Indicative planning numbers, not a bid.

### Greenfield: one new build from scratch, calibrated to the owner's workbook
Pick **Project type → Greenfield** for a single design (no "current" case, no retrofit path). Choose a
GPU platform from the cost workbook *AI Rack Research: The Right Estimate* (H100, H200, B200, GB200,
GB300, Vera Rubin, TPU Ironwood, Kyber) or a custom kW/rack, and size it by IT MW (default 100 MW,
the workbook campus) or by racks. The engine (`run_greenfield` in `engine.py`, data in `workbook_basis.py`):

- prices facility $ = workbook **RIGHT $/IT MW** (03_SIDE8 r8) × IT MW, split into the **22 CSI
  divisions** of 20_CSI8_MATRIX; kW/rack, GPUs/rack, IT $/rack, GSF/MW, PUE and CDU MW come from 01_ASSUME8;
- counts N+1 machines the workbook way: gens = ROUNDUP(IT × PUE / 3) + 1, UPS ≈ 1.1 × IT MW modules,
  CDUs = ROUNDUP(IT MW / CDU MW) + 1, taps = 2 × racks;
- prices changes with 12_CHANGE_PRICING (N+2, 2N gens, 2N UPS, 96 h fuel, union/seismic/piles,
  contingency, IT fit-out): machines × unit + 13% soft on the delta;
- adds what the workbook keeps outside facility $: land ($5M) and utility-side interconnect ($8M)
  screens (01_ASSUME8 r78-79), IT iron (r9) and optional AI fabric (14_EIGHT_DEEP r47) in ROI;
- shows a **reconciliation table** back to the workbook's own totals, the LOW / RIGHT / HIGH band,
  all 8 platforms at the same MW, the 11_SPEC_MOVES scope sheet, OpEx, payback and a schedule
  (power-real + 6 months, 90-week transformers, design + construction).

| 100 MW IT greenfield | GB300 NVL72 | H100 HGX | Vera Rubin |
|---|---|---|---|
| kW/rack · racks · cooling | 135 · 741 · D2C (auto) | 41 · 2,439 · RDHx / air | 220 · 455 · D2C (auto) |
| Facility $ (= workbook 03_SIDE8 r9) | $1,916.3M | $1,700.0M | $2,163.1M |
| Facility $/MW IT · band check | $19.2M · IN BAND | $17.0M · IN BAND | $21.6M · IN BAND |
| Greenfield CapEx (+ land + interconnect) | $1,929.3M | $1,713.0M | $2,176.1M |
| ALL-IN facility + IT + adders (= 03_SIDE8 r16) | $4,892.2M | $3,908.1M | $6,039.8M |
| Simple payback (indicative $/GPU-hr) | 3.3 yrs | 3.5 yrs | 4.1 yrs |

App totals match the workbook to the dollar at workbook defaults; differences only appear when you turn
on changes, a location factor, owner costs or escalation (all shown as reconciliation lines).

### Cooling rule
Every design above **45 kW/rack** uses **direct-to-chip (D2C) liquid**, auto-selected and locked in the
sidebar ("D2C auto-selected above 45 kW/rack"). At or below 45 kW you choose air, rear-door hybrid or D2C.

See a live Nemotron narrative in [`docs/sample_nemotron_narrative.md`](docs/sample_nemotron_narrative.md).

## Screenshots

| | |
|---|---|
| **1 · Assumptions**: every unit rate and multiplier<br>![Assumptions](docs/demo_tab1.png) | **2 · CapEx**: by system and CSI division<br>![CapEx](docs/demo_tab2.png) |
| **3 · Future-ready upgrade**: day one vs retrofit<br>![Upgrade](docs/demo_tab3.png) | **4 · OpEx**: energy, maintenance, staffing, PUE impact<br>![OpEx](docs/demo_tab4.png) |
| **5 · Revenue & ROI**: revenue, payback, NPV<br>![ROI](docs/demo_tab5.png) | **6 · Comparison**: current vs future-ready<br>![Comparison](docs/demo_tab6.png) |
| **7 · Risks & recommendations**: long-lead equipment and the narrative (shown here with the offline fallback)<br>![Risks](docs/demo_tab7.png) | |

## Features
- Project type: **existing building fit-out** (current vs future-ready + retrofit path) or
  **greenfield new build from scratch** (one design, priced from the owner's 8-platform cost workbook).
- Inputs: racks, current and future kW/rack, 3 cooling types (air, hybrid rear-door, direct-to-chip D2C,
  auto-selected above 45 kW/rack), 8 regions with location factors, $/kWh, utilization, analysis horizon,
  Tier II/III/IV, N/N+1/2N, and GPUs per rack and $/GPU-hr for revenue.
- 4 headline cards and 7 report tabs with tables, Plotly charts and expanders.
- Cooling rule: D2C is auto-selected above 45 kW/rack in every mode; the app warns when air is pushed past ~30 kW.
- Downloads: the full report as Markdown and all tables as a CSV zip.
- A "How it works" expander explains the domain in plain language.

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
The app opens at http://localhost:8501. You can also paste a key into **🤖 AI settings** in the sidebar.
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

## Tuning the model
Edit `ASSUMPTIONS` in `engine.py`. Every rate is commented, and the Assumptions tab shows the live values.
Greenfield values come from `workbook_basis.py`; the few indicative greenfield inputs the workbook
lacks (months to power, construction months, $/GPU-hr, insurance) are in `ASSUMPTIONS["greenfield"]`.
`SAMPLE_INPUTS.md` has demo scenarios (NoVA, Dallas, Singapore Tier IV 2N, and a greenfield build) with expected results.

## Project structure
```
rackready_ai/
├── app.py                       # Streamlit UI (cards, 7 tabs, downloads)
├── engine.py                    # ASSUMPTIONS + deterministic cost engine
├── llm.py                       # Nebius/Nemotron client, system prompt, fallback narrative
├── workbook_basis.py            # values extracted from the owner's cost workbook (sheet/row cited)
├── ui_common.py / ui_fitout.py / ui_greenfield.py   # tab layouts per project type
├── requirements.txt
├── LICENSE                      # MIT
├── .streamlit/config.toml       # dark theme
├── .streamlit/secrets.toml.example
├── SAMPLE_INPUTS.md             # demo scenarios + 60-second script
├── docs/                        # screenshots + sample Nemotron narrative
└── tests/test_rackready.py      # engine + fallback unit tests (pytest)
```

## Tests
```bash
pip install pytest
python -m pytest -q tests
```

## Tech stack
Python · Streamlit · pandas · Plotly · OpenAI Python SDK · Nebius Token Factory · NVIDIA Nemotron · pytest

## Disclaimer
RackReady AI is an early-stage planning tool. Unit rates are indicative 2026 benchmarks, not quotes.
Validate against local pricing and a qualified estimator before making investment decisions.

## License
[MIT](LICENSE) © 2026 Kosha Solanki
