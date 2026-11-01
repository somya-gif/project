# Retention Lens — detailed walkthrough for Sumit Gole

## 1. Humne kaunsi problem solve ki?

Business ke paas past sales hain. Ab do questions hain: “Sales aur customer retention kaise perform kar rahe hain?” aur “Kaunsa existing customer agle 30 din mein dobara purchase kar sakta hai?” Pehle question ke liye descriptive analytics aur Power BI; doosre ke liye supervised machine learning aur Streamlit.

Example: customer 12345 ne pichhle kuch mahino mein multiple orders kiye. Prediction date par hum us date tak available history dekhte hain. Model probability deta hai—maan lo 0.62. Iska interpretation estimated 62% repeat-purchase likelihood hai, guarantee nahi. Yeh example number hai; app mein actual customer ka computed score dikhta hai.

Project historical UK giftware business par hai, modern Indian grocery store par nahi. Currency GBP hai. Source mein wholesale customers bhi hain. Is context ko interview mein clear rakhna.

## 2. Dataset aur grain samjho

UCI Online Retail II mein 1,067,371 raw rows hain, December 2009 se December 2011 tak. Har row ek invoice ka product line hai. Ek order mein 10 products hain toh 10 rows ho sakti hain. Isliye row count ko order count kehna galat hai.

Three grains yaad rakho:

- Transaction line: ek invoice mein ek product line.
- Order: invoice ki lines ko aggregate karke ek purchase.
- Customer snapshot: ek customer ko ek prediction date par represent karne wali row.

ML ki ek row customer snapshot hai. Same customer different months mein multiple rows bana sakta hai. Customer ki recency, total orders aur next-30-day outcome har snapshot mein change ho sakte hain.

Original workbook ZIP mein included nahi hai, lekin download code, attribution, checksum aur actual processed data included hain. GitHub version mein customer-level CSVs excluded hain; first setup par pipeline run karke data regenerate karna required hai.

## 3. Cleaning mein kya decisions liye?

`src/features.py` ka `quality_and_clean` function full raw data receive karta hai. Column names normalize hote hain, date parse hoti hai, numeric values validate hoti hain aur duplicate rows remove hoti hain. 34,335 exact duplicate rows remove hui. Important nuance: line-level ID nahi hai, isliye duplicate removal ek heuristic hai—kuch genuine identical lines bhi ho sakti hain. Real business mein ingestion logs aur source keys verify karne honge.

Positive quantity aur positive price wali non-cancelled lines purchase sales banati hain. Negative quantity with positive price credit banata hai. Invoice ka C prefix cancellation signal hai. Missing date, invalid quantity/price ya other unusable lines audit mein count hote hain.

Missing customer ID ko zero ya arbitrary customer ID se replace karke ML mein nahi daalte. Aisa karne se sab anonymous purchases ek fake customer ban jayenge. Anonymous sales financial totals mein rehti hain; customer features aur retention se exclude hoti hain.

Observed gross invoiced sales roughly £20.48 million hain; credits roughly £1.46 million; net invoiced sales roughly £19.01 million. Yeh profit nahi, kyunki cost data nahi hai. Shipping/postage type valid positive invoice lines remain kar sakti hain. Business definition invoiced sales hai.

## 4. Target exactly kaise banta hai?

Cutoff date T maan lo. Existing customer ka matlab T se strictly pehle at least one positive invoice. Label 1 tab hai jab `[T, T + 30 days)` mein purchase ho. Otherwise label 0—sirf tab jab poora outcome window data mein available ho.

Square bracket ka matlab start included; round bracket ka matlab end excluded. Example: 1 February 2020 se 30 days ka end 2 March 2020 hai. Exactly 2 March par hua purchase is label mein count nahi hoga. Test suite mein yahi boundary verify hoti hai.

Last source day partial hai. Isliye 9 December 2011 ki midnight ko reliable observation boundary maana. Latest scoring isi date par hai, aur future 30-day outcomes available nahi hain. Latest predictions par accuracy claim nahi karte. Evaluation earlier mature snapshots par hoti hai.

## 5. Leakage kya hoti hai?

Leakage ka matlab model ko training/evaluation mein aisi information milna jo actual prediction time par available nahi hoti. Example: June 1 ka score predict karte waqt June 15 ka order total spend mein add kar diya. Model future dekh raha hai; offline score artificially improve ho sakta hai.

Hum `orders.order_date < cutoff` filter **features banane se pehle** lagate hain. Lifetime spend ka matlab dataset ke end tak spend nahi, current cutoff se pehle observed spend hai. Features aur labels alag windows se aate hain. Test future revenue badal kar verify karta hai ki current features unchanged rahen.

