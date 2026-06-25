from __future__ import annotations

import json
import socket
from math import sin
from time import sleep, time

HOST = "127.0.0.1"
PORT = 3000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Sending JSON test telemetry to udp://{HOST}:{PORT}. Ctrl+C to stop.")
try:
    while True:
        now = time()
        msg = {
            "source": "DIS_JSON_TEST",
            "timestamp": now,
            "lat": 35.04 + sin(now * 0.02) * 0.05,
            "lon": -106.60 + sin(now * 0.017) * 0.05,
            "altitude_ft": 9600 + sin(now * 0.05) * 400,
            "airspeed_kts": 220 + sin(now * 0.08) * 10,
            "heading_deg": (270 + sin(now * 0.04) * 20) % 360,
            "vertical_speed_fpm": sin(now * 0.07) * 300,
            "pitch_deg": 2.0 + sin(now * 0.09),
            "roll_deg": sin(now * 0.06) * 8,
            "fuel_lbs": 5200,
            "engine_temp_c": 630,
        }
        sock.sendto(json.dumps(msg).encode("utf-8"), (HOST, PORT))
        sleep(0.2)
except KeyboardInterrupt:
    print("Stopped.")
