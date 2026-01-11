# SonoPlex

> **The missing bridge between Plexamp and your DLNA speakers**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)

---

## The Problem

You love Plexamp. You have great DLNA speakers (Sonos, Yamaha, Denon, smart TVs). But **Plexamp can't cast to DLNA/UPnP devices**.

The community has been asking for this for years:

> *"Frustrating that PlexAmp can't render to UPnP devices... I SO VERY BADLY wish PlexAmp would add UPnP support"*

> *"Is there a way to get PlexAmp to find network devices?"*

## The Solution

**SonoPlex makes your DLNA speakers appear as Plex players.** Cast from Plexamp to any DLNA device on your network.

```
Plexamp → SonoPlex → Your DLNA Speakers
```

That's it. No complicated setup. No Raspberry Pi projects. Just works.

---

## Quick Start

### Docker (Recommended)

```bash
docker run -d \
  --name sonoplex \
  --network host \
  --restart unless-stopped \
  -v /path/to/config:/config \
  ghcr.io/aquantumofdonuts/sonoplex:stable
```

Or with Docker Compose:

```bash
git clone --branch stable https://github.com/aquantumofdonuts/sonoplex.git
cd sonoplex
docker compose up -d
```

### Configuration (Optional)

SonoPlex works out of the box with sensible defaults. To customize, copy `.env.example` to `.env`:

```bash
cp .env.example .env
# Edit .env with your settings
```

Available settings:
- `HTTP_PORT` - Web UI port (default: 32488)
- `HOST_IP` - Your server's IP (auto-detected if not set)
- `CLIENT_PROFILE` - Plex transcoding profile (Sonos, DLNA, Chromecast, etc.)

### Then:

1. Open `http://your-server:32488`
2. Click "Link to Plex" on your speaker
3. Open Plexamp → Cast → Select your speaker
4. Enjoy 🎵

---

## Features

### 🔊 DLNA Device Discovery
Automatically finds all DLNA/UPnP speakers, receivers, and smart TVs on your network.

### 🎵 Full Plexamp Integration
- PIN-based Plex.tv authentication
- Automatic Plex server discovery
- Play queue support with track info
- Real-time playback status sync

### 🏠 Multi-Room Audio
Create virtual device groups for synchronized playback across multiple speakers.

### 🎨 Modern Web Interface
- Device management dashboard
- Real-time status updates
- Mobile-friendly design

### 🐳 Docker-Ready
One command deployment with persistent storage and automatic restarts.

---

## Supported Devices

SonoPlex works with any DLNA/UPnP compatible device:

- **Sonos** speakers (via DLNA mode)
- **Yamaha** MusicCast receivers
- **Denon/Marantz** HEOS devices
- **Samsung/LG/Sony** smart TVs
- **Chromecast Audio** (via DLNA bridge)
- Any UPnP MediaRenderer

---

## Requirements

- Docker (recommended) or Python 3.12+
- Plex Media Server on your network
- Plex Pass (for Plexamp)
- DLNA-compatible speakers/devices

---



## How It Works

1. **Discovery**: SonoPlex uses SSDP to find DLNA devices and Plex GDM to announce them as Plex players
2. **Linking**: When you link a device to Plex.tv, Plexamp can discover it
3. **Streaming**: Plexamp sends playback commands to SonoPlex, which translates them to DLNA control commands
4. **Transcoding**: Audio is automatically transcoded to formats your device supports

---


## FAQ

### Why can't Plexamp cast to DLNA natively?
Plex chose not to implement DLNA casting in Plexamp. This has been a community request since 2020.

### Does this replace the SonoPlex server?
No. Plex's DLNA server lets DLNA devices browse your library. SonoPlex does the opposite—it lets Plex apps control DLNA devices.

### Do I need Plex Pass?
Plexamp requires Plex Pass. SonoPlex itself is free and open source.

### What about gapless playback?
Gapless playback depends on your DLNA device's capabilities. Most modern receivers support it.

---

## Contributing

Issues and PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Credits

Originally forked from [plexdlnaplayer](https://github.com/songchenwen/plexdlnaplayer) by songchenwen.

---

## License

GPL v3 - See [LICENSE](LICENSE) for details.