StandardScaler logistic pipeline ke andar fit hota hai aur training rows par hi learn karta hai. Customer IDs feature matrix mein nahi hain. Snapshot date model feature nahi hai.

## 6. Features ka intuition

Recency: customer ne last purchase kitne din pehle kiya? Frequency: total aur recent orders kitne hain? Monetary: total aur recent positive spend kitna hai? Ye RFM-related signals hain.

Tenure batata hai first observed order kitna purana hai. Average order value basket size ka proxy hai. Mean gap historical order spacing ka rough summary hai. Single-order customer ke paas gap calculate nahi ho sakta, toh -1 sentinel use kiya hai; model ko repeat-gap missingness ka consistent signal milta hai.

Active months help distinguish purchases clustered in one burst vs several observed months. `is_uk` latest pre-cutoff purchase country se derived hai. Feature dictionary mein exact formulas hain. Ye associations hain, reasons ka causal proof nahi.

## 7. Train/validation/test kyun alag?

Training par model patterns seekhta hai. Validation par model choice aur threshold decide hota hai. Test final unseen future-period estimate deta hai. Hum random split nahi karte, kyunki target time-dependent hai.

| Split | Snapshot months | Use |
|---|---|---|
| Train | June 2010–February 2011 | Fit weights/trees |
| Validation | April–June 2011 | Choose candidate and threshold |
| Test | August–November 2011 | Final evaluation |

Partitions ke beech gap ensure karta hai ki training ka 30-day outcome validation mein overlap na ho. Same customer future split mein aa sakta hai: existing customer ka future predict karna hi intended use hai. Customer ID memorization avoid hoti hai kyunki ID feature nahi hai.

Within a split monthly windows kabhi overlap kar sakti hain, aur customer repeated hai. Isliye rows independent people nahi hain. Hum unsupported confidence interval claim nahi karte. More advanced extension customer-clustered uncertainty aur rolling forward-validation hogi.

## 8. Teen models kyun?

Dummy baseline training purchase rate ko sabko score deta hai. Isse pata chalta hai ki ML useful information seekh raha hai ya bas majority behaviour repeat kar raha hai.

Logistic regression simple linear baseline hai. Feature scaling ke baad weighted combination se probability deta hai. Fast aur interpretable baseline hota hai, lekin complex nonlinear relationships capture karne mein limited ho sakta hai.

Histogram gradient boosting sequential small decision trees fit karta hai. Har stage previous errors improve karti hai. Nonlinear effects aur feature interactions handle kar sakta hai. Is project mein validation average precision ke basis par ye select hua. Test data ko selection ke liye use nahi kiya.

Model training ke baad refit nahi kiya gaya. Bundled model exactly evaluated fit hai. Latest customer features fresher history use karti hain, weights same rehte hain. Real deployment mein retraining cadence separately define karni hogi.

## 9. Metrics ko correctly explain karo

Test prevalence 20.81% hai. Agar har row par “no purchase” bol dein, apparent accuracy high ho sakti hai, lekin buyers identify nahi honge. Isliye accuracy primary metric nahi rakhi.

**Average precision 0.5569:** Different score thresholds par precision/recall ranking summarize karta hai. Ye accuracy nahi aur “55.69% customers correct” bhi nahi. Base rate reference 20.81% hai. Here AP means sklearn average precision, not a separately computed trapezoidal PR area.

**Precision 52.98%:** Threshold 0.27 par predicted-positive snapshots mein approximately 53% actual buyers hain. **Recall 50.37%:** Actual future buyers mein approximately half identify hote hain. **F1 0.5164:** Precision aur recall ka harmonic mean.

**ROC AUC 0.7906:** Randomly selected positive ko negative se higher rank dene ki tendency summarize karta hai. **Brier 0.1299:** Probability aur actual 0/1 outcome ke squared error ka mean; lower better. Reliability bins mein predicted mean aur observed rate compare kar sakte ho. Probability calibrated hai, yeh blindly claim nahi karna.

**Top-decile precision 65.33% aur lift 3.14×:** Highest-scored 10% pooled test snapshots mein purchase concentration overall base rate se 3.14 times hai. Yeh causal sales increase nahi. Per-month lift export bhi diya hai, kyunki campaign normally ek date par run hota hai.

Confusion matrix: TN 15,019; FP 1,999; FN 2,219; TP 2,252. Total 21,489 customer-snapshot rows. Threshold 0.27 validation F1 se choose hua; threshold 0.5 automatically best nahi hota. Business cost information mile toh threshold policy change ho sakti hai, with new validation.

