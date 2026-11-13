# Bank of Japan historical monetary policy candidate

This development audit covers 40 selected original decisions through October 30, 2026. The BOJ annual statement indexes for 2024–2026 supply an independent date census for the March 2024 onward framework. Date reconciliation is a narrower claim than full historical or instrument coverage. Run #22 verified two 2026 statements in the earlier verifier. The new historical audit awaits a hosted run.

## Source inventory

| Source | Use |
| --- | --- |
| [BOJ meeting minutes, annual index](https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_all/index.htm) and [April 9, 1998 minutes](https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_1998/g980409.htm) | Meeting census, including early meetings and references to attachments. Minutes and original statements have different release dates. |
| [September 9, 1998 original decision](https://www.boj.or.jp/en/mopo/mpmdeci/mpr_1998/k980909c.htm) and [BOJ operating guideline history](https://www.boj.or.jp/en/about/education/oshiete/seisaku/b42.htm) | Earliest explicit numeric overnight-call-rate decision located for this build. The BOJ describes market-rate targeting from 1995 and specific published operating guidelines from 1998. |
| [Unconventional policy decision index](https://www.boj.or.jp/en/mopo/outline/bpreview/ref.htm), [QQE original release index](https://www.boj.or.jp/en/mopo/outline/ref_qqe.htm), [financial crisis measures](https://www.boj.or.jp/en/mopo/outline/cfc.htm) | Discovery and cross-checks. Observation authority comes from the original decision linked by each source. |
| [2024 statements](https://www.boj.or.jp/en/mopo/mpmdeci/state_2024/index.htm), [2025 statements](https://www.boj.or.jp/en/mopo/mpmdeci/state_2025/index.htm), [2026 statements](https://www.boj.or.jp/en/mopo/mpmdeci/state_2026/index.htm) | Date census from March 19, 2024 through October 30, 2026. Reference charts and documents on the same date do not add meetings. A date match establishes listed-date coverage only. |
| [BOJ Time-Series Data Search](https://www.stat-search.boj.or.jp/index_en.html) and [discount and basic loan rate CSVs](https://www.boj.or.jp/en/statistics/boj/other/discount/) | Observed call rates and measured monetary base are context. Discount and loan rate downloads cover different administered instruments. No downloaded series was established as a continuous announced overnight target. |

## Regime timeline and coverage

| Decision window | BOJ operating policy | Coverage in this audit |
| --- | --- | --- |
| Before September 9, 1998 | Earlier discount-rate and market-rate guidance frameworks. April 1998 minutes describe maintaining the existing stance. | Unsupported by this inventory. Earlier original numeric guidelines and policy baselines require separate reconstruction. |
| September 1998 to February 1999 | Uncollateralized overnight call target. September 9 decision around 0.25%. | Selected anchor only. |
| February 1999 to August 2000 | ZIRP. Initial guidance around 0.15%, then as low as possible. | Introduction and exit are selected. Keep initial guidance separate from the qualitative operating instruction. April 1999 forward guidance and intervening decisions need reconciliation. |
| August 2000 to March 2001 | Overnight call targeting resumed. August 11 around 0.25%. February 28, 2001 original English statement says around 0.15%. | Selected anchors. A BOJ-hosted research paper summarizes the February 2001 move as 0.125%. The original English statement governs this receipt. Record and reconcile the discrepancy with the Japanese original and minutes before promotion. The discount-rate effective date in that statement applies to a separate instrument. |
| March 2001 to March 2006 | QE targeted outstanding BOJ current-account balances in yen. | Introduction and three 2001 changes. The 2002–04 adjustments and the full meeting census remain open. |
| March 2006 to October 2010 | Overnight call targeting resumed. March 2006 explicitly said effectively zero. Subsequent adjustments include the 2006 and 2007 increases and two 2008 reductions. | March 2006 anchor. The linked original releases for July 2006, February 2007, October 2008 and December 2008 still need parser coverage and effective-date review. |
| October 2010 to April 2013 | Comprehensive easing combined a 0–0.1% overnight call range and asset purchases. | Introduction only. Asset purchase and intervening guidelines remain open. |
| April 2013 to January 2016 | QQE targeted annual monetary-base growth, initially around ¥60–70 trillion per year. | Introduction and October 2014 expansion. Other decisions and instruments remain open. |
| January to September 2016 | QQE plus a −0.1% rate on a tier of BOJ current-account balances, effective February 16, 2016. | Negative-rate anchor. Concurrent monetary-base and tier changes need separate reconstruction. |
| September 2016 to March 2024 | YCC combined a −0.1% policy-balance rate and around 0% 10-year JGB yield target. Later bands, fixed-rate offers and references had distinct roles. | Introduction, December 2022 and July/October 2023 changes, and January 2024 snapshot. Earlier YCC modifications, including 2018 and 2021, and the full meeting census remain open. |
| March 19, 2024 onward | Short-term rate again the main tool. Announced call range 0–0.1%, effective March 21. Subsequent announced increases to 0.25%, 0.50%, 0.75%, 1.00% and 1.25%. | 22 selected statements, including intervening reaffirmations, through October 30, 2026. Audit reconciles listed dates and independently tests source text and supported effective dates. |

September 9, 1998 is a defensible starting anchor for the reconstructed decision history. March 19, 2024 is the candidate start for a contiguous modern call-guideline segment, subject to hosted reconciliation and an independent coverage review. Keep event-level regimes, instruments, and qualifiers. A scalar series that crosses reserve quantity, reserve-tier rates and JGB yield targeting would change economic meaning. A future call-guideline view can preserve point guidance, ranges and qualitative guidance with gaps during regimes where no comparable call target applies.

## Evidence schema

| Field | Meaning |
| --- | --- |
| `decision_date`, `decision_date_status`, `frequency` | Tokyo calendar date from the decision header when verified. An unresolved row retains the inventory date as a candidate only. Frequency is decision-event, including reaffirmations. |
| `effective_date`, `effective_date_status` | ISO date only if the statement explicitly supports it for the instrument or guideline. A reaffirmation can have a verified target and a null effective date. |
| `regime`, `targets[]` | Each target carries instrument, qualifier, unit and either a scalar value, lower/upper range, or null values for qualitative guidance. Mixed decisions may include multiple independent targets. |
| `source_url`, `source_document_type`, `source_document_title`, `content_type`, `content_sha256` | Exact original BOJ endpoint and digest of the bytes retrieved. The digest can identify changed snapshots across runs. Raw publisher files are omitted from artifacts. |
| `publication_date`, `publication_timestamp`, `publication_precision`, `publication_timezone`, `retrieved_utc` | The dated decision release supports day precision. Unknown publication times remain null. Retrieval time records when the runner received the response. |
| `publisher_connectivity`, `http_status`, `verification_status`, `reason` | Publisher response, document validation, and missing or contradictory evidence are separate. Failed document verification yields no numerical targets. |
| `periods[]`, `gaps[]`, `historical_completeness` | Modern archive reconciliation, unresolved dates, out-of-scope windows, and explicit historical gaps. |
| `revision_status`, `revision_of_sha256` | Reserved for source revision lineage. The initial audit records the retrieved digest and leaves historical vintages unresolved. An archived revision needs its own timestamp, digest, original provenance and relationship to any superseded release. |

Suggested observation key is decision date, instrument, qualifier and document digest. Retain conflicting evidence for investigation and prevent it from yielding a numerical observation. The source manifest contains reviewed assertions. The runtime requires agreement with independently parsed publisher bytes. No interpolation, market-rate substitution, or forward-fill is performed.

## Hosted verification

Review the separate workflow-only PR, then merge that PR manually. In GitHub Actions open **G7 Core Batch 1 audit (development)**, select **Run workflow** on `main`, and dispatch. Check the pinned checkout SHA, Poppler version, and automated test totals. Download the `g7-core-batch1-verification` artifact and inspect `boj_historical_policy_evidence.json`, especially document counts, unresolved reasons, and each annual date comparison. Keep the feature PR in draft. Green execution means the verifier ran and emitted receipts. Coverage and economic comparability must be assessed from the evidence before any registration.

`G7-JP-22` is unconfigured. Commercial rights are pending, and production approval is withheld. The development audit writes only to its supplied disposable output directory.
