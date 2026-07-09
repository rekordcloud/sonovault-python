"""Find a track's ISRC, genre, and label from artist + title.

Run: SONOVAULT_API_KEY=svk_live_... python examples/find_isrc.py
"""

import os

from sonovault import SonoVault

sv = SonoVault(api_key=os.environ["SONOVAULT_API_KEY"])

page = sv.tracks.search(artist="Daft Punk", title="Harder, Better, Faster, Stronger", limit=1)
track = page["results"][0]

print("Title: ", track["title"])
print("ISRC:  ", track["isrc"])
print("Genre: ", track["genre"])
release = track["releases"][0] if track["releases"] else None
print("Label: ", release["label"]["name"] if release and release["label"] else None)
