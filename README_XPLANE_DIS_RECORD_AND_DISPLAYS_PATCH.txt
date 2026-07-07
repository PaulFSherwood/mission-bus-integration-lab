MBIL X-Plane DIS Replay + Displays Patch
========================================

This patch adds two things:

1. Translated source recording
   - Raw DIS recording still records only real UDP DIS packets.
   - New option: "Record selected source as DIS replay".
   - This records X-Plane, Synthetic, or any decoded source as MBIL DIS JSON packets in:

       data/dis_captures/dis_capture_<timestamp>.jsonl

   - The existing DIS replay source can load these files later.
   - This is replayable MBIL JSON telemetry inside the existing DIS capture wrapper, not real binary DIS Entity State PDUs yet.

2. Real /displays page
   - /displays now renders a display bench instead of the not_found page.
   - Includes Pilot PFD, Radar, Map/Nav, Copilot PFD, summary, controls, simulated failures, data flow, and performance.
   - It reads /api/state and uses the same 1553/ARINC exchange-fed state as cockpit.

Install from MBIL root:

    unzip MBIL_xplane_dis_record_and_displays_patch.zip -d .

Usage: record X-Plane for replay later
--------------------------------------

1. Start X-Plane.
2. Start MBIL Control Center:

       ./run_mbil_control_center.sh

3. Set Source: xplane
4. Check: Record selected source as DIS replay
5. Start Adapter / Start Stack
6. Fly for a bit.
7. Stop Adapter.
8. Use Browse Replay to select the generated file from data/dis_captures.
9. Set Source: replay and start the adapter.

Headless example:

    python -m adapters.mbil_adapter --headless --source xplane --record-translated-dis

Replay example:

    python -m adapters.mbil_adapter --headless --source replay --replay data/dis_captures/dis_capture_1234567890.jsonl

Runtime files to keep out of git:

    data/dis_captures/*.jsonl
    data/exchange/*.json
    data/exchange/*.jsonl
