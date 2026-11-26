# 06 · Skema Data

Semua file UTF-8, JSON berindentasi 2. Angka disimpan presisi penuh (bukan dibulatkan) di `results.json`.

## 1. `session.json` (storage/sessions/<session_id>/session.json)
```json
{
  "session_id": "nusacompute-2026",
  "title": "Prioritas produksi GPU 2027",
  "goal": "Memilih 1 rancangan GPU untuk produksi massal",
  "alternatives": [{"id": "A1", "name": "NX-Edge 10", "segment": "Edge / IoT", "desc": "..."}],
  "criteria": [{"id": "C1", "name": "Performa AI", "unit": "TFLOPS", "type": "benefit"}],
  "values": {"A1": {"C1": 40, "C2": 0.8, "C3": 120, "C4": 900, "C5": 35, "C6": 6, "C7": 3}},
  "dms": [{"id": "DM1", "role": "CEO", "name": "Direktur Utama"}],
  "dm_weighting": {"mode": "ahp", "pairwise": [[1, 2, 3, 3, 4], ["1/2", 1, 2, 2, 3]], "order": ["DM1","DM2","DM3","DM4","DM5"]},
  "dm_inputs": {
    "DM1": {
      "criteria": ["C1", "C4", "C5", "C6"],
      "pairwise": [[1, "1/2", "1/3", 2], [2, 1, "1/2", 3], [3, 2, 1, 4], ["1/2", "1/3", "1/4", 1]],
      "chosen_method": "AHP",
      "submitted_at": "2026-11-20T09:00:00+07:00"
    }
  },
  "locked_alternatives": true,
  "status": "ready"
}
```
- Pecahan disimpan sebagai string `"1/3"` agar tampil persis; angka bulat sebagai angka.
- `dm_weighting.mode`: `"ahp"` | `"equal"`.
- `chosen_method`: `"AHP"` | `"SAW"` | `"TOPSIS"` | `"COPELAND"`.

## 2. `results.json` (storage/runs/<run_id>/results.json)
```json
{
  "run_id": "20261120-090512-ab12",
  "session_id": "nusacompute-2026",
  "created_at": "2026-11-20T09:05:12+07:00",
  "app_version": "0.1.0",
  "alternatives": ["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
  "alternative_names": {"A1": "NX-Edge 10"},
  "dm_weights": {"weights": {"DM1": 0.4017}, "lambda_max": 5.0331, "CI": 0.0083, "CR": 0.0074, "steps": []},
  "individual": {
    "DM1": {
      "role": "CEO",
      "criteria": ["C1", "C4", "C5", "C6"],
      "criteria_weights": {"C1": 0.1611, "C4": 0.2771, "C5": 0.4658, "C6": 0.0960},
      "consistency": {"lambda_max": 4.031, "CI": 0.0103, "CR": 0.0115, "consistent": true},
      "chosen_method": "AHP",
      "models": {
        "AHP":      {"scores": {"A1": 0.1267}, "ranks": {"A1": 5}, "steps": []},
        "SAW":      {"scores": {}, "ranks": {}, "steps": [], "contributions": {"A1": {"C1": 0.0036}}},
        "TOPSIS":   {"scores": {}, "ranks": {}, "steps": [], "extra": {"d_plus": {}, "d_minus": {}}},
        "COPELAND": {"scores": {}, "ranks": {}, "steps": [], "extra": {"wins": {}, "ties": {}, "losses": {}, "contests": []}}
      }
    }
  },
  "group": {
    "BORDA_UNWEIGHTED": {"scores": {}, "normalized": {}, "ranks": {}, "steps": []},
    "BORDA_WEIGHTED":   {"scores": {}, "normalized": {}, "ranks": {}, "steps": [], "contributions": {"A6": {"DM1": 2.4102}}},
    "COPELAND_GROUP":   {"scores": {}, "ranks": {}, "steps": [], "extra": {"wins": {}, "ties": {}, "losses": {}, "contests": []}},
    "AHP_GROUP_AIP":    {"scores": {}, "ranks": {}, "steps": []}
  },
  "agreement": {"spearman": {"BORDA_WEIGHTED|COPELAND_GROUP": 1.0}, "kendall": {}},
  "winners": {"BORDA_WEIGHTED": ["A6"], "BORDA_UNWEIGHTED": ["A2"], "COPELAND_GROUP": ["A6"], "AHP_GROUP_AIP": ["A6"]},
  "warnings": []
}
```
`winners` berupa list karena bisa seri.

