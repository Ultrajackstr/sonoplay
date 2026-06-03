# Web UI tests (Playwright)

Browser tests for the SonoPlay web UI. They drive the **real** FastAPI app in a
headless Chromium and intercept `/api/*` with fixtures, so device data is
deterministic and no real DLNA hardware (or outbound network) is needed.

They exist to make the deferred frontend refactors safe to do — they pin the
current behavior of:

- **card render states** — playing / paused / stopped (guards the incremental
  re-render rewrite),
- **`sendCommand` wiring** — which `/player/playback/*` URL + headers each button
  fires (guards the `sendCommand` dedup),
- **the Plex PIN-link flow** — `POST /` + the PIN dialog (guards extracting the
  shared `runPlexPinFlow` helper),
- **CSS contract** — computed `.icon-btn` / `.device-controls` styles (guards
  moving the duplicated inline CSS into `minimal-clean.css`).

## Setup

```bash
cd web-tests
npm install
npx playwright install --with-deps chromium   # browser + OS libs (needs sudo for --with-deps)
```

## Run

```bash
npm test            # or: npx playwright test
```

Playwright's `webServer` starts the app itself (`python main.py` on port 32499)
and waits for `/health`. If a server is already listening there it is reused.

### Environment

- `SONOPLAY_PYTHON` — interpreter that has the app's deps installed. Defaults to
  `python3`; set it to your venv (e.g. `/path/to/venv/bin/python`) if the app's
  dependencies aren't on the default `python3`.
- `SONOPLAY_TEST_PORT` (default `32499`), `SONOPLAY_TEST_CONFIG`
  (default `/tmp/sp-test-config`).

```bash
SONOPLAY_PYTHON=/path/to/venv/bin/python npm test
```

## Notes

- **Hermetic.** `/api/*` and the external CDN assets (SweetAlert2, FontAwesome,
  Google Fonts) are stubbed in `tests/helpers.js`. SweetAlert2 is replaced with a
  small shim that records `fire()` calls and renders the standard `.swal2-*` DOM,
  so the link/relink flows work without the CDN. This also sidesteps sandboxes
  whose TLS proxy the browser won't trust.
- Run artifacts go to `/tmp/sonoplay-pw-results` (kept off the repo mount).
- `node_modules/` and the downloaded browser are not committed.
