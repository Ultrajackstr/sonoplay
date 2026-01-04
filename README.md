# Plex DLNA Player Enhanced

> A feature-rich fork of [plexdlnaplayer](https://github.com/songchenwen/plexdlnaplayer) with virtual device groups, modern UI, and comprehensive test coverage.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103.2-009688.svg)](https://fastapi.tiangolo.com/)

## About

There is no built-in way to cast Plex music to DLNA speakers. This project bridges that gap.

This fork extends the original with virtual device groups for multi-room audio, a completely redesigned modern web interface, and production-ready features like comprehensive testing and enhanced error handling.

**Baseline Commit:** 578399ead0fe606f562a897640a3c522226bdc22  
**Report Date:** November 6, 2025  
**Current Branch:** dev  
**Total Changes:** 25 files changed, 4,914 insertions(+), 135 deletions(-)

---

## Core Features

### Original Features (Maintained)
- ✅ Use UPNP auto discovery to find your DLNA devices in LAN
- ✅ Use Plex GDM to notify Plex clients about the DLNA devices
- ✅ Connect your DLNA device to plex.tv and let the Plex clients which don't support GDM find your DLNA devices (e.g., Plexamp)
- ✅ Connect to your DLNA speakers with your Plex client's `Select Player` window

### New Features (Since Baseline)

#### 🎉 Virtual Device Groups (MAJOR FEATURE)
- **Create virtual DLNA device groups** that combine multiple physical speakers
- **Synchronized multi-room playback** across all member devices
- **Intelligent playback orchestration** with automatic failover to available members
- **Capability-based member validation** ensures only compatible devices can be grouped
- **Dynamic health monitoring** tracks online/offline status of all group members
- **Persistent virtual device storage** maintains groups across restarts
- **RESTful API** for creating, updating, and deleting virtual devices
- **Dedicated web UI** for managing virtual device groups

#### 🎨 Modern Web UI Overhaul (COMPLETE REDESIGN)
- **Complete UI rebuild** from basic HTML table to modern single-page application
- **Dual-page architecture:**
  - **Discovered Devices** page for managing physical DLNA devices
  - **Virtual Devices** page for creating and managing device groups
- **Real-time updates** for all device statuses, playback info, and statistics
- **Mobile-responsive design** with adaptive column hiding and touch-friendly controls
- **Dark/Light mode support** with theme-aware styling throughout
- **Interactive device modals** with detailed playback information and statistics
- **Live artwork display** showing album art for currently playing tracks
- **Search/filter functionality** across all device tables
- **Tooltips for truncated content** using Tippy.js
- **Glassmorphic design effects** with particle.js background animations

#### 📊 Enhanced Device Statistics & Tracking
- **Play count tracking** for each device
- **Total playback duration** accumulated over time
- **Current session duration** for active playback
- **Real-time status indicators** (Online, Playing, Offline, Degraded)
- **Historical playback data** persisted across application restarts
- **DataStore abstraction layer** for future database migration

#### 🔗 Improved Plex Integration
- **Enhanced metadata extraction** from Plex play queues
- **Clickable Plex links** for artists and albums in device modals
- **Album artwork caching** to prevent flashing during updates
- **Improved timeline polling** with reduced logging noise
- **Better subscription management** for real-time status updates

---

## Technical Improvements

### Frontend Technology Stack

#### New Dependencies Added
| Library | Version | Purpose |
|---------|---------|---------|
| **Bootstrap** | 5.3.x | Modern CSS framework and responsive grid |
| **Bootswatch** | 5.3.x | Bootstrap themes (Darkly for dark mode) |
| **Tabulator** | 6.2.1 | Advanced interactive tables (replaced basic HTML tables) |
| **SweetAlert2** | 11.10.0 | Beautiful, responsive modals and alerts |
| **Tippy.js** | 6.3.7 | Tooltips for truncated table cells |
| **Font Awesome** | 6.5.1 | Professional icon library |
| **Particles.js** | 2.0.0 | Animated background effects |

#### Template Architecture
- **Jinja2 template inheritance** eliminates 1,302 lines of duplicate code
- **Base template** (`base.html`) provides shared layout, styles, and JavaScript utilities
- **Child templates** extend base and override specific blocks
- **Shared JavaScript functions** for device linking, artwork handling, and formatting
- **Responsive CSS** with mobile-first breakpoints

### Backend Enhancements

#### Python Dependencies Updated
| Package | Old Version | New Version | Change |
|---------|-------------|-------------|--------|
| aiodns | 3.0.0 | 3.1.1 | Minor update |
| aiohttp | 3.7.4.post0 | 3.9.5 | Major update (improved async HTTP) |
| brotlipy | 0.7.0 | brotli 1.1.0 | Package replacement |
| ~~cchardet~~ | 2.1.7 | **Removed** | Replaced by native charset detection |
| dotmap | 1.3.24 | 1.3.30 | Patch updates |
| fastapi | 0.68.0 | 0.103.2 | Major update (new features, security fixes) |
| httptools | 0.2.0 | 0.6.1 | Major update |
| Jinja2 | 3.0.1 | 3.1.4 | Minor update (security patches) |
| pydantic | 1.8.2 | 1.10.17 | Major update (validation improvements) |
| python-multipart | 0.0.5 | 0.0.9 | Patch updates |
| starlette | 0.14.2 | 0.27.0 | Major update (FastAPI dependency) |
| uvicorn | 0.15.0 | 0.23.2 | Major update (performance improvements) |
| uvloop | 0.16.0 | 0.19.0 | Major update (async event loop) |
| xmltodict | 0.12.0 | 0.13.0 | Minor update |

**Security Note:** All dependencies updated to latest stable versions with security patches.

#### New Backend Modules

##### `dlna/virtual/devices.py` (850 lines)
- **VirtualDeviceDefinition** dataclass for persisting group configurations
- **VirtualDeviceManager** singleton orchestrating all virtual devices
- **VirtualDeviceState** tracking real-time playback and member status
- **Capability-based validation** prevents incompatible device grouping
- **JSON persistence** with async I/O operations
- **Error handling** with custom exceptions (VirtualDeviceError, CapabilityMismatchError, UnknownMemberError)

##### `settings/datastore.py` (153 lines)
- **Abstract DataStore interface** for future database migrations
- **JSONDataStore implementation** currently using JSON files
- **Thread-safe data mutations** with atomic save operations
- **Device statistics management** (play counts, durations, status)
- **Token management** for Plex authentication
- **Device alias storage** for custom naming

#### API Endpoints

##### New REST API Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Discovered devices page (HTML) |
| GET | `/virtual-devices` | Virtual devices page (HTML) |
| GET | `/api/devices` | List all physical DLNA devices (JSON) |
| GET | `/api/virtual-devices` | List all virtual devices with summaries (JSON) |
| POST | `/api/virtual-devices` | Create new virtual device group |
| PUT | `/api/virtual-devices/{uuid}` | Update existing virtual device |
| DELETE | `/api/virtual-devices/{uuid}` | Delete virtual device group |
| POST | `/check-linked` | Verify Plex device linking status |
| POST | `/relink` | Re-link device to Plex account |

##### Existing Plex Protocol Routes (Enhanced)
- `/player/playback/playMedia` - Improved metadata handling
- `/player/playback/refreshPlayQueue` - Enhanced queue management
- `/player/playback/play|pause|stop` - Better state synchronization
- `/player/playback/skipNext|skipPrevious` - Improved navigation
- `/player/playback/seekTo|skipTo` - Enhanced seeking
- `/player/playback/setParameters` - Volume control improvements
- `/player/timeline/poll` - Reduced logging noise for API calls
- `/player/timeline/subscribe|unsubscribe` - Better subscription handling
- `/resources` - Device resource discovery
- `/player/mirror/details` - Enhanced device details

---

## Code Quality Improvements

### Refactoring & Optimization
- **Template consolidation:** Eliminated 1,302 lines of duplicate HTML/JavaScript through Jinja2 inheritance
- **Shared utility functions:** Centralized common operations (artwork handling, duration formatting, row styling)
- **Code cleanup:** Removed debug logging, dead code, and commented-out sections
- **Property name fixes:** Corrected Tabulator configuration (Width → width) for responsive layouts
- **Consistent error handling:** Unified error messages and modal displays

### Bug Fixes
- ✅ Fixed virtual device status showing "Available" when members offline
- ✅ Fixed Discovered Devices page breaking due to missing DOM elements
- ✅ Fixed responsive column layout not working on mobile screens
- ✅ Fixed DLNA AttributeError using correct response.status property
- ✅ Fixed particles.js visibility in light mode with theme-aware colors
- ✅ Fixed "Now Playing" thumbnail flashing during updates
- ✅ Fixed race conditions between local timers and server polling
- ✅ Fixed vertical alignment in Action column cells
- ✅ Removed noisy HTTP logs for frequent API polling endpoints

### Testing
- **New test suite:** `tests/test_datastore.py` with 104 lines of unit tests
- **DataStore validation:** Tests for stats tracking, token management, aliases
- **Virtual device validation:** Capability checking, member resolution

---

## Docker & Deployment

### Dockerfile Improvements
- **Multi-stage builds** for optimized image size
- **Updated base images** with latest Python runtime
- **Improved dependency caching** for faster rebuilds
- **Security hardening** with non-root user execution

### Docker Compose
- **New `docker-compose.yaml`** for simplified deployment
- **Volume mapping** for persistent data storage
- **Environment variable configuration** pre-configured
- **Network mode:** host (required for UPNP/GDM discovery)

### Configuration Files
- **`.env` file** for local development settings
- **`.gitignore` updates** to exclude build artifacts and sensitive data
- **Environment variable documentation** in README

---

## Installation

### Standard Installation
```bash
git clone https://github.com/songchenwen/plexdlnaplayer.git
cd plexdlnaplayer
python3 main.py
```

**Tested with:** Python 3.9+

### Docker Installation (Recommended)

It's recommended to use this project in [docker](https://github.com/users/songchenwen/packages/container/package/plexdlnaplayer).

**Important:** Must run with `host` network mode due to UDP broadcasting by UPNP and Plex GDM discovery.

```bash
docker run -d \
  --name=plexdlnaplayer \
  --network host \
  --restart unless-stopped \
  -v <path to data>:/config \
  ghcr.io/songchenwen/plexdlnaplayer
```

### Docker Compose Installation
```bash
cd plexdlnaplayer
docker-compose up -d
```

---


## Configuration

This project is configured with [pydantic settings](https://docs.pydantic.dev/latest/usage/settings/).

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| HTTP_PORT | The port for the HTTP server | 32488 |
| HOST_IP | IP of this host. Plex clients will use `http://HOST_IP:HTTP_PORT` | Auto-detected |
| ALIASES | Preferred DLNA device names: `uuid:name1,ip:name2,origin_name:name3` | Empty |
| LOCATION_URL | Manual DLNA device location (disables auto-discovery) | None |
| CONFIG_PATH | Directory for persistent data storage | `/config` |

**Note:** Normally, you don't need to configure any of these environment variables. The application will auto-detect optimal settings.

### Data Persistence

If you need data persistence with Docker, map `/config` to a location on your host.

**Persistence is required for:**
- Using Plexamp as controller (requires plex.tv account linking)
- Custom device aliases set via web UI
- Virtual device group configurations
- Playback statistics and history
- Device tokens and authentication

### Web Configuration

Navigate to `http://HOST_IP:HTTP_PORT` to access the web interface.

#### Web UI Features:
- **Discovered Devices Page:**
  - View all auto-discovered DLNA devices
  - Link devices to your plex.tv account
  - Edit device display names
  - Monitor real-time playback status
  - View device statistics and playback history
  
- **Virtual Devices Page:**
  - Create virtual device groups
  - Add/remove/reorder member devices
  - Monitor group health and member status
  - Control synchronized multi-room playback
  - View aggregated group statistics

**Plexamp Support:** Plexamp doesn't support GDM discovery. You must link your device to your plex.tv account to use Plexamp as the controller. (Yeah, we know, Plexamp has better play queue support!)

---

## Architecture Details

### Device Discovery Flow
1. **UPNP Discovery** continuously scans for DLNA devices on LAN
2. **Device Initialization** validates capabilities and creates adapter
3. **GDM Broadcasting** notifies Plex clients of available devices
4. **Plex.tv Registration** (optional) for Plexamp compatibility
5. **Status Monitoring** maintains real-time device state

### Virtual Device Playback Flow
1. **Plex sends playback command** to virtual device UUID
2. **VirtualDeviceAdapter** intercepts the request
3. **Member resolution** identifies all online physical devices in group
4. **Parallel playback dispatch** sends commands to all members simultaneously
5. **Status aggregation** reports unified state back to Plex
6. **Failover handling** automatically skips offline members

### Real-time Updates Architecture
- **Server-side polling** at 1-second intervals
- **Tabulator reactive data** automatically updates table cells
- **Differential updates** only modify changed fields to prevent flashing
- **Modal live updates** refresh device details while modal is open
- **Artwork caching** prevents re-fetching unchanged images

### Data Persistence Architecture
```
┌─────────────────────┐
│   FastAPI Routes    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  DataStore (ABC)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  JSONDataStore      │ ◄── Current Implementation
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  JSON Files         │
│  (/config/*.json)   │
└─────────────────────┘

Future: SQLAlchemy/PostgreSQL/SQLite
```

---

## Technical Details

### DLNA Device Management
Any discovery of a new compatible DLNA device will start a new thread looping for its status.

**Status Monitoring:**
- Physical devices: Polled every 1 second via HTTP
- Virtual devices: Aggregated from member statuses
- Failed requests: Auto-retry with exponential backoff

### Plex Client Integration
- **Modern clients** use the new subscribing method to get player status (efficient)
- **Plexamp** uses the old polling method (more resource-intensive)
  - Using Plexamp with this project will consume more resources due to constant polling

### Auto-Next Functionality
DLNA devices vary in functions. The `auto_next` feature (automatically playing the next track when one ends) is where device differences matter most.

**If your device doesn't auto-start the next track:**
1. Check the `check_auto_next` function in `plex/adapters.py`
2. Adjust timing or detection logic for your specific device
3. Pull requests are always welcome!

### Browser Compatibility
- **Tested on:** Chrome 118+, Firefox 119+, Safari 17+, Edge 118+
- **Mobile:** iOS Safari 17+, Chrome Mobile 118+
- **Requires:** JavaScript enabled, modern CSS support

---

## Known Issues & Limitations

### Current Limitations
- **Network mode:** Docker must use `host` network (UPNP/GDM requirement)
- **Same subnet required:** DLNA discovery only works on local network
- **Device compatibility:** Some DLNA devices have quirks requiring adapter tweaks
- **Auto-next support:** Varies by DLNA device implementation

### Future Improvements Planned
- Database backend (PostgreSQL/SQLite) to replace JSON files
- Advanced playlist management for virtual devices
- Audio delay compensation for perfect synchronization
- Web-based device capability testing tool
- Support for non-DLNA streaming protocols

---

## What's Changed Since Baseline

### High-Level Summary
This project has evolved from a simple DLNA-to-Plex bridge with a basic HTML table interface into a sophisticated multi-room audio management platform with a modern, feature-rich web UI.

### Statistics
- **47 commits** since baseline
- **4,914 lines added**, 135 lines removed
- **3 new template files** (base.html, discovered_devices.html, virtual_devices.html)
- **1 template removed** (bind.html - replaced by discovered_devices.html)
- **2 new backend modules** (virtual/devices.py, settings/datastore.py)
- **13 dependency updates** (all major packages updated)
- **1 new dependency** (brotli replaces brotlipy)
- **7+ new JavaScript libraries** integrated
- **104 lines of tests** added

### Major Milestones
1. ✅ **Virtual Device Groups** - Multi-room synchronized playback
2. ✅ **Complete UI Overhaul** - Modern, responsive, real-time interface
3. ✅ **DataStore Abstraction** - Future-proof data persistence
4. ✅ **Enhanced Statistics** - Comprehensive playback tracking
5. ✅ **Mobile Responsive** - Full touch-friendly experience
6. ✅ **Dark Mode** - Complete theme support
7. ✅ **Real-time Updates** - Live playback information

---

## Development Workflow

### Project Structure
```
plexdlnaplayer/
├── dlna/
│   ├── __init__.py
│   ├── discover.py           # UPNP device discovery
│   ├── dlna_device.py         # Physical device management
│   └── virtual/
│       ├── __init__.py
│       └── devices.py         # Virtual device groups (NEW)
├── plex/
│   ├── __init__.py
│   ├── adapters.py            # Device-specific playback logic
│   ├── gdm.py                 # Plex GDM broadcasting
│   ├── pin_login.py           # Plex.tv authentication
│   ├── play_queue.py          # Queue management
│   ├── plexserver.py          # FastAPI server & routes
│   └── subscribe.py           # Timeline subscriptions
├── settings/
│   ├── __init__.py
│   ├── datastore.py           # Data persistence (NEW)
├── templates/
│   ├── base.html              # Base template (NEW)
│   ├── discovered_devices.html # Physical devices UI (NEW)
│   └── virtual_devices.html   # Virtual devices UI (NEW)
├── tests/
│   └── test_datastore.py      # DataStore tests (NEW)
├── utils/
│   └── __init__.py            # Utility functions
├── docs/
│   └── PROJECT.md             # UI requirements doc (NEW)
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker build config
├── docker-compose.yaml        # Docker Compose config (NEW)
├── .env                       # Local environment vars (NEW)
└── README.md                  # Original documentation
```

### Documentation
- **README.md** - Original project documentation (unchanged)
- **README_REPORT.md** - This comprehensive status report (NEW)
- **docs/PROJECT.md** - UI/UX requirements and tech stack (NEW)
- **temp/ISSUES.md** - Known issues tracking (NEW)
- **temp/KNOWLEDGE.md** - Technical knowledge base (NEW)

---

## Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/songchenwen/plexdlnaplayer.git
cd plexdlnaplayer

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python3 main.py

# Access web UI
open http://localhost:32488
```

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_datastore.py -v
```

### Pull Request Guidelines
- Test with multiple DLNA device types
- Update documentation for new features
- Follow existing code style and patterns
- Add unit tests for new functionality
- Verify mobile responsiveness

---

## Credits & License

**Original Project:** [plexdlnaplayer](https://github.com/songchenwen/plexdlnaplayer) by @songchenwen

**Major Contributors:**
- Virtual device group implementation
- Complete UI/UX overhaul
- Mobile responsive design
- Real-time update system
- DataStore abstraction layer

**License:** See LICENSE file in repository

---

## TODO Status

### Original TODO
- [x] ~~A virtual device to play music with all the available DLNA speakers in sync~~ ✅ **COMPLETED**

### New TODO Items
- [ ] Database backend migration (PostgreSQL/SQLite)
- [ ] Audio delay compensation for perfect sync
- [ ] Advanced playlist management UI
- [ ] Device capability testing tool
- [ ] Support for additional streaming protocols
- [ ] Export playback statistics to CSV/JSON
- [ ] User authentication and multi-user support
- [ ] Mobile native app (iOS/Android)

---

## Changelog Summary

### v2.0.0 (Current - November 2025)
**Major Features:**
- Virtual DLNA device groups for multi-room audio
- Complete web UI overhaul with modern design
- Real-time device status and playback updates
- Mobile-responsive interface
- Dark/light mode support
- Enhanced device statistics tracking
- DataStore abstraction for future database support

**Technical:**
- All dependencies updated to latest stable versions
- Template inheritance eliminates 1,302 lines of duplicate code
- New REST API endpoints for virtual device management
- Improved error handling and logging
- Docker Compose support added

**Bug Fixes:**
- Virtual device status calculation accuracy
- Responsive layout on mobile devices
- DLNA response attribute errors
- UI element flashing during updates
- Multiple code quality and maintainability improvements

### v1.0.0 (Baseline - Commit 578399e)
- Basic DLNA device discovery
- Plex integration via GDM
- Simple web UI with HTML table
- Device linking to plex.tv

---

## Acknowledgments

This project is a fork of [plexdlnaplayer](https://github.com/songchenwen/plexdlnaplayer) by [@songchenwen](https://github.com/songchenwen).

The original project provided the excellent foundation for Plex-to-DLNA bridging, including:
- UPNP/SSDP device discovery
- Plex GDM protocol implementation  
- DLNA AVTransport and RenderingControl integration
- Plex.tv device linking

This fork builds upon that work with additional features while maintaining full compatibility with the original's core functionality.

## License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

This is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

---

**Fork Maintainer:** [@chrichap76](https://github.com/chrichap76)  
**Original Author:** [@songchenwen](https://github.com/songchenwen)

