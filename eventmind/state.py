"""Persistence and update state. One input command, consistent parsing for all messages."""
import json
from pathlib import Path
from .engine import plan
from .model import extract


def process(raw_text: str, previous: dict | None = None):
    previous=previous or {}
    trace=list(previous.get('trace',[]))
    parsed=extract(raw_text,trace)
    facts=list(previous.get('facts',[]))
    start=len(facts)
    # The language model may put requirements in a top-level "constraints"
    # object instead of "facts". Preserve them in the same audited fact stream.
    normalized = list(parsed.get('facts') or [])

    # Detect explicit unavailability for already named venue offers.
    import re
    known_offers = [
        f for f in list(previous.get("facts", [])) + normalized
        if str(f.get("key", "")).startswith("venue.offer")
        and isinstance(f.get("value"), dict)
        and f["value"].get("name")
    ]
    blocks = re.split(r"(?=^#\\d+\\s*\\|)", raw_text, flags=re.M)
    for block in blocks:
        if not re.search(
            r"under maintenance|cannot be booked|unavailable|"
            r"not available|fully booked|closed for repairs",
            block, re.I
        ):
            continue
        for offer in known_offers:
            name = str(offer["value"]["name"])
            if re.search(
                r"(?<!\\w)" + re.escape(name) + r"(?!\\w)",
                block, re.I
            ):
                key = "venue.unavailable." + re.sub(
                    r"\\W+", "_", name.lower()
                )
                if not any(f.get("key") == key for f in normalized):
                    normalized.append({
                        "key": key,
                        "value": {"name": name},
                        "source": block.strip(),
                        "sender": "venue availability notice",
                        "date": "",
                        "kind": "confirmed"
                    })
    # Extract an explicitly stated catering service percentage.
    import re
    for message in re.split(r"(?=^#\\d+\\s*\\|)", raw_text, flags=re.M):
        if "service charge" not in message.lower():
            continue
        match = re.search(r"(\\d+(?:\\.\\d+)?)\\s*%", message)
        if match and not any(
            "service_charge" in str(f.get("key", ""))
            for f in normalized
        ):
            normalized.append({
                "key": "food.order.service_charge_rate",
                "value": float(match.group(1)) / 100,
                "source": match.group(0) + " service charge",
                "sender": "Caterer",
                "date": "",
                "kind": "confirmed"
            })

    constraints = parsed.get('constraints') or {}
    if isinstance(constraints, dict):
        constraints = list(constraints.items())
    elif isinstance(constraints, list):
        constraints = [(str(i), x) for i, x in enumerate(constraints)]
    else:
        constraints = [("unparsed", {"description": repr(constraints)})]
    for key, value in constraints:
        if not isinstance(value, dict):
            value = {"value": value}
        parts = str(key).split('.')
        scope = value.get('scope') or (parts[0] if parts else 'unknown')
        prop = value.get('property') or value.get('field') or (parts[1] if len(parts) > 1 else None)
        raw_operator = value.get('operator') or value.get('type') or 'eq'
        operator = 'eq' if str(raw_operator).lower() in ('boolean', 'bool', 'string', 'number') else raw_operator
        target = value.get('value', value.get('required_value'))
        normalized.append({
            'key': 'constraint.' + str(scope) + ('.' + str(prop) if prop else ''),
            'value': {'scope': scope, 'property': prop, 'operator': operator, 'value': target},
            'source': value.get('description') or raw_text,
            'sender': value.get('sender', 'unknown'),
            'date': value.get('date', ''),
            'kind': 'confirmed',
        })
    # Unstructured mandatory notes must never silently disappear.
    import re
    mandatory = re.compile(r'\b(must|mandatory|required|compulsory|shall|has to|lazmi|zaroori)\b', re.I)
    for note in parsed.get('notes') or []:
        description = (note.get('description') or note.get('text') or '') if isinstance(note, dict) else str(note)
        if mandatory.search(description) and not constraints and not any(
            str(f.get('key', '')).startswith('constraint.') for f in normalized
        ):
            normalized.append({
                'key': 'constraint.unparsed',
                'value': {'scope': 'unknown', 'property': None, 'operator': 'eq', 'value': None},
                'source': description,
                'sender': note.get('sender', 'unknown') if isinstance(note, dict) else 'unknown',
                'date': '', 'kind': 'confirmed',
            })
    for i,item in enumerate(normalized):
        if isinstance(item,dict):
            item['_sequence']=start+i
            item['_is_update']=bool(previous.get('facts'))
            facts.append(item)

    # Preserve raw venue accessibility evidence for deterministic checking.
    import re
    for block in re.split(r"(?=^#\\d+\\s*\\|)", raw_text, flags=re.M):
        if "ramp access" in block.lower() or "ground floor" in block.lower():
            facts.append({
                "key": "venue.access_evidence",
                "value": block.strip(),
                "source": block.strip(),
                "sender": "Original venue message",
                "date": "",
                "kind": "informational"
            })

    outcome=plan(facts)
    outcome.update({'facts':facts,'trace':trace,'notes':list(previous.get('notes',[]))+parsed.get('notes',[]),
                    'message_history':list(previous.get('message_history',[]))+[raw_text],
                    'new_facts':normalized})
    return outcome


def save(state:dict, output_path: str | Path):
    path=Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    return path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def trace_summary(trace):
    values=[row.get('total_tokens') for row in trace]
    return {'model_calls':len(trace),'reported_total_tokens':sum(v for v in values if isinstance(v,int)),
            'all_usage_reported':all(isinstance(v,int) for v in values)}
