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
