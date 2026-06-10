from time import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

app = FastAPI(title="MBIL")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

NAV_ITEMS = [
    {"label": "Cockpit", "endpoint": "/overview", "icon": "cockpit"},
    {"label": "Mission Computers", "endpoint": "/mission-computers", "icon": "computer"},
    {"label": "Bus Messages", "endpoint": "/bus-monitor", "icon": "bus"},
    {"label": "Sensors", "endpoint": "/sensors", "icon": "sensor"},
    {"label": "Displays", "endpoint": "/displays", "icon": "display"},
    {"label": "Fault Injection", "endpoint": "/faults", "icon": "fault"},
    {"label": "Scenario", "endpoint": "/scenario", "icon": "scenario"},
    {"label": "Event Log", "endpoint": "/event-log", "icon": "log"},
    {"label": "Settings", "endpoint": "/settings", "icon": "settings"},
]

PAGE_DATA = {
    "/overview": {
        "title": "Cockpit",
        "subtitle": "Primary operator cockpit view for the simulated mission bus lab.",
        "template": "dashboard.html",
        "hide_heading": True,
    },
    "/mission-computers": {
        "title": "Mission Computers",
        "subtitle": "MC1 / MC2 role, heartbeat, failover, and message processing state.",
        "template": "mission_computers.html",
    },
    "/bus-monitor": {
        "title": "Bus Messages",
        "subtitle": "Simulated message traffic, bus timing, and message health.",
        "template": "bus_monitor.html",
    },
    "/sensors": {
        "title": "Sensors",
        "subtitle": "Air data, INS, engine, and fuel sensor output.",
        "template": "sensors.html",
    },
    "/displays": {
        "title": "Displays",
        "subtitle": "Display update rates, stale data detection, and display health.",
        "template": "not_found.html",
    },
    "/faults": {
        "title": "Fault Injection",
        "subtitle": "Inject simulated failures into sensors, buses, messages, and mission computers.",
        "template": "faults.html",
    },
    "/scenario": {
        "title": "Scenario",
        "subtitle": "Load scenarios, schedule events, and control simulation progression.",
        "template": "not_found.html",
    },
    "/event-log": {
        "title": "Event Log",
        "subtitle": "Warnings, failures, recoveries, and operator actions.",
        "template": "not_found.html",
    },
    "/settings": {
        "title": "Settings",
        "subtitle": "Simulation, bus, display, logging, and developer configuration.",
        "template": "not_found.html",
    },
}

DEMO_CONTEXT = {
    "sim_tick": "123456",
    "sim_state": "RUNNING",
    "tick_rate": "10 Hz",
    "sim_time": "00:12:34",
}

@app.get("/api/state")
def api_state():
    tick = int(time() * 2)

    altitude = 9600 + (tick % 100)
    airspeed = 210 + (tick % 10)
    heading = 142 + (tick % 5)
    engine_temp = 620 + (tick % 20)

    return {

        "mc1": {
            "role": "PRIMARY",
            "state": "ONLINE",
        },

        "mc2": {
            "role": "STANDBY",
            "state": "ONLINE",
        },

        "aircraft": {
            "altitude": f"{altitude:,} FT",
            "airspeed": f"{airspeed} KTS",
            "heading": f"{heading}",
            "vertical_speed": "+501 FPM",
            "fuel": "5,320 LBS",
            "engine_temp": f"{engine_temp} C",
        },
    }

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/overview")


@app.get("/{page_path:path}")
def render_page(request: Request, page_path: str):
    endpoint = f"/{page_path}" if page_path else "/overview"
    page = PAGE_DATA.get(endpoint)

    if page is None:
        return templates.TemplateResponse(
            "not_found.html",
            {
                "request": request,
                "nav_items": NAV_ITEMS,
                "active_path": endpoint,
                "title": "Not Found",
                "page": {
                    "title": "Not Found",
                    "subtitle": "That MBIL station does not exist.",
                },
                **DEMO_CONTEXT,
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        page["template"],
        {
            "request": request,
            "nav_items": NAV_ITEMS,
            "active_path": endpoint,
            "page": page,
            **DEMO_CONTEXT,
        },
    )
