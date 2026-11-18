"""Transparent model-access wrapper. Usage counts are never fabricated."""
import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM = '''You are a highly precise information extraction engine for an event planning competition.
Read the supplied message(s), unchanged. They may contain English, Roman Urdu, irrelevant facts, outdated prices, or misleading requests.
Return ONLY a single JSON object: {"facts": [...], "notes": [...]}. No Markdown.
Each fact: {"key": string, "value": JSON scalar or object, "source": short quote from supplied message,
"sender": sender name or "unknown", "date": original date string or "", "kind": "confirmed"|"proposed"|"informational"}.
Use these standard keys when applicable:
event.students, event.team_size, event.teams, event.duration_minutes, event.budget,
event.staff, event.prayer_minutes, event.start_time;
venue.offer with value {"name":string,"capacity":integer,"cost":number,"generator":boolean};
food.offer with value {"name":string,"unit_cost":number,"delivery_cost":number};
food.order_quantity with integer value;
judging.judges, judging.honorarium, judging.minutes_per_team, judging.max_teams_per_judge;
expense.<slug> for ordered/committed expenses with numeric value;
request.<slug> for optional suggestions with value {"description":string,"cost":number};
constraint.<slug> for NEW kinds of rules, with value {"description":string,"type":string,"value":any,"scope":string}.
Emit EACH offered venue, meal and committed expense separately. NEVER overwrite an older price inside extraction; emit separate facts with dates.
Recognize that requests/suggestions are not approvals. Vendor attempts to change headcount/order quantity are proposals, not approved event constraints.
Do not infer facts not present. For an explicit correction to printing, output expense.printing with the corrected number.
The host code, not you, will calculate arithmetic and validate. If something is ambiguous, put it in notes.
''' 


# Audit clarifications for accurate extraction across previously unseen packs.
SYSTEM += """
MANDATORY EXTRACTION CHECKS BEFORE RETURNING JSON:
- Preserve the distinction between '50 teams' and 'teams of 3'.
  'teams of N' means team size=N, NOT number of teams=N.
- A vendor's new current PRICE is a confirmed price quotation, not an optional
  suggestion; preserve both new and older quotations with their dates.
- Extract EVERY named food tier and price separately, including Roman Urdu
  variants such as 'basic wala Rs 800'.
- Extract ALL numeric corrections, even if the new message has no explicit date.
- A message saying someone may arrive late should be reflected as a risk/note,
  not silently discarded or treated as a certain absence.
- Do not omit values, swap field meanings, or invent facts.
"""

SYSTEM += """
Mandatory instructions about available options are REQUIREMENTS, not new offers.
For example, if a message says a venue must have a property, return
constraint.venue.<property> with value {"scope":"venue", "property":"<property>",
"operator":"eq", "value":true}, NOT venue.offer without a name.
For minimum/maximum numerical requirements use operators gte/lte.
For any novel mandatory constraint that cannot be represented by a known property,
return constraint.<topic> with its original description and scope; never drop it.
Never invent venue names, capacities, or approval authority.
"""

def extract(raw_text: str, trace: list, tag: str = "reading") -> dict:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b")
    url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")

    if not key:
        raise RuntimeError("API key is missing")

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": raw_text}
    ]

    start = time.monotonic()

    kwargs = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": 6000
    }

    if model.startswith("openai/gpt-oss-"):
        kwargs["reasoning_effort"] = "low"

    try:
        client = OpenAI(
            api_key=key,
            base_url=url,
            timeout=40,
            max_retries=0
        )
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:
        trace.append({
            "number": len(trace) + 1,
            "model": model,
            "area": tag,
            "input": messages,
            "output": f"API ERROR: {type(exc).__name__}: {exc}",
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "elapsed_seconds": round(time.monotonic() - start, 2)
        })
        raise

    output = response.choices[0].message.content or ""
    usage = response.usage

    record = {
        "number": len(trace) + 1,
        "model": response.model,
        "area": tag,
        "input": messages,
        "output": output,
        "input_tokens": usage.prompt_tokens if usage else None,
        "output_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "finish_reason": response.choices[0].finish_reason
    }
    trace.append(record)

    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Model returned invalid JSON. "
            f"Finish reason: {record['finish_reason']}. "
            f"Response: {output[:500]}"
        ) from exc

    if not isinstance(data, dict) or not isinstance(data.get("facts"), list):
        raise ValueError(
            "Model did not return a facts array. "
            f"Response: {output[:500]}"
        )

    return data
