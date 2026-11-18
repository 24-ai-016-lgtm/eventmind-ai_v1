
"""Analyze planning dependencies without model calls."""

AREAS = ("venue", "schedule", "food", "judging", "budget")

DEPENDENCIES = {
    "venue": {"venue", "budget"},
    "schedule": {"schedule"},
    "food": {"food", "budget"},
    "judging": {"judging", "schedule", "food", "venue", "budget"},
    "expense": {"budget"},
    "budget": {"budget"},
    "event": set(AREAS),
    "constraint": set(AREAS),
    "request": {"budget"},
}

def analyze(facts):
    affected = set()
    unknown = []
    keys = []

    for fact in facts:
        key = str(fact.get("key", ""))
        keys.append(key)
        prefix = key.split(".")[0]

        if prefix == "constraint":
            parts = key.split(".")
            if len(parts) > 1 and parts[1] in AREAS:
                affected.add(parts[1])
                if parts[1] in ("venue", "food", "judging"):
                    affected.add("budget")
            else:
                affected.update(AREAS)

        elif prefix in DEPENDENCIES:
            affected.update(DEPENDENCIES[prefix])

        else:
            unknown.append(key)
            affected.update(AREAS)

    return {
        "model_call_prediction": ["reading"],
        "model_call_count_prediction": 1,
        "potentially_affected_areas": [
            a for a in AREAS if a in affected
        ],
        "fact_keys": keys,
        "unrecognized_keys": unknown,
        "requires_validation": True,
    }
