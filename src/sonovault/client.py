"""SonoVault API client.

Usage:
    from sonovault import SonoVault

    sv = SonoVault(api_key="...")
    page = sv.tracks.search(artist="Daft Punk", title="One More Time")
    print(page["results"][0]["isrc"])
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union

import requests

from ._version import __version__
from .errors import SonoVaultError

DEFAULT_BASE_URL = "https://api.sonovault.now"
USER_AGENT = f"sonovault-python/{__version__}"


class SonoVault:
    """Client for the SonoVault music metadata API (https://sonovault.now).

    Args:
        api_key: your API key. Get a free one at https://sonovault.now
            (1,000 requests/month, no credit card).
        base_url: override the API base URL.
        max_retries: retries on retryable 429/5xx responses. Default 2.
        timeout: per-request timeout in seconds. Default 30. Does not apply
            to the read side of ``streams.live()``, which stays open.
        session: optional ``requests.Session`` (for pooling or testing).
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 2,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ):
        if not api_key:
            raise ValueError("SonoVault: api_key is required")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._timeout = timeout
        self._session = session or requests.Session()

        self._owns_session = session is None

        self.tracks = _Tracks(self)
        self.artists = _Artists(self)
        self.labels = _Labels(self)
        self.releases = _Releases(self)
        self.genres = _Genres(self)
        self.suggestions = _Suggestions(self)
        self.streams = _Streams(self)
        self.webhooks = _Webhooks(self)

    def close(self) -> None:
        """Close the underlying session (only if the client created it)."""
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> "SonoVault":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # -- plumbing ---------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Any = None,
        data: Optional[bytes] = None,
        content_type: Optional[str] = None,
    ) -> Any:
        url = self._base_url + path
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        headers = {"x-api-key": self._api_key, "User-Agent": USER_AGENT}
        if content_type:
            headers["Content-Type"] = content_type

        last_error: Optional[SonoVaultError] = None
        for attempt in range(self._max_retries + 1):
            try:
                res = self._session.request(
                    method, url, params=clean_params, json=json, data=data,
                    headers=headers, timeout=self._timeout,
                )
            except requests.RequestException as exc:
                last_error = SonoVaultError(f"Network error: {exc}", 0)
                continue

            if res.ok:
                if res.status_code == 204 or not res.content:
                    return None
                return res.json()

            try:
                body = res.json()
            except ValueError:
                body = None
            message = None
            if isinstance(body, dict):
                message = body.get("error") or body.get("message")
            last_error = SonoVaultError(message or f"HTTP {res.status_code}", res.status_code, body)

            # Retry only transient failures. A 429 with Retry-After is a rate
            # limit (retryable); a 429 without one is usually quota exhaustion.
            retry_after = res.headers.get("Retry-After")
            retryable = res.status_code >= 500 or (res.status_code == 429 and retry_after is not None)
            if not retryable or attempt == self._max_retries:
                raise last_error
            time.sleep(float(retry_after) if retry_after else 0.5 * (2 ** attempt))

        raise last_error or SonoVaultError("Request failed", 0)

    def _sse(self, path: str):
        """Connect to an SSE endpoint. Yield one parsed JSON dict per event."""
        import json as _json

        url = self._base_url + path
        headers = {
            "x-api-key": self._api_key,
            "User-Agent": USER_AGENT,
            "Accept": "text/event-stream",
        }
        # Connect timeout only. The read side must stay open indefinitely.
        res = self._session.get(url, headers=headers, stream=True, timeout=(self._timeout, None))
        if not res.ok:
            try:
                body = res.json()
            except ValueError:
                body = None
            message = body.get("error") if isinstance(body, dict) else None
            raise SonoVaultError(message or f"HTTP {res.status_code}", res.status_code, body)

        def events():
            data_lines = []
            try:
                for line in res.iter_lines(decode_unicode=True):
                    if line is None:
                        continue
                    if line == "":
                        # Blank line ends the frame.
                        if data_lines:
                            raw = "\n".join(data_lines)
                            data_lines.clear()
                            try:
                                yield _json.loads(raw)
                            except ValueError:
                                pass  # skip non-JSON frames (keep-alives)
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].lstrip(" "))
                    # event:, id:, retry:, and comment lines are ignored.
            finally:
                res.close()

        return events()


class _Namespace:
    def __init__(self, client: SonoVault):
        self._client = client


class _Tracks(_Namespace):
    def search(self, *, artist: str, title: str, limit: Optional[int] = None,
               cursor: Optional[str] = None) -> Dict[str, Any]:
        """Search by artist + title (both required — there is no free-text query)."""
        return self._client._request("GET", "/v1/tracks/search", params={
            "artist": artist, "title": title, "limit": limit, "cursor": cursor,
        })

    def get(self, track_id: int) -> Dict[str, Any]:
        """Fetch a track by its SonoVault ID."""
        return self._client._request("GET", f"/v1/tracks/{track_id}")

    def by_isrc(self, isrc: str) -> Dict[str, Any]:
        """Look up a track by any of its ISRCs."""
        return self._client._request("GET", f"/v1/tracks/isrc/{isrc}")

    def iswc(self, *, isrc: Optional[str] = None, track_id: Optional[int] = None) -> Dict[str, Any]:
        """Recording → composition: the ISWC(s) behind a recording."""
        return self._client._request("GET", "/v1/tracks/iswc",
                                     params={"isrc": isrc, "id": track_id})

    def by_iswc(self, iswc: str, *, limit: Optional[int] = None) -> Dict[str, Any]:
        """Composition → recordings: every recording of a work, by ISWC."""
        return self._client._request("GET", f"/v1/tracks/iswc/{iswc}", params={"limit": limit})

    def links(self, **ids: Union[str, int]) -> Dict[str, Any]:
        """Cross-platform IDs + deep links, from any platform ID or ISRC.

        Keyword args: ``id``, ``isrc``, ``spotify_id``, ``beatport_id``,
        ``discogs_id``, ``musicbrainz_id``, ``applemusic_id``, ``tidal_id``,
        ``youtube_id``.
        """
        return self._client._request("GET", "/v1/tracks/links", params=dict(ids))

    def resolve(self, *, input_type: str,
                items: List[Union[str, Dict[str, str]]]) -> Dict[str, Any]:
        """Resolve up to 100 track names, ISRCs, or platform IDs in one request."""
        return self._client._request("POST", "/v1/tracks/resolve",
                                     json={"input_type": input_type, "items": items})

    def identify(self, *, fingerprint: List[int],
                 fingerprint_duration: Optional[float] = None,
                 top_n: Optional[int] = None) -> Dict[str, Any]:
        """Identify a track from a Chromaprint fingerprint (``fpcalc -raw``). Paid tiers."""
        body: Dict[str, Any] = {"fingerprint": fingerprint}
        if fingerprint_duration is not None:
            body["fingerprint_duration"] = fingerprint_duration
        if top_n is not None:
            body["top_n"] = top_n
        return self._client._request("POST", "/v1/tracks/identify", json=body)

    def identify_audio(self, audio: bytes, *, length: Optional[int] = None,
                       top_n: Optional[int] = None) -> Dict[str, Any]:
        """Identify a track from raw audio bytes (any ffmpeg-decodable format).

        Send the whole track when you can — the matching section is often
        mid-track. Paid tiers; costs 10 + ceil(MB) credits.
        """
        return self._client._request(
            "POST", "/v1/tracks/identify",
            params={"length": length, "top_n": top_n},
            data=audio, content_type="application/octet-stream",
        )

    def browse(self, **params: Any) -> Dict[str, Any]:
        """Browse the catalog by ``labelId``, ``artistId``, ``genre``, ``genreId``,
        ``year``, or ``randomize``. Paid tiers."""
        return self._client._request("GET", "/v1/tracks/browse", params=dict(params))


class _Artists(_Namespace):
    def search(self, *, name: str, limit: Optional[int] = None,
               cursor: Optional[str] = None) -> Dict[str, Any]:
        return self._client._request("GET", "/v1/artists/search",
                                     params={"name": name, "limit": limit, "cursor": cursor})

    def get(self, artist_id: int) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/artists/{artist_id}")

    def releases(self, artist_id: int, *, limit: Optional[int] = None,
                 cursor: Optional[str] = None) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/artists/{artist_id}/releases",
                                     params={"limit": limit, "cursor": cursor})


class _Labels(_Namespace):
    def search(self, *, name: str, limit: Optional[int] = None,
               cursor: Optional[str] = None) -> Dict[str, Any]:
        return self._client._request("GET", "/v1/labels/search",
                                     params={"name": name, "limit": limit, "cursor": cursor})

    def get(self, label_id: int) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/labels/{label_id}")

    def releases(self, label_id: int, *, limit: Optional[int] = None,
                 cursor: Optional[str] = None) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/labels/{label_id}/releases",
                                     params={"limit": limit, "cursor": cursor})

    def artists(self, label_id: int, *, limit: Optional[int] = None,
                cursor: Optional[str] = None) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/labels/{label_id}/artists",
                                     params={"limit": limit, "cursor": cursor})


class _Releases(_Namespace):
    def search(self, *, title: str, artist: Optional[str] = None,
               limit: Optional[int] = None, cursor: Optional[str] = None) -> Dict[str, Any]:
        return self._client._request("GET", "/v1/releases/search", params={
            "title": title, "artist": artist, "limit": limit, "cursor": cursor,
        })

    def get(self, release_id: int) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/releases/{release_id}")

    def latest(self, *, limit: Optional[int] = None,
               cursor: Optional[str] = None) -> Dict[str, Any]:
        """Newly released albums (``GET /v1/releases/new``). Paid tiers."""
        return self._client._request("GET", "/v1/releases/new",
                                     params={"limit": limit, "cursor": cursor})


class _Genres(_Namespace):
    def list(self) -> Dict[str, Any]:
        """The canonical genre/subgenre hierarchy."""
        return self._client._request("GET", "/v1/genres")


class _Suggestions(_Namespace):
    def submit(self, track_id: int, body: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest a metadata correction for a track. Paid tiers."""
        return self._client._request("POST", f"/v1/tracks/{track_id}/suggestions", json=body)

    def list(self, *, limit: Optional[int] = None,
             cursor: Optional[str] = None) -> Dict[str, Any]:
        return self._client._request("GET", "/v1/suggestions",
                                     params={"limit": limit, "cursor": cursor})


class _Streams(_Namespace):
    def create(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Start monitoring an Icecast/Shoutcast stream. Paid tiers."""
        return self._client._request("POST", "/v1/streams", json=body)

    def list(self) -> Dict[str, Any]:
        return self._client._request("GET", "/v1/streams")

    def get(self, stream_id: str) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/streams/{stream_id}")

    def update(self, stream_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._client._request("PATCH", f"/v1/streams/{stream_id}", json=body)

    def history(self, stream_id: str, *, since: Optional[str] = None) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/streams/{stream_id}/history",
                                     params={"since": since})

    def report(self, *, from_: str, until: str,
               stream_id: Optional[str] = None) -> Dict[str, Any]:
        """Play report between two timestamps. ``from_`` maps to the ``from`` param."""
        return self._client._request("GET", "/v1/streams/report", params={
            "from": from_, "until": until, "stream_id": stream_id,
        })

    def live(self):
        """Real-time play events for your monitored streams.

        Yields one dict per Server-Sent Event. Blocks while waiting for
        events; run it in a thread if you need concurrency::

            for event in sv.streams.live():
                print(event["data"].get("track", {}).get("title"))
        """
        return self._client._sse("/v1/streams/live")

    def stop(self, stream_id: str) -> None:
        """Stop monitoring a stream."""
        return self._client._request("DELETE", f"/v1/streams/{stream_id}")


class _Webhooks(_Namespace):
    def create(self, *, url: str, event_types: Optional[List[str]] = None,
               description: Optional[str] = None) -> Dict[str, Any]:
        """Register a webhook. The response includes ``secret`` once — store it."""
        body: Dict[str, Any] = {"url": url}
        if event_types is not None:
            body["event_types"] = event_types
        if description is not None:
            body["description"] = description
        return self._client._request("POST", "/v1/webhooks", json=body)

    def list(self) -> Dict[str, Any]:
        return self._client._request("GET", "/v1/webhooks")

    def get(self, webhook_id: str) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/webhooks/{webhook_id}")

    def update(self, webhook_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._client._request("PATCH", f"/v1/webhooks/{webhook_id}", json=body)

    def delete(self, webhook_id: str) -> None:
        return self._client._request("DELETE", f"/v1/webhooks/{webhook_id}")

    def test(self, webhook_id: str) -> Dict[str, Any]:
        return self._client._request("POST", f"/v1/webhooks/{webhook_id}/test")

    def deliveries(self, webhook_id: str) -> Dict[str, Any]:
        return self._client._request("GET", f"/v1/webhooks/{webhook_id}/deliveries")
