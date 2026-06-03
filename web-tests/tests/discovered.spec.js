// Characterization tests for the Discovered Devices page.
//
// These pin the CURRENT behavior so the deferred refactors (sendCommand dedup,
// incremental re-render, CSS dedup) can be proven regression-free: do the
// refactor, re-run, everything stays green.
//
// Icon assertions check the DOM class (not glyph rendering) so they don't
// depend on the FontAwesome web-font finishing loading.
const { test, expect } = require('@playwright/test');
const { playing, paused, stopped, mockApi } = require('./helpers');

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
