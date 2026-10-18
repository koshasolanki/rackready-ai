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
| GB300 NVL72 | 135 kW (155 kW peak), 3,500 lb, 90% liquid | 132-140 kW operating, up to 155 kW peak; 3,300-3,480 lb; about 90% liquid | Verified | HPE, Lenovo, Supermicro GB300 NVL72 specifications 2025-26 |
| Vera Rubin NVL144 | 220 kW (230 kW peak) | published figures 120-230 kW; in production, ships 2H 2026 | **Announced; estimate** | NVIDIA GTC 2025 / CES 2026; trade press |
| Rubin Ultra NVL576 (Kyber) | 600 kW (660 kW peak), 800 VDC | about 600 kW per rack, 2H 2027 | **Announced; estimate** | NVIDIA GTC 2025 keynote; DatacenterDynamics |
| 1 MW-class racks (15-year horizon) | 1,000 kW | industry direction for 800 VDC | **Speculative** | NVIDIA 800 VDC technical blog 2025; Schneider Electric |
| TPU Ironwood (rack) | 100 kW | no public per-rack figure | **Estimate** | Google Cloud announcement 2025 (chip level only) |

Roadmap weights, prices and rental rates for Rubin, Kyber and TPU are estimates and are labelled so in the app.

## 2. Facility cost per MW of IT

| Item | Value used | Range | Status | Source |
|---|---|---|---|---|
| Air-cooled facility (15 kW/rack) | $12.0M/MW (+8% contingency -> $12.4M) | $10-15M/MW | Verified | JLL 2026 Global Data Center Outlook: $11.3M/MW average shell & core (air-cooled); Cushman & Wakefield 2026: US & Canada $17.6M/MW all-in |
| H100 HGX facility | $17.0M/MW | $15-25M+/MW | Verified range | JLL 2026: liquid cooling adds about 10%, AI fit-out up to $25M/MW; T&T 2025-26: AI builds +7-10% |
| GB300 NVL72 facility | $19.2M/MW basis -> $19.8M/MW at 8% contingency | $15-25M+/MW | Verified range | as above |
| Vera Rubin facility | $21.6M/MW | $15-25M+/MW | Derived; estimate | interpolated on the density ladder |
| Kyber 600 kW facility | $30.3M/MW | above $25M/MW | **Estimate** | no public cost data yet for 600 kW halls |
| Cost growth | escalation 5%/yr to construction mid-point | 5-6%/yr | Verified | Turner & Townsend Data Centre Construction Cost Index 2025-26 (about 5.5%); C&W 2026 (+21% since Q4 2024) |
| Contingency | 8% (planning) | 5-15% | Assumption | standard planning practice |
| Owner costs | 3% | 2-5% | Assumption | |
| Location factors (N. Virginia = 1.00) | Dallas 0.92, Phoenix 0.90, NY/NJ 1.12, Dublin 0.90, Nordics 1.07, Singapore 1.26, Mumbai 0.58 | ratios of public $/W indices | Derived | T&T 2025-26 ($/W: Singapore 14.5, NJ 12.9, Stockholm 12.3, Dublin 10.0, Phoenix 9.8, Mumbai 6.6); JLL 2026 market ranges |
| Utility interconnection | $80k per MW of service | highly site-specific | Assumption | |
| Land $/acre (powered) | NoVA $2.5M, Dallas $0.5M, Phoenix $0.6M, Singapore $10M, others $0.25-1.5M | NoVA $2.3-3.75M; DFW about $0.5M; Phoenix $0.2-1.0M | Verified (US); assumption (others) | Cushman & Wakefield / JLL land reports 2025 |
| Resilience changes | generators $3.5M per 3 MW (x1.15 N+2, x1.30 2N), UPS $0.6M per MW (x1.2 2N), unit substations $0.45M each, +13% soft cost | | Assumption | unit-rate planning allowances |

**Changed because they were unrealistic:** Dublin was 1.10 (T&T shows Dublin below N. Virginia, so it is now 0.90);
NY/NJ was 1.25 (now 1.12, from the T&T ratio); Mumbai was 0.70 (now 0.58). Utility lead time was 24 months and is now 36
months by default (JLL 2026: grid-connection waits above 4 years in primary markets). The GPU-rental sanity range was
widened for Blackwell (below).

## 3. Energy, water, operations

| Item | Value used | Range | Status | Source |
|---|---|---|---|---|
| PUE, air-cooled | about 1.45 | 1.4-1.55 | Verified | Uptime Institute Global Data Center Survey 2025: average 1.54; new builds 1.48; 20 MW+ sites 1.44 |
| PUE, rear-door hybrid | about 1.35 | 1.3-1.4 | Derived | component model |
| PUE, direct-to-chip | about 1.20 | 1.1-1.25 | Verified range | ASHRAE TC 9.9 liquid cooling guidance; vendor-reported liquid sites |
| Power price, US | $0.075-0.12/kWh | $0.06-0.12 | Verified | US EIA Electric Power Monthly 2026: industrial about 9.0 cents/kWh YTD, 9.8 cents in July |
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

| Item | Value used | Range | Status | Source |
|---|---|---|---|---|
| Power transformers | 128 weeks | 80-210 weeks | Verified | Wood Mackenzie, Q2 2025 supply study (average 128 weeks; GSU 143 weeks) |
| Standby generators | 78-104 weeks | about 1.5-2 years | Verified | industry reporting 2025 on high-horsepower gensets |
| Switchgear, UPS, chillers, CDUs, busway | 16-80 weeks | | Assumption | confirm with vendors |
| Months to utility power (greenfield default) | 36 | 18 to 48+ | Verified range | JLL 2026 |
| Commissioning after power | 6 months | | Assumption | |

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
| 800 VDC readiness | flagged at 400 kW/rack and above | Verified: NVIDIA 800 VDC blog 2025; Schneider Electric |

## 8. Sources

- JLL, *2026 Global Data Center Outlook*.
- Cushman & Wakefield, *Data Center Development Cost Guide 2026*.
- Turner & Townsend, *Data Centre Construction Cost Index 2025-2026*.
- Uptime Institute, *Global Data Center Survey 2025*.
- NVIDIA: GTC 2025 keynote; DGX H100/H200/B200 datasheets; technical blog on 800 VDC architecture (2025).
- HPE, Lenovo and Supermicro GB300 NVL72 specifications (2025-26).
- US Energy Information Administration, *Electric Power Monthly* (2026).
- Wood Mackenzie, power transformer supply study (Q2 2025).
- ASHRAE TC 9.9, liquid cooling guidance for data processing environments.
- US EPA Technology Transitions rule (low-GWP refrigerants for IT cooling, 2027).
- Public GPU rental price trackers (October 2026).
