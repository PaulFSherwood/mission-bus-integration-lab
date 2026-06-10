from dataclasses import dataclass 
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path 

@dataclass 
class Waypoint:
    ident: str 
    lat: float 
    lon: float 

def gps_to_decimal(direction_value: str, minutes_value: str) -> float:
    direction = direction_value[0].upper()
    degrees = float(direction_value[1:])
    minutes = float(minutes_value)

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

        # Example:
        # KPNS GPS N30 28.60 W87 11.07
        ident = parts[0]
        lat = gps_to_decimal(parts[2], parts[3])
        lon = gps_to_decimal(parts[4], parts[5])

        waypoints.append(Waypoint(ident=ident, lat=lat, lon=lon,))
    
    return waypoints

def distance_nm(a: Waypoint, b: Waypoint) -> float:
    """
    Simple flat-earth approximation.
    Good enough for this simulator.
    """
    avg_lat = radians((a.lat + b.lat) / 2.0)

    nm_per_degree_lat = 60.0 
    nm_per_degree_lon = 60.0 * cos(avg_lat)

    dx = (b.lon - a.lon) * nm_per_degree_lon
    dy = (b.lat - a.lat) * nm_per_degree_lat

    return sqrt(dx * dx + dy * dy)

def bearing_deg(a: Waypoint, b: Waypoint) -> float:
    avg_lat = radians((a.lat + b.lat) / 2.0)

    nm_per_degree_lat = 60.0 
    nm_per_degree_lon = 60.0 * cos(avg_lat)

    dx = (b.lon - a.lon) * nm_per_degree_lon
    dy = (b.lat - a.lat) * nm_per_degree_lat

    bearing = atan2(dx, dy)
    degrees = (bearing * 180.0 / 3.141592653589793) % 360.0 

    return degrees
    
