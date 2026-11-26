# TOPSIS — model individu

Bobot kriteria **diambil dari AHP** milik DM tersebut.
Ide: pilih alternatif yang **paling dekat ke solusi ideal** dan **paling jauh dari solusi terburuk**.

## Langkah
| Langkah | Rumus | Jejak |
|---|---|---|
| 1. Matriks keputusan | `v_kj` | tabel |
| 2. Pembagi | `d_j = sqrt(Σ_k v_kj²)` | tabel per kolom "40² + 120² + … = …; √… = d" |
| 3. Normalisasi vektor | `r_kj = v_kj / d_j` | tabel per sel + matriks R |
| 4. Terbobot | `y_kj = w_j · r_kj` | tabel per sel + matriks Y |
| 5. Solusi ideal | `A+_j = max_k y_kj` (benefit) / `min` (cost); `A−_j` kebalikannya | tabel A+ dan A− |
| 6. Jarak | `D+_k = sqrt(Σ_j (y_kj − A+_j)²)`, `D−_k = sqrt(Σ_j (y_kj − A−_j)²)` | tabel per alternatif |
| 7. Kedekatan | `V_k = D−_k / (D+_k + D−_k)` | tabel |
| 8. Ranking | urut V menurun | tabel ranking |

Kasus khusus: jika `D+ + D− = 0` (semua alternatif identik), V = 0.5 untuk semua dan beri peringatan.

## Contoh acuan (DM2 CTO, kriteria C1, C2, C6, C7)
Bobot = (0.4658, 0.2771, 0.0960, 0.1611), CR = 0.0115.
Skor TOPSIS A1…A7 = (0.1483, 0.1301, 0.1842, 0.1606, 0.4024, 0.8576, 0.1522) → juara A6.

DM5 (C3, C6, C7, semua cost): A1 mendapat V = 1.0000 (terbaik di semua kriteria), A6 mendapat V = 0.0000 (terburuk di semua kriteria).
Ini kasus uji yang baik untuk batas 0 dan 1.

## Kelemahan (bahan LLM)
- Bisa terjadi *rank reversal*: menambah/menghapus alternatif dapat mengubah urutan alternatif lain.
- Hasil peka terhadap alternatif ekstrem karena ideal dan anti-ideal ditentukan oleh nilai ekstrem.
