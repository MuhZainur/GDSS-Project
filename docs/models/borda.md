# Borda — model kelompok

Sumber: materi dosen "10. GDSS". Ranking tiap DM diubah menjadi **poin**: peringkat tinggi dapat poin besar.
Untuk m alternatif: peringkat 1 = m−1 poin, peringkat 2 = m−2, …, peringkat m = 0
(untuk 3 kandidat: 2, 1, 0 seperti contoh dosen; untuk 7 alternatif: 6, 5, …, 0).

Masukan: ranking tiap DM dari **model pilihan DM**, dan bobot DM dari AHP antar-DM.

## Varian A: Borda tanpa bobot (persis contoh dosen)
| Langkah | Isi | Jejak |
|---|---|---|
| 1 | Tabel ranking DM × alternatif | tabel |
| 2 | Tabel frekuensi: berapa DM yang menaruh alternatif k di peringkat 1, 2, …, m | tabel seperti slide dosen |
| 3 | Poin = Σ (frekuensi × poin peringkat) | tabel "0×2 + 4×1 + 3×0 = 4" |
| 4 | Bobot akhir = poin / total poin | tabel + total |
| 5 | Ranking dari bobot terbesar | tabel |

## Varian B: Borda berbobot (bobot DM dari AHP)
`B_k = Σ_i v_i · (m − r_ik)` dengan v_i bobot DM ke-i dan r_ik ranking yang diberikan DM i ke alternatif k.
Bobot akhir = B_k / Σ B.

Catatan kesetaraan (materi dosen menyebut versi "skor = Σ bobot DM × ranking, terkecil yang terbaik"):
karena Σ v_i = 1, maka `B_k = m − Σ v_i r_ik`. Urutannya **identik** dengan versi dosen. Tampilkan kedua angka di tab Perhitungan.

## Contoh acuan
- Tanpa bobot: poin A1…A7 = (20, 21, 11, 7, 12, 17, 17) → ranking (2, 1, 6, 7, 5, 3, 3) — A6 dan A7 seri.
- Berbobot: B = (3.0347, 3.9163, 2.0287, 1.1661, 3.1820, 4.5622, 3.1099), bobot akhir = (0.1445, 0.1865, 0.0966, 0.0555, 0.1515, 0.2172, 0.1481) → juara A6.

## Contoh dosen untuk uji (7 DM, 3 kandidat)
Ranking A = (2,3,3,2,2,3,2), B = (1,2,1,1,3,1,1), C = (3,1,2,3,1,2,3).
Harus keluar poin A = 4, B = 11, C = 6, total 21, bobot (0.19, 0.52, 0.29) → B juara.
(Di slide tertulis "4+11+5 = 20"; yang benar 4+11+6 = 21, dan bobot di slide memang memakai 21.)

## Kelemahan (bahan LLM)
- Menganggap jarak antar-peringkat selalu sama (peringkat 1 ke 2 sama jauhnya dengan 6 ke 7), padahal skor aslinya bisa sangat dekat.
- Bisa dimanipulasi dengan sengaja menaruh pesaing di peringkat paling bawah.
