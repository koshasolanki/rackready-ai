# Sample inputs and demo script

All numbers come from the built-in model at default settings (indicative planning estimate, not a bid; 2026 USD).
Choose a preset in the sidebar, then change any input; results update automatically.

## Preset 1 (default): 100 MW AI campus, greenfield, GB300 NVL72
| Input | Value |
|---|---|
| Project type / size | Greenfield, 100 MW IT |
| GPU platform | NVIDIA GB300 NVL72 (135 kW/rack, 155 kW peak, 72 GPUs) |
| Location / redundancy | US - Northern Virginia / N+1 |
| Future-proof horizon | 10 years (600 kW/rack, Kyber class, year 5) |

Expected: **741 racks**, D2C liquid (auto, above 45 kW/rack), PUE **1.20**, utility **156 MVA**, **50** x 3 MW
generators, **129** x 1 MW UPS modules, **30,024 tons**, **67 CDUs**, liquid flow **2,252 L/s**, 260,000 sf on 26.2 acres.
Total project cost **$2.28B** (**$22.8M/MW** including land, interconnection, owner costs and escalation; facility
construction $19.8M/MW), IT hardware **$3.46B**, payback **3.1 years**, ready for service in about **42 months**
(utility power is the critical path). Future-ready paths (present cost): retrofit later $1,233M, **provisions now
$1,016M** (recommended), full future build $1,244M.

## Preset 2: 10 MW edge AI hall, greenfield, H200 HGX, Dallas
42 kW/rack, so you can choose the cooling: rear-door hybrid. 239 racks, PUE **1.35**, WUE **2.28 L/kWh** (towers),
18 MVA, 6 generators, 3,002 tons. Total **$181.3M** (**$18.1M/MW**), IT **$340.7M**, payback **6.7 years**.
5-year horizon (230 kW): provisions now **$44M** vs retrofit later $65M vs full build $49M.

## Preset 3: existing-hall fit-out, 200 racks, 15 kW air to GB300 NVL72
Current fit-out **$39.0M** (3 MW IT) vs future-ready **$352.1M** (27 MW IT, **$13.0M/MW**, D2C auto). Building current
now and retrofitting in year 3 costs **$556.8M** including 4 months of downtime, so the model recommends **fit out
future-ready now** (NPV $1.63B vs $0.62B). The utility service upgrade (transformers about 128 weeks) sets the
schedule at about 32 months.

## More scenarios
| Scenario | Inputs | Expected |
|---|---|---|
| D2C switch | Greenfield, Custom density 40 then 50 kW/rack, 20 MW, Dallas, Hybrid chosen | 40 kW: Hybrid, PUE 1.35, $18.1M/MW. 50 kW: D2C selected automatically (warning shown), PUE 1.20, $19.1M/MW |
| Premium 2N | Greenfield, 50 MW GB200 NVL72, Singapore, 2N, 15-year horizon | $1.76B ($35.2M/MW), 44 generators, provisions now recommended |
| Kyber campus | Greenfield, 200 MW Rubin Ultra NVL576 (Kyber), Phoenix | 334 racks at 600 kW, $6.31B ($31.5M/MW), 313 MVA (transmission-level substation warning), roadmap warning |
| Colo upgrade | Fit-out, 100 racks, 12 kW to B200 HGX, Dallas | $15.1M current vs $72.7M future-ready ($12.8M/MW); fit out future-ready now |

## 60-second demo script
1. Open the default preset: point at the four summary cards and the recommendation.
2. **Design calculations**: scroll power, cooling and floor loading; switch to "Future target (600 kW/rack)".
3. **Future-ready**: the three paths and the provisions list (800 VDC space, slab, headers).
4. Change the platform to Custom 40 kW, then 50 kW: the cooling locks to D2C above 45 kW.
5. Switch the preset to the existing-hall fit-out: current vs future-ready vs retrofit later.
6. Download the one-page PDF. Open the narrative written by NVIDIA Nemotron on Nebius Token Factory.
