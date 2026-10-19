# RackReady AI: verification of numbers

Every number the model uses, its value, the range it must sit in, and the public source or the reason it is
an assumption. The automated tests (`tests/test_rackready.py`) enforce the ranges and the physics.
**Early budget estimate (±30–50%), not a bid.** Prices are 2026 US dollars. Not engineering, legal or financial
advice: a licensed professional engineer and the authority having jurisdiction (AHJ) must review any design.

Status: **Verified** = matches a public 2025-2026 source. **Derived** = computed from verified inputs with a
standard formula. **Assumption** = planning judgement with no single public source; you can change it.

## 1. GPU platforms (rack level)

| Platform | Value used | Public range / spec | Status | Source |
|---|---|---|---|---|
| H100 / H200 HGX (4 x 8-GPU servers) | 41-42 kW/rack, 32 GPUs | about 10.2 kW per 8-GPU server | Verified | NVIDIA DGX H100/H200 datasheets |
| B200 HGX (4 x 8-GPU servers) | 57 kW/rack | about 14.3 kW per 8-GPU server | Verified | NVIDIA DGX B200 datasheet |
| GB200 NVL72 | 120 kW (132 kW peak) | about 120-132 kW | Verified | NVIDIA / OEM specifications 2025 |
| GB300 NVL72 | 135 kW (155 kW peak), 3,500 lb, 90% liquid | 132-140 kW operating, up to 155 kW peak; 3,300-3,480 lb; about 90% liquid | Verified | System-maker GB300 NVL72 specifications 2025-26 |
| Vera Rubin NVL144 | 220 kW (230 kW peak) | published figures 120-230 kW; in production, ships 2H 2026 | **Announced; estimate** | NVIDIA GTC 2025 / CES 2026; trade press |
| Rubin Ultra NVL576 (Kyber) | 600 kW (660 kW peak), 800 VDC | about 600 kW per rack, 2H 2027 | **Announced; estimate** | NVIDIA GTC 2025 keynote; DatacenterDynamics |
| 1 MW-class racks (15-year horizon) | 1,000 kW | industry direction for 800 VDC | **Speculative** | NVIDIA 800 VDC technical blog 2025 |
| Custom AI accelerator (ASIC) rack (estimated) | 100 kW | no public per-rack figure for a generic ASIC rack | **Estimate** | generic planning value; network fabric $3.5M/MW (about 18% of IT cost) |

Roadmap weights, prices and rental rates for Rubin, Kyber and the ASIC rack are estimates and are labelled so in the app.

## 2. Facility cost per MW of IT

| Item | Value used | Range | Status | Source |
|---|---|---|---|---|
| Air-cooled facility (15 kW/rack) | $12.0M/MW (+8% contingency -> $12.4M) | $10-15M/MW | Verified | 2026 global data center outlook (real-estate advisor): $11.3M/MW average shell & core (air-cooled); 2026 cost guide: US & Canada $17.6M/MW all-in |
| H100 HGX facility | $17.0M/MW | $15-25M+/MW | Verified range | 2026 outlook: liquid cooling adds about 10%, AI fit-out up to $25M/MW; 2025-26 cost index: AI builds +7-10% |
| GB300 NVL72 facility | $19.2M/MW basis -> $19.8M/MW at 8% contingency | $15-25M+/MW | Verified range | as above |
| Vera Rubin facility | $21.6M/MW | $15-25M+/MW | Derived; estimate | interpolated on the density ladder |
| Kyber 600 kW facility | $30.3M/MW | above $25M/MW | **Estimate** | no public cost data yet for 600 kW halls |
| Cost growth | escalation 5%/yr to construction mid-point | 5-6%/yr | Verified | Data centre construction cost index 2025-26 (about 5.5%); 2026 cost guide (+21% since Q4 2024) |
| Contingency | 8% (planning) | 5-15% | Assumption | standard planning practice |
| Owner costs | 3% | 2-5% | Assumption | |
| Location factors (N. Virginia = 1.00) | Dallas 0.92, Phoenix 0.90, NY/NJ 1.12, Dublin 0.90, Nordics 1.07, Singapore 1.26, Mumbai 0.58 | ratios of public $/W indices | Derived | 2025-26 cost index ($/W: Singapore 14.5, NJ 12.9, Stockholm 12.3, Dublin 10.0, Phoenix 9.8, Mumbai 6.6); 2026 market ranges |
| Utility interconnection | $80k per MW of service | highly site-specific | Assumption | |
| Land $/acre (powered) | NoVA $2.5M, Dallas $0.5M, Phoenix $0.6M, Singapore $10M, others $0.25-1.5M | NoVA $2.3-3.75M; DFW about $0.5M; Phoenix $0.2-1.0M | Verified (US); assumption (others) | Real-estate advisor land reports 2025 |
| Resilience changes | generators $3.5M per 3 MW (x1.15 N+2, x1.30 2N), UPS $0.6M per MW (x1.2 2N), unit substations $0.45M each, +13% soft cost | | Assumption | unit-rate planning allowances |

**Changed because they were unrealistic:** Dublin was 1.10 (the cost index shows Dublin below N. Virginia, so it is now 0.90);
NY/NJ was 1.25 (now 1.12, from the cost-index ratio); Mumbai was 0.70 (now 0.58). Utility lead time was 24 months and is now 36
months by default (2026 market outlook: grid-connection waits above 4 years in primary markets). The GPU-rental sanity range was
widened for Blackwell (below).

## 3. Energy, water, operations

