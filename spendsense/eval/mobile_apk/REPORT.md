# Step 7: connected Android APK

Built 20 November 2026 after steps 1-3 passed. **SpendSense 1.1.0**, package pk.spendsense.student, versionCode 2, minimum Android 8.0/API26, target API35. Development-signed universal Java/WebView client; 41,518 bytes.

[APK](../../../output/android/SpendSense-Android.apk) · [Build metadata](../../../output/android/BUILD_INFO.json) · [Setup guide](../../android/README.md)

SHA256: `3e2738e26cb1016da7b39f9486b88b46c40ac3e7e0a41c7af2350531cef31240`.

## Done

- Official SDK archives completed, validated against freshly fetched Google repository sizes/checksums and ZIP CRCs. URLs, published SHA1 and locally computed SHA256 are recorded in sdk_verified.json.
- Java compiled; all 19 native URL/origin checks passed; D8 converted bytecode; APK alignment, required entries, CRC and Android package metadata passed. APK v2/v3 signatures verify. Build logs and certificate details are saved with the output.
- The thin client provides server setup, account WebView, connection retry, same-origin navigation, system image selection, finance export and Back navigation. No private database, dataset, Berka artifact or other model is bundled. Storage and optional local Llama remain on the configured backend.
- Full current Python regression suite: 86 passed. Additional real HTTP journey passed against an isolated temporary database: registration/session, wallet, half-cent accounting, replay-safe save, foreign-currency rejection, reviewed correction and next suggestion, numerical veto, unchanged cash for advice/carts/corrections, private export and anonymous-access rejection. No benchmark model is scored by that journey.
- JavaScript syntax checks passed. Existing local desktop and mobile services were restarted; mobile health confirms version1.1.0, and desktop health is OK. The test journey does not write personal records.

## Resolved build failures

The previous SDK downloads were incomplete. The first resumed range attempt encountered content-encoding/response problems; identity encoding, raw binary reads and exact Content-Range checks fixed this. Final full published archive checksums pass. The first compiler invocation used a missing hardcoded javac path; tool resolution now uses the installed working Java/Javac launchers, with a JDK-module keytool fallback. Final compilation/signing passed. These resolved failures are not hidden as successful first attempts.

## Still unvalidated

Physical Android installation, emulator UI execution, native image chooser/document export, keyboard/insets, device Back behavior, university Wi-Fi isolation and HTTPS-hosted production use are not verified. Native hooks being compiled does not prove those device flows work. No offline financial sync, on-device Python models or production Play Store signing is provided. The local development signing certificate is for this installable build, not publisher identity verification.

## Use

Install the APK on an Android8+ phone. Keep the backend running; it currently serves the mobile app on port8765. On the same permitted Wi-Fi, the current laptop address is `http://10.102.144.88:8765`; it may change. Enter your own trusted server origin in the APK; no IP is baked into the package. The existing local HTTP-preview acknowledgement remains. Use a trusted HTTPS endpoint for real credentials/finances over a network. No public hosting or firewall/router changes were made.

Open My finances or your mobile account; it starts without generated sample transactions. Category corrections are available through reviewed chat (for example, "change last expense to Food") and desktop History. Research clusters and newly benchmarked candidates are not automatically assigned to accounts.

Berka's frozen protocol, saved models and test predictions remain unchanged. No Berka model is deployed, bundled or re-scored. Survival validation remains partial as documented in step6, despite the APK being buildable.
