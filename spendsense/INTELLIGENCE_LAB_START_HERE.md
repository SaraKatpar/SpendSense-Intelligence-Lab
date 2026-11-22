# SpendSense Intelligence Lab — Build 1

This is a **new, reversible Streamlit entry point**. The original `app.py` and its mobile application remain untouched.

## Run

From the `spendsense` directory, install the compatible dependencies in `requirements.txt` using a Python virtual environment, then run:

```bash
streamlit run intelligence_lab.py
```

## What is implemented

- Violet/cyan dark visual identity, separate Student and ML Lab navigation.
- Home HQ: local recorded transactions, spending breakdown and honest model status.
- Capture Studio: text input, manual form, receipt upload via the existing optional Tesseract pipeline, mandatory confirmation before saving.
- Future Lab: actual historical spending chart and guarded LSTM loading.
- Spending DNA: descriptive category analysis, with clear missing K-Means notice.
- Pattern Detective: guarded autoencoder loading.
- Model Arena: archived metrics from `eval/*/metrics.json`.
- Dataset Explorer, Experiment Console, Evaluation Report.

## Not yet implemented / known blockers

- Model weight files are missing from this ZIP. No ML inference is claimed until trained artifacts are restored and validated.
- K-Means research is not yet connected to personal inference.
- Text categorization currently requires user confirmation; model integration is pending.
- OCR requires external Tesseract installation and permission under applicable course rules.
- No synthetic ML predictions are displayed.
- Existing Android client still uses the old workflow.
- This build has not been verified on your local Windows environment.

## Next build

Reproduce training artifacts and connect categorization, K-Means and benchmark adapters. Then run the full regression suite and validate a clean environment.