## 10. Retention ka common confusion

Maan lo January mein 100 customers aur February mein 80 customers buy karte hain. January ke 40 customers February mein return hue. February retention 40/100 = 40% hai. February ke 80 active customers mein se 60 pehle kabhi buy kar chuke hain, toh returning-customer share 60/80 = 75% hai. Ye same metric nahi.

Cohort ka matlab customers ko first observed purchase month se group karna. January cohort ke 100 customers mein March mein 25 buy karein toh month-2 cohort retention 25% hai. February skip karke March return allowed hai; ye survival analysis nahi.

Future/unobserved cohort cell blank hona chahiye, zero nahi. Zero ka matlab observed month mein no purchases. Dataset start se pehle customer history missing ho sakti hai, isliye “first observed” bolte hain, true acquisition nahi.

## 11. Power BI pipeline ka flow

Python validated CSVs export karta hai. Power Query in CSVs ko typed tables mein import karta hai. Calendar se Sales/DailySales ko date relationship milti hai. Customers se Sales/Predictions ko customer relationship milti hai. Retention/cohort aggregates apni independent grain par rehte hain.

DAX measures filters ke context mein calculate hote hain. Sales month slicer se gross/net/order metrics change hote hain. Prediction snapshot fixed historical date hai; sales month slicer ko prediction date badalne ka illusion nahi dena chahiye.

Five pages: Sales, Retention, Cohorts, Predictions, Evidence. Editable definitions present hain. Actual Desktop opening, refresh, visual checks aur PBIX Save As pending acceptance steps hain—generated source ko tested PBIX kehna incorrect hoga.

## 12. Streamlit interview demo

Sales overview se start karo. Customer prediction page par ID select karo. App trusted model artifact load karta hai, snapshot features leta hai aur `predict_proba` run karta hai. Probability, binary threshold decision aur past orders show hote hain. Customer-level causal explanation claim nahi hota.

Campaign page par high likelihood filter select karke audience CSV download kar sakte ho. CSV upload mein sirf known customer IDs chahiye. Unknown IDs blank score return karte hain, zero score nahi. ID lookup is snapshot batch lookup; arbitrary new store transactions score nahi karta.

Model evidence page par validation candidates, test-month performance, probability reliability aur permutation importance dikhao. Importance feature shuffle karne se AP decline measure karti hai. Correlated features importance split kar sakti hain.

## 13. Engineering issue jo testing ne catch kiya

CSV parse hone par tiny floating-point differences tree split boundary cross kar sakte hain. Initial test mein 5,877 customer scores mein 2 mismatch hue. Solution: inference CSV reader mein `float_precision='round_trip'`. Tolerance badha kar issue hide nahi kiya. Test all exported scores ko model output se match karta hai.

Other tests: complete-window eligibility, inclusive/exclusive date boundary, no future features, missing-ID treatment, duplicate/credit handling, revenue reconciliation, cohort maturity, split separation, every Streamlit page and empty audience. CI workflow repository mein added hai; remote GitHub run abhi execute nahi hua.

## 14. Short interview answers

**Why not deep learning?** Tabular behavioural features aur modest customer sample ke liye strong classical baselines useful hain; compute aur complexity low rakhi. No evidence justified a deep model here.

**Is this churn prediction?** Specifically 30-day repeat-purchase propensity. No purchase in that window permanent churn prove nahi karta.

**Why customer can be in train and test?** Existing customers ka later behaviour score karna deployment objective hai; time order and feature cutoff respected hain. New-customer generalization alag experiment hoga.

**Why no customer ID feature?** Identity arbitrary hai; memorization aur poor generalization ka risk. ID joining/display ke liye hai.

**What happens to cancelled orders?** Positive cancelled invoice lines purchase target mein nahi; valid negative lines credits hain. Future refunds ke basis par historical event rewrite nahi hota.

**How would you improve?** Source-quality review, duplicate sensitivity, seasonal features, rolling temporal validation, probability calibration on a dedicated time block, mature-label monitoring and real campaign randomized tests. Improvement claim tabhi jab measured result support kare.

**Is it industry-ready?** Industry-style portfolio foundation with reproducibility, leakage controls, audit and tests. Production deployment, access controls, ongoing monitoring, business validation and Desktop PBIX acceptance abhi additional work hain.

## 15. Ab practice kaise karna hai?

Pehle README se app run karo. Ek customer choose karke recency/order count/history manually reconcile karo. Phir metrics JSON kholo aur precision/recall explain karo. Power BI checklist complete karke actual PBIX save/reopen karo. Last mein 3-minute video record karo aur historical nature plus limitations honestly mention karo.
