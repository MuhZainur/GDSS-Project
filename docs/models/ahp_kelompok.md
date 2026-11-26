# AHP-Kelompok (AIP) — model kelompok

Menggabungkan **skor AHP** tiap DM (bukan rankingnya), sehingga selisih tipis/telak tetap terbawa.
Metode: **AIP (Aggregation of Individual Priorities)** dengan rata-rata geometrik berbobot.

Kenapa AIP, bukan AIJ? AIJ (rata-rata geometrik tiap sel matriks) mensyaratkan semua DM memakai kriteria yang sama.
Di kasus ini tiap DM memakai subset kriteria berbeda, jadi AIP yang cocok. AIJ boleh dibuat sebagai opsi (O)
yang hanya aktif bila semua DM memilih kriteria yang sama.

## Langkah
| Langkah | Rumus | Jejak |
|---|---|---|
| 1 | Ambil skor AHP tiap DM: `s_ik` | tabel DM × alternatif |
| 2 | Ambil bobot DM `v_i` (AHP antar-DM) | tabel |
| 3 | Rata-rata geometrik berbobot: `g_k = Π_i s_ik^(v_i)` (hitung via `exp(Σ v_i ln s_ik)`) | tabel per alternatif: "0.1267^0.4017 × 0.0897^0.2442 × … = g" |
| 4 | Normalisasi: `G_k = g_k / Σ g` | tabel |
| 5 | Ranking | tabel |

Skor AHP selalu > 0 (karena pakai normalisasi jumlah dan kebalikan untuk cost), jadi logaritma aman.
Tetap tambahkan pengaman: jika ada skor ≤ 0, ganti 1e−12 dan beri peringatan.

## Contoh acuan
G = (0.1494, 0.1494, 0.1237, 0.1092, 0.1362, 0.1904, 0.1418) → ranking (2, 3, 6, 7, 5, 1, 4).
Dengan 6 desimal: A1 = 0.149435, A2 = 0.149352 (A1 sedikit di atas A2, tidak seri).
