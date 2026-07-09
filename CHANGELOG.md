# Changelog

All notable changes to this package are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added

- `verify_webhook_signature()` helper for checking the `SonoVault-Signature` header on webhook deliveries (HMAC-SHA256, constant-time compare, replay-window check).

### Fixed

- `streams.live()` now consumes the endpoint as Server-Sent Events and returns a generator of parsed events. It previously tried to parse the infinite stream as JSON and hung.

## [1.0.0] - 2026-07-09

### Added

- Initial release.
- `SonoVault` client covering the full public API: tracks (search, get, by_isrc, iswc, by_iswc, links, resolve, identify, identify_audio, browse), artists, labels, releases, genres, suggestions, streams, and webhooks.
- Cursor pagination on all list endpoints.
- Typed errors via `SonoVaultError` with `is_auth_error`, `is_forbidden`, and `is_rate_limited` properties.
- Automatic retry on 5xx responses and on 429 responses that carry a `Retry-After` header.
- Python 3.9+, `requests` as the only dependency.
- Live integration test suite, skipped unless `SONOVAULT_API_KEY` is set.
