# Reference results (answer key)

`golden_results.json` was computed with numpy (float64) from `../sample_case.json`, rounded to 4 decimals.
Ranking uses the `min` method (a tie gives the same rank). The individual rankings used for group aggregation
are taken from each DM's `chosen_method`.

Contents:
- `dm.<DMx>`: criteria, matrix, weights, λmax, CR, scores and ranks of the 4 individual models (AHP, SAW, TOPSIS, COPELAND = criteria Copeland).
- `dm_weights`: the DM-vs-DM matrix, weights, CR.
- `group`: BORDA_weighted, BORDA_unweighted, COPELAND_group, AHP_group_AIP.

In the app's `results.json` the group keys are upper case as in `docs/06_skema_data.md`
(`BORDA_WEIGHTED`, `BORDA_UNWEIGHTED`, `COPELAND_GROUP`, `AHP_GROUP_AIP`). A test only needs to map the names.
