# Changelog

All notable changes to this package are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added

- Each entry in `releases.get()`'s `editions` now carries `label` and `catalog_no`: the label that issued that pressing and its catalog number. Pressings of one album often differ (the UK original and a US reissue each carry their own), which the single release-level `label` cannot show.
- `from_` and `until` on `artists.releases()` and `labels.releases()`: inclusive `YYYY-MM-DD` release-date bounds (`from_` maps to the `from` param), so `labels.releases(label_id, from_="2026-09-11", until="2026-09-11")` lists what a label released that day. Undated releases are left out when either is set.

## [2.2.0] - 2026-09-14

### Added

- `releases.get(release_id, edition=...)` renders one edition's track numbering instead of the default consensus. Tracks that edition does not carry keep a `None` position and come last, and `edition` on the response echoes what you asked for.
- `GET /v1/releases/:id` now returns `editions`: the real editions behind a release. A SonoVault release groups every edition of an album onto one record, so the single, the album, the deluxe edition and the box set share one ID; each entry carries its provider, format, release date, barcode, country and track count. At most 20, ordered so each is a genuinely different edition rather than twenty pressings of the same one.

## [2.1.0] - 2026-09-04

### Added

- `releases.get()` returns its `tracks` in playing order, each carrying `disc_number` and `track_number`. A track whose position is unknown sorts last with both fields `None`. A position belongs to the pairing of track and release rather than to the track alone, so the same recording can be track 6 on an album and track 2 on a compilation.
- `artists.get()`, `artists.search()` and `labels.artists()` return `musicbrainz_id`, the MusicBrainz artist MBID, alongside the existing `wikidata_id`. `None` when we hold no mapping.
- `releases.get()` returns `musicbrainz_release_ids` and `musicbrainz_release_group_ids`. Lists, because a SonoVault release groups every edition of an album and each edition carries its own MBID, so you pick the edition you need. Empty when unmapped.

## [2.0.0] - 2026-08-22

### Removed

- **BREAKING:** `sv.tracks.identify()`. The API's client-side-Chromaprint request body (`POST /v1/tracks/identify` with a JSON `fingerprint` array) was removed on 2026-08-22 and now returns 415, so the method could only fail. Use `sv.tracks.identify_audio()` instead: send the raw audio bytes and the server fingerprints them. It is also the more accurate route, because cross-window voting, the tempo cross-check, and a second independent matcher all need the audio itself.

## [1.2.0] - 2026-07-09

### Added

- `examples/` folder: find an ISRC, cross-platform links, play-log enrichment, live SSE events, and a webhook receiver with signature verification.
- `paginate()` helper: iterate every item across all pages of any cursor-paginated endpoint.
- Context-manager support: `with SonoVault(api_key=...) as sv:` closes the session on exit (injected sessions are left open).

## [1.1.0] - 2026-07-09

### Added

- `verify_webhook_signature()` helper for checking the `SonoVault-Signature` header on webhook deliveries (HMAC-SHA256, constant-time compare, replay-window check).
- `timeout` client option in seconds (default 30, was hardcoded).
- `webhooks.get(webhook_id)` for fetching a single webhook endpoint.
- `User-Agent: sonovault-python/<version>` header on every request.
- `py.typed` marker so mypy and pyright pick up the package's type hints.

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
