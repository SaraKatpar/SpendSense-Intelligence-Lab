# SpendSense Android APK

This native Android package opens the existing mobile SpendSense UI in a restricted WebView. It adds a native connection screen, saved server address, connection-error/retry screen, Android image picker, finance export through Android's document picker and Back navigation. It is a connected client for the FastAPI/SQLite/Ollama server, not an offline Python-model bundle.

## Install and connect

1. Transfer `output/android/SpendSense-Android.apk` to your Android phone and open it with the Android package installer. Minimum supported version is Android 8.0 (API 26). No installation on a physical phone or emulator has been claimed.
2. Keep your laptop and phone on the same trusted Wi-Fi. Run `spendsense/run_mobile_lan.bat` on the laptop, unless the mobile server is already running on port 8765.
3. The app's connection screen accepts your server origin, for example `http://<laptop-Wi-Fi-IP>:8765` or a trusted `https://` hosting address. No address is baked into the APK; enter the address of your own running backend. A university Wi-Fi network may prevent devices from reaching each other.
4. For local HTTP preview, use fictional data. The app asks you to acknowledge that local HTTP is unencrypted. Use trusted HTTPS before real credentials/financial data cross the network. Public HTTP addresses are rejected; HTTP is accepted only for private RFC1918 IPv4 addresses, including emulator host `10.0.2.2`. Certificate errors are never bypassed.
5. Create your student account and set up the wallet. The database remains on the server. Start Ollama with `llama3.2:3b` on that server for conversational AI. Manual finances remain usable if the model is unavailable.

The top-right app menu changes the server, exports your finances or opens the server in a browser. Changing server clears app cookies, so sign in again afterward. The app requests no broad storage/camera permissions: image selection and JSON export use Android's system pickers. Selecting an existing receipt/cart image is supported; direct camera capture is not implemented.

The image picker, document export, keyboard/inset behavior and actual device startup require physical-device verification. Build/signature verification is separate from those runtime checks.

## Build

The source is Java plus Android resources; it intentionally introduces no Flutter/React Native or Node build stack. `build_apk.py` uses official SDK `aapt2`, `d8`, `zipalign`, `apksigner` and a JDK. Default tool locations are on E: to avoid filling C:. Override them with `ANDROID_TOOLS_ROOT` and `JAVA_HOME`. SDK downloads must be obtained and checked against Google's repository metadata before running the build.

```powershell
python spendsense/android/build_apk.py
```

The build compiles Java, runs JVM URL/origin checks, converts to DEX, packages Android resources, aligns the APK, signs it and verifies the signature/CRC/package metadata. It writes the APK and `BUILD_INFO.json` under the workspace's `output/android/`.

The signing key is a **local development key**, stored outside the source at `E:/extra curricular/SpendSense-build/android-tools/spendsense-development.keystore`. Its standard development password is not a production secret. Keep the same key if you want later APKs to update this installation; increment versionCode for new builds. For Play Store distribution create and protect a separate production/upload key, perform device testing and configure production HTTPS hosting. The development certificate does not establish publisher identity.

## Security boundaries

No JavaScript-to-Java object bridge is exposed. Native export accepts one exact custom URI only while the main page belongs to the configured server, then fetches that server's authenticated finance export. WebView file URL access and third-party cookies are disabled. Non-server HTTP resources are blocked in the native request client; normal pages also inherit the backend's same-origin Content Security Policy. External HTTPS navigation opens in the system browser. User-selected content URIs are returned only through the Android file chooser callback.

This LAN-pilot APK enables Android cleartext capability to support changing private server IPs; URL validation and request filtering restrict its use. It is not a claim of encrypted HTTP or a public-production security audit. Existing mobile/backend limits, including no email verification or password recovery and no offline financial sync, are documented in `../docs/MOBILE_APP.md`.
