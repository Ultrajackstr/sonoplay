// Characterization tests for the Discovered Devices page.
//
// These pin the CURRENT behavior so the deferred refactors (sendCommand dedup,
// incremental re-render, CSS dedup) can be proven regression-free: do the
// refactor, re-run, everything stays green.
//
// Icon assertions check the DOM class (not glyph rendering) so they don't
// depend on the FontAwesome web-font finishing loading.
const { test, expect } = require('@playwright/test');
const { playing, paused, stopped, mockApi, mockExternal } = require('./helpers');

// Serve /api/devices so the no-wait variant returns the CURRENT state instantly
// while the wait=1 long-poll idles for `longPollMs` (no events fire once a
// device is paused/idle, so the real server waits out its ~5s timeout). The
// returned device flips to paused `flipAfterMs` after the pause command lands,
// modelling the backend's periodic check loop.
async function mockLaggyBackend(page, { flipAfterMs = 500, longPollMs = 5000 } = {}) {
  let isPaused = false;
  await mockExternal(page);
  await page.route('**/api/plex-status', (r) => r.fulfill({ json: { connected: true } }));
  await page.route('**/api/onboarding', (r) => r.fulfill({ json: { eligible: false, enabled: false, completed: true, steps: {} } }));
  await page.route('**/api/virtual-devices', (r) => r.fulfill({ json: { groups: [], total: 0 } }));
  await page.route(/\/api\/devices(\?.*)?$/, async (r) => {
    if (r.request().url().includes('wait=1')) {
      await new Promise((res) => setTimeout(res, longPollMs)); // idle long-poll
    }
    return r.fulfill({ json: { devices: [isPaused ? paused() : playing()], total_devices: 1 } });
  });
  await page.route('**/player/playback/pause**', (r) => {
    setTimeout(() => { isPaused = true; }, flipAfterMs); // backend reflects it late
    return r.fulfill({ status: 200, body: '' });
  });
}

const goto = (page) => page.goto('/', { waitUntil: 'domcontentloaded' });

test.describe('discovered devices — card render states', () => {
  test('playing device shows now-playing block + a pause main button', async ({ page }) => {
    await mockApi(page, { devices: [playing()] });
    await goto(page);
    const card = page.locator('.device-card').first();
    await expect(card.locator('.now-playing-track')).toHaveText('Song A');
    await expect(card.locator('.playback-controls .playback-btn')).toHaveCount(3);
    await expect(card.locator('.playback-btn.main i')).toHaveClass(/fa-pause/);
    await expect(card.locator('.device-status')).toContainText('Now Playing');
  });

  test('paused device keeps now-playing + controls and shows a play button', async ({ page }) => {
    await mockApi(page, { devices: [paused()] });
    await goto(page);
    const card = page.locator('.device-card').first();
    await expect(card.locator('.now-playing-track')).toHaveText('Song A');
    await expect(card.locator('.playback-controls .playback-btn')).toHaveCount(3);
    await expect(card.locator('.playback-btn.main i')).toHaveClass(/fa-play/);
    await expect(card.locator('.device-status')).toContainText('Paused');
  });

  test('stopped device hides the now-playing block and controls', async ({ page }) => {
    await mockApi(page, { devices: [stopped()] });
    await goto(page);
    await expect(page.locator('.device-card')).toHaveCount(1);
    await expect(page.locator('.now-playing')).toHaveCount(0);
    await expect(page.locator('.playback-controls')).toHaveCount(0);
  });
});

test.describe('discovered devices — sendCommand wiring', () => {
  async function captureFirstPlaybackRequest(page, buttonSelector, deviceFixture) {
    await mockApi(page, { devices: [deviceFixture] });
    const reqs = [];
    await page.route('**/player/playback/**', (r) => {
      reqs.push(r.request());
      return r.fulfill({ status: 200, body: '' });
    });
    await goto(page);
    await page.locator(buttonSelector).first().click();
    await expect.poll(() => reqs.length).toBeGreaterThan(0);
    return reqs[0];
  }

  test('pause button -> GET /player/playback/pause with target header', async ({ page }) => {
    const req = await captureFirstPlaybackRequest(page, '.playback-btn.main', playing());
    expect(req.method()).toBe('GET');
    expect(new URL(req.url()).pathname).toBe('/player/playback/pause');
    expect(req.headers()['x-plex-target-client-identifier']).toBe('dev-1');
  });

  test('play button (when paused) -> GET /player/playback/play', async ({ page }) => {
    const req = await captureFirstPlaybackRequest(page, '.playback-btn.main', paused());
    expect(new URL(req.url()).pathname).toBe('/player/playback/play');
  });

  test('previous / next buttons -> skipPrevious / skipNext', async ({ page }) => {
    await mockApi(page, { devices: [playing()] });
    const paths = [];
    await page.route('**/player/playback/**', (r) => {
      paths.push(new URL(r.request().url()).pathname);
      return r.fulfill({ status: 200, body: '' });
    });
    await goto(page);
    const btns = page.locator('.playback-controls .playback-btn');
    await btns.nth(0).click(); // previous
    await btns.nth(2).click(); // next
    await expect.poll(() => paths.length).toBe(2);
    expect(paths).toContain('/player/playback/skipPrevious');
    expect(paths).toContain('/player/playback/skipNext');
  });
});

