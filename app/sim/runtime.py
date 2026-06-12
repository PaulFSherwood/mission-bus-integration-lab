import json
from pathlib import Path

from dataclasses import dataclass, field 
from time import time 

from app.sim.bus1553 import Bus1553
from app.sim.route_loader import Waypoint, bearing_deg, distance_nm, load_route_points

@dataclass
class AircraftState:
    lat: float 
    lon: float 
    altitude_ft: float = 0.0
    airspeed_kts: float = 0.0
    heading_deg: float = 0.0
    vertical_speed_fpm: float = 0.0
    fuel_lbs: float = 5320.0
    engine_temp_c: float = 620.0

@dataclass
class BusMessage:
    tick: int
    bus: str
    source: str
    destination: str
    message_type: str
    payload: dict

@dataclass
class SimulatorRuntime:
   route_path: str
   route: list[Waypoint] = field(default_factory=list)
   aircraft: AircraftState | None = None
   current_leg_index: int = 0
   tick: int = 0
   last_update_time: float = field(default_factory=time)
   messages: list[BusMessage] = field(default_factory=list)
   bus: Bus1553 = field(default_factory=Bus1553)
   
   def map_info(self) -> dict:
       path = Path("data/maps/kpns_kabq_map_bounds.json")

       if not path.exists():
           return {}

       return json.loads(path.read_text())

   def start(self) -> None:
      self.route = load_route_points(self.route_path)

      if len(self.route) < 2:
         raise RuntimeError("Route must be at least two waypoints")

      start_wp = self.route[0]
      next_wp = self.route[1]

      self.aircraft = AircraftState(
         lat=start_wp.lat,
         lon=start_wp.lon,
         altitude_ft=1500.0,
         airspeed_kts=180.0,
         heading_deg=bearing_deg(start_wp, next_wp),
         vertical_speed_fpm=1200.0,
         fuel_lbs=5320.0,
         engine_temp_c=610.0,
      )

      self.current_leg_index = 0
      self.tick = 0
      self.last_update_time = time()
      self.messages.clear()

   def update(self) -> None:
      if self.aircraft is None:
         self.start()

      now = time()
      dt = now -self.last_update_time
      self.last_update_time = now

      # Avoid huge jumps after debugger pauses.
      if dt > 1.0:
         dt = 1.0

      self.tick += 1

      self._fly_aircraft(dt)
      self.bus.run_tick(
         tick=self.tick,
         aircraft=self.aircraft,
         runtime=self,
      )
      # Old simple message bus
      # self._publish_sensor_messages()

   def _fly_aircraft(self, dt: float) -> None:
      aircraft = self.aircraft

      if aircraft is None:
         return

      if self.current_leg_index >= len(self.route) - 1:
         aircraft.airspeed_kts = max(0.0, aircraft.airspeed_kts - 3.0)
         aircraft.vertical_speed_fpm = 0.0
         return

      from_wp = Waypoint("AIRCRAFT", aircraft.lat, aircraft.lon)
      to_wp = self.route[self.current_leg_index + 1]

      distance_to_wp = distance_nm(from_wp, to_wp)
      desired_heading = bearing_deg(from_wp, to_wp)

      aircraft.heading_deg = desired_heading

      # Simple climb/cruise/decent profile
      target_altitude = 28000.0

      if self.current_leg_index >= len(self.route) - 3:
         target_altitude = 7000.0

      altitude_error = target_altitude - aircraft.altitude_ft

      if abs(altitude_error) < 100.0:
         aircraft.vertical_speed_fpm = 0.0
      elif altitude_error > 0:
         aircraft.vertical_speed_fpm = 1500.0
      else:
         aircraft.vertical_speed_fpm = -1200.0

      aircraft.altitude_ft += (aircraft.vertical_speed_fpm / 60.0) * dt

      # Simple speed schedule.
      if aircraft.altitude_ft < 10000.0:
         target_speed = 250.0
      else:
         target_speed = 430.0

      if aircraft.airspeed_kts < target_speed:
         aircraft.airspeed_kts += 2.0 * dt 
      elif aircraft.airspeed_kts > target_speed:
         aircraft.airspeed_kts -= 2.0 * dt

      # Move aircraft along the heading
      distance_traveled_nm = aircraft.airspeed_kts * (dt / 3600.0)

      if distance_to_wp <= 2.0:
         self.current_leg_index += 1
         aircraft.lat = to_wp.lat
         aircraft.lon = to_wp.lon
         return
      
      fraction = min(distance_traveled_nm / distance_to_wp, 1.0)

      aircraft.lat = aircraft.lat + (to_wp.lat - aircraft.lat) * fraction
      aircraft.lon = aircraft.lon + (to_wp.lon - aircraft.lon) * fraction

      aircraft.fuel_lbs = max(0.0, aircraft.fuel_lbs - (0.35 * dt))
      aircraft.engine_temp_c = 620.0 + ((self.tick % 20) - 10)

   def _publish_sensor_messages(self) -> None:
      aircraft = self.aircraft

      if aircraft is None:
         return 
      
      current_wp = self.route[self.current_leg_index].ident

      if self.current_leg_index < len(self.route) - 1:
         next_wp = self.route[self.current_leg_index + 1].ident
      else:
         next_wp = self.route[-1].ident

      self.messages.append(
         BusMessage(
            tick=self.tick,
            bus="BUS_A",
            source="AIR_DATA_SENSOR",
            destination="MC1",
            message_type="AIR_DATA",
            payload={
               "altitude_ft": round(aircraft.altitude_ft),
               "airspeed_kts": round(aircraft.airspeed_kts),
               "vertical_speed_fpm": round(aircraft.vertical_speed_fpm),
            },
         )
      )

      self.messages.append(
         BusMessage(
            tick=self.tick,
            bus="BUS_B",
            source="NAV_SENSOR",
            destination="MC2",
            message_type="NAV_DATA",
            payload={
               "lat": round(aircraft.lat, 5),
               "lon": round(aircraft.lon, 5),
               "heading_deg": round(aircraft.heading_deg),
               "current_wp": current_wp,
               "next_wp": next_wp,
            },
         )
      )

      self.messages = self.messages[-50:]

   def to_api_state(self) -> dict:
      self.update()

      aircraft = self.aircraft 
      air_data = self.bus.get_latest_payload("AIR_DATA")
      nav_data = self.bus.get_latest_payload("NAV_DATA")
      engine_data = self.bus.get_latest_payload("ENGINE_DATA")
      fuel_data = self.bus.get_latest_payload("FUEL_DATA")
      weather_data = self.bus.get_latest_payload("WEATHER_RADAR")

      if aircraft is None:
         raise RuntimeError("Simulator not started")
      
      current_wp = self.route[self.current_leg_index].ident
      if self.current_leg_index < len(self.route) - 1:
         next_wp = self.route[self.current_leg_index + 1].ident
      else:
         next_wp = self.route[-1].ident

      route_points = [
         {
            "id": waypoint.ident,
            "lat": round(waypoint.lat, 5),
            "lon": round(waypoint.lon, 5),
         }
         for waypoint in self.route 
      ]

      return {
         "sim": {
            "tick": self.tick,
            "state": "RUNNING",
            "route": "KPNS-KABQ",
            "current_wp": current_wp,
            "next_wp": next_wp,
            "leg": self.current_leg_index + 1,
            "total_legs": len(self.route) - 1,
         },
         "map": self.map_info(),
         "route_points": route_points,
         "mc1": {
            "role": "PRIMARY",
            "state": "ONLINE",
         },
         "mc2": {
            "role": "STANDBY",
            "state": "ONLINE",
         },
         "aircraft": {
            "altitude": f"{round(air_data.get('altitude_ft', aircraft.altitude_ft)):,} FT",
            "airspeed": f"{round(air_data.get('airspeed_kts', aircraft.airspeed_kts))} KTS",
            "heading": f"{round(nav_data.get('heading_deg', aircraft.heading_deg)):03d}",
            "vertical_speed": f"{round(air_data.get('vertical_speed_fpm', aircraft.vertical_speed_fpm)):+} FPM",
            "fuel": f"{round(fuel_data.get('fuel_lbs', aircraft.fuel_lbs)):,} LBS",
            "engine_temp": f"{round(engine_data.get('engine_temp_c', aircraft.engine_temp_c))} C",
            "lat": round(nav_data.get('lat', aircraft.lat), 5),
            "lon": round(nav_data.get('lon', aircraft.lon), 5),
            "current_wp": nav_data.get("current_wp", current_wp),
            "next_wp": nav_data.get("next_wp", next_wp),
         },
         "bus1553": {
            "active_controller": "MC1",
            "bus_a": "ONLINE",
            "bus_b": "ONLINE",
            "message_count": len(self.bus.monitor_log),
         },
         "weather": weather_data,
      }
   
   def recent_messages(self) -> list[dict]:
      self.update()

      return [
         {
            "tick": msg.tick,
            "bus": msg.bus,
            "source": msg.source,
            "destination": msg.destination,
            "type": msg.message_type,
         }
         for msg in reversed(self.messages[-20:])
      ]

   def weather_cells(self) -> list[dict]:
      if self.aircraft is None:
         return []
      
      return [
         {
            "id": "WX01",
            "lat": round(self.aircraft.lat + 0.35, 5),
            "lon": round(self.aircraft.lon - 0.45, 5),
            "radius_nm": 12,
            "intensity": 0.75,
         },
         {
            "id": "WX02",
            "lat": round(self.aircraft.lat - 0.35, 5),
            "lon": round(self.aircraft.lon + 0.45, 5),
            "radius_nm": 7,
            "intensity": 0.45,
         }
      ]