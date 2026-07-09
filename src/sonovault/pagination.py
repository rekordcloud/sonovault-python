"""Cursor-pagination helper."""

from typing import Any, Callable, Dict, Iterator, Optional


def paginate(fetch_page: Callable[[Optional[str]], Dict[str, Any]]) -> Iterator[Any]:
    """Iterate every item across all pages of a cursor-paginated endpoint.

    Example::

        from sonovault import SonoVault, paginate

        sv = SonoVault(api_key="...")
        for release in paginate(lambda cursor: sv.artists.releases(42, cursor=cursor)):
            print(release["title"])
    """
    cursor: Optional[str] = None
    while True:
        page = fetch_page(cursor)
        for item in page.get("results", []):
            yield item
        cursor = page.get("next_cursor")
        if not cursor:
            return
