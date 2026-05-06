# Fake News Check (Chrome extension)

Small Manifest V3 extension that extracts **article text** from the active tab (JSON-LD `articleBody` when present, else **Mozilla Readability**, else page `innerText`), then calls your Go gateway **`POST /predict`**.

## Build (required after clone or editing `src/content-main.js`)

```bash
cd chrome-extension
npm install
npm run build
```

This writes **`content-bundle.js`**, which `manifest.json` loads. Reload the extension in `chrome://extensions` after each build.

## Setup

1. Start **Redis**, **ML service**, and **Go gateway** (see repo root docs / your usual `docker compose` + `go run`).
2. Run **`npm install` && `npm run build`** in this folder (see above).
3. Open Chrome → **Extensions** → enable **Developer mode** → **Load unpacked** → select this `chrome-extension` folder.
4. Open **Options** (right-click the extension icon → Options, or from the popup link):
   - **Gateway base URL**: e.g. `http://localhost:8080`
   - **API key**: same value as **`API_KEY`** in `go-gateway/.env` (e.g. `test-key-123`)

## Production / other hosts

`manifest.json` → **`host_permissions`** must include every origin you call (scheme + host + port). Add your deployed gateway URL, then reload the extension.

## Limitations

- **JSON-LD** is used only when `articleBody` is long enough (~400+ chars); otherwise **Readability**, then raw `innerText`.
- **Paywalls** and late-rendered SPAs can still produce weak text.
- **API key in the extension** is fine for a portfolio demo; do not treat it as secure for public users.

## Privacy

Text and URL are sent only to **your** gateway URL. Nothing is sent to third parties except what your backend already does (ML / Groq / Qdrant).
