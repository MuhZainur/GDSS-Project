# 04 · Alur Pengguna

```
[1 Fasilitator: buat sesi] → [2 atur alternatif & kriteria] → [3 daftar DM]
      → [4 bobot antar-DM (AHP)] → [5 tiap DM isi formnya] → [6 Hitung]
      → [7 lihat Ranking / Visualisasi / Perhitungan] → [8 Analisis LLM] → [9 Chat]
```

## Rincian
| No | Siapa | Halaman | Yang terjadi | Validasi |
|---|---|---|---|---|
| 1 | Fasilitator | Pengaturan | Buat sesi baru atau muat contoh "NusaCompute" | judul wajib |
| 2 | Fasilitator | Pengaturan › Data | Edit tabel alternatif × kriteria; tandai benefit/cost | ≥3 alternatif, nilai > 0 |
| 3 | Fasilitator | Pengaturan › DM | Tambah/hapus DM, isi peran | 2–10 DM |
| 4 | Fasilitator | Pengaturan › Bobot DM | Slider berpasangan antar-DM atau "sama rata"; CR langsung terlihat | peringatan jika CR ≥ 0.1 |
| 5 | Tiap DM | Input DM | Pilih identitas → pilih kriteria → isi slider berpasangan → lihat bobot + CR → pilih model pilihan → Simpan | ≥3 kriteria |
| 6 | Fasilitator | (tombol di sidebar) | **Hitung**: aktif bila semua DM sudah simpan | tampilkan daftar DM yang belum mengisi |
| 7 | Semua | Ranking, Visualisasi, Perhitungan | Lihat hasil run terbaru atau pilih run lama | — |
| 8 | Semua | Analisis LLM | Analisis otomatis (atau tombol jika kunci API belum ada) | tanpa kunci → pesan jelas |
| 9 | Semua | Chat | Diskusi; konteks = run yang dipilih | terkunci sebelum ada run |

## Status sesi (ditampilkan di sidebar)
`Draf` → `Input DM berlangsung (3/5)` → `Siap dihitung` → `Sudah dihitung (run_id ...)`.
Mengubah data setelah dihitung membuat status kembali ke `Siap dihitung`; run lama tetap tersimpan.

## Mode demo
Tombol "Isi semua dengan data contoh" memuat `data/sample_case.json` (5 DM sudah terisi) supaya presentasi cepat.
