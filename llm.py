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
  heat exchangers (RDHx) extend to ~45 kW; above that you need direct-to-chip (D2C) liquid with
  CDUs, a technology cooling system (TCS) secondary loop, rack manifolds and warm-water heat
  rejection (dry/adiabatic coolers) with trim chillers.
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
- Rule used by the engine: above 45 kW/rack the cooling is always direct-to-chip (D2C) liquid
  (cold plates, L2L CDUs N+1 on UPS, TCS loop, dry/adiabatic hybrid reject, residual air share).
- Greenfield (new build from scratch) is priced from the owner's cost workbook "AI Rack Research -
  The Right Estimate" (8 platforms H100 ... Kyber): RIGHT facility $/IT MW = average of Method A
  bottoms-up and Method B mix mid, LOW/HIGH band, 22-division CSI mix, N+1 block redundancy, GC 9% +
  BIM/CxA + 4% contingency inside the number, change pricing (N+2, 2N, 96 h fuel, union/seismic/piles,
  contingency) as machines x unit + 13% soft on the delta. Facility $ excludes IT racks, AI fabric,
  land, utility-side interconnect, owner staff, financing, tax and escalation past 2026; those sit
  on adders. Never present land without months-to-power.

If "project_type" starts with "Greenfield" there is ONE design and NO current-vs-future case: do not
mention a current build or a retrofit. Explain the platform and density, the CSI split, the
reconciliation to the workbook (facility $ vs RIGHT, band check), the adders, OpEx, payback, and the
schedule/critical path. Name the section "## Design & scope recommendation" instead of
"## Upgrade path recommendation". Cover greenfield risks: interconnection queue and months-to-power,
long-lead transformers/switchgear/generators, module freeze, CDU MW ladder, contingency at 4% vs 7-10%,
site/geotech, permitting.

Write exactly these sections:
## Executive summary
## Assumptions commentary
## Upgrade path recommendation   (greenfield: ## Design & scope recommendation)
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
    if res.get("mode") == "greenfield":
        return _fallback_greenfield(res)
    return _fallback_fitout(res)


def _fallback_greenfield(res: dict) -> str:
    i, d = res["inputs"], res["design"]
    b, q, s = d["basis"], d["quantities"], d["schedule"]
    land = sum(v for k, v in d["adders"].items() if k.startswith("Land"))
    ic = sum(v for k, v in d["adders"].items() if "interconnect" in k)
    top = sorted(d["csi"].items(), key=lambda kv: -kv[1])[:3]
    lines = [
        "## Executive summary",
        f"- **{i['project_name']}**: one **greenfield new build from scratch** in **{i['region']}**, "
        f"**{d['platform']}** at {d['kw_per_rack']:.0f} kW/rack, {d['racks']:,.0f} racks, "
        f"{d['it_mw']:.1f} MW IT, {d['cooling']}"
        + (" (D2C auto-selected above 45 kW/rack)." if d["cooling_auto"] else "."),
        f"- Facility cost **{_fmt_m(d['facility'])}** = **{_fmt_m(d['facility_per_mw'])}/MW IT** against the "
        f"workbook RIGHT {_fmt_m(b['right'])}/MW (band {_fmt_m(b['low'])} to {_fmt_m(b['high'])}): "
        f"**{d['band_check']}**.",
        f"- Total greenfield CapEx **{_fmt_m(d['capex'])}** including land {_fmt_m(land)} and utility-side "
        f"interconnect {_fmt_m(ic)}. IT iron adds {_fmt_m(d['it_hw'])} outside facility $.",
        f"- Annual OpEx {_fmt_m(d['opex'])}, revenue {_fmt_m(d['revenue'])} at ${d['gpu_price']:.2f}/GPU-hr, "
        f"simple payback **{d['simple_payback']:.1f} yrs**." if d["simple_payback"] else
        f"- Annual OpEx {_fmt_m(d['opex'])}; the design does not pay back at these revenue inputs.",
        "- All figures are indicative planning numbers, not a bid.",
        "",
        "## Assumptions commentary",
        f"- Basis is the owner's workbook: RIGHT $/IT MW = average of Method A bottoms-up and Method B mix "
        f"mid, N+1 block-redundant, GC {b['gc_pct']:.0%} + BIM/CxA + {b['cont_pct']:.0%} contingency inside.",
        f"- Largest CSI divisions: " + ", ".join(f"{k} {_fmt_m(v)}" for k, v in top) + ".",
        f"- Quantities: {q['standby_mw']:.0f} MW running plant (IT x PUE {d['pue']:.2f}), "
        f"{q['gens_n1']} x 3 MW generators (N+1), {q['ups_n1']} x 1 MW UPS modules, {q['cdus']} CDUs, "
        f"{d['gsf']:,.0f} gsf.",
    ]
    if d["changes"]:
        lines.append("- Changes priced as machines x unit with 13% soft on the delta: "
                     + "; ".join(f"{n} {_fmt_m(w)}" for n, _, w in d["changes"]) + ".")
    lines += [
        "",
        "## Design & scope recommendation",
        f"- Price the hall you will pour: this is a {d['platform']} column, not a blended $/MW.",
        "- Keep IT iron, AI fabric, land and the utility-side interconnect on their own rows; they are "
        "outside facility $ in the workbook.",
        "- Hold N+1 block redundancy unless the tenant writes 2N; price N+2 or 2N with the change sheet.",
        "",
        "## Key risks",
        f"- **Power**: ~{s['months_to_power']} months to utility power assumed (workbook range 12-48); "
        "interconnect is excluded from facility $ and live studies often run $2-20M+.",
        f"- **Schedule**: ~{s['months_to_rfs']:.0f} months to ready-for-service; critical path is "
        f"**{s['critical_path']}**.",
        f"- **Long-lead gear**: a {90}-week transformer cannot be crashed; switchgear and generators 52-80 weeks.",
        f"- **Module freeze**: {b['module']}; wrong-gen module means a missed slot.",
        f"- **CDU MW ladder** and **contingency at {b['cont_pct']:.0%}** (7-10% at 60% CD) are the first "
        "numbers to attack.",
        "- **Site & permits**: rock, piles, haul road, zoning and generator air permits.",
    ]
    for w in res["warnings"]:
        lines.append(f"- **Design check**: {w}")
    lines += [
        "",
        "## Recommendations & next steps",
        "- File the interconnection request for the full MW and reserve transformer / switchgear / generator slots.",
        "- Freeze the platform ICD before rebar and module orders.",
        "- Replace the Method A anchors with a BOM and bid units; keep this register and structure.",
        "- Run geotech borings before closing on land.",
        "",
        "_Narrative generated by the built-in rule engine (no LLM)._",
    ]
    return "\n".join(lines)


