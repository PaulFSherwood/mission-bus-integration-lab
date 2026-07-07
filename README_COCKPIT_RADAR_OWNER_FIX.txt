MBIL Cockpit Radar Owner Fix
============================

Fixes cockpit radar overlay issues:
- Cockpit radar canvas is north-up.
- Shared display renderer owns radar route drawing, not a second cockpit-only overlay.
- Route/active leg/next waypoint draw on top of weather.
- Range buttons use event delegation and refresh the display after a click.
- BRG/TO readouts keep last good values instead of blinking to ---.

Install from MBIL root:

    unzip MBIL_cockpit_radar_owner_fix.zip -d .

Then hard-refresh the browser with Ctrl+F5.
