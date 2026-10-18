## Executive summary
AI Hall 1 is a 200-rack hall in Northern Virginia, Tier III with N+1 redundancy. The cost engine compares a current air-cooled baseline at 15 kW per rack (3 MW IT, 4.5 MW facility, 15,000 gross sf) against a future-ready closed-loop liquid design at 140 kW per rack (28 MW IT, 32.2 MW facility, 90,000 gross sf). Day-one CAPEX is approximately $37.6M for air versus $384.4M for liquid. Over a 10-year horizon, building future-ready on day one yields an NPV of about $820.1M versus $141.6M for building air now and retrofitting in year 3—a retrofit penalty of roughly $162.5M, plus four months of downtime and $9.3M in lost revenue. The engine recommendation is unambiguous: build future-ready on day one. These figures are indicative planning numbers, not a bid.

## Assumptions commentary
- Region factor is 1.0 for Northern Virginia; power is $0.08/kWh at 80% utilization over 10 years.
- Current state: 200 racks at 15 kW, air-cooled, PUE 1.5. This is within practical air-cooling limits.
- Future state: 200 racks at 140 kW, closed-loop full liquid, PUE 1.15. This exceeds air and rear-door heat exchanger limits and requires CDUs, a technology cooling system secondary loop, rack manifolds, and warm-water heat rejection with dry coolers and trim chillers.
- Structural divisions (03/05/09) must support liquid-cooled racks at 3,000–4,000+ lb each.
- GPU density rises from 1,600 to 14,400 processors, with hourly rates moving from $2.50 to $3.50.
- Annual revenue scales from $28.0M to $353.2M; GPU hardware cost rises from $48.0M to $648.0M.

## Upgrade path recommendation
Path A (future-ready day one): $384.4M CAPEX, 3.21-year simple payback, $820.1M NPV.  
Path B (air now, retrofit in year 3): $37.6M initial plus $499.9M retrofit, totaling $537.5M CAPEX, $141.6M NPV. The retrofit path also forces four months of downtime and $9.3M in lost revenue.  
Path A avoids demolishing recently installed air infrastructure, avoids structural rework under load, and captures liquid-cooling efficiency ($5.5M annual energy savings versus air PUE) immediately. The economic gap is too large to justify deferring liquid infrastructure.

## Key risks
- Long-lead procurement: MV transformers (80–130 weeks), MV switchgear (52–80), diesel generators (52–78), UPS (30–52), chillers/dry coolers (30–50), and CDUs (20–40). Slips here directly delay mechanical completion and revenue.
- Full-liquid complexity at 140 kW/rack: CDU/TCS integration, manifold leakage, and warm-water rejection performance must be validated in design and commissioning.
- Structural capacity: slab and framing must be designed for concentrated liquid-rack loads, not standard air-raised floor loading.
- Revenue concentration: NPV is sensitive to GPU utilization and pricing; the model assumes 80% utilization and $3.50/hr in the future state.
- Tier III N+1 maintenance during any retrofit would challenge concurrent maintainability if Path B were ever revisited.

## Recommendations & next steps
1. Approve Path A and budget approximately $384.4M CAPEX plus $42.9M soft costs and $34.9M contingency as shown.
2. Release early procurement packages immediately for transformers, switchgear, generators, UPS, chillers/dry coolers, and CDUs; use reservation agreements to lock slots.
3. Structure the design schedule through SD, DD, and CD, followed by shell & core, MEP fit-out, and commissioning levels 1–5.
4. Engage a structural engineer early to confirm slab and framing for 3,000–4,000+ lb liquid racks.
5. Validate the GPU-as-a-service revenue model (14,400 GPUs at $3.50/hr, 80% utilization) with offtake or market data before final financial close.