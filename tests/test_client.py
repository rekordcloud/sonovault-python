import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock

import pytest

from sonovault import SonoVault, SonoVaultError, paginate, verify_webhook_signature

TRACK = {
    "id": 123,
    "title": "One More Time",
    "artists": [{"id": 1, "name": "Daft Punk"}],
    "isrc": "GBDUW0000053",
    "releases": [],
    "duration": 320,
    "genre": "House",
    "subgenre": None,
}


def make_response(status=200, body=None, headers=None):
    res = MagicMock()
    res.ok = 200 <= status < 300
    res.status_code = status
    res.headers = headers or {}
    res.content = b"" if body is None else json.dumps(body).encode()
    if body is None:
        res.json.side_effect = ValueError("no body")
    else:
        res.json.return_value = body
    return res


def make_client(*responses):
    session = MagicMock()
    session.request.side_effect = list(responses)
    return SonoVault(api_key="svk_test", session=session), session


def test_requires_api_key():
    with pytest.raises(ValueError):
        SonoVault(api_key="")


def test_search_sends_key_and_params():
    sv, session = make_client(make_response(body={"results": [TRACK], "next_cursor": None}))

    page = sv.tracks.search(artist="Daft Punk", title="One More Time", limit=5)

    assert page["results"][0]["isrc"] == "GBDUW0000053"
    method, url = session.request.call_args[0]
    kwargs = session.request.call_args[1]
    assert method == "GET"
    assert url == "https://api.sonovault.now/v1/tracks/search"
    assert kwargs["params"] == {"artist": "Daft Punk", "title": "One More Time", "limit": 5}
    assert kwargs["headers"]["x-api-key"] == "svk_test"


def test_none_params_are_dropped():
    sv, session = make_client(make_response(body={"results": [], "next_cursor": None}))

    sv.tracks.search(artist="Daft Punk", title="Around the World")

    assert "cursor" not in session.request.call_args[1]["params"]
    assert "limit" not in session.request.call_args[1]["params"]


def test_resolve_posts_json_body():
    sv, session = make_client(make_response(body={"results": [], "partial": False}))

    sv.tracks.resolve(input_type="isrc", items=["GBDUW0000053"])

    method, url = session.request.call_args[0]
    assert (method, url) == ("POST", "https://api.sonovault.now/v1/tracks/resolve")
    assert session.request.call_args[1]["json"] == {
        "input_type": "isrc",
        "items": ["GBDUW0000053"],
    }


def test_error_carries_status_and_message():
    sv, _ = make_client(make_response(status=403, body={"error": "Paid plan required"}))

    with pytest.raises(SonoVaultError) as exc:
        sv.tracks.browse(genre="House")

    assert exc.value.status == 403
    assert exc.value.is_forbidden
    assert "Paid plan required" in str(exc.value)


def test_retries_429_with_retry_after():
    sv, session = make_client(
        make_response(status=429, body={"error": "rate limited"}, headers={"Retry-After": "0"}),
        make_response(body=TRACK),
    )

    track = sv.tracks.get(123)

    assert track["title"] == "One More Time"
    assert session.request.call_count == 2


def test_does_not_retry_quota_429():
    sv, session = make_client(make_response(status=429, body={"error": "Monthly quota exceeded"}))

    with pytest.raises(SonoVaultError) as exc:
        sv.tracks.get(123)

    assert exc.value.is_rate_limited
    assert session.request.call_count == 1


def test_stream_report_maps_from_param():
    sv, session = make_client(make_response(body={"plays": []}))

    sv.streams.report(from_="2026-07-01", until="2026-07-08")

    assert session.request.call_args[1]["params"] == {"from": "2026-07-01", "until": "2026-07-08"}


def test_delete_returns_none_on_204():
    sv, _ = make_client(make_response(status=204))

    assert sv.webhooks.delete("wh_1") is None


def test_streams_live_parses_sse_frames():
    sv, session = make_client()
    res = MagicMock()
    res.ok = True
    res.iter_lines.return_value = [
        'data: {"id": "e1", "type": "stream.play.started", "created": 1, "data": {"stream_id": "s1"}}',
        "",
        ": keep-alive comment",
        "",
        "event: stream.online",
        'data: {"id": "e2", "type": "stream.online", "created": 2, "data": {"stream_id": "s1"}}',
        "",
    ]
    session.get.return_value = res

    events = list(sv.streams.live())

    assert [e["id"] for e in events] == ["e1", "e2"]
    assert events[1]["type"] == "stream.online"
    res.close.assert_called_once()


def test_streams_live_raises_on_error_response():
    sv, session = make_client()
    res = MagicMock()
    res.ok = False
    res.status_code = 401
    res.json.return_value = {"error": "nope"}
    session.get.return_value = res

    with pytest.raises(SonoVaultError) as exc:
        sv.streams.live()

    assert exc.value.status == 401


def _sign(secret, timestamp, payload):
    return hmac.new(
        secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256
    ).hexdigest()


def test_verify_webhook_signature_valid_and_tampered():
    secret = "whsec_test"
    payload = '{"id": "evt_1", "type": "stream.play.started"}'
    t = int(time.time())
    header = f"t={t},v1={_sign(secret, t, payload)}"

    assert verify_webhook_signature(secret, header, payload)
    assert verify_webhook_signature(secret, header, payload.encode())
    assert not verify_webhook_signature(secret, header, payload + "x")
    assert not verify_webhook_signature("whsec_other", header, payload)
    assert not verify_webhook_signature(secret, "garbage", payload)


def test_verify_webhook_signature_stale_timestamp():
    secret = "whsec_test"
    payload = "{}"
    t = int(time.time()) - 3600
    header = f"t={t},v1={_sign(secret, t, payload)}"

    assert not verify_webhook_signature(secret, header, payload)
    assert verify_webhook_signature(secret, header, payload, tolerance_seconds=0)


def test_custom_base_url():
    sv, session = make_client(make_response(body={"genres": []}))
    sv2 = SonoVault(api_key="svk_test", base_url="http://localhost:3000/", session=session)

    sv2.genres.list()

    assert session.request.call_args[0][1] == "http://localhost:3000/v1/genres"


def test_timeout_is_configurable():
    session = MagicMock()
    session.request.return_value = make_response(body={"genres": []})
    sv = SonoVault(api_key="svk_test", timeout=7.5, session=session)

    sv.genres.list()

    assert session.request.call_args[1]["timeout"] == 7.5


def test_sends_user_agent_header():
    sv, session = make_client(make_response(body={"genres": []}))

    sv.genres.list()

    ua = session.request.call_args[1]["headers"]["User-Agent"]
    assert ua.startswith("sonovault-python/")


def test_paginate_walks_all_pages():
    sv, session = make_client(
        make_response(body={"results": [{"id": 1}, {"id": 2}], "next_cursor": "c1"}),
        make_response(body={"results": [{"id": 3}], "next_cursor": None}),
    )

    items = list(paginate(lambda cursor: sv.suggestions.list(cursor=cursor)))

    assert [i["id"] for i in items] == [1, 2, 3]
    assert session.request.call_count == 2


def test_context_manager_closes_owned_session(monkeypatch):
    sv = SonoVault(api_key="svk_test")
    closed = []
    monkeypatch.setattr(sv._session, "close", lambda: closed.append(True))

    with sv:
        pass

    assert closed == [True]


def test_context_manager_leaves_injected_session_open():
    session = MagicMock()
    with SonoVault(api_key="svk_test", session=session):
        pass

    session.close.assert_not_called()
