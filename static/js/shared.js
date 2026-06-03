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
