# MBIL Exchange Input Release

This release is the next step after the adapter / DIS boundary release.

It connects MBIL's web API to the adapter exchange files without removing the
internal simulator yet.

## What changed

- Adapter CLI now accepts easy source names:
  - `--source synthetic`
  - `--source dis`
  - `--source replay`
  - `--source xplane`
  - `--source msfs`
  - `--source dcs`
- Adapter `AircraftTruth` now carries route/current waypoint/next waypoint.
- 1553 NAV_DATA messages now include route/current_wp/next_wp/source.
- MBIL `/api/state` can now be built from `data/exchange/bus1553_*_latest.json`.
- MBIL `/api/messages` can now show adapter-written 1553 messages.
- New `/api/input/status` endpoint shows adapter freshness and input mode.
- Added `tools/watch_exchange.py` to verify exchange files without opening MBIL.

## Input modes

Set with environment variable `MBIL_INPUT_MODE`.

```bash
# Default. Use adapter exchange files when fresh, otherwise fall back to internal sim.
MBIL_INPUT_MODE=auto

# Ignore adapter files and use built-in sim only.
MBIL_INPUT_MODE=internal

# Prefer adapter exchange files. Useful when testing the adapter boundary.
MBIL_INPUT_MODE=exchange
```

Freshness defaults to 3 seconds:

```bash
MBIL_EXCHANGE_STALE_SEC=3.0
```

## Recommended first test: synthetic adapter -> MBIL

Terminal 1:

```bash
python -m adapters.mbil_adapter --headless --source synthetic
```

Terminal 2:

```bash
python tools/watch_exchange.py
```

You should see messages like:

```text
source=Synthetic Aircraft Source online=True age=0.10s messages=6 types=AIR_DATA,ATTITUDE_DATA,ENGINE_DATA,FUEL_DATA,NAV_DATA
```

Terminal 3:

```bash
MBIL_INPUT_MODE=auto python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

```text
http://<vm-ip>:8000/overview
http://<vm-ip>:8000/api/input/status
http://<vm-ip>:8000/api/messages
```

With the adapter fresh, `/api/state` should contain:

```json
"input": {
  "active": "exchange"
}
```

## DIS JSON test

Important: if you want the JSON DIS test sender to be consumed, the adapter must
be running with the DIS source, not the synthetic source.

Terminal 1:

```bash
python -m adapters.mbil_adapter --headless --source dis
```

Terminal 2:

```bash
python tools/send_json_dis_test.py
```

Terminal 3:

```bash
python tools/watch_exchange.py
```

You should see DIS raw and decoded counts rising in the adapter terminal, and
`source=DIS UDP Source` in `watch_exchange.py`.

Then run MBIL:

```bash
MBIL_INPUT_MODE=auto python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The cockpit should now be driven by the adapter's 1553-style exchange files.

## DIS capture recording

Headless recording:

```bash
python -m adapters.mbil_adapter --headless --source dis --record-dis
```

Captures are written to:

```text
data/dis_captures/dis_capture_<timestamp>.jsonl
```

Replay:

```bash
python -m adapters.mbil_adapter --headless --replay data/dis_captures/dis_capture_<timestamp>.jsonl
```

## What is still intentionally not done

- MBIL still has the internal simulator available as fallback.
- Real binary DIS Entity State PDU decoding is still a later step.
- X-Plane / MSFS / DCS remain stubs.
- ARINC 429, discrete, analog, and ethernet files are still stubs.

This release proves the important architecture:

```text
Adapter chooses source of truth
  -> adapter writes avionics-style exchange files
  -> MBIL reads 1553-style messages
  -> cockpit / bus monitor / sensors use bus-derived state
```
