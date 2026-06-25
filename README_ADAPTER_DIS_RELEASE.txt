# MBIL Adapter / DIS Boundary Release

This release adds the first external source-adapter boundary without forcing MBIL
to become an X-Plane/MSFS/DCS/DIS parser.

## What this adds

- A standalone adapter switchboard program: `adapters/mbil_adapter.py`
- A Synthetic Aircraft Source moved outside the web UI path
- A DIS UDP source stub
- Raw DIS capture recording to `data/dis_captures/*.jsonl`
- DIS capture replay mode
- 1553-style exchange files in `data/exchange/`
- Stubbed ARINC 429, discrete, analog, and ethernet/AFDX-style exchange files
- MBIL web API endpoints:
  - `/api/adapter/status`
  - `/api/exchange/latest`

## Why this design

The adapter chooses the source of truth.
MBIL reads aircraft-style input products.

Source simulator / replay / synthetic model
  -> adapter truth model
  -> 1553 / ARINC / discrete / analog / ethernet encoders
  -> data/exchange files
  -> MBIL

This keeps MBIL from being tied directly to any one simulator.

## Install adapter GUI dependency

From your project venv:

```bash
pip install -r requirements_adapter.txt
```

If you do not want the GUI yet, run headless with no extra dependency:

```bash
python -m adapters.mbil_adapter --headless
```

## Run the PyQt adapter

```bash
python -m adapters.mbil_adapter
```

The GUI lets you choose:

- Synthetic Aircraft Source
- DIS UDP Source
- DIS Capture Replay
- X-Plane Stub
- MSFS Stub
- DCS Stub

The stubs are intentionally present so the architecture is ready without pretending
those adapters are implemented.

## DIS capture recording

1. Start the adapter GUI.
2. Choose `DIS UDP Source`.
3. Click `Start`.
4. Click `Record DIS`.
5. Send UDP packets to port 3000.
6. Click `Stop Record`.

Captures are written to:

```text
data/dis_captures/dis_capture_<timestamp>.jsonl
```

Phase 1 records raw UDP datagrams as base64 JSONL. If the datagram is JSON telemetry,
the adapter can decode it immediately for testing. Real binary DIS Entity State PDU
decoding is a later parser stage.

## Test DIS-like flow without a real DIS sender

Terminal 1:

```bash
python -m adapters.mbil_adapter
```

Choose `DIS UDP Source`, then Start.

Terminal 2:

```bash
python tools/send_json_dis_test.py
```

You should see decoded packet count increase and 1553 exchange files update.

## Exchange files written

```text
data/exchange/adapter_status.json
data/exchange/bus1553_A_latest.json
data/exchange/bus1553_B_latest.json
data/exchange/bus1553_messages.jsonl
data/exchange/arinc429_latest.json
data/exchange/discretes_latest.json
data/exchange/analog_latest.json
data/exchange/ethernet_latest.json
```

## Current MBIL behavior

This release does not rip out your existing internal MBIL runtime yet. That keeps the
working cockpit/TAWS/sensors pages stable.

Next release should switch MBIL from internal aircraft truth to reading the exchange
files, starting with 1553 latest/messages.

## Good commit name

```bash
git add app/main.py app/sim/exchange_reader.py adapters data/exchange data/dis_captures tools/send_json_dis_test.py requirements_adapter.txt README_ADAPTER_DIS_RELEASE.txt
git commit -m "Add adapter boundary with DIS capture and replay stubs"
```