| Item | Value used | Range | Status | Source |
|---|---|---|---|---|
| PUE, air-cooled | about 1.45 | 1.4-1.55 | Verified | Global data center survey 2025: average 1.54; new builds 1.48; 20 MW+ sites 1.44 |
| PUE, rear-door hybrid | about 1.35 | 1.3-1.4 | Derived | component model |
| PUE, direct-to-chip | about 1.20 | 1.1-1.25 | Verified range | ASHRAE TC 9.9 liquid cooling guidance; vendor-reported liquid sites |
| Power price, US | $0.075-0.12/kWh | $0.06-0.12 | Verified | US government Electric Power Monthly 2026: industrial about 9.0 cents/kWh YTD, 9.8 cents in July |
| Power price, Dublin / Singapore | $0.18 / $0.17 | higher than US | Assumption | regional tariffs |
| WUE, evaporative towers | about 2.3 L/kWh (physics: evaporation = heat / 2,430 kJ/kg, 5 cycles) | 1.8-2.6 | Verified | public operator reports; hyperscale averages 1.8-1.9 |
| WUE, dry/adiabatic (liquid) | 0.20 L/kWh | 0-0.5 | Verified range | operator reports (dry coolers near zero; best fleets about 0.3) |
| Diesel use | 0.070 gal/kWh | 0.068-0.072 at high load | Verified | 2,000 kVA / 1,600 ekW genset at full load about 114 gal/h |
| Maintenance | 2% of facility cost/yr | 1.5-3% | Assumption | |
| Staffing | 8 + 0.5 FTE per MW, $140k loaded | | Assumption | |
| Insurance / property tax | 0.3% / 0.5% of facility cost | site-specific | Assumption | |
| Cloud operations overhead | 15% of revenue | 10-20% | Assumption | |

## 4. GPU rental prices (October 2026)

| Platform | Default $/GPU-hr | Public range (spot to on-demand) | Status | Source |
|---|---|---|---|---|
| H100 | $2.50 | $1.30-4.50 (on-demand about $3.56, spot $2.43, transacted index $2.81) | Verified | public GPU price trackers, Oct 2026 |
| H200 | $3.25 | $2.09-5.40 (1-year about $3.40) | Verified | as above |
| B200 | $4.50 | $3.69-8.60 (spot $4.38, median $6.25) | Verified | as above |
| GB200 NVL72 | $6.00 | $6-16 (cloud 1-year about $10.6) | Verified | as above |
| GB300 NVL72 | $7.00 | $6-17.8 (B300 median about $7.9) | Verified | as above |
| Vera Rubin / Kyber / ASIC rack | $9.00 / $3.00 / $3.00 | no market yet | **Estimate** | |

The original "$2-4/GPU-hr" sanity range only holds for Hopper (H100/H200). Blackwell rents for more, so the test
checks each platform against its own public range. Rental price change is -8%/yr between hardware refreshes
(**assumption**), with a refresh every 5 years at 70% of the original IT cost (**assumption**).

## 5. Schedule and long-lead equipment

Lead time = released for manufacture (approved submittals) to delivery, incl. factory test and shipping. 2026 values.

| Item | Typical (weeks) | Range (weeks) | Status | Source |
|---|---|---|---|---|
| Large power transformers (>50 MVA) | 128 | 100-160 | Verified | Q2 2025 transformer supply-chain study (average 128 weeks); 2026 procurement surveys 100-150+; some quotes 36-42 months |
| Substation transformers (5-50 MVA) | 88 | 65-110 | Verified | 2026 procurement surveys |
| MV switchgear, 38 kV / 15 kV class | 91 / 66 | 78-104 / 52-80 | Verified | 2026 procurement surveys |
| Unit-substation transformers (2.5-5 MVA) | 52 | 40-65 | Verified | 2026 procurement surveys (pad-mount 0-5 MVA) |
| LV switchgear and switchboards | 36 | 18-54 | Verified | 2026 procurement surveys |
| Standby diesel generators (2.5-3.5 MW) | 82 | 62-110 | Verified | 2026 surveys: 2.5-3.5 MW 62-82 weeks, above 3 MW 90-110 weeks |
| UPS | 44 | 30-60 | Verified | 2026 surveys (500-1,500 kVA 30-48; modular 40-60) |
| Chillers / CDUs / busway | 55 / 40 / 26 | 40-70 / 30-50 / 16-40 | Verified range | 2026 surveys; busway depends on rating |
| Fire pumps and pre-action valves; carrier fiber laterals | 28; 52 | 20-36; 26-78 | Assumption | confirm with suppliers and carriers |
| Gas turbines (bridging / on-site) | aeroderivative about 40 months; heavy-duty mostly sold out to about 2030 | | Verified | 2026 market reporting |
| Months to utility power (greenfield default) | 36 months | 18 to 48+ | Verified range | 2026 market outlooks |

**Procurement chain per item (reverse schedule):** specification and RFQ 6 wk + bids 6 + award/PO 3 + submittal
preparation 5 + review 8 + quoted lead + staging 1.5, plus a 15% buffer on submittals and lead (planning practice:
RFQ to PO 8-16 weeks, submittal review 4-12 weeks, buffer 10-20%). When it is needed (months after start): main and unit transformers 1-2.5 months
before energization starts, MV switchgear 3 months before, generators 1.5 months before, UPS at energization,
chillers 1 month before, CDUs during energization, busway and fire equipment during MEP rough-in, carrier fiber at
commissioning. Send RFQ (months after start) = need - (chain + buffer); "Order it N months before you need it" with
N = need - max(RFQ month, 0); "Order before NTP" when the PO month falls before notice to proceed. No calendar dates
are shown. The ready-for-IT range runs from the short lead times with no weather allowance to the long lead times with
10% more weather allowance (100 MW default: about 41–51 months from start, typical 43).

