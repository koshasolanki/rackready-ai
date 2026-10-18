"""
RackReady AI - LLM narrative layer (OpenAI-compatible: Nebius Token Factory + NVIDIA Nemotron)
with a rule-based fallback so the demo never breaks.
"""
from __future__ import annotations

import json
import os
from typing import Iterator

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_MODEL = "nvidia/Nemotron-3.5-Super-VL"
SUGGESTED_MODELS = [
    "nvidia/Nemotron-3.5-Super-VL",
    "nvidia/Nemotron-3-Ultra-550b-a55b",
    "nvidia/Nemotron-3_5-Lightning",
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
]

SYSTEM_PROMPT = """You are RackReady AI, a senior data center cost manager and estimator with 20+ years
on hyperscale and AI/HPC projects. You write for owners, developers and general contractors.

Domain you apply:
- High-density AI racks: today's 10-20 kW air-cooled racks versus 40-140+ kW GPU racks
  (GB200/GB300 NVL72 class at ~120-140 kW). Air cooling tops out near 30 kW/rack; rear-door
  heat exchangers (RDHx) extend to ~50 kW; above that you need direct-to-chip liquid or a
  closed-loop full liquid design with CDUs, a technology cooling system (TCS) secondary loop,
  rack manifolds and warm-water heat rejection (dry coolers) with trim chillers.
- Power distribution: MV service, transformers, switchgear, UPS, generators, overhead
  high-amp busway with tap-off boxes versus whips from PDUs/RPPs, 415/240 V distribution.
- CSI MasterFormat: Div 03/05/09 (concrete, steel, finishes, incl. slab loading for
  3,000-4,000+ lb liquid-cooled racks), Div 21 fire suppression, Div 23 HVAC/mechanical,
  Div 26 electrical, Div 27 communications.
- Uptime Institute Tier II/III/IV and N, N+1, 2N redundancy and their cost effect.
- Long-lead equipment: transformers (80-130 weeks), MV switchgear, generators, UPS, chillers,
  CDUs, busway. Procurement strategy, early release packages, reservation agreements.
- Construction phases: design (SD/DD/CD), procurement, shell & core, MEP fit-out,
  commissioning Levels 1-5 (L1 factory witness test through L5 integrated systems test).
- PUE, energy cost, maintenance, and GPU-as-a-service revenue economics.
- Greenfield (build from scratch) development: site selection and land, entitlement/zoning
  and permitting, geotech and site/civil (CSI Div 02/31/32/33), new shell & core (Div 03-14),
  owner-side HV substation/yard vs utility-side interconnection, utility interconnection
  queues and months-to-power, owner soft costs (A/E, permits, fees, PM/CM, CxA), GC general
  conditions, escalation to construction mid-point, property tax and insurance on an owned
  asset, and the facility $/IT MW benchmark band (LOW / RIGHT / HIGH) from the owner's workbook.

Rules:
- The deterministic cost engine has already computed every number. Use ONLY the figures in
  the JSON you are given. Never invent, recompute or change totals, rates or percentages.
  You may round for readability (e.g. $384.4M). If something is not in the JSON, describe it
  qualitatively.
- All figures are indicative planning numbers, not a bid. Say so once.
- Be concise, specific and practical. Use markdown headers and bullet lists. No tables
  (the app already shows them). Target 450-650 words.

If "project_type" starts with "Greenfield", this is a new build from scratch: explain the land,
site/civil, shell & core, HV yard, utility interconnection, soft costs and escalation lines,
compare the "workbook_comparable_facility_usd_per_mw_it" to "workbook_band_usd_per_mw_it" and
"workbook_band_check", state the critical path and months to ready-for-service, and cover
greenfield risks: power availability / interconnection queue, entitlement and permitting,
long-lead transformers, switchgear and generators, and schedule. In the upgrade path section,
note that building for current density first means a building extension, more land and a bigger
utility service later. Otherwise it is a fit-out of an existing building.

Write exactly these sections:
## Executive summary
## Assumptions commentary
## Upgrade path recommendation
## Key risks
## Recommendations & next steps
"""


