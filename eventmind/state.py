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
