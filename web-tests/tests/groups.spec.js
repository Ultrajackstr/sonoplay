// Tests for the Groups (virtual-devices) page, bringing it to parity with the
// Devices page: a reactive volume slider, the /api/virtual-devices?wait=1
// long-poll, and the post-command fast-poll so play/pause registers promptly.
const { test, expect } = require('@playwright/test');
const { groupPlaying, groupPaused, mockGroupsApi, mockLaggyGroupsBackend } = require('./helpers');

const goto = (page) => page.goto('/virtual-devices', { waitUntil: 'domcontentloaded' });

test.describe('groups — card render', () => {
  test('a playing group shows the now-playing block + a pause main button', async ({ page }) => {
    await mockGroupsApi(page, { groups: [groupPlaying()] });
    await goto(page);
    const card = page.locator('.device-card').first();
    await expect(card.locator('.now-playing-track')).toHaveText('Song A');
    await expect(card.locator('.playback-btn.main i')).toHaveClass(/fa-pause/);
  });
});

test.describe('groups — volume slider', () => {
  test('renders the slider at the group volume', async ({ page }) => {
    await mockGroupsApi(page, { groups: [groupPlaying({ volume: 35 })] });
    await goto(page);
    await expect(page.locator('.device-card .volume-slider')).toHaveValue('35');
  });

  test('moving the slider sends setParameters with the group uuid + volume', async ({ page }) => {
    await mockGroupsApi(page, { groups: [groupPlaying()] });
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
    expect(req.headers()['x-plex-target-client-identifier']).toBe('grp-1');
  });
});

test.describe('groups — long-poll', () => {
  test('the page long-polls /api/virtual-devices?wait=1', async ({ page }) => {
    await mockGroupsApi(page, { groups: [groupPlaying()] });
    const reqPromise = page.waitForRequest(
      (r) => r.url().includes('/api/virtual-devices') && r.url().includes('wait=1'),
      { timeout: 5000 }
    );
    await goto(page);
    expect(await reqPromise).toBeTruthy();
  });
});

test.describe('groups — command latency', () => {
  test('pause reflects promptly without waiting out the idle long-poll', async ({ page }) => {
    // The group's member flips to paused ~500ms after the command; the idle
    // long-poll would take 5s. The card must flip to the play (paused) icon
    // well before then -- via the no-wait fast-poll, not the long-poll.
    await mockLaggyGroupsBackend(page, { flipAfterMs: 500, longPollMs: 5000 });
    await goto(page);
    const main = page.locator('.device-card .playback-btn.main i');
    await expect(main).toHaveClass(/fa-pause/);

    await page.locator('.device-card .playback-btn.main').click(); // pause
    await expect(main).toHaveClass(/fa-play/, { timeout: 2500 });
  });
});
