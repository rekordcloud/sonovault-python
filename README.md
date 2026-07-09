# sonovault

[![CI](https://github.com/rekordcloud/sonovault-python/actions/workflows/ci.yml/badge.svg)](https://github.com/rekordcloud/sonovault-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sonovault)](https://pypi.org/project/sonovault/)

Python client for the **[SonoVault](https://sonovault.now)** music metadata API. 90M+ tracks with ISRC, ISWC, genre, record label, canonical release dates, and cross-platform IDs for Spotify, Apple Music, Tidal, Beatport, Discogs, and MusicBrainz. One call resolves them all.

- **One key, no OAuth.** A single `x-api-key` header, no approval queue.
- **Free tier.** 1,000 requests/month, no credit card: [get an API key](https://sonovault.now).
- **Docs.** Full API reference at [sonovault.now/docs](https://sonovault.now/docs).

## Install

```bash
pip install sonovault
```

Python 3.9+.

## Quickstart

```python
from sonovault import SonoVault

sv = SonoVault(api_key="YOUR_API_KEY")

# Find a track's ISRC from artist + title
page = sv.tracks.search(artist="Daft Punk", title="One More Time")
track = page["results"][0]
print(track["isrc"])   # "GBDUW0000053"
print(track["genre"], track["releases"][0]["label"]["name"])

# Resolve that ISRC to its ID on every platform
links = sv.tracks.links(isrc=track["isrc"])
for link in links["links"]:
    print(link["source"], link["url"])  # spotify https://open.spotify.com/track/...

# Recording to composition (ISWC), for royalty and publishing workflows
work = sv.tracks.iswc(isrc=track["isrc"])
```

## Bulk resolve

Resolve up to 100 lines in one request: track names, ISRCs, or platform IDs. Useful for enriching play logs and library exports.

```python
batch = sv.tracks.resolve(
    input_type="track_name",
    items=[
        {"artist": "Daft Punk", "title": "Harder, Better, Faster, Stronger"},
        {"artist": "Daft Punk", "title": "Around the World"},
    ],
)
for row in batch["results"]:
    print(row["status"], row["track"] and row["track"]["isrc"])
```

## Pagination

List endpoints return `{"results": [...], "next_cursor": ...}`. Pass the cursor back for the next page. `next_cursor` is `None` on the last page.

```python
cursor = None
while True:
    page = sv.artists.releases(42, cursor=cursor)
    # ...use page["results"]
    cursor = page.get("next_cursor")
    if not cursor:
        break
```

## Error handling

Non-2xx responses raise `SonoVaultError`:

```python
from sonovault import SonoVaultError

try:
    sv.tracks.browse(genre="House")  # paid-tier endpoint
except SonoVaultError as err:
    print(err.status, err.is_forbidden, err)
```

Rate-limited responses that carry a `Retry-After` header are retried automatically. The default is 2 retries, configurable with `max_retries`.

## API coverage

| Namespace | Methods |
|---|---|
| `sv.tracks` | `search`, `get`, `by_isrc`, `iswc`, `by_iswc`, `links`, `resolve`, `identify`, `identify_audio`, `browse` |
| `sv.artists` | `search`, `get`, `releases` |
| `sv.labels` | `search`, `get`, `releases`, `artists` |
| `sv.releases` | `search`, `get`, `latest` |
| `sv.genres` | `list` |
| `sv.suggestions` | `submit`, `list` |
| `sv.streams` | `create`, `list`, `get`, `update`, `history`, `report`, `live`, `stop` |
| `sv.webhooks` | `create`, `list`, `get`, `update`, `delete`, `test`, `deliveries` |

Some endpoints (audio identify, browse, stream monitoring) need a paid tier. See [pricing](https://sonovault.now/pricing). Everything else works on the free tier.

## Related

- [SonoVault API docs](https://sonovault.now/docs). Full endpoint reference with examples in 8 languages.
- [sonovault-js](https://github.com/rekordcloud/sonovault-js). The TypeScript/Node client.
- [Free ISRC lookup](https://sonovault.now/isrc-lookup) and [ISWC lookup](https://sonovault.now/iswc-lookup). Browser tools built on the same API.

## License

MIT
