# SpendSense mobile edition

## What was built

An installable progressive web app (PWA), with a dedicated phone interface and a same-origin FastAPI backend. The PWA also has a compiled thin Android client (1.1.0); see ../android/README.md and ../eval/mobile_apk/REPORT.md. No iOS binary is provided. The existing Streamlit desktop research interface remains available on port 8501.

The mobile interface uses HTML/CSS/JavaScript with no Node build dependency. Python keeps the financial logic, local models, receipt OCR and conversational Llama. SQLite is an actual persistent server database, not browser localStorage. Accounts remain signed in through revocable seven-day HTTP-only session cookies. A student can use the same account from multiple devices connected to the same server.

## Start locally

On this laptop double-click `run_mobile.bat`, or run from `spendsense`:

```powershell
../.venv/Scripts/python.exe -m uvicorn mobile.api:app --host 127.0.0.1 --port 8765 --no-access-log
```

Open `http://127.0.0.1:8765`. Create your own account, then enter your current cash, next allowance date, daily essential costs and emergency reserve. No demo history is silently inserted. Your account is separate from the original desktop My finances workspace; existing user records have not been migrated or relabelled.

On a fresh machine install the original Python dependencies plus `mobile/requirements.txt`. From the `mobile` directory: `python -m pip install -r requirements.txt`. Tesseract and Ollama are separate installations; existing local model artifacts are reused. Run the same server command from the parent `spendsense` directory.

## Preview on a phone

Use `run_mobile_lan.bat` instead of the loopback launcher; do not start both on the same port. Put your phone and laptop on the same trusted Wi-Fi. Open `http://<laptop-Wi-Fi-IPv4-address>:8765` on the phone. Windows Firewall or university Wi-Fi isolation may block this; no firewall or network security settings are changed by this project.

HTTP LAN preview is for fictional test data. A trusted HTTPS address is needed before using real account credentials and financial data over a network. Home-screen install and service workers require HTTPS, except for localhost development. Do not bypass certificate warnings.

Once served over trusted HTTPS: Android Chrome menu â†’ Install app / Add to Home screen. iPhone Safari Share â†’ Add to Home Screen. The manifest includes standalone display and 192/512px icons. Install availability depends on the device and browser; it has not been installed on a physical phone during this build.

## Student journey

1. Create account or sign in. Email format is validated, but email ownership is not verified.
2. Set up an empty personal wallet. Saving a later balance snapshot replaces the snapshot; old history is not deducted twice.
3. **Home:** daily ceiling, essentials, optional room, remaining balance, recent activity, seven-day spending and repeated weekly-limit flags.
4. **Add:** manual expense/income, reviewed text extraction, receipt/cart screenshots or pasted order email. Camera images can be selected through the native file picker where the phone offers them. Images stay in request memory; no image archive is created. Saving an unpurchased cart never deducts cash. Paid orders should be entered once, including COD only after payment.
5. **Plan:** purchase/allowance-delay simulator, weekly limits, carts, upcoming dues and reviewed mark-paid flow. Simulation is read-only. Due payment records a local expense and clears its reservation atomically; it never transfers money.
6. **Buddy:** local Llama conversation, persisted messages, and explicit account-change previews. Applying a proposal validates its active account, amount/date/category, expiry and financial snapshot. Cancellation writes no financial change.
7. **You:** wallet settings, latest 80 activity entries, reviewed deletion, finance export, sign out and installation guidance.

## Database and access boundaries

Default database: `spendsense/data/spendsense.db`; `SPENDSENSE_DB` can select another absolute file path. Existing tables hold wallets, transactions, commitments, carts and weekly limits. New tables hold `mobile_users`, `mobile_sessions`, `mobile_attempts`, `mobile_requests`, `mobile_proposals` and `mobile_messages`.

Each account gets a random user ID and server-derived workspace `mobile:<id>`. Clients cannot submit workspace or user IDs to the financial routes. Passwords use per-user random salts and scrypt hashes. Only SHA-256 hashes of opaque session tokens are stored. Logout revokes the session. Mutating requests require a same-origin custom header plus session CSRF token; cross-origin browser requests are rejected. No permissive CORS is configured. A basic persisted 15-attempt/15-minute IP gate applies to registration/login.

