# 10 · Rencana Kerja (bertahap, gaya prototyping)

Setiap tahap diakhiri demo kecil + uji lolos. Prompt siap tempel ada di `prompts/prompt_untuk_ai_pengembang.md`.

| Tahap | Hasil | Uji wajib lolos | Perkiraan |
|---|---|---|---|
| 1. Kerangka + skema | Struktur folder, `schemas.py`, `fractions_util.py`, muat `sample_case.json` | parse pecahan, validasi skema | 0.5 hari |
| 2. Mesin AHP | `ahp.py` lengkap + jejak langkah + saran perbaikan | L-1, L-2, G-1, G-3 | 1 hari |
| 3. Model individu | `saw.py`, `topsis.py`, `copeland.py` (kriteria) | G-2, G-8, G-9, L-4 | 1 hari |
| 4. Model kelompok | `borda.py`, `copeland.py` (kelompok), `ahp_group.py`, `ranking.py`, `pipeline.py` | G-4…G-7, L-3, `test_pipeline_golden.py` | 1 hari |
| 5. Penyimpanan | `repository.py`, ekspor JSON/CSV, riwayat run | CSV 168 baris | 0.5 hari |
| 6. UI dasar | Tab Pengaturan, Input DM, Ranking | uji manual D-1, D-2 | 1–1.5 hari |
| 7. UI hasil | Tab Visualisasi & Kontribusi, Perhitungan (dropdown, tabel → matriks) | uji manual D-4 | 1.5 hari |
| 8. LLM analisis | `llm/client.py`, `payload.py`, `analyze.py`, tab Analisis | D-6, D-7, D-8 | 1 hari |
| 9. Chat + web | `chat.py`, `websearch.py`, tab Chat, penyimpanan chat | D-3, D-9 | 1 hari |
| 10. Rapikan | *what-if*, README pengguna, deploy, rekam demo | semua | 1 hari |

Total kira-kira 9–10 hari kerja santai. Kalau waktunya mepet, urutan yang boleh dipangkas: *what-if* (F-C6),
ekspor PDF (F-E5), opsi AIJ, kriteria kualitatif 7×7.
