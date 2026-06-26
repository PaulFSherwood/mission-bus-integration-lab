# adapters/common/terrain_grid.py
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DEFAULT_GRID_PATH = Path("data/terrain/kpns_kabq_terrain.pgm")
DEFAULT_BOUNDS_PATH = Path("data/terrain/kpns_kabq_terrain_bounds.json")


@dataclass(frozen=True)
class TerrainBounds:
    north: float
    south: float
    west: float
    east: float
    min_ft: float
    max_ft: float


@dataclass
class TerrainGrid:
    width: int
    height: int
    max_value: int
    pixels: list[int]
    bounds: TerrainBounds

    def sample_ft(self, lat: float, lon: float) -> float:
        if self.width <= 1 or self.height <= 1:
            return synthetic_terrain_ft(lat, lon)

        if self.bounds.east == self.bounds.west or self.bounds.north == self.bounds.south:
            return synthetic_terrain_ft(lat, lon)

        # Clamp to the terrain-map coverage.
        lon_c = max(self.bounds.west, min(self.bounds.east, lon))
        lat_c = max(self.bounds.south, min(self.bounds.north, lat))

        x = (lon_c - self.bounds.west) / (self.bounds.east - self.bounds.west) * (self.width - 1)
        y = (self.bounds.north - lat_c) / (self.bounds.north - self.bounds.south) * (self.height - 1)

        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        x1 = min(self.width - 1, x0 + 1)
        y1 = min(self.height - 1, y0 + 1)
        dx = x - x0
        dy = y - y0

        p00 = self._pixel(x0, y0)
        p10 = self._pixel(x1, y0)
        p01 = self._pixel(x0, y1)
        p11 = self._pixel(x1, y1)

        top = p00 * (1.0 - dx) + p10 * dx
        bottom = p01 * (1.0 - dx) + p11 * dx
        value = top * (1.0 - dy) + bottom * dy

        scale = 0.0 if self.max_value <= 0 else value / float(self.max_value)
        return self.bounds.min_ft + scale * (self.bounds.max_ft - self.bounds.min_ft)

    def _pixel(self, x: int, y: int) -> int:
        return self.pixels[y * self.width + x]


def _pgm_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        tokens.extend(line.split())
    return tokens


def load_pgm_grid(grid_path: Path = DEFAULT_GRID_PATH, bounds_path: Path = DEFAULT_BOUNDS_PATH) -> TerrainGrid | None:
    if not grid_path.exists() or not bounds_path.exists():
        return None

    tokens = _pgm_tokens(grid_path.read_text(encoding="utf-8"))
    if len(tokens) < 4 or tokens[0] != "P2":
        return None

    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    raw_pixels = [int(v) for v in tokens[4:]]

    expected = width * height
    if len(raw_pixels) < expected:
        return None

    raw_pixels = raw_pixels[:expected]

    data = json.loads(bounds_path.read_text(encoding="utf-8"))
    bounds = TerrainBounds(
        north=float(data["north"]),
        south=float(data["south"]),
        west=float(data["west"]),
        east=float(data["east"]),
        min_ft=float(data.get("min_ft", 0.0)),
        max_ft=float(data.get("max_ft", 10000.0)),
    )

    return TerrainGrid(
        width=width,
        height=height,
        max_value=max_value,
        pixels=raw_pixels,
        bounds=bounds,
    )


@lru_cache(maxsize=1)
def load_default_grid() -> TerrainGrid | None:
    return load_pgm_grid()


def synthetic_terrain_ft(lat: float, lon: float) -> float:
    """Fallback terrain model if no PGM terrain grid exists.

    This is simulation-only. It intentionally rises toward New Mexico so the
    KPNS/KHRT-to-KABQ route has useful TAWS behavior.
    """
    west_rise = max(0.0, (-lon - 94.0) * 470.0)
    gulf_lowland = max(0.0, 31.5 - lat) * -120.0
    ridge_a = max(0.0, math.sin((lat + lon) * 2.15)) * 1400.0
    ridge_b = max(0.0, math.sin((lat * 1.35) - (lon * 0.75))) * 900.0
    wave = math.sin(lat * 0.8) * 250.0 + math.cos(lon * 0.7) * 250.0

    return max(0.0, 300.0 + gulf_lowland + west_rise + ridge_a + ridge_b + wave)


def terrain_elevation_ft(lat: float, lon: float) -> float:
    grid = load_default_grid()
    if grid is not None:
        return grid.sample_ft(lat, lon)
    return synthetic_terrain_ft(lat, lon)


def lat_lon_from_offset(lat: float, lon: float, east_nm: float, north_nm: float) -> tuple[float, float]:
    avg_lat_rad = math.radians(lat)
    cos_lat = math.cos(avg_lat_rad)
    if abs(cos_lat) < 0.0001:
        cos_lat = 0.0001

    out_lat = lat + north_nm / 60.0
    out_lon = lon + east_nm / (60.0 * cos_lat)
    return out_lat, out_lon
