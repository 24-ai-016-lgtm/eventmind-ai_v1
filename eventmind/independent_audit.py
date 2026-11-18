"""Independent, read-only audit for EventMind's saved state.

Usage: python eventmind_independent_audit.py outputs/state.json
No API/model calls and no edits to existing state. Checks source-derived facts,
not sample-specific numbers. Unknown mandatory constraints block PASS.
"""
import json
import math
import sys
from pathlib import Path


def number(v):
    if isinstance(v, bool):
        return None
    try:
        n = float(v)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def eq(a, b):
    x, y = number(a), number(b)
    return x is not None and y is not None and math.isclose(x, y, rel_tol=1e-9, abs_tol=0.01)


def audit(state):
    p = state.get('plan') or {}
    facts = state.get('facts') or []
    checks = []
    def check(name, passed, detail):
        checks.append({'check': name, 'pass': bool(passed), 'detail': detail})

    event = p.get('event') or {}
    students, teams, team_size = map(number, (event.get('students'), event.get('teams'), event.get('team_size')))
    check('Student-team arithmetic', all(x is not None and x > 0 and x.is_integer() for x in (students, teams, team_size)) if None not in (students,teams,team_size) else False and False,
          'Student count, team count and team size must be positive whole numbers')
    check('Teams × size equals students', None not in (students,teams,team_size) and eq(teams*team_size, students),
          'Team count and size must agree with student count')
    attendee_parts = [number(event.get(k)) for k in ('students','staff','judges')]
    check('Attendance arithmetic', all(x is not None and x >= 0 for x in attendee_parts) and eq(event.get('attendees'),sum(x or 0 for x in attendee_parts)),
          'Attendance must equal students + staff + judges')
    attendees = number(event.get('attendees'))

    venue = p.get('venue') or {}
    capacity = number(venue.get('capacity'))
    check('Venue capacity', bool(venue) and capacity is not None and attendees is not None and capacity >= attendees,
          'Selected venue must seat all calculated attendees')
    offers = [f.get('value') for f in facts if f.get('key') == 'venue.offer' and isinstance(f.get('value'),dict) and f.get('value',{}).get('name')]
    check('Venue is offered', bool(venue.get('name')) and any(v.get('name')==venue.get('name') for v in offers),
          'Selected venue must appear in the input offers')

    food = p.get('food') or {}
    selected = food.get('selected') or {}
    meals = number(food.get('required_meals'))
    check('Food quantity', meals is not None and attendees is not None and meals >= attendees and bool(selected),
          'Enough meals must be provided to cover attendance')
    unit = number(selected.get('unit_cost'))
    delivery = number(selected.get('delivery_cost'))
    cost = number(selected.get('total_cost'))
    check('Food arithmetic', None not in (meals,unit,delivery,cost) and eq(cost, meals*unit+delivery),
          'Food total must equal quantity × unit price + delivery charge')
    # Unknown delivery must not be implicitly presumed free, unless an explicit offer says so.
    if selected:
        check('Food cost source', bool(selected.get('source')),
              'Selected meal must identify its source quotation')

    j = p.get('judging') or {}
    judges = number(j.get('judges'))
    per_team = number(j.get('minutes_per_team'))
    max_per = number(j.get('max_teams_per_judge'))
    slot = number(j.get('estimated_parallel_minutes'))
    capacity_ok = None not in (judges,teams,max_per) and judges > 0 and max_per > 0 and judges*max_per>=teams
    check('Judge coverage', capacity_ok,
          'Judge count × maximum teams per judge must cover all teams')
    rounds = math.ceil(teams/judges) if None not in (teams,judges) and judges>0 else None
    check('Judging schedule time', rounds is not None and per_team is not None and per_team>0 and slot is not None and slot >= rounds*per_team,
          'Judging must allow enough parallel rounds at the specified team time')

    schedule = p.get('schedule') or []
    duration = number(event.get('duration_minutes'))
    time_values = [number(item.get('minutes')) for item in schedule]
    check('Schedule duration', bool(schedule) and duration is not None and all(n is not None and n>=0 for n in time_values) and eq(sum(time_values), duration),
          'Scheduled activities must exactly fit the event duration')
    # Check prayer requirement from extracted source facts, never from hardcoded pack values.
    prayer_facts = [f for f in facts if f.get('key')=='event.prayer_minutes' and f.get('kind','confirmed')=='confirmed']
    if prayer_facts:
        required_prayer = max((number(f.get('value')) for f in prayer_facts), default=None)
        scheduled_prayer = sum(number(x.get('minutes')) or 0 for x in schedule if 'prayer' in str(x.get('activity','')).lower())
        check('Prayer requirement', required_prayer is not None and scheduled_prayer >= required_prayer,
              'Required prayer duration must be present in the event schedule')

    b = p.get('budget') or {}
    approved = number(b.get('approved'))
    committed = b.get('committed') or {}
    amounts = [number(x) for x in committed.values()]
    components = [number(b.get(k)) for k in ('venue','judges','food')]
    total = number(b.get('total'))
    valid_costs = all(x is not None and x>=0 for x in amounts+components)
    computed = sum(amounts+components) if valid_costs else None
    check('Budget arithmetic', computed is not None and total is not None and eq(total,computed),
          'Total cost must equal venue + judges + food + all committed expenses')
    check('Budget remaining', approved is not None and total is not None and eq(b.get('remaining'), approved-total),
          'Remaining budget must match approved minus total')
    check('Within approved budget', approved is not None and total is not None and total<=approved,
          'Total cost must not exceed the approved limit')

    # Explicit structured constraints must be applied, not merely listed.
    constraints = [f for f in facts if str(f.get('key','')).startswith('constraint.')]
    applied = p.get('other_constraints') or []
    for index, f in enumerate(constraints,1):
        source = f.get('source','')
        key = str(f.get('key',''))
        value = f.get('value')
        scope, field, op, target = None, None, 'eq', value
        parts = key.split('.')
        if len(parts)>1: scope = parts[1]
        if len(parts)>2: field = parts[2]
        if isinstance(value,dict):
            scope = value.get('scope', scope)
            field = value.get('property',value.get('field',field))
            op = str(value.get('operator',value.get('type','eq'))).lower()
            target = value.get('value',value.get('required_value'))
        status_ok = any(c.get('key')==key and c.get('status')=='applied' for c in applied)
        actual = venue.get(field) if scope=='venue' and field else None
        if scope == 'venue' and field and actual is not None and target is not None:
            if op in ('eq','required','boolean','bool','is','equals'):
                satisfied = (actual is target) if isinstance(target,bool) else actual==target
            elif op in ('gte','min','minimum','>=','at_least'):
                satisfied = number(actual) is not None and number(target) is not None and number(actual)>=number(target)
            elif op in ('lte','max','maximum','<=','at_most'):
                satisfied = number(actual) is not None and number(target) is not None and number(actual)<=number(target)
            else:
                satisfied = False
            check(f'Mandatory constraint {index}: {key}', status_ok and satisfied,
                  f'Applied and verified: {source}')
        else:
            check(f'Mandatory constraint {index}: {key}', False,
                  'Cannot independently verify this mandatory requirement; do not declare valid')
    for c in applied:
        if c.get('status') != 'applied':
            check('Unsupported constraint',False,f"Unverified: {c.get('key')}")

    check('Planner warning agreement', not state.get('warnings'),
          'Planner has unresolved warnings')
    return {'passed':sum(c['pass'] for c in checks),'total':len(checks),
            'independently_valid':all(c['pass'] for c in checks),'checks':checks,
            'planner_reported_valid':state.get('valid')}

if __name__ == '__main__':
    filename = Path(sys.argv[1]) if len(sys.argv)>1 else Path('outputs/state.json')
    result = audit(json.loads(filename.read_text(encoding='utf-8')))
    for c in result['checks']:
        print(('PASS' if c['pass'] else 'FAIL'),c['check'],'—',c['detail'])
    print(f"\nINDEPENDENT AUDIT: {result['passed']}/{result['total']} checks")
    print('Independent plan validity:',result['independently_valid'])
    print('Planner-reported validity:',result['planner_reported_valid'])
    sys.exit(0 if result['independently_valid'] else 1)
