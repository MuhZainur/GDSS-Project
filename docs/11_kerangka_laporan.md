# 11 · Kerangka Laporan Tugas Besar

Mengikuti tahapan "Proses Pengembangan DSS" di materi *Membangun DSS*.

1. **Pendahuluan** — latar (keputusan kelompok di perusahaan GPU), rumusan masalah, tujuan, batasan (data fiktif).
2. **Landasan teori** — DSS dan GDSS (definisi, ciri, level teknologi 1–3), AHP, SAW, TOPSIS, Borda, Copeland, AIP; penyelesaian konflik keputusan kelompok.
3. **Perencanaan** — lingkup, kebutuhan (ringkas dari `01_kebutuhan_sistem.md`), alasan memilih pendekatan *prototyping*.
4. **Penelitian / data** — alternatif, kriteria, DM, sumber dan asumsi data.
5. **Analisis & perancangan konsep** — kenapa tiap model dipakai, alur keputusan individu → kelompok, diagram hierarki.
6. **Perancangan** tiga subsistem:
   - Subsistem data (skema JSON/CSV),
   - Subsistem model (rumus + langkah),
   - Subsistem dialog (rancangan tab dan alur pengguna, *wireframe*).
7. **Konstruksi** — teknologi, struktur kode, integrasi LLM.
8. **Implementasi & pengujian** — hasil uji acuan (tabel cocok/tidak), uji contoh dosen, tangkapan layar.
9. **Hasil & pembahasan** — ranking tiap model, perbedaan antar-model dan penyebabnya, pengaruh bobot DM
   (Borda berbobot memilih A6, tanpa bobot memilih A2), analisis kepekaan, ringkasan analisis LLM.
10. **Keterbatasan** — data fiktif; Borda/Copeland membuang selisih skor; AHP bergantung penilaian subjektif;
    LLM gratis bisa berganti/terbatas kuota dan bisa salah, sehingga keputusan akhir tetap di tangan manusia.
11. **Kesimpulan & saran**.
Lampiran: tangkapan layar tiap tab, contoh `results.json`, contoh analisis LLM, transkrip chat.
