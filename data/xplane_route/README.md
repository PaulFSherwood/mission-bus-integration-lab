# X-Plane Route Files

Optional local route source for the MBIL X-Plane adapter.

If the X-Plane Web API does not expose the full FMS route list, copy a `.fms` flight plan here. The adapter will parse the newest `.fms` file and write `data/exchange/route_latest.json`.

Runtime/probe JSON should not be committed.
