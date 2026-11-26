# 09 · Pengujian

Semua uji model ditulis dengan `pytest`. Toleransi: `abs(hasil − acuan) ≤ 5e−4` untuk angka 4 desimal.

## A. Uji kasus NusaCompute (kunci jawaban)
Sumber: `data/expected/golden_results.json` (dihitung dengan numpy, presisi penuh, dibulatkan 4 desimal).
Masukan: `data/sample_case.json`.

| Uji | Yang dicek |
|---|---|
| G-1 | Bobot kriteria, λmaks, CR tiap DM |
| G-2 | Skor dan ranking AHP, SAW, TOPSIS, Copeland-kriteria tiap DM |
| G-3 | Bobot DM: (0.4017, 0.2442, 0.1373, 0.1373, 0.0794), λ = 5.0331, CR = 0.0074 |
| G-4 | Borda tanpa bobot: poin (20, 21, 11, 7, 12, 17, 17), ranking (2, 1, 6, 7, 5, 3, 3) |
| G-5 | Borda berbobot: (3.0347, 3.9163, 2.0287, 1.1661, 3.1820, 4.5622, 3.1099) |
| G-6 | Copeland-kelompok: poin (−2, 4, −4, −6, 2, 6, 0) |
| G-7 | AHP-kelompok AIP: (0.1494, 0.1494, 0.1237, 0.1092, 0.1362, 0.1904, 0.1418), ranking (2, 3, 6, 7, 5, 1, 4) |
| G-8 | DM5 TOPSIS: A1 = 1.0000, A6 = 0.0000 (batas) |
| G-9 | DM2 Copeland-kriteria menghasilkan seri peringkat 4 untuk A1, A3, A4 |

Ringkasan nilai individu (skor A1…A7):

| DM | AHP | SAW | TOPSIS | Copeland (poin) |
|---|---|---|---|---|
| DM1 | .1267 .1541 .1238 .1165 .1466 .2013 .1310 | .4923 .5539 .4697 .4776 .5644 .6795 .4888 | .3458 .4741 .2979 .3070 .4130 .5298 .3935 | −2 −4 2 0 4 6 −6 |
| DM2 | .0897 .0782 .1047 .0984 .1816 .3560 .0913 | .3537 .2831 .3183 .3101 .4869 .8326 .3299 | .1483 .1301 .1842 .1606 .4024 .8576 .1522 | −2 −4 −2 −2 4 6 0 |
| DM3 | .2264 .2237 .1122 .0661 .0683 .1086 .1948 | .6498 .6730 .3309 .1955 .1823 .2369 .5719 | .6011 .7326 .5207 .4246 .3355 .2749 .6571 | 2 6 0 −2 −4 −6 4 |
| DM4 | .1929 .1775 .1204 .1142 .1132 .1143 .1675 | .6498 .6122 .4699 .4811 .4995 .5162 .5808 | .5507 .6115 .5096 .4936 .4623 .3858 .5742 | 6 2 −2 0 −4 −6 4 |
| DM5 | .2573 .1706 .1255 .1183 .0872 .0661 .1750 | 1.000 .6974 .5320 .5074 .3843 .2929 .6960 | 1.000 .8557 .7172 .6978 .4288 .0000 .8367 | 6 4 0 −2 −4 −6 2 |

Bobot kriteria: DM1 (C1 .1611, C4 .2771, C5 .4658, C6 .0960) · DM2 (C1 .4658, C2 .2771, C6 .0960, C7 .1611) ·
DM3 (C1 .1653, C3 .2550, C4 .4715, C6 .1083) · DM4 (C3 .1611, C4 .2771, C5 .4658, C7 .0960) · DM5 (C3 .1638, C6 .2973, C7 .5390).
CR: DM1 .0115, DM2 .0115, DM3 .0170, DM4 .0115, DM5 .0079.