## 3. Objek `Step` (dipakai di semua `steps`)
```json
{
  "id": "ahp.normalize",
  "title": "Langkah 2. Normalisasi",
  "explanation": "Tiap angka dibagi jumlah kolomnya.",
  "table": {
    "columns": ["Norm_A", "C1", "C4"],
    "rows": [["C1", "1 ÷ 6.500 = 0.154", "0.5 ÷ 3.833 = 0.130"]],
    "highlight": [[0, 1]]
  },
  "matrix": {"latex": "A=\\begin{bmatrix}1 & 0.5\\\\ 2 & 1\\end{bmatrix} \\rightarrow \\ldots"},
  "result": {"text": "Setiap kolom berjumlah 1.", "status": "info"}
}
```
`status`: `info` | `ok` | `warn` | `bad`. Semua field kecuali `id`, `title` boleh `null`.

## 4. `rankings.csv` (format panjang, satu baris = satu alternatif dalam satu model)
```
run_id,scope,dm_id,dm_role,model,is_chosen_method,alternative_id,alternative_name,score,rank
20261120-090512-ab12,individual,DM1,CEO,AHP,true,A1,NX-Edge 10,0.126700,5
20261120-090512-ab12,group,,,BORDA_WEIGHTED,,A6,NX-Train 200,4.562200,1
```
Format panjang dipilih supaya mudah difilter di Excel/pandas dan mudah dibaca LLM.

## 5. `llm_payload.json` (ringkas, yang dikirim ke LLM)
Tanpa `steps` (terlalu panjang). Berisi:
```json
{
  "run_id": "...",
  "decision": {"goal": "...", "company": "PT NusaCompute (fiktif)"},
  "alternatives": [{"id": "A1", "name": "NX-Edge 10", "segment": "Edge / IoT", "values": {"C1": 40}}],
  "criteria": [{"id": "C1", "name": "Performa AI", "unit": "TFLOPS", "type": "benefit"}],
  "dm": [{"id": "DM1", "role": "CEO", "weight": 0.4017, "criteria_weights": {"C1": 0.1611}, "CR": 0.0115, "chosen_method": "AHP"}],
  "individual_rankings": {"DM1": {"AHP": {"ranks": {}, "scores": {}}, "SAW": {}, "TOPSIS": {}, "COPELAND": {}}},
  "group_rankings": {"BORDA_WEIGHTED": {"ranks": {}, "scores": {}}},
  "winners": {},
  "agreement": {},
  "flags": {"inconsistent_dm": [], "ties": [{"model": "BORDA_UNWEIGHTED", "alternatives": ["A6", "A7"], "rank": 3}], "close_calls": [{"model": "AHP_GROUP_AIP", "a": "A1", "b": "A2", "gap": 0.000083}]},
  "method_notes": {"BORDA": "...", "COPELAND": "...", "SAW": "...", "TOPSIS": "...", "AHP": "..."}
}
```
`close_calls`: pasangan peringkat berurutan yang selisih skornya < 1% dari skor tertinggi model tersebut.

## 6. `analysis.json` + `analysis.md`
```json
{"run_id": "...", "model_used": "nvidia/...:free", "created_at": "...", "version": 1,
 "sections": {"ringkasan": "...", "perbandingan": "...", "kelebihan_kelemahan": "...",
              "rekomendasi": {"alternative": "A6", "based_on_model": "BORDA_WEIGHTED", "reasons": ["..."]},
              "risiko": "...", "konsistensi": "..."},
 "markdown": "..."}
```

## 7. Chat: `storage/chats/<run_id>/<session_id>.json`
```json
{
  "chat_id": "c-20261120-0915-x1",
  "run_id": "20261120-090512-ab12",
  "created_at": "...",
  "title": "Diskusi risiko A6",
  "messages": [
    {"role": "user", "content": "Apa risiko memilih A6?", "ts": "...", "web_search": true},
    {"role": "assistant", "content": "...", "ts": "...", "model_used": "nvidia/...:free",
     "sources": [{"title": "...", "url": "https://..."}]}
  ]
}
```
