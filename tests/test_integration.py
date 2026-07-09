"""Live integration tests against the production API.

Skipped unless SONOVAULT_API_KEY is set:

    SONOVAULT_API_KEY=svk_live_… pytest tests/test_integration.py
"""

import os

import pytest

from sonovault import SonoVault, SonoVaultError

API_KEY = os.environ.get("SONOVAULT_API_KEY")

pytestmark = pytest.mark.skipif(not API_KEY, reason="SONOVAULT_API_KEY not set")


@pytest.fixture(scope="module")
def sv():
    return SonoVault(api_key=API_KEY)


def test_search_by_artist_title(sv):
    page = sv.tracks.search(artist="Daft Punk", title="One More Time", limit=3)
    assert page["results"]
    track = page["results"][0]
    assert "one more time" in track["title"].lower()
    assert any(a["name"] == "Daft Punk" for a in track["artists"])
    assert track["isrc"]


def test_isrc_and_id_lookup_agree(sv):
    page = sv.tracks.search(artist="Daft Punk", title="Around the World", limit=1)
    found = page["results"][0]
    assert sv.tracks.by_isrc(found["isrc"])["id"] == found["id"]
    assert sv.tracks.get(found["id"])["title"] == found["title"]


def test_cross_platform_links(sv):
    page = sv.tracks.search(artist="Daft Punk", title="One More Time", limit=1)
    links = sv.tracks.links(isrc=page["results"][0]["isrc"])
    sources = [link["source"] for link in links["links"]]
    assert len(sources) > 1
    assert "spotify" in sources


def test_recording_to_iswc(sv):
    page = sv.tracks.search(artist="Daft Punk", title="One More Time", limit=1)
    work = sv.tracks.iswc(isrc=page["results"][0]["isrc"])
    assert isinstance(work.get("iswcs"), list)


def test_bulk_resolve(sv):
    page = sv.tracks.search(artist="Daft Punk", title="Harder, Better, Faster, Stronger", limit=1)
    found = page["results"][0]
    batch = sv.tracks.resolve(input_type="isrc", items=[found["isrc"]])
    assert batch["results"][0]["status"] == "matched"
    assert batch["results"][0]["track"]["id"] == found["id"]


def test_genres(sv):
    genres = sv.genres.list()["genres"]
    assert len(genres) > 10


def test_bad_key_is_401():
    bad = SonoVault(api_key="svk_live_invalid")
    with pytest.raises(SonoVaultError) as exc:
        bad.genres.list()
    assert exc.value.status == 401