**Phase model (assumptions, editable):** auto build = 12 + 12 x sqrt(MW/100) months (greenfield, 12-40):
24 months at 100 MW agrees with the public 18-30 month NTP-to-completion range
for 100 MW-class builds. Pre-construction: site studies (ESA 4-6 wk, geotech 6-10, survey and title 4-8, wetlands
8-16) and utility agreement (3-6 months review + 3-9 months agreement) in parallel with design; permits 4 months from
60% design; contractor selection 3 months. Overtime factor = 40 / (hours x productivity) with productivity 0.965 at
50 h, 0.875 at 60 h, 0.80 at 70 h (published overtime-productivity studies); weather applies to exterior work,
congestion to interior work and commissioning; commissioning does not compress with overtime. Energization starts
when field work is ready, utility power is available and the power-chain equipment has arrived (whichever is
latest). Substantial completion follows the integrated systems test; final completion 2 months later.
Escalation runs to the construction mid-point (NTP + build / 2).

**Estimate accuracy.** The app calls its output an "early budget estimate (±30–50%)". For reference only (this
term is not shown in the app): this corresponds to AACE International Recommended Practice 18R-97 Class 5 (0-2% project
definition; typical accuracy -20% to -50% low and +30% to +100% high). Later stage gates use "updated budget estimate
(about ±20–30%)" (18R-97 Class 4/3) and "control budget (about ±10–20%)" (Class 3/2).

## 6. Engineering formulas (checked by tests)

| Formula | Used for | Check |
|---|---|---|
| S (MVA) = P / PF | utility service, PF 0.95 | test: MVA >= MW / PF |
| I = P / (sqrt3 x V x PF) | rack feed, busway, switchboard | 120 kW at 415 V, PF 0.98 = 170 A |
| Busway rating >= 1.25 x I (continuous load) | row busway | NEC continuous-load rule |
| tons = kW / 3.517 | cooling | 1 ton = 12,000 Btu/h |
| Q = P / (rho x cp x dT) | liquid, facility-water and chilled-water flow | 18 MW at 10 K = 431 L/s (6,850 gpm) |
| Airflow = P / (rho x cp x dT) | residual air, rho 1.2, cp 1.006, dT 12 K | 13.5 kW = 0.93 m3/s (1,975 CFM) |
| Q_reject = Q + W_compressor | heat rejection | test: rejection >= cooling load |
| E_fac = E_IT x PUE (annual) | energy cost | PUE is an energy ratio (ISO/IEC 30134-2), not a peak multiplier |
| Battery kWh = P x t / eta / ageing | UPS | 2 MW x 10 min = 333 kWh before losses |
| Floor pressure = W / footprint | slab design | GB300: 3,500 lb on 0.64 m2 = 507 psf (24.3 kPa) |
| Liquid capture 85-95%, never 100% | residual air sizing | D2C platforms |

Cooling rule: air tops out near 30 kW/rack and rear-door heat exchangers near 45 kW/rack, so above 45 kW/rack
the model always uses direct-to-chip liquid cooling. Immersion is a niche option and is not modelled.


### Detailed calculations and the codes they follow

| Calculation | Formula / rule | 100 MW GB300 result | Code / basis |
|---|---|---|---|
| MV current | I = S / (sqrt3 x V); bus >= 1.25 x I_feed, frames 1,200/2,000/3,000/4,000 A | 2,615 A total at 34.5 kV; 1,339 A per 80 MVA lineup -> 2,000 A | IEEE C37.20.2 ratings; fault study for kA |
| A/B rack feed | each side >= P_rack / PF; breaker >= 1.25 x I, standard size | 157 kVA per side; 300 A | NEC 240.6(A); a 2 x 45 kVA design fails a 50 kW rack |
| Busway loading | I / rating <= 80% | 72.6% | NEC 210.19 / 215.2 continuous load |
| Generators | sized on kW (ratings already at 0.8 PF) | 50 x 3 MW (44 + 6, N+1) | ISO 8528-1 ratings; "2N+1" wording corrected to N+1 |
| Airflow (US) | CFM = BTU/h / (1.08 x dT_F) | 2.28 M CFM at 21.6 F | standard air; agrees with SI |
| Chilled water (US) | GPM = tons x 24 / dT_F | 8,823 gpm (SI 8,851) | 500 = 8.33 x 60 |
| Thermal storage | V = Q x t / (rho cp dT x FOM), 10 min, FOM 0.9 | 372 m3 | chiller restart on generator |
| Tower make-up | E = Q / h_fg; M = E x CoC / (CoC - 1) | 708 gpm evaporation (2.3 per 100 tons); 885 gpm make-up at CoC 5 | physics; Legionella plan per ASHRAE 188 |
| Sprinklers | OH-1 0.15 gpm/sf over 1,500 sf, +30% area for double-interlock pre-action; + 250 gpm hose | 292.5 + 250 = 542.5 gpm; 160 heads at 130 sf | NFPA 13 (2025); OH-2 0.20 gpm/sf shown as the range |
| Fire pump and storage | smallest rating >= demand; 60 min (supervised) or 90 min | 750 gpm; 32,550 gal (90 min: 48,825) | NFPA 20 (65% pressure at 150% flow), NFPA 22 |
| Clean agent | W = (V / S) x C / (100 - C), S = 0.9856 + 0.002441 T (FK-5-1-12) | 2,047 lb for 54,000 ft3 at 4.2%, 70 F | NFPA 2001; 10-min hold, door-fan test |
| Domestic water | IPC Table 2902.1 fixtures; WSFU -> Hunter's curve | 9 fixtures, 30.2 WSFU -> 23.4 gpm | IPC Appendix E |
| Stormwater | Q = C i A; detention = (Q_post - Q_pre) x 1 h (first pass) | 54 cfs post vs 24 pre; 2.5 acre-ft | rational method; local ordinance and IDF data govern |
| Fiber | GPUs x 16 (800G class) x 1.25 per rack; backbone racks x GPUs x 16 | 1,440 per rack; 853,632 backbone | planning assumption; 2x pathway fill |
| Entrance diversity | 2 entrance rooms, 2+ carriers, routes >= 20 m apart | 2 | TIA-942-C, BICSI 002-2024 |

