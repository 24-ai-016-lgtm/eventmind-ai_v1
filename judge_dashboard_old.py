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
