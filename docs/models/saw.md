# SAW (Simple Additive Weighting) — model individu

Bobot kriteria **diambil dari AHP** milik DM tersebut.

## Langkah
| Langkah | Rumus | Jejak |
|---|---|---|
| 1. Matriks keputusan | nilai mentah `v_kj` untuk kriteria milik DM | tabel |
| 2. Normalisasi | benefit: `r_kj = v_kj / max_k v_kj`; cost: `r_kj = min_k v_kj / v_kj` | tabel per sel "v ÷ max = r" + matriks R |
| 3. Bobot | `w` dari AHP DM | tabel bobot |
| 4. Skor | `S_k = Σ_j w_j · r_kj` | tabel per alternatif "w1×r1 + … = S" + versi matriks `R × w = S` |
| 5. Ranking | urut S menurun | tabel ranking |

Kontribusi kriteria (untuk grafik bertumpuk): `kontribusi_kj = w_j · r_kj`.

## Contoh acuan (DM3 CMO, kriteria C1, C3, C4, C6)
Bobot = (0.1653, 0.2550, 0.4715, 0.1083), CR = 0.0170.
Skor SAW A1…A7 = (0.6498, 0.6730, 0.3309, 0.1955, 0.1823, 0.2369, 0.5719) → juara A2.

## Kelemahan yang perlu diketahui (bahan LLM)
- Kompensatoris penuh: nilai sangat buruk di satu kriteria bisa ditutup nilai bagus di kriteria lain.
- Normalisasi min/max peka terhadap pencilan (A6 dengan biaya 11000 membuat alternatif lain terlihat sangat murah).
