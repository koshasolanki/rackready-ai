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

SYSTEM_PROMPT = """You are RackReady AI, a senior data center cost manager and MEP estimator with 20+ years on
hyperscale and AI/HPC projects. You write for owners, developers and general contractors in plain language.

You receive the JSON output of a deterministic cost and design engine. Never change, recompute or invent
numbers: quote them from the JSON (in $M or $B, MW, kW/rack, months). If something is not in the JSON, say it
needs confirming. Every figure is an early budget estimate (±30-50%), not a bid.

Domain you apply:
- Rack density: air cooling tops out near 30 kW/rack, rear-door heat exchangers near 45 kW/rack. Above
  45 kW/rack the engine always uses direct-to-chip (D2C) liquid cooling: cold plates, CDUs, a technology
  cooling loop, warm-water dry/adiabatic heat rejection, and a residual air share (liquid captures about
  85-95%, never 100%). Immersion is a niche option and is not modelled.
- NVIDIA roadmap: GB200/GB300 NVL72 about 120-140 kW/rack (shipping); Vera Rubin NVL144 about 190-230 kW
  (announced, 2H 2026); Rubin Ultra NVL576 "Kyber" about 600 kW with 800 VDC power (announced, 2H 2027);
  1 MW-class racks are speculative. Say "announced" or "estimate" when you use roadmap values.
- Power: utility service in MVA (power factor), main transformers, unit substations, switchgear, UPS with
  short battery ride-through, standby generators (N, N+1, N+2, 2N) and fuel storage, row busway sized by
  I = P / (sqrt3 x V x PF). PUE is an annual energy ratio, not a peak multiplier.
- Long-lead equipment drives the schedule (2026): large power transformers about 100-160 weeks (average
  about 128), MV switchgear 52-104 weeks, large diesel generators 62-110 weeks, UPS 30-60, chillers 40-70,
  CDUs 30-50. Utility interconnection often takes years. Use the schedule JSON: the ready-for-IT range in
  months from start (say "about X-Y months from start"; never give calendar dates), the critical path and
  when to order each item ("order it N months before you need it", RFQ by month N after start).
- Commissioning L1-L5 (factory test, delivery/install, start-up, functional test, integrated systems test).
  Hard stop: no IT power-on until the liquid loop passes leak test, flushing, chemistry and leak detection.
  Substantial completion follows a passed IST.
- Costs: cost_lines lists 13 end-to-end lines with included true/false. total_capex_usd is the sum of the
  included lines; always quote that total and name any large line that is not included.
- Call it an "early budget estimate (±30-50%)". Never use the words concept, screening or estimate class.
- Mention one or two items from how_to_avoid_delays that fit the project.
- Tier-style resilience wording (Tier I/III/IV-style); do not claim certification. Units needed plus one
  spare is N+1 (never "2N+1").
- Never name companies, vendors, suppliers, people, projects or sites.
- End with: not engineering, legal or financial advice; a licensed engineer and the AHJ must review.

Rules:
- If project_type starts with "Greenfield" there is ONE new build: never mention a current build or a
  retrofit of it. Name section 3 "## Design & future-ready recommendation".
- For an existing building fit-out, compare the current racks with the future-ready fit-out and the
  retrofit-later option. Name section 3 "## Upgrade path recommendation".
- When future_ready / future_proof_horizon is present, explain the three paths (retrofit later,
  provisions now, full future build) and why the engine's lowest present cost wins; list the key provisions.
- Use design_calculations to state the key engineering quantities (MVA, generators, UPS, tons, CDUs, flow,
  floor loading, PUE, water).
- Mention any benchmark check outside its range and every warning, and the top active risks from
  risk_register (impact in months).

Write exactly these sections, concise (about 450-650 words in total):
## Executive summary
## Assumptions commentary
## Upgrade path recommendation   (greenfield: ## Design & future-ready recommendation)
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
    """Rule-based narrative from the same engine output (used when no LLM is available)."""
    import guide as G
    import report as R

    i = res["inputs"]
    h = R.headline(res)
    v = R.main_design(res)["v"]
    f = R.horizon(res)
    rec = res["recommendation"]
    gf = res["mode"] == "greenfield"
    x = res["design"] if gf else res["future"]
    pay = f"about {h['payback']:.1f} years" if h["payback"] is not None else "not reached in the analysis period"
    out = ["## Executive summary"]
    if gf:
        out.append(f"{i['project_name']}: one new build in {i['region']}, {h['racks']:,} {h['platform']} racks at "
                   f"{h['kw']:,.0f} kW/rack ({h['it_mw']:,.1f} MW IT), {h['cooling'][0].lower() + h['cooling'][1:]} "
                   f"cooling. Total {R.money(h['total'])} ({R.money(h['per_mw'])}/MW IT) for the ticked cost lines; "
                   f"{R.money(h['total_all'])} with every line ticked.")
    else:
        cur, up = res["current"], res["upgrade"]
        out.append(f"{i['project_name']}: {cur['racks']:,} racks today at {cur['kw']:.0f} kW/rack vs a future-ready "
                   f"fit-out for {h['platform']} at {x['kw']:.0f} kW/rack. Total {R.money(h['total'])} "
                   f"({R.money(h['per_mw'])}/MW IT) for the ticked cost lines; {R.money(h['total_all'])} with every line "
                   f"ticked. Like-for-like construction: {R.money(x['construction_cost'])} future-ready vs "
                   f"{R.money(cur['capex'])} for today's racks; today's racks plus a year-{up['year']} retrofit cost "
                   f"{R.money(up['path_b_total'])} including {up['downtime_months']} months of downtime.")
    if h["excluded"]:
        out.append("Not in the total: " + ", ".join(h["excluded"]) + ".")
    out.append(f"Ready for IT {h['rfs_text']}. Payback including IT: {pay}.")
    out.append(f"**Verdict: {rec['headline']}.** {rec['detail']}")

    out.append("## Assumptions commentary")
    out.append(f"Key design: {R.key_design_line(res)}. Facility peak {v['fac_peak_kw'] / 1000:,.1f} MW (IT, UPS "
               f"losses, design-day cooling, house load); PUE {v['pue']:.2f} is an annual energy ratio. Resilience "
               f"{E_RES(i)}. Power ${x['power_cost']:.3f}/kWh; GPU rental ${x['gpu_price']:.2f}/GPU-hr at "
               f"{i['utilization']:.0%} utilization, changing {float(i.get('price_change') or 0):+.0%}/yr "
               "between hardware refreshes (assumption).")
    bad = [c for c in res["checks"] if not c["ok"]]
    out.append("All benchmark checks are within their public ranges." if not bad else
               "Outside benchmark range: " + "; ".join(f"{c['check']} = {c['value']:,.2f}" for c in bad) + ".")

    out.append("## Design & future-ready recommendation" if gf else "## Upgrade path recommendation")
    if not gf:
        up = res["upgrade"]
        out.append(f"Fit out future-ready now: NPV {R.money(up['npv_a'])}. Keep today's racks and retrofit later: NPV "
                   f"{R.money(up['npv_b'])}. Recommended: **{up['recommended']}**.")
    if f.get("active"):
        out.append(f"Horizon {f['horizon']}: {f['target_kw']:,.0f} kW/rack in year {f['year']}. Present cost: " +
                   "; ".join(f"{p['path'].lower()} {R.money(p['pv_total'])}" for p in f["paths"]) +
                   f". Lowest: **{f['best']}**.")
        if "provisions" in f["best"]:
            out.append("Provisions to build in now: " + "; ".join(p["provision"] for p in f["provisions"]) + ".")
    elif f.get("reason"):
        out.append(f["reason"])

    out.append("## Key risks")
    S = res["cx"]["schedule"]
    first = [it for it in S["items"] if not it["flag"].startswith("After")]
    risks = [f"Critical path: {S['critical_path']}."]
    for it in first[:3]:
        risks.append(f"{it['item']}: send the RFQ by month {max(it['rfq'], 0):.0f} and order it "
                     f"{it['order_ahead']:,.0f} months before it is needed. {it['flag'].rstrip('.')}.")
    if not first:
        risks.append("All long-lead orders can follow notice to proceed.")
    if R.main_design(res)["cooling"] == "Direct-to-chip (D2C) liquid":
        risks.append("Hard stop: no IT power-on until the liquid loop passes leak, flush, chemistry and "
                     "leak-detection tests.")
    risks.append(f"Floor loading about {v['rack_psf']:,.0f} psf on the rack footprint: confirm the slab design.")
    out.append("\n".join([f"- {r}" for r in risks] + [f"- {w}" for w in res["warnings"]]))

    out.append("## Recommendations & next steps")
    out.append("\n".join(["- Get firm MW and an energization date from the utility in writing.",
                          "- Freeze the rack platform; get OEM power, weight and coolant specs in writing.",
                          "- Carry the future-ready provisions into the basis of design.",
                          *[f"- {t}" for t in G.HOW_TO_AVOID[1:3]],
                          "- Replace the per-MW rates with a quantity-based estimate once schematic design is drawn.",
                          "- " + DISCLAIMER_TEXT]))
    return "\n\n".join(out)


DISCLAIMER_TEXT = ("Early budget estimate (±30–50%), not a bid, and not engineering, legal or financial advice; a "
                   "licensed engineer and the AHJ must review.")


def E_RES(i):
    import engine as E
    return E.RESILIENCE.get(i.get("resilience"), i.get("resilience"))
