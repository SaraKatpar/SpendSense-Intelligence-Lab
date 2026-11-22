# SpendSense: Technical Evaluation and Improvement Report

**Review date:** 18 November 2026  
**Purpose:** External academic evaluation, technical critique and improvement planning  
**Scope:** Current local Streamlit implementation and saved model artifacts  
**Review type:** Evidence-based technical self-assessment, not independent certification

## 1. Executive assessment

SpendSense is a working local semester-project prototype with genuine trained ML components, persistent expense records, receipt extraction, deterministic allowance planning, purchase simulations and a local conversational model. It is more substantial than a dashboard or chatbot wrapper. However, it is not yet a validated student financial-advice product or a production-ready multi-user service.


Concrete correctness gaps also remain. This review reproduced unknown currency on a dollar order, acceptance of a foreign-currency CSV without unit enforcement, mixed relative dates being assigned one date, and inconsistent rounding between a ledger entry and cash adjustment. These are open findings, not fixes completed by this report.

Local Llama chat is real and has produced live responses. It is pretrained, not fine-tuned on financial records. Its first live affordability test gave incorrect advice before stronger grounding was added; subsequent examples passed. Prompt improvements are not a mathematical guarantee. The financial calculator must remain authoritative.

**Recommended status:** Suitable for a clearly labelled academic demonstration with explicit limitations. Not ready to be described as accurate financial advice, autonomous monitoring, a bank-connected account or a secure public/mobile service.

## 2. Review scope and evidence quality

Reviewed files include app.py, storage.py, campus.py, survival.py, ml.py, capture.py, shopping.py, receipt_ocr.py, coach.py, student_styles.py, intelligence.py, ai_chat.py, training scripts, model reports, dataset metadata and tests. The original supplied archive was inspected earlier: it was a Tkinter/local-records application rather than the final five-model Streamlit system.

This report distinguishes:

- **Executed evidence:** Saved training/evaluation results, the latest complete 34-test run, prior live local-model replies and targeted checks performed for this report.
- **Code finding:** Behaviour evident from implementation, without necessarily reproducing an entire browser or production failure.
- **Research limitation:** Necessary data or independent evaluation is absent; no result is invented to fill it.
- **Untested behaviour:** No systematic evidence was found. This is not proof that the feature is broken.

The latest full suite passed 34 tests before this report. Those tests do not cover all newly identified negative cases. This review added targeted checks with synthetic inputs and temporary databases; it did not rerun or expand the complete suite and did not modify the user's financial records. Outputs and source hashes are in docs/review_checks.json. This is a self-assessment, not an independent audit.

## 3. Implemented features and readiness

| Area | Actual implementation | Assessment |
|---|---|---|
| Expense capture | Manual forms, conservative multi-expense parsing, DistilBERT categories, reviewed atomic batch saves | Working; narrower than general financial-language understanding |
| Receipt extraction | OpenCV, pretrained Tesseract, heuristic fields and user confirmation | Working pipeline; weak local-layout evidence |
| Shopping intake | Cart/order screenshots, pasted emails, .eml files, saved wishlists and reviewed expense entry | Basic intake works; currency, lifecycle and duplicate handling are incomplete |
| Financial HQ and shield | Cash snapshot, allowance date, daily essentials, reserve, commitments and safe ceilings | Useful deterministic core, not a learned guarantee |
| Survival forecast | Scoped LSTM optional-cost projection, protected costs and seven-day baseline | Integrated; end-to-end exhaustion-date accuracy unmeasured |
| What-If Lab | Purchase amount, allowance delay and discretionary reduction | Working numerical controls, not unrestricted free-text simulation |
| Pattern Detective | Autoencoder errors plus descriptive comparisons | Research component; detection accuracy unknown |
| Spending mix | Recorded category shares in app; rebuilt research clusters kept offline | No student identity or population validation |
| Spending coach | Weekly caps and repeated spending above them | Rules, not a learned habit agent or push-alert service |
| Conversational AI | Local Llama 3.2, session chat and check-in pop-up | Live integration; advice quality needs evaluation |
| Accounts and storage | SQLite workspaces on one machine | Not authentication or banking integration |
| UI | Streamlit, grouped navigation, charcoal/mint cards | Functional; independent usability/accessibility evidence absent |

