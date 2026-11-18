import unittest
from eventmind.engine import plan


def sample_facts():
    base=[
        ('event.students',150),('event.team_size',3),('event.duration_minutes',240),('event.budget',650000),
        ('event.staff',10),('event.prayer_minutes',15),('judging.judges',20),('judging.honorarium',5000),
        ('judging.minutes_per_team',15),('judging.max_teams_per_judge',3),
        ('expense.prizes',100000),('expense.backup_internet',20000),('expense.printing',10000),
    ]
    facts=[{'key':k,'value':v,'source':k,'kind':'confirmed','date':'9 Nov','_sequence':i} for i,(k,v) in enumerate(base)]
    for name,c,price in [('Room D',80,40000),('Hall A',200,120000),('Hall B',200,150000)]:
        facts.append({'key':'venue.offer','value':{'name':name,'capacity':c,'cost':price},'kind':'confirmed','date':'3 Nov'})
    facts.extend([
        {'key':'food.offer','value':{'name':'standard','unit_cost':1000},'kind':'confirmed','date':'20 Oct'},
        {'key':'food.offer','value':{'name':'standard','unit_cost':1200},'kind':'confirmed','date':'12 Nov'},
        {'key':'food.offer','value':{'name':'basic','unit_cost':800},'kind':'confirmed','date':'12 Nov'},
    ])
    return facts

class PlannerTests(unittest.TestCase):
    def test_sample_plan(self):
        res=plan(sample_facts())
        self.assertTrue(res['valid'],res['warnings'])
        p=res['plan']
        self.assertEqual(p['event']['teams'],50)
        self.assertEqual(p['event']['attendees'],180) # 150 students + 10 staff + 20 judges
        self.assertEqual(p['venue']['name'],'Hall A')
        self.assertEqual(p['food']['selected']['total_cost'],216000)
        self.assertEqual(p['judging']['estimated_parallel_minutes'],45)
        self.assertEqual(sum(x['minutes'] for x in p['schedule']),240)
        self.assertEqual(p['budget']['remaining'],84000)
    def test_bad_caterer_quantity(self):
        facts=sample_facts()+[{'key':'food.order_quantity','value':100,'source':'Only 100 boxes','sender':'Caterer','kind':'proposed'}]
        r=plan(facts)
        self.assertTrue(r['valid'])
        self.assertTrue(any('100 meals' in x['reason'] for x in r['rejected']))
    def test_printing_correction(self):
        facts=sample_facts()+[{'key':'expense.printing','value':15000,'kind':'confirmed','source':'printing increased','date':'18 Nov','_sequence':200}]
        r=plan(facts)
        self.assertEqual(r['plan']['budget']['committed']['printing'],15000)
        self.assertEqual(r['plan']['budget']['remaining'],79000)
    def test_unknown_constraint_never_silently_accepted(self):
        facts=sample_facts()+[{'key':'constraint.accessibility','value':{'description':'wheelchair ramps required'},'kind':'confirmed'}]
        self.assertFalse(plan(facts)['valid'])

if __name__=='__main__': unittest.main()
