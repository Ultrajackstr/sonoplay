// Shared fixtures + request mocking for the web UI tests.
//
// The page fetches /api/devices, /api/plex-status and /api/onboarding on load;
// we stub all three so rendering is deterministic and the onboarding overlay
// (which would otherwise intercept clicks) stays hidden.
//
// We also stub the external CDN assets (SweetAlert2, FontAwesome, Google Fonts)
// so tests are hermetic and don't depend on outbound network. SweetAlert2 is
// replaced with a tiny shim that records fire() calls AND injects the standard
// .swal2-* DOM, so both call-based and DOM-based assertions work.

function device(over = {}) {
  return {
    uuid: 'dev-1',
    name: 'Test Speaker',
    ip: '10.0.0.5',
    model: 'TestModel',
    binded: true,
    status: 'playing',
    current_track: {
      title: 'Song A', artist: 'Artist A', duration: 200000, position_ms: 50000,
      media: { container: 'flac', codec: 'flac', bitrate_kbps: 1411, sample_rate_hz: 44100, channels: 2 },
      transcode: false,
    },
    artwork_urls: [],
    play_count: 1,
    play_duration_ms: 1000,
    current_session_ms: 50000,
    volume: 40,
    ...over,
  };
}

function devicesPayload(devices) {
  return { devices, total_devices: devices.length };
}

// Builders for the three states the card-render logic distinguishes.
const playing = (over = {}) => device({ status: 'playing', ...over });
const paused = (over = {}) => device({ status: 'online', ...over }); // online + current_track => paused
const stopped = (over = {}) => device({ status: 'online', current_track: null, ...over });
const unlinked = (over = {}) => device({ binded: false, status: 'online', current_track: null, pin: 'WXYZ', pin_id: 'pin-1', ...over });

const NEUTRAL_ONBOARDING = {
  enabled: false, completed: true, completed_at: null, steps: {},
  eligible: false, stored_device_count: 0, user_configured_device_count: 0, virtual_device_count: 0,
};

// Minimal SweetAlert2 replacement: records calls and renders the standard
// .swal2-popup / .swal2-title / .swal2-html-container so the app's flows and
// our assertions both work without the real (CDN-hosted) library.
const SWAL_SHIM = `
window.Swal = {
  _calls: [],
  fire(opts) {
    opts = (typeof opts === 'object' && opts) ? opts : { title: arguments[0], text: arguments[1] };
    this._calls.push(opts);
    document.querySelectorAll('.swal2-container').forEach(function (e) { e.remove(); });
    var c = document.createElement('div'); c.className = 'swal2-container';
    var pop = document.createElement('div'); pop.className = 'swal2-popup';
    var title = document.createElement('h2'); title.className = 'swal2-title'; title.textContent = opts.title || '';
    var html = document.createElement('div'); html.className = 'swal2-html-container'; html.innerHTML = opts.html || (opts.text || '');
    pop.appendChild(title); pop.appendChild(html); c.appendChild(pop); document.body.appendChild(c);
    // Tests set window.__swalConfirmNext = true to simulate the user confirming.
    var confirmed = !!window.__swalConfirmNext;
    return Promise.resolve({ isConfirmed: confirmed, isDismissed: !confirmed, value: undefined });
  },
  showLoading() {},
  close() { document.querySelectorAll('.swal2-container').forEach(function (e) { e.remove(); }); },
  isVisible() { return !!document.querySelector('.swal2-popup'); },
  DismissReason: { cancel: 'cancel', backdrop: 'backdrop', close: 'close', timer: 'timer' },
};
`;

async function mockExternal(page) {
  // SweetAlert2 script -> shim (register last so it wins over the CSS rule).
  await page.route(/(sweetalert2.*\.css|font-awesome|all\.min\.css|fonts\.googleapis|fonts\.gstatic)/, (r) =>
    r.fulfill({ contentType: 'text/css', body: '' })
  );
  await page.route(/sweetalert2.*\.js/, (r) =>
    r.fulfill({ contentType: 'application/javascript', body: SWAL_SHIM })
  );
}