### Corrections applied (values found wrong in planning material and fixed)

| Wrong | Correct value used |
|---|---|
| Generators sized as kW / 0.8 | size on kW: genset kW ratings already assume 0.8 PF |
| Clean-agent quantity without the specific-volume term | W = (V/S) x C/(100-C) with S = 0.9856 + 0.002441 T |
| Tower make-up about 1.5 gpm per 100 tons | about 2.3-2.4 evaporation + blowdown, about 3 gpm per 100 tons |
| 2 x 45 kVA feeds for a 50 kW rack called A/B | each side must carry the whole rack: fails |
| Busway at 100% of rating | <= 80% continuous |
| "2N+1" for units plus one spare | N+1 |
| "72 h" of fuel from a tank that holds about 36 h | fuel hours = usable gallons / burn rate, shown per 100,000 gal |
| Next-generation racks 120-130 kW | about 187-227 kW announced; model keeps 230 kW |
| OSHA reporting | fatality 8 h; hospitalization, amputation, eye loss 24 h (29 CFR 1904.39) |
| Hot-work fire watch 30 min | at least 1 h (NFPA 51B 2019+) |
| Humidity as 30-60% / 40-60% RH | dew-point limits (ASHRAE TC 9.9) |
| Substantial completion before integrated testing | substantial completion follows a passed IST |
| Liquid classes W1-W5 | W17, W27, W32, W40, W45, W+ |
| Tier availability percentages as requirements | historical only; Tier is topology |
| "Class B" for data hall fires | Class C (energized electrical) and Class A |
| 4-hour generator acceptance test | NFPA 110: 2-hour full-load test (30% / 50% / 100%) after the cold start |
| OH-2 0.20 gpm/sf over 2,000 sf | 0.20 over 1,500 sf (single-point criterion) |
| Lead times from older tables | 2026 ranges above |
| Workforce counts and bulk quantities | not used (not verifiable as generic values) |

## 7. Future-proof horizon (all assumptions, editable)

| Item | Value | Status |
|---|---|---|
| Targets | 5 years: 230 kW (Vera Rubin class); 10 years: 600 kW (Kyber class); 15 years: 1,000 kW | announced / announced / speculative |
| Year the target arrives | 3 / 5 / 8 years after ready-for-service | Assumption |
| Retrofit later | 1.35x premium for live-building work, 6% demolition of power/cooling, 4 months of lost margin | Assumption |
| Provisions now | pre-install shares: structure, envelope, site 100%; piping 40%; plumbing 50%; electrical pathways, controls, comms 25%; prefab modules 0%. The rest is installed later at 1.10x with 1 month of lost margin | Assumption |
| Full future build | all upgrade work on day one; 2%/yr upkeep on idle capacity | Assumption |
| Probability the target is deployed at this site | 70% | Assumption |
| Discount rate | 8% | Assumption |
| 800 VDC readiness | flagged at 400 kW/rack and above | Verified: NVIDIA 800 VDC blog 2025 |

## 8. Sources

- *2026 Global Data Center Outlook* (commercial real-estate advisor).
- *Data Center Development Cost Guide 2026* (commercial real-estate advisor).
- *Data Centre Construction Cost Index 2025-2026* (cost consultancy).
- *Global Data Center Survey 2025* (industry survey).
- NVIDIA: GTC 2025 keynote; DGX H100/H200/B200 datasheets; technical blog on 800 VDC architecture (2025).
- System-maker GB300 NVL72 specifications (2025-26).
- US government *Electric Power Monthly* (2026).
- Power transformer supply-chain study (Q2 2025) and 2026 procurement surveys.
- ASHRAE TC 9.9, thermal guidelines and liquid cooling guidance for data processing environments.
- NFPA 13, 20, 22, 70 (NEC), 110, 2001, 51B, 855; IPC 2021/2024 (Table 2902.1, Appendix E); NETA ATS; IEEE C37.20.2,
  C37.20.7; TIA-942-C; BICSI 002; ASHRAE 188; OSHA 29 CFR 1904.39 and 1926.652; AACE 18R-97 (estimate-class
  mapping above only). Editions and URLs: section 10.
- 2026 equipment procurement surveys (lead times) and published overtime-productivity studies.
- US EPA Technology Transitions rule (low-GWP refrigerants for IT cooling, 2027).
- Public GPU rental price trackers (October 2026).

## 9. End-to-end cost lines and the "Include in total" checklist

The total and the cost per MW are always the sum of the ticked lines (tested with random tick sets on every preset). The same total is used in the summary cards, the Costs tab, the Nemotron payload, the
rule-based narrative, the one-page PDF, the Markdown report and the CSV exports.

