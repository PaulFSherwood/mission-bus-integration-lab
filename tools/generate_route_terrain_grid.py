# tools/generate_route_terrain_grid.py
from __future__ import annotations

import json
from pathlib import Path

# Small enough for Git, large enough to create useful TAWS returns.
WIDTH = 96
HEIGHT = 64
OUT_DIR = Path("data/terrain")
PGM_PATH = OUT_DIR / "kpns_kabq_terrain.pgm"
BOUNDS_PATH = OUT_DIR / "kpns_kabq_terrain_bounds.json"

# Covers the current KPNS-KABQ base map area.
BOUNDS = {
    "north": 36.114,
    "south": 29.476666666666667,
    "west": -110.4949,
    "east": -83.29943333333334,
}


def synthetic_height(lat: float, lon: float) -> float:
    # Deliberately simple and deterministic. This is not real DEM data.
    # Gulf/eastern side low, western/New Mexico side higher, with ridge bands.
    import math

    west_rise = max(0.0, (-lon - 94.0) * 470.0)
    gulf_lowland = max(0.0, 31.5 - lat) * -120.0
    ridge_a = max(0.0, math.sin((lat + lon) * 2.15)) * 1400.0
    ridge_b = max(0.0, math.sin((lat * 1.35) - (lon * 0.75))) * 900.0
    wave = math.sin(lat * 0.8) * 250.0 + math.cos(lon * 0.7) * 250.0

    return max(0.0, 300.0 + gulf_lowland + west_rise + ridge_a + ridge_b + wave)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    heights: list[float] = []
    for y in range(HEIGHT):
        lat = BOUNDS["north"] - (y / (HEIGHT - 1)) * (BOUNDS["north"] - BOUNDS["south"])
        for x in range(WIDTH):
            lon = BOUNDS["west"] + (x / (WIDTH - 1)) * (BOUNDS["east"] - BOUNDS["west"])
            heights.append(synthetic_height(lat, lon))

    min_ft = min(heights)
    max_ft = max(heights)
    span = max(1.0, max_ft - min_ft)
    pixels = [round((h - min_ft) / span * 255) for h in heights]

    with PGM_PATH.open("w", encoding="utf-8") as f:
        f.write("P2\n")
        f.write("# MBIL synthetic grayscale elevation grid. Simulation-only.\n")
        f.write(f"{WIDTH} {HEIGHT}\n")
        f.write("255\n")
        for row in range(HEIGHT):
            start = row * WIDTH
            end = start + WIDTH
            f.write(" ".join(str(v) for v in pixels[start:end]))
            f.write("\n")

    bounds_out = dict(BOUNDS)
    bounds_out["min_ft"] = round(min_ft, 1)
    bounds_out["max_ft"] = round(max_ft, 1)
    bounds_out["width"] = WIDTH
    bounds_out["height"] = HEIGHT
    bounds_out["format"] = "P2 PGM grayscale elevation"
    bounds_out["simulation_only"] = True

    BOUNDS_PATH.write_text(json.dumps(bounds_out, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {PGM_PATH} ({PGM_PATH.stat().st_size} bytes)")
    print(f"Wrote {BOUNDS_PATH} ({BOUNDS_PATH.stat().st_size} bytes)")
    print(f"Elevation range: {min_ft:.1f} ft to {max_ft:.1f} ft")


if __name__ == "__main__":
    main()
