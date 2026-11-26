"""
Visual theme of "Decision Room": palette, CSS, Plotly template and HTML component helpers.

All text that comes from user data (alternative names, session title, and so on) MUST go through esc()
before it enters HTML, because a session can be uploaded from a JSON file.
"""
import html as _html

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ─── Palet ───────────────────────────────────────────────────────────────────
PAPER = "#F5F2EA"
SURFACE = "#FFFFFF"
INK = "#1A1F24"
MUTED = "#5E6670"
LINE = "#DDD7C9"
BRAND = "#0E3B3F"
BRAND_SOFT = "#E3EDEA"
ACCENT = "#C2410C"       # reserved for the recommended choice
ACCENT_SOFT = "#FBE7DA"
OK = "#2F7D4F"
WARN = "#A8660A"
BAD = "#B42318"
NEUTRAL_BAR = "#A9B4B3"

# Fixed category colours: one alternative / criterion = one colour in every chart.
CAT = ["#2A6F97", "#5B8E3E", "#C99A2E", "#7A4E8C", "#B5446E", "#2F8F9D", "#6B7280"]

FONT_BODY = "'IBM Plex Sans', 'Segoe UI', system-ui, -apple-system, sans-serif"
FONT_DISPLAY = "'Newsreader', Georgia, 'Times New Roman', serif"
FONT_MONO = "'IBM Plex Mono', Consolas, 'Courier New', monospace"


# ─── Helper HTML ─────────────────────────────────────────────────────────────
def esc(value) -> str:
    """Escapes text for HTML and stops markdown from reading '$' as a LaTeX formula."""
    return _html.escape(str(value), quote=True).replace("$", "&#36;")


def compact(*parts: str) -> str:
    """Joins HTML pieces without indentation or blank lines (markdown would treat those as a code block)."""
    return "".join(p.strip() for p in parts if p)


def render_html(*parts: str) -> None:
    st.markdown(compact(*parts), unsafe_allow_html=True)


def eyebrow(text: str) -> str:
    return f'<div class="eyebrow">{esc(text)}</div>'


def page_header(title: str, lede: str = "") -> None:
    render_html(
        f'<div class="page-head"><h1>{esc(title)}</h1>',
        f'<p>{esc(lede)}</p>' if lede else "",
        "</div>",
    )


def section(title: str, note: str = "") -> None:
    render_html(
        f'<div class="sec-head"><h2>{esc(title)}</h2>',
        f'<span>{esc(note)}</span>' if note else "",
        "</div>",
    )


def callout(kind: str, text: str, title: str = "") -> None:
    """kind: info | ok | warn | bad | accent. text/title are treated as plain text."""
    kind = kind if kind in {"info", "ok", "warn", "bad", "accent"} else "info"
    render_html(
        f'<div class="callout {kind}">',
        f'<div class="callout-title">{esc(title)}</div>' if title else "",
        f'<div class="callout-body">{esc(text)}</div></div>',
    )


def chip(text: str, kind: str = "neutral") -> str:
    return f'<span class="chip {kind}">{esc(text)}</span>'


def stat(label: str, value: str, hint: str = "") -> str:
    return compact(
        '<div class="stat">',
        f'<div class="stat-label">{esc(label)}</div>',
        f'<div class="stat-value">{esc(value)}</div>',
        f'<div class="stat-hint">{esc(hint)}</div>' if hint else "",
        "</div>",
    )


def stat_row(items) -> None:
    render_html('<div class="stat-row">', *[stat(*i) for i in items], "</div>")


def bar_cell(value: float, vmax: float, kind: str = "") -> str:
    pct = 0 if vmax <= 0 else max(0.0, min(100.0, value / vmax * 100))
    return f'<div class="minibar"><div class="minibar-fill {kind}" style="width:{pct:.1f}%"></div></div>'


