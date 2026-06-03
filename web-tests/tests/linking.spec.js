// Characterization of the Plex PIN-link flow (checkLinked).
//
// Pins the request + PIN-dialog behavior so the deferred "extract the PIN flow
// into a shared helper" refactor can be proven regression-free.
const { test, expect } = require('@playwright/test');
const { unlinked, mockApi } = require('./helpers');

const goto = (page) => page.goto('/', { waitUntil: 'domcontentloaded' });

test.describe('discovered devices — Plex link (PIN) flow', () => {
  test('an unlinked device shows a Link button', async ({ page }) => {
    await mockApi(page, { devices: [unlinked()], plexConnected: false });
    await goto(page);
    await expect(page.locator('.device-card .control-btn.primary')).toContainText('Link');
  });

  test('clicking Link POSTs / with the uuid and shows the returned PIN', async ({ page }) => {
    await mockApi(page, { devices: [unlinked()], plexConnected: false });

    let postBody = null;
    // Intercept only the root path; POST = the form submit (stub it), GET = the
    // page navigation (let it hit the real app).
    await page.route(
      (url) => {
        try { return new URL(url).pathname === '/'; } catch { return false; }
      },
      (route, request) => {
        if (request.method() === 'POST') {
          postBody = request.postData();
          return route.fulfill({ json: { status: 'not_linked', pin: 'WXYZ', pin_id: 'pin-1' } });
        }
        return route.fallback();
      }
    );

    await goto(page);
    await page.locator('.device-card .control-btn.primary').click();

    // The PIN dialog (SweetAlert2) appears with the code from the response.
    await expect(page.locator('.swal2-popup')).toBeVisible();
    await expect(page.locator('.swal2-title')).toContainText('Link to Plex');
    await expect(page.locator('.swal2-html-container')).toContainText('WXYZ');

    expect(postBody).toContain('dev-1');
    expect(postBody).toContain('check_status');
  });
});