| # | Line | Default | How it is priced | Status / source type |
|---|---|---|---|---|
| 1 | Facility: shell, power, cooling, fire | ticked | $/MW IT benchmark by division (section 2), net of the lines carved out below | Verified range |
| 2 | Land and site work | ticked | powered land $/acre x acres + site divisions 31-33 | Verified (US land); assumption |
| 3 | Utility interconnect and substation | ticked | $80k per MW of service + 15% of division 26 (on-site substation) | Assumption |
| 4 | On-site or bridging power | **not ticked** | $2,000/kW x 1.1 x facility peak | Verified range: US EIA capital cost assumptions, combustion turbines about $1,522-1,606/kW, reciprocating engines about $2,460/kW |
| 5 | GPU and server hardware | **not ticked** | platform price per rack | Estimate (public system pricing) |
| 6 | AI network fabric | **not ticked** | $/MW by platform; 8.8-18.6% of IT cost ($9,375 per GPU for GB300) | Verified range: networking about 10-15% (6-20%) of AI cluster cost |
| 7 | Fiber and structured cabling | ticked | division 27 of the cost basis | Derived |
| 8 | Racks, rack PDUs, CDUs and manifolds | ticked | carved from the facility; HGX-type platforms add $6,000 per rack + $120/kW rack PDUs (NVL72-type rack prices already include the rack); manifolds $18k (hybrid) / $30k (D2C) per rack | Assumption within trade ranges |
| 9 | Security and controls | ticked | divisions 25 and 28 | Derived |
| 10 | Design, permits and fees | ticked | 2.5% design carve + owner costs | Assumption (below published A/E fee guides) |
| 11 | Commissioning | ticked | 1.5% of construction (0.75-2%) | Trade press: about 1.5% of construction cost for complex data centers |
| 12 | Owner contingency and escalation | ticked | planning contingency + escalation to the construction mid-point | Assumption; cost index |
| 13 | Spares and first fill | ticked | 1% of electrical + mechanical + diesel first fill at $6.00/gal | US EIA weekly retail diesel $6.179/gal (12 Oct 2026) |

**Greenfield carve.** Lines 1, 2 (site part), 3 (substation part), 7, 8, 9, 10 (design part), 11 and 12 (embedded
contingency) are regrouped from the facility estimate, so they add back exactly to the facility cost (tested). Only
spares, the interconnect allowance, land and (for HGX-type platforms) racks and rack PDUs are new money.

| Preset | Default ticks | Per MW | Every line ticked | Per MW |
|---|---|---|---|---|
| 100 MW GB300 NVL72 greenfield | $2,328.2M | $23.28M | $6,076.2M | $60.76M |
| 10 MW H200 HGX greenfield | $188.1M | $18.81M | $561.6M | $56.16M |

## 10. Codes and standards: editions checked on the publishers' sites (October 2026)

| Code / standard | Edition used | Publisher page |
|---|---|---|
| NFPA 70 (NEC) | 2026 | https://www.nfpa.org/codes-and-standards/nfpa-70-standard-development/70 |
| NFPA 70E | 2027 | https://www.nfpa.org/codes-and-standards/nfpa-70e-standard-development/70e |
| NFPA 110 | 2025 | https://www.nfpa.org/codes-and-standards/nfpa-110-standard-development/110 |
| NFPA 111 | 2025 | https://www.nfpa.org/codes-and-standards/nfpa-111-standard-development/111 |
| NFPA 13 | 2025 | https://www.nfpa.org/codes-and-standards/nfpa-13-standard-development/13 |
| NFPA 20 | 2025 | https://www.nfpa.org/codes-and-standards/nfpa-20-standard-development/20 |
| NFPA 22 | 2023 | https://www.nfpa.org/codes-and-standards/nfpa-22-standard-development/22 |
| NFPA 72 | 2025 | https://www.nfpa.org/codes-and-standards/nfpa-72-standard-development/72 |
| NFPA 75 | 2024 | https://www.nfpa.org/codes-and-standards/nfpa-75-standard-development/75 |
| NFPA 76 | 2024 | https://www.nfpa.org/codes-and-standards/nfpa-76-standard-development/76 |
| NFPA 2001 | 2025 | https://www.nfpa.org/codes-and-standards/nfpa-2001-standard-development/2001 |
| NFPA 855 | 2026 | https://www.nfpa.org/codes-and-standards/nfpa-855-standard-development/855 |
| NFPA 101 | 2027 | https://www.nfpa.org/codes-and-standards/nfpa-101-standard-development/101 |
| NFPA 30 | 2027 | https://www.nfpa.org/codes-and-standards/nfpa-30-standard-development/30 |
| NFPA 37 | 2024 | https://www.nfpa.org/codes-and-standards/nfpa-37-standard-development/37 |
| IEEE 1584 | 2018 | https://standards.ieee.org/ieee/1584/5802/ |
| IEEE C57.12.00 | 2021 | https://standards.ieee.org/ieee/C57.12.00/6962/ |
| NESC (IEEE C2) | 2023 | https://standards.ieee.org/ieee/C2/10814/ |
| UL 9540 | 3rd edition (2023, revised 2025) | https://www.shopulstandards.com/ProductDetail.aspx?productId=UL9540_3_S_20230628 |
| UL 9540A | 5th edition (2025) | https://www.shopulstandards.com/ProductDetail.aspx?productId=UL9540A_5_S_20250312 |
| IBC, IFC, IMC, IPC, IECC | 2027 (published 2026) | https://codes-conv.iccsafe.org/content/IBC2027V1.0 ; https://codes-conv.iccsafe.org/content/IFC2027V1.0 |
| ASHRAE 90.4 | 2025 | https://www.ashrae.org/technical-resources/bookstore/datacom-series |
| ASHRAE TC 9.9 Thermal Guidelines | 5th edition, revised and expanded | https://www.ashrae.org/technical-resources/bookstore/datacom-series |
| ASHRAE 188 | 2021 | https://www.ashrae.org/technical-resources/bookstore/ansi-ashrae-standard-188-2021-legionellosis-risk-management-for-building-water-systems |
| TIA-942 | TIA-942-C (2024) | https://tiaonline.org/products-and-services/tia942certification/ansi-tia-942-standard/ |
| BICSI 002 | 2024 | https://www.bicsi.org/standards/available-standards-store/single-purchase/ansi-bicsi-002-the-standard-for-data-center-design |
| OSHA 29 CFR 1926 / 1910 | current eCFR | https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926 ; https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1910 |
| EPA SPCC, 40 CFR 112 | current eCFR (1,320 gal aboveground threshold) | https://www.ecfr.gov/current/title-40/chapter-I/subchapter-D/part-112 |
| FAA 14 CFR Part 77 | current eCFR (Form 7460-1) | https://www.ecfr.gov/current/title-14/chapter-I/subchapter-E/part-77 |
| ADA | 2010 Standards | https://www.ada.gov/law-and-regs/design-standards/2010-stds/ |

