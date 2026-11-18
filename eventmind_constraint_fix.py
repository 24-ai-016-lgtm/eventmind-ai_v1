"""Patch EventMind's constraint extraction/validation without embedding pack values."""
from pathlib import Path
import ast
ROOT = Path('/content/eventmind_project')
if not ROOT.exists():
    ROOT = Path(__file__).resolve().parent / 'em_fix' / 'eventmind_project'
engine = ROOT/'eventmind'/'engine.py'
model = ROOT/'eventmind'/'model.py'
code = engine.read_text()
old = """    valid_venues.sort(key=lambda v: (v['cost'],v['capacity']))
    venue = valid_venues[0] if valid_venues else None
"""
new = """    # Generic constraint schema: constraint.<scope>.<field>, value may be
    # a scalar or {operator: required|eq|gte|lte, value: ...}.
    # Backward compatibility: a name-less 'venue.offer' whose source explicitly
    # states a mandatory requirement is NOT an offer, but a venue constraint.
    all_constraints = []
    mandatory_words = re.compile(r'\\b(must|mandatory|required|compulsory|shall|has to|zaroori|lazmi)\\b', re.I)
    for f in confirmed:
        key = str(f.get('key',''))
        if key.startswith('constraint.'):
            value = f.get('value')
            parts = key.split('.')
            scope = parts[1] if len(parts)>1 else None
            property_name = parts[2] if len(parts)>2 else None
            if isinstance(value,dict):
                scope = value.get('scope') or scope
                property_name = value.get('property') or value.get('field') or property_name
                operator = value.get('operator') or value.get('type') or 'eq'
                target = value.get('value',value.get('required_value'))
            else:
                operator, target = 'eq', value
            all_constraints.append({'scope':scope,'field':property_name,'operator':operator,
                                    'value':target,'source':f.get('source',''),'key':key})
        elif key=='venue.offer' and isinstance(f.get('value'),dict):
            v = f['value']
            if not v.get('name') and mandatory_words.search(f.get('source','')):
                for field_name, target in v.items():
                    if field_name in ('name','description'): continue
                    all_constraints.append({'scope':'venue','field':field_name,'operator':'eq',
                                            'value':target,'source':f.get('source',''),'key':'constraint.venue.'+field_name})

    def satisfies(actual, operator, target):
        op = str(operator).strip().lower()
        if op in ('required','equals','equal','eq','==','is','must','boolean'):
            if isinstance(target,bool): return isinstance(actual,bool) and actual is target
            return actual == target
        try:
            a, b = float(actual), float(target)
        except (ValueError, TypeError):
            return False
        if op in ('gte','>=','min','minimum','at_least'): return a>=b
        if op in ('lte','<=','max','maximum','at_most'): return a<=b
        if op in ('gt','>'): return a>b
        if op in ('lt','<'): return a<b
        return False

    supported_constraints = []
    unsupported_constraints = []
    for requirement in all_constraints:
        # Never silently ignore an unrecognized constraint.
        if requirement['scope']=='venue' and requirement['field'] and requirement['value'] is not None:
            prop = requirement['field']
            if valid_venues and all(prop in v for v in valid_venues):
                supported_constraints.append(requirement)
            else:
                unsupported_constraints.append(requirement)
        else:
            unsupported_constraints.append(requirement)
    for requirement in supported_constraints:
        valid_venues = [v for v in valid_venues if satisfies(
            v.get(requirement['field']), requirement['operator'], requirement['value'])]
    if unsupported_constraints:
        warnings.append('One or more mandatory constraints could not be verified: '+
                        ', '.join(str(c['key']) for c in unsupported_constraints))
    valid_venues.sort(key=lambda v: (v['cost'],v['capacity']))
    venue = valid_venues[0] if valid_venues else None
"""
if old not in code:
    if 'supported_constraints = []' not in code:
        raise RuntimeError('Venue block not found. No changes made; please send engine.py.')
else:
    code=code.replace(old,new,1)
old2 = """    unknown_constraints=[]
    for f in confirmed:
        if f.get('key','').startswith('constraint.'):
            unknown_constraints.append({'key':f['key'],'value':f.get('value'),'source':f.get('source','')})
    if unknown_constraints:
        warnings.append('New constraint types were extracted but require explicit validation before the plan can be marked valid.')
"""
new2 = """    unknown_constraints = [{**c, 'status':('unverified' if c in unsupported_constraints else 'applied')}
                           for c in all_constraints]
"""
if old2 in code:
    code=code.replace(old2,new2,1)
elif 'unknown_constraints = [{**c' not in code:
    raise RuntimeError('Other-constraints block not found. No changes made; please send engine.py.')
ast.parse(code)
engine.write_text(code)
mcode=model.read_text()
addition = '''\nSYSTEM += """\nMandatory instructions about available options are REQUIREMENTS, not new offers.\nFor example, if a message says a venue must have a property, return\nconstraint.venue.<property> with value {"scope":"venue", "property":"<property>",\n"operator":"eq", "value":true}, NOT venue.offer without a name.\nFor minimum/maximum numerical requirements use operators gte/lte.\nFor any novel mandatory constraint that cannot be represented by a known property,\nreturn constraint.<topic> with its original description and scope; never drop it.\nNever invent venue names, capacities, or approval authority.\n"""\n'''
if 'Mandatory instructions about available options are REQUIREMENTS' not in mcode:
    pos=mcode.index('\ndef extract(')
    mcode=mcode[:pos]+addition+mcode[pos:]
ast.parse(mcode)
model.write_text(mcode)
print('Constraint handling patch installed. Rerun fresh sample and updates before generator test.')
