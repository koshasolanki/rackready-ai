"""
RackReady AI - plain-language guide content: common causes of delay with proven fixes, and a
"How it works" glossary of verified generic facts (power path, 800 VDC, cooling types, water, storage).
No project, company or person names. Sources by type here; full URLs in docs/VERIFICATION.md.
"""
from __future__ import annotations

LEGAL = ("Not engineering, legal or financial advice. A licensed professional engineer and the authority having "
         "jurisdiction (AHJ) must review any design before it is used.")
TRADEMARKS = ("NVIDIA, Nebius and product names such as GB300, Vera Rubin and Nemotron are trademarks of their "
              "owners, used only to identify platforms. RackReady AI is not affiliated with or endorsed by them.")

# (cause, what public reporting shows, proven fixes)
DELAYS = [
    ("Power and grid interconnection",
     "Utility interconnection queues and large-load studies now take years in many US markets (2025 consultancy "
     "and industry reports).",
     "Early utility load study and application; phased energization; flexible (curtailable) load agreement; "
     "on-site or bridging power while the grid connection is built."),
    ("Transmission",
     "New load often needs network upgrades before full MW can be served (utility study results).",
     "Phase the MW with the upgrades; site near existing capacity; a flexible-load agreement can unlock "
     "capacity sooner: a 2025 university study estimated about 76 GW of new load could connect if curtailed "
     "about 0.25% of the year."),
    ("Permits and zoning",
     "Local reviews, public hearings, moratoria and new environmental rules lengthen approvals (2025 reporting).",
     "Early environmental review at site selection; pre-application meetings; design to noise, height and "
     "emissions limits from the start."),
    ("Community opposition",
     "A 2025 tracking report counted about $64B of US projects blocked or delayed by local opposition from "
     "May 2024 to March 2025 (power bills, water, noise, property values).",
     "Engage before filing; community benefit agreement; publish the water and power plan; noise and "
     "visual barriers designed in."),
    ("Water",
     "Water use is a leading objection and some utilities cannot commit supply or discharge capacity.",
     "Dry or closed-loop cooling with little or no evaporation; reclaimed water; on-site treatment and reuse."),
    ("Equipment supply",
     "Large transformers average about 2.5 years; big generators and MV switchgear 1-2 years (2025-26 studies "
     "and procurement surveys).",
     "Early equipment reservations with slot deposits (makers commonly ask 10-30%); frame agreements; "
     "specify by rating, not by brand, so several makers can bid."),
    ("Gas pipelines (for on-site power)",
     "On-site gas generation needs firm pipeline capacity and a lateral, which have their own permits.",
     "Confirm firm gas capacity before choosing gas; consider batteries, fuel cells or phased grid power."),
    ("Labor",
     "Electricians, pipefitters and commissioning technicians are short in active markets (2025 reporting).",
     "Labor agreement and workforce plan; modular prefabrication (skids, power modules, pipe racks); "
     "realistic overtime."),
    ("Financing",
     "Lenders and investors want firm power and equipment slots before committing (2025 reporting).",
     "Secure the power agreement first; phase capital with energization steps; engage lenders early."),
]

HOW_TO_AVOID = [
    "Start the utility load study and application at site selection; get firm MW and a date in writing.",
    "Reserve transformer, switchgear and generator slots with deposits before the design is finished.",
    "Energize in phases so the first halls earn revenue while upgrades finish.",
    "Offer a flexible (curtailable) load agreement or bridging power if the grid date is late.",
    "Choose dry or closed-loop cooling where water is scarce or contested.",
    "Engage the community early and agree a community benefit plan before zoning hearings.",
    "Prefabricate power and cooling modules off site and plan the workforce with a labor agreement.",
    "Run environmental review and air permits for generators in parallel with design.",
]

# "How it works": (term, plain explanation). Generic, checked against public engineering references.
HOW_IT_WORKS = [
    ("Grid-to-rack power path", "Utility high-voltage line -> substation transformer -> medium-voltage switchgear -> "
     "unit substation (MV to 415/480 V) -> low-voltage switchboard -> UPS -> busway or PDU -> rack power shelf -> "
     "server power supplies. Generators back up the switchboards; the UPS bridges the seconds until they start."),
    ("800 VDC", "Announced next step for very dense racks: convert AC to 800 V DC centrally and send DC to the racks, "
     "cutting conversion stages and copper (platform maker's public roadmap, from 2027 with MW-class racks)."),
    ("Air cooling", "Computer-room air handlers (CRAH) or fan walls push cooled air through the racks; practical "
     "to about 30 kW per rack."),
    ("Rear-door heat exchanger (RDHx)", "A water coil on the rack door removes heat at the rack; about 45 kW per rack "
     "with air still moving through the servers."),
    ("In-row cooling", "Cooling units placed between racks in the row, close to the heat; a step between room air "
     "and rear doors."),
    ("Direct-to-chip (D2C) liquid", "Cold plates on GPUs and CPUs carry most of the heat in liquid (single-phase "
     "water-glycol, or two-phase with a fluid that boils at the plate); the remaining heat still needs air."),
    ("Immersion (single- and two-phase)", "Servers sit in a tank of dielectric fluid. Single-phase pumps the fluid "
     "through a heat exchanger; two-phase lets it boil and condense. Niche today; some two-phase fluids face "
     "PFAS restrictions."),
    ("Hybrid cooling", "Liquid for the chips plus air (or rear doors) for the remaining heat: how most GPU halls run."),
    ("CDU vs CRAH vs dry cooler", "A CDU (coolant distribution unit) pumps the rack liquid loop and passes its heat to "
     "facility water. A CRAH cools room air with chilled water. A dry cooler rejects facility-water heat to outdoor "
     "air with fans and no water use."),
    ("Busway", "Prefabricated copper or aluminum bars in a housing with plug-in tap-off boxes: feeds rows of racks "
     "faster and more flexibly than cable."),
    ("Insulation", "Pipe insulation stops condensation and heat gain on chilled-water lines; warm-water liquid loops "
     "run above the dew point. Electrical insulation is proven by insulation-resistance (megger) tests before "
     "energizing."),
    ("Energy storage", "UPS batteries ride through for minutes until generators start. A battery energy storage "
     "system (BESS) stores hours of energy for peak shaving, grid support or bridging, and must follow NFPA 855 "
     "with UL 9540A fire-test data."),
    ("Water and wastewater", "Evaporative towers lose water to evaporation and blowdown and need chemical treatment and "
     "a Legionella plan (ASHRAE 188). Closed liquid loops need filtration and coolant chemistry. Dry coolers use "
     "little or no water."),
]

# Illustrative split of $100 of AI data center capex (from the user's reference image), checked against a
# public 2025 consultancy estimate of AI data center investment to 2030 (60% chips and computing hardware,
# 25% power, cooling and electrical, 15% land, materials and site). Broadly consistent: shown as illustrative.
CAPEX_SPLIT = [("Chips and servers", 50.0), ("Networking", 15.0), ("Power", 20.0), ("Cooling", 7.5),
               ("Facilities", 7.5)]
CAPEX_PUBLIC = [("Chips and computing hardware", 60.0), ("Power, cooling and electrical", 25.0),
                ("Land, materials and site", 15.0)]
CAPEX_NOTE = ("Illustrative only. A public 2025 consultancy estimate splits AI data center investment about "
              "60% chips and computing hardware, 25% power, cooling and electrical and 15% land, materials and site, "
              "broadly in line with this split. Your project's own split is in the cost lines above.")
