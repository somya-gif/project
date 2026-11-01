# Model card — retail-v1

## Purpose

Predicts whether an existing customer will make at least one purchase in the next 30 days, based on their historical order behaviour. Built on the UCI Online Retail II dataset (UK giftware, Dec 2009–Dec 2011).

## Training setup

- **Train:** monthly snapshots, June 2010–February 2011
- **Validation:** April–June 2011 (model selection + threshold)
- **Test:** August–November 2011 (final evaluation only)
- Chronological gaps between splits prevent label leakage
- Three candidates compared: dummy baseline, logistic regression, histogram gradient boosting
- Selected on validation average precision; threshold 0.27 maximizes validation F1

## Key limitations

1. Single old dataset — one UK retailer, mixed retail/wholesale. Results may not transfer to other businesses.
2. Missing customer IDs are excluded from prediction, creating selection bias.
3. Features use gross revenue (refunds still count as purchases).
4. No seasonal features included; test months differ seasonally from validation.
5. Probabilities are not separately calibrated.
6. No customer-level explanations — global permutation importance only.
7. High/low probability does not imply discount responsiveness. An A/B test is needed for uplift estimation.

## Production considerations

For real use: replace demo data with a live feed, add a stable transaction key, implement retraining with mature labels, set up monitoring (feature drift, score distribution, outcome metrics), and add proper access controls.
