MBIL Cockpit Nav Overlay Fix
============================

Fixes cockpit radar/map nav overlay behavior after Cockpit Wiring Phase 1.

Changes:
- Uses a shared waypoint-ident helper instead of only data.sim.current_wp/next_wp.
- Supports nav_display.current_wp/next_wp, route.current_wp/next_wp, and sim.current_wp/next_wp.
- Keeps cockpit radar flight plan drawn on top of weather returns.
- Highlights active leg and next waypoint in yellow.
- Draws waypoint labels with black outlines for readability.
- Schedules a second post-render overlay draw to prevent the radar renderer from clearing the route overlay.

Install from MBIL root:

    unzip MBIL_cockpit_nav_overlay_fix.zip -d .

Then hard-refresh the browser page.
