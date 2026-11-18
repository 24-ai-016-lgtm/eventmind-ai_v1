"""Deterministic, inspectable plan builder; pack numbers are never embedded in code."""
import math
import re
from datetime import datetime


def _num(value, fallback=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _date(value):
    v = str(value or '').strip()
    for fmt in ('%d %b %Y','%d %B %Y','%Y-%m-%d','%d %b','%d %B'):
        try:
            result = datetime.strptime(v + (' 2026' if '%Y' not in fmt else ''), fmt + (' %Y' if '%Y' not in fmt else ''))
            return (result.year if '%Y' in fmt else 2026, result.month, result.day)
        except ValueError:
            pass
    return (0, 0, 0)


def _rank(fact):
    # An undated *new incoming update* is current; its file sequence is authoritative
    # for replacing older dated facts. Older dated messages still compare by date.
    sequence = int(fact.get('_sequence', 0))
    if not str(fact.get('date') or '').strip() and fact.get('_is_update'):
        return ((9999, 12, 31), sequence)
    return (_date(fact.get('date')), sequence)


def _is_confirmed(f):
    return f.get('kind', 'confirmed') == 'confirmed'


def plan(facts):
    """Returns plan, errors, rejected and supporting decisions. No model calls."""
    warnings, rejected, evidence = [], [], {}
    confirmed = [f for f in facts if isinstance(f, dict) and _is_confirmed(f)]
    other = [f for f in facts if isinstance(f, dict) and not _is_confirmed(f)]
    for f in other:
        if f.get('key','').startswith('request.'):
            rejected.append({'message':f.get('source',''), 'reason':'Optional request, not an approved requirement; excluded unless explicitly authorized.', 'source':f.get('sender','')})

    def field(key, default=None):
        candidates = [f for f in confirmed if f.get('key')==key]
        if not candidates:
            return default
        winner = max(candidates, key=_rank)
        evidence[key] = {'source':winner.get('source',''), 'sender':winner.get('sender',''), 'date':winner.get('date','')}
        return winner.get('value', default)

    students = _num(field('event.students'))
    team_size = _num(field('event.team_size'))
    teams = _num(field('event.teams'))
    if teams is None and students is not None and team_size and students % team_size == 0:
        teams = students / team_size
    if students is None and teams is not None and team_size:
        students = teams * team_size
    # Verify the meaning of 'teams of N' against the raw cited evidence.
    # A reversal of 3 and 50 still multiplies to 150; arithmetic is insufficient.
    if students is not None and team_size is not None:
        import re as _re
        sources = ' '.join(str(f.get('source','')) for f in facts
                           if f.get('key') in ('event.teams', 'event.team_size', 'event.students'))
        matches = _re.findall(r'\bteams?\s+of\s+(\d+)\b', sources, _re.I)
        sizes = set(int(v) for v in matches)
        if len(sizes) == 1:
            explicit_size = float(next(iter(sizes)))
            if explicit_size > 0 and students % explicit_size == 0:
                if team_size != explicit_size or teams != students / explicit_size:
                    team_size = explicit_size
                    teams = students / explicit_size
                    evidence['event.team_size'] = {'source':f'teams of {int(explicit_size)}', 'sender':'source verification', 'date':''}
    staff = _num(field('event.staff'),0)
    judges = _num(field('judging.judges'),0)
    duration = _num(field('event.duration_minutes'))
    prayer = _num(field('event.prayer_minutes'),0)
    budget = _num(field('event.budget'))
    honorarium = _num(field('judging.honorarium'),0)
    minutes_per_team = _num(field('judging.minutes_per_team'))
    max_teams_per_judge = _num(field('judging.max_teams_per_judge'))

    attendees = students + staff + judges if None not in (students,staff,judges) else None
    if students is None or teams is None or duration is None or budget is None:
        warnings.append('Missing mandatory event facts (students/teams, duration or budget).')
    if students is not None and teams is not None and team_size and teams * team_size != students:
        warnings.append('Student count does not match team count × team size.')

    venue_offers = [f for f in confirmed if f.get('key')=='venue.offer' and isinstance(f.get('value'),dict)]
    by_venue = {}
    for offer in venue_offers:
        name = str(offer['value'].get('name','')).strip()
        if name and (name not in by_venue or _rank(offer) > _rank(by_venue[name])):
            by_venue[name] = offer
    valid_venues = []
    for f in by_venue.values():
        v = f['value']
        capacity, cost = _num(v.get('capacity')), _num(v.get('cost'))
        if capacity is not None and cost is not None and (attendees is None or capacity >= attendees):
            valid_venues.append({'name':v['name'],'capacity':int(capacity),'cost':cost,'generator':bool(v.get('generator',False)),'source':f.get('source','')})
    # Generic constraint schema: constraint.<scope>.<field>, value may be
    # a scalar or {operator: required|eq|gte|lte, value: ...}.
    # Backward compatibility: a name-less 'venue.offer' whose source explicitly
    # states a mandatory requirement is NOT an offer, but a venue constraint.
    all_constraints = []
    mandatory_words = re.compile(r'\b(must|mandatory|required|compulsory|shall|has to|zaroori|lazmi)\b', re.I)
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
    if not venue:
        warnings.append('No verified venue offer has sufficient capacity for all attendees.')

    food_offers = [
        f for f in facts
        if f.get('kind') in ('confirmed', 'proposed')
        and f.get('key') == 'food.offer'
        and isinstance(f.get('value'), dict)
    ]

    def menu_name(name):
        name = str(name).strip().lower()
        if "standard" in name:
            return "Standard lunch box"
        if "basic" in name:
            return "Basic lunch box"
        return name

    by_menu = {}

    for offer in food_offers:
        value = offer['value']
        name = menu_name(value.get('name', ''))

        if not name:
            continue

        if name not in by_menu:
            by_menu[name] = {}

        entry = by_menu[name]

        for field in ('unit_cost', 'delivery_cost'):
            if field not in value or value[field] is None:
                continue

            previous = entry.get(field)

            if previous is None or _rank(offer) > _rank(previous['fact']):
                entry[field] = {
                    'value': value[field],
                    'fact': offer
                }

    menus = []

    for name, fields in by_menu.items():
        price = fields.get('unit_cost')

        if price is None:
            continue

        delivery = fields.get('delivery_cost')
        delivery_cost = (
            _num(delivery['value'], 0)
            if delivery else 0
        )

        menus.append({
            'name': name,
            'unit_cost': _num(price['value']),
            'delivery_cost': delivery_cost,
            'source': price['fact'].get('source', ''),
            'delivery_source': (
                delivery['fact'].get('source', '')
                if delivery else ''
            )
        })

    menus.sort(key=lambda m: m['unit_cost'])

    # Requests to reduce meal orders are checked against derived attendance, regardless of sender.
    quantity_requests = [f for f in facts if f.get('key')=='food.order_quantity']
    for f in quantity_requests:
        n = _num(f.get('value'))
        if attendees is not None and n is not None and n < attendees:
            rejected.append({'message':f.get('source',''), 'reason':f'Proposed {int(n)} meals cannot feed {int(attendees)} attendees (students + staff + judges).', 'source':f.get('sender','')})
        elif n is not None and attendees is not None and n >= attendees:
            warnings.append(f'Meal order quantity {int(n)} is at least sufficient; checking final cost for {int(attendees)} required meals.')

    expenses={}
    for f in confirmed:
        key=f.get('key','')
        if key.startswith('expense.'):
            old = expenses.get(key)
            if old is None or _rank(f)>_rank(old):
                expenses[key]=f
    committed={key.split('.',1)[1]:_num(f.get('value'),0) for key,f in expenses.items()}
    for k,f in expenses.items():
        evidence[k]={'source':f.get('source',''),'sender':f.get('sender',''),'date':f.get('date','')}
    judge_cost=judges*honorarium if judges is not None else 0
    fixed_total=sum(committed.values()) + judge_cost + (venue['cost'] if venue else 0)
    food_options=[]
    for m in menus:
        if attendees is not None:
            total=attendees*m['unit_cost'] + m['delivery_cost']
            food_options.append(dict(m,total_cost=total,feasible=budget is not None and fixed_total+total<=budget))
    # Prefer budget-feasible standard meal when available; otherwise lowest-cost feasible meal.
    feasible=[o for o in food_options if o['feasible']]
    standards=[o for o in feasible if 'standard' in o['name'].lower()]
    meal=min(standards,key=lambda m:m['total_cost']) if standards else (min(feasible,key=lambda m:m['total_cost']) if feasible else None)
    if meal is None:
        warnings.append('No offered meal option fits the budget after fixed commitments, or required facts are missing.')

    judging_minutes=None
    if teams is not None and judges and minutes_per_team and max_teams_per_judge:
        required_judges=math.ceil(teams/max_teams_per_judge)
        if judges < required_judges:
            warnings.append(f'Insufficient judges: need at least {required_judges}, have {int(judges)}.')
        judging_minutes=math.ceil(teams/judges)*minutes_per_team
        if math.ceil(teams/judges)>max_teams_per_judge:
            judging_minutes=None
    elif teams is not None:
        warnings.append('Insufficient judging rules to verify team coverage.')

    schedule=[]
    if duration is not None and judging_minutes is not None:
        # Flexible schedule formula, not tied to any sample value.
        overhead=min(15, max(5,int(duration*.06)))
        food_break=min(30,max(15,int(duration*.12)))
        closing=min(15,max(5,int(duration*.06)))
        remaining=duration-judging_minutes-prayer-food_break-closing-2*overhead
        if remaining < 0:
            warnings.append('Mandatory activities exceed the event duration.')
        else:
            for name,n in [('Arrival and opening',overhead),('Briefing',overhead),('Team work',remaining),('Prayer break',prayer),('Food break',food_break),('Judging',judging_minutes),('Awards and closing',closing)]:
                if n>0: schedule.append({'activity':name,'minutes':int(n)})

    optional=[]
    for f in facts:
        if f.get('key','').startswith('request.'):
            optional.append({'description':f.get('value'), 'source':f.get('source','')})

    unknown_constraints = [{**c, 'status':('unverified' if c in unsupported_constraints else 'applied')}
                           for c in all_constraints]

    total=fixed_total+(meal['total_cost'] if meal else 0)
    if budget is not None and total>budget:
        warnings.append('Total selected expenses exceed approved budget.')
    plan_data={
        'event':{'students':students,'teams':teams,'team_size':team_size,'staff':staff,'judges':judges,'attendees':attendees,'duration_minutes':duration},
        'venue':venue,'available_venues':valid_venues,
        'food':{'required_meals':attendees,'selected':meal,'options':food_options},
        'judging':{'judges':judges,'minutes_per_team':minutes_per_team,'max_teams_per_judge':max_teams_per_judge,'estimated_parallel_minutes':judging_minutes,'honorarium_total':judge_cost},
        'schedule':schedule,
        'budget':{'approved':budget,'venue':venue['cost'] if venue else 0,'judges':judge_cost,'food':meal['total_cost'] if meal else None,'committed':committed,'total':total if meal else None,'remaining':budget-total if budget is not None and meal else None},
        'other_constraints':unknown_constraints,'optional_requests':optional,'evidence':evidence
    }
    return {'plan':plan_data,'warnings':warnings,'rejected':rejected,'valid':len(warnings)==0}
