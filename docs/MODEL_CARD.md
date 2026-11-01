# Model Card — retail-v1 🤖

This document explains what the machine learning model does, how it was trained, and where it works best.

---

## 1. What Does This Model Do?

- **Goal:** Predict whether an existing store customer will make at least one purchase in the next 30 days.
- **Input:** 11 customer shopping habits (how recently they bought, how often they buy, how much they spent).
- **Output:** A probability between 0% and 100% showing how likely the customer is to buy again.

---

## 2. How Was the Model Trained?

We split the 2-year dataset by time so the model never cheats by seeing future data:

- **Training period (June 2010 to February 2011):** The model studies past purchases to learn patterns.
- **Validation period (April 2011 to June 2011):** Used to test different algorithms and pick the best decision threshold (0.27).
- **Test period (August 2011 to November 2011):** Completely untouched data used to calculate the final report card scores.

### Why Histogram Gradient Boosting Won:
We compared 3 approaches:
1. **Simple baseline (prior guess):** Just guessed the average rate for everyone.
2. **Logistic Regression:** A good simple baseline, but struggles with non-linear patterns.
3. **Histogram Gradient Boosting (Winner):** Builds small decision trees step-by-step. It handled features like "days since last order" and "order gaps" best and scored the highest.

---

## 3. Practical Limitations to Keep in Mind

1. **One specific store:** The data comes from a UK giftware shop between 2009 and 2011. A modern fashion store or grocery shop will have different shopping patterns.
2. **Anonymous customers:** Orders without a customer ID cannot be used for predictions (since we don't know who bought them).
3. **High score does not mean "send a discount":** A customer with a 90% score will probably buy anyway without any coupon. In marketing, you often want to target customers in the middle who need a gentle reminder.
4. **No holidays or seasons included:** Holiday spending in November/December is much higher than February. The model does not currently have seasonal features.

---

## 4. How to Use This in a Real Company

If deploying this in a live business:
1. Connect the pipeline to your live database instead of historical Excel files.
2. Set up a regular retraining schedule (e.g., retrain the model once every month using the latest data).
3. Monitor performance over time to make sure the predictions stay accurate as customer tastes change.
4. Run a simple A/B test on marketing campaigns to measure real extra sales caused by outreach.
