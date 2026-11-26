"""Page 1: Decision summary. Designed so a business team can read it on a single screen."""
from typing import Dict, Optional

import streamlit as st

from app.insights import close_calls, consensus, dm_picks, top_alts
from app.labels import METHOD_ORDER, METHODS, group_label
from app.pages_.common import need_run
from app.state import go_to, run_analysis
from app.theme import bar_cell, callout, compact, esc, page_header, render_html, section
from engine.schemas import RunResult, Session


def _names(result: RunResult, ids) -> str:
    return " / ".join(result.alternative_names.get(a, a) for a in ids)


def _pick_text(result: RunResult, ids) -> str:
    return " / ".join(ids) if ids else "-"


def render(result: Optional[RunResult], session: Session) -> None:
    page_header(
        "Decision summary",
        session.goal or "Which product to prioritise, and how strongly the team backs it.",
    )

    if result is None:
        _empty(session)
        return

    names = result.alternative_names
    seg: Dict[str, str] = {a.id: (a.segment or "") for a in session.alternatives}
    crit_names = {c.id: c.name for c in session.criteria}

    cons = consensus(result)
    best = cons["best"]
    n_methods = cons["n_methods"]
    n_agree = len(cons["agree"])
    table = cons["table"]
    picks = dm_picks(result, crit_names)
    n_dm = len(picks)
    n_dm_agree = sum(1 for p in picks if best in p["winners"])

    # ── Recommendation + agreement map ──────────────────────────────────────
    col_hero, col_votes = st.columns([3, 2.2], gap="medium")
    with col_hero:
        render_html(
            '<div class="hero rec">',
            '<div class="eyebrow">Team recommendation</div>',
            f'<div class="hero-title">{esc(names.get(best, best))}</div>',
            f'<div class="hero-sub">{esc(best)}'
            + (f" · {esc(seg.get(best, ''))}" if seg.get(best) else "")
            + "</div>",
            '<div class="hero-facts">',
            f'<div><div class="fact-num">{n_agree} of {n_methods}</div><div class="fact-lab">group methods chose it</div></div>',
            f'<div><div class="fact-num">{table.loc[best, "avg_rank"]:.2f}</div><div class="fact-lab">average rank</div></div>',
            f'<div><div class="fact-num">{n_dm_agree} of {n_dm}</div><div class="fact-lab">DMs back it (by AHP)</div></div>',
            "</div></div>",
        )
    with col_votes:
        rows = []
        for k in cons["agree"] + cons["differ"]:
            ids = top_alts(result.group[k].ranks)
            yes = k in cons["agree"]
            rows.append(
                f'<div class="vote-row"><span class="vote-dot {"yes" if yes else "no"}"></span>'
                f'<span class="vote-name">{esc(group_label(k))}</span>'
                f'<span class="vote-pick {"yes" if yes else ""}">{esc(_pick_text(result, ids))}</span></div>'
            )
        render_html('<div class="vote-list"><div class="eyebrow" style="margin-bottom:0.3rem">Pick of each group method</div>', *rows, "</div>")

    if cons["differ"]:
        diff_txt = "; ".join(
            f"{group_label(k)} picks {_names(result, top_alts(result.group[k].ranks))}" for k in cons["differ"]
        )
        callout(
            "warn",
            f"{diff_txt}. Each method scores in its own way, so results can differ. "
            "See where this product stands in those methods on the Compare page.",
            f"{len(cons['differ'])} methods did not pick {names.get(best, best)}",
        )
    else:
        callout("ok", "Every group method produced the same winner.", "Full agreement")

    # ── Consensus ranking ─────────────────────────────────────────────────
    section("Consensus ranking", "ordered by the best average rank across all group methods")
    n_alt = len(result.alternatives)
    body = []
    for i, (a, row) in enumerate(table.iterrows(), start=1):
        strength = (n_alt + 1) - row["avg_rank"]
        body.append(
            f'<tr class="{"top" if i == 1 else ""}">'
            f'<td><span class="rank-badge {"first" if i == 1 else ""}">{i}</span></td>'
            f'<td><b>{esc(names.get(a, a))}</b><div class="sub">{esc(a)}'
            + (f" · {esc(seg.get(a, ''))}" if seg.get(a) else "")
            + "</div></td>"
            f'<td class="num">{row["avg_rank"]:.2f}</td>'
            f'<td style="width:22%">{bar_cell(strength, n_alt, "accent" if i == 1 else "")}</td>'
            f'<td class="num">{int(row["wins"])} of {n_methods}</td>'
            "</tr>"
        )
    render_html(
        '<table class="tbl"><thead><tr><th></th><th>Product</th><th class="num">Average rank</th>',
        '<th>Strength</th><th class="num">Winner in</th></tr></thead><tbody>',
        *body,
        "</tbody></table>",
    )

    # ── Things to look at ────────────────────────────────────────────
    section("Things to look at")
    notes = []
    second = table.index[1] if len(table) > 1 else None
    if second is not None:
        gap = table.loc[second, "avg_rank"] - table.loc[best, "avg_rank"]
        if gap < 0.5:
            notes.append(("warn", f"The average ranks of {names.get(best, best)} and {names.get(second, second)} differ by only {gap:.2f}. Both deserve discussion before deciding."))
    for cc in close_calls(result):
        if cc["top"]:
            notes.append((
                "warn",
                f"In {group_label(cc['model'])}, the scores of {names.get(cc['a'], cc['a'])} (rank 1) and {names.get(cc['b'], cc['b'])} (rank 2) "
                f"are almost level (gap {cc['gap']:.4f}). Their order can flip if the data shifts slightly.",
            ))
    for p in picks:
        if p["cr"] >= 0.1:
            notes.append(("bad", f"The assessment of {p['role']} ({p['dm_id']}) is not consistent enough (CR {p['cr']:.3f}, limit 0.10). It should be redone on the Team assessment page."))
    other_warn = [w for w in result.warnings if not w.startswith("Close call")]
    for w in other_warn:
        notes.append(("warn", w))
    if not notes:
        notes.append(("ok", "No warnings. The gaps between ranks are clear and every DM's assessment is consistent."))
    for kind, text in notes:
        callout(kind, text)

    # ── Each DM's vote ───────────────────────────────────────────────────────
    section("Each decision maker's vote", "how much each person's vote counts in the group decision")
    vmax = max([p["vote_weight"] for p in picks] + [0.01])
    body = []
    for p in picks:
        emph = ", ".join(f"{crit_names.get(c, c)} ({w * 100:.0f}%)" for c, w in p["top_criteria"])
        winner_txt = _names(result, p["winners"])
        agree = best in p["winners"]
        cr_chip = f'<span class="chip {"ok" if p["cr"] < 0.1 else "bad"}">CR {p["cr"]:.3f}</span>'
        body.append(
            "<tr>"
            f'<td><b>{esc(p["role"])}</b><div class="sub">{esc(p["dm_id"])}</div></td>'
            f'<td class="num">{p["vote_weight"] * 100:.1f}%</td>'
            f'<td style="width:14%">{bar_cell(p["vote_weight"], vmax)}</td>'
            f'<td>{esc(emph)}</td>'
            f'<td><span class="chip {"accent" if agree else ""}">{esc(winner_txt)}</span></td>'
            f"<td>{cr_chip}</td>"
            "</tr>"
        )
    render_html(
        '<table class="tbl"><thead><tr><th>Role</th><th class="num">Vote weight</th><th></th><th>Emphasises most</th>',
        '<th>Winner by AHP</th><th>Consistency</th></tr></thead><tbody>',
        *body,
        "</tbody></table>",
    )

    # ── Next steps ──────────────────────────────────────────────────────
    st.write("")
    c1, c2, c3, _ = st.columns([1.5, 1.5, 1.5, 2.5])
    c1.button("Compare all methods", on_click=go_to, args=("Compare",), key="sum_go_cmp", width="stretch")
    c2.button("See how it is calculated", on_click=go_to, args=("Results by method",), key="sum_go_method", width="stretch")
    c3.button("Ask the AI assistant", on_click=go_to, args=("AI assistant",), key="sum_go_ai", width="stretch")

    with st.expander("How to read this summary"):
        st.markdown(
            "**The recommendation** is the product with the best average rank across all group methods. "
            "On a tie, the product that wins in more methods goes first.\n\n"
            "**Methods used:**"
        )
        for key in METHOD_ORDER:
            m = METHODS[key]
            st.markdown(f"- **{m['label']}**: {m['plain']}")


