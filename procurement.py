"""
RackReady AI - US procurement view of the long-lead packages.

This is the ONLY module that names companies. Each supplier is listed because a public source shows it
makes that equipment category for large US data center or utility projects (manufacturer product page or
US plant announcement); the source type is shown in the app and the full URL is in docs/VERIFICATION.md.
Listed alphabetically; no rankings, no market-share claims, no logos.
"""
from __future__ import annotations

import buildcx as CX

DISCLAIMER = "Listed alphabetically for reference; not exhaustive, not an endorsement; no affiliation."

TARIFF_2026 = ("Section 232 (proclamation of 2 Apr 2026, amended 1 Jun 2026): 50% duty on steel, aluminum and "
               "copper products, 25% on derivative products, and a temporarily reduced 15% on fixed industrial "
               "machinery and power equipment. Country-specific tariffs can apply on top. Check the current "
               "schedule when you order.")

# supplier: (name, evidence, source type, url)
S = {
    "Aurora (Pentair)": ("UL-listed, FM-approved split-case fire pumps (NFPA 20)", "Manufacturer product page",
                         "https://www.pentair.com/en-us/flow/aurora-brand-page/aurora-products/aurora-horizontal-split-case-electric-drive-fire-pump-series-912.html"),
    "AFL": ("US fiber optic cable manufacturing expansion, South Carolina (2024)", "Manufacturer press release",
            "https://www.aflglobal.com/en/company/company-profile/news/2024/afl-announces-a-multi-million-dollar-investment-and-expansion-to-its-us-fiber-optic-cable"),
    "Carrier": ("Water-cooled centrifugal chiller for data centers", "Manufacturer product page",
                "https://www.carrier.com/commercial/en/us/19mv/data-center/"),
    "Caterpillar": ("Lafayette, Indiana large-engine and genset expansion for data center backup power (2024)",
                    "Manufacturer press release",
                    "https://www.caterpillar.com/en/news/corporate-press-releases/h/lafayette-large-engine-expansion.html"),
    "CommScope": ("US fiber cable manufacturing expansion, Catawba County, North Carolina (2023)",
                  "Manufacturer press release",
                  "https://www.businesswire.com/news/home/20230726503630/en/CommScope-Announces-Fiber-Cable-Manufacturing-Expansion-in-North-Carolina"),
    "Corning": ("Optical cable manufacturing expansion, Hickory, North Carolina", "Local government press release",
                "https://hickorync.gov/corning-expand-operations-trivium-plans-add-132-jobs-and-invest-170m-2679m"),
    "Cummins": ("QSK95 data center generator sets; engines built in Seymour, Indiana", "Manufacturer press release",
                "https://www.cummins.com/en-na/news/releases/2020/12/21/cummins-qsk95-diesel-generator-series-reaches-1000th-unit-milestone"),
    "Eaton": ("UPS made in the Raleigh, North Carolina area; metal-clad MV switchgear; busway",
              "Manufacturer press release and product pages",
              "https://www.eaton.com/us/en-us/company/news-insights/news-releases/2022/eaton-reinvests-in-north-carolina.html"),
    "Flex (JetCool)": ("Coolant distribution units for AI/HPC; US manufacturing sites", "Manufacturer press release",
                       "https://investors.flex.com/news/news-details/2025/Flexs-Liquid-Cooling-Business-Expands-Portfolio-with-High-Performance-Coolant-Distribution-Unit-for-AI-and-HPC-Applications/default.aspx"),
    "Fluence": ("Battery storage with US-made cells, modules and enclosures", "Manufacturer page",
                "https://fluenceenergy.com/domestic-content/"),
    "Hitachi Energy": ("Large power transformer factory, South Boston, Virginia (announced 2025)",
                       "Manufacturer press release",
                       "https://www.hitachienergy.com/us/en/news-and-events/press-releases/2025/09/hitachi-announces-historic-1-billion-usd-manufacturing-investment-to-power-america-s-energy-future-through-production-of-critical-grid-infrastructure"),
    "Hyosung HICO": ("Large power transformer plant, Memphis, Tennessee; expansions announced 2025 (+50% capacity)",
                     "Manufacturer press release",
                     "https://www.hyosunghico.com/blog/powering-americas-future-hyosung-hico-expands-memphis-headquarters"),
    "Johnson Controls (YORK)": ("Air-cooled magnetic-bearing chillers for data centers", "Manufacturer product page",
                                "https://www.york.com/commercial-equipment/chilled-water-systems/air-cooled-chillers/yvam_ch/yvam-air-cooled-magnetic-bearing-centrifugal-chiller"),
    "Legrand (Starline)": ("Track busway for data centers", "Manufacturer product page",
                           "https://www.legrand.com/datacenter/en/grey-space/busbar-busway/starline-track-busway"),
    "LG Energy Solution Vertech": ("LFP energy-storage cell production, Holland, Michigan", "Trade press",
                                   "https://www.canarymedia.com/articles/energy-storage/lg-michigan-lfp-battery-factory"),
    "Mitsubishi Electric Power Products": ("UPS and switchgear for US data centers (Warrendale, Pennsylvania)",
                                           "Manufacturer press release",
                                           "https://www.meppi.com/news/mitsubishi-electric-to-provide-integrated-power-protection-and-it-cooling-solutions-for-us-data-center-applications"),
    "Modine": ("US chiller production expansion for data centers (Grenada, Mississippi)", "Manufacturer press release",
               "https://investors.modine.com/news/news-details/2025/Modine-Expands-U-S--Chiller-Production-Capacity-to-Serve-Data-Center-Customers/default.aspx"),
    "Motivair (Schneider Electric)": ("CDUs built in Buffalo, New York", "Manufacturer press release",
                                      "https://www.motivaircorp.com/news/motivair-by-schneider-electric-expands-u-s-manufacturing-footprint/"),
    "Munters": ("Data center cooling factory expansion, Virginia (2025)", "Manufacturer press release",
                "https://www.munters.com/en-us/news-media/stories/2025/munters-to-expand-its-data-center-technology-factory-in-virginia/"),
    "Patterson Pump": ("UL-listed, FM-approved split-case fire pumps", "Manufacturer product page",
                       "https://pattersonpumps.com/markets/fire-pumps/horizontal-split-case-fire/"),
    "Peerless Pump": ("UL/FM split-case fire pumps (NFPA 20)", "Manufacturer product page",
                      "https://www.peerlesspump.com/products/fire/aef/"),
    "Powell Industries": ("ANSI metal-clad MV switchgear (Houston, Texas)", "Manufacturer product page",
                          "https://www.powellind.com/ansi-metal-clad-switchgear"),
    "Prolec GE": ("US transformer plant investment, North Carolina", "Manufacturer press release",
                  "https://www.prolec.energy/news/prolec-ge-invests-an-additional-140-million-in-the-u-s-to-support-north-american-electric-grid-goals/"),
    "Prysmian": ("US optical cable plants (Tennessee, North Carolina)", "Manufacturer press release",
                 "https://na.prysmian.com/resources/press-releases/prysmian-partners-with-dow-to-advance-production-of-sirocco-microduct-cables"),
    "Rehlko": ("Diesel generators up to about 4 MW for data centers", "Manufacturer product page",
               "https://www.powersystems.rehlko.com/data-center"),
    "Rolls-Royce (mtu)": ("Series 4000 data center generator sets, Mankato, Minnesota expansion (2026)",
                          "Manufacturer press release",
                          "https://www.rolls-royce.com/media/press-releases/2026/09-07-2026-rr-cuts-ribbon-on-new-usd-24m-expansion-in-mankato-minnesota.aspx"),
    "Schneider Electric": ("US plants for MV equipment (Tennessee) and switchgear (Texas, North Carolina); data center UPS",
                           "Manufacturer press release and product page",
                           "https://www.se.com/us/en/about-us/newsroom/news/press-releases/Schneider-Electric-Plans-to-Invest-Over-700-million-in-the-U-S-Supporting-Energy-AI-Sectors-and-Job-Growth-67bdeb3ee4475a5955011b6a/"),
    "Siemens": ("Fort Worth, Texas plant for low-voltage switchboards for AI infrastructure", "Manufacturer press release",
                "https://news.siemens.com/en-us/siemens-opens-190m-ft-worth-mfg-hub-ai-infrastructure/"),
    "Siemens Energy": ("Large power transformer factory, Charlotte, North Carolina (production from 2027)",
                       "Manufacturer press release",
                       "https://www.siemens-energy.com/us/en/home/press-releases/siemens_energy_addresses_shortage_US_powertransformers_invests_new_factory.html"),
    "Tesla": ("Megapack battery storage built in Lathrop, California; data center use", "Manufacturer product page",
              "https://www.tesla.com/megapack"),
    "Toshiba International": ("UPS and power electronics made in Houston, Texas", "Manufacturer page",
                              "https://toshiba.com/tic/about-us/company-overview/"),
    "Trane": ("Data center chillers", "Manufacturer product page",
              "https://www.trane.com/commercial/north-america/us/en/products-systems/chillers/data-center-chillers.html"),
    "Vertiv": ("Data center UPS and CDUs; US manufacturing sites", "Manufacturer product pages",
               "https://www.vertiv.com/en-us/products-catalog/thermal-management/high-density-solutions/vertiv-coolchip-cdu/"),
    "Virginia Transformer": ("Power transformer plant expansion, Rincon, Georgia", "Manufacturer press release",
                             "https://www.vatransformer.com/expand-georgia-transformer-plant-in-rincon/"),
}
# Extra product-page URLs for suppliers listed in more than one package (VERIFICATION.md lists them all)
EXTRA_URLS = {
    ("Eaton", "MV switchgear"): "https://www.eaton.com/us/en-us/catalog/medium-voltage-power-distribution-control-systems/vacclad-w-5-15-kv-metal-clad-medium-voltage-switchgear.html",
    ("Eaton", "Busway"): "https://www.eaton.com/us/en-us/catalog/low-voltage-power-distribution-controls-systems/pow-r-way-III-busway.html",
    ("Schneider Electric", "UPS"): "https://www.se.com/us/en/work/products/master-ranges/galaxy/",
    ("Vertiv", "UPS"): "https://www.vertiv.com/en-us/products-catalog/critical-power/uninterruptible-power-supplies-ups/liebert-exl-s1/",
}

