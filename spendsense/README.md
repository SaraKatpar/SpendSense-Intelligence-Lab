# SpendSense — Student Financial Survival Assistant

> **Ordered rebuild, 20 November 2026:** generated training/demo sources are retired. Accounting and numerical-advice guards pass regression checks; per-account corrections and a shared real-reference classifier benchmark are implemented. Survival validation is partial because verified balances/exhaustion outcomes are absent. A signed connected Android APK is built. All Berka artifacts remain research-only, outside the app; its frozen test must not be re-scored. See [ordered status and reports](docs/ORDERED_WORK.md).

**Will your money last until the next allowance?** SpendSense combines five proposal ML/CV components with explicit cash accounting for hostel students. Python + Streamlit, local SQLite storage, free local inference. No React, Node, Firebase or paid AI API dependency.

## Mobile app

A dedicated mobile PWA is now included: run `run_mobile.bat` and open `http://127.0.0.1:8765`. It provides student sign-up/sign-in, an empty private wallet, daily budget, expense/income capture, receipt/cart uploads, purchase simulation, dues, weekly limits, persisted local-AI chat and reviewed account changes. Financial records persist in SQLite with per-account isolation and replay-safe writes. Use the PWA directly, or install the signed thin Android client from output/android/SpendSense-Android.apk at the workspace root.

For phone preview on the same trusted Wi-Fi, use `run_mobile_lan.bat` and the laptop's Wi-Fi IP. Real network use and home-screen installation need trusted HTTPS. The server and Ollama must be running; models execute on the server, not the phone. No cloud deployment or physical-phone installation is claimed. See [mobile setup, architecture and limitations](docs/MOBILE_APP.md).

Mobile accounts are separate from the original local desktop workspaces. Existing private records have not been migrated. The original Streamlit interface and all research pages remain available using the instructions below.

## Run

On this laptop, double-click `run.bat`, or from the project folder:

```powershell
../.venv/Scripts/python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

For a new machine: install Python compatible with the pinned packages, run `setup.bat`, install Tesseract separately and set `TESSERACT_CMD` if it is not detected. `requirements.lock.txt` records the tested Windows/Python 3.14 environment; different Python/OS versions may need a compatible PyTorch wheel. No virtual environment, private database or Ollama weights are bundled in the project ZIP.

## One connected journey

1. **My wallet â†’ Financial HQ:** enter available cash, next allowance, minimum meals/transport and emergency reserve. Reserve dated fees and travel. Cash snapshots replace the old snapshot; imported history is not deducted again.
2. **Add spending â†’ Text & manual entry:** try `Spent 350 on biryani and 150 on rickshaw yesterday.` Amount/date extraction is conservative rule parsing; trained DistilBERT supplies categories. Review each editable row before an atomic save.
3. **Scan a receipt:** local OpenCV/Tesseract extraction, editable fields, optional cash update. Missing totals/dates are not invented. OCR is imperfect.
4. **Cart & online orders:** screenshots, pasted emails and .eml files. Wishlist carts persist without reducing cash. Only confirmed purchases become reviewed expenses.
5. **Plan ahead â†’ Survival forecast:** distinguish deterministic daily ceilings from LSTM scenarios and a seven-day statistical baseline. Personal models are not silently replaced with household INR models.
6. **What-If Lab:** purchase price, delayed allowance and reduced discretionary spending. Compare original and changed timelines; no real balances change. Where a suitable LSTM is available, the same scenario also runs through its optional-spending pipeline.
7. **Insights:** Pattern Detective uses the autoencoder, Spending mix shows descriptive recorded category shares; research-only spending-mix clusters are not deployed, and Spending coach uses explicitly separate weekly-limit rules. Every numerical summary comes from records or artifacts.

## Workspaces and model boundaries

- **My finances:** your local records, separate from demos; starts empty. Until a suitable personal forecast/anomaly model is trained, show transparent unavailable/fallback messages.
- **Household sample:** read-only historical INR reference from one household; never relabelled PKR.

SQLite is local persistence, not a multi-user authentication system. Workspace names isolate records in this local application; they are not online bank or university accounts. Keep `data/spendsense.db` private. Upload photographs remain in app-session memory; saved receipt cards are transaction summaries, not stored photographs.

## Forecast and accounting contract

Safe daily ceiling = max(0, (cash âˆ’ unpaid commitments due before allowance âˆ’ reserve) / days).
Discretionary ceiling = max(0, daily ceiling âˆ’ entered meals/transport).

Survival LSTM projections use the learned Shopping/Entertainment/Other components, exclude optional categories that have reserved commitments, then add entered daily essentials and dated commitments **once**. This scoped model does not forecast all possible essential costs. Enter other known essentials as commitments. The separate monthly forecast exposes all category outputs. Neither prediction is a calibrated probability of going broke.

The seven-day baseline is compared on the same scoped cost structure. Delaying allowance includes newly due commitments. Unpaid overdue items are counted today. Marking a commitment paid records its expense and removes its reservation atomically. CSV history imports never change cash. Backfilled expenses can leave the cash snapshot unchanged.

## Real evaluation results

See `docs/MODEL_CARDS.md` and `models/evaluation_report.json` for protocols, confusion matrix, class precision/recall/F1, error distributions and stability.

- DistilBERT: held-out accuracy 78.17%, macro-F1 0.589 on 252 deduplicated reference descriptions. Rare classes are weak; review predictions.
- Household LSTM: rolling one-day category MAE 316.56 INR, RMSE 1821.67; seven-day-mean baseline MAE 321.16, RMSE 1947.80. These are category-day errors, not total monthly errors.
- OCR: five-image SROIE smoke sample, merchant 60%, date 80%, total 60%. This is not an official benchmark score.
- Autoencoder: no verified anomaly labels; report reconstruction error and threshold/flag rate, not fraud accuracy.

## Training and reproducibility

Run commands from the project folder:

```powershell
python training/prepare_household.py
python training/train.py --csv data/household_clean.csv --model all --epochs 3 --output models/research
python training/prepare_campus.py
python training/evaluate_models.py --classifier
python training/evaluate_receipts.py --images data/sroie/images --labels data/sroie/entities --output models/research/ocr_evaluation.json
python -m unittest discover -s tests -v
```


## Optional conversational AI

Local Llama 3.2 (`llama3.2:3b`) explains budget context through Ollama on `127.0.0.1:11434`. All five ML/CV features and financial calculations work without it. Disable **Daily AI check-in** to hide its pop-up. Conversations are session-only. Chat can prepare local PKR expense/income entries, wallet field updates and weekly limits. Review the proposed fields and balance impact, then choose Apply account change or Cancel change. Advice and hypothetical questions should not propose changes. No real money is transferred. The small local model can misunderstand requests: always review its preview.

This laptop stores runtime and weights at `E:/extra curricular/SpendSense-build/local-ai`; the app can start that runtime automatically. Else install Ollama and run `ollama pull llama3.2:3b`, then `ollama serve`. `SPENDSENSE_LLAMA_MODEL` can select an existing Llama 3.2 tag. The text-only model uses extracted cart text/totals, not raw images. Local model advice can be wrong; calculated limits are authoritative.

## Submission materials

- `docs/IMPLEMENTATION_PLAN.md`: audit, phased plan and feature-to-proposal traceability.
- `docs/ARCHITECTURE.md`: structure, flow diagram and storage boundaries.
- `docs/MODEL_CARDS.md`: inputs, preprocessing, training, evaluation and limits.
- `docs/DATA_AUDIT.md`: schemas, suitability, attribution and licensing status.
- `docs/VIVA_AND_DEMO.md`: three-person task allocation, viva questions and presentation journey.


## Fresh Kaggle training

Downloaded and audited new Kaggle sources, trained a new DistilBERT candidate plus separate reference LSTM/autoencoder/month-window K-Means, and evaluated saved artifacts. See docs/KAGGLE_TRAINING.md and models/kaggle_evaluation.json. Candidate text classification is selectable in Settings; unlabelled source-currency monetary models remain separate from PKR wallets.

## Current real-data cleanup

Known generated data and derived campus/demo artifacts have been retired from training, evaluation and demos. Only My finances and the historical Household sample remain. See [spending-mix report](eval/spending_mix_v1/REPORT.md) for the development-only K-Means rebuild and stability. All Berka models remain outside app deployment and the frozen test set must not be re-scored.