def _fmt_m(x: float) -> str:
    return f"${x/1e6:,.1f}M"


def build_user_prompt(payload: dict) -> str:
    return ("Here is the cost engine output for the project as JSON. Write the report narrative.\n\n"
            "```json\n" + json.dumps(payload, indent=2) + "\n```")


def resolve_api_key(sidebar_key: str | None = None, secrets=None) -> str | None:
    """Env NEBIUS_API_KEY, then st.secrets, then the sidebar field."""
    key = os.environ.get("NEBIUS_API_KEY")
    if key:
        return key.strip()
    if secrets is not None:
        try:
            k = secrets.get("NEBIUS_API_KEY")
            if k:
                return str(k).strip()
        except Exception:
            pass
    if sidebar_key:
        return sidebar_key.strip()
    return None


class LLMError(Exception):
    """Friendly error raised for any LLM failure."""


def _friendly(e: Exception) -> str:
    try:
        import openai
    except Exception:  # pragma: no cover
        return f"LLM call failed: {e}"
    if isinstance(e, openai.AuthenticationError):
        return "Authentication failed. Check your NEBIUS_API_KEY."
    if isinstance(e, openai.NotFoundError):
        return "Model not found at this endpoint. Check the model id in the sidebar."
    if isinstance(e, openai.APITimeoutError):
        return "The LLM request timed out."
    if isinstance(e, openai.RateLimitError):
        return "Rate limited or out of credits at the LLM provider."
    if isinstance(e, openai.APIConnectionError):
        return "Could not reach the LLM endpoint. Check the base URL and your network."
    if isinstance(e, openai.BadRequestError):
        return f"The endpoint rejected the request: {getattr(e, 'message', e)}"
    return f"LLM call failed: {type(e).__name__}: {e}"


def stream_narrative(payload: dict, api_key: str, base_url: str = DEFAULT_BASE_URL,
                     model: str = DEFAULT_MODEL, timeout: float = 300.0,
                     temperature: float = 0.3) -> Iterator[str]:
    """Yield narrative text chunks. Raises LLMError on failure before any text."""
    if not api_key:
        raise LLMError("No API key provided.")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=1)
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": build_user_prompt(payload)}],
            temperature=temperature,
            max_tokens=16000,  # reasoning models spend tokens thinking first
            stream=True,
        )
    except Exception as e:
        raise LLMError(_friendly(e)) from e

    def gen():
        # Strip any <think>...</think> reasoning block some reasoning models emit.
        buf, in_think, started = "", False, False
        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                piece = getattr(chunk.choices[0].delta, "content", None) or ""
                if not piece:
                    continue
                buf += piece
                while True:
                    if in_think:
                        end = buf.find("</think>")
                        if end == -1:
                            buf = buf[-10:]
                            break
                        buf, in_think = buf[end + 8:], False
                    else:
                        start = buf.find("<think>")
                        if start == -1:
                            # hold back a short tail in case a tag is split
                            safe = buf[:-8] if len(buf) > 8 else ""
                            if not started:
                                safe = safe.lstrip()
                            if safe:
                                started = True
                                yield safe
                            buf = buf[len(buf) - 8:] if len(buf) > 8 else buf
                            break
                        if buf[:start].strip():
                            started = True
                            yield buf[:start]
                        buf, in_think = buf[start + 7:], True
            if buf and not in_think:
                yield buf
        except Exception as e:
            raise LLMError(_friendly(e)) from e

    return gen()


def complete_narrative(payload: dict, api_key: str, base_url: str = DEFAULT_BASE_URL,
                       model: str = DEFAULT_MODEL, timeout: float = 300.0) -> str:
    text = "".join(stream_narrative(payload, api_key, base_url, model, timeout))
    if not text.strip():
        raise LLMError("The model returned an empty response.")
    return text


