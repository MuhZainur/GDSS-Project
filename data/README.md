# Data

| File | Contents |
|---|---|
| `sample_case.json` | Full sample session: 7 alternatives, 7 criteria, values, 5 DMs, each DM's AHP matrix, the DM-vs-DM matrix, reference models. Format follows `docs/06_skema_data.md` section 1. |
| `sample_gpu_lengkap.json` | The sample data loaded by the UI (v0.3): the same case, but every DM assesses all 7 criteria and all DMs use AHP as the reference. `sample_case.json` above stays in use for the engine tests. |
| `alternatif_gpu.csv` | The decision matrix, to open in Excel. The second row holds the criterion types (benefit/cost). |
| `expected/golden_results.json` | The answer key for the tests (see `expected/README.md`). |

All data is fictional.