async function mockApi(page, { devices = [], plexConnected = true } = {}) {
  await mockExternal(page);
  // Match /api/devices and /api/devices?wait=1 (the long-poll), but NOT the
  // /api/devices/{uuid}/capabilities sub-path.
  await page.route(/\/api\/devices(\?.*)?$/, (r) => r.fulfill({ json: devicesPayload(devices) }));
  await page.route('**/api/virtual-devices', (r) => r.fulfill({ json: { groups: [], total: 0 } }));
  await page.route('**/api/plex-status', (r) => r.fulfill({ json: { connected: plexConnected } }));
  await page.route('**/api/onboarding', (r) => r.fulfill({ json: NEUTRAL_ONBOARDING }));
}

// --- Groups (virtual-devices) page fixtures + mocking -----------------------
// The Groups page (/virtual-devices) fetches /api/virtual-devices, which carries
// {virtual_devices, physical_devices}. A group's play state is derived from its
// members' statuses; volume is the unified 0-100 aggregate the slider binds to.

function group(over = {}) {
  return {
    uuid: 'grp-1', name: 'Living Room', model: 'SonoPlay Group', ip: '',
    status: 'all_available', status_label: 'All Online', status_class: 'all-available',
    is_heterogeneous: false, binded: true, pin_id: '',
    volume: 40, current_session_ms: 50000,
    members: [{ uuid: 'm-1', name: 'Speaker One', ip: '10.0.0.5', status: 'playing', available: true, volume: 40 }],
    member_count: 1, missing_members: [],
    current_track: {
      title: 'Song A', artist: 'Artist A', duration: 200000,
      media: { container: 'flac', codec: 'flac', bitrate_kbps: 1411, sample_rate_hz: 44100, channels: 2 },
      transcode: false,
    },
    ...over,
  };
}

const memberPaused = { uuid: 'm-1', name: 'Speaker One', ip: '10.0.0.5', status: 'paused', available: true, volume: 40 };
const groupPlaying = (over = {}) => group(over);
const groupPaused = (over = {}) => group({ members: [memberPaused], ...over });

function groupsPayload(groups, physical = []) {
  return { virtual_devices: groups, physical_devices: physical };
}

async function mockGroupsApi(page, { groups = [], plexConnected = true } = {}) {
  await mockExternal(page);
  await page.route(/\/api\/virtual-devices(\?.*)?$/, (r) => r.fulfill({ json: groupsPayload(groups) }));
  await page.route(/\/api\/devices(\?.*)?$/, (r) => r.fulfill({ json: devicesPayload([]) }));
  await page.route('**/api/plex-status', (r) => r.fulfill({ json: { connected: plexConnected } }));
  await page.route('**/api/onboarding', (r) => r.fulfill({ json: NEUTRAL_ONBOARDING }));
}

// Models the real timing for the Groups command-latency test: wait=1 idles
// ~5s (no events once paused), and the group's member flips to paused
// ~flipAfterMs after the pause command lands (its check loop). The card must
// update promptly via the no-wait fast-poll, not by waiting out the long-poll.
async function mockLaggyGroupsBackend(page, { flipAfterMs = 500, longPollMs = 5000 } = {}) {
  let isPaused = false;
  await mockExternal(page);
  await page.route('**/api/plex-status', (r) => r.fulfill({ json: { connected: true } }));
  await page.route('**/api/onboarding', (r) => r.fulfill({ json: NEUTRAL_ONBOARDING }));
  await page.route(/\/api\/devices(\?.*)?$/, (r) => r.fulfill({ json: devicesPayload([]) }));
  await page.route(/\/api\/virtual-devices(\?.*)?$/, async (r) => {
    if (r.request().url().includes('wait=1')) {
      await new Promise((res) => setTimeout(res, longPollMs));
    }
    return r.fulfill({ json: groupsPayload([isPaused ? groupPaused() : groupPlaying()]) });
  });
  await page.route('**/player/playback/pause**', (r) => {
    setTimeout(() => { isPaused = true; }, flipAfterMs);
    return r.fulfill({ status: 200, body: '' });
  });
}

module.exports = {
  device, devicesPayload, playing, paused, stopped, unlinked, mockApi, mockExternal,
  group, groupPlaying, groupPaused, groupsPayload, mockGroupsApi, mockLaggyGroupsBackend,
};
