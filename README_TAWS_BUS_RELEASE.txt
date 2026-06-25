# MBIL TAWS / Weather Bus Release

This release makes TAWS and weather radar adapter/bus products instead of only
client-side display calculations.

## What changed

- Adapter now writes `TAWS_DATA` 1553-style messages from `TERRAIN_RT`.
- Adapter now writes `WEATHER_RADAR` 1553-style messages from `WEATHER_RADAR_RT`.
- `/api/state` now exposes:
  - `taws`
  - `weather_radar`
- TAWS / Weather display now prefers bus-derived `data.taws` and `data.weather_radar`.
- Cockpit radar and TAWS page use the same weather cells when adapter exchange is active.
- Control Center now has a Synthetic Profile selector:
  - normal
  - low-level
  - terrain-caution
  - terrain-pull-up

## Why this matters

The display is no longer the only place calculating TAWS state. The adapter
encodes terrain and weather products as 1553-style messages, MBIL reads those
messages, and the displays consume `/api/state`.

This better matches the project architecture:

sim/replay/DIS/source -> adapter truth -> RT/message products -> MBIL -> displays

## Test

Start the control center:

```bash
python -m tools.mbil_control_center
```

For a normal clear case:

1. Source: `synthetic`
2. Synthetic Profile: `normal`
3. Input Mode: `auto`
4. Click `Start Stack`
5. Open TAWS / Weather

For TAWS alert testing:

- Choose `terrain-caution` to force `CAUTION TERRAIN`.
- Choose `terrain-pull-up` to force `TERRAIN PULL UP`.

Watch exchange messages:

```bash
python tools/watch_exchange.py
```

You should see message types like:

```text
AIR_DATA, ATTITUDE_DATA, ENGINE_DATA, FUEL_DATA, NAV_DATA, TAWS_DATA, WEATHER_RADAR
```

Check API:

```text
http://127.0.0.1:8000/api/state
http://127.0.0.1:8000/api/input/status
http://127.0.0.1:8000/api/messages
```

## Headless examples

```bash
python -m adapters.mbil_adapter --headless --source synthetic --profile normal
python -m adapters.mbil_adapter --headless --source synthetic --profile terrain-caution
python -m adapters.mbil_adapter --headless --source synthetic --profile terrain-pull-up
```
