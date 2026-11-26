# 00 · Ringkasan Proyek

## Latar
Tugas besar mata kuliah *Intelligent Decision Support System*: membangun aplikasi **Group Decision
Support System (GDSS)**. Ketentuan dari dosen:
- AHP **wajib** ada.
- Ada model lain, termasuk model penyelesaian konflik kelompok (Borda dan Copeland, sesuai materi GDSS).
- Ada input dari masing-masing anggota kelompok (pengambil keputusan / DM).

## Tujuan aplikasi
Membantu kelompok direksi PT NusaCompute (perusahaan GPU fiktif) memilih **satu rancangan GPU** dari 7 kandidat
untuk diprioritaskan pada siklus produksi berikutnya, dengan:
1. Menghitung ranking tiap DM dengan beberapa model.
2. Menggabungkan ranking semua DM menjadi keputusan kelompok.
3. Menampilkan hasil, visualisasi, kontribusi, dan **hitungan langkah demi langkah**.
4. Menyimpan hasil (JSON + CSV) lalu meminta **LLM** menganalisis perbedaan antar-model dan memberi rekomendasi beralasan.
5. Menyediakan **mode chat** untuk diskusi lanjutan, dengan pencarian internet.

## Prinsip dari materi GDSS yang dipegang
| Prinsip (materi dosen) | Wujud di aplikasi |
|---|---|
| Tiap DM boleh punya tingkat kepentingan berbeda | Bobot DM dihitung dengan AHP antar-DM |
| Tiap DM boleh memakai model berbeda | (Disederhanakan di UI v0.3) Semua metode dihitung untuk semua DM; peringkat AHP tiap DM dibawa ke Borda dan Copeland kelompok |
| Tiap DM boleh memakai bobot berbeda | (UI v0.3) Semua DM menilai semua kriteria; tiap DM mengisi matriks AHP sendiri. Jumlah dan nama produk, kriteria, DM bebas diubah pengguna |
| **Alternatif harus sama** | 7 alternatif GPU dikunci untuk semua DM |
| Penyelesaian konflik: Borda, Copeland | Tersedia di tingkat kelompok |
| Arsitektur GDSS: DBMS, MBMS, DGMS | Basis data JSON, mesin model, antarmuka web (lihat `03_arsitektur.md`) |
| Pengembangan dengan prototyping | Rencana kerja bertahap (`10_rencana_kerja.md`) |

## Istilah
| Istilah | Arti | Perumpamaan |
|---|---|---|
| DM (*decision maker*) | Pengambil keputusan | Juri |
| Alternatif | Pilihan yang diranking (7 GPU) | Peserta lomba |
| Kriteria | Aspek penilaian | Aspek yang dinilai juri |
| Bobot | Seberapa penting suatu kriteria / DM | Porsi nilai tiap aspek |
| CR (*consistency ratio*) | Ukuran konsistensi penilaian AHP; harus < 0.1 | Alarm penilaian yang saling bertabrakan |
| Model individu | Model yang menghasilkan ranking satu DM | Cara satu juri menilai |
| Model kelompok | Model yang menggabungkan ranking semua DM | Rapat juri merangkum nilai |
| Fasilitator | Pengguna yang menyiapkan sesi dan mengisi bobot antar-DM | Ketua panitia |
| Run | Satu kali perhitungan lengkap, punya `run_id` | Satu sesi penjurian |

## Di luar lingkup
- Login dan otentikasi tingkat produksi (cukup pemilihan peran sederhana).
- Data pasar GPU nyata dan waktu nyata (data contoh fiktif; LLM boleh mencari konteks pasar di internet saat chat).
- Aplikasi mobile native (cukup web yang responsif).
