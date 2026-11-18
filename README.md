# EventMind AI — Mind to Machine Hackathon

A **working prototype** of a traceable, constraint-aware event planning agent. Built for the brief's five areas: venue, schedule, food, judging, budget. Runs on macOS using Python, an OpenAI-compatible small-model endpoint, and Streamlit.

## 1. Set up on Mac

Open **Terminal** in the project folder (or open the folder in VS Code):

```bash
python3 --version
git --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and insert a *real* model API key. Configure `OPENAI_MODEL` to an eligible model **after verifying the organizers' small-model list**. Do not commit `.env`.

## 2. First run — ONE command

```bash
python cli.py data/sample_messages.txt --fresh
```

Saved automatically:
- `outputs/state.json`: all facts, source messages, validation, history, and full trace
- `outputs/plan.json`: five-area event plan
- `outputs/trace.json`: actual model calls, exact input/output and reported tokens

## 3. Process new messages — SAME command

```bash
python cli.py data/practice_change.txt
python cli.py data/practice_wrong.txt
```

The only argument that changes is the path to the incoming text file. When judges release their unseen pack, run `python cli.py /path/to/unseen.txt --fresh`, then run `python cli.py /path/to/new-message.txt` for each update. No facts or messages are edited in Python code. An initial fresh run is required when switching to a separate test pack.

## 4. Launch UI

```bash
streamlit run app.py
```

Upload the same message pack, then updates one by one. The UI displays plan validity, the five areas, rejected messages, evidence and every model call. The terminal runner remains the auditable single-command path.

## 5. Run tests

```bash
python -m unittest discover -s tests -v
```

The tests use synthetic facts in test fixtures, **not in the production planner**. Tests don't require internet/API keys.

## 6. Understanding the architecture

- `eventmind/model.py`: exactly one text-understanding API request per supplied file; records exact prompt, reply, reported tokens, model and area tag.
- `eventmind/engine.py`: pure Python arithmetic, venue selection, meal sufficiency, budget and judging feasibility. Recomputes the plan without extra AI calls.
- `eventmind/state.py`: facts + trace persistence across incremental updates.
- `cli.py`: the same command for pack and all later messages, with printed trace and file exports.
- `app.py`: Streamlit interface.

**Why this architecture?** Language parsing benefits from a model; arithmetic doesn't. Full recomputation of deterministic code is fast and requires zero tokens. Therefore an update uses **one reading model call** and no venue/schedule/food/judging/budget model calls. Predict that before an update: *reading only*.

## 7. Important prototype limits — fix before judging

- **The brief says 177 people to feed in its wrong-message example, but the sample message figures imply 180**: 150 students + 10 staff + 20 judges. Do not silently choose between those: ask organizers which staff/judges overlap, or which attendance convention applies. Our current deterministic plan gives 180 on the sample's explicit counts.
- Unknown constraints are *collected and flagged as unvalidated*, **not** automatically enforced. This is safer than claiming a valid plan for an unknown rule, but more general constraint handlers are needed for hidden tests.
- An AI extraction call could omit facts, mix up dates, or output invalid JSON. We deliberately surface failures rather than invent output or tokens. Test the selected provider for `response_format=json_object` support.
- The trace records actual provider-reported counts. If the provider omits usage, the trace says `null`; we never fabricate token statistics.
- The current schedule uses a flexible duration policy; it is not yet a full time-window/resource constraint solver. Some hidden rules may need more validations.
- A requested DJ is excluded unless approved. Confirm any optional purchasing policy with the organizers.
- The brief originally says code freeze **1:25 PM**, whereas you report a later oral instruction to consider **1:50 PM**. Verify the updated deadline in the official all-teams channel before relying on it.

## 8. Submission checklist

1. Create a GitHub repository and commit your code frequently.
2. Test API speed and rate limits during the first minutes of the build.
3. Test unseen-style packs, misleading instructions, dates, and Roman Urdu.
4. Verify `git status` clean and save the final `git log -1` hash.
5. Push before the confirmed code freeze. Do not alter the code afterwards.
6. Save/upload `plan.json`, `trace.json`, and complete run output as requested.
7. All three teammates should understand each component and why it exists.

**Security:** Never share your `.env` or API keys. `.gitignore` excludes local state and secrets. Do not make unverifiable claims about scoring, model eligibility, or runtime.
