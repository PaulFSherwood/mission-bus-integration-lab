from time import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.sim.runtime import SimulatorRuntime
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from app.sim.exchange_reader import read_adapter_status, read_exchange_latest

app = FastAPI(title="MBIL")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

sim_runtime = SimulatorRuntime("data/routes/kpns_kabq_points.txt")

NAV_ITEMS = [
    {"label": "Cockpit", "endpoint": "/overview", "icon": "cockpit"},
    {"label": "TAWS / Weather", "endpoint": "/taws-weather", "icon": "display"},
    {"label": "Mission Computers", "endpoint": "/mission-computers", "icon": "computer"},
    {"label": "Bus Messages", "endpoint": "/bus-messages", "icon": "bus"},
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
    "/taws-weather": {
        "title": "TAWS / Weather",
        "subtitle": "Simulation-only terrain awareness and local weather radar.",
        "template": "taws_weather.html"
    },
    "/mission-computers": {
        "title": "Mission Computers",
        "subtitle": "MC1 / MC2 role, heartbeat, failover, and message processing state.",
        "template": "mission_computers.html",
    },
    "/bus-messages": {
        "title": "Bus Messages",
        "subtitle": "Live 1553-style bus monitor traffic.",
        "template": "bus_messages.html",
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

class FaultValue(BaseModel):
    enabled: bool

@app.get("/api/faults")
def api_faults():
    return sim_runtime.bus.fault_status()

@app.post("/api/faults/rt/{rt_name}/failed")
def api_set_rt_failed(rt_name: str, value: FaultValue):
    sim_runtime.bus.set_rt_failed(rt_name, value.enabled)

    return {
        "ok": True,
        "rt": rt_name,
        "failed": value.enabled,
        "faults": sim_runtime.bus.fault_status(),
    }

@app.post("/api/faults/rt/{rt_name}/stale")
def api_set_rt_stale(rt_name: str, value: FaultValue):
    sim_runtime.bus.set_rt_stale(rt_name, value.enabled)

    return {
        "ok": True,
        "rt": rt_name,
        "stale": value.enabled,
        "faults": sim_runtime.bus.fault_status(),
    }

@app.post("/api/faults/clear")
def api_clear_faults():
    sim_runtime.bus.clear_faults()

    return {
        "ok": True,
        "faults": sim_runtime.bus.fault_status(),
    }

@app.get("/api/state")
def api_state():
    return sim_runtime.to_api_state()

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/overview")

@app.get("/api/messages")
def api_messages():
    return {
        "messages": sim_runtime.bus.recent_messages()
    }


@app.get("/api/adapter/status")
def api_adapter_status():
    return read_adapter_status()

@app.get("/api/exchange/latest")
def api_exchange_latest():
    return read_exchange_latest()

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