# ─── Plotly ──────────────────────────────────────────────────────────────────
def _register_plotly_template() -> None:
    pio.templates["nusa"] = go.layout.Template(
        layout=dict(
            font=dict(family=FONT_BODY, size=13, color=INK),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=CAT,
            title=dict(font=dict(family=FONT_DISPLAY, size=18, color=INK), x=0, xanchor="left"),
            xaxis=dict(gridcolor="#E9E4D7", linecolor=LINE, zerolinecolor=LINE, ticks="", automargin=True),
            yaxis=dict(gridcolor="#E9E4D7", linecolor=LINE, zerolinecolor=LINE, ticks="", automargin=True),
            legend=dict(font=dict(size=12), bgcolor="rgba(0,0,0,0)"),
            hoverlabel=dict(font=dict(family=FONT_BODY, size=12), bgcolor=SURFACE, bordercolor=LINE),
            margin=dict(l=10, r=20, t=56, b=20),
        )
    )
    pio.templates.default = "nusa"


_register_plotly_template()


def show_chart(fig, key: str) -> None:
    """Shows a Plotly chart with our own template (theme=None so the Streamlit theme does not override it)."""
    st.plotly_chart(
        fig,
        theme=None,
        width="stretch",
        key=key,
        config={"displayModeBar": False, "responsive": True},
    )


# ─── CSS ─────────────────────────────────────────────────────────────────────
_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap');

:root {{
  --paper:{PAPER}; --surface:{SURFACE}; --ink:{INK}; --muted:{MUTED}; --line:{LINE};
  --brand:{BRAND}; --brand-soft:{BRAND_SOFT}; --accent:{ACCENT}; --accent-soft:{ACCENT_SOFT};
  --ok:{OK}; --warn:{WARN}; --bad:{BAD};
  --f-body:{FONT_BODY}; --f-display:{FONT_DISPLAY}; --f-mono:{FONT_MONO};
}}

