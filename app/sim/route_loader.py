from dataclasses import dataclass 
from pathlib import Path 

@dataclass 
class Waypoint:
    ident: str 
    lat: float 
    lon: float 

def gps_to_decimal(value: str) -> float:
    direction = value[0].upper()
    body = value[1:]

    parts = body.split()
    degrees = float(parts[0])
    minutes = float(parts[1])

    decimal = degrees + (minutes / 60.0)

    if direction in ("S", "W"):
        decimal *= -1

    return decimal

def load_route_points(path: str) -> list[Waypoint]:
    route_path = Path(path)
    waypoints: list[Waypoint] = []

    for line in route_path.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        parts = line.split()

        ident = parts[0]
        lat_raw = f"{parts[2]} {parts[3]}"
        lon_raw = f"{parts[4]} {parts[5]}"

        waypoints.append(
            Waypoint(
                ident=ident,
                lat=gps_to_decimal(lat_raw),
                lon=gps_to_decimal(lon_raw),
            )
        )
    
    return waypoints