The adopted edition is set by each state and city, often one or two cycles behind the latest, so the app's "Confirm
locally" checklist lists what to check with the AHJ. NFPA 780 is not listed (edition not re-verified).

## 11. Delays: public evidence behind the risk register and "How to avoid delays"

| Topic | Public evidence | Source |
|---|---|---|
| Power and grid | 2025 university study: about 76 GW of new load fits on the US grid if it accepts curtailment about 0.25% of the time | https://nicholasinstitute.duke.edu/publications/rethinking-load-growth |
| Community opposition | 2025 tracking report: about $64B of US projects blocked or delayed by local opposition, May 2024 - March 2025 | https://www.datacenterwatch.org/report |
| Equipment supply | US DOE report and 2025 transformer study (US procurement section); lead times in section 5 | see below |
| Capex split (How it works) | 2025 consultancy estimate: about 60% chips and computing hardware, 25% power, cooling and electrical, 15% land, materials and site | https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights/the-cost-of-compute-a-7-trillion-dollar-race-to-scale-data-centers |
| Fixes | early utility load study, phased energization, flexible-load agreements, bridging power, factory slot deposits (typically 10-30%), early environmental review, closed-loop or dry cooling, community benefit agreements, labor agreements and prefabrication | 2025-26 trade and industry reporting |

The app's illustrative capex split (50% chips and servers, 15% networking, 20% power, 7.5% cooling, 7.5% facilities)
is consistent with the public 60/25/15 split (chips + networking 65% vs 60%; power + cooling + facilities 35% vs 40%)
and is labelled illustrative.

**Other benchmark URLs.** US EIA weekly retail diesel: https://www.eia.gov/petroleum/gasdiesel/ . US EIA capital cost
and performance assumptions: https://www.eia.gov/outlooks/aeo/assumptions/pdf/elec_cost_perf.pdf . Commissioning about
1.5% of construction: https://www.datacenterknowledge.com/business/getting-the-most-out-of-commissioning-through-best-practices .
AI cluster networking about 10-15% of cluster cost: https://www.amcompute.com/blog/gpu-cluster-networking .

## 12. US procurement: lead times, supply, tariffs and suppliers

This is the only section of the project that names companies. Listed alphabetically for reference; not exhaustive,
not an endorsement; no affiliation. Each supplier has one public source showing it makes that equipment for data
centers or makes it in the US. No rankings, logos or market shares are shown.

**Supply and tariff sources.** US DOE Large Power Transformer Resilience report to Congress (July 2024): 82% of LPTs
imported in 2019 (617 imported vs 137 US-made), US plants about 40% utilized, grain-oriented electrical steel mostly
imported: https://www.energy.gov/sites/default/files/2024-10/EXEC-2022-001242%20-%20Large%20Power%20Transformer%20Resilience%20Report%207-10-24.pdf .
2025 industry study, transformer supply deficits (30% power, 10% distribution):
https://www.woodmac.com/press-releases/power-transformers-and-distribution-transformers-will-face-supply-deficits-of-30-and-10-in-2025 .
Section 232 metals proclamation of 2 Apr 2026 (50% metals, 25% derivatives, temporary 15% for listed industrial
machinery and equipment): https://www.whitehouse.gov/presidential-actions/2026/04/strengthening-actions-taken-to-adjust-imports-of-aluminum-steel-and-copper-into-the-united-states/ ;
amendment of 1 Jun 2026: https://www.whitehouse.gov/presidential-actions/2026/06/further-adjusting-the-tariff-regimes-for-imports-of-aluminum-steel-and-copper-into-the-united-states/ .

