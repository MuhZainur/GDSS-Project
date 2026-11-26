# Prompt Siap Tempel untuk AI Pengembang

Tempel satu per satu sesuai tahap. Selalu lampirkan/arahkan AI ke seluruh folder spesifikasi ini.

---
## Prompt awal (sekali, sebelum Tahap 1)
```
Kamu akan membangun aplikasi GDSS berdasarkan spesifikasi di folder ini. Baca dulu AGENTS.md, README.md,
lalu semua file di docs/ dan docs/models/. Jangan menulis kode dulu. Balas dengan:
1) ringkasan pemahamanmu dalam 10 poin,
2) daftar pertanyaan bila ada yang ambigu,
3) rencana file yang akan kamu buat di Tahap 1.
```

## Tahap 1 — Kerangka dan skema
```
Kerjakan Tahap 1 di docs/10_rencana_kerja.md: buat struktur folder sesuai docs/08_tumpukan_teknologi.md,
requirements.txt, engine/schemas.py (pydantic untuk Session, Step, RunResult sesuai docs/06_skema_data.md),
engine/fractions_util.py (parse "1/3" -> Fraction, format), dan fungsi memuat data/sample_case.json.
Tulis tests untuk parse pecahan dan validasi sample_case.json. Jalankan pytest dan tunjukkan hasilnya.
```

## Tahap 2 — AHP
```
Kerjakan Tahap 2: engine/ahp.py sesuai docs/models/ahp.md, termasuk jejak langkah (steps) dengan tabel aritmatika
per sel dan LaTeX versi matriks, tabel RI, saran perbaikan saat CR >= 0.1, dan ranking AHP (langkah 7–8).
Uji wajib: L-1, L-2, G-1, G-3 di docs/09_pengujian.md. Tunjukkan output pytest.
```

## Tahap 3 — Model individu
```
Kerjakan Tahap 3: engine/saw.py, engine/topsis.py, dan copeland_criteria() di engine/copeland.py sesuai docs/models/.
Semua memakai bobot dari AHP, mengembalikan scores, ranks (metode min), steps, dan extra (kontribusi, D+/D-, contests).
Uji wajib: G-2, G-8, G-9, L-4. Tunjukkan output pytest.
```

## Tahap 4 — Model kelompok dan pipeline
```
Kerjakan Tahap 4: engine/borda.py (tanpa bobot dan berbobot, tampilkan juga kesetaraan dengan versi "Σ bobot × ranking,
terkecil terbaik"), copeland_group(), engine/ahp_group.py (AIP), engine/ranking.py (rank_min, winners, agreement
Spearman/Kendall, close_calls), dan engine/pipeline.py run_all(session) -> RunResult.
Uji wajib: G-4..G-7, L-3, dan tests/test_pipeline_golden.py yang membandingkan seluruh hasil dengan
data/expected/golden_results.json (toleransi 5e-4).
```

## Tahap 5 — Penyimpanan
```
Kerjakan Tahap 5: app/repository.py (save/load/list session, run, chat) dengan struktur storage/ di docs/03_arsitektur.md,
ekspor results.json, rankings.csv (format panjang), dan llm_payload.json (docs/06_skema_data.md bagian 5).
Uji: CSV data contoh berisi 168 baris data.
```

## Tahap 6 — UI dasar
```
Kerjakan Tahap 6: app/main.py dengan sidebar dan 7 tab sesuai docs/05_desain_ui.md. Isi tab Pengaturan, Input DM
(slider berpasangan dua arah, CR langsung, saran perbaikan, pilih model pilihan), dan Ranking. Tab lain tampil
placeholder. Chat terkunci sampai ada run. Tambahkan tombol "Isi semua dengan data contoh".
```

## Tahap 7 — Visualisasi dan Perhitungan
```
Kerjakan Tahap 7: tab Visualisasi & Kontribusi (semua grafik di tabel docs/05_desain_ui.md, plotly, warna tetap per alternatif)
dan tab Perhitungan (dropdown model, dropdown DM untuk model individu, dropdown pasangan untuk Copeland; satu halaman
satu model; tiap langkah: penjelasan → tabel aritmatika → versi matriks LaTeX → kotak hasil). Renderer membaca steps,
tidak menghitung ulang.
```

## Tahap 8 — LLM analisis
```
Kerjakan Tahap 8 sesuai docs/07_integrasi_llm.md: llm/client.py (OpenRouter, parameter models untuk cadangan,
retry 3x, catat model_used), llm/payload.py, llm/analyze.py (prompt di prompts/analisis_sistem.md, keluaran JSON,
fallback markdown, validasi angka yang menandai angka tidak ditemukan), scripts/check_free_models.py, dan tab Analisis LLM.
Aplikasi harus tetap jalan tanpa API key.
```

## Tahap 9 — Chat dan pencarian web
```
Kerjakan Tahap 9: llm/websearch.py (ddgs default, tavily opsional, openrouter_online opsional), llm/chat.py
(konteks run + ringkasan analisis + 12 pesan terakhir + ringkasan pesan lama + hasil web bernomor), penyimpanan
chat per run di storage/chats/<run_id>/<chat_id>.json, dan tab Chat dengan saklar "Cari di internet",
daftar sumber, dan chip saran pertanyaan.
```

## Tahap 10 — Rapikan
```
Kerjakan Tahap 10: fitur what-if (slider bobot DM -> ranking Borda/Copeland/AIP berubah langsung), README pengguna
(cara instal, isi .env, jalankan, deploy ke Streamlit Community Cloud), dan jalankan seluruh daftar uji manual di
docs/09_pengujian.md bagian D. Laporkan mana yang lolos dan mana yang belum.
```
