# Sonoplex v1.0.0 Release Notes

**Release Date:** January 4, 2026

## 🎉 Initial Release

Sonoplex is a bridge that enables Plex media playback on DLNA/UPnP devices like Sonos speakers, smart TVs, and network audio receivers.

### Features

- **Plex Integration**
  - PIN-based authentication with Plex.tv
  - Automatic Plex server discovery via GDM (G'Day Mate)
  - Play queue management for seamless playback
  - Timeline subscription for playback state sync

- **DLNA/UPnP Support**
  - SSDP device discovery
  - Real-time device control (play, pause, stop, seek, volume)
  - Virtual device support for testing and development

- **Web Interface**
  - Device management dashboard
  - 8 customizable themes (Neon Cyber, Soft Aurora, Midnight Luxury, and more)
  - Real-time device status updates

- **Docker Deployment**
  - Ready-to-use Docker Compose configuration
  - Host network mode for SSDP/multicast support
  - Persistent storage for settings and device data

### Technical Highlights

- Built with FastAPI and async Python
- Comprehensive test suite with pytest
- Atomic settings persistence
- Thread-safe device list management

### Requirements

- Python 3.12+
- Docker & Docker Compose (recommended)
- Network access to Plex server and DLNA devices

### Getting Started

```bash
docker compose up -d
```

Then visit `http://localhost:8456` to authenticate with Plex and start streaming.

---

For issues and contributions, visit the [GitHub repository](https://github.com/aquantumofdonuts/sonoplex).
