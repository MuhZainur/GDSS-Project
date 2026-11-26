# Changelog

## 0.5.0 — 2026-11-19 (English interface, engine fallback, saved reports)
- **Everything is English now:** interface text, calculation step titles and explanations, warnings, LLM prompts and
  output, fallback text, sample data, scripts and documentation. Page names: Summary, Case data, Team assessment,
  Results by method, Compare, AI assistant. The app is now called "Decision Room". Page modules were renamed
  (`app/pages_/summary.py`, `case_data.py`, `assessment.py`, `methods.py`, `compare.py`, `assistant.py`).
  The internal JSON keys of the LLM report (`ringkasan`, `perbandingan`, ...) stay as identifiers and are never shown.
- **OpenRouter list is now 4 models:** Nemotron 3 Ultra 550B, Dots3-Note 280B, Nemotron 3.5 Super VL 120B and
  ERNIE 5.5 Flash 280B. Gemma 4 31B (429 from a shared upstream pool) and Inkling 2 Small (403, only for agentic harnesses) were removed.
- **No retry on 429/403/401/404** for any engine: a quota or rate-limit error now gives a clear message at once
  (including the reset time when the API states it) instead of waiting and retrying. 5xx and connection errors get one retry.
- **Automatic fallback between engines:** the selected engine first, then the others (Gemini then the OpenRouter list, or the
  chosen OpenRouter model, the other OpenRouter models, then Gemini). Engines without a key are skipped. The report and the chat say
  who answered and why the earlier engines failed.
- **No LLM repair call anymore.** The free quotas are tiny, so a report now costs one request. Weak or missing sections are
  filled from the calculation results (flagged as automatic), so all five tabs are always filled.
- **Reports are saved per run and engine** (`storage/runs/<run_id>/analysis_<engine>.json`) and reopened without a request.

## 0.4.0 — 2026-11-19 (uniform AI models and reports)
- **Gemini:** all older models removed; only `gemini-4-hydrogen` with thinking level `low`
  (`generationConfig.thinkingConfig.thinkingLevel`). The API key is sent in a header, not in the URL. Room for thinking tokens
  is added to `maxOutputTokens`, and an empty answer counts as a failure.
- **OpenRouter:** only free models above 29B parameters (at least 10B active); `OPENROUTER_MODELS` in `.env` can only narrow or
  reorder the list. The `reasoning` text is no longer used as an answer.
- **Uniform AI report for any model** (`llm/completeness.py`): shape normalisation, per-section assessment, and fallback text built
  from the calculation results. All five tabs (Summary, Across methods, Strengths and weaknesses, Risks and consistency, Full document)
  are always filled, and the UI says which parts were filled automatically.
- The analysis and chat prompts no longer contain a company, product or job title example, and the default company name was removed from the payload.
- `scripts/check_free_models.py` compares the current OpenRouter free models with the allowed list.

## 0.3.0 — 2026-11-19 (editable case)
- **The case data is fully editable:** product name, segment and description; criterion name, unit and type (Benefit/Cost dropdown);
  the value of every product (an editable table that accepts pasting from Excel); DM title and name.
  Products, criteria and DMs can be added or removed (limits: products 3-12, criteria 3-10, DMs 2-10). Logic in `app/case_edit.py`.
- **Every DM assesses every criterion.** The per-DM criteria subset was removed; old judgements are kept per pair
  when criteria are added or removed.
- **The per-DM reference method was removed.** Each DM's AHP ranking is what Borda and group Copeland use; every other method
  is still calculated for all DMs as before. The engine is unchanged (the schema default `chosen_method` = AHP).
- **DM vote weights can be set in the UI:** equal, or assessed with AHP (DM-vs-DM comparison), with an explanation of how
  they differ from criteria weights.
- Data checks before the analysis (empty or duplicate names, Cost value 0, negative values, minimum counts) and a
  "Start an empty case" button in the sidebar.
- New UI sample data `data/sample_gpu_lengkap.json` (every DM assesses 7 criteria). The old `data/sample_case.json` stays in use for the
  engine tests; old sessions with a criteria subset are adjusted automatically when loaded.

## 0.2.0 — 2026-11-19 (interface redesign, engine unchanged)
- The interface was replaced by "Decision Room": 6 task-oriented pages (Summary, Case data, Team assessment,
  Results by method, Compare, AI assistant) instead of 12 per-method tabs. New theme, CSS, charts and components (`app/theme.py`).
- Summary for business teams: recommendation, agreement map between methods, things to look at, each DM's vote.
- Vote-weight scenario test (using the existing `engine.sensitivity.simulate_what_if`).
- Results are marked stale when the data or assessment changes after the analysis.
- Fixes: uploading a session can no longer cause endless reruns; comparison sliders are keyed per criterion (not per index) and
  old judgements are kept when criteria change; the agreement heatmap reads the "A|B" format correctly (it used to show 1.0 everywhere);
  the WP "S vector" column is filled (it used to be 0); reset clears the widget state; API keys are no longer written to `os.environ`.
- Removed: the "Feasibility Gate" (it had no basis in the data schema and always said "Pass") and the unused old page modules.
- Deployment: `requirements.txt` pinned to Streamlit 1.52.1, `run.bat`, `Dockerfile`, `DEPLOY.md`.

## 0.0.1 — 2026-11-18
- Initial specification package: requirements, case study, models, architecture, UI, data schema, LLM integration, testing, work plan.
