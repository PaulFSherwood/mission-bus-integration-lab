import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image

Image.MAX_IMAGE_PIXELS = None

from app.sim.route_loader import load_route_points


ROUTE_PATH = "data/routes/kpns_kabq_points.txt"
WORLD_IMAGE_PATH = "data/maps/world_blue_marble.jpg"

OUTPUT_IMAGE_PATH = "app/static/img/kpns_kabq_base_map.png"
OUTPUT_BOUNDS_PATH = "data/maps/kpns_kabq_map_bounds.json"


def lon_to_x(lon: float, width: int) -> int:
    return int(((lon + 180.0) / 360.0) * width)


def lat_to_y(lat: float, height: int) -> int:
    return int(((90.0 - lat) / 180.0) * height)


def main() -> None:
    route = load_route_points(ROUTE_PATH)

    lats = [wp.lat for wp in route]
    lons = [wp.lon for wp in route]

    south = min(lats)
    north = max(lats)
    west = min(lons)
    east = max(lons)

    # Padding so route is not against the edge.
    lat_pad = max((north - south) * 0.20, 1.0)
    lon_pad = max((east - west) * 0.20, 1.0)

    south -= lat_pad
    north += lat_pad
    west -= lon_pad
    east += lon_pad

    world_path = Path(WORLD_IMAGE_PATH)

    if not world_path.exists():
        raise FileNotFoundError(f"Missing world image: {WORLD_IMAGE_PATH}")

    image = Image.open(world_path).convert("RGB")
    width, height = image.size

    left = lon_to_x(west, width)
    right = lon_to_x(east, width)
    top = lat_to_y(north, height)
    bottom = lat_to_y(south, height)

    crop = image.crop((left, top, right, bottom))

    # This keeps the cockpit load quick.
    crop.thumbnail((1600, 900))

    output_image_path = Path(OUTPUT_IMAGE_PATH)
    output_image_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(output_image_path)

    bounds = {
        "image": "/static/img/kpns_kabq_base_map.png",
        "north": north,
        "south": south,
        "west": west,
        "east": east,
    }

    output_bounds_path = Path(OUTPUT_BOUNDS_PATH)
    output_bounds_path.parent.mkdir(parents=True, exist_ok=True)
    output_bounds_path.write_text(json.dumps(bounds, indent=2))

    print("Wrote:", OUTPUT_IMAGE_PATH)
    print("Wrote:", OUTPUT_BOUNDS_PATH)
    print(json.dumps(bounds, indent=2))


if __name__ == "__main__":
    main()
