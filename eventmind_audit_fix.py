from pathlib import Path
import ast

ROOT = Path('/content/eventmind_project')
if not ROOT.exists():
    ROOT = Path(__file__).resolve().parent / 'em_fix' / 'eventmind_project'
engine = ROOT / 'eventmind' / 'engine.py'
model = ROOT / 'eventmind' / 'model.py'
code = engine.read_text()
old = """def _rank(fact):
    return (_date(fact.get('date')), int(fact.get('_sequence',0)))
"""
new = """def _rank(fact):
    # An undated *new incoming update* is current; its file sequence is authoritative
    # for replacing older dated facts. Older dated messages still compare by date.
    sequence = int(fact.get('_sequence', 0))
    if not str(fact.get('date') or '').strip() and fact.get('_is_update'):
        return ((9999, 12, 31), sequence)
    return (_date(fact.get('date')), sequence)
"""
if old in code: code = code.replace(old,new)
old = """    if students is None and teams is not None and team_size:
        students = teams * team_size
    staff = _num(field('event.staff'),0)
"""
new = """    if students is None and teams is not None and team_size:
        students = teams * team_size
    # Extraction sanity check: an LLM may reverse number-of-teams and
    # people-per-team. Repair only when the reversal is mathematically provable.
    if (students is not None and teams is not None and team_size is not None
            and teams * team_size != students
            and teams > 0 and team_size > 0
            and students == teams * team_size):
        pass  # unreachable, retained for readability
    if (students is not None and teams is not None and team_size is not None
            and teams * team_size != students and teams != team_size
            and students % teams == 0 and students % team_size == 0):
        # Arithmetic alone cannot disambiguate reversed factors! Source text
        # must explicitly say 'teams of N' before correction is defensible.
        sources = ' '.join(str(f.get('source','')) for f in facts
                           if f.get('key') in ('event.teams', 'event.team_size'))
        import re as _re
        m = _re.search(r'\\bteams?\\s+of\\s+(\\d+)\\b', sources, _re.I)
        if m:
            explicit_team_size = float(m.group(1))
            if explicit_team_size in (teams, team_size) and students % explicit_team_size == 0:
                teams, team_size = students / explicit_team_size, explicit_team_size
                evidence['event.team_size'] = {'source':m.group(0),'sender':'source verification','date':''}
    staff = _num(field('event.staff'),0)
"""
# Fix the flaw in first draft: reversed 3 and 50 multiply to students too,
# so need compare original source instead of only arithmetic mismatch.
new = """    if students is None and teams is not None and team_size:
        students = teams * team_size
    # Verify the meaning of 'teams of N' against the raw cited evidence.
    # A reversal of 3 and 50 still multiplies to 150; arithmetic is insufficient.
    if students is not None and team_size is not None:
        import re as _re
        sources = ' '.join(str(f.get('source','')) for f in facts
                           if f.get('key') in ('event.teams', 'event.team_size', 'event.students'))
        matches = _re.findall(r'\\bteams?\\s+of\\s+(\\d+)\\b', sources, _re.I)
        sizes = set(int(v) for v in matches)
        if len(sizes) == 1:
            explicit_size = float(next(iter(sizes)))
            if explicit_size > 0 and students % explicit_size == 0:
                if team_size != explicit_size or teams != students / explicit_size:
                    team_size = explicit_size
                    teams = students / explicit_size
                    evidence['event.team_size'] = {'source':f'teams of {int(explicit_size)}', 'sender':'source verification', 'date':''}
    staff = _num(field('event.staff'),0)
"""
if old in code: code=code.replace(old,new)
engine.write_text(code)

state = ROOT / 'eventmind' / 'state.py'
scode = state.read_text()
scode = scode.replace("            item['_sequence']=start+i\n", "            item['_sequence']=start+i\n            item['_is_update']=bool(previous.get('facts'))\n")
state.write_text(scode)

mcode=model.read_text()
addon = '''
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
'''
if 'MANDATORY EXTRACTION CHECKS BEFORE RETURNING JSON' not in mcode:
    idx = mcode.index('\ndef extract(')
    mcode = mcode[:idx] + addon + mcode[idx:]
model.write_text(mcode)

ast.parse(engine.read_text())
ast.parse(state.read_text())
ast.parse(model.read_text())
print('Audit patches installed. Next: restart from the sample pack with --fresh, then run both updates.')