## 4. Datasets actually used

| Dataset | Actual role | Limitation |
|---|---|---|
| Daily Household Transactions | 2,461 raw rows; 2,301 cleaned records. Reference classifier, LSTM, autoencoder and household-month clustering | One INR household. Direct Kaggle download matches existing data and is not extra people or examples |
| Personal Finance, entrepreneurlife on Kaggle | 806 records; 617 retained debit expenses after credit/card-payment exclusion. New reference models and extra classifier text | One history, 63 unique retained descriptions. Publisher's real-world claim is not independently verified. Currency absent |
| Combined classifier corpus | Cleaned descriptions/categories from both sources; 20 conflicting description strings removed. New split: 787 training, 263 held out | Different split from the original. No cross-student or unseen-merchant generalization established |
| SROIE sample | Five images and entity labels for extraction evaluation | Small, non-local sample; not full-benchmark testing |
| WFP and other student files | Historical price context and schema exploration | Not the user's monetary-model training. WFP has no Sukkur coverage and the bundle ends 15 September 2026 |

Kaggle metadata reports MIT for Personal Finance, CC0 for the matching household copy and Apache 2.0 for Student Spending Habits. These are publisher declarations, not independent proof of original collection rights. Selected metadata, source URLs and checksums are retained. Public availability does not establish valid collection consent or unrestricted redistribution.

Personal-reference currency is preserved as UNSPECIFIED_SOURCE_UNITS, not relabelled PKR. Only text/category examples are combined for DistilBERT; unlike currencies' amounts are not pooled into a monetary series. This is a sound training boundary, but transaction intake does not enforce the same boundary consistently.

## 5. Model results and their interpretation

### 5.1 DistilBERT classification

The original model used 755 training and 252 held-out unique descriptions. Accuracy is 78.17%, macro precision 0.615, macro recall 0.571 and macro-F1 0.589. Bills has zero precision/recall/F1 on one test example; Shopping F1 is 0.444 on ten examples.

The fresh Kaggle candidate uses 787 training and 263 held-out unique descriptions. Accuracy is 76.05%, macro precision 0.559, macro recall 0.510 and macro-F1 0.500. Bills and Education both have zero F1 on three and four examples. Shopping F1 is 0.690 on eleven examples.

These results are not a head-to-head comparison: test sets differ. They do not establish improvement, and very small class counts make conclusions unstable. The original remains default; the candidate is opt-in.

The final two DistilBERT encoder blocks and classification head were fine-tuned. This is not a transformer trained from scratch. Number/date parsing is separate rule code. Softmax confidence is not calibrated correctness. There is no validated abstention policy, unseen-merchant benchmark, Urdu/Roman Urdu benchmark or independent Pakistani-student test. Excluding conflicting descriptions cleans supervision but does not solve ambiguous notes in actual use.

### 5.2 LSTM forecasting

| Source and units | Category-day MAE | RMSE | Baseline MAE | Baseline RMSE |
|---|---:|---:|---:|---:|
| Household reference, INR | 316.56 | 1,821.67 | 321.16 | 1,947.80 |
| Fictional campus, PKR | 23.35 | 103.38 | 27.86 | 106.88 |
| New personal reference, source units unspecified | 25.65 | 278.32 | 29.80 | 298.29 |

The LSTM consumes 14 daily category vectors, uses 32 hidden units and predicts next-day category expenses. Scales are fitted on training history. Evaluation is chronological, but the rolling one-day protocol observes earlier validation days. It must not be called a free-running monthly test. Separate recursive 30-day results are saved in forecast.json, with limited reference windows rather than a broad student trial.

High RMSE relative to MAE shows sensitivity to large spikes. Averaging across nine categories, including zero entries, can conceal poor performance on important categories and daily totals. There are no confidence intervals or calibrated uncertainty bands. Missing dates are zero-filled; complete logging coverage of public histories is not independently verified.

