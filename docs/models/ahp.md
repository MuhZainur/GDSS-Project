# AHP (Analytic Hierarchy Process) — model wajib

Dipakai di tiga tempat: (1) bobot kriteria tiap DM, (2) bobot antar-DM, (3) ranking AHP per DM.
Urutan langkah mengikuti 8 langkah di materi dosen.

## Skala Saaty
| Nilai | Arti |
|---|---|
| 1 | Sama penting |
| 3 | Sedikit lebih penting |
| 5 | Lebih penting |
| 7 | Sangat lebih penting |
| 9 | Mutlak lebih penting |
| 2, 4, 6, 8 | Nilai tengah |
| 1/x | Kebalikan |

Aturan matriks: `a_ii = 1`, `a_ji = 1/a_ij`. UI hanya meminta n(n−1)/2 pasangan.

## Langkah 1–5: bobot dan konsistensi (untuk satu matriks A berukuran n×n)
| Langkah | Rumus | Jejak yang disimpan |
|---|---|---|
| 1. Matriks | A (pecahan ditampilkan sebagai pecahan dan desimal 3 angka) | tabel A |
| 1b. Jumlah kolom | `s_j = Σ_i a_ij` | tabel "1 + 0.5 + 0.333 + 2 = 3.833" per kolom |
| 2. Normalisasi | `n_ij = a_ij / s_j` | tabel per sel "a ÷ s = n" + matriks Norm_A |
| 3. Bobot (vektor eigen pendekatan) | `x_i = (Σ_j n_ij) / n` | tabel per baris: penjumlahan, ÷ n, hasil |
| 4a. A·x | `(Ax)_i = Σ_j a_ij x_j` | tabel per baris: "1×0.299 + 2×0.348 + … = 1.370" |
| 4b. λmaks | `λ = (1/n) Σ_i (Ax)_i / x_i` | tabel per baris rasio + jumlah + rata-rata |
| 5. Konsistensi | `CI = (λ − n)/(n − 1)`, `CR = CI / RI(n)` | tabel 5 langkah + tabel RI |

**Tabel RI (Saaty):** n=1: 0, 2: 0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, **7: 1.32**, 8: 1.41, 9: 1.45, 10: 1.49.
Untuk n ≤ 2, CR = 0 (selalu konsisten).
**Aturan:** CR < 0.1 = konsisten. CR ≥ 0.1 = tampilkan peringatan.

Versi matriks yang ditampilkan (seperti PPT dosen):
`A → Norm_A → X` dan `A · x = λmaks · x`.

### Saran perbaikan saat CR ≥ 0.1
Untuk tiap sel i<j hitung `e_ij = a_ij · x_j / x_i` (idealnya 1). Tampilkan 3 pasangan dengan `|ln e_ij|` terbesar beserta
nilai yang disarankan `x_i / x_j` dibulatkan ke skala Saaty terdekat. Ini hanya saran; DM yang memutuskan.

## Langkah 6: sub-kriteria
Tidak dipakai di kasus ini (dilewati, tetapi tampilkan sebagai langkah "dilewati" agar sesuai alur dosen).

## Langkah 7: bobot alternatif per kriteria
Semua kriteria kasus ini kuantitatif, jadi bobot alternatif dihitung langsung dari data (sama seperti Latihan 1 dosen):
- **benefit:** `p_kj = v_kj / Σ_k v_kj`
- **cost:** `p_kj = (1/v_kj) / Σ_k (1/v_kj)` (pakai kebalikan dulu supaya yang murah dapat bobot besar)

Opsional (S): kriteria kualitatif dengan matriks berpasangan antar-alternatif 7×7 (21 pasangan); bobot = langkah 1–3,
dan CR dicek (RI n=7 = 1.32).

## Langkah 8: ranking akhir AHP
`skor_k = Σ_j w_j · p_kj` (matriks prioritas × vektor bobot kriteria). Tampilkan juga versi matriks:
`[P] × [w] = [skor]`.

## Contoh acuan (DM1 CEO)
Bobot (C1, C4, C5, C6) = (0.1611, 0.2771, 0.4658, 0.0960), λmaks = 4.0310, CR = 0.0115.
Skor AHP A1…A7 = (0.1267, 0.1541, 0.1238, 0.1165, 0.1466, 0.2013, 0.1310) → juara A6.

Contoh dari latihan kelas (untuk uji tambahan), matriks kriteria Latihan 1 motor:
`[[1,2,3,1/2],[1/2,1,4,3],[1/3,1/4,1,1/3],[2,1/3,3,1]]` → bobot (0.299, 0.348, 0.079, 0.274), λ = 4.566, CI = 0.189, CR = 0.210 (tidak konsisten).