test.describe('discovered devices — CSS contract (for the dedup)', () => {
  test('.icon-btn keeps its 36x36 sizing', async ({ page }) => {
    // .icon-btn has exactly one rule (the one being deduped into the stylesheet);
    // a botched move would drop the rule and the button would fall back to its
    // content-sized default rather than 36x36.
    await mockApi(page, { devices: [playing()] });
    await goto(page);
    const box = await page.locator('.device-card .icon-btn').first().evaluate((el) => {
      const cs = getComputedStyle(el);
      return { width: cs.width, height: cs.height };
    });
    expect(box).toEqual({ width: '36px', height: '36px' });
  });

  test('.device-controls lays out as a flex row', async ({ page }) => {
    await mockApi(page, { devices: [playing()] });
    await goto(page);
    const display = await page.locator('.device-controls').first().evaluate((el) => getComputedStyle(el).display);
    expect(display).toBe('flex');
  });
});

test.describe('discovered devices — track quality line', () => {
  test('shows codec / bitrate / sample rate / channels / Direct', async ({ page }) => {
    await mockApi(page, { devices: [playing()] });
    await goto(page);
    const q = page.locator('.device-card .now-playing-quality');
    await expect(q).toContainText('FLAC');
    await expect(q).toContainText('1411 kbps');
    await expect(q).toContainText('44.1 kHz');
    await expect(q).toContainText('Stereo');
    await expect(q).toContainText('Direct');
  });

  test('shows Transcoded when the track is being transcoded', async ({ page }) => {
    const d = playing();
    d.current_track = { ...d.current_track, transcode: true };
    await mockApi(page, { devices: [d] });
    await goto(page);
    await expect(page.locator('.device-card .now-playing-quality')).toContainText('Transcoded');
  });
});

test.describe('discovered devices — device capabilities modal', () => {
  test('opening details shows formats, volume range and features', async ({ page }) => {
    await mockApi(page, { devices: [playing()] });
    await page.route('**/api/devices/*/capabilities', (r) => r.fulfill({ json: {
      manufacturer: 'Sennheiser', model: 'AMBEO',
      formats: ['audio/flac', 'audio/mpeg', 'audio/L16'],
      volume: { min: 0, max: 100, step: 1 },
      gapless: true, can_seek: true,
    } }));
    await goto(page);
    await page.locator('.device-card .device-name').click(); // bubbles to showDeviceDetails
    const body = page.locator('.swal2-html-container');
    await expect(body).toContainText('audio/flac');
    await expect(body).toContainText('Volume range');
    await expect(body).toContainText('Gapless');
  });
});