def _empty(session: Session) -> None:
    render_html(
        '<div class="stat-row">',
        compact(
            '<div class="stat"><div class="stat-label">Step 1</div><div class="stat-value" style="font-size:1.25rem">Check the case data</div>',
            f'<div class="stat-hint">{len(session.alternatives)} products, {len(session.criteria)} criteria</div></div>',
        ),
        compact(
            '<div class="stat"><div class="stat-label">Step 2</div><div class="stat-value" style="font-size:1.25rem">Check the team assessment</div>',
            f'<div class="stat-hint">{len(session.dms)} decision makers</div></div>',
        ),
        compact(
            '<div class="stat"><div class="stat-label">Step 3</div><div class="stat-value" style="font-size:1.25rem">Run the analysis</div>',
            '<div class="stat-hint">The results appear on this page</div></div>',
        ),
        "</div>",
    )
    st.write("")
    c1, c2, c3, _ = st.columns([1.4, 1.4, 1.4, 3])
    c1.button("Run analysis", type="primary", on_click=run_analysis, key="sum_run", width="stretch")
    c2.button("View case data", on_click=go_to, args=("Case data",), key="sum_go_data", width="stretch")
    c3.button("Fill in the team assessment", on_click=go_to, args=("Team assessment",), key="sum_go_team", width="stretch")
