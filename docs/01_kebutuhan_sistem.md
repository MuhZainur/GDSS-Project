# 01 · Kebutuhan Sistem

Kode: **F** = fungsional, **N** = nonfungsional. Prioritas: **W** = wajib, **S** = sebaiknya ada, **O** = opsional.

## A. Pengaturan sesi (fasilitator)
- [ ] F-A1 (W) Membuat sesi keputusan: judul, tujuan, tanggal.
- [ ] F-A2 (W) Memuat 7 alternatif dan 7 kriteria dari `data/sample_case.json`; bisa diedit (nama, nilai, jenis benefit/cost).
- [ ] F-A3 (W) Validasi: minimal 3 alternatif (kita pakai 7), minimal 3 kriteria per DM, nilai numerik > 0.
- [ ] F-A4 (W) Mendaftarkan DM (default 5: CEO, CTO, CMO, CFO, Kepala Rantai Pasok); bisa tambah/hapus (min 2, maks 10).
- [ ] F-A5 (W) Menentukan bobot kepentingan DM dengan **matriks AHP antar-DM** (dengan CR), atau pilihan "bobot sama rata".
- [ ] F-A6 (S) Mengunci alternatif setelah ada DM yang mengisi (alternatif harus sama untuk semua DM).

## B. Input tiap DM
- [ ] F-B1 (W) DM memilih identitasnya (dropdown), lalu mengisi formnya sendiri.
- [ ] F-B2 (W) DM memilih subset kriteria (minimal 3).
- [ ] F-B3 (W) DM mengisi perbandingan berpasangan kriteria dengan skala Saaty 1–9 (slider dua arah, misalnya "C1 ←9…1…9→ C4"). Hanya segitiga atas yang diisi; kebalikannya otomatis.
- [ ] F-B4 (W) CR tampil langsung saat mengisi. Jika CR ≥ 0.1: tampil peringatan + saran pasangan paling tidak konsisten (lihat `models/ahp.md` bagian "Saran perbaikan"). Penyimpanan tetap boleh, tetapi ditandai.
- [x] F-B5 (diubah di v0.3) Tidak ada lagi pilihan model per DM: peringkat AHP tiap DM yang dibawa ke penggabungan Borda dan Copeland kelompok.
- [ ] F-B6 (S) Status pengisian tiap DM terlihat oleh fasilitator (belum / sudah / CR bermasalah).

## C. Perhitungan
- [ ] F-C1 (W) Tombol **Hitung** aktif jika semua DM sudah mengisi dan bobot DM sudah ada.
- [ ] F-C2 (W) Untuk tiap DM dihitung **semua model individu** (AHP, SAW, TOPSIS, Copeland-kriteria), bukan hanya model pilihannya.
- [ ] F-C3 (W) Model kelompok: **Borda (berbobot dan tanpa bobot)**, **Copeland-kelompok**, **AHP-kelompok (AIP)**.
- [ ] F-C4 (W) Setiap model menyimpan jejak langkah (`steps`) untuk tab Perhitungan.
- [ ] F-C5 (W) Aturan peringkat seri: skor sama → peringkat sama (metode "min": 1, 2, 2, 4). Perbandingan memakai skor yang dibulatkan 10 desimal.
- [ ] F-C6 (S) Analisis kepekaan (*what-if*): ubah bobot DM / bobot kriteria dengan slider, lalu lihat apakah juara berubah, tanpa menyimpan run baru.

## D. Hasil dan tampilan
- [ ] F-D1 (W) Tab **Ranking**: tabel ranking tiap model (individu per DM dan kelompok) dan ringkasan juara per model.
- [ ] F-D2 (W) Tab **Visualisasi & Kontribusi**: grafik ranking, perbandingan antar-model, kontribusi kriteria (detail di `05_desain_ui.md`).
- [ ] F-D3 (W) Tab **Perhitungan**: dropdown pemilihan model (dan DM bila relevan); satu halaman hanya menampilkan satu model. Isi: langkah demi langkah dengan **tabel aritmatika lalu versi matriks**.
- [ ] F-D4 (W) Tab **Analisis LLM**: laporan analisis otomatis dari LLM.
- [ ] F-D5 (W) Tab **Chat**: terkunci sampai ada minimal 1 run.

## E. Penyimpanan dan ekspor
- [ ] F-E1 (W) Setiap run disimpan di `storage/runs/<run_id>/`: `input.json`, `results.json`, `rankings.csv`, `llm_payload.json`, `analysis.md`.
- [ ] F-E2 (W) Tombol unduh JSON dan CSV.
- [ ] F-E3 (W) Riwayat run: bisa membuka run lama.
- [ ] F-E4 (W) Setiap percakapan chat disimpan di `storage/chats/<run_id>/<session_id>.json`, terhubung ke run.
- [ ] F-E5 (S) Ekspor laporan PDF/Markdown (ranking + analisis LLM).

## F. LLM
- [ ] F-F1 (W) Analisis otomatis setelah run (atau tombol "Analisis dengan LLM").
- [ ] F-F2 (W) Isi analisis wajib (lihat `07_integrasi_llm.md`): ringkasan, perbandingan antar-model, kelebihan dan kelemahan tiap model **pada data ini**, rekomendasi alternatif X dari model Y beserta alasannya, risiko, dan catatan konsistensi (CR).
- [ ] F-F3 (W) Mode chat menyertakan konteks hasil run + riwayat percakapan.
- [ ] F-F4 (W) Pencarian internet di mode chat (bisa dinyalakan/dimatikan); sumber ditampilkan sebagai tautan.
- [ ] F-F5 (W) Cadangan model: jika model 1 gagal (429/5xx/timeout), coba model berikutnya. Model yang menjawab dicatat.
- [ ] F-F6 (S) Pemilih model di UI dari daftar `LLM_MODELS`.

## N. Nonfungsional
- [ ] N-1 (W) Perhitungan 7 alternatif × 5 DM selesai < 1 detik.
- [ ] N-2 (W) Angka ditampilkan 3–4 desimal; perhitungan memakai presisi penuh (float64). Catatan ±0.001 ditampilkan di tab Perhitungan.
- [ ] N-3 (W) Antarmuka Bahasa Indonesia; istilah teknis diberi penjelasan singkat (tooltip).
- [ ] N-4 (W) Kunci API hanya dari `.env`; tidak tampil di UI atau log.
- [ ] N-5 (W) Aplikasi tetap berjalan tanpa kunci API (fitur LLM dinonaktifkan dengan pesan jelas).
- [ ] N-6 (S) Bisa di-*deploy* gratis (mis. Streamlit Community Cloud / Hugging Face Spaces).
- [ ] N-7 (S) Warna grafik ramah buta warna; setiap warna disertai label.
