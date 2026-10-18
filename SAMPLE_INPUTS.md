# Sample inputs & demo script

All numbers below come from the built-in engine at default `ASSUMPTIONS` (indicative, 2026 USD).

## Scenario 1 (default): 200-rack AI hall, Northern Virginia
These are the app defaults, so you only need to click **Run cost model**.

| Input | Value |
|---|---|
| Racks | 200 |
| Current kW/rack → future | 15 → 140 |
| Cooling current → future | Air → D2C liquid (auto-selected above 45 kW/rack) |
| Region | US - Northern Virginia (1.00) |
| Power cost | $0.08/kWh |
| Utilization | 80% |
| Tier / redundancy | Tier III / N+1 |
| GPUs/rack, $/GPU-hr (current) | 8 at $2.50 (HGX H100-class) |
| GPUs/rack, $/GPU-hr (future) | 72 at $3.50 (GB200/GB300 NVL72-class) |
| Horizon | 10 years |

Expected headline: CapEx **$37.6M → $350.2M** (3 MW → 28 MW IT), **$12.5M → $12.5M per MW**,
future annual OpEx **$31.0M**, payback **3.7 → 3.6 yrs**, 19 CDUs (N+1, 1.6 MW). Build-current-then-retrofit
costs about **$500.7M** including downtime, so the engine recommends **future-ready on day one**.

## Scenario 2: mid-density colo upgrade, Dallas
Racks 100 · 12 → 80 kW · Air → D2C liquid (auto) · US - Dallas / Texas · $0.06/kWh · 70% ·
Tier III N+1 · GPUs 8 at $2.25 → 32 at $3.00.
Expected: CapEx $14.7M → $96.4M ($12.3M → $12.1M/MW), future payback ≈ 5.3 yrs, retrofit path ≈ $141.0M.

## Scenario 3: premium Tier IV 2N, Singapore
Racks 200 · 20 → 140 kW · Air → D2C liquid (auto) · Singapore (1.15) · $0.18/kWh · 85% ·
Tier IV · 2N. Expected: CapEx $75.8M → $570.0M ($19.0M → $20.4M/MW), future OpEx ≈ $63.4M/yr,
payback 6.8 → 4.4 yrs. This shows how tier, redundancy and location stack up.

## Scenario 4: greenfield, one new build from scratch (workbook-calibrated)
Select **Project type → Greenfield: new build from scratch**. There is no "current" case: you price
one design. Defaults: platform **GB300 NVL72** (the workbook's 2026 GMP reference), size by **100 MW IT**
(workbook campus), N+1, contingency 4%, land $5M and utility-side interconnect $8M (workbook screens),
24 months to power, NoVA 1.00.

Expected: 741 racks × 135 kW, 53,333 GPUs, **D2C auto-selected**, 41 × 3 MW gens, 110 UPS modules,
64 CDUs, 260,000 gsf. Facility **$1,916.3M = $19.2M/MW IT = workbook RIGHT (IN BAND)**; greenfield
CapEx **$1,929.3M** with land + interconnect; ALL-IN with IT iron **$4,892.2M = 03_SIDE8 r16**.
OpEx $119.5M/yr, payback **3.3 yrs**, ~30 months to ready-for-service (power-real + 6 months).

| Try | Expected |
|---|---|
| Platform H100 HGX (41 kW, RDHx / air) | Facility $1,700.0M ($17.0M/MW), 2,439 racks, payback 3.5 yrs |
| Platform Vera Rubin (220 kW) | Facility $2,163.1M ($21.6M/MW), 455 racks, payback 4.1 yrs |
| Size by racks = 200 (GB300) | 27 MW IT, facility $517.4M, CapEx $530.4M |
| Redundancy 2N gens + 2N UPS, contingency 8% | +$200.5M (C2) +$73.2M (C3) +$67.8M (C12) → CapEx $2,270.9M |
| Custom 40 kW vs 50 kW | 40 kW keeps your cooling choice; 50 kW locks to D2C |

## "Gotcha" check (good for Q&A)
Set current kW/rack to **50**: the cooling selector locks to **D2C** ("D2C auto-selected above 45
kW/rack"). Set it to **40** with **Air**: the app warns that air tops out around 30 kW/rack.

## Suggested prompt (what the agent sends Nemotron)
The app sends the engine's JSON with a system prompt casting the model as a senior data center
cost manager. If you want to try it by hand in the Nebius playground:
> "Using only these engine numbers, write an executive summary, assumptions commentary,
> upgrade-path recommendation (day-one future-ready vs retrofit), key risks (long-lead
> transformers/switchgear/CDUs, power availability, slab loading, commissioning L1-L5) and next
> steps for a 200-rack AI hall going from 15 kW air to 140 kW D2C liquid in Northern Virginia."

## 60-second demo script
1. **(0-10s)** "AI racks went from 15 kW to 140 kW. Owners have to decide: build for today, or
   build future-ready? RackReady AI answers that in one click."
2. **(10-20s)** Point at the sidebar defaults (200 racks, NoVA, D2C auto above 45 kW) and click
   **Run cost model**. Read the cards: $37.6M vs $350.2M, $12.5M per MW for both.
3. **(20-30s)** **CapEx tab**: "Div 26 electrical and Div 23 mechanical are two-thirds of the cost.
   CDUs and liquid piping are the new money."
4. **(30-40s)** **Future-ready upgrade tab**: "Retrofitting later costs ~$501M vs $350M day one,
   because of the live-site premium, demolition and four months of downtime."
5. **(40-50s)** **Risks tab**: "The deterministic engine does the math, and NVIDIA Nemotron on
   Nebius Token Factory writes the narrative as a senior cost manager: long-lead transformers,
   power availability, slab loading."
6. **(50-60s)** Click **Download report**. "A cost manager gets a defensible first-pass model in
   minutes instead of days."
