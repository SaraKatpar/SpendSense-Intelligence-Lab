# SpendSense: revised constraints and step 1

The user supplied a revised specification on 19 November 2026. It supersedes the earlier ML design: only real datasets, no pretrained models except the advice/logging LLM, from-scratch scikit-learn/PyTorch models, and a step-by-step build with an explicit stop before choosing text-reading/OCR technology.

## Current boundary

The earlier running application, stored model artifacts and old evaluation reports do not meet this revised specification. Known generated sources and derived artifacts are now retired outside the project; other legacy work is not treated as compliant rebuilt evidence. In particular, DistilBERT categorization, Tesseract OCR, fictional campus data, synthetic student profiles and any models/metrics derived from them are excluded from the revised training and evaluation pipeline. No data has been regenerated to replace missing real samples. Private records and real original source datasets are preserved; known generated transaction rows were removed after a full backup, with all other transaction rows verified unchanged.

The ordered work now includes a compiled, development-signed connected Android APK, built after steps 1–3 passed. SDK archives were completed and verified against freshly fetched official metadata. See ../eval/mobile_apk/REPORT.md and ORDERED_WORK.md; physical Android execution remains unvalidated.

## Step 1: inspected household file

`data/household_original.csv` and the downloaded Kaggle copy have 2,461 rows and eight actual columns: Date, Mode, Category, Subcategory, Note, Amount, Income/Expense, Currency. This is one more column than the seven listed in the revised prompt; the observed currency column says INR. Source identity does not independently prove that the underlying collection is real.

Observed quality issues: 635 missing Subcategory values, 521 missing Note values, nine identical full rows, and 24 distinct normalized nonempty notes assigned to more than one raw Category. All amounts are positive and parse as numbers; the range is INR 2 to INR 250,000. Income/Expense contains 2,176 Expense, 160 Transfer-Out and 125 Income rows. Transfers and income must not be silently mixed into an expense-only target.

Dates parse with a day-first mixed-format audit check from 1 January 2015 to 20 September 2018. There are 896 observed dates over 1,359 calendar days. Missing calendar dates do not prove zero spending or complete logging. The file has no account/user ID; payment Mode is not a person identifier. This household history cannot supply cross-user persona validation by inventing users or splitting one person's months into independent people.

No general category mapping, duplicate removal, imputation, train/test split, zero-fill or model training has been implemented for this revised pipeline. The user-approved Berka record-role/eligibility policy is now implemented in app/data/berka_policy.py and checked on original real rows; it preserves raw files. Audits and policy checks are saved under eval/.

## Source status and remaining provenance

- Berka original account/trans/order files are now completely downloaded, checksum/CRC verified and inspected. The original ASC source was selected after comparing precision with MariaDB; the partial transaction CSV was deleted. Missing-operation policy and CZK-only/scale-free feature restrictions are documented in DATA_AUDIT.md.
- The user has explicitly dropped the student spending dataset. Neither the fictional 1,000-row file nor the unverified 105-row survey is eligible for the revised pipeline. Personas use Berka account profiles; the single household can provide a separately reported reference, not invented additional people.
- Original household source/collection documentation, if available, to support the real-data-only provenance requirement.

## Reproduce this audit

From `spendsense`:

```powershell
../.venv/Scripts/python.exe training/inspect_real_data.py --csv data/household_original.csv --output eval/household_audit.json
```

Inspect `eval/household_audit.json` for source hash, actual columns, data types, missing values, label distributions and date/text/amount summaries. The script reads the source and never rewrites it.

The requested Berka source/schema/precision/policy inspection is complete. Continue the next preprocessing/categorizer/SQLite stage separately, preserving the revised rules. Later stages follow the supplied order. Receipt work must stop after OpenCV preprocessing and ask the user which text-reading approach the instructor permits. WhatsApp provider/account setup and the chatbot API need the user's selected service and credentials; no provider messages have been sent or secrets requested in this step.


## Frozen monthly low-balance protocol

The user selected low-balance event B (balance below 5% of prior typical monthly outflow before month end) with relaxed coverage. The timestamped, hashed v1 contract is in app/data/low_balance_protocol_v1.json, with documentation in DATA_AUDIT.md and eval/berka_low_balance/REPORT.md. The binary event classifier is exploratory: the fixed 832-account cohort has 7 positive test account-months. A separate continuous primary target is exact month-end balance/reference outflow; thresholding its prediction creates a month-end warning, not the same outcome as an earlier observed event. Berka features are monthly only; no daily LSTM/GRU. No model training is authorized or performed. All 832 accounts remain registered, but exact targets exist in the assigned periods for only 639; missing cases must be reported rather than invented. Prior competing proposals are historical only.


## Training authorized and completed after the freeze

The latest user instruction authorized from-scratch Berka monthly regression and an exploratory B classifier. The original protocol JSON and all definition/threshold/cohort/split hashes are unchanged. A separate training authorization/plan records pooled development account-grouped forward CV, configuration locking and the single final test prediction pass. Four final bundles were fitted: linear regression, ridge, shallow regression gradient boosting and heavily regularized five-feature logistic regression. The binary booster failed the predeclared development gate and was not retained/tested. See eval/berka_modeling_v1/REPORT.md, LIMITATIONS.md, verification.json and the one-pass ledger. Primary full-target errors and the 193-account selection-bias analysis must be reported; no claim of reliable student event classification is supported. Earlier no-training statements describe the prior freeze stage.
