# Batch 0: preserved planning evidence

Recovered on 30 October 2026 from the earlier workspace research directory
`outputs/data-architecture-research/`. These files were not in the application
Git tree at release `e70e338a546afb64bf1e427f12bd63532f7ec9b4`.

`originals/` contains the byte-for-byte 264-entry JSON catalog, readable index,
architecture proposal (27 October), and 34-selection gap report (28 October).
`provenance.json` records original workspace paths, byte counts and SHA-256 hashes.
Git attributes disable newline conversion for these originals. Workbooks, images,
provider response bodies, databases and credentials are deliberately excluded.
Credential placeholders in published endpoint examples are not credentials.

Original research is historical evidence, not current permission approval. In
particular, the original G15 iron-ore unit/selector assumption is superseded by
`WORLD_BANK_INGESTION_READINESS.md` and the actual adapter. The original is retained
unchanged so that this correction is visible rather than silently rewriting it.

## Reconciliation

- 264 individually identified original catalog rows; no repeated source selector.
- 34 additional selections. Panels, stock components and paired trade flows are
  not falsely expanded into invented atomic series.
- 19 original rows reuse existing public canonical IDs.
- Three gap selections reuse `wb_brent_monthly`, `wb_copper_monthly`, and
  `wb_iron_ore_monthly`; they remain private and rights-unreviewed.
- 11 existing public datasets outside the original plan are retained.
- Result: 309 manifest entries with exactly 298 planning references, not a claim
  that there are 309 approved or implemented atomic feeds.
- FRED USREC remains separate optional recession context. Legacy financial/macro
  engine configurations are not silently promoted into this expansion manifest.
- Agricultural commodities and St. Louis-specific series were not selected by
  these original plans and need a separate scope decision.

`legacy_public_e70.json` freezes the 30 existing public definitions from the
reviewed release. Existing public display is recorded as historical behavior,
not inferred redistribution clearance. AI stays denied in the planning manifest;
existing runtime AI remains disabled and unchanged. Discovery eligibility for the
existing definitions mirrors the existing curated modes.

## Canonical assignments

`catalog/datasets.json` is the checked-in assignment record. New IDs use a
provider prefix and a hash of provider, exact selector, region and frequency.
Names, units and ML/G row numbers do not determine identity. Once assigned, IDs
are retained; provider/definition changes require an explicit alias/version review.
`planning_refs` holds original references without making aliases extra datasets.
The generator refuses to reassign an existing source identity to another ID.

All nonlegacy entries default to private, AI denied and Discovery excluded.
Every rights status remains `unreviewed`. Source evidence and licence links are
review inputs, not grants. Unknown units/selectors are explicitly unresolved;
multi-series selections cannot be registered as a single public series.

Rebuild locally from repository root:

```text
python scripts/build_dataset_manifest.py
python -m pytest backend/tests/test_batch0_foundation.py -q
```

This reads only the checked-in planning sources. It does not use HTTP, initialize
SQLite, register ingestion jobs, invoke the scheduler or change permissions.