test.describe('discovered devices — volume slider', () => {
  test('renders the slider at the device volume', async ({ page }) => {
    await mockApi(page, { devices: [playing({ volume: 35 })] });
    await goto(page);
    await expect(page.locator('.device-card .volume-slider')).toHaveValue('35');
  });

  test('moving the slider sends setParameters with the volume + target header', async ({ page }) => {
    await mockApi(page, { devices: [playing()] });
    let req = null;
    await page.route('**/player/playback/setParameters**', (r) => {
      req = r.request();
      return r.fulfill({ status: 200, body: '' });
    });
    await goto(page);
    await page.locator('.volume-slider').first().evaluate((el) => {
      el.value = '70';
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await expect.poll(() => req && new URL(req.url()).searchParams.get('volume')).toBe('70');
    expect(req.headers()['x-plex-target-client-identifier']).toBe('dev-1');
  });

  test('the dashboard long-polls /api/devices?wait=1', async ({ page }) => {
    await mockApi(page, { devices: [playing()] });
    const reqPromise = page.waitForRequest(
      (r) => r.url().includes('/api/devices') && r.url().includes('wait=1'),
      { timeout: 5000 }
    );
    await goto(page);
    expect(await reqPromise).toBeTruthy();
  });

  test('reflects an externally-changed volume on the next poll', async ({ page }) => {
    let vol = 40;
    await mockExternal(page);
    await page.route(/\/api\/devices(\?.*)?$/, (r) =>
      r.fulfill({ json: { devices: [playing({ volume: vol })], total_devices: 1 } }));
    await page.route('**/api/plex-status', (r) => r.fulfill({ json: { connected: true } }));
    await page.route('**/api/onboarding', (r) => r.fulfill({ json: { eligible: false, enabled: false, completed: true, steps: {} } }));
    await goto(page);
    await expect(page.locator('.volume-slider')).toHaveValue('40');
    vol = 70; // external change, e.g. from the phone
    await page.evaluate(() => window.refreshDevices());
    await expect(page.locator('.volume-slider')).toHaveValue('70');
  });
});

test.describe('discovered devices — command latency', () => {
  test('pause reflects promptly without waiting out the idle long-poll', async ({ page }) => {
    // The pause lands in the backend ~500ms after the command; the idle
    // long-poll would take 5s. The card must flip to the play (paused) icon
    // well before then -- i.e. via a fast no-wait re-poll, not the long-poll.
    await mockLaggyBackend(page, { flipAfterMs: 500, longPollMs: 5000 });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const main = page.locator('.device-card .playback-btn.main i');
    await expect(main).toHaveClass(/fa-pause/);

    await page.locator('.device-card .playback-btn.main').click(); // pause
    await expect(main).toHaveClass(/fa-play/, { timeout: 2500 });
  });
});

test.describe('discovered devices — re-render skipped when unchanged', () => {
  test('a re-poll with identical data preserves the existing card nodes', async ({ page }) => {
    await mockApi(page, { devices: [stopped()] }); // static card: no advancing progress
    await goto(page);
    const card = page.locator('.device-card').first();
    await card.waitFor();
    // Mark the live node; if the grid is rebuilt, the marker is lost.
    await card.evaluate((el) => el.setAttribute('data-pw-marker', '1'));
    // A second poll with the same payload must not rebuild the grid.
    await page.evaluate(() => window.refreshDevices());
    await expect(page.locator('.device-card[data-pw-marker="1"]')).toHaveCount(1);
  });
});

test.describe('discovered devices — modal click zone (header only)', () => {
  async function withCaps(page, dev) {
    await mockApi(page, { devices: [dev] });
    await page.route('**/api/devices/*/capabilities', (r) =>
      r.fulfill({ json: { formats: [], volume: {}, gapless: false, can_seek: false } }));
  }

  test('clicking the header opens the details modal', async ({ page }) => {
    await withCaps(page, playing());
    await goto(page);
    await page.locator('.device-card .device-header').click();
    await expect(page.locator('.swal2-popup')).toBeVisible();
  });

  test('clicking the now-playing area does NOT open the modal', async ({ page }) => {
    await withCaps(page, playing());
    await goto(page);
    await page.locator('.device-card .now-playing-track').click();
    await page.waitForTimeout(300);
    await expect(page.locator('.swal2-popup')).toHaveCount(0);
  });
});

test.describe('discovered devices — mute button', () => {
  test('mute (volume>0) sends setParameters volume=0 with the target header', async ({ page }) => {
    await mockApi(page, { devices: [playing({ volume: 40 })] });
    let req = null;
    await page.route('**/player/playback/setParameters**', (r) => {
      req = r.request();
      return r.fulfill({ status: 200, body: '' });
    });
    await goto(page);
    await page.locator('.device-card .volume-mute-btn').click();
    await expect.poll(() => req && new URL(req.url()).searchParams.get('volume')).toBe('0');
    expect(req.headers()['x-plex-target-client-identifier']).toBe('dev-1');
  });

  test('unmute (volume==0) restores a non-zero volume', async ({ page }) => {
    await mockApi(page, { devices: [playing({ volume: 0 })] });
    let vol = null;
    await page.route('**/player/playback/setParameters**', (r) => {
      vol = new URL(r.request().url()).searchParams.get('volume');
      return r.fulfill({ status: 200, body: '' });
    });
    await goto(page);
    await page.locator('.device-card .volume-mute-btn').click();
    await expect.poll(() => vol !== null && parseInt(vol, 10) > 0).toBe(true);
  });
});

test.describe('discovered devices — seekbar', () => {
  test('clicking the progress bar seeks to that fraction of the track', async ({ page }) => {
    await mockApi(page, { devices: [playing()] }); // duration 200000ms
    let req = null;
    await page.route('**/player/playback/seekTo**', (r) => {
      req = r.request();
      return r.fulfill({ status: 200, body: '' });
    });
    await goto(page);
    const bar = page.locator('.device-card .progress-bar');
    const box = await bar.boundingBox();
    await bar.click({ position: { x: box.width * 0.75, y: Math.max(1, box.height / 2) } });
    await expect.poll(() => req && new URL(req.url()).searchParams.get('offset')).not.toBeNull();
    const offset = parseInt(new URL(req.url()).searchParams.get('offset'), 10);
    expect(offset).toBeGreaterThan(135000); // ~75% of 200000 = 150000, tolerance for click precision
    expect(offset).toBeLessThan(165000);
  });

  test('the progress bar + fill render with a visible height', async ({ page }) => {
    // Regression: enlarging the click target with padding under box-sizing:
    // border-box collapsed the 4px track + fill to 0px (clickable but invisible).
    await mockApi(page, { devices: [playing()] });
    await goto(page);
    const bar = await page.locator('.device-card .progress-bar').evaluate((el) => el.getBoundingClientRect().height);
    const fill = await page.locator('.device-card .progress-fill').evaluate((el) => el.getBoundingClientRect().height);
    expect(fill).toBeGreaterThanOrEqual(3);  // the visible 4px track, not a collapsed sliver
    expect(bar).toBeGreaterThanOrEqual(12);   // enlarged click target (4px track + padding)
  });
});
