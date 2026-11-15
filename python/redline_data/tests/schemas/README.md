# Offline STAC schema fixtures

Pinned STAC 1.1.0, Projection 2.1.0, SSYS 1.1.1, plus their GeoJSON and PROJJSON dependencies. These are unchanged upstream JSON schemas; normalization to LF and a single final newline is recorded separately by source_sha256 and sha256. Schema registry tests never retrieve resources from the network. manifest.json records each official source URL and both hashes.

STAC and Projection: Apache-2.0 (LICENSE-stac.txt, LICENSE-projection.txt). SSYS: Unlicense (LICENSE-ssys.txt). GeoJSON: MIT, copyright 2018 Tim Schaub (LICENSE-geojson.txt). PROJJSON: PROJ MIT (LICENSE-projjson.txt). No project data or license entitlement is provided by these schemas.
