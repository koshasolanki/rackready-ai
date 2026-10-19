# Sample inputs and demo script

All numbers come from the built-in model at default settings (early budget estimate, ±30–50%, not a bid; 2026 USD). Totals use the
default "Include in total" ticks: every cost line except on-site/bridging power, GPU hardware and the AI fabric.
Choose a preset in the sidebar, then change any input; results update automatically.

## Preset 1 (default): 100 MW AI campus, greenfield, GB300 NVL72
| Input | Value |
|---|---|
| Project type / size | Greenfield, 100 MW IT |
| GPU platform | NVIDIA GB300 NVL72 (135 kW/rack, 155 kW peak, 72 GPUs) |
| Location / redundancy | US - Northern Virginia / N+1 |
| Future-proof horizon | 10 years (600 kW/rack Kyber-class target installed in year 5 after ready for IT) |

Expected: **741 racks**, D2C liquid (auto, above 45 kW/rack), PUE **1.20**, utility **156 MVA**, **50** x 3 MW
generators, **129** x 1 MW UPS modules, **30,024 tons**, **67 CDUs**, liquid flow **2,252 L/s**, 260,000 sf on 26.2 acres.
Total project cost **$2.33B** (**$23.3M/MW**, the sum of the 10 default cost lines; facility construction
$19.8M/MW). With every line ticked (adds on-site/bridging power $284.0M, GPU hardware $2.96B, AI fabric $500.0M):
**$6.08B** ($60.8M/MW). IT hardware with fabric **$3.46B**, payback **3.1 years**.
Schedule: notice to proceed about month 10, build 24 months (auto), **ready for IT about 41–51 months from start**
(typical 43; the large power transformers are the critical path; RFQ now). MV switchgear and generators must be ordered before notice to proceed.
Fire: 542.5 gpm demand, 750 gpm pump, 32,550 gal; clean agent 2,047 lb. Future-ready paths (present cost): retrofit
later $1.23B, **provisions now $1.02B** (the verdict), full future build $1.24B.

## Preset 2: 10 MW edge AI hall, greenfield, H200 HGX, Dallas
42 kW/rack, so you can choose the cooling: rear-door hybrid. 239 racks, PUE **1.35**, WUE **2.28 L/kWh** (towers),
18 MVA, 6 generators, 3,002 tons. Total **$188.1M** (**$18.8M/MW**; every line ticked $561.6M), IT **$340.7M**,
payback **6.7 years**. Build auto 15.8 months; ready for IT about 26–38 months from start (power-chain long-lead
equipment is the critical path).
5-year horizon (230 kW): provisions now **$44M** vs retrofit later $65M vs full build $49M.

## More scenarios
| Scenario | Inputs | Expected |
|---|---|---|
| D2C switch | Greenfield, Custom density 40 then 50 kW/rack, 20 MW, Dallas, Hybrid chosen | 40 kW: Hybrid, PUE 1.35, $18.2M/MW. 50 kW: D2C selected automatically (warning shown), PUE 1.20, $19.3M/MW |
| Premium 2N | Greenfield, 50 MW GB200 NVL72, Singapore, 2N, 15-year horizon | $1.79B ($35.8M/MW), 44 generators, provisions now recommended |
| Kyber campus | Greenfield, 200 MW Rubin Ultra NVL576 (Kyber), Phoenix | 334 racks at 600 kW, $6.52B ($32.6M/MW), 313 MVA (transmission-level substation warning), roadmap warning |

## 60-second demo script
1. Default preset: the four cards (total, cost per MW, payback, ready-for-IT months) and the one-line verdict.
2. **Costs**: tick GPU hardware and watch the total and cost per MW change everywhere, PDFs included.
3. **Future-ready**: retrofit later vs provisions now vs full build, and the provisions to build in.
4. **Design calculations**: power, cooling and floor loading; switch to "Future target (600 kW/rack)".
5. **Schedule & risks**: the Gantt, what sets the finish and when to order (transformers: send the RFQ now).
6. **Codes & procurement**: latest code editions, Confirm locally and US lead times.
7. **Build & commission**: the liquid-loop hard stop, L1-L5 and IST scenarios; download the checklist PDF.
8. Sidebar: Custom density 40 kW, then 50 kW: the cooling locks to D2C above 45 kW.
9. Preset: 10 MW edge AI hall (H200 HGX): rear-door hybrid cooling, $188.1M, provisions now for the 5-year horizon.
10. Open the narrative written by NVIDIA Nemotron on Nebius Token Factory and download the one-page PDF.
