# Fresh Kaggle training — 18 November 2026

## Selected and downloaded

| Dataset | Source card license | Use |
|---|---|---|
| [Personal Finance](https://www.kaggle.com/datasets/entrepreneurlife/personal-finance) by entrepreneurlife | MIT as reported by Kaggle metadata | 806 dated records, 617 retained debit expenses after removing credits and card-payment transfers. Train separate reference LSTM, autoencoder and monthly-window K-Means; supply additional text labels for classification. |
| [Daily Household Transactions](https://www.kaggle.com/datasets/soumojit11/daily-household-transactions) | CC0 as reported by this Kaggle publisher | Direct download matches the already bundled 2,461-row source. This is provenance confirmation, not 2,461 new examples or a second household. |

Licenses above are the dataset publishers’ metadata declarations, not independent proof of original collection rights. Full selected source metadata, cleaned data, dates and SHA256 checksums are in data/kaggle. Publisher describes Personal Finance as real-world personal records; that claim is not independently verified. The file does not explicitly store currency. Preserve **UNSPECIFIED_SOURCE_UNITS**; do not relabel it PKR or combine its amounts with INR/PKR time series.

## Data-quality decisions

- Excluded all Credit Card Payment rows regardless of debit/credit to avoid double counting transfers.
- Retained positive, mapped debit expense records, with one explicit reference-history identifier. Account names are not treated as different people.
- Normalized descriptions with the same NLTK preprocessing used by the classifier.
- Removed 20 conflicting text descriptions from the classifier corpus; monetary reference histories are not removed merely because text labels conflict elsewhere.
- Combined only text/category examples across sources for DistilBERT. Amounts and currencies never enter the text classifier.
- Rejected monthly snapshots for daily forecasting, random sentence/category pairs for classification and intentionally dirty mixed-currency synthetic examples for clean model training. Candidate audit lists exact source references and reasons.

## Training actually executed

```powershell
python training/fetch_kaggle_training.py
python training/train.py --csv data/kaggle/personal_reference_clean.csv --model forecast --epochs 30 --output models/kaggle_reference
python training/train.py --csv data/kaggle/personal_reference_clean.csv --model anomaly --epochs 25 --output models/kaggle_reference
python training/train.py --csv data/kaggle/personal_reference_clean.csv --model personas --output models/kaggle_reference
python training/train.py --csv data/kaggle/categorizer_training.csv --model categorizer --epochs 3 --output models/kaggle_categorizer
python training/evaluate_kaggle.py
```

No external paid API is used. openpyxl is a lightweight supporting dependency required to read the selected XLSX download. Training retains the proposal’s DistilBERT, LSTM, autoencoder and K-Means architectures. Tesseract is pretrained; receipt extraction is not a new neural model trained on these financial CSVs.

## Actual held-out results

- DistilBERT: 263 unique held-out descriptions, accuracy **76.05%**, macro-F1 **0.500**. The new split differs from the old split; do not call this a head-to-head improvement. Existing reference remains default; opt into the candidate in My wallet → Settings.
- LSTM: 128 chronological rolling one-day evaluation days, category-day MAE **25.65** and RMSE **278.32**, versus seven-day-mean baseline MAE **29.80**, RMSE **298.29**. Units are unspecified source units. High RMSE shows sensitivity to large spikes. Recursive 30-day totals are separately reported in forecast.json.
- Autoencoder: stored calibration threshold and error quantiles in models/kaggle_evaluation.json. No verified anomaly labels, so no fraud accuracy or precision/recall claim.
- K-Means: 21 monthly windows from one reference history, silhouette **0.304**. This clusters months, not a student population. Generic Balanced Mix labels are retained when learned centers do not support a stronger description.

## In-app access and deployment boundary

Insights → Research & model evidence → New Kaggle training results shows these metrics and a 14-day forecast anchored immediately after the historical source. Settings can select the newly trained text classifier. Monetary candidates never substitute into the live PKR survival planner. All saved artifacts and source/preprocessing/evaluation scripts are included in the package; personal database and optional Llama weights are excluded.

Kaggle makes licensed reference training possible, but these downloads still do not establish independent Pakistani-student validation. Missing-date zero filling depends on unverified logging coverage. Do not claim that an outside reference forecast establishes the accuracy of a student’s real allowance prediction.


Current clustering supersedes earlier reference personas: see ../eval/spending_mix_v1/REPORT.md. The shared untouched categorizer benchmark remains pending; prior classifier results are not a head-to-head comparison.
