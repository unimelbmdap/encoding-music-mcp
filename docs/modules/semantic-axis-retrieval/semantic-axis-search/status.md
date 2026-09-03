# Semantic axis search — ✓

## Verification

2026-09-03 — Subagent implemented the opt-in `return_z_score` flag. `PYTHONPATH=src .venv/bin/pytest tests/` passed, confirming exact-model filtering, normalization arithmetic, and the new dataset-normalized z-score return shape without disturbing the default structure.

Qualification: the strict build retains the pre-existing external-notebook-link warning.

## Next move

(none — complete)
