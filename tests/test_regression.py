
import json
import unittest
from pathlib import Path

class TestEventMindRegression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.state = json.loads(
            Path("outputs/state.json").read_text()
        )
        cls.plan = cls.state["plan"]

    def test_team_calculation(self):
        e = self.plan["event"]
        self.assertEqual(e["teams"], 50)
        self.assertEqual(e["team_size"], 3)

    def test_generator_constraint(self):
        self.assertEqual(self.plan["venue"]["name"], "Hall B")
        self.assertTrue(self.plan["venue"]["generator"])

    def test_judging(self):
        self.assertEqual(
            self.plan["judging"]["estimated_parallel_minutes"], 45
        )

    def test_food_options(self):
        prices = [
            x["unit_cost"]
            for x in self.plan["food"]["options"]
        ]
        self.assertIn(800, prices)
        self.assertIn(1200, prices)

    def test_printing_update(self):
        self.assertEqual(
            self.plan["budget"]["committed"]["printing"], 15000
        )

    def test_budget(self):
        self.assertEqual(self.plan["budget"]["total"], 601000)
        self.assertEqual(self.plan["budget"]["remaining"], 49000)

    def test_wrong_food_message_rejected(self):
        self.assertTrue(any(
            "100 meals" in item["reason"]
            for item in self.state["rejected"]
        ))

    def test_valid_plan(self):
        self.assertTrue(self.state["valid"])

if __name__ == "__main__":
    unittest.main()