| Package | Supplier | What the source shows | Source |
|---|---|---|---|
| Large power transformers | Hitachi Energy | Large power transformer factory, South Boston, Virginia (announced 2025) | https://www.hitachienergy.com/us/en/news-and-events/press-releases/2025/09/hitachi-announces-historic-1-billion-usd-manufacturing-investment-to-power-america-s-energy-future-through-production-of-critical-grid-infrastructure |
| Large power transformers | Hyosung HICO | Large power transformer plant, Memphis, Tennessee; expansions announced 2025 (+50% capacity) | https://www.hyosunghico.com/blog/powering-americas-future-hyosung-hico-expands-memphis-headquarters |
| Large power transformers | Prolec GE | US transformer plant investment, North Carolina | https://www.prolec.energy/news/prolec-ge-invests-an-additional-140-million-in-the-u-s-to-support-north-american-electric-grid-goals/ |
| Large power transformers | Siemens Energy | Large power transformer factory, Charlotte, North Carolina (production from 2027) | https://www.siemens-energy.com/us/en/home/press-releases/siemens_energy_addresses_shortage_US_powertransformers_invests_new_factory.html |
| Large power transformers | Virginia Transformer | Power transformer plant expansion, Rincon, Georgia | https://www.vatransformer.com/expand-georgia-transformer-plant-in-rincon/ |
| MV switchgear | Eaton | UPS made in the Raleigh, North Carolina area; metal-clad MV switchgear; busway | https://www.eaton.com/us/en-us/catalog/medium-voltage-power-distribution-control-systems/vacclad-w-5-15-kv-metal-clad-medium-voltage-switchgear.html |
| MV switchgear | Powell Industries | ANSI metal-clad MV switchgear (Houston, Texas) | https://www.powellind.com/ansi-metal-clad-switchgear |
| MV switchgear | Schneider Electric | US plants for MV equipment (Tennessee) and switchgear (Texas, North Carolina); data center UPS | https://www.se.com/us/en/about-us/newsroom/news/press-releases/Schneider-Electric-Plans-to-Invest-Over-700-million-in-the-U-S-Supporting-Energy-AI-Sectors-and-Job-Growth-67bdeb3ee4475a5955011b6a/ |
| Standby generators | Caterpillar | Lafayette, Indiana large-engine and genset expansion for data center backup power (2024) | https://www.caterpillar.com/en/news/corporate-press-releases/h/lafayette-large-engine-expansion.html |
| Standby generators | Cummins | QSK95 data center generator sets; engines built in Seymour, Indiana | https://www.cummins.com/en-na/news/releases/2020/12/21/cummins-qsk95-diesel-generator-series-reaches-1000th-unit-milestone |
| Standby generators | Rehlko | Diesel generators up to about 4 MW for data centers | https://www.powersystems.rehlko.com/data-center |
| Standby generators | Rolls-Royce (mtu) | Series 4000 data center generator sets, Mankato, Minnesota expansion (2026) | https://www.rolls-royce.com/media/press-releases/2026/09-07-2026-rr-cuts-ribbon-on-new-usd-24m-expansion-in-mankato-minnesota.aspx |
| UPS | Eaton | UPS made in the Raleigh, North Carolina area; metal-clad MV switchgear; busway | https://www.eaton.com/us/en-us/company/news-insights/news-releases/2022/eaton-reinvests-in-north-carolina.html |
| UPS | Mitsubishi Electric Power Products | UPS and switchgear for US data centers (Warrendale, Pennsylvania) | https://www.meppi.com/news/mitsubishi-electric-to-provide-integrated-power-protection-and-it-cooling-solutions-for-us-data-center-applications |
| UPS | Schneider Electric | US plants for MV equipment (Tennessee) and switchgear (Texas, North Carolina); data center UPS | https://www.se.com/us/en/work/products/master-ranges/galaxy/ |
| UPS | Toshiba International | UPS and power electronics made in Houston, Texas | https://toshiba.com/tic/about-us/company-overview/ |
| UPS | Vertiv | Data center UPS and CDUs; US manufacturing sites | https://www.vertiv.com/en-us/products-catalog/critical-power/uninterruptible-power-supplies-ups/liebert-exl-s1/ |
| Busway | Eaton | UPS made in the Raleigh, North Carolina area; metal-clad MV switchgear; busway | https://www.eaton.com/us/en-us/catalog/low-voltage-power-distribution-controls-systems/pow-r-way-III-busway.html |
| Busway | Legrand (Starline) | Track busway for data centers | https://www.legrand.com/datacenter/en/grey-space/busbar-busway/starline-track-busway |
| Chillers and dry coolers | Carrier | Water-cooled centrifugal chiller for data centers | https://www.carrier.com/commercial/en/us/19mv/data-center/ |
| Chillers and dry coolers | Johnson Controls (YORK) | Air-cooled magnetic-bearing chillers for data centers | https://www.york.com/commercial-equipment/chilled-water-systems/air-cooled-chillers/yvam_ch/yvam-air-cooled-magnetic-bearing-centrifugal-chiller |
| Chillers and dry coolers | Modine | US chiller production expansion for data centers (Grenada, Mississippi) | https://investors.modine.com/news/news-details/2025/Modine-Expands-U-S--Chiller-Production-Capacity-to-Serve-Data-Center-Customers/default.aspx |
| Chillers and dry coolers | Munters | Data center cooling factory expansion, Virginia (2025) | https://www.munters.com/en-us/news-media/stories/2025/munters-to-expand-its-data-center-technology-factory-in-virginia/ |
| Chillers and dry coolers | Trane | Data center chillers | https://www.trane.com/commercial/north-america/us/en/products-systems/chillers/data-center-chillers.html |
| CDUs | Flex (JetCool) | Coolant distribution units for AI/HPC; US manufacturing sites | https://investors.flex.com/news/news-details/2025/Flexs-Liquid-Cooling-Business-Expands-Portfolio-with-High-Performance-Coolant-Distribution-Unit-for-AI-and-HPC-Applications/default.aspx |
| CDUs | Motivair (Schneider Electric) | CDUs built in Buffalo, New York | https://www.motivaircorp.com/news/motivair-by-schneider-electric-expands-u-s-manufacturing-footprint/ |
| CDUs | Vertiv | Data center UPS and CDUs; US manufacturing sites | https://www.vertiv.com/en-us/products-catalog/thermal-management/high-density-solutions/vertiv-coolchip-cdu/ |
| Switchboards (LV) | Schneider Electric | US plants for MV equipment (Tennessee) and switchgear (Texas, North Carolina); data center UPS | https://www.se.com/us/en/about-us/newsroom/news/press-releases/Schneider-Electric-Plans-to-Invest-Over-700-million-in-the-U-S-Supporting-Energy-AI-Sectors-and-Job-Growth-67bdeb3ee4475a5955011b6a/ |
| Switchboards (LV) | Siemens | Fort Worth, Texas plant for low-voltage switchboards for AI infrastructure | https://news.siemens.com/en-us/siemens-opens-190m-ft-worth-mfg-hub-ai-infrastructure/ |
| Fiber and optics | AFL | US fiber optic cable manufacturing expansion, South Carolina (2024) | https://www.aflglobal.com/en/company/company-profile/news/2024/afl-announces-a-multi-million-dollar-investment-and-expansion-to-its-us-fiber-optic-cable |
| Fiber and optics | CommScope | US fiber cable manufacturing expansion, Catawba County, North Carolina (2023) | https://www.businesswire.com/news/home/20230726503630/en/CommScope-Announces-Fiber-Cable-Manufacturing-Expansion-in-North-Carolina |
| Fiber and optics | Corning | Optical cable manufacturing expansion, Hickory, North Carolina | https://hickorync.gov/corning-expand-operations-trivium-plans-add-132-jobs-and-invest-170m-2679m |
| Fiber and optics | Prysmian | US optical cable plants (Tennessee, North Carolina) | https://na.prysmian.com/resources/press-releases/prysmian-partners-with-dow-to-advance-production-of-sirocco-microduct-cables |
| Fire pumps | Aurora (Pentair) | UL-listed, FM-approved split-case fire pumps (NFPA 20) | https://www.pentair.com/en-us/flow/aurora-brand-page/aurora-products/aurora-horizontal-split-case-electric-drive-fire-pump-series-912.html |
| Fire pumps | Patterson Pump | UL-listed, FM-approved split-case fire pumps | https://pattersonpumps.com/markets/fire-pumps/horizontal-split-case-fire/ |
| Fire pumps | Peerless Pump | UL/FM split-case fire pumps (NFPA 20) | https://www.peerlesspump.com/products/fire/aef/ |
| Battery energy storage (BESS) | Fluence | Battery storage with US-made cells, modules and enclosures | https://fluenceenergy.com/domestic-content/ |
| Battery energy storage (BESS) | LG Energy Solution Vertech | LFP energy-storage cell production, Holland, Michigan | https://www.canarymedia.com/articles/energy-storage/lg-michigan-lfp-battery-factory |
| Battery energy storage (BESS) | Tesla | Megapack battery storage built in Lathrop, California; data center use | https://www.tesla.com/megapack |

