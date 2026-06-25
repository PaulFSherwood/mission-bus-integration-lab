MBIL Control Center Release
===========================

Purpose
-------
This release adds one PyQt GUI to start and stop the separate MBIL pieces that were previously run in separate terminals:

- Adapter source process
- MBIL web server / uvicorn
- Exchange file watcher
- DIS JSON test sender
- Browser shortcuts for Cockpit, TAWS / Weather, and /api/input/status

Files added
-----------

tools/mbil_control_center.py
run_mbil_control_center.sh
README_CONTROL_CENTER_RELEASE.txt

Install / run
-------------

From the project root:

    pip install -r requirements_adapter.txt
    python -m tools.mbil_control_center

Or:

    ./run_mbil_control_center.sh

Recommended first test
----------------------

1. Start the Control Center.
2. Source: synthetic.
3. MBIL Input Mode: auto.
4. Click Start Stack.
5. Click Open Cockpit.
6. Click Open /api/input/status.

DIS JSON test
-------------

1. Set Adapter Source to dis.
2. Click Start Adapter.
3. Click Send DIS JSON Test.
4. Click Start MBIL Web if it is not already running.
5. Open /api/input/status or /api/messages.

Notes
-----

- This GUI does not replace the existing adapter GUI. It is a higher-level launcher/control panel.
- MBIL_INPUT_MODE is set by the GUI before starting uvicorn.
- If you close the GUI while processes are running, it will ask whether to stop them.
- Browser buttons open localhost by default. If you access MBIL from another machine, continue using the VM IP in your browser.