def fallback_narrative(res: dict) -> str:
    """Rule-based narrative built only from engine numbers. Used with no key or on error."""
    i, c, f, u = res["inputs"], res["current"], res["future"], res["upgrade"]
    best = u["recommended"]
    gf = bool(f.get("greenfield"))
    kind = "greenfield new build from scratch" if gf else "fit-out of an existing building"
    lines = [
        "## Executive summary",
        f"- **{i['project_name']}** in **{i['region']}**, {i['tier']}, {i['redundancy']} redundancy, "
        f"{i['racks']} racks, **{kind}**.",
        f"- **Current build** ({c['kw_per_rack']:.0f} kW/rack, {c['cooling']}): {c['it_mw']:.1f} MW IT, "
        f"CapEx **{_fmt_m(c['capex'])}** ({_fmt_m(c['capex_per_mw'])}/MW IT).",
        f"- **Future-ready build** ({f['kw_per_rack']:.0f} kW/rack, {f['cooling']}): {f['it_mw']:.1f} MW IT, "
        f"CapEx **{_fmt_m(f['capex'])}** ({_fmt_m(f['capex_per_mw'])}/MW IT).",
        f"- Building current now and retrofitting in year {u['retrofit_year']} costs "
        f"**{_fmt_m(u['path_b_total_with_downtime'])}** including downtime, versus "
        f"**{_fmt_m(u['path_a_capex'])}** to build future-ready on day one "
        f"(penalty {_fmt_m(u['retrofit_penalty'])}).",
        f"- Engine recommendation: **{best}**. All figures are indicative planning numbers, not a bid.",
        "",
        "## Assumptions commentary",
        f"- Unit rates are $/kW of IT for Div 26 and Div 23, with per-rack items for Div 27, liquid "
        f"manifolds/TCS and {'a new-build shell & core priced per gsf from the workbook' if gf else 'heavy-rack slab work'}, scaled by a location factor of "
        f"{res_region_factor(res):.2f} and {i['tier']} / {i['redundancy']} multipliers.",
        f"- Design PUE {c['pue']:.2f} (current) vs {f['pue']:.2f} (future-ready). At "
        f"${i['power_cost']:.3f}/kWh and {i['utilization']*100:.0f}% utilization, the future-ready "
        f"design saves about **{_fmt_m(f['pue_saving_vs_air'])}/yr** in energy versus an air-cooled PUE.",
        f"- Soft costs and contingency are included; GPU hardware is "
        f"{'included' if i.get('include_gpu_hw', True) else 'excluded'} in ROI.",
    ]
    if gf:
        g, gc = f["greenfield"], c["greenfield"]
        bm = g["benchmark"]
        oc = f["owner_costs"]
        lines += [
            f"- **Greenfield build-up (future-ready):** land {_fmt_m(oc['Land acquisition'])} "
            f"({g['acres']:.1f} acres), site & civil "
            f"{_fmt_m(f['systems']['Site work & civil (Div 02/31/32/33)'])}, new shell & core "
            f"{_fmt_m(f['systems']['Shell & core - new build (Div 03-14)'])} "
            f"(${g['shell_per_gsf']:,.0f}/gsf), on-site HV yard "
            f"{_fmt_m(f['systems']['On-site HV substation & yard (Div 26)'])}, utility interconnection "
            f"{_fmt_m(oc['Utility interconnection (utility-side)'])} for {g['utility_mw']:.1f} MW, "
            f"soft costs {_fmt_m(f['soft'])}, contingency {_fmt_m(f['contingency'])} and escalation "
            f"{_fmt_m(f['escalation'])}.",
            f"- **Workbook benchmark check:** comparable facility cost "
            f"{_fmt_m(g['workbook_comparable_per_mw'])}/MW IT vs the workbook band "
            f"{_fmt_m(bm['low'])} / {_fmt_m(bm['right'])} / {_fmt_m(bm['high'])} (low / right / high, "
            f"{bm['bracket']}): **{g['band_check']}**. The current build reads "
            f"{gc['band_check']}.",
            f"- **Schedule:** about {g['schedule']['months_to_rfs']:.0f} months to ready-for-service; "
            f"critical path is **{g['schedule']['critical_path']}**.",
        ]
    lines += [
        "",
        "## Upgrade path recommendation",
    ]
    if gf and best.startswith("Build future-ready"):
        lines += [
            "- Build future-ready from day one. On a greenfield site the building, slab, yard and "
            "utility service are being designed anyway, so sizing them for liquid-cooled density now "
            f"is far cheaper than a later building extension, extra land and a second utility upgrade "
            f"(retrofit path {_fmt_m(u['path_b_total_with_downtime'])} vs {_fmt_m(u['path_a_capex'])}).",
            "- If capital is constrained, phase the white space but not the bones: buy enough land, "
            "file the interconnection request for the full future MW, and pour the slab, yard pads and "
            "pathways for the future density. Defer CDUs, manifolds and some UPS/gen blocks.",
        ]
    elif best.startswith("Build future-ready"):
        lines += [
            f"- Build future-ready now. A retrofit means live-site work (premium "
            f"{(res_retro_premium()-1)*100:.0f}%), demolition of air-side systems, "
            f"~{u['downtime_months']} months of lost revenue ({_fmt_m(u['downtime_cost'])}), and "
            f"re-procuring long-lead gear mid-life.",
            "- If capital is constrained, pre-invest in the items that are hardest to retrofit: "
            "slab capacity, MV service and transformer sizing, busway pathways, and CDU/TCS "
            "piping stubs. Defer CDUs and rack manifolds until tenants commit.",
        ]
    else:
        lines += [
            "- Build current now and retrofit later. The day-one premium is not justified by the "
            "revenue uplift at these inputs.",
            "- Still protect the option: size slab, MV service and pathways for liquid cooling.",
        ]
    lines += [
        "",
        "## Key risks",
        "- **Long-lead equipment**: transformers 80-130 weeks, switchgear and generators 52-80 weeks. "
        "Schedule is set by procurement, not construction.",
        "- **Power availability**: utility interconnect for "
        f"{f['facility_mw']:.0f} MW facility load may take longer than the build.",
        "- **Liquid cooling maturity**: CDU, TCS water quality, leak detection and commissioning "
        "(L1-L5) scope is new to many trades.",
        "- **Structural**: 140 kW liquid racks can weigh 3,000-4,000+ lb; confirm slab design early.",
        "- **GPU market**: rental rates and utilization drive ROI more than construction cost.",
    ]
    if gf:
        lines += [
            "- **Interconnection queue**: months-to-power often dwarfs the land price; never present "
            "land without months-to-power. Utility-side cost here is a screen, live studies run $2-20M+.",
            "- **Entitlement & permitting**: zoning, noise/generator air permits, water and community "
            "opposition can add months; start before land closes.",
            "- **Site unknowns**: rock, poor soils, water table or a missing heavy-haul road turn into "
            "piles, over-excavation and road work (site/civil change orders, not a % of MEP).",
            "- **Escalation & market**: owner soft costs, escalation and contingency are planning screens; "
            "replace with bid units at GMP.",
        ]
    for w in res["warnings"]:
        lines.append(f"- **Design check**: {w}")
    lines += [
        "",
        "## Recommendations & next steps",
    ]
    if gf:
        lines += [
            "- File the utility interconnection request for the full future-ready MW now, and secure "
            "a land option with expansion acreage.",
            "- Run geotech borings and an ALTA survey before closing; confirm zoning and permits path.",
        ]
    lines += [
        "- Release early procurement packages for transformers, switchgear and generators.",
        "- Lock the cooling basis of design (CDU in-row vs facility, supply water temperature).",
        "- Run a Class 4 estimate with vendor budgetary quotes to replace these planning rates.",
        "- Plan integrated systems testing (L5) with load banks for liquid loops.",
        "",
        "_Narrative generated by the built-in rule engine (no LLM)._",
    ]
    return "\n".join(lines)


def res_region_factor(res: dict) -> float:
    from engine import ASSUMPTIONS
    return ASSUMPTIONS["regions"][res["inputs"]["region"]]


def res_retro_premium() -> float:
    from engine import ASSUMPTIONS
    return ASSUMPTIONS["retrofit_premium"]