## B. Uji contoh dari slide dosen
| Uji | Masukan | Harus keluar |
|---|---|---|
| L-1 AHP (Latihan 1, matriks kriteria motor) | `[[1,2,3,1/2],[1/2,1,4,3],[1/3,1/4,1,1/3],[2,1/3,3,1]]` | w = (0.299, 0.348, 0.079, 0.274), λ = 4.566, CI = 0.189, CR = 0.210 |
| L-2 AHP (Latihan 2, kriteria asisten) | `[[1,2,1/2,3],[1/2,1,1/3,2],[2,3,1,4],[1/3,1/2,1/4,1]]` | w = (0.277, 0.161, 0.466, 0.096) |
| L-3 Borda (7 DM, 3 kandidat) | A=(2,3,3,2,2,3,2), B=(1,2,1,1,3,1,1), C=(3,1,2,3,1,2,3) | poin 4, 11, 6; total 21; bobot 0.19, 0.52, 0.29 |
| L-4 Copeland-kriteria (5 pegawai, 7 kriteria) | data Ahmad…Anwar, bobot 23/20/18/15/11/8/5 | poin −2, 0, 2, −4, 4; ranking 4, 3, 2, 5, 1 |

Data L-4 (kolom C1…C7, semua benefit):
```
Ahmad (A1) 113.67 91.25 91.58 94.65 92.25 91.33 91.98
Ihsan (A2) 107.14 93.13 92.85 96.15 92.80 93.73 94.69
Akbar (A3) 106.02 94.98 94.87 95.90 94.65 94.45 94.65
Asrul (A4) 108.75 94.55 91.22 92.45 91.55 93.63 92.16
Anwar (A5) 110.15 96.48 92.55 94.10 95.39 93.82 94.10
```

### Salah ketik di slide dosen (jangan disalin)
| Slide | Tertulis | Seharusnya |
|---|---|---|
| Borda | "4 + 11 + 5 = 20" | 4 + 11 + 6 = 21 (tabel dan bobot memakai 21, sudah benar) |
| Copeland, urutan C2 | A5, A3, A2, A2, A1 | A5, A3, **A4**, A2, A1 |
| Copeland, urutan C4 | A2, A3, A1, A4, A5 | A2, A3, A1, **A5, A4** |
| Copeland, tabel pertandingan A1 vs A2 | judul kolom "Bobot A1" dua kali | kolom kedua "Bobot A2" |
Hasil akhir Copeland di slide **sudah benar**.

## C. Uji unit lain
- Matriks berpasangan: diagonal 1, kebalikan otomatis, tolak nilai di luar 1/9…9.
- n = 2: CR = 0 tanpa pembagian nol.
- Peringkat seri: skor (0.5, 0.5, 0.3) → ranking (1, 1, 3).
- TOPSIS semua alternatif identik → V = 0.5 semua + peringatan.
- AIP dengan skor 0 → diganti 1e−12 + peringatan.
- Copeland dengan nilai sama di satu kriteria → bobot kriteria itu tidak diberikan ke siapa pun.

## D. Uji integrasi dan UI (manual, daftar centang)
- [ ] Muat data contoh → Hitung → semua tab tampil tanpa error.
- [ ] Ubah satu slider DM1 → CR berubah langsung.
- [ ] Tab Chat terkunci sebelum Hitung, terbuka sesudahnya.
- [ ] Tab Perhitungan: ganti dropdown model → hanya model itu yang tampil.
- [ ] Unduh JSON/CSV → bisa dibuka; CSV punya 7 × (5 DM × 4 model + 4 model kelompok) = 168 baris data.
- [ ] Tanpa `OPENROUTER_API_KEY` → tab LLM menampilkan pesan, aplikasi tidak error.
- [ ] Model pertama dibuat gagal (ID palsu) → cadangan menjawab dan `model_used` tercatat.
- [ ] Analisis LLM: tidak ada ikon ⚠ angka karangan pada data contoh (jika ada, perbaiki prompt).
- [ ] Chat dengan pencarian web → daftar sumber muncul; tutup aplikasi, buka lagi → riwayat chat masih ada.
