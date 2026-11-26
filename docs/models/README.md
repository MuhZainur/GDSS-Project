# Model-Model dan Hubungannya

```
                 ┌──────────────── AHP (wajib) ────────────────┐
                 │                                              │
  Tiap DM: matriks kriteria ──► bobot kriteria w_DM      Fasilitator: matriks antar-DM ──► bobot DM v
                 │                                              │
     ┌───────────┼─────────────┬───────────────┐                │
     ▼           ▼             ▼               ▼                │
   AHP        SAW          TOPSIS      Copeland-kriteria        │   (model individu, per DM)
   (skor)     (skor)       (skor)      (poin)                   │
     └───────────┴──── pilih "model pilihan" DM ──┘             │
                         │ ranking tiap DM                      │
                         ▼                                      ▼
          ┌──────── Borda (berbobot v / tanpa bobot) ───────────┤
          ├──────── Copeland-kelompok (berbobot v) ─────────────┤   (model kelompok)
          └──────── AHP-kelompok AIP (skor AHP tiap DM, bobot v)┘
```

| Model | Tingkat | Masukan | Butuh bobot dari AHP? | Keluaran | File |
|---|---|---|---|---|---|
| AHP | individu + bobot | matriks berpasangan, nilai alternatif | (menghasilkan bobot) | bobot, skor, CR | `ahp.md` |
| SAW | individu | nilai alternatif + bobot | ya | skor 0–1 | `saw.md` |
| TOPSIS | individu | nilai alternatif + bobot | ya | skor kedekatan 0–1 | `topsis.md` |
| Copeland-kriteria | individu | nilai alternatif + bobot | ya | poin menang−kalah | `copeland.md` |
| Borda | kelompok | ranking tiap DM (+ bobot DM) | bobot DM dari AHP | poin, bobot akhir | `borda.md` |
| Copeland-kelompok | kelompok | ranking tiap DM + bobot DM | bobot DM dari AHP | poin | `copeland.md` |
| AHP-kelompok (AIP) | kelompok | skor AHP tiap DM + bobot DM | ya | skor | `ahp_kelompok.md` |

**Peran AHP sebagai "pemasok bobot":** SAW, TOPSIS, dan Copeland tidak bisa menentukan bobot sendiri.
AHP mengubah penilaian "kriteria A sedikit lebih penting dari B" menjadi angka bobot, lalu bobot itu dipakai model lain.

## Konvensi umum (semua model)
- Ranking: skor lebih besar = lebih baik (kecuali disebut lain). Seri → peringkat sama (metode `min`).
- Presisi: float64; tampil 4 desimal.
- Setiap fungsi model mengembalikan:
```python
{
  "model": "SAW",                # nama model
  "scope": "individual",         # individual | group
  "dm_id": "DM3",                # None untuk model kelompok
  "scores": {"A1": 0.6498, ...},
  "ranks":  {"A1": 2, ...},
  "steps":  [ Step, ... ],       # jejak untuk tab Perhitungan
  "meta":   {...}                # mis. CR, lambda_max
}
```
- `Step` (lihat `../06_skema_data.md`): `{ "id", "title", "explanation", "table": {...} | null, "matrix": {...} | null, "formula": "LaTeX" | null }`.
  Urutan tampilan tiap langkah: **penjelasan → tabel aritmatika (setiap sel ditulis "a ÷ b = c") → versi matriks (LaTeX bmatrix)**.
