# 08 · Tumpukan Teknologi dan Struktur Kode

## Pilihan utama (disarankan): Python + Streamlit
Alasan: cepat dibuat, gratis di-*deploy*, perhitungan numerik dan grafik dalam satu bahasa, cocok untuk prototipe tugas kuliah
(sesuai pendekatan *prototyping* di materi "Membangun DSS").

| Bagian | Pustaka |
|---|---|
| UI | `streamlit` (≥ 1.40) |
| Hitung | `numpy`, `pandas`, `scipy` (rankdata, spearman, kendall) |
| Grafik | `plotly` |
| Pecahan | `fractions` (bawaan Python) |
| LLM | `openai` (klien kompatibel OpenRouter) atau `httpx` |
| Pencarian web | `ddgs`; opsional `tavily-python` |
| Konfigurasi | `python-dotenv`, `pydantic` (validasi skema) |
| Uji | `pytest` |

Alternatif bila dosen meminta web "sungguhan": FastAPI (backend, memakai `engine/` yang sama) + React/Next.js (frontend).
Karena `engine/` murni Python, perpindahan ini tidak mengubah logika hitung.

## Struktur folder kode
```
gdss-nusacompute/
├── app/
│   ├── main.py                 # entry Streamlit, tab, sidebar
│   ├── pages_/                 # satu file per tab: setup.py, dm_input.py, ranking.py, visual.py, steps.py, analysis.py, chat.py
│   ├── components/             # pairwise_slider.py, step_renderer.py, charts.py, matrix_latex.py
│   └── repository.py           # simpan/muat sesi, run, chat (JSON)
├── engine/
│   ├── fractions_util.py       # parse "1/3", format pecahan
│   ├── ahp.py                  # pairwise → bobot, λ, CI, CR, saran perbaikan, ranking AHP
│   ├── saw.py
│   ├── topsis.py
│   ├── copeland.py             # copeland_criteria(), copeland_group()
│   ├── borda.py                # borda_unweighted(), borda_weighted()
│   ├── ahp_group.py            # aip()
│   ├── ranking.py              # rank_min(), agreement(), winners(), close_calls()
│   ├── sensitivity.py          # what-if
│   ├── pipeline.py             # run_all(session) -> RunResult
│   └── schemas.py              # pydantic: Session, RunResult, Step
├── llm/
│   ├── client.py               # OpenRouter + cadangan model
│   ├── payload.py              # RunResult -> llm_payload.json
│   ├── analyze.py              # analisis otomatis + validasi angka
│   ├── chat.py                 # chat + penyimpanan
│   └── websearch.py            # ddgs / tavily / openrouter_online
├── prompts/                    # salin dari paket spesifikasi
├── data/sample_case.json
├── storage/                    # dibuat otomatis, masuk .gitignore
├── scripts/check_free_models.py
├── tests/
│   ├── test_ahp.py  test_saw.py  test_topsis.py  test_copeland.py  test_borda.py  test_ahp_group.py
│   ├── test_pipeline_golden.py # cocokkan dengan data/expected/golden_results.json
│   └── test_lecturer_examples.py
├── .env.example
├── requirements.txt
└── README.md
```

## Deploy gratis
- Streamlit Community Cloud atau Hugging Face Spaces (SDK Streamlit). Kunci API diisi di menu *secrets*.
- Catatan: penyimpanan file di layanan gratis bisa hilang saat aplikasi dimulai ulang. Untuk demo cukup; sediakan tombol unduh
  JSON/CSV, dan tombol "Muat run dari file" untuk mengunggah kembali.
