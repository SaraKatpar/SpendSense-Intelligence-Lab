# SpendSense implementation audit

Approved proposal supplied in the conversation: five model families, receipt entry, monthly forecasts, anomaly alerts, personas and recurring-payment detection. The 18 November master brief refines this into student financial survival. Reuse the existing Python/Streamlit/SQLite code and trained artifacts. Llama 3.2 stays optional and local.

| Requirement | Proposal foundation | Existing reusable component | Work in this revision |
|---|---|---|---|
| Smart capture | DistilBERT + OCR | ml.py, receipt_ocr.py, entry_form, shopping.py | Multi-expense text parsing, per-row review, atomic saving |
| Survival forecast | LSTM | forecast.pt, daily_matrix, campus.runway | Daily horizon inference, baseline comparison, cash projection without double-counting reserved costs |
| What-if lab | Forecast + calculations | render_purchase, runway | Allowance delay and explicit discretionary reductions alongside purchase scenario |
| Pattern detective | Autoencoder | anomaly.pt and reconstruction errors | Transaction-level context and separate rule-warning labels |
| Emergency shield | Financial calculations | commitments, buffer and minimum daily costs | Reuse reserve accounting and expose protected vs spendable money |
| Insights | All models | coach, analytics, ML metadata | Verified summaries, no LLM requirement |
| Local chat | Optional enhancement | Ollama + Llama 3.2 | Preserve optional chat, do not block dashboard |
| Viva/delivery | All | training scripts, README, tests | Reproducible evaluation, architecture, licensing audit, roles and demo guide |

## Phases
1. Audit supplied archive, current source, model artifacts and data provenance.
2. Extend capture and financial calculation helpers; retain isolated SQLite workspaces.
3. Evaluate saved models, improve evaluation scripts and report actual outcomes. No unnecessary retraining.
4. Integrate daily LSTM survival predictions, scenarios and readable pattern explanations.
5. Apply the brief’s charcoal/mint design to the compact grouped navigation.
6. Run regression and new accounting/inference checks, then package source and trained artifacts.

## Known risks and resources
- Household data are one INR household, not Pakistani student ground truth.
- Spending-mix clusters remain research-only; known generated sources and derived artifacts are retired.
- Generic personal-workspace LSTM inference must remain unavailable until a suitable personal model exists.
- A reserve/commitment can appear in both future ML spending and explicit commitments; forecast only variable categories, and add known fixed commitments once.
- Receipt OCR needs manual review; existing evaluation is five images, not the full SROIE benchmark.
- Some source redistribution permissions need verification; record exact status rather than imply a license.
- C: space is constrained; model artifacts/runtime remain on E: through the existing junctions.

## Revision completion evidence

All six engineering phases completed for this revision: source audit; reusable capture/storage helpers; reproduced model evaluation; survival/scenario/insight integration; dark grouped interface; documentation and 32 passing tests. This does not resolve the research limitations or licensing/attribution items in DATA_AUDIT.md. No independent real-student pilot or full OCR benchmark is claimed.
