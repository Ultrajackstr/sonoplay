# Changelog

All notable changes to this project will be documented in this file.

The latest version is always available by pulling the [stable] tag.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.2] - 2026-01-17

This release improves DLNA device compatibility with a device quirks system for manufacturer-specific workarounds.

### Added

#### Device Quirks System
- New `dlna/quirks.py` module with per-device workaround registry
- Case-insensitive regex matching against device model names
- User overrides via `device_quirks` in data.json
- Built-in quirks for Sony, Denon/HEOS, Marantz, and Bose SoundTouch

#### Sony Device Fixes
- Premature STOPPED filtering: ignore spurious STOPPED events before PLAYING is seen
- Wait-for-can-play: poll `GetCurrentTransportActions` before sending play commands

#### Subscription Tracking
- Track subscription expiry time for proactive renewal
- `needs_resubscription()` method for checking renewal status
- Extended timeout support (540s) for Denon/HEOS/Marantz devices

### Changed

- Increased `http_timeout_dlna` from 5s to 10s for slower devices
- Added 0.5s delay between retry attempts to prevent retry storms
- Use `settings.http_timeout_dlna` instead of hardcoded timeout values

### Tests

- 39 new tests across 4 test files (201 total tests pass)

---

## [v1.1.1] - 2026-01-16

# Release Notes: DLNA Device Compatibility Improvements

**Release Date:** January 2026

## Overview

This release significantly improves DLNA device compatibility by addressing HTTP 5xx server error handling and XML response sanitization. These changes enable playback on previously broken devices (especially Oppo players) and add defensive handling for malformed XML from various manufacturers.

---

## Features

### 1. HTTP 5xx Retry Logic

**Problem:** Oppo devices return HTTP 500 errors during normal operation, causing "Couldn't start playback" failures.

**Solution:** Treat HTTP 5xx errors as transient (like connection errors) and retry up to 3 times.

| Behavior | Before | After |
|----------|--------|-------|
| HTTP 500 | Immediate failure | Retry up to 3× |
| HTTP 4xx | Immediate failure | Immediate failure (unchanged) |
| Connection error | Retry 3× | Retry 3× (unchanged) |

---

### 2. XML Response Sanitization

**Problem:** Many DLNA devices return malformed or non-compliant XML responses that cause parsing failures.

**Solution:** Pre-process all XML responses through `sanitize_soap_response()` to fix known device quirks before parsing.

---

## Sanitization Fixes

| Fix | Affected Devices | Description | Source |
|-----|------------------|-------------|--------|
| **Malformed namespace prefix** | Oppo | Replace `<&` with `<s:` in SOAP envelope | User logs |
| **Illegal XML characters** | Sonos, various | Strip Unicode chars 0x00-0x08, 0x0B-0x0C, 0x0E-0x1F | [SoCo](https://github.com/SoCo/SoCo), XML 1.0 §2.2 |
| **Missing namespace declaration** | Various | Add `xmlns:dlna` when `dlna:` prefix used but undeclared | [jupnp](https://github.com/jupnp/jupnp) |
| **Non-standard namespace** | Belkin WeMo | Replace `urn:Belkin:device-1-0` with standard UPnP namespace | [jupnp](https://github.com/jupnp/jupnp) |
| **Trailing garbage** | Various | Truncate after `</s:Envelope>` or `</root>` | [jupnp](https://github.com/jupnp/jupnp) |
| **Leading HTTP garbage** | Windows UPnP | Strip HTTP headers before `<?xml` declaration | [jupnp](https://github.com/jupnp/jupnp) |

---

## Affected Platforms

| Platform/Device | Issues Fixed |
|-----------------|--------------|
| **Oppo** (UDP-203, UDP-205, etc.) | HTTP 500 errors, `<&Envelope` malformed namespace |
| **Sonos** | Illegal XML control characters in responses |
| **Belkin WeMo** | Non-standard `urn:Belkin:device-1-0` namespace |
| **Windows Media Player** | HTTP headers prepended to XML body |
| **Various DLNA devices** | Missing `xmlns:dlna` declaration, trailing garbage |

---

## Research Sources

The XML sanitization patterns are based on documented issues from established DLNA/UPnP implementations:

| Source | Repository | Reference |
|--------|------------|-----------|
| **jupnp** | [github.com/jupnp/jupnp](https://github.com/jupnp/jupnp) | `RecoveringUDA10DeviceDescriptorBinderImpl.java` |
| **SoCo** | [github.com/SoCo/SoCo](https://github.com/SoCo/SoCo) | XML illegal character handling for Sonos |
| **XML 1.0 Specification** | [w3.org](https://www.w3.org/TR/xml/#charsets) | Section 2.2 - Character ranges |

---

## Files Changed

| File | Changes |
|------|---------|
| `dlna/dlna_device.py` | Added `ServerErrorException`, `sanitize_soap_response()`, 5xx retry logic |
| `tests/unit/test_dlna_connection_retry.py` | New test class `TestSoapResponseSanitization` |

---



## [v1.1.0] - 2025-11-06

This release represents a major evolution of the original plexdlnaplayer project, adding virtual device groups for multi-room audio, a completely redesigned web interface, and comprehensive test coverage.

### Added

#### Virtual Device Groups (Major Feature)
- Create virtual DLNA device groups that combine multiple physical speakers
- Synchronized multi-room playback across all member devices
- Capability-based member validation ensures only compatible devices can be grouped
- Status tracking shows online/offline status of all group members
- Persistent virtual device storage maintains groups across restarts
- RESTful API for creating, updating, and deleting virtual devices
- Dedicated web UI page for managing virtual device groups

#### Modern Web UI (Complete Redesign)
- Complete UI rebuild from basic HTML table to modern responsive application
- Dual-page architecture: Discovered Devices and Virtual Devices pages
- Real-time updates for all device statuses, playback info, and statistics
- Mobile-responsive design with adaptive layouts and touch-friendly controls
- Interactive device modals with detailed playback information
- Search and filter functionality across all device views

#### Device Statistics & Tracking
- Play count tracking for each device
- Total playback duration accumulated over time
- Current session duration for active playback
- Real-time status indicators (Online, Playing, Offline, Degraded)
- Historical playback data persisted across application restarts
- DataStore abstraction layer for future database migration

#### Plex Integration Enhancements
- Enhanced metadata extraction from Plex play queues
- Improved timeline polling with reduced logging noise
- Better subscription management for real-time status updates

#### Testing & Quality
- Comprehensive test suite with 18+ test files
- pytest with coverage reporting
- Tests for adapters, datastore, DLNA state lifecycle, and more
- HTTP timeout handling tests
- Security tests for Plex token handling
- UUID validation tests

#### Infrastructure
- Docker Compose support for easy deployment
- Health endpoint for container monitoring
- Structured logging improvements
- Python 3.12 support with updated dependencies

### Changed

#### Dependencies Updated
| Package | Old Version | New Version |
|---------|-------------|-------------|
| aiohttp | 3.7.4 | 3.9.5 |
| fastapi | 0.68.0 | 0.103.2 |
| pydantic | 1.8.2 | 1.10.17 |
| uvicorn | 0.15.0 | 0.23.2 |
| uvloop | 0.16.0 | 0.19.0 |
| Jinja2 | 3.0.1 | 3.1.4 |
| starlette | 0.14.2 | 0.27.0 |

#### Architecture Improvements
- Jinja2 template inheritance eliminates duplicate code
- Base template provides shared layout, styles, and JavaScript utilities
- Improved error handling throughout the codebase
- Better async/await patterns in DLNA state management

### Fixed
- Virtual device status calculation accuracy
- Responsive layout issues on mobile devices
- DLNA response attribute errors (missing attributes handled gracefully)
- UI element flashing during real-time updates
- Race conditions in device list access
- HTTP timeout handling for unresponsive DLNA devices

### Removed
- `cchardet` dependency (replaced by native charset detection)
- `brotlipy` dependency (replaced by `brotli`)
- Basic HTML table UI (replaced by modern responsive design)

## [v1.0.0] - Original Baseline

Original implementation by [@songchenwen](https://github.com/songchenwen).

Based on commit `578399ead0fe606f562a897640a3c522226bdc22`.

### Features
- UPNP auto discovery to find DLNA devices in LAN
- Plex GDM to notify Plex clients about DLNA devices
- Connect DLNA devices to plex.tv for Plexamp support
- Basic web UI with HTML table for device management
- Device linking via plex.tv PIN authentication

---


[1.0.0]: https://github.com/songchenwen/plexdlnaplayer/tree/578399ead0fe606f562a897640a3c522226bdc22
