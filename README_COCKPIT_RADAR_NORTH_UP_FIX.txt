MBIL Cockpit Radar North-Up Fix
===============================

Fixes the cockpit radar flight-plan overlay so it uses the same north-up
projection as the MAP / NAV panel.

Changes:
- Cockpit radar nav overlay is north-up instead of heading-up.
- Overlay center matches the radar/map center instead of projecting from the lower display.
- Flight plan and active leg still draw on top of weather returns.
- Next waypoint remains yellow.
- Radar label changes from HDG UP to N UP.

Install from MBIL root:

    unzip MBIL_cockpit_radar_north_up_fix.zip -d .

Then hard refresh the browser with Ctrl+F5.
