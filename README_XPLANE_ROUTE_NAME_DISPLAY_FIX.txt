MBIL X-Plane Route Name / Display Fix
=====================================

Fixes:

1. Decodes X-Plane Web API fixed-string waypoint IDs.
   Example:
     TE9YTFkAAAAAAAA -> LOXLY
     U0pJAAAAAAAA    -> SJI

2. Rejects garbage placeholder GPS IDs instead of showing huge waypoint names.

3. Improves X-Plane .fms route file discovery.
   You can still force a route with:
     MBIL_XPLANE_FMS_FILE=/path/to/route.fms
   or:
     MBIL_XPLANE_FMS_DIR=/path/to/FMS/plans

4. If a full .fms route is found, MBIL uses the full route and chooses the active leg.
   If no .fms route is found, MBIL uses active GPS bearing/distance only.

5. Map/Nav and Radar display labels now sanitize waypoint IDs and truncate long route/distance text.

Install:

  unzip MBIL_xplane_route_name_display_fix.zip -d .

Then restart adapter/MBIL and hard-refresh browser:

  Ctrl+F5

Check:

  http://127.0.0.1:8000/api/state

Look for:

  xplane_route.point_count
  xplane_route.route_source
  xplane_route.current_wp
  xplane_route.next_wp

If point_count is only 2 and route_source is XPLANE_ACTIVE_GPS_ONLY, the Web API did not expose the full flight plan and MBIL did not find an .fms file. Save/copy the .fms file into data/xplane_route/ or set MBIL_XPLANE_FMS_FILE.
