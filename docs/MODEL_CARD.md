# Model card · retail-v1

## Intended use

Portfolio demonstration of existing-customer purchase propensity in a historical UK giftware business. Input: positive invoice history strictly before a cutoff. Output: probability of at least one further positive invoice in 30 days. This is not a new-customer model, permanent-churn model, fraud model or causal marketing-uplift model.

## Development and validation

- Training snapshots: monthly, June 2010–February 2011.
- Validation snapshots: April–June 2011.
- Held-out test snapshots: August–November 2011.
- Training outcome windows finish before validation starts; validation outcome windows finish before test starts. Chronological gaps remove overlapping labels across partitions.
- Some 30-day windows within a partition overlap (calendar months can be shorter than 30 days); repeated customer rows are dependent. Reported snapshot metrics are descriptive, without unsupported IID confidence intervals.
- Customers may occur in all splits. This matches the intended existing-customer task; random row splitting was not used. IDs are not features.
- Three candidates: prior-probability dummy, standardized logistic regression, histogram gradient boosting.
- Selection: validation average precision. Gradient boosting won. Hyperparameters were fixed before test; no search on test.
- Decision threshold: 0.27 selected using validation F1. It is illustrative until costs/budgets are supplied. Descriptive likelihood bands use separate fixed thresholds 0.20 and 0.50.
- Model is not refit after evaluation: the bundled weights are exactly the tested training fit. A deployed model should have a defined, revalidated retraining schedule.
- Latest demo scoring date: 2011-12-09, using all history strictly before midnight. This latest window is unobserved and is never included in reported test metrics.

See `artifacts/metrics.json` for exact candidate and monthly results; `calibration.csv` for reliability bins; `data_quality.json` for row accounting; `provenance.json` for input checksum and environment. Exported probabilities must be read with round-trip floating-point parsing for inference parity.

## Material limitations

1. Dataset is old, one retailer and mixed retail/wholesale. Modern stores, geographies and categories may have different behaviour.
2. Full-row deduplication is a heuristic without a source line ID. Duplicate-line sensitivity has not been benchmarked.
3. Missing customer IDs are excluded from prediction and retention, creating selection bias. Their financial sales remain counted.
4. Features use observed positive revenue, not net revenue. A purchase later refunded still counts as a repeat purchase. Credits lack reliable original-invoice matching.
5. First observed purchase is not necessarily acquisition. Existing customers before December 2009 are left-censored.
6. No explicit seasonal calendar feature is included. Test months differ seasonally from validation; month-level evaluation is provided. Do not assume year-round stability.
7. Probabilities are not separately calibrated; Brier score/reliability bins are diagnostics, not proof of perfect calibration.
8. No customer-level SHAP or causal explanations are provided. Global permutation importance is validation sensitivity, affected by correlated features.
9. Low repeat probability does not imply discount responsiveness; high repeat probability can represent people who would buy anyway. An A/B test or an uplift model with treatment data is needed to estimate incremental value.
10. No authenticated multitenant app, customer consent system, online feature store, automated refresh, production monitoring or operational service-level agreement is implemented.

## Operational design before real use

Replace historical demo data with an authorized store feed and versioned ingestion. Use a stable line-level transaction key, capture timezone, distinguish refunds/returns/cancellations and agree the target business event. Backfill mature outcomes, validate joins, and establish exact customer eligibility. Prefer daily point-in-time scoring with an immutable snapshot ID and model hash.

Monitor missing-ID rates, invalid values, data delay, feature distributions (especially recency, order count and spend), score distribution, and daily audience count. Compare to versioned baseline distributions; thresholds are business-specific, not fabricated here. After the 30-day window closes, compute AP, Brier score, precision/recall at the chosen threshold and budget-based lift. Review breakdowns by market, tenure and activity level, subject to sufficient sample size. Monitor changes in customer composition as well as metrics.

Retraining should use only mature labels and forward validation. Keep the prior artifact for rollback and require reproducible metrics and inference-parity tests before promotion. Establish access controls, retention policy and audit logs for actual customer data. Validate Windows Power BI rendering and PBIX export independently from Python tests.
