MBIL Cockpit Wiring Phase 1 Patch
=================================

Adds live cockpit wiring for:

- Pilot and copilot PFD attitude horizon using pitch/roll.
- Airspeed, altitude, vertical-speed, heading, and selected-bug displays.
- Autopilot / flight-director annunciators: AP, FD, YD, HDG, NAV, ALT, VS, FLC, APR, GS.
- Bearing pointer driven from GPS/nav bearing when available.
- Cockpit radar range buttons: 10, 20, 40, 80, 160 NM.
- Cockpit radar nav overlay with next waypoint highlighted yellow.
- MC1/MC2 CNI status driven from live exchange state.
- /api/state sections for autopilot, pfd, nav_display, radar_display, and mission_computers.
- 1553 AUTOPILOT_DATA messages and ARINC autopilot/selected bug labels.

Install from MBIL root:

    unzip MBIL_cockpit_wiring_phase1_patch.zip -d .

Run with X-Plane source:

    ./run_mbil_control_center.sh

Then open:

    http://127.0.0.1:8000/overview
    http://127.0.0.1:8000/api/state

Check /api/state for:

    autopilot
    pfd
    nav_display
    radar_display
    mission_computers

Notes:

- If an X-Plane autopilot dataref is not available on a given aircraft, the annunciator remains off.
- The cockpit radar still uses MBIL's weather-radar renderer, then overlays route/waypoint symbology on top.
- The next waypoint is drawn yellow on cockpit radar to match the TAWS/weather page behavior.
