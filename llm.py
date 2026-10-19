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
needs confirming. Every figure is an indicative planning estimate, not a bid.

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
  CDUs 30-50. Utility interconnection often takes years. Use the schedule JSON: substantial completion month,
  notice to proceed, the critical path and the order-by dates (RFQ and PO by month, items to order before NTP).
- Commissioning L1-L5 (factory test, delivery/install, start-up, functional test, integrated systems test).
  Hard stop: no IT power-on until the liquid loop passes leak test, flushing, chemistry and leak detection.
  Substantial completion follows a passed IST.
- The estimate is AACE Class 5 (concept screening, about -20% to -50% / +30% to +100%).
- Tier-style resilience wording (Tier I/III/IV-style); do not claim certification. Units needed plus one
  spare is N+1 (never "2N+1").
- Never name companies, vendors, people, projects or sites.

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
    import report as R

    i = res["inputs"]
    h = R.headline(res)
    v = R.main_design(res)["v"]
    f = R.horizon(res)
    rec = res["recommendation"]
    gf = res["mode"] == "greenfield"
    out = ["## Executive summary"]
    if gf:
        out.append(f"{i['project_name']} is a single new build in {i['region']}: {h['racks']:,} {h['platform']} racks at "
                   f"{h['kw']:,.0f} kW/rack, {h['it_mw']:,.1f} MW of IT load, cooled by {h['cooling']}. The indicative "
                   f"project cost is {R.money(h['total'])} ({R.money(h['per_mw'])} per MW IT, including land, utility "
                   f"interconnection, owner costs and escalation). GPU and network hardware add {R.money(h['it_total'])}. "
                   f"Payback including IT is {'about %.1f years' % h['payback'] if h['payback'] is not None else 'not reached in the period'} "
                   f"from ready-for-service, expected in about {h['rfs']:.0f} months.")
    else:
        cur, fu, up = res["current"], res["future"], res["upgrade"]
        out.append(f"{i['project_name']}: {cur['racks']:,} racks today at {cur['kw']:.0f} kW/rack ({cur['cooling']}) vs a "
                   f"future-ready fit-out for {h['platform']} at {fu['kw']:.0f} kW/rack ({fu['cooling']}). The future-ready "
                   f"fit-out costs {R.money(fu['capex'])} vs {R.money(cur['capex'])} for the current design; building current "
                   f"now and retrofitting in year {up['year']} costs {R.money(up['path_b_total'])} including "
                   f"{up['downtime_months']} months of downtime.")
    out.append(f"**Recommendation:** {rec['headline']}. {rec['detail']}")
    out.append("## Assumptions commentary")
    out.append(f"Key design: {R.key_design_line(res)}. Facility peak demand is {v['fac_peak_kw'] / 1000:,.1f} MW "
               f"from a component load model (IT, UPS losses, design-day cooling, house load); annual PUE "
               f"{v['pue']:.2f} is an energy ratio. Resilience is {E_RES(i)}. Power is priced at "
               f"${(res['design'] if gf else res['future'])['power_cost']:.3f}/kWh and GPU rental at "
               f"${(res['design'] if gf else res['future'])['gpu_price']:.2f}/GPU-hr with {i['utilization']:.0%} "
               "utilization; rental prices are assumed to fall 8%/yr between hardware refreshes (assumption).")
    bad = [c for c in res["checks"] if not c["ok"]]
    out.append("All benchmark checks are within their public ranges." if not bad else
               "Outside benchmark range: " + "; ".join(f"{c['check']} = {c['value']:,.2f}" for c in bad) + ".")
    out.append("## Design & future-ready recommendation" if gf else "## Upgrade path recommendation")
    if not gf:
        up = res["upgrade"]
        out.append(f"Fit out future-ready now: NPV {R.money(up['npv_a'])}. Keep current and retrofit later: NPV "
                   f"{R.money(up['npv_b'])}. Engine recommendation: **{up['recommended']}**.")
    if f.get("active"):
        best = next(x for x in f["paths"] if x["path"] == f["best"])
        out.append(f"Future-proof horizon {f['horizon']}: {f['horizon_text']} The target ({f['target_kw']:,.0f} kW/rack "
                   f"in year {f['year']}) is priced three ways. " + " ".join(
                       f"{x['path']}: {R.money(x['pv_total'])} present cost." for x in f["paths"]) +
                   f" Lowest: **{best['path']}**.")
        out.append("Provisions to include: " + "; ".join(p["provision"] + " (" + p["when"][0].lower() + p["when"][1:] + ")"
                                                         for p in f["provisions"]) + ".")
    else:
        out.append(f.get("reason", ""))
    out.append("## Key risks")
    S = res["cx"]["schedule"]
    first = [x for x in S["items"] if not x["flag"].startswith("After")]
    risks = [f"Schedule: substantial completion (ready for IT) about month {S['sc']:.0f}; critical path: "
             f"{S['critical_path']}.",
             ("Order first: " + "; ".join(f"{x['item']} (RFQ by month {max(x['rfq'], 0):.0f}: {x['flag']})"
                                         for x in first) + "." if first else
              "All long-lead orders can follow notice to proceed."),
             "2026 lead times: large power transformers about 100-160 weeks, MV switchgear 52-104, large diesel "
             "generators 62-110.",
             "Commissioning hard stop: no IT power-on until the liquid loop passes leak, flush, chemistry and "
             "leak-detection tests; substantial completion follows a passed integrated systems test.",
             "Roadmap uncertainty: announced rack densities, weights and prices can change before delivery.",
             f"Floor loading: about {v['rack_psf']:,.0f} psf on the rack footprint; confirm slab design.",
             "Liquid cooling commissioning and water quality for the technology cooling loop."]
    out.append("\n".join([f"- {r}" for r in risks] + [f"- {w}" for w in res["warnings"]]))
    out.append("## Recommendations & next steps")
    out.append("\n".join(["- Confirm firm MW and the energization date with the utility; secure transformer and generator slots.",
            "- Freeze the rack platform and density; get the OEM rack power, weight and coolant specs in writing.",
            "- Carry the future-ready provisions into the basis of design and the site layout.",
            "- Replace these planning rates with a quantity-based estimate at concept design (this is an AACE Class 5 "
            "concept estimate).",
            "- " + DISCLAIMER_TEXT]))
    return "\n\n".join(out)


DISCLAIMER_TEXT = "All figures are an indicative planning estimate, not a bid."


def E_RES(i):
    import engine as E
    return E.RESILIENCE.get(i.get("resilience"), i.get("resilience"))
