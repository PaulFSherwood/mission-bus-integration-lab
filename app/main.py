from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse

app = FastAPI(title="MBIL")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

NAV_ITEMS = [
    {"label": "Overview", "endpoint": "/overview", "icon": "dashboard"},
    {"label": "Bus Monitor", "endpoint": "/bus-monitor", "icon": "bus"},
    {"label": "Mission Computers", "endpoint": "/mission-computers", "icon": "computer"},
    {"label": "Sensors", "endpoint": "/sensors", "icon": "sensor"},
    {"label": "Faults", "endpoint": "/faults", "icon": "fault"},
]

PAGE_DATA = {
    "/overview": {
        "title": "System Overview",
        "subtitle": "Mission bus lab status, simulated aircraft state, and system health.",
        "template": "dashboard.html",
    },
    "/bus-monitor": {
        "title": "Bus Monitor",
        "subtitle": "Simulated message traffic, bus timing, and message health.",
        "template": "bus_monitor.html",
    },
    "/mission-computers": {
        "title": "Mission Computers",
        "subtitle": "MC1 / MC2 role, heartbeat, failover, and message processing state.",
        "template": "mission_computers.html",
    },
    "/sensors": {
        "title": "Sensors",
        "subtitle": "Air data, INS, engine, and fuel sensor output.",
        "template": "sensors.html",
    },
    "/faults": {
        "title": "Fault Injection",
        "subtitle": "Inject simulated failures into sensors, buses, messages, and mission computers.",
        "template": "faults.html",
    },
}

DEMO_CONTEXT = {
    "sim_tick": "0001234",
    "sim_state": "RUNNING",
    "tick_rate": "10 Hz",
    "mc_online": 2,
    "bus_healthy": 2,
    "sensor_online": 4,
    "display_online": 2,
    "active_faults": 0,
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