The app's survival projection uses selected optional forecasts plus entered essentials and commitments. Reported category metrics do not evaluate the complete hybrid balance projection, reserve-breach date or money-exhaustion date. Therefore the central promise, 'predict when this student will run out of money,' is not yet validated by the current scores.

### 5.3 Autoencoder detection

The autoencoder reconstructs twelve features: log amount, normalized weekday/day of month and nine-category indicators. It has a four-unit bottleneck. Thresholds use the 95th percentile of later calibration errors.


These flag rates largely follow calibration and do not demonstrate correctness. There are no verified anomaly labels or independent labelled anomaly tests. Fraud accuracy, precision and recall cannot be claimed. The training population is not verified to be clean normal spending. Descriptive category comparisons are context, not faithful explanations of the neural network's internal decision.

The feature vector does not explicitly contain a rolling purchase-frequency statistic. The autoencoder must not be credited with learning every type of repeated/frequent spending. Weekly-cap flags are a separate rule-based component.

### 5.4 Spending-mix clusters

Old profile/fixture results have been retired. See [real-source rebuild](../eval/spending_mix_v1/REPORT.md); research artifacts are not deployed.

### 5.5 Receipt OCR

OpenCV and pretrained Tesseract are used; financial CSVs did not train a new OCR model. The five-case SROIE sample gives merchant exact match 60%, date 80% and total 60%. One image changes a percentage by 20 points. This is a smoke test, not reliable evidence for Pakistani receipts or shopping screenshots.

There is no evaluated local set spanning canteen slips, low light, rotation, Urdu, shipping, discounts, cancelled orders or cash-on-delivery. Merchant detection is heuristic and can mistake a header for a store. Extraction leaves missing dates empty, but the review form defaults them to today and can clamp future dates to today. That must be identified as an editable default, rather than implied to be an extracted fact.

## 6. Proposal and vision mismatches

All five proposal ML/CV families are present and integrated. Python, Pandas/NumPy, scikit-learn, PyTorch, Transformers, OpenCV/Tesseract and Streamlit remain the foundation. SQLite, requests and XLSX-reading support are lightweight additions. Current operation does not require React, Firebase, a Node service or a paid generative API.

Important narrower implementations or unfulfilled implications:

- The shield is arithmetic; survival forecasts lack end-to-end validation. The learned layer covers selected optional categories, not all future costs.
- Natural-language extraction uses rules for amounts/dates, not unrestricted learned financial-language parsing.
- What-if controls cover purchases, delay and discretionary cuts. A free-text 'reduce food by 20%' request is not automatically a complete scenario; the discretionary slider does not reduce protected food essentials.
- Repeated spending flags are rules over logged entries, not a trained sequential habit model or background push notifications.
- Llama is pretrained and not fine-tuned on private finances. Its initial check-in greeting is scripted; later responses are generated.
- Chat context contains wallet/runway arithmetic, recent category amounts, cap summaries and cart totals, but not the complete LSTM, autoencoder or K-Means outputs. It is not yet a conversational explanation of every ML result.
- Workspaces are local partitions, not authenticated accounts or bank connections. A mobile app/backend has not been built.
- The appearance is original Streamlit styling inspired by the supplied reference, not the commercial Vue Paper Dashboard PRO package. Legacy styling functions remain, and no independent UX study validates the current design.

## 7. Reproduced correctness issues

The checks below used synthetic examples and temporary storage, not the user's records.

| ID | Finding | Observed result | Impact |
|---|---|---|---|
| F01 | Dollar currency is not recognized consistently | 'Order total: $120.00' returns amount 120 and currency None | PKR form can accept a foreign amount without a foreign-currency warning |
| F02 | CSV currency is ignored | A currency=USD row was accepted into a workspace | Analytics can mix units; imports correctly leave cash unchanged |
| F03 | Relative date applies globally | 'Spent 350 on lunch yesterday and 150 on rickshaw today' assigns 17 Nov to both for an 18 Nov reference | Second purchase is misdated unless reviewed |
| F04 | Ledger/cash rounding differs | Input 0.005 stores expense 0.01 but changes cash 100 to 99.995, not 99.99 | Reconciliation can disagree at sub-cent precision |