**Left out as unverifiable** (no public source tying the company to the category or to US manufacturing when
checked): a cooling maker whose US production starts only in 2027; a CDU product page that could not be reached; a
multinational with no category-specific US source; two makers whose sources covered other products (for example
1-10 MVA units, not LPTs); US makers of optical transceivers; guessed product URLs that did not resolve.

## 13. Final QA checks (October 2026)

| Check | Result | Enforced by |
|---|---|---|
| Every project type x platform (incl. custom) x redundancy x horizon (2 x 9 x 4 x 4 = 288 runs) plus 150 seeded random edge cases (0.5-2,000 MW, 1-50,000 racks, 5-1,500 kW/rack, extreme prices, schedule factors and random ticks) | No exceptions, no NaN or infinite values, no negative cost line, ticked lines = total within $1, schedule range brackets the central case, no negative phase, one-page PDF always 1 page, Markdown, checklist PDF and narrative build | `tests/test_fuzz.py` |
| Tiny sites (1-2 racks) at redundancy N | A redundancy reduction is capped at half of its construction division, so dropping one 3 MW generator from a site that needs one can no longer make a division negative | `tests/test_fuzz.py` |
| Rounding | $M shown to 1 decimal and $M per MW to 2 decimals in the app, PDF and Markdown (e.g. facility 1,397.3 and 13.97), so the per-MW column adds up to the per-MW total | `report._md`, `ui_views._df` |
| Units | Land cost shown as money ($65.5M), not "65,482,510 $"; key design line omits "(0 CDUs)" on air or rear-door designs | `report.val`, `report.key_design_line` |
| One verdict wording | "Verdict" on the first screen, PDF, Markdown and narrative; payback shown once; the narrative uses the price-change input instead of a fixed value | `tests/test_app.py`, `tests/test_round3.py` |
| Disclaimer | Once on the first screen, once in the footer, in the Terms of use and in every export; no repeated warnings | `tests/test_app.py::test_first_screen_terms_and_no_nagging` |
| Terms of use | TERMS.md identical to the in-app text and covers every required point | `tests/test_terms.py` |
| Preset totals after QA | 100 MW GB300: $2,328.2M ($23.28M/MW; $6,076.2M all lines) · 10 MW H200: $188.1M ($18.81M/MW; $561.6M) | `tests/test_round3.py` |
| Future target wording | The horizon is the planning window; the target racks go in earlier, in year 3, 5 or 8 after ready for IT (5, 10, 15-year horizons; editable). Every output says e.g. "a 600 kW/rack target installed in year 5 after ready for IT" | `tests/test_round3.py::test_target_wording_every_horizon` |
| Day-one density vs roadmap | The Future-ready roadmap starts with the selected platform's own day-one density (e.g. GB300 NVL72 about 135 kW/rack, H200 HGX about 42 kW/rack) and labels 40-60 kW as typical enterprise and earlier AI racks | `tests/test_round3.py::test_roadmap_day_one_density` |
