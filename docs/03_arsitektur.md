# 03 · Arsitektur

Mengikuti arsitektur GDSS level 2 di materi dosen: **DGMS (dialog) ↔ MBMS (basis model) ↔ DBMS (basis data)**.

```
┌───────────────────────── Pengguna: Fasilitator + DM1..DM5 ─────────────────────────┐
│                                                                                     │
│  DGMS · Antarmuka (Streamlit)                                                       │
│  Pengaturan │ Input DM │ Ranking │ Visualisasi │ Perhitungan │ Analisis LLM │ Chat  │
└───────┬──────────────────────────────┬──────────────────────────────┬──────────────┘
        │                              │                              │
┌───────▼────────┐   ┌─────────────────▼──────────────┐   ┌───────────▼─────────────┐
│ DBMS           │   │ MBMS · engine/                 │   │ Layanan LLM · llm/      │
│ storage/       │◄──┤ ahp, saw, topsis, copeland,    │   │ OpenRouter client       │
│  sessions/     │   │ borda, ahp_group, ranking,     │──►│ + cadangan model        │
│  runs/<id>/    │   │ sensitivity                    │   │ + pencarian web (ddgs)  │
│  chats/<id>/   │   │ (fungsi murni + jejak langkah) │   │ + penyimpan percakapan  │
└────────────────┘   └────────────────────────────────┘   └─────────────────────────┘
```

## Komponen
| Komponen | Tugas | Catatan |
|---|---|---|
| `engine/` (MBMS) | Semua hitungan model | Tanpa Streamlit, tanpa I/O. Bisa diuji dengan pytest. |
| `storage/` + `app/repository.py` (DBMS) | Simpan/muat sesi, input DM, run, chat | File JSON/CSV. Boleh ganti SQLite nanti. |
| `app/` (DGMS) | Halaman dan komponen UI | Membaca hasil dari `engine`, tidak menghitung sendiri |
| `llm/` | Membangun payload, memanggil OpenRouter, pencarian web, menyimpan chat | Lihat `07_integrasi_llm.md` |

## Alur data satu run
1. Fasilitator menekan **Hitung** → `repository.load_session()` → `engine.run_all(session)`.
2. `run_all` menghasilkan objek `RunResult` (skema di `06_skema_data.md`).
3. `repository.save_run()` menulis `input.json`, `results.json`, `rankings.csv`, `llm_payload.json`.
4. UI menampilkan tab hasil dari `results.json`.
5. `llm.analyze(llm_payload)` → `analysis.md` + `analysis.json`.
6. Chat aktif; setiap pesan disimpan ke `storage/chats/<run_id>/<session_id>.json`.

## Kenapa file JSON, bukan database server
Cocok untuk prototipe tugas kuliah (gratis, mudah diperiksa dosen, mudah dikirim ke LLM). Antarmuka repository
dibuat abstrak (`save_run`, `load_run`, `list_runs`, `save_chat`, `load_chat`) supaya bisa diganti SQLite tanpa mengubah UI.
