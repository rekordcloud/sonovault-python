"""Enrich a play log that only has artist + title with ISRC, album, and label.

Typical use: preparing a royalty report from radio automation output.
Run: SONOVAULT_API_KEY=svk_live_... python examples/enrich_play_log.py
"""

import os

from sonovault import SonoVault

sv = SonoVault(api_key=os.environ["SONOVAULT_API_KEY"])

# In real use, read these lines from your playout export.
play_log = [
    {"artist": "Daft Punk", "title": "One More Time"},
    {"artist": "Daft Punk", "title": "Around the World"},
    {"artist": "Daft Punk", "title": "Veridis Quo"},
]

batch = sv.tracks.resolve(input_type="track_name", items=play_log)

for row in batch["results"]:
    if row["status"] != "matched":
        print(f"NOT FOUND: {row['input']['artist']} - {row['input']['title']}")
        continue
    track = row["track"]
    release = track["releases"][0] if track["releases"] else {}
    label = (release.get("label") or {}).get("name")
    print(" | ".join(str(v) for v in [
        track["artists"][0]["name"], track["title"], track["isrc"], release.get("title"), label,
    ]))

print(f"\nProcessed {batch['processed']} lines, {batch['credits_used']} credits used.")
