# 02 · Studi Kasus: PT NusaCompute

> Semua angka **fiktif tetapi dibuat masuk akal** (perbandingan antar-produk realistis). Bukan data produk nyata.

## Masalah keputusan
PT NusaCompute punya kapasitas produksi terbatas untuk tahun depan. Direksi harus memilih **satu rancangan GPU**
yang diprioritaskan untuk produksi massal. Setiap direktur melihat dari sudut berbeda:
CEO melihat strategi dan keuntungan, CTO melihat teknologi, CMO melihat pasar, CFO melihat biaya dan margin,
Kepala Rantai Pasok melihat risiko produksi.

## Alternatif (7, dikunci untuk semua DM)
| Kode | Nama | Segmen | Deskripsi singkat |
|---|---|---|---|
| A1 | NX-Edge 10 | Edge / IoT | GPU kecil hemat daya untuk perangkat pintar |
| A2 | NX-Game 40 | Gaming menengah | Kartu gaming harga terjangkau, pasar terbesar |
| A3 | NX-Game 80 | Gaming kelas atas | Performa tinggi untuk penggemar |
| A4 | NX-Pro 60 | Workstation | Desain 3D, rendering, CAD |
| A5 | NX-Infer 100 | Pusat data, inferensi AI | Menjalankan model AI yang sudah jadi |
| A6 | NX-Train 200 | Pusat data, pelatihan AI | GPU unggulan untuk melatih model besar |
| A7 | NX-Mobile 30 | Laptop | GPU untuk laptop tipis |

## Kriteria (7)
| Kode | Nama | Satuan | Jenis | Arti |
|---|---|---|---|---|
| C1 | Performa AI | TFLOPS (FP16) | benefit | Makin besar makin baik |
| C2 | Efisiensi daya | TFLOPS per watt | benefit | Makin hemat makin baik |
| C3 | Biaya produksi per unit | USD | **cost** | Makin murah makin baik |
| C4 | Proyeksi permintaan | ribu unit/tahun | benefit | Pasar makin besar makin baik |
| C5 | Margin kotor | % | benefit | Keuntungan per unit |
| C6 | Waktu ke pasar | bulan | **cost** | Makin cepat makin baik |
| C7 | Risiko rantai pasok | skor 1–9 | **cost** | Makin kecil risikonya makin baik |

## Matriks keputusan (nilai mentah)
| Alt | C1 | C2 | C3 | C4 | C5 | C6 | C7 |
|---|---|---|---|---|---|---|---|
| A1 NX-Edge 10 | 40 | 0.80 | 120 | 900 | 35 | 6 | 3 |
| A2 NX-Game 40 | 120 | 0.55 | 280 | 1500 | 30 | 8 | 4 |
| A3 NX-Game 80 | 330 | 0.73 | 650 | 600 | 42 | 10 | 5 |
| A4 NX-Pro 60 | 260 | 0.87 | 900 | 250 | 55 | 11 | 5 |
| A5 NX-Infer 100 | 700 | 1.75 | 4200 | 180 | 65 | 12 | 7 |
| A6 NX-Train 200 | 1800 | 2.57 | 11000 | 90 | 72 | 16 | 9 |
| A7 NX-Mobile 30 | 90 | 1.13 | 210 | 1100 | 33 | 9 | 4 |

Sengaja dibuat **saling tarik-menarik**: A6 unggul di performa dan margin tetapi paling mahal, paling lama, dan paling berisiko;
A1/A2 murah, cepat, dan pasarnya besar tetapi performanya rendah. Akibatnya, model dan DM yang berbeda akan memberi juara
berbeda, dan itu bahan analisis LLM.

## Pengambil keputusan (5)
| Kode | Peran | Kriteria yang dipakai | Model pilihan |
|---|---|---|---|
| DM1 | CEO | C1, C4, C5, C6 | AHP |
| DM2 | CTO | C1, C2, C6, C7 | TOPSIS |
| DM3 | CMO | C1, C3, C4, C6 | SAW |
| DM4 | CFO | C3, C4, C5, C7 | SAW |
| DM5 | Kepala Rantai Pasok | C3, C6, C7 | TOPSIS |

Sesuai materi GDSS: kriteria, bobot, dan model **boleh berbeda** antar-DM, alternatif **wajib sama**.

## Matriks perbandingan berpasangan kriteria (contoh isian)
Urutan baris/kolom mengikuti urutan kriteria di tabel DM.

**DM1 CEO** (C1, C4, C5, C6): margin paling penting, lalu permintaan.
```
      C1   C4   C5   C6
C1    1   1/2  1/3   2
C4    2    1   1/2   3
C5    3    2    1    4
C6   1/2  1/3  1/4   1
```
**DM2 CTO** (C1, C2, C6, C7): performa paling penting.
```
      C1   C2   C6   C7
C1    1    2    4    3
C2   1/2   1    3    2
C6   1/4  1/3   1   1/2
C7   1/3  1/2   2    1
```
**DM3 CMO** (C1, C3, C4, C6): permintaan pasar paling penting.
```
      C1   C3   C4   C6
C1    1   1/2  1/3   2
C3    2    1   1/2   2
C4    3    2    1    4
C6   1/2  1/2  1/4   1
```
**DM4 CFO** (C3, C4, C5, C7): margin paling penting, lalu permintaan.
```
      C3   C4   C5   C7
C3    1   1/2  1/3   2
C4    2    1   1/2   3
C5    3    2    1    4
C7   1/2  1/3  1/4   1
```
**DM5 Kepala Rantai Pasok** (C3, C6, C7): risiko paling penting.
```
      C3   C6   C7
C3    1   1/2  1/3
C6    2    1   1/2
C7    3    2    1
```

## Matriks AHP antar-DM (diisi fasilitator)
```
       DM1  DM2  DM3  DM4  DM5
DM1     1    2    3    3    4
DM2    1/2   1    2    2    3
DM3    1/3  1/2   1    1    2
DM4    1/3  1/2   1    1    2
DM5    1/4  1/3  1/2  1/2   1
```
Hasil: bobot DM = (0.4017, 0.2442, 0.1373, 0.1373, 0.0794), CR = 0.0074.

## Hasil acuan singkat (lengkapnya di `data/expected/golden_results.json`)
| Model kelompok | Juara | Urutan lengkap |
|---|---|---|
| Borda berbobot | A6 NX-Train 200 | A6, A2, A5, A7, A1, A3, A4 |
| Borda tanpa bobot | A2 NX-Game 40 | A2, A1, A6=A7 (seri), A5, A3, A4 |
| Copeland-kelompok | A6 NX-Train 200 | A6, A2, A5, A7, A1, A3, A4 |
| AHP-kelompok (AIP) | A6 NX-Train 200 | A6, A1, A2, A7, A5, A3, A4 |

Pelajarannya: bobot DM mengubah juara (A6 kalau suara CEO dan CTO lebih berat, A2 kalau semua DM setara).
Ini persis jenis perbedaan yang harus dijelaskan LLM.