_LT = {k: (lo, hi) for k, _n, lo, hi, _t, _s in CX.LEAD_TIMES}

# package: lead key or (lo, hi), US supply note, domestic vs imported, risk, suppliers
PACKAGES = [
    {"package": "Large power transformers", "lead": _LT["main_tx"],
     "lead_basis": "2025 transformer supply study (average about 128 weeks) and 2026 quotes",
     "us_suppliers": "Few US plants: 5 verified below, several new plants due 2027-2028",
     "domestic": "About 18% US-made, 82% imported (US government data for 2019, in a 2024 DOE report); "
                 "US plants ran at about 40% of a roughly 343 units/year capacity",
     "risk": "High: power transformers about 30% short of demand in 2025 (industry study); specialty steel "
             "(GOES) about 80% imported; metal tariffs apply.",
     "suppliers": ["Hitachi Energy", "Hyosung HICO", "Prolec GE", "Siemens Energy", "Virginia Transformer"]},
    {"package": "MV switchgear", "lead": (_LT["mv_swgr_15"][0], _LT["mv_swgr_38"][1]),
     "lead_basis": "2026 procurement surveys: 15 kV 52-80 weeks, 38 kV 78-104 weeks",
     "us_suppliers": "Several with US plants: 3 verified below",
     "domestic": "No public split found; most US data center gear is assembled in US plants with imported parts",
     "risk": "Medium-high: 38 kV class has the fewest makers; copper and steel tariffs.",
     "suppliers": ["Eaton", "Powell Industries", "Schneider Electric"]},
    {"package": "Standby generators", "lead": _LT["gens"],
     "lead_basis": "2026 procurement surveys: 62-82 weeks at 2.5-3.5 MW, 90-110 weeks above 3.5 MW",
     "us_suppliers": "Several with US engine or genset plants: 4 verified below",
     "domestic": "No public split found; large engines are built in US and overseas plants",
     "risk": "High: large sets are slot-limited; air permits and fuel storage also take time.",
     "suppliers": ["Caterpillar", "Cummins", "Rehlko", "Rolls-Royce (mtu)"]},
    {"package": "UPS", "lead": _LT["ups"], "lead_basis": "2026 procurement surveys: 30-48 weeks, modular 40-60",
     "us_suppliers": "Several with US plants: 5 verified below",
     "domestic": "No public split found; batteries (lithium-ion cells) are mostly imported",
     "risk": "Medium: battery cells and electronics are tariff-exposed.",
     "suppliers": ["Eaton", "Mitsubishi Electric Power Products", "Schneider Electric", "Toshiba International", "Vertiv"]},
    {"package": "Busway", "lead": _LT["busway"], "lead_basis": "2026 manufacturer schedules; tap-off units often longer",
     "us_suppliers": "Several: 2 verified below", "domestic": "No public split found",
     "risk": "Medium: copper or aluminum content is tariff-exposed.", "suppliers": ["Eaton", "Legrand (Starline)"]},
    {"package": "Chillers and dry coolers", "lead": _LT["chillers"], "lead_basis": "2026 consultant survey: 40-70 weeks",
     "us_suppliers": "Many with US plants: 5 verified below", "domestic": "No public split found",
     "risk": "Medium: large magnetic-bearing and air-cooled units are slot-limited.",
     "suppliers": ["Carrier", "Johnson Controls (YORK)", "Modine", "Munters", "Trane"]},
    {"package": "CDUs", "lead": _LT["cdus"], "lead_basis": "2026 consultant survey: 30-50 weeks",
     "us_suppliers": "Growing: 3 verified below with US production", "domestic": "No public split found",
     "risk": "Medium: new product category; agree the coolant spec with the IT vendor early.",
     "suppliers": ["Flex (JetCool)", "Motivair (Schneider Electric)", "Vertiv"]},
    {"package": "Switchboards (LV)", "lead": _LT["lv_swbd"], "lead_basis": "2026 manufacturer schedules and surveys",
     "us_suppliers": "Several with US plants: 2 verified below", "domestic": "No public split found",
     "risk": "Medium: breakers and copper bus; tariffs.", "suppliers": ["Schneider Electric", "Siemens"]},
    {"package": "Fiber and optics", "lead": _LT["fiber"],
     "lead_basis": "Carrier lateral builds 6-18 months; cable from stock to a few months",
     "us_suppliers": "Fiber cable: several US plants, 4 verified below. Optical transceivers: no US maker verified",
     "domestic": "No public split found",
     "risk": "Medium: carrier permits and make-ready work drive the lateral date; transceivers are tariff-exposed.",
     "suppliers": ["AFL", "CommScope", "Corning", "Prysmian"]},
    {"package": "Fire pumps", "lead": _LT["fire"], "lead_basis": "Typical 2026 quotes: 20-36 weeks",
     "us_suppliers": "Several US makers: 3 verified below", "domestic": "No public split found",
     "risk": "Low-medium: diesel drivers and controllers set the date.",
     "suppliers": ["Aurora (Pentair)", "Patterson Pump", "Peerless Pump"]},
    {"package": "Battery energy storage (BESS)", "lead": (22, 35),
     "lead_basis": "2026 trade press: factory 12-26 weeks plus shipping and haul, about 5-8 months to the pad",
     "us_suppliers": "US cell and system production ramping: 3 verified below",
     "domestic": "No public split found; most cells are imported, US cell plants started 2025",
     "risk": "High: cell tariffs and domestic-content rules change often; NFPA 855 and UL 9540A data needed for permits.",
     "suppliers": ["Fluence", "LG Energy Solution Vertech", "Tesla"]},
]


def rows() -> list[dict]:
    out = []
    for p in PACKAGES:
        lo, hi = p["lead"]
        out.append({"Package": p["package"], "2026 lead time (weeks)": f"{lo}-{hi}",
                    "Qualified US suppliers (approx.)": p["us_suppliers"], "Domestic vs imported": p["domestic"],
                    "Tariff and capacity risk": p["risk"],
                    "Verified suppliers (A-Z)": ", ".join(sorted(p["suppliers"], key=str.lower)),
                    "Lead-time source type": p["lead_basis"]})
    return out


def supplier_rows() -> list[dict]:
    out = []
    for p in PACKAGES:
        for n in sorted(p["suppliers"], key=str.lower):
            ev, typ, url = S[n]
            out.append({"Package": p["package"], "Supplier": n, "What the source shows": ev, "Source type": typ,
                        "URL": EXTRA_URLS.get((n, p["package"].split(" (")[0]), url)})
    return out
