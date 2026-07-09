"""Follow your monitored streams in real time over Server-Sent Events.

Needs at least one registered stream (POST /v1/streams). Blocks while
waiting for events; stop with Ctrl+C.
Run: SONOVAULT_API_KEY=svk_live_... python examples/live_events.py
"""

import os

from sonovault import SonoVault

sv = SonoVault(api_key=os.environ["SONOVAULT_API_KEY"])

print("Listening for stream events (Ctrl+C to stop)...")
try:
    for event in sv.streams.live():
        if event["type"] == "stream.play.started":
            track = event["data"].get("track") or {}
            artist = (track.get("artists") or [{}])[0].get("name")
            print(f"[{event['data']['stream_id']}] now playing: {artist} - {track.get('title')}")
        else:
            print(f"[{event['data']['stream_id']}] {event['type']}")
except KeyboardInterrupt:
    print("\nDone.")