F01-F02 are particularly important: model-training currencies are isolated, but intake is not equally strict. A foreign planned cart is also presented through a PKR-labelled form before the confirmed-purchase currency check. Central currency handling is needed across every entry path.

Review screens mitigate these problems but do not remove them. Unknown currency and inferred/default dates should be explicitly highlighted, not left for users to notice.

## 8. Other open implementation risks

**Duplicate saves and order lifecycle - code finding.** Forms can be submitted again without an order-ID/document-fingerprint idempotency constraint across receipts, emails and confirmations. Planned carts have no complete edit/delete/converted/cancelled lifecycle and can remain after logging a purchase. 'Order placed' does not necessarily mean cash was paid. Cash-on-delivery and cancellation need paid-versus-committed handling.

**Money representation - code finding and F04.** Python floats and SQLite REAL are used. The batch path rounds before cash adjustment, but the single-entry path can use unrounded input. Adopt one minor-unit or Decimal policy across saving, refunds and deletion reversal.

**Taxonomy - code finding.** Eating out is a keyword subset of Food, not a stable first-class subcategory. Generic descriptions or misclassified restaurant entries can evade caps. Online-order intake defaults to Shopping, including groceries, medicines or books unless corrected.

**Concurrency - architectural risk.** ml.MODELS is a process-global mutable selection. Some calls temporarily swap and restore it. This is not a robust simultaneous-session boundary. Prefer explicit immutable model paths/services before multi-user deployment. A race is not claimed to have been reproduced in this review.

**Local-model alias - code finding.** Readiness can accept llama3.2:latest while inference still requests llama3.2:3b. With only the alias installed, ready status and request can disagree. This laptop has the requested tag, so this is a portability edge case, not a current reported outage.

**Portability - code finding.** Automatic model startup defaults to a laptop-specific E: location. It supports an override, but clean installation/configuration needs testing. Runtime and large model weights are deliberately outside the ZIP.

**Freshness and monitoring - limitation.** Alerts run during app activity, not continuous observation. Some saves do not immediately recalculate every earlier rendered summary. Daily check-in state is session-based, so a new session may show it again. It is not a durable daily notification service.

**Privacy and security - architectural limitation.** Local SQLite and loopback binding reduce exposure. Workspace names still do not enforce authenticated access. Encryption-at-rest, role controls, backup/recovery policy and a public-deployment security assessment are absent. Do not expose this server as a secure shared account service.

## 9. Conversational-model reliability

Llama-3.2-3B-Instruct runs locally through Ollama; the quantized file's checksum was verified during setup. Conversations are session-only. The model has no database-write tools, cannot transfer funds and does not monitor an inbox/bank account.

In an early live check, Rs. 1,000 shoes exceeded calculated protected capacity of Rs. 750, but the model called them affordable. Explicit calculated cart verdicts and stronger instructions were added. A follow-up gave the correct Rs. 250 shortfall; another chai-spending conversation produced a relevant question. These examples are not an advice benchmark.

Current enforcement is prompt-based, with no output validator proving that contradictory advice cannot appear. Numerical consistency, multi-step reasoning and adversarial phrasing are not systematically measured. A 2,048-token context plus up to sixteen messages and financial data may require truncation; retention is not systematically evaluated. Memory pressure can affect latency/availability.

Recommended boundary: calculate facts in Python, display the authoritative affordability verdict separately, and use Llama for explanation/questions. Validate generated numerical claims before presenting them as advice. An explanation must not override failed reserve/essential constraints.

## 10. Test coverage and missing evidence

The latest suite passed **34 tests**, covering navigation, manual/reviewed receipt saving, batch atomicity, snapshots, commitments, imports, delayed obligations, model loading/shapes, future-entry exclusion, selected Kaggle checks and local-chat request/error contracts.

This does not mean 34 independent user studies, full line coverage, secure deployment or validated ML. Insufficiently tested areas include:

- Regression cases F01-F04; duplicate, cancelled and unpaid orders.
- Local receipt/cart benchmarks with independent annotations.
- Unseen students/merchants, regional language and missing-log patterns.
- Hybrid final-balance, reserve-breach and exhaustion-date accuracy.
- A common untouched comparison set for classifier candidates.
- Confidence calibration, abstention and uncertainty coverage.
- Concurrent sessions, interrupted operations, backup recovery and adversarial input.
- Accessibility, independent phone-layout checks and usability studies.
- Cold/warm model latency, memory footprint and clean offline restart/setup.

No fresh complete browser/visual audit is claimed here. Earlier screenshots reflect earlier designs; capture current screenshots using the README checklist.

## 11. Strengths to preserve

1. Five actual ML/CV implementations and saved artifacts; no random fake predictions.
2. Explicit separation of arithmetic, descriptive summaries and model outputs in key screens.
3. Separate monetary sources/currencies; new reference amounts do not fund a PKR wallet.
4. Human review and atomic multi-entry saving.
5. Imports do not replay cash; commitments and snapshot revisions address double counting.
6. Reports include confusion matrices, baselines, error distributions and cluster stability.
7. A newly trained candidate is not automatically promoted as better.
8. Local Llama is optional, without a paid-API dependency.
9. Private databases and large local-model weights are excluded from the release.

## 12. Prioritized improvement plan

Acceptance criteria below are proposed targets, not results already achieved.

| Priority | Work item | Acceptance criterion |
|---|---|---|
| P0 before a real-money pilot | Central currency enforcement | Unknown/conflicting units require explicit confirmation on every intake path; foreign-currency regressions pass |
| P0 | Exact accounting/reconciliation | Saved entry, cash change, refund and reversal reconcile; F04 covered |
| P0 | Idempotent saves and paid states | Repeat submit cannot double-log; unpaid/COD orders do not silently become paid expenses |
| P0 | Numerical advice guard | A failed Python affordability check cannot be presented as affordable; multi-step/adversarial examples evaluated |
| P0 before public exposure | Authentication and session isolation | No cross-user access or global model-selection race; security review completed |
| P1 | Common untouched model benchmark | Same unseen comparison set, class counts, uncertainty and final untouched test |
| P1 | Evaluate actual survival outcomes | Daily-total, final-balance, exhaustion-date and reserve-breach errors reported for the hybrid pipeline |
| P1 | Consented local pilot | Document population, currency, logging coverage and participant/time holdouts |
| P1 | Local receipt/cart benchmark | Independent field annotations, varied layouts and held-out merchants |
| P1 | Per-expense dates/provenance | Mixed relative dates correct or rejected; defaults and extracted fields clearly distinguished |
| P1 | Stable taxonomy and honest personas | Reviewable eating-out subcategory, explicit share denominator and uncertainty labels |
| P1 | Verified chat context | Include sourced ML outputs if claimed; measure factual consistency |
| P2 | UI/CSS simplification and usability | Core tasks completed without guidance; phone, keyboard and accessibility findings documented |
| P2 | Operational reproducibility | Portable setup, artifact manifests, backup/restore and performance measurements |

A small consented hostel/commuter pilot can be designed with the supervisor. No arbitrary participant count guarantees enough data. Sparse histories may need a statistical baseline rather than a personal LSTM. Avoid adding more features until the correctness and evidence gaps are addressed.

## 13. Recommended experiments

**Classification:** Freeze a shared benchmark before tuning. Group near-duplicate descriptions and merchant families; hold out students where possible. Include campus-language examples. Report class precision/recall/F1, macro-F1, confusion, calibration and abstention trade-offs rather than accuracy alone.

**Forecasting:** Rolling-origin evaluation with scales fitted inside training windows. Compare last-value, last-week and mean baselines. Evaluate category and daily-total errors, recursive horizons and downstream balances/dates. Separate known zero-spend days from missing logs.

**Anomalies:** Separate training, threshold calibration and test. Obtain human review without equating unusual to fraudulent. Use precision/recall only with trustworthy labels; otherwise report flag counts, reviewer agreement and calibration limits.

**Clustering:** Compare seeds and resampled participants. Report stability, center interpretation and weak assignments. Test whether category-share summaries help as much as persona labels. Do not force entertaining names unsupported by fitted clusters.

