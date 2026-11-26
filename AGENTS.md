# Rules for the developer AI

You are working on the GDSS application described by the documents in this folder. Follow these rules.

## 1. Sources of truth
- Formulas and the order of steps: `docs/models/*.md`. **Do not change a formula** without the project owner's permission.
- Reference numbers: `data/expected/golden_results.json`. Every model implementation **must pass** the tests in
  `docs/09_pengujian.md` (tolerance ±0.0005 for 4-decimal scores).
- If documents conflict, the order of precedence is: `docs/models/` > `docs/06_skema_data.md` >
  `docs/05_desain_ui.md` > other documents. Record the conflict in `docs/KEPUTUSAN.md` (create it if missing).

## 2. Principles
1. **The calculation engine is separate from the interface.** Every model is a pure function in `engine/`
   (input → output + step trace). The UI only displays.
2. **Every model returns a step trace** (`steps`). The calculation views read this trace and never recalculate.
3. **The LLM must not calculate.** The LLM only reads the result JSON and explains it. Every number in an LLM answer
   must come from the result JSON.
4. **Interface language: English.** Internal JSON keys of the LLM report keep their original identifiers
   (`ringkasan`, `perbandingan`, `kelebihan_kelemahan`, `rekomendasi`, `risiko`, `konsistensi`); they are never shown to users.
5. **API keys must never enter the repo.** Use `.env` (see `.env.example`).
6. Work **stage by stage** following `docs/10_rencana_kerja.md`. Do not jump to the UI before the engine passes its tests.

## 3. Definition of done (per feature)
- There is an automated test (pytest) and it passes.
- It shows in the UI without errors with the sample data `data/sample_case.json`.
- It is recorded in `CHANGELOG.md`.

## 4. Forbidden
- Inventing real GPU data or presenting fictional data as real.
- Storing API keys in code, logs or result files.
- Letting the LLM state numbers that are not in the result JSON.
- Removing the step trace to "tidy up" the code.
