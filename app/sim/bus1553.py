from dataclasses import dataclass

from app.sim.messages import Bus1553Message
from app.sim.remote_terminals import (
    AirDataRT,
    EngineRT,
    FuelRT,
    NavRT,
    WeatherRadarRT
)

@dataclass
class BusScheduleEntry:
   bus: str
   controller: str
   rt_name: str
   subaddress: int
   message_type: str
   word_count: int
   rate_ticks: int

class Bus1553:
   def __init__(self) -> None:
      self.remote_terminals = {
         "AIR_DATA_RT": AirDataRT(),
         "NAV_RT": NavRT(),
         "ENGINE_RT": EngineRT(),
         "FUEL_RT": FuelRT(),
         "WEATHER_RADAR_RT": WeatherRadarRT(),
      }

      self.schedule = [
         BusScheduleEntry("BUS_A", "MC1", "AIR_DATA_RT", 1, "AIR_DATA", 8, 1),
         BusScheduleEntry("BUS_A", "MC1", "NAV_RT", 1, "NAV_DATA", 8, 1),
         BusScheduleEntry("BUS_A", "MC1", "ENGINE_RT", 1, "ENGINE_DATA", 8, 1),
         BusScheduleEntry("BUS_A", "MC1", "FUEL_RT", 1, "FUEL_DATA", 8, 1),
         BusScheduleEntry("BUS_B", "MC2", "AIR_DATA_RT", 1, "AIR_DATA", 8, 1),
         BusScheduleEntry("BUS_B", "MC2", "NAV_RT", 1, "NAV_DATA", 8, 1),
         BusScheduleEntry("BUS_A", "MC1", "WEATHER_RADAR_RT", 1, "WEATHER_RADAR", 8, 1),
      ]

      self.monitor_log: list[Bus1553Message] = []
      self.latest_by_type: dict[str, Bus1553Message] = {}

   def run_tick(self, *, tick: int, aircraft, runtime) -> list[Bus1553Message]:
      messages: list[Bus1553Message] = []

      for entry in self.schedule:
         if tick % entry.rate_ticks != 0:
            continue

         rt = self.remote_terminals.get(entry.rt_name)

         if rt is None:
            continue

         msg = rt.respond(
            tick=tick,
            bus=entry.bus,
            controller=entry.controller,
            subaddress=entry.subaddress,
            message_type=entry.message_type,
            word_count=entry.word_count,
            aircraft=aircraft,
            runtime=runtime,
         )

         messages.append(msg)
         self.monitor_log.append(msg)

         if msg.status in ("OK", "STALE"):
            self.latest_by_type[msg.message_type] = msg

      self.monitor_log = self.monitor_log[-200:]

      return messages
   
   def recent_messages(self, limit: int = 50) -> list[dict]:
      return [msg.to_dict() for msg in reversed(self.monitor_log[-limit:])]

   def get_latest_payload(self, message_type: str) -> dict:
      msg = self.latest_by_type.get(message_type)

      if msg is None:
         return {}
      
      return msg.payload

   def set_rt_failed(self, rt_name, str, failed: bool) -> None:
      rt = self.remote_terminals.get(rt_name)

      if rt:
         rt.failed = failed

   def set_rt_stale(self, rt_name: str, stale: bool) -> None:
      rt = self.remote_terminals.get(rt_name)

      if rt:
         rt.stale = stale

   def fault_status(self) -> dict:
      terminals = {}

      for name, rt in self.remote_terminals.items():
         terminals[name] = {
            "failed": rt.failed,
            "stale": rt.stale,
            "status": "NO_RESPONSE" if rt.failed else "STALE" if rt.stale else "OK",
         }
      return {
         "remote_terminals": terminals,
         "bus_a": "ONLINE",
         "bus_b": "ONLINE",
      }
   
   def clear_fault(self) -> None:
      for rt in self.remote_terminals.values():
         rt.failed = False
         rt.stale = False