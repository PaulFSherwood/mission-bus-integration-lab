MBIL Cockpit Radar Heading-Up Fix
=================================

This patch keeps MAP / NAV north-up but changes the cockpit RADAR page back to aircraft-heading-up.

It keeps:
- radar range buttons
- no flashing route/BRG readout
- route drawn on top of weather
- active leg / next waypoint highlighted yellow

Install from MBIL root:

    unzip MBIL_cockpit_radar_heading_up_fix.zip -d .

Then hard refresh the browser with Ctrl+F5.
