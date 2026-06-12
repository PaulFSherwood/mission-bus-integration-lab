from typing import Any

from app.sim.messages import Bus1553Message, make_message

class RemoteTerminal:
   def __init__(self, rt_name: str, rt_address: int) -> None:
      self.rt_name = rt_name
      self.rt_address = rt_address
      self.failed = False
      self.stale = False
      self.last_payload: dict[str, Any] = {}

   def read_payload(self, aircraft, runtime) -> dict:
      return {}

   def respond(
      self,
      *,
      tick: int,
      bus: str,
      controller: str,
      subaddress: int,
      message_type: str,
      word_count: int,
      aircraft,
      runtime,
   ) -> Bus1553Message:
      if self.failed:
         return make_message(
            tick=tick,
            bus=bus,
            controller=controller,
            rt=self.rt_name,
            subaddress=subaddress,
            direction="RT_TO_BC",
            word_count=0,
            message_type=message_type,
            status="NO_RESPONSE",
            payload={},
         )
      if self.stale and self.last_payload:
         payload = self.last_payload
         status = "STALE"
      else:
         payload = self.read_payload(aircraft, runtime)
         self.last_payload = payload
         status = "OK"

      return make_message(
         tick=tick,
         bus=bus,
         controller=controller,
         rt=self.rt_name,
         subaddress=subaddress,
         direction="RT_TO_BC",
         word_count=word_count,
         message_type=message_type,
         status=status,
         payload=payload,
      )

class AirDataRT(RemoteTerminal):
   def __init__(self) -> None:
      super().__init__("AIR_DATA_RT", 1)

   def read_payload(self, aircraft, runtime) -> dict:
      return {
         "altitude_ft": round(aircraft.altitude_ft),
         "airspeed_kts": round(aircraft.airspeed_kts),
         "vertical_speed_fpm": round(aircraft.vertical_speed_fpm),
      }

class NavRT(RemoteTerminal):
   def __init__(self) -> None:
      super().__init__("NAV_RT", 2)

   def read_payload(self, aircraft, runtime) -> dict:
      current_wp = runtime.route[runtime.current_leg_index].ident

      if runtime.current_leg_index < len(runtime.route) - 1:
         next_wp = runtime.route[runtime.current_leg_index + 1].ident
      else:
         next_wp = runtime.route[-1].ident

      return {
         "lat": round(aircraft.lat, 5),
         "lon": round(aircraft.lon, 5),
         "heading_deg": round(aircraft.heading_deg),
         "current_wp": current_wp,
         "next_wp": next_wp,
      }

class EngineRT(RemoteTerminal):
   def __init__(self) -> None:
      super().__init__("ENGINE_RT", 3)

   def read_payload(self, aircraft, runtime) -> dict:
      return {
         "engine_temp_c": round(aircraft.engine_temp_c),
         "engine_status": "NORMAL",
      }

class FuelRT(RemoteTerminal):
   def __init__(self) -> None:
      super().__init__("FUEL_RT", 3)

   def read_payload(self, aircraft, runtime) -> dict:
      return {
         "fuel_lbs": round(aircraft.fuel_lbs),
         "fuel_status": "NORMAL",
      }

class WeatherRadarRT(RemoteTerminal):
   def __init__(self) -> None:
      super().__init__("WEATHER_RADAR_RT", 3)

   def read_payload(self, aircraft, runtime) -> dict:
      return {
         "mode": "WX",
         "range_nm": 40,
         "returns": runtime.weather_cells(),
      }
