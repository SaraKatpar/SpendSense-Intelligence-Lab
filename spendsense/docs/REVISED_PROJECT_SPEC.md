# SpendSense: authoritative rebuild specification

Updated with the user's dataset correction on 19 November 2026. This supersedes the earlier proposal implementation where the requirements differ.

## Hard constraints

- Use real source data only in model training and evaluation. No simulated, fictional, generated or Faker data, and no artificial users made from one household's time windows.
- No pretrained models, embeddings or OCR engines. The advice/logging chatbot alone may use a pretrained LLM through an API. Instructor approval is required before any exception to this rule.
- Train the categorizer, forecast, anomaly detector and personas from scratch in scikit-learn or PyTorch. Save artifacts and evaluation metrics to disk.
- Inspect actual dataset columns and provenance before preprocessing. Report missing data and unsupported features honestly; do not invent substitutes silently.
- Work one step at a time and report how to run/check each completed step before continuing to the next.

## Eligible sources and exclusions

1. **Daily Household Transactions:** existing 2,461-row downloaded file, audit in `eval/household_audit.json`. Use for note categorization, household forecast/anomaly experiments and separately reported recurring-payment/persona references. Preserve INR and the fact that it is one household with no user identifier. The publisher/source record still needs transparent provenance attribution.
2. **Berka PKDD'99 Financial:** CTU labels it Type Real. Use the original archived account.asc, trans.asc and order.asc. The full archive is CRC/SHA-256 verified. Original fractional CZK amounts/balances were compared with the integer-valued MariaDB copy; preserve original precision. MariaDB is comparison/fallback only, with bounded exports and validated counts. The partial transaction CSV was discarded. It is an account-level Czech banking reference, not a verified student dataset.
3. **Personas:** K-Means is built from Berka per-account spending profiles and Household Transactions data only. Do NOT use any Kaggle Student Spending Habits dataset: it is fictional. Before using any extra source, inspect its description and report whether it says synthetic, fictional, generated or simulated. Do not count household months as distinct people or pool unconverted monetary currencies.

The student spending datasets are dropped. The IEEE UPI behaviour survey is not used for spending-amount clustering. The optional Personal Budget Transactions dataset is **not approved or used**, because its real-data provenance is unverified. No extra dataset is needed merely to increase sample count.

## Berka policy fixed by the user

Berka amounts are CZK. Only scale-free model features (ratios, shares, training-fitted z-scores) are permitted; do not mix raw amounts into the PKR wallet or INR household models. All 183,114 missing-operation rows are PRIJEM/UROK in the original data. Retain and label them bank_generated/unknown_operation without imputing operation; exclude them from spending, anomaly and persona features, but retain them for balance/cash-flow calculations. See DATA_AUDIT.md and app/data/berka_policy.py.

## Models and shared application services

- Categorizer: TF-IDF + Logistic Regression, compared with Naive Bayes. Report accuracy and per-class F1. Resolve rare/conflicting labels and split leakage explicitly; do not reuse DistilBERT artifacts.
- Household forecasting may retain the separately specified from-scratch LSTM/baseline research plan. Berka instead uses monthly features only and the frozen low-balance protocol: continuous month-end balance/reference outflow primary target, selected binary event B/relaxed coverage secondary and exploratory, persistence/monthly pace baselines, gradient-boosting regression and logistic/gradient-boosting binary benchmarks. No Berka daily LSTM or GRU. No models are trained at this stage.
- Anomalies: from-scratch numeric-feature autoencoder with a validation-selected reconstruction threshold. Without true labels, report error/flag distributions and review results rather than invented accuracy/fraud precision.
- Personas: choose K using elbow/inertia and silhouette, then describe centroids. Weekend share and account-flow features may be observable. Food share, true subscription share and true savings rate are not directly supplied by Berka; resolve the feature definition before implementing that stage. Do not infer student identity from a bank account.
- Recurring payments: rules/statistics on repeated counterparty, similar amount and intervals. Use Berka standing orders as partial reference evidence and household transactions separately. Standing orders include loans, insurance and household payments; they are not all consumer subscriptions, and the order table has no execution dates.
- Receipt preparation: OpenCV only for grayscale, denoise, threshold, deskew/crop/text-region detection. STOP and ask which text-reading method the instructor permits before implementing OCR. Do not call Tesseract or EasyOCR in the rebuild.
- Chatbot: the only pretrained component, through an API with restricted tools such as add_expense, get_summary, get_budget_status and get_forecast, grounded in actual records.
- WhatsApp: a FastAPI/Flask webhook with an explicitly selected provider and user-provided credentials at that stage. Text/receipts and category corrections call the same service functions as the dashboard/chatbot. Images cannot complete text-to-logging until the permitted reading approach is chosen.
- Dashboard: Streamlit manual entry, monthly charts, allowance countdown, safe daily spend, budgets/alerts, forecast, anomalies, persona and recurring payments. SQLite holds users, transactions and budgets. No duplicated business logic between dashboard, webhook and chat tools.

