// Playwright config for the SonoPlay web UI tests.
//
// Tests drive the REAL FastAPI app in a headless Chromium and intercept the
// /api/* calls with fixtures, so the device data is deterministic without
// needing real DLNA hardware. Set SONOPLAY_PYTHON to the interpreter that has
// the app's deps installed (defaults to python3).
const { defineConfig } = require('@playwright/test');
const path = require('path');

const PORT = process.env.SONOPLAY_TEST_PORT || '32499';
const PYTHON = process.env.SONOPLAY_PYTHON || 'python3';
const CONFIG_PATH = process.env.SONOPLAY_TEST_CONFIG || '/tmp/sp-test-config';

module.exports = defineConfig({
  testDir: './tests',
  // Keep run artifacts off the /c host mount (rmdir there throws EIO).
  outputDir: '/tmp/sonoplay-pw-results',
  timeout: 30000,
  expect: { timeout: 5000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${PORT}`,
    actionTimeout: 5000,
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `HTTP_PORT=${PORT} CONFIG_PATH=${CONFIG_PATH} LOG_LEVEL=WARNING PYTHONPATH=. ${PYTHON} main.py`,
    cwd: path.resolve(__dirname, '..'),
    url: `http://localhost:${PORT}/health`,
    reuseExistingServer: true,
    timeout: 30000,
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
