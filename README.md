

Can we predict which customers will come back and buy again?

This project answers that question using real transaction data from a UK online store (~1 million orders over 2 years). It uses Machine Learning to predict whether an existing customer will buy something again in the next 30 days.

![Evaluation Summary](docs/Measured_Evidence.png)

---
What Does This Project Do?

1. Cleans messy sales data** — removes duplicate lines, separates returned orders from real purchases, and fixes missing customer numbers.
2.  Creates smart customer signals — checks how recently each person bought, how often they buy, and how much money they spent (without peeking into the future).
3. Train machine learning models — compares 3 different models and picks the best one (Gradient Boosting).
4. Shows results in a web app — an interactive Streamlit website where you can see sales trends, check any customer's score, and download customer lists for marketing campaigns.

---

How Well Does the Model Work?

 tested the model on 4 months of completely unseen future data (August to November 2011). how it  waas performed:

| What we measured | Model score | What this means in plain words |
|---|---:|---|
| **Base Rate** | 20.8% | In normal times, only about 21 out of 100 customers come back to buy within 30 days. |
| **Top 10% Lift** | **3.14×** | Customers in the model's top 10% list are **over 3 times more likely to buy** than average. |
| **ROC AUC** | **0.791** | When comparing a buyer and a non-buyer, the model correctly ranks the buyer higher ~79% of the time. |
| **Precision** | **53.0%** | When the model says "this person will buy", it is correct 53% of the time (more than double the 21% baseline). |
| **Recall** | **50.4%** | The model catches about half of all repeat buyers. |

---

What is data leakage?  
It happens when a model accidentally "sees the future" during training. For example, if you are predicting what a customer will do in July, you cannot use their August purchases to help make that prediction.

How i prevented it:
- **Time Gaps:** We trained on older data (2010 to early 2011) and tested on newer data (late 2011). We left a gap between them so windows never overlap.
- **Strict Cutoffs:** When calculating customer stats, the code strictly ignores any order placed after the cutoff date.
- **Automatic Test:** We have a test in `tests/test_features.py` that intentionally changes future data and proves that past numbers stay 100% unchanged.

---
 Quick Start (How to Run It on Windows)
only need Python installed.
Double-click `START_WINDOWS.bat`, or run these 4 commands in your terminal:

```powershell
# 1. Create and turn on a virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install the required libraries
pip install -r requirements.txt

# 3. Download the data and train the model (takes ~3 minutes on first run)
python -m src.pipeline

# 4. Open the web dashboard
streamlit run app.py
```

Your browser will automatically open to `http://localhost:8501`.

---

 How to Run Tests

To make sure all calculations and leakage checks pass:

```powershell
python -m unittest discover -s tests -v
```

 Data Source

This project uses the public **Online Retail II** dataset from the UCI Machine Learning Repository:  
Chen, D. (2012). [UCI Repository Link](https://doi.org/10.24432/C5CG6D) (CC BY 4.0).
