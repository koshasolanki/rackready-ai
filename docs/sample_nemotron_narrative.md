# Sample Nemotron narrative

_Generated live by `nvidia/Nemotron-3.5-Super-VL` on Nebius Token Factory for the default preset (100 MW AI campus, greenfield, GB300 NVL72, N. Virginia, N+1, 10-year horizon). The numbers come from the deterministic model; the model only writes the text. Indicative planning estimate, not a bid._

## Executive summary
This is a 100 MW greenfield AI campus in Northern Virginia, N+1 (Tier III-style, concurrently maintainable), with 741 NVIDIA GB300 NVL72 racks at 135 kW/rack. Direct-to-chip (D2C) liquid cooling applies because density exceeds 45 kW/rack. Indicative capex is $2.276B: $1.984B facility construction, $59.5M owner costs, $155.2M escalation, $65.5M land (26.2 acres at $2.5M/acre), and $11.9M utility interconnection. IT hardware is $3.464B additional. Year-1 revenue is $2.617B, opex $528.1M/year, NPV $4.225B, payback 3.1 years. Critical path is utility power plus six months commissioning (42 months total); design/permits/construction are 27 months, and transformers (128-week lead, ordered at month 3, plus 3 months install/test) are 35.5 months.

## Assumptions commentary
Engineering quantities: 156 MVA service, three main transformers, 58 IT unit substations, 50 generators, 433,752 gallons fuel, 129 UPS modules and 11,176 kWh battery, 30,024 tons cooling, 67 CDUs, 90,000 kW liquid and 15,593 kW air load, 108,192 kW heat rejection, 20,741 SF white space, 260,000 SF gross, 507 psf, 218 A rack feed and 3,000 A busway. PUE is 1.2 (annual energy ratio, not peak multiplier); WUE is 0.2 L/kWh. All benchmark checks pass: $19.8M/MW IT (range $14–40M/MW), PUE 1.201 (1.1–1.55), power $0.085/kWh ($0.05–0.20), transformer lead 128 weeks (80–210), WUE 0.2 (0–2.6), GPU $7.00/hr ($6–17.80). No warnings are flagged. The 600 kW/rack target is announced roadmap and should be treated as an estimate.

## Design & future-ready recommendation
This is one new build; there is no existing building to retrofit. For the 10-year horizon targeting 600 kW/rack by year 5, the lowest present cost is "Build today + future-ready provisions" at $1,016.4M, versus $1,232.6M for build-today/retrofit-later (4 months downtime) and $1,244.4M for full future build on day one. The recommended path spends $504.9M day one and $961.5M later nominal, with 1 month downtime. Key provisions: structure for 8,000 lb racks (516 psf today) and overhead hanger capacity for liquid headers; liquid headers and pipe galleries for 856 L/min per rack (182 today) with valved taps for 111 future CDUs; busway pathways and tap-off space for 927 A per rack feed (218 today), with 5,000 A row busway or 800 VDC; rack bays at 1,200 x 1,200 mm (600 x 1,068 mm today) and rows for 167 racks; reserved space for 800 VDC conversion (600 kW rack draws 11,111 A at 54 VDC vs 750 A at 800 VDC); and yard space for 107.4 MW heat rejection (108.2 MW today) with warm-water (45 C) dry coolers.

## Key risks
- Utility interconnection drives the 42-month critical path and often takes years; early reservation is essential.
- 128-week transformer lead time requires ordering at month 3; slippage moves ready-for-service.
- D2C leaves a residual air share, so air-side capacity cannot be eliminated.
- 600 kW/rack is announced, not shipping; confirm vendor roadmap and 800 VDC ecosystem before committing provisions.
- Escalation ($155.2M to mid-point) assumes an 18-month window; market shifts could alter this.

## Recommendations & next steps
1. Reserve utility interconnection and deposits now; confirm the $11.9M allowance with the local utility.
2. Order transformers and generators at month 3 to protect the 42-month schedule.
3. Approve future-ready provisions before slab pour; structural and pipe-gallery work is cheap now and near-impossible later.
4. Validate the 135 kW/rack GB300 NVL72 assumption and the 600 kW/rack year-5 target with vendors.
5. Complete detailed electrical and liquid-cooling coordination for 800 VDC readiness and CDU placement before construction.
