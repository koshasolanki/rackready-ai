"""
RackReady AI - codes and standards to follow (US), plus a "Confirm locally" checklist.

Editions are the latest published editions shown on each publisher's own site (checked Oct 2026; URLs in
docs/VERIFICATION.md). The edition that applies to a project is the one the local authority having
jurisdiction (AHJ) has adopted, often one or two cycles older, with local amendments.
"""
from __future__ import annotations

# (code, title, latest edition, publisher, what it covers in one plain line, group)
CODES = [
    ("NFPA 70", "National Electrical Code (NEC)", "2026", "NFPA",
     "Wiring, overcurrent protection, grounding and equipment installation for all electrical work.", "Electrical"),
    ("NFPA 70E", "Electrical Safety in the Workplace", "2027", "NFPA",
     "Safe work practices around energized equipment: arc-flash and shock risk assessment, PPE.", "Electrical"),
    ("NFPA 110", "Emergency and Standby Power Systems", "2025", "NFPA",
     "Generator systems: transfer within 10 seconds (Type 10), fuel, installation and acceptance testing.", "Electrical"),
    ("NFPA 111", "Stored Electrical Energy Emergency and Standby Power Systems", "2025", "NFPA",
     "Battery/UPS-based emergency and standby power: performance, installation and testing.", "Electrical"),
    ("IEEE 1584", "Guide for Performing Arc-Flash Hazard Calculations", "2018", "IEEE",
     "How to calculate incident energy and arc-flash boundaries for equipment labels.", "Electrical"),
    ("IEEE C57 series", "Power and distribution transformers (e.g. C57.12.00 general requirements)", "C57.12.00-2021",
     "IEEE", "Ratings, construction and testing of liquid-immersed transformers.", "Electrical"),
    ("NESC (IEEE C2)", "National Electrical Safety Code", "2023", "IEEE",
     "Utility-side lines and substations: clearances, grounding and safety (the utility side of the meter).", "Electrical"),
    ("NFPA 13", "Installation of Sprinkler Systems", "2025", "NFPA",
     "Sprinkler design, including the pre-action systems common in data halls.", "Fire and life safety"),
    ("NFPA 20", "Installation of Stationary Pumps for Fire Protection", "2025", "NFPA",
     "Fire pumps, drivers, controllers and acceptance tests.", "Fire and life safety"),
    ("NFPA 22", "Water Tanks for Private Fire Protection", "2023", "NFPA",
     "Design and installation of fire-water storage tanks.", "Fire and life safety"),
    ("NFPA 72", "National Fire Alarm and Signaling Code", "2025", "NFPA",
     "Fire detection and alarm, including air-sampling smoke detection and notification.", "Fire and life safety"),
    ("NFPA 75", "Fire Protection of Information Technology Equipment", "2024", "NFPA",
     "Fire protection for IT equipment rooms: construction, detection, suppression.", "Fire and life safety"),
    ("NFPA 76", "Fire Protection of Telecommunications Facilities", "2024", "NFPA",
     "Fire protection for telecom spaces such as meet-me and network rooms.", "Fire and life safety"),
    ("NFPA 2001", "Clean Agent Fire Extinguishing Systems", "2025", "NFPA",
     "Gaseous clean-agent suppression: design concentration, room integrity (door-fan) testing.", "Fire and life safety"),
    ("NFPA 855", "Installation of Stationary Energy Storage Systems", "2026", "NFPA",
     "Battery energy storage: spacing, size limits, ventilation, explosion control, fire testing data.", "Fire and life safety"),
    ("NFPA 101", "Life Safety Code", "2027", "NFPA",
     "Egress, occupancy and life-safety features for people in the building.", "Fire and life safety"),
    ("NFPA 30", "Flammable and Combustible Liquids Code", "2027", "NFPA",
     "Storage and handling of liquids such as generator diesel (tanks, containment, piping).", "Fire and life safety"),
    ("NFPA 37", "Stationary Combustion Engines and Gas Turbines", "2024", "NFPA",
     "Installation of generator engines and turbines: fuel, exhaust, enclosures, separation.", "Fire and life safety"),
    ("UL 9540", "Energy Storage Systems and Equipment", "3rd edition (2023, revised 2025)", "UL Standards & Engagement",
     "Safety listing of complete battery energy storage systems.", "Fire and life safety"),
    ("UL 9540A", "Test Method for Thermal Runaway Fire Propagation in Battery Systems", "5th edition (2025)",
     "UL Standards & Engagement", "Cell-to-unit fire tests that NFPA 855 and the IFC use for spacing and protection.",
     "Fire and life safety"),
    ("IBC", "International Building Code", "2027", "ICC",
     "Construction type, height and area, structure, fire-resistance and egress.", "Building codes"),
    ("IFC", "International Fire Code", "2027", "ICC",
     "Fire department access, fire protection systems, batteries and hazardous materials in use.", "Building codes"),
    ("IMC", "International Mechanical Code", "2027", "ICC",
     "HVAC equipment, ventilation, refrigeration machinery rooms and ductwork.", "Building codes"),
    ("IPC", "International Plumbing Code", "2027", "ICC",
     "Water supply, drainage, fixtures and backflow protection.", "Building codes"),
    ("IECC", "International Energy Conservation Code", "2027", "ICC",
     "Building energy efficiency; data centers usually comply through ASHRAE 90.4 where adopted.", "Building codes"),
    ("ASHRAE 90.4", "Energy Standard for Data Centers", "2025", "ASHRAE",
     "Maximum mechanical and electrical loss for data centers (energy compliance path).", "Mechanical and energy"),
    ("ASHRAE TC 9.9", "Thermal Guidelines for Data Processing Environments", "5th edition (revised and expanded)",
     "ASHRAE", "Recommended and allowable inlet air and liquid-cooling temperature classes for IT.",
     "Mechanical and energy"),
    ("ASHRAE 188", "Legionellosis: Risk Management for Building Water Systems", "2021", "ASHRAE",
     "Water management program for cooling towers and other building water systems.", "Mechanical and energy"),
    ("TIA-942", "Telecommunications Infrastructure Standard for Data Centers", "TIA-942-C (2024)", "TIA",
     "Data center cabling, spaces, pathways and infrastructure ratings.", "Telecom"),
    ("BICSI 002", "Data Center Design and Implementation Best Practices", "2024", "BICSI",
     "Design best practice across power, cooling, cabling and security.", "Telecom"),
    ("OSHA 29 CFR 1926", "Safety and Health Regulations for Construction", "Current eCFR", "US Department of Labor",
     "Construction safety: excavation, fall protection, cranes, electrical work on site.", "Safety and environment"),
    ("OSHA 29 CFR 1910", "Occupational Safety and Health Standards (general industry)", "Current eCFR",
     "US Department of Labor", "Operations-phase safety: lockout/tagout, electrical safe work, PPE.",
     "Safety and environment"),
    ("EPA SPCC (40 CFR 112)", "Spill Prevention, Control and Countermeasure", "Current eCFR", "US EPA",
     "Spill plans and containment when oil storage (e.g. generator diesel) exceeds 1,320 gal aboveground.",
     "Safety and environment"),
    ("FAA 14 CFR Part 77", "Safe, Efficient Use and Preservation of the Navigable Airspace", "Current eCFR (Form 7460-1)",
     "FAA", "Notice to the FAA for tall structures or cranes near airports.", "Safety and environment"),
    ("ADA Standards", "2010 ADA Standards for Accessible Design", "2010", "US Department of Justice / Access Board",
     "Accessibility of the occupied areas (offices, entrances, restrooms).", "Safety and environment"),
    ("Local AHJ amendments", "State and local amendments to the adopted codes", "As adopted locally", "Local AHJ",
     "Local changes, adopted editions and permit conditions that override the model codes.", "Local"),
]

CONFIRM_LOCALLY = [
    "Adopted edition of each code (states often enforce an edition one or two cycles older than the latest).",
    "Local amendments to the building, fire, electrical and energy codes.",
    "Utility interconnection rules: large-load tariff, study process, deposits, protection and metering requirements.",
    "Environmental and air permits for generators (run-hour limits, emissions, testing schedule).",
    "Noise limits at the property line (generators, cooling equipment, transformers).",
    "Water supply, wastewater discharge and stormwater permits.",
    "Fire marshal requirements: access roads, water supply, battery rooms, clean agent, pre-incident plan.",
]

CODES_NOTE = ("Latest editions as published (checked Oct 2026). The edition that applies is the one your "
              "jurisdiction adopted: confirm with the AHJ.")


def codes_rows() -> list[dict]:
    return [{"Code": c, "Title": t, "Latest edition": e, "Publisher": p, "What it covers": w, "Group": g}
            for c, t, e, p, w, g in CODES]
