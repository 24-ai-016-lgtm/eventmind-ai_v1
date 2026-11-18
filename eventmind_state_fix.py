"""Normalize model constraints into EventMind's fact pipeline. No sample-pack facts."""
from pathlib import Path
import ast
ROOT=Path('/content/eventmind_project')
if not ROOT.exists():
    ROOT=Path('/mnt/data/em_fix/eventmind_project')
p=ROOT/'eventmind'/'state.py'
s=p.read_text()
needle="    for i,item in enumerate(parsed['facts']):\n"
insert='''    # The language model may put requirements in a top-level "constraints"
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
    mandatory = re.compile(r'\\b(must|mandatory|required|compulsory|shall|has to|lazmi|zaroori)\\b', re.I)
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
'''
assert needle in s, 'Expected processing loop not found: no changes made'
s=s.replace(needle,insert,1)
s=s.replace("'new_facts':parsed.get('facts',[])","'new_facts':normalized",1)
ast.parse(s)
p.write_text(s)
print('State constraint normalization installed:',p)