**OCR/intake:** Hold out merchants/layouts. Include currencies, absent dates, shipping, discounts, mixed language, low-quality images and duplicates. Measure field accuracy, correction effort and manual-entry rate.

**Advice/usability:** Fix a test set with independently calculated financial answers. Measure numerical agreement, contradictions, unsupported claims and useful requests for missing information. Observe completion and comprehension of capture, forecast and simulation tasks, not just satisfaction.

## 14. Defensible versus unestablished claims

| Defensible now | Not established |
|---|---|
| Integrated local student-oriented ML prototype | Accurate exhaustion predictions for Pakistani students |
| Models trained/evaluated on documented data | Kaggle availability proves relevance or generalization |
| Deterministic protection under entered assumptions | Daily ceiling is learned, guaranteed or calibrated advice |
| Autoencoder flags reconstruction errors | Known fraud/irresponsible-spending detection accuracy |
| K-Means describes spending mixes | Stable psychological student identities |
| OCR proposes fields for review | Reliable unattended receipt/cart saving |
| Local Llama can explain supplied facts | Financial expertise or guaranteed numerical correctness |
| Thirty-four tests passed | Comprehensive security, usability and edge-case coverage |

## 15. Questions for the evaluator

1. Should the contribution be narrowed to explainable survival forecasting and protected-cost simulation?
2. What independent local validation is required for the final claims?
3. Are the classifier split, rare-class strategy and model-selection procedure defensible?
4. When should a simple baseline replace LSTM for sparse histories?
5. Is hybrid forecast cost coverage correctly defined and understandable?
6. Do anomaly/persona features add value given the absent labels and weak stability?
7. Which currency, rounding, duplicate-order and session issues are release blockers?
8. Is optional Llama within scope, and what consistency standard should it meet?
9. What receipt, usability and clean-install evidence is necessary for submission?

## 16. Evidence index and conclusion

- README.md: installation, current journey and assumptions.
- docs/IMPLEMENTATION_PLAN.md and ARCHITECTURE.md: traceability and design.
- docs/MODEL_CARDS.md and KAGGLE_TRAINING.md: training/evaluation details.
- docs/DATA_AUDIT.md: attribution and adaptation constraints.
- models/evaluation_report.json: original metrics/confusion/stability.
- models/kaggle_evaluation.json: fresh candidate evaluations.
- models/research/ocr_evaluation.json: five-case OCR evidence.
- docs/review_checks.json: negative checks and source hashes.
- tests/: current 34-test suite; it does not cover all findings above.

The strongest honest description is **an integrated and tested research prototype**. The next improvement is not a larger feature list: it is fixing demonstrated financial-intake inconsistencies, validating the actual survival/advice outcomes promised to users and obtaining independent student-relevant evidence. Implementation completion should not be mistaken for validated product readiness. This report intentionally preserves open deficiencies for external evaluation.


## 19 November revision: reviewed chat account changes

The earlier read-only chat findings describe the audited version. Chat now prepares PKR transactions, individual wallet updates and weekly limits for an explicit Apply/Cancel preview. The server validates fields and amounts, binds the workspace, rejects stale previews and records application tokens atomically to avoid duplicate application. Transaction previews show wallet impact; cash snapshot changes preserve other settings. No bank transfer or external account edit is supported. Llama intent extraction is not a verified safety classifier and can misinterpret messages; human review remains required. Existing currency intake, OCR, dataset and other evaluation findings remain open.


## 19 November mobile revision

A mobile PWA and authenticated FastAPI/SQLite API were added after the original audit. Student accounts now use server-derived workspaces, scrypt password hashes, revocable sessions, CSRF/origin checks, and atomic replay-safe financial writes. New mobile text intake parses dates per clause and foreign-currency review includes common symbols. These changes do not fix the original desktop CSV/intake findings or validate public datasets. New accounts do not receive personal LSTM/autoencoder predictions. The app is locally hosted; physical-phone installation, trusted HTTPS hosting and public production readiness remain unverified. See MOBILE_APP.md and mobile/VERIFICATION.json for exact scope and checks. The earlier PDF remains a snapshot of the original audit.