## Sequence and project locations

1. Source/account audits completed and monthly low-balance v1 protocol frozen; source files are unchanged and training remains unauthorized.
2. Categorizer and SQLite.
3. Manual-entry dashboard.
4. Total-spend forecast and baselines.
5. Anomaly detection.
6. Personas and recurring-payment detection.
7. OpenCV preprocessing; stop before text reading.
8. WhatsApp webhook/provider integration.
9. Chatbot tools and advice.

Use `training/` for source/training scripts, `app/` for the revised application and shared services, and `eval/` for audit/evaluation outputs. Existing top-level legacy app modules and artifacts are not evidence of compliance with this specification. APK packaging remains a later delivery task after its connected backend meets these rules.

## Provenance references

- CTU source: https://relational.fel.cvut.cz/dataset/Financial
- Original archive supplied by user: https://web.archive.org/web/20070214120527/http://lisp.vse.cz/pkdd99/DATA/data_berka.zip
- Original documentation: https://web.archive.org/web/20180506035658/http://lisp.vse.cz/pkdd99/Challenge/berka.htm

Source pages are archived locally under the task's `work/berka_source/` for inspection. Public availability does not itself establish redistribution licensing.

## Current frozen low-balance contract

The current authoritative definition, fixed 832-account registry, relaxed policy, 5% threshold, monthly-only features, bootstrap plan and unchanged account/time split are timestamped and hashed in app/data/low_balance_protocol_v1.json. See docs/DATA_AUDIT.md (DATA_AUDIT.md in this directory). The classifier is exploratory because only 7 positive test account-months are observed. No training or test tuning occurred. Previous alternative definitions and coverage experiments are retired to eval/history. Month-end prediction warnings and earlier-month observed events are distinct outcomes. All 832 accounts remain in the registry, with explicit target availability; do not claim every account can be scored inside the unchanged split.


## Later user-authorized modeling run

The user subsequently authorized the frozen Berka monthly benchmark. Account-grouped forward CV on pooled original train+validation periods selected configurations before a single locked test prediction pass. Frozen definitions, 5% thresholds, relaxed coverage, 832-account membership and account/time assignments were not changed. The trained artifacts and evaluation are documented in eval/berka_modeling_v1/REPORT.md; the event classifier remains exploratory, all 193 unscorable accounts are explicitly reported, and models are not evidence of validation on modern students. Earlier no-training wording is a dated stage boundary, superseded solely for this authorized experiment.


## Latest ordered work supersedes older scope where specified

Step 1 now includes the existing personal-reference source alongside household and eligible Berka development accounts. Use the name spending-mix clusters; the documented comparable features are debit timing/concentration, with fixed K=3 and entity-weighted fitting. The latest request explicitly calls for DistilBERT candidates versus TF-IDF+LR on a shared untouched benchmark (step 5); older pretrained-exclusion wording does not override that request. No Berka models are deployed or re-scored on the frozen test. See SPENDING_MIX.md and ORDERED_WORK.md.
