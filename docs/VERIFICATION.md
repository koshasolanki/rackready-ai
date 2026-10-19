# RackReady AI: verification of numbers

Every number the model uses, its value, the range it must sit in, and the public source or the reason it is
an assumption. The automated tests (`tests/test_rackready.py`) enforce the ranges and the physics.
**Indicative planning estimate, not a bid.** Prices are 2026 US dollars.

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
| TPU Ironwood (rack) | 100 kW | no public per-rack figure | **Estimate** | Google Cloud announcement 2025 (chip level only) |

Roadmap weights, prices and rental rates for Rubin, Kyber and TPU are estimates and are labelled so in the app.

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
| Vera Rubin / Kyber / TPU | $9.00 / $3.00 / $3.00 | no market yet | **Estimate** | |

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
RFQ to PO 8-16 weeks, submittal review 4-12 weeks, buffer 10-20%). Need dates: main and unit transformers 1-2.5 months
before energization starts, MV switchgear 3 months before, generators 1.5 months before, UPS at energization,
chillers 1 month before, CDUs during energization, busway and fire equipment during MEP rough-in, carrier fiber at
commissioning. RFQ by = need - (chain + buffer); "Order before NTP" when the PO date falls before notice to proceed.

**Phase model (assumptions, editable):** auto build = 12 + 12 x sqrt(MW/100) months (greenfield, 12-40) or
8 + 6 x sqrt(MW/100) (fit-out, 8-24): 24 months at 100 MW agrees with the public 18-30 month NTP-to-completion range
for 100 MW-class builds. Pre-construction: site studies (ESA 4-6 wk, geotech 6-10, survey and title 4-8, wetlands
8-16) and utility agreement (3-6 months review + 3-9 months agreement) in parallel with design; permits 4 months from
60% design; contractor selection 3 months. Overtime factor = 40 / (hours x productivity) with productivity 0.965 at
50 h, 0.875 at 60 h, 0.80 at 70 h (published overtime-productivity studies); weather applies to exterior work,
congestion to interior work and commissioning; commissioning does not compress with overtime. Energization starts
when field work is ready, utility power is available and the power-chain equipment has arrived (whichever is
latest). Substantial completion follows the integrated systems test; final completion 2 months later.
Escalation runs to the construction mid-point (NTP + build / 2).

**Estimate class:** AACE 18R-97 Class 5 (concept screening, 0-2% definition): -20% to -50% / +30% to +100%.

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


### Round-2 calculations and the codes they follow

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
| Sprinklers | OH-1 0.15 gpm/sf over 1,500 sf, +30% area for double-interlock pre-action; + 250 gpm hose | 292.5 + 250 = 542.5 gpm; 160 heads at 130 sf | NFPA 13 (2022/2025); OH-2 0.20 gpm/sf shown as the range |
| Fire pump and storage | smallest rating >= demand; 60 min (supervised) or 90 min | 750 gpm; 32,550 gal (90 min: 48,825) | NFPA 20 (65% pressure at 150% flow), NFPA 22 |
| Clean agent | W = (V / S) x C / (100 - C), S = 0.9856 + 0.002441 T (FK-5-1-12) | 2,047 lb for 54,000 ft3 at 4.2%, 70 F | NFPA 2001; 10-min hold, door-fan test |
| Domestic water | IPC Table 2902.1 fixtures; WSFU -> Hunter's curve | 9 fixtures, 30.2 WSFU -> 23.4 gpm | IPC Appendix E |
| Stormwater | Q = C i A; detention = (Q_post - Q_pre) x 1 h (screening) | 54 cfs post vs 24 pre; 2.5 acre-ft | rational method; local ordinance and IDF data govern |
| Fiber | GPUs x 16 (800G class) x 1.25 per rack; backbone racks x GPUs x 16 | 1,440 per rack; 853,632 backbone | planning assumption; 2x pathway fill |
| Entrance diversity | 2 entrance rooms, 2+ carriers, routes >= 20 m apart | 2 | TIA-942-B, BICSI 002 |

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
  C37.20.7; TIA-942-B; BICSI 002; ASHRAE 188; OSHA 29 CFR 1904.39 and 1926.652; AACE 18R-97.
- 2026 equipment procurement surveys (lead times) and published overtime-productivity studies.
- US EPA Technology Transitions rule (low-GWP refrigerants for IT cooling, 2027).
- Public GPU rental price trackers (October 2026).
