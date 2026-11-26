# GDSS NusaCompute: a Group Decision Support System for a GPU company

**Live demo:** https://gdss-project-bmsy5ocs4ym7zwr8pqcijn.streamlit.app/

The demo runs on Streamlit Community Cloud. After a period without visitors it has to be woken up first, saved sessions
and reports are not permanent there, and an AI report usually takes 1 to 3 minutes.

A web app (Streamlit) for a *Group Decision Support System* (GDSS). The fictional GPU company **PT NusaCompute**
must choose **1 of 7 GPU product designs** to prioritise for production next year. The decision is made by
**5 decision makers (DMs)**: CEO, CTO, CMO, CFO and Head of Supply Chain. Every part of the case (products,
criteria, values, DMs) can be edited in the app, so it works for any group decision.

- **AHP** gives each DM's criteria weights, the DM-vs-DM vote weights, each DM's AHP ranking and the group AHP.
- **Per-DM models** that use the AHP weights: SAW, WP, TOPSIS, Profile Matching, Copeland (criteria).
- **Group aggregation models**: Borda (weighted and unweighted), Copeland (group), AHP (group, AIP).
- **AI assistant**: Gemini 4 Hydrogen (thinking low) or free OpenRouter models above 29B parameters write an analysis
  report and answer questions in a chat (with optional web search). The AI only explains; it never calculates.

## Run it
```bash
python -m pip install -r requirements.txt
python -m streamlit run app/main.py
```
or double-click `run.bat`. See `DEPLOY.md` for classroom, Streamlit Cloud and Docker options.

## Project layout
| Folder | Contents |
|---|---|
| `engine/` | Pure calculation functions that return scores, ranks and a step trace. Formulas follow `docs/models/`. |
| `app/` | The Streamlit interface: pages in `app/pages_/`, charts, theme, case editing, storage. |
| `llm/` | LLM client (engine chain with fallback), report generation, completeness guarantee, chat, web search. |
| `prompts/` | System prompts of the LLM (`analysis_system.md`, `chat_system.md`). |
| `data/` | Sample case (7 GPUs, 5 DMs) and the reference results used by the tests. |
| `docs/` | Design documents of the project (originally written in Indonesian). |
| `tests/` | pytest suite: golden numbers, case editing, LLM layer (no real API calls), interface (AppTest). |

## AI engines in short
1. The engine you select answers first. If it fails (quota, rate limit, outage), the next engine answers automatically
   and the report shows who answered and why.
2. Quota errors (HTTP 429) are never retried. Free quotas are small: Gemini 4 Hydrogen about 20 requests per day,
   OpenRouter free about 50 per day.
3. Every report always has all five sections. Missing parts are filled from the calculation results and marked as automatic.
4. Finished reports are saved with the run, so reopening one costs no request.

Details: `docs/07_integrasi_llm.md`.

## Notes
- The GPU data is **fictional but plausible**. Replace it freely; the calculation steps stay the same.
- The list of free OpenRouter models changes often. `python scripts/check_free_models.py` compares the current free list with the allowed one.
- Some numbers in the lecturer's slides contain typos; they are listed in `docs/09_pengujian.md`.
