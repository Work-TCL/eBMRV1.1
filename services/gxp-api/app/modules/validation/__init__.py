"""WP-12 -- Validation Platform & Evidence (Documents 79, 80, 81, 82, 83, 84, 86, 88, 89, 90, 91, 92,
93, 94, 96 / SPEC-VAL-001..018 except 007/009/017, which belong to WP-14's PQ/UAT and go-live scope).

One `validation` PostgreSQL schema owns every entity in `04_DATA_MODEL_CATALOGUE.md`'s Document 79-96
section. Submodules are split one-per-source-document (same "per concern" split as
`app/modules/security/`), sharing the Mutation Gateway helpers in `shared.py`.
"""
