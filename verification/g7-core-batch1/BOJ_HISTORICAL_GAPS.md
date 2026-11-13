# BOJ historical gap reconstruction — development candidate inventory

This is the first isolated implementation slice for issue #65. **None of the entries below is a verified observation**. Values are discovery assertions only, never fed into the production mapping or the existing 40-document verifier.

## Official-source leads and classification

| Date | Regime | Candidate / research task | Official source lead |
| --- | --- | --- | --- |
| 2006-07-14 | Overnight call rate | Around 0.25%; find original policy decision, reaffirmations, and effective date | [BOJ fiscal-2006 operations review](https://www.boj.or.jp/en/research/brp/ron_2007/ron0707c.htm) |
| 2007-02-21 | Overnight call rate | Around 0.5%; independently parse original decision and distinguish basic loan rate | [BOJ meeting minutes](https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_2007/g070221.pdf) |
| 2008-10-31 | Overnight call rate | Extract exact target from original change decision | [BOJ 2008 statement index](https://www.boj.or.jp/en/mopo/mpmdeci/state_2008/index.htm) |
| 2008-12-19 | Overnight call rate | Extract exact target and effective date from original release | [BOJ 2008 statement index](https://www.boj.or.jp/en/mopo/mpmdeci/state_2008/index.htm) |
| 2018-07-31 | YCC | Classify qualitative flexibility, yield target, and any tolerance band separately | [BOJ minutes and original decision attachment](https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_2018/g180731.htm) |
| 2021-03-19 | YCC | ±0.25pp 10Y JGB fluctuation range, separate from around-zero yield target and fixed-rate purchases | [BOJ original policy PDF](https://www.boj.or.jp/en/mopo/mpmdeci/state_2021/k210319a.pdf) |

## Mandatory next verification steps

1. Build independent **2006, 2007, 2008 and 2016–2024** meeting-date censuses using original BOJ indexes; do not assume every statement is a rate change.
2. Locate each exact original decision document and verify publisher bytes, document title, Tokyo decision date, instrument-specific policy language, SHA-256 and any explicit effective date.
3. Extend the regime-aware parser and tests with no-change meetings, instrument-specific qualifiers, contradictions, PDF extraction failures and archive ambiguity.
4. Produce coverage receipts and separate workflow-only PR for manual hosted testing. Only verified original-source receipts may become economic observations.
5. Resolve February 2001 English/Japanese disagreement and historical publication vintages separately.

## Safety / status

- Historical coverage: **PARTIAL**. Candidate discovery is **NOT_VERIFIED**.
- G7-JP-22: **UNCONFIGURED**. Commercial rights: **PENDING**. Production approval: **NOT_APPROVED**.
- Do not merge this feature to main, register datasets, alter existing 194 public IDs, or touch saved research.
- Modern 2024–2026 date reconciliation from Run #24 remains a separate, narrower evidence claim.
