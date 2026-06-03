/**
 * Shared utility functions for SonoPlay templates.
 */

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} value - The text to escape
 * @returns {string} The escaped text
 */
function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Format milliseconds as human-readable duration (e.g., "1:05:30" or "3:45").
 * @param {number} ms - Duration in milliseconds
 * @returns {string} Formatted duration string
 */
function formatDuration(ms) {
    if (!ms) return '0:00';
    const seconds = Math.floor((ms / 1000) % 60);
    const minutes = Math.floor((ms / (1000 * 60)) % 60);
    const hours = Math.floor((ms / (1000 * 60 * 60)));
    const secondsStr = seconds.toString().padStart(2, '0');
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secondsStr}`;
    }
    return `${minutes}:${secondsStr}`;
}

/**
 * Send a transport command to a device or group, then run onSuccess on success.
 * Shared by the device and group pages (pinned by test_webui_playback_routes).
 * @param {string} uuid - target client identifier
 * @param {string} command - UI token (previous|pause|play|next) or a canonical route name
 * @param {Function} [onSuccess] - invoked after a successful command (e.g. a refresh)
 */
async function sendPlaybackCommand(uuid, command, onSuccess) {
    const endpoints = { previous: 'skipPrevious', pause: 'pause', play: 'play', next: 'skipNext' };
    const endpoint = endpoints[command] || command;
    try {
        const response = await fetch(`/player/playback/${endpoint}?commandID=0&type=music`, {
            method: 'GET',
            headers: {
                'X-Plex-Target-Client-Identifier': uuid,
                'X-Plex-Client-Identifier': 'sonoplay'
            }
        });
        if (!response.ok) throw new Error('Command failed');
        if (typeof onSuccess === 'function') onSuccess();
    } catch (error) {
        console.error('Command error:', error);
        Swal.fire('Error', 'Failed to send command', 'error');
    }
}

/**
 * Show the Plex PIN dialog for data.pin; on confirm, POST the pin_id back to
 * verify and report success/retry. Shared by the link + relink flows on both
 * the device and group pages.
 * @param {string} uuid - target client identifier
 * @param {{pin: string, pin_id: string}} data - from the link/relink POST response
 * @param {{title: string, successTitle: string, successText: string}} opts - labels
 */
async function confirmPlexPin(uuid, data, opts) {
    const result = await Swal.fire({
        icon: 'info',
        title: opts.title,
        html: `
            <p>Visit <a href="https://plex.tv/link" target="_blank" style="color: #e5a00d; font-weight: bold;">plex.tv/link</a></p>
            <p style="margin-top: 1rem;">Enter this code:</p>
            <div style="font-size: 2rem; font-weight: bold; letter-spacing: 0.2rem; font-family: 'JetBrains Mono', monospace; margin: 1rem 0;">${escapeHtml(String(data.pin))}</div>
        `,
        confirmButtonText: "I've Entered the Code",
        showCancelButton: true,
        cancelButtonText: 'Cancel'
    });
    if (!result.isConfirmed) return;
    Swal.fire({ title: 'Checking...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });
    const verifyForm = new FormData();
    verifyForm.append('uuid', uuid);
    verifyForm.append('pin_id', data.pin_id);
    const verifyResponse = await fetch('/', { method: 'POST', body: verifyForm });
    if (verifyResponse.ok) {
        const verifyData = await verifyResponse.json();
        if (verifyData.status === 'linked') {
            Swal.fire({ icon: 'success', title: opts.successTitle, text: opts.successText, timer: 2000, showConfirmButton: false });
        } else {
            Swal.fire({ icon: 'warning', title: 'Not Yet Linked', text: 'Please enter the code at plex.tv/link and try again.' });
        }
    }
}

/**
 * Set a container's innerHTML only when it changed. Lets the 5s poll skip
 * rebuilding the card grid -- and resetting focus/hover and the progress-bar
 * transition -- when the rendered markup is identical to what's already shown.
 * (Actively-playing cards still update, since their progress markup changes.)
 * @param {HTMLElement} grid
 * @param {string} html
 */
function setGridHtml(grid, html) {
    if (!grid || html === grid._lastHtml) return;
    grid._lastHtml = html;
    grid.innerHTML = html;
}

/**
 * Build a one-line audio-quality summary from a track's media info, e.g.
 * "FLAC · 1411 kbps · 44.1 kHz · Stereo · Direct". Returns '' when no info.
 * @param {object} media - {container, codec, bitrate_kbps, sample_rate_hz, channels}
 * @param {boolean|null} transcode - true = transcoded, false = direct, null = unknown
 */
function formatTrackQuality(media, transcode) {
    media = media || {};
    const parts = [];
    const fmt = media.container || media.codec;
    if (fmt) parts.push(String(fmt).toUpperCase());
    if (media.bitrate_kbps) parts.push(`${media.bitrate_kbps} kbps`);
    if (media.sample_rate_hz) {
        const khz = media.sample_rate_hz / 1000;
        parts.push(`${Number.isInteger(khz) ? khz : khz.toFixed(1)} kHz`);
    }
    if (media.channels === 1) parts.push('Mono');
    else if (media.channels === 2) parts.push('Stereo');
    else if (media.channels) parts.push(`${media.channels}ch`);
    if (transcode === true) parts.push('Transcoded');
    else if (transcode === false) parts.push('Direct');
    return parts.join(' · ');
}

/**
 * Build the HTML capabilities block for the device-details modal from the
 * /api/devices/{uuid}/capabilities payload. Returns '' when nothing useful.
 * @param {object} caps - {formats, volume:{min,max,step}, gapless, can_seek}
 */
function formatDeviceCapabilities(caps) {
    if (!caps) return '';
    const rows = [];
    if (Array.isArray(caps.formats) && caps.formats.length) {
        rows.push(`<p><strong>Plays:</strong> ${caps.formats.map(escapeHtml).join(', ')}</p>`);
    }
    const v = caps.volume || {};
    if (v.max != null) {
        const step = (v.step != null && v.step !== 1) ? ` (step ${escapeHtml(String(v.step))})` : '';
        rows.push(`<p><strong>Volume range:</strong> ${escapeHtml(String(v.min))}–${escapeHtml(String(v.max))}${step}</p>`);
    }
    const features = [];
    if (caps.gapless) features.push('Gapless');
    if (caps.can_seek) features.push('Seek');
    if (features.length) rows.push(`<p><strong>Supports:</strong> ${features.join(', ')}</p>`);
    return rows.join('');
}

/**
 * Set a device's volume (0-100) via the Plex setParameters transport route.
 * Fire-and-forget: errors are logged, not toasted (slider drags are frequent).
 */
async function setDeviceVolume(uuid, volume) {
    try {
        const response = await fetch(`/player/playback/setParameters?commandID=0&type=music&volume=${encodeURIComponent(volume)}`, {
            method: 'GET',
            headers: {
                'X-Plex-Target-Client-Identifier': uuid,
                'X-Plex-Client-Identifier': 'sonoplay'
            }
        });
        if (!response.ok) throw new Error('Volume failed');
    } catch (error) {
        console.error('Volume error:', error);
    }
}

// Volume-slider interaction state, shared by the device + group grids. While
// the user drags a slider we suppress the grid re-render (it would recreate the
// <input> mid-drag and interrupt the drag); the flag clears ~1.5s after the
// last interaction, by which point the poll has reconciled the real volume so
// the next render shows the settled value. The render loops gate on
// isVolumeInteracting() rather than a bare cross-script variable.
let _volumeInteracting = false;
let _volumeInteractTimer = null;
function isVolumeInteracting() { return _volumeInteracting; }
function markVolumeInteracting() {
    _volumeInteracting = true;
    clearTimeout(_volumeInteractTimer);
    _volumeInteractTimer = setTimeout(() => { _volumeInteracting = false; }, 1500);
}
function onVolumeInput(el) {
    markVolumeInteracting();
    const label = el.parentElement.querySelector('.volume-value');
    if (label) label.textContent = el.value;
}
function onVolumeChange(uuid, el) {
    markVolumeInteracting();
    setDeviceVolume(uuid, parseInt(el.value, 10));
}

// Toggle "mute" by setting volume to 0 and restoring the prior level on unmute.
// (True UPnP SetMute isn't reliably settable across renderers; volume-0 is
// guaranteed to silence via the proven setParameters path.) The button icon is
// derived from the polled volume (0 = muted), so it also reflects a mute/volume
// change made from the phone. Shared by the device + group cards.
const _preMuteVolume = {};
function toggleMute(uuid, btn) {
    const control = btn.closest('.volume-control');
    const slider = control ? control.querySelector('.volume-slider') : null;
    const current = slider ? parseInt(slider.value, 10) : 0;
    const target = current > 0 ? 0 : (_preMuteVolume[uuid] || 30);
    if (current > 0) _preMuteVolume[uuid] = current;
    markVolumeInteracting();              // hold off the re-render so the optimistic UI sticks
    setDeviceVolume(uuid, target);
    if (slider) slider.value = target;
    const label = control ? control.querySelector('.volume-value') : null;
    if (label) label.textContent = target;
    const icon = btn.querySelector('i');
    if (icon) icon.className = target === 0 ? 'fas fa-volume-xmark' : 'fas fa-volume-high';
}

// Seek a device/group via the Plex seekTo route (offset in ms). adapter.seek
// updates state immediately and the timeline subscription keeps Plex in sync,
// so a UI seek stays in sync with the device + Plexamp. Shared by both cards.
async function seekDevice(uuid, offsetMs) {
    try {
        const response = await fetch(`/player/playback/seekTo?commandID=0&type=music&offset=${encodeURIComponent(offsetMs)}`, {
            method: 'GET',
            headers: {
                'X-Plex-Target-Client-Identifier': uuid,
                'X-Plex-Client-Identifier': 'sonoplay'
            }
        });
        if (!response.ok) throw new Error('Seek failed');
    } catch (error) {
        console.error('Seek error:', error);
    }
}

// Click-to-seek: map the click's x within the progress bar to a track position
// and seek there, with an optimistic fill update (the poll reconciles via the
// elapsed_jump event). A track with no/zero duration is a no-op.
function seekToPosition(uuid, event, durationMs) {
    if (!durationMs || durationMs <= 0) return;
    const bar = event.currentTarget;
    const rect = bar.getBoundingClientRect();
    if (!rect.width) return;
    const frac = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    seekDevice(uuid, Math.round(frac * durationMs));
    const fill = bar.querySelector('.progress-fill');
    if (fill) fill.style.width = `${frac * 100}%`;
}
