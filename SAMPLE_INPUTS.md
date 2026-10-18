# Sample inputs & demo script

All numbers below come from the built-in engine at default `ASSUMPTIONS` (indicative, 2026 USD).

## Scenario 1 (default): 200-rack AI hall, Northern Virginia
These are the app defaults, so you only need to click **Run cost model**.

| Input | Value |
|---|---|
| Racks | 200 |
| Current kW/rack → future | 15 → 140 |
| Cooling current → future | Air → Closed-loop full liquid |
| Region | US - Northern Virginia (1.00) |
| Power cost | $0.08/kWh |
| Utilization | 80% |
| Tier / redundancy | Tier III / N+1 |
| GPUs/rack, $/GPU-hr (current) | 8 at $2.50 (HGX H100-class) |
| GPUs/rack, $/GPU-hr (future) | 72 at $3.50 (GB200/GB300 NVL72-class) |
| Horizon | 10 years |

Expected headline: CapEx **$37.6M → $384.4M** (3 MW → 28 MW IT), **$12.5M → $13.7M per MW**,
future annual OpEx **$31.1M**, payback **3.7 → 3.2 yrs**. Build-current-then-retrofit costs about
**$546.9M** including downtime, so the engine recommends **future-ready on day one**.

## Scenario 2: mid-density colo upgrade, Dallas
Racks 100 · 12 → 80 kW · Air → Direct-to-chip liquid · US - Dallas / Texas · $0.06/kWh · 70% ·
Tier III N+1 · GPUs 8 at $2.25 → 32 at $3.00.
Expected: CapEx $14.7M → $98.4M (about $12.3M/MW both), future payback ≈ 4.8 yrs, retrofit path ≈ $143.7M.

## Scenario 3: premium Tier IV 2N, Singapore
Racks 200 · 20 → 140 kW · Air → Closed-loop full liquid · Singapore (1.15) · $0.18/kWh · 85% ·
Tier IV · 2N. Expected: CapEx $75.8M → $623.9M ($19.0M → $22.3M/MW), future OpEx ≈ $62.9M/yr,
payback 6.8 → 4.1 yrs. This shows how tier, redundancy and location stack up.

## Scenario 4: greenfield, build from scratch (same 200-rack hall)
Select **Project type → Greenfield: new build from scratch** and keep every other default
(land $400k/acre, site acres and utility MW auto, interconnect $3.0M + $50k/MW, 24 months to power,
shell & core $/gsf from the workbook, 18-month construction, design/permits 7%, contingency 8%,
escalation 4%/yr).

Expected: greenfield CapEx **$60.2M → $613.3M** incl. land (**$20.1M → $21.9M per MW IT**).
Future-ready build-up: land $5.6M (14.0 acres), site & civil $30.6M, shell & core $135.3M
($1,504/gsf), HV substation & yard $11.3M, utility interconnection $4.6M (32.2 MW), soft costs
$72.9M, contingency $42.3M, escalation $32.0M. Workbook-comparable facility cost **$18.6M/MW IT,
IN BAND** ($18.4M / $19.3M / $25.2M low / right / high). Future OpEx $36.6M/yr (adds property
tax, insurance, grounds), payback **4.8 → 4.0 yrs**, ~30 months to ready-for-service with
transformers on the critical path. Build-current-then-retrofit ≈ **$896.6M**, so build future-ready
on day one. Try 48 months to power: the critical path flips to the utility.

## "Gotcha" check (good for Q&A)
Set future cooling to **Air** at 140 kW. The app warns that air tops out around 30 kW/rack. The
domain guardrail catches a design that looks cheaper on paper but can't work.

## Suggested prompt (what the agent sends Nemotron)
The app sends the engine's JSON with a system prompt casting the model as a senior data center
cost manager. If you want to try it by hand in the Nebius playground:
> "Using only these engine numbers, write an executive summary, assumptions commentary,
> upgrade-path recommendation (day-one future-ready vs retrofit), key risks (long-lead
> transformers/switchgear/CDUs, power availability, slab loading, commissioning L1-L5) and next
> steps for a 200-rack AI hall going from 15 kW air to 140 kW closed-loop liquid in Northern Virginia."

## 60-second demo script
1. **(0-10s)** "AI racks went from 15 kW to 140 kW. Owners have to decide: build for today, or
   build future-ready? RackReady AI answers that in one click."
2. **(10-20s)** Point at the sidebar defaults (200 racks, NoVA, closed-loop liquid) and click
   **Run cost model**. Read the cards: $37.6M vs $384.4M, $12.5M vs $13.7M per MW.
3. **(20-30s)** **CapEx tab**: "Div 26 electrical and Div 23 mechanical are two-thirds of the cost.
   CDUs and liquid piping are the new money."
4. **(30-40s)** **Future-ready upgrade tab**: "Retrofitting later costs ~$547M vs $384M day one,
   because of the live-site premium, demolition and four months of downtime."
5. **(40-50s)** **Risks tab**: "The deterministic engine does the math, and NVIDIA Nemotron on
   Nebius Token Factory writes the narrative as a senior cost manager: long-lead transformers,
   power availability, slab loading."
6. **(50-60s)** Click **Download report**. "A cost manager gets a defensible first-pass model in
   minutes instead of days."
