# Copeland — dua varian

Sumber: materi dosen "10. GDSS" (contoh Ahmad, Ihsan, Akbar, Asrul, Anwar). Prinsipnya **adu satu lawan satu**:
setiap pasangan alternatif dipertandingkan. Menang = +1, imbang = 0, kalah = −1. Poin dijumlahkan, lalu diranking.
Untuk m alternatif ada m(m−1)/2 pertandingan (7 alternatif → 21).

---

## Varian 1: Copeland-kriteria (model individu, per DM) — persis seperti contoh dosen
Bobot kriteria **dari AHP** milik DM.

| Langkah | Isi | Jejak |
|---|---|---|
| 1. Data | kriteria, bobot (AHP), nilai alternatif | tabel |
| 2. Urutkan | per kriteria, urutkan alternatif dari terbaik (benefit: terbesar; cost: terkecil) | tabel urutan per kriteria |
| 3. Pertandingan | untuk pasangan (a, b): jumlahkan bobot kriteria di mana a lebih baik (`W_a`) dan di mana b lebih baik (`W_b`). Nilai sama di satu kriteria = bobotnya tidak diberikan ke siapa pun | satu tabel per pasangan (dropdown pasangan) + matriks hasil 7×7 |
| 4. Poin | `W_a > W_b` → a menang (+1), b kalah (−1); sama (selisih < 1e−12) → imbang (0) | tabel |
| 5. Hasil | tabel menang / imbang / kalah / poin / ranking | tabel |

**Contoh acuan (DM1 CEO):** poin A1…A7 = (−2, −4, 2, 0, 4, 6, −6) → ranking (5, 6, 3, 4, 2, 1, 7).
**DM2 CTO:** poin = (−2, −4, −2, −2, 4, 6, 0) → ranking (4, 7, 4, 4, 2, 1, 3), ada peringkat seri.

---

## Varian 2: Copeland-kelompok (model kelompok)
Pemetaan dari varian 1: **"kriteria" diganti "DM"**, **"bobot kriteria" diganti "bobot DM"**, dan
**"nilai alternatif" diganti "ranking dari model pilihan DM"** (ranking lebih kecil = lebih baik).

| Langkah | Isi |
|---|---|
| 1 | Kumpulkan ranking tiap DM (dari model pilihannya) dan bobot DM (AHP antar-DM) |
| 2 | Untuk setiap pasangan (a, b): `W_a = Σ v_i` untuk DM i yang menaruh a di atas b; `W_b` sebaliknya |
| 3 | Menang +1, imbang 0, kalah −1 |
| 4 | Tabel menang/imbang/kalah/poin/ranking + matriks 7×7 pemenang pertandingan |

Opsi (S): mode tanpa bobot (setiap DM bernilai 1, jadi pemenang = suara mayoritas).

**Contoh acuan (bobot DM dari AHP):** menang = (2, 5, 1, 0, 4, 6, 3), kalah = (4, 1, 5, 6, 2, 0, 3), poin = (−2, 4, −4, −6, 2, 6, 0)
→ juara A6, lalu A2, A5, A7, A1, A3, A4.
Contoh satu pertandingan: A1 vs A2 → W_A1 = 0.4609, W_A2 = 0.5391 → A2 menang.

## Contoh dosen untuk uji (varian 1, bobot 23/20/18/15/11/8/5 %)
Hasil yang harus keluar: poin Ahmad −2, Ihsan 0, Akbar 2, Asrul −4, Anwar 4 → ranking Anwar 1, Akbar 2, Ihsan 3, Ahmad 4, Asrul 5.
(Catatan: tabel urutan kolom C2 dan C4 di slide ada salah ketik; hasil akhirnya tetap benar. Lihat `../09_pengujian.md`.)

## Kelemahan (bahan LLM)
- Hanya melihat siapa yang menang, bukan selisihnya: menang tipis dan menang telak sama-sama +1.
- Sering menghasilkan seri; perlu aturan pemecah seri (aplikasi menampilkan seri apa adanya, LLM mengomentarinya).