Financial writes use SQLite transactions, parameterized queries, finite PKR amounts with at most two decimal places and client request IDs. A replay with the same ID/payload returns the first result; reusing an ID with a different payload is rejected. Wallet forms use an optimistic snapshot version to reject stale edits. Due payment is safe against repeated clicks and different replay IDs. Transaction deletion reverses cash only for the corresponding current wallet revision. Chat apply uses its separate atomic application ledger; it cannot apply twice.

Private API responses have `Cache-Control: no-store`. The service worker caches only public app-shell assets, never account/API responses, receipt images or chat. The shell can open without network, but sign-in, financial reads/writes and AI require a live server. Offline edits are not silently queued. No push notifications are implemented.

## AI/model boundaries

- Text categorization loads the existing reference DistilBERT directly from its artifact directory under a lock. It does not mutate the desktop app's global `ml.MODELS`. Low confidence still needs manual review.
- Receipt screenshots use existing OpenCV/Tesseract OCR. Currency detection includes dollar/euro/pound symbols in this mobile intake. Foreign totals are left blank in the PKR review form; there is no automatic conversion.
- Natural-language clauses are parsed separately so an explicit yesterday in one clause does not change another clause's today. Ambiguous quantities still require review.
- Fitted style assignment is disabled. Spending-mix clusters are research-only; no Berka model is loaded into the app.
- No suitable personal LSTM/autoencoder is assigned to a new account. This mobile release does not claim learned personal forecasts or anomaly detection. Existing training/research tools stay in the desktop app. Daily ceilings and purchase simulations use entered costs and deterministic calculations.
- Llama 3.2 runs on the server laptop via `127.0.0.1:11434`; it does not run on the phone. Ollama must be running. A server lock serializes inference; another concurrent user may receive a retry message. No model API key is needed.

## Hosting and production limits

The app is currently self-hosted on this laptop, not published to the Internet. Sites/Cloudflare Workers cannot run the existing PyTorch/Tesseract/Ollama workload directly, so publishing a static shell there would leave the financial/AI backend disconnected. No cloud service, paid database or credentials have been provisioned.

For a real pilot, use a persistent Python-capable server or container with an HTTPS reverse proxy. Keep the database on a persistent disk. Set `SPENDSENSE_HTTPS=1` for Secure cookies; configure proxy scheme/host forwarding only from trusted proxies. Keep Ollama private to the server; never expose its port to the Internet. Use one server instance while SQLite is on local disk. Multiple replicas need a shared database design, normally PostgreSQL, with schema migration and transaction adaptations.

Back up the database using SQLite's backup API or a consistent stopped-server copy; protect backups as financial data. This prototype has no password recovery, verified email, MFA, account deletion UI, managed encryption-at-rest, automatic backups, audit dashboard, per-user AI quotas or production load test. Do not describe it as a fully hardened public banking service.

## Validation

`python -m unittest discover -s tests -p test_mobile.py -v` exercises HTTP registration/session auth, CSRF/origin checks, cross-account isolation, atomic/replayed writes, stale wallet edits, deletion accounting, limits/carts/dues, paid-once accounting, read-only simulation, per-clause dates, foreign-currency handling, invalid amounts/dates, persisted/reviewed chat actions, stale cancellation, logout/login persistence, static PWA assets, API cache headers and export privacy. Tests use temporary databases only. UI/browser checks and any remaining limits are recorded in `mobile/VERIFICATION.json`.

PWA requirements reference: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable


## Ordered rebuild update, 20 November 2026

Steps 1–3 pass, corrections now update a per-account categorizer layer through reviewed chat/history actions, and an isolated real HTTP journey verifies the updated backend. No Berka or newly benchmarked research model is deployed. Source/model and survival limitations are in ORDERED_WORK.md. The native APK still needs physical-device installation, picker/export and network validation; its database and optional Llama stay on the configured server.
