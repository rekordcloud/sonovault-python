"""Resolve one ISRC to its ID and deep link on every supported platform.

Run: SONOVAULT_API_KEY=svk_live_... python examples/cross_platform_links.py
"""

import os

from sonovault import SonoVault

sv = SonoVault(api_key=os.environ["SONOVAULT_API_KEY"])

# "One More Time" by Daft Punk
links = sv.tracks.links(isrc="GBDUW0000053")

for link in links["links"]:
    print(f"{link['source']:<12} {link['url']}")