html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"] {{ background: var(--paper); }}
html, body, .stMarkdown, p, li, label, input, textarea, select, button, [data-testid="stWidgetLabel"] {{
  font-family: var(--f-body);
  color: var(--ink);
}}
[data-testid="stHeader"] {{ background: transparent; height: 2.2rem; }}
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] {{ visibility: hidden; }}
.block-container {{ max-width: 1180px; padding: 3.4rem 1.5rem 4rem; }}
h1, h2, h3, h4 {{ font-family: var(--f-display); letter-spacing: -0.01em; color: var(--ink); }}
code {{ font-family: var(--f-mono); font-size: 0.85em; background: #EFEADD; color: var(--ink); padding: 0.1em 0.35em; border-radius: 4px; }}

/* Sidebar */
[data-testid="stSidebar"] {{ background: #ECE7DA; border-right: 1px solid var(--line); }}
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarContent"] {{ padding-top: 1rem; }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ font-size: 1.05rem; }}

/* Masthead */
.masthead {{ display:flex; align-items:center; gap:0.85rem; padding:0.2rem 0 0.2rem; }}
.mark {{ width:34px; height:34px; border-radius:7px; background:var(--brand); position:relative; flex:none; }}
.mark::before {{ content:""; position:absolute; inset:7px; border:2px solid #F5F2EA; border-radius:3px; }}
.mark::after {{ content:""; position:absolute; left:13px; top:13px; width:8px; height:8px; background:var(--accent); border-radius:1px; }}
.brand-name {{ font-family:var(--f-display); font-size:1.45rem; font-weight:600; line-height:1.1; color:var(--ink); }}
.brand-sub {{ font-size:0.82rem; color:var(--muted); margin-top:2px; }}
.status-line {{ display:flex; justify-content:flex-end; align-items:center; gap:0.5rem; font-size:0.82rem; color:var(--muted); height:100%; padding-top:0.35rem; }}

/* Navigasi: radio key "nav_*" tampil sebagai tab bergaris bawah */
[class*="st-key-nav_"] [role="radiogroup"] {{ gap:0; flex-wrap:wrap; border-bottom:1px solid var(--line); margin-top:0.4rem; }}
[class*="st-key-nav_"] [role="radiogroup"] > label {{
  margin:0; padding:0.7rem 1.05rem 0.65rem; border-bottom:2px solid transparent; cursor:pointer;
}}
[class*="st-key-nav_"] [role="radiogroup"] > label > div:first-child {{ display:none; }}
[class*="st-key-nav_"] [role="radiogroup"] > label p {{ font-size:0.95rem; color:var(--muted); font-weight:500; }}
[class*="st-key-nav_"] [role="radiogroup"] > label:hover p {{ color:var(--ink); }}
[class*="st-key-nav_"] [role="radiogroup"] > label:has(input:checked) {{ border-bottom-color:var(--accent); }}
[class*="st-key-nav_"] [role="radiogroup"] > label:has(input:checked) p {{ color:var(--ink); font-weight:600; }}

/* Pilihan cepat: radio key "pill_*" tampil sebagai chip */
[class*="st-key-pill_"] [role="radiogroup"] {{ gap:0.4rem; flex-wrap:wrap; }}
[class*="st-key-pill_"] [role="radiogroup"] > label {{
  margin:0; padding:0.32rem 0.8rem; border:1px solid var(--line); border-radius:999px; background:var(--surface); cursor:pointer;
}}
[class*="st-key-pill_"] [role="radiogroup"] > label > div:first-child {{ display:none; }}
[class*="st-key-pill_"] [role="radiogroup"] > label p {{ font-size:0.88rem; color:var(--ink); }}
[class*="st-key-pill_"] [role="radiogroup"] > label:hover {{ border-color:var(--brand); }}
[class*="st-key-pill_"] [role="radiogroup"] > label:has(input:checked) {{ background:var(--brand); border-color:var(--brand); }}
[class*="st-key-pill_"] [role="radiogroup"] > label:has(input:checked) p {{ color:#fff; font-weight:500; }}

/* Page and section titles */
.page-head {{ margin:1.6rem 0 1.1rem; }}
.page-head h1 {{ font-size:2.05rem; font-weight:500; margin:0 0 0.35rem; padding:0; }}
.page-head p {{ color:var(--muted); font-size:1.02rem; margin:0; max-width:46rem; line-height:1.55; }}
.sec-head {{ display:flex; align-items:baseline; gap:0.8rem; margin:2rem 0 0.7rem; padding-bottom:0.45rem; border-bottom:1px solid var(--line); }}
.sec-head h2 {{ font-size:1.25rem; font-weight:600; margin:0; padding:0; }}
.sec-head span {{ color:var(--muted); font-size:0.88rem; }}
.eyebrow {{ font-size:0.72rem; font-weight:600; letter-spacing:0.09em; text-transform:uppercase; color:var(--muted); }}
.col-head {{ font-size:0.72rem; font-weight:600; letter-spacing:0.07em; text-transform:uppercase; color:var(--muted); margin:0.4rem 0 0.1rem; }}
.explain {{ background:var(--surface); border:1px solid var(--line); border-left:3px solid var(--brand); border-radius:8px; padding:0.8rem 1rem; margin:0.2rem 0 0.9rem; font-size:0.94rem; line-height:1.55; color:var(--ink); }}

/* Kartu rekomendasi */
.hero {{ background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:1.5rem 1.7rem 1.4rem; height:100%; }}
.hero.rec {{ border-top:4px solid var(--accent); }}
.hero .eyebrow {{ color:var(--accent); }}
.hero-title {{ font-family:var(--f-display); font-size:2.7rem; font-weight:500; line-height:1.05; margin:0.45rem 0 0.2rem; color:var(--ink); }}
.hero-sub {{ color:var(--muted); font-size:1rem; margin-bottom:1.1rem; }}
.hero-facts {{ display:flex; gap:2rem; flex-wrap:wrap; border-top:1px solid var(--line); padding-top:0.9rem; }}
.fact-num {{ font-family:var(--f-display); font-size:1.7rem; font-weight:500; line-height:1; }}
.fact-lab {{ font-size:0.8rem; color:var(--muted); margin-top:0.25rem; }}

/* Peta kesepakatan */
.vote-list {{ background:var(--surface); border:1px solid var(--line); border-radius:10px; padding:0.9rem 1.2rem 0.7rem; height:100%; }}
.vote-row {{ display:flex; align-items:center; gap:0.7rem; padding:0.42rem 0; border-bottom:1px solid #EEE9DC; font-size:0.92rem; }}
.vote-row:last-child {{ border-bottom:0; }}
.vote-dot {{ width:10px; height:10px; border-radius:50%; flex:none; }}
.vote-dot.yes {{ background:var(--accent); }}
.vote-dot.no {{ background:transparent; border:2px solid var(--muted); }}
.vote-name {{ flex:1; color:var(--ink); }}
.vote-pick {{ font-family:var(--f-mono); font-size:0.85rem; color:var(--muted); }}
.vote-pick.yes {{ color:var(--accent); font-weight:500; }}

[data-testid="stColumn"]:has(.hero), [data-testid="stColumn"]:has(.vote-list) {{ display:flex; }}
[data-testid="stColumn"]:has(.hero) > div, [data-testid="stColumn"]:has(.vote-list) > div,
[data-testid="stColumn"]:has(.hero) [data-testid="stVerticalBlock"], [data-testid="stColumn"]:has(.vote-list) [data-testid="stVerticalBlock"],
[data-testid="stElementContainer"]:has(.hero), [data-testid="stElementContainer"]:has(.vote-list),
[data-testid="stElementContainer"]:has(.hero) [data-testid="stMarkdown"], [data-testid="stElementContainer"]:has(.vote-list) [data-testid="stMarkdown"],
[data-testid="stElementContainer"]:has(.hero) [data-testid="stMarkdown"] > div, [data-testid="stElementContainer"]:has(.vote-list) [data-testid="stMarkdown"] > div,
[data-testid="stElementContainer"]:has(.hero) [data-testid="stMarkdownContainer"], [data-testid="stElementContainer"]:has(.vote-list) [data-testid="stMarkdownContainer"] {{ height:100%; width:100%; }}

/* Chip, stat, callout */
.chip {{ display:inline-block; font-size:0.78rem; font-weight:500; padding:0.12rem 0.55rem; border-radius:999px; border:1px solid var(--line); background:var(--surface); color:var(--muted); white-space:nowrap; }}
.chip.ok {{ background:#E5F1E9; border-color:#C5DFCD; color:var(--ok); }}
.chip.warn {{ background:#FBF0DC; border-color:#EBD6AB; color:var(--warn); }}
.chip.bad {{ background:#FBE5E2; border-color:#EFC3BD; color:var(--bad); }}
.chip.accent {{ background:var(--accent-soft); border-color:#F0C9B0; color:var(--accent); }}
.stat-row {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:0.8rem; margin:0.2rem 0 0.4rem; }}
.stat {{ background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:0.8rem 1rem; }}
.stat-label {{ font-size:0.76rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.06em; font-weight:600; }}
.stat-value {{ font-family:var(--f-display); font-size:1.7rem; font-weight:500; margin-top:0.15rem; }}
.stat-hint {{ font-size:0.82rem; color:var(--muted); margin-top:0.1rem; }}
.callout {{ border:1px solid var(--line); border-left-width:4px; border-radius:6px; background:var(--surface); padding:0.75rem 1rem; margin:0.5rem 0 0.9rem; }}
.callout-title {{ font-weight:600; font-size:0.93rem; margin-bottom:0.15rem; }}
.callout-body {{ font-size:0.93rem; line-height:1.5; color:var(--ink); }}
.callout.info {{ border-left-color:var(--brand); }}
.callout.ok {{ border-left-color:var(--ok); background:#F3F9F5; }}
.callout.warn {{ border-left-color:var(--warn); background:#FFF9EE; }}
.callout.bad {{ border-left-color:var(--bad); background:#FEF3F1; }}
.callout.accent {{ border-left-color:var(--accent); background:#FFF6F0; }}

/* Tabel HTML ringan */
.tbl {{ width:100%; border-collapse:collapse; background:var(--surface); border:1px solid var(--line); border-radius:8px; overflow:hidden; font-size:0.92rem; }}
.tbl th {{ text-align:left; font-size:0.74rem; text-transform:uppercase; letter-spacing:0.06em; color:var(--muted); font-weight:600; padding:0.6rem 0.8rem; background:#FAF8F2; border-bottom:1px solid var(--line); }}
.tbl td {{ padding:0.62rem 0.8rem; border-bottom:1px solid #EEE9DC; vertical-align:middle; }}
.tbl tr:last-child td {{ border-bottom:0; }}
.tbl tr.top td {{ background:#FFF6F0; }}
.tbl td.num, .tbl th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.tbl .sub {{ color:var(--muted); font-size:0.82rem; }}
.rank-badge {{ display:inline-flex; align-items:center; justify-content:center; width:1.7rem; height:1.7rem; border-radius:50%; background:#EFEADD; font-weight:600; font-size:0.85rem; }}
.rank-badge.first {{ background:var(--accent); color:#fff; }}
.minibar {{ background:#EFEADD; border-radius:3px; height:8px; min-width:90px; }}
.minibar-fill {{ background:var(--brand); height:100%; border-radius:3px; }}
.minibar-fill.accent {{ background:var(--accent); }}

/* Meter konsistensi */
.meter {{ margin:0.3rem 0 0.2rem; }}
.meter-track {{ position:relative; height:10px; border-radius:5px; background:linear-gradient(90deg,#CFE3D6 0%,#CFE3D6 50%,#F2D6D2 50%,#F2D6D2 100%); }}
.meter-pin {{ position:absolute; top:-4px; width:4px; height:18px; border-radius:2px; background:var(--ink); }}
.meter-scale {{ display:flex; justify-content:space-between; font-size:0.72rem; color:var(--muted); margin-top:0.25rem; }}

/* Kontrol Streamlit */
.stButton > button, .stDownloadButton > button {{ border-radius:6px; border:1px solid var(--line); background:var(--surface); color:var(--ink); font-weight:500; box-shadow:none; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color:var(--brand); color:var(--brand); }}
.stButton > button[kind="primary"] {{ background:var(--brand); border-color:var(--brand); color:#fff; }}
.stButton > button[kind="primary"]:hover {{ background:#0A2D30; border-color:#0A2D30; color:#fff; }}
.stButton > button[kind="primary"] *, .stButton > button[kind="primary"]:hover * {{ color:#fff !important; }}
[data-testid="stExpander"] {{ border:1px solid var(--line); border-radius:8px; background:var(--surface); }}
[data-testid="stExpander"] summary p {{ font-weight:500; }}
[data-testid="stDataFrame"] {{ border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
[data-testid="stAlert"] {{ border-radius:6px; }}
[data-testid="stChatMessage"] {{ background:var(--surface); border:1px solid var(--line); border-radius:8px; }}
[class*="st-key-live_panel"] {{ position:sticky; top:3.2rem; }}

/* Calculation steps */
.step-title {{ font-family:var(--f-display); font-size:1.12rem; font-weight:600; margin:1.1rem 0 0.2rem; }}
.step-note {{ color:var(--muted); font-size:0.92rem; margin-bottom:0.5rem; }}

@media (max-width: 760px) {{
  .block-container {{ padding: 0.8rem 0.9rem 3rem; }}
  .hero-title {{ font-size:2.1rem; }}
  .page-head h1 {{ font-size:1.65rem; }}
  [class*="st-key-live_panel"] {{ position:static; }}
}}
"""


def inject_css() -> None:
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
