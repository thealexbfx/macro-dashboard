# Official CPI connectivity verification

The manual workflow runs only for the development branch. It checks the official publisher endpoints with the existing bounded, TLS-verified transport. If all probes succeed, it imports the six histories into a new runner-local database and repeats the refresh with a new worker and saved validators. It compares coverage and active generations and checks SQLite integrity and zero public grants. Native keys enforce unique dataset-period rows. Only sanitized receipts are uploaded. The database is temporary.

## Validation status

- Local workflow YAML and manual trigger/permission checks passed. The live verification script compiled. Two existing simulated refresh tests passed, covering 304, retry/backoff, last-good retention and revision preservation.
- GitHub-hosted connectivity is untested. GitHub requires the workflow file on the default branch before manual dispatch. The default branch is main, and the new workflow is only on the feature branch. No workflow run occurred. [GitHub manual dispatch requirements](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
- The six previously validated development backfills remain at 4,278 values and 984 source nulls. There is no new-release verification or new fundamentals backfill in this phase.
- An approved network-enabled development host can run the same checks without any default-branch change. Run `python -m scripts.g7_cpi_probe`, then `python -m scripts.verify_g7_cpi_live <new-directory>`. The supported official alternatives are Statistics Canada's bulk CSV ZIPs or Web Data Service and e-Stat's publisher CSV linked from the 2025-base history listing. Browser captures establish file provenance and coverage only.

## Future operation

Once the live transport is verified, use a separate development job to collect and validate publisher releases. Keep source hashes, definitions, reference dates, release dates, revision evidence and receipts together. If production transfer is later approved, stage the validated artifacts through the existing native importer with explicit identity, rights and release review. A GitHub runner should have no production database credentials. Require approval of a separately reviewed ingestion change before adding schedules, synchronization or publication. Start the eight outstanding GDP, labour, wage and expenditure histories after publisher access is verified.