def _fallback_fitout(res: dict) -> str:
    i, c, f, u = res["inputs"], res["current"], res["future"], res["upgrade"]
    best = u["recommended"]
    def cl(x):
        return x["cooling"] + (" (auto-selected above 45 kW/rack)" if x["cooling_auto"] else "")
    lines = [
        "## Executive summary",
        f"- **{i['project_name']}** in **{i['region']}**, {i['tier']}, {i['redundancy']} redundancy, "
        f"{i['racks']} racks, **fit-out of an existing building**.",
        f"- **Current build** ({c['kw_per_rack']:.0f} kW/rack, {cl(c)}): {c['it_mw']:.1f} MW IT, "
        f"CapEx **{_fmt_m(c['capex'])}** ({_fmt_m(c['capex_per_mw'])}/MW IT).",
        f"- **Future-ready build** ({f['kw_per_rack']:.0f} kW/rack, {cl(f)}): {f['it_mw']:.1f} MW IT, "
        f"CapEx **{_fmt_m(f['capex'])}** ({_fmt_m(f['capex_per_mw'])}/MW IT).",
        f"- Building current now and retrofitting in year {u['retrofit_year']} costs "
        f"**{_fmt_m(u['path_b_total_with_downtime'])}** including downtime, versus "
        f"**{_fmt_m(u['path_a_capex'])}** to build future-ready on day one "
        f"(penalty {_fmt_m(u['retrofit_penalty'])}).",
        f"- Engine recommendation: **{best}**. All figures are indicative planning numbers, not a bid.",
        "",
        "## Assumptions commentary",
        f"- Unit rates are $/kW of IT for Div 26 and Div 23, with per-rack items for Div 27, liquid "
        f"manifolds/TCS and heavy-rack slab work, scaled by a location factor of "
        f"{res_region_factor(res):.2f} and {i['tier']} / {i['redundancy']} multipliers.",
        f"- Above 45 kW/rack the engine always uses D2C liquid: {f['cdus']} CDUs (1.6 MW skids, N+1, "
        "workbook rule) feed the racks.",
        f"- Design PUE {c['pue']:.2f} (current) vs {f['pue']:.2f} (future-ready). At "
        f"${i['power_cost']:.3f}/kWh and {i['utilization']*100:.0f}% utilization, the future-ready "
        f"design saves about **{_fmt_m(f['pue_saving_vs_air'])}/yr** in energy versus an air-cooled PUE.",
        f"- Soft costs and contingency are included; GPU hardware is "
        f"{'included' if i.get('include_gpu_hw', True) else 'excluded'} in ROI.",
        "",
        "## Upgrade path recommendation",
    ]
    if best.startswith("Build future-ready"):
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
            "- Still protect the option: size slab, MV service and pathways for D2C liquid cooling.",
        ]
    lines += [
        "",
        "## Key risks",
        "- **Long-lead equipment**: transformers 80-130 weeks, switchgear and generators 52-80 weeks. "
        "Schedule is set by procurement, not construction.",
        f"- **Power availability**: the utility service for {f['facility_mw']:.0f} MW facility load may "
        "take longer than the build.",
        "- **Liquid cooling maturity**: CDU, TCS water quality, leak detection and commissioning "
        "(L1-L5) scope is new to many trades.",
        "- **Structural**: 140 kW liquid racks can weigh 3,000-4,000+ lb; confirm slab design early.",
        "- **GPU market**: rental rates and utilization drive ROI more than construction cost.",
    ]
    for w in res["warnings"]:
        lines.append(f"- **Design check**: {w}")
    lines += [
        "",
        "## Recommendations & next steps",
        "- Release early procurement packages for transformers, switchgear and generators.",
        "- Lock the D2C basis of design (CDU in-row vs facility, supply water temperature).",
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
