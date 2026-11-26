# 05 · Desain Antarmuka

## Tata letak
- **Sidebar:** pilih sesi, status sesi, pilih peran (Fasilitator / DM1…DMn), tombol **Hitung**, pilih run (riwayat).
- **Area utama: tab** (urutan tetap):
  1. `Pengaturan` (fasilitator)
  2. `Input DM`
  3. `Ranking`
  4. `Visualisasi & Kontribusi`
  5. `Perhitungan`
  6. `Analisis LLM`
  7. `Chat` 🔒 (terkunci sampai ada run)

Tab 3–7 menampilkan pesan "Belum ada perhitungan. Tekan Hitung di sidebar." jika belum ada run.

## Tab 2 · Input DM
- Pilih kriteria (multiselect, min 3).
- Slider berpasangan per pasangan: kiri = kriteria i lebih penting (9…2), tengah = 1, kanan = kriteria j lebih penting (2…9).
  Tulis artinya di bawah slider ("C5 sedikit lebih penting daripada C1, nilai 3").
- Panel kanan langsung memperbarui: matriks, bobot (diagram batang), λmaks, CI, CR (hijau < 0.1, merah ≥ 0.1) + saran perbaikan.
- Pilih model pilihan (radio): AHP / SAW / TOPSIS / Copeland-kriteria, dengan tooltip satu kalimat tiap model.

## Tab 3 · Ranking
1. **Kartu ringkasan:** juara tiap model kelompok (Borda berbobot, Borda tanpa bobot, Copeland-kelompok, AHP-kelompok) + tanda "sepakat / berbeda".
2. **Tabel ranking kelompok:** baris = alternatif, kolom = model kelompok, isi = peringkat (skor dalam tanda kurung).
3. **Tabel ranking individu:** pilih DM (dropdown) → tabel alternatif × {AHP, SAW, TOPSIS, Copeland-kriteria}; kolom model pilihan DM diberi tanda ★.
4. **Matriks juara:** DM × model individu, isi = juara.
5. Tombol unduh: `results.json`, `rankings.csv`.

## Tab 4 · Visualisasi & Kontribusi
| Grafik | Isi | Kegunaan |
|---|---|---|
| Batang horizontal per model | skor alternatif, juara disorot | melihat jarak antar-alternatif |
| Peta panas peringkat | alternatif × semua model (individu + kelompok), angka peringkat di sel | melihat model mana yang berbeda |
| *Bump chart* | garis peringkat tiap alternatif melintasi model | melihat perpindahan peringkat |
| Batang bertumpuk kontribusi (AHP/SAW per DM) | `w_j × nilai normalisasi` per kriteria | kriteria apa yang membuat alternatif menang |
| Batang bertumpuk kontribusi DM (Borda berbobot) | `v_i × (m − r_ik)` per DM | DM mana yang mendorong alternatif |
| Diagram TOPSIS | D+ vs D− (sebar) per DM | dekat ideal vs jauh dari terburuk |
| Matriks pertandingan Copeland | 7×7, hijau = baris menang, merah = kalah, abu = seri | siapa mengalahkan siapa |
| Bobot | batang bobot kriteria tiap DM dan bobot DM | membandingkan sudut pandang DM |
| Kesepakatan antar-model | tabel korelasi Spearman / Kendall tau antar-model | seberapa mirip urutan antar-model |
| *What-if* (S) | slider bobot DM → grafik ranking Borda/Copeland langsung berubah | analisis kepekaan |

Aturan grafik: satu sumbu Y saja; warna kategori tetap per alternatif di semua grafik (A1 selalu warna yang sama);
setiap grafik punya legenda dan tooltip; sediakan tampilan tabel untuk setiap grafik.

## Tab 5 · Perhitungan (langkah demi langkah)
- **Dropdown 1: model** → `AHP bobot kriteria`, `AHP ranking`, `SAW`, `TOPSIS`, `Copeland-kriteria`, `AHP bobot DM`,
  `Borda (tanpa bobot)`, `Borda (berbobot)`, `Copeland-kelompok`, `AHP-kelompok (AIP)`.
- **Dropdown 2: DM** → hanya muncul untuk model individu.
- **Dropdown 3: pasangan** → hanya untuk Copeland (memilih pertandingan yang ditampilkan; tabel ringkasan semua pertandingan tetap ada).
- **Satu halaman = satu model.** Tidak menampilkan model lain.
- Tiap langkah dirender dari `steps` dengan pola tetap:
  1. Judul langkah ("Langkah 2. Normalisasi").
  2. Penjelasan 1–2 kalimat dalam bahasa awam.
  3. **Tabel aritmatika**: setiap sel ditulis lengkap, mis. `0.5 ÷ 3.833 = 0.130`; penjumlahan ditulis `1 + 0.5 + 0.333 + 2 = 3.833`.
  4. **Versi matriks** (LaTeX `bmatrix`), mis. `A → Norm_A → X` dan `A·x = λmaks·x`.
  5. Kotak hasil (mis. "CR = 0.0115 < 0.1 → konsisten").
- Navigasi langkah: daftar langkah di atas (bisa diklik) atau tombol Sebelumnya/Berikutnya (pilih salah satu, konsisten).
- Catatan kaki tetap: "Angka ditampilkan 4 desimal; perhitungan memakai presisi penuh, selisih ±0.001 saat dihitung manual itu wajar."

## Tab 6 · Analisis LLM
- Tombol **Analisis** (atau otomatis setelah run, bisa diatur).
- Tampilkan: nama model LLM yang benar-benar menjawab, waktu, run_id.
- Bagian laporan (judul tetap): Ringkasan · Perbandingan antar-model · Kelebihan & kelemahan tiap model pada data ini ·
  Rekomendasi akhir · Risiko & catatan · Konsistensi penilaian.
- Tombol unduh `analysis.md`. Tombol "Buat ulang" (menyimpan versi baru, versi lama tidak dihapus).

## Tab 7 · Chat
- Terkunci (ikon gembok + penjelasan) sampai ada run.
- Pilih run sebagai konteks (default run terbaru) dan pilih/buat sesi chat.
- Saklar **"Cari di internet"**. Jika menyala, tampilkan daftar sumber (judul + tautan) di bawah jawaban.
- Riwayat chat tersimpan otomatis dan bisa dibuka kembali.
- Saran pertanyaan awal (chip): "Kenapa Borda tanpa bobot memilih A2?", "Apa risiko memilih A6?",
  "Bagaimana tren permintaan GPU pusat data saat ini?"
