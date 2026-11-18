"""EventMind Judge Console v2. Read-only presentation of outputs/state.json.

No model calls, API keys, state mutation or network requests are made here.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="EventMind — Judge Console", page_icon="◈", layout="wide", initial_sidebar_state="collapsed")

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "outputs" / "state.json"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--em-muted:#93a3b8;--em-card:#131e30;--em-border:rgba(145,169,199,.17);--em-accent:#67e8d0}
html,body,[class*="css"],.stApp{font-family:'DM Sans',system-ui,sans-serif}
.stApp{background:radial-gradient(ellipse at 8% 0%,rgba(36,82,114,.26),transparent 34%),#09111d;color:#edf5ff}
.block-container{max-width:1450px;padding-top:1.65rem;padding-bottom:3rem}
#MainMenu,footer,[data-testid="stDecoration"]{visibility:hidden}
h1,h2,h3{font-family:'Space Grotesk',system-ui,sans-serif;letter-spacing:-.035em}
h2{font-size:1.5rem!important}h3{font-size:1.14rem!important}
[data-testid="stHorizontalBlock"]{gap:1rem}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:8px;flex-wrap:wrap;border-bottom:1px solid var(--em-border)}
[data-testid="stTabs"] button[role="tab"]{background:#101b2b;border:1px solid var(--em-border);border-radius:9px 9px 0 0;padding:10px 16px;font-weight:600;color:#aec1d7}
[data-testid="stTabs"] button[aria-selected="true"]{color:#c3fff2!important;border-color:#42cdb1!important;background:#152b33}
[data-testid="stTabs"] [data-baseweb="tab-panel"]{padding-top:22px}
[data-testid="stDataFrame"], [data-testid="stExpander"]{border-radius:12px;overflow:hidden}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button{border-radius:10px;border:1px solid #385269;background:#172b3c;color:#e4f4ff;font-weight:600}
[data-testid="stButton"] button:hover,[data-testid="stDownloadButton"] button:hover{border-color:#71d9c9;color:#baffef}
[data-testid="stAlert"]{border-radius:12px}
.em-eyebrow{color:#59ddc5;font-size:.74rem;letter-spacing:.17em;font-weight:800;text-transform:uppercase;margin:0 0 6px}
.em-hero{display:flex;align-items:center;gap:15px;padding:10px 0 13px}
.em-symbol{width:51px;height:51px;display:grid;place-items:center;border:1px solid rgba(104,232,207,.32);border-radius:15px;background:linear-gradient(140deg,#163943,#0d1b2d);color:#83f5df;font-size:29px;font-weight:700;flex-shrink:0}
.em-title{font:700 2.35rem 'Space Grotesk',system-ui,sans-serif;letter-spacing:-.055em;line-height:1.06;color:#f3faff}
.em-subtitle{color:#9bb0c5;font-size:.89rem;margin-top:6px}
.em-status{border:1px solid var(--em-border);border-radius:13px;padding:16px 18px;display:flex;gap:14px;align-items:center;margin:5px 0 20px;background:rgba(21,39,55,.9)}
.em-status.good{border-color:rgba(69,215,172,.27);background:rgba(17,66,59,.52)}
.em-status.bad{border-color:rgba(255,127,127,.32);background:rgba(81,31,42,.48)}
.em-status-icon{font-size:24px}.em-status strong{display:block;font-size:1rem;color:#f2fbff}.em-status small{color:#b0c5d5}
.em-kpi{background:linear-gradient(160deg,#192a40,#111d2e);border:1px solid var(--em-border);border-radius:14px;min-height:114px;padding:18px 18px 16px;margin:2px 0 8px}
.em-kpi-label{font-size:.77rem;text-transform:uppercase;letter-spacing:.075em;color:#97aabf;font-weight:700}
.em-kpi-value{font:700 clamp(1.45rem,2vw,2.05rem) 'Space Grotesk',sans-serif;letter-spacing:-.045em;margin-top:9px;line-height:1.2;color:#f2f8ff;overflow-wrap:anywhere}
.em-kpi-sub{font-size:.76rem;color:#74dec9;margin-top:4px}
.em-section{margin:0 0 14px}.em-section-label{color:#f1f7ff;font:700 1.14rem 'Space Grotesk',sans-serif;letter-spacing:-.025em}.em-section-help{color:#8aa0b7;font-size:.84rem;margin-top:2px}
.em-panel{background:linear-gradient(158deg,#172438,#111c2d);border:1px solid var(--em-border);border-radius:14px;padding:21px;margin-bottom:14px}
.em-panel-label{font-size:.8rem;color:#8fa8bf;text-transform:uppercase;letter-spacing:.085em;font-weight:700}
.em-panel-value{color:#eff8ff;font:700 1.45rem 'Space Grotesk',sans-serif;margin-top:6px;letter-spacing:-.03em}
.em-pill{display:inline-flex;align-items:center;padding:5px 10px;border:1px solid #276c65;background:#153e3c;border-radius:999px;color:#9df5df;font-size:.75rem;font-weight:700;margin-top:10px}
.em-pill.warn{border-color:#7c6037;background:#42301e;color:#ffe0aa}
.em-detail{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:10px 0;border-bottom:1px solid rgba(148,170,190,.11);font-size:.89rem}.em-detail:last-child{border-bottom:0}.em-detail span:first-child{color:#9cb0c5}.em-detail span:last-child{color:#f0f7ff;font-weight:650;text-align:right}
.em-progress{width:100%;height:10px;border-radius:99px;background:#304053;overflow:hidden;margin:17px 0 10px}.em-progress>div{height:100%;background:linear-gradient(90deg,#3ea99d,#8af2d5);border-radius:99px}
.em-stage{display:flex;align-items:flex-start;gap:12px;padding:11px 0;border-bottom:1px solid rgba(148,170,190,.1)}.em-stage:last-child{border-bottom:0}
.em-stage-no{width:27px;height:27px;border-radius:8px;background:#1a3947;color:#8de9db;display:grid;place-items:center;font-size:.78rem;font-weight:800;flex-shrink:0}
.em-stage-text{flex:1}.em-stage-name{font-size:.91rem;color:#eef8ff;font-weight:600}.em-stage-meta{font-size:.77rem;color:#829bb2;margin-top:2px}.em-stage-min{font-size:.88rem;color:#dbeef7;font-weight:700;white-space:nowrap}
.em-banner{padding:13px 16px;background:#12263b;border:1px solid rgba(102,157,195,.22);border-radius:11px;color:#bcd1e1;font-size:.86rem;margin-bottom:13px}
.em-chip{display:inline-block;border-radius:7px;padding:4px 8px;background:#1c3d44;color:#94e8d9;font-size:.8rem;font-weight:700;margin:0 7px 6px 0}
.em-note{font-size:.82rem;color:#849db4}
@media(max-width:800px){.em-title{font-size:1.8rem}.block-container{padding:1rem}.em-kpi{min-height:100px;padding:13px}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(value):
    return html.escape(str(value), quote=True)


def whole(value):
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "—"


def money(value):
    return "—" if value is None else f"Rs {whole(value)}"


def positive(value):
    try:
        return max(0, float(value))
    except (TypeError, ValueError):
        return 0.0


def kpi(label, value, sub=""):
    return (f'<div class="em-kpi"><div class="em-kpi-label">{esc(label)}</div>'
            f'<div class="em-kpi-value">{esc(value)}</div>'
            f'{f"<div class=\"em-kpi-sub\">{esc(sub)}</div>" if sub else ""}</div>')


def panel_label(title, subtitle=""):
    st.markdown(f'<div class="em-section"><div class="em-section-label">{esc(title)}</div>'
                f'<div class="em-section-help">{esc(subtitle)}</div></div>', unsafe_allow_html=True)


def details(rows):
    return "".join(f'<div class="em-detail"><span>{esc(k)}</span><span>{esc(v)}</span></div>' for k, v in rows)


@st.cache_data(show_spinner=False)
def read_state(path: str, modified: int):
    return json.loads(Path(path).read_text(encoding="utf-8"))

st.markdown('''<div class="em-hero"><div class="em-symbol">◈</div><div>
<div class="em-eyebrow">Mind to Machine · Judge Console</div>
<div class="em-title">EventMind AI</div>
<div class="em-subtitle">Constraint-aware event planning · Transparent decisions · Auditable AI</div>
</div></div>''', unsafe_allow_html=True)

if not STATE_PATH.exists():
    st.error("No saved plan found. Run the event planner CLI before opening the dashboard.")
    st.code("python cli.py data/sample_messages.txt --fresh", language="bash")
    st.stop()

try:
    state = read_state(str(STATE_PATH), STATE_PATH.stat().st_mtime_ns)
except Exception as exc:
    st.error(f"Cannot read state file: {exc}")
    st.stop()

plan = state.get("plan") or {}
event = plan.get("event") or {}
venue = plan.get("venue") or {}
food = plan.get("food") or {}
judging = plan.get("judging") or {}
budget = plan.get("budget") or {}
schedule = plan.get("schedule") or []
audit = state.get("independent_audit") or {}
trace = state.get("trace") or []
rejected = state.get("rejected") or []
warnings = state.get("warnings") or []
valid = bool(state.get("valid")) and audit.get("independently_valid") is True

l, r = st.columns([5, 1], vertical_alignment="center")
with l:
    if valid:
        st.markdown('<div class="em-status good"><span class="em-status-icon">✓</span><div><strong>Plan verified</strong><small>Independent audit passed · All recorded checks satisfied</small></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="em-status bad"><span class="em-status-icon">!</span><div><strong>Plan requires review</strong><small>Check missing facts, mandatory constraints or independent audit failures</small></div></div>', unsafe_allow_html=True)
with r:
    if st.button("↻ Refresh", use_container_width=True):
        read_state.clear()
        st.rerun()

k1, k2, k3, k4, k5 = st.columns(5)
for col, markup in zip((k1,k2,k3,k4,k5), (
    kpi("Students",whole(event.get("students")),f'{whole(event.get("team_size"))} per team'),
    kpi("Teams",whole(event.get("teams"))),
    kpi("Selected venue",venue.get("name") or "Not selected"),
    kpi("Total expenses",money(budget.get("total"))),
    kpi("Budget remaining",money(budget.get("remaining"))),
)):
    with col:
        st.markdown(markup, unsafe_allow_html=True)

plan_tab, audit_tab, reject_tab, trace_tab, evidence_tab = st.tabs([
    "◈ Event plan", "✓ Verification", "⊘ Rejections", "⌁ Model trace", "▤ Evidence"
])

with plan_tab:
    left, right = st.columns([1.04, 1], gap="large")
    with left:
        panel_label("01  Venue & facilities", "Selection checked against capacity and mandatory requirements")
        attendance = positive(event.get("attendees"))
        capacity = positive(venue.get("capacity"))
        seat_pct = round(100 * attendance / capacity) if capacity else 0
        gen = "Standby generator available" if venue.get("generator") is True else "No confirmed generator"
        gen_cls = "" if venue.get("generator") is True else " warn"
        st.markdown(f'''<div class="em-panel"><div class="em-panel-label">Selected location</div>
        <div class="em-panel-value">{esc(venue.get('name') or 'No eligible venue')}</div>
        <div class="em-pill{gen_cls}">{esc(gen)}</div>
        <div style="margin-top:14px">{details([('Venue cost',money(venue.get('cost'))),('Required seats',whole(attendance)),('Available capacity',whole(capacity))])}</div>
        <div class="em-progress"><div style="width:{min(100,seat_pct)}%"></div></div>
        <div class="em-note">{esc(whole(attendance))} of {esc(whole(capacity))} seats required ({seat_pct}% occupancy)</div></div>''', unsafe_allow_html=True)
        with st.expander("Compare available venues"):
            st.dataframe(plan.get("available_venues") or [], use_container_width=True, hide_index=True)

        panel_label("02  Catering", "Meal coverage and priced menu options")
        chosen = food.get("selected") or {}
        st.markdown(f'''<div class="em-panel"><div class="em-panel-label">Selected meal package</div>
        <div class="em-panel-value">{esc(chosen.get('name') or 'No package selected')}</div>
        <div style="margin-top:10px">{details([('Meals required',whole(food.get('required_meals'))),('Price per meal',money(chosen.get('unit_cost'))),('Total catering cost',money(chosen.get('total_cost')))])}</div></div>''', unsafe_allow_html=True)
        if food.get("options"):
            options = food.get("options") or []
            st.dataframe([{"Menu":o.get("name"),"Per meal":money(o.get("unit_cost")),"Total":money(o.get("total_cost")),"Feasible":o.get("feasible")} for o in options],use_container_width=True,hide_index=True)
        else:
            st.warning("No usable catering option was found.")

        panel_label("03  Judging coverage", "Capacity, duration and honorarium")
        st.markdown(f'''<div class="em-panel">{details([
          ('Confirmed judges',whole(judging.get('judges'))),
          ('Teams to evaluate',whole(event.get('teams'))),
          ('Maximum teams per judge',whole(judging.get('max_teams_per_judge'))),
          ('Estimated parallel judging',f"{whole(judging.get('estimated_parallel_minutes'))} min"),
          ('Total honorarium',money(judging.get('honorarium_total')))
        ])}</div>''', unsafe_allow_html=True)

    with right:
        panel_label("04  Event schedule", "All activities fit within the approved event duration")
        stages = "".join(f'''<div class="em-stage"><div class="em-stage-no">{i:02d}</div>
            <div class="em-stage-text"><div class="em-stage-name">{esc(x.get('activity','Activity'))}</div>
            <div class="em-stage-meta">{esc(round(positive(x.get('minutes')) / max(1,positive(event.get('duration_minutes'))) * 100))}% of event</div></div>
            <div class="em-stage-min">{whole(x.get('minutes'))} min</div></div>''' for i,x in enumerate(schedule,1))
        st.markdown(f'''<div class="em-panel">{stages}{details([('Total scheduled',f"{whole(sum(positive(s.get('minutes')) for s in schedule))} min"),('Approved duration',f"{whole(event.get('duration_minutes'))} min")])}</div>''', unsafe_allow_html=True)

        panel_label("05  Budget allocation", "Approved funding, commitments and remaining headroom")
        approved = positive(budget.get("approved"))
        spent = positive(budget.get("total"))
        ratio = spent / approved * 100 if approved else 0
        commitments = budget.get("committed") or {}
        expenditure_rows = [('Venue',money(budget.get('venue'))),('Judges',money(budget.get('judges'))),('Catering',money(budget.get('food')))]
        expenditure_rows.extend((str(k).replace('_',' ').title(),money(v)) for k,v in commitments.items())
        st.markdown(f'''<div class="em-panel"><div class="em-panel-label">Budget utilization</div>
            <div class="em-panel-value">{esc(money(budget.get('total')))} <span style="font-size:.86rem;color:#90a9bd;font-family:DM Sans;font-weight:500">/ {esc(money(budget.get('approved')))}</span></div>
            <div class="em-progress"><div style="width:{min(100,max(0,ratio)):.2f}%"></div></div>
            <div class="em-note">{ratio:.1f}% used · {esc(money(budget.get('remaining')))} remaining</div>
            <div style="margin-top:16px">{details(expenditure_rows)}</div></div>''', unsafe_allow_html=True)

    panel_label("Mandatory constraints", "Each constraint must be enforced or marked as unresolved")
    constraints = plan.get("other_constraints") or []
    if constraints:
        for c in constraints:
            label = c.get("key") or f"{c.get('scope','unknown')}.{c.get('field','unknown')}"
            status = c.get("status", "unresolved")
            msg = c.get("source") or "No source text"
            st.markdown(f'<div class="em-banner"><strong>{esc(label)}</strong> &nbsp;·&nbsp; {esc(status)}<div class="em-note">{esc(msg)}</div></div>',unsafe_allow_html=True)
    else:
        st.info("No explicit mandatory constraints were recorded.")

with audit_tab:
    panel_label("Independent verification", "Checks are computed separately from the planner's own validity flag")
    if not audit:
        st.error("No independent audit is saved. Do not treat the planner's validity flag as verified.")
    else:
        a,b,c=st.columns(3)
        with a: st.markdown(kpi("Checks passed",f"{audit.get('passed','—')} / {audit.get('total','—')}"),unsafe_allow_html=True)
        with b: st.markdown(kpi("Independent result","PASS" if audit.get('independently_valid') else "FAIL"),unsafe_allow_html=True)
        with c: st.markdown(kpi("Planner result","PASS" if state.get('valid') else "FAIL"),unsafe_allow_html=True)
        checks = audit.get("checks") or []
        failed=[x for x in checks if not x.get("pass")]
        if failed:
            st.error(f"{len(failed)} failed check(s) need attention.")
        for passed_group, title in [(False,"Failures / unresolved"),(True,"Passed checks")]:
            items=[x for x in checks if bool(x.get("pass")) == passed_group]
            if not items: continue
            with st.expander(f"{title} ({len(items)})",expanded=not passed_group):
                for x in items:
                    mark="✓" if x.get("pass") else "✕"
                    st.markdown(f"**{mark} {x.get('check','Unnamed check')}**")
                    if x.get("detail") or x.get("reason"):
                        st.caption(str(x.get("detail") or x.get("reason")))
    if warnings:
        st.warning("\n\n".join(map(str,warnings)))

with reject_tab:
    panel_label("Rejected or excluded messages", "Shows why a message was not allowed to change the plan")
    st.markdown(kpi("Recorded rejections",len(rejected)),unsafe_allow_html=True)
    if not rejected:
        st.info("No rejected messages in the current run.")
    for i, item in enumerate(rejected,1):
        with st.container(border=True):
            st.markdown(f"**{i:02d} · {item.get('source','Unknown source')}**")
            st.write(item.get("message") or "(Message text unavailable)")
            st.error(str(item.get("reason") or "Reason not recorded"))

with trace_tab:
    panel_label("Model-call audit trail", "Real calls only · Actual inputs, outputs and token counts reported by the provider")
    tokens = sum(positive(c.get("total_tokens")) for c in trace)
    seconds = sum(positive(c.get("elapsed_seconds")) for c in trace)
    a,b,c=st.columns(3)
    with a:st.markdown(kpi("Model calls",len(trace)),unsafe_allow_html=True)
    with b:st.markdown(kpi("Reported tokens",whole(tokens)),unsafe_allow_html=True)
    with c:st.markdown(kpi("Combined call time",f"{seconds:.2f}s"),unsafe_allow_html=True)
    st.caption("Call duration is not the same as total CLI wall-clock time. Missing usage is never estimated.")
    for i,call in enumerate(trace,1):
        title=f"Call {call.get('number',i)} · {call.get('area','unknown')} · {call.get('model','unknown')} · {whole(call.get('total_tokens'))} tokens"
        with st.expander(title,expanded=False):
            st.write("**Provider-reported usage**",{k:call.get(k) for k in ('input_tokens','output_tokens','total_tokens')})
            st.caption(f"Elapsed: {call.get('elapsed_seconds','unknown')}s · Finish: {call.get('finish_reason','not reported')}")
            st.markdown("**Input sent to model**")
            st.json(call.get('input'),expanded=False)
            st.markdown("**Raw model output**")
            output=call.get('output')
            if isinstance(output,str): st.code(output,language="json")
            else: st.json(output,expanded=False)

with evidence_tab:
    panel_label("Evidence & provenance", "Source-supported planning decisions and the original message history")
    with st.expander("Evidence for selected facts",expanded=True):
        st.json(plan.get("evidence") or {},expanded=False)
    with st.expander(f"All extracted facts ({len(state.get('facts') or [])})"):
        st.json(state.get('facts') or [],expanded=False)
    with st.expander(f"Input message batches ({len(state.get('message_history') or [])})"):
        for i,message in enumerate(state.get('message_history') or [],1):
            st.text_area(f"Input batch {i}",str(message),height=125,key=f"input_batch_{i}")

st.divider()
x,y=st.columns([1,2],vertical_alignment="center")
with x:
    st.download_button("↓ Download full judge report (JSON)", data=json.dumps(state,indent=2,ensure_ascii=False),file_name="eventmind_judge_report.json",mime="application/json",use_container_width=True)
with y:
    st.caption("Read-only judge console. Process messages through the CLI; use Refresh to view the latest saved run. No AI calls occur when opening this page.")
