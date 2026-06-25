// app/static/js/taws_weather.js
// Unified MBIL display renderer.
// One public API draws any canvas tagged with data-mbil-display.
// Supported modes now: weather-radar, taws-weather.
// Simulation-only. Not for real aviation use.

(function () {
    const DEFAULT_RANGE_NM = 40;
    const TERRAIN_GRID_STEP_PX = 8;

    const state = {
        storms: [],
        initialized: false,
        lastStormUpdateMs: 0,
        pollHandle: null,
    };

    function number(value, fallback = 0) {
        if (typeof value === "number") return value;
        if (value === null || value === undefined) return fallback;
        const parsed = Number(String(value).replace(/[^0-9.+-]/g, ""));
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function radians(deg) {
        return deg * Math.PI / 180.0;
    }

    function aircraftFromData(data) {
        const aircraft = data?.aircraft || {};
        return {
            lat: number(aircraft.lat, 30.5),
            lon: number(aircraft.lon, -87.2),
            altitudeFt: number(aircraft.altitude, 4000),
            headingDeg: number(aircraft.heading, 0),
            airspeedKts: number(aircraft.airspeed, 220),
        };
    }

    function getCanvasSize(canvas) {
        const rect = canvas.getBoundingClientRect();

        if (rect.width < 10 || rect.height < 10) {
            return null;
        }

        canvas.width = Math.floor(rect.width);
        canvas.height = Math.floor(rect.height);

        return {
            width: canvas.width,
            height: canvas.height,
            centerX: canvas.width / 2,
            centerY: canvas.height / 2,
        };
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function layerEnabled(name) {
        const button = document.querySelector(`[data-display-layer-button="${name}"]`);
        return !button || button.classList.contains("active");
    }

    function setupLayerButtons() {
        document.querySelectorAll("[data-display-layer-button]").forEach((button) => {
            if (button.dataset.ready === "1") return;

            const name = button.dataset.displayLayerButton;
            const key = "mbil_display_layer_" + name;
            const saved = localStorage.getItem(key);

            if (saved !== null) {
                button.classList.toggle("active", saved === "true");
            }

            button.addEventListener("click", () => {
                const enabled = !button.classList.contains("active");
                button.classList.toggle("active", enabled);
                localStorage.setItem(key, enabled ? "true" : "false");
            });

            button.dataset.ready = "1";
        });
    }

    function seedStorms() {
        state.storms = [
            { id: "WX01", eastNm: 15, northNm: 10, radiusNm: 12, intensity: 0.55, driftEast: 0.015, driftNorth: -0.006, lightning: true },
            { id: "WX02", eastNm: -20, northNm: -8, radiusNm: 9, intensity: 0.85, driftEast: 0.010, driftNorth: 0.008, lightning: true },
            { id: "WX03", eastNm: 5, northNm: -24, radiusNm: 7, intensity: 0.35, driftEast: -0.006, driftNorth: 0.012, lightning: false },
        ];
        state.initialized = true;
        state.lastStormUpdateMs = performance.now();
    }

    function updateStorms() {
        if (!state.initialized) seedStorms();

        const now = performance.now();
        const dt = Math.min(2.0, Math.max(0.0, (now - state.lastStormUpdateMs) / 1000.0));
        state.lastStormUpdateMs = now;

        state.storms.forEach((storm) => {
            storm.eastNm += storm.driftEast * dt;
            storm.northNm += storm.driftNorth * dt;

            if (storm.eastNm > 50) storm.eastNm = -50;
            if (storm.eastNm < -50) storm.eastNm = 50;
            if (storm.northNm > 50) storm.northNm = -50;
            if (storm.northNm < -50) storm.northNm = 50;
        });
    }

    function weatherColor(intensity) {
        if (intensity >= 0.90) return "rgba(190, 50, 255, 0.82)";
        if (intensity >= 0.72) return "rgba(255, 45, 40, 0.78)";
        if (intensity >= 0.48) return "rgba(255, 220, 50, 0.76)";
        return "rgba(0, 190, 80, 0.70)";
    }

    function weatherCellsFromData(data) {
        const externalCells = data?.weather_radar?.cells;

        if (Array.isArray(externalCells) && externalCells.length > 0) {
            return externalCells.map((cell, index) => ({
                id: cell.id || `WX${String(index + 1).padStart(2, "0")}`,
                eastNm: number(cell.east_nm, number(cell.eastNm, 0)),
                northNm: number(cell.north_nm, number(cell.northNm, 0)),
                radiusNm: number(cell.radius_nm, number(cell.radiusNm, 5)),
                intensity: number(cell.intensity, 0.25),
                lightning: Boolean(cell.lightning),
            }));
        }

        updateStorms();
        return state.storms;
    }

    function drawStorm(ctx, x, y, radiusPx, intensity, lightning, id) {
        [
            { scale: 1.00, intensity: intensity * 0.45 },
            { scale: 0.66, intensity: intensity * 0.70 },
            { scale: 0.34, intensity: intensity },
        ].forEach((level) => {
            ctx.beginPath();
            ctx.fillStyle = weatherColor(level.intensity);
            ctx.arc(x, y, radiusPx * level.scale, 0, Math.PI * 2);
            ctx.fill();
        });

        if (lightning && intensity > 0.50) {
            ctx.save();
            ctx.strokeStyle = "rgba(255, 255, 110, 0.95)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(x - 5, y - 12);
            ctx.lineTo(x + 2, y - 2);
            ctx.lineTo(x - 2, y - 2);
            ctx.lineTo(x + 6, y + 12);
            ctx.stroke();
            ctx.restore();
        }

        ctx.fillStyle = "rgba(255,255,255,0.85)";
        ctx.font = "bold 10px monospace";
        ctx.fillText(id, x + radiusPx * 0.35, y - radiusPx * 0.35);
    }

    function terrainFt(lat, lon) {
        const westRise = Math.max(0, (-lon - 98.0) * 420.0);
        const wave1 = Math.sin(lat * 0.85) * 700.0;
        const wave2 = Math.cos(lon * 0.65) * 520.0;
        const ridge = Math.max(0, Math.sin((lat + lon) * 2.1)) * 1800.0;
        return Math.max(0, 250.0 + westRise + wave1 + wave2 + ridge);
    }

    function terrainColor(elevationFt, altitudeFt) {
        const clearance = altitudeFt - elevationFt;
        if (clearance <= 300) return "rgba(255, 40, 40, 0.85)";
        if (clearance <= 1000) return "rgba(255, 215, 50, 0.80)";
        if (clearance <= 2500) return "rgba(30, 175, 65, 0.60)";
        return "rgba(0, 70, 35, 0.35)";
    }

    function alertFromClearance(clearanceFt) {
        if (clearanceFt <= 300) return "TERRAIN PULL UP";
        if (clearanceFt <= 1000) return "CAUTION TERRAIN";
        return "CLEAR";
    }

    function latLonFromOffset(aircraft, eastNm, northNm) {
        const avgLatRad = radians(aircraft.lat);
        return {
            lat: aircraft.lat + northNm / 60.0,
            lon: aircraft.lon + eastNm / (60.0 * Math.cos(avgLatRad)),
        };
    }

    function projectNorthUp(aircraft, lat, lon, cx, cy, pixelsPerNm) {
        const avgLatRad = radians(aircraft.lat);
        const northNm = (lat - aircraft.lat) * 60.0;
        const eastNm = (lon - aircraft.lon) * 60.0 * Math.cos(avgLatRad);
        return { x: cx + eastNm * pixelsPerNm, y: cy - northNm * pixelsPerNm, eastNm, northNm };
    }

    function projectHeadingUp(relative, aircraft, cx, cy, pixelsPerNm) {
        const h = radians(aircraft.headingDeg);
        const forwardNm = relative.northNm * Math.cos(h) + relative.eastNm * Math.sin(h);
        const rightNm = relative.eastNm * Math.cos(h) - relative.northNm * Math.sin(h);
        return { x: cx + rightNm * pixelsPerNm, y: cy - forwardNm * pixelsPerNm, forwardNm, rightNm };
    }

    function drawGrid(ctx, cx, cy, width, height, pixelsPerNm) {
        ctx.save();
        ctx.strokeStyle = "rgba(120, 180, 220, 0.18)";
        ctx.lineWidth = 1;
        const spacing = 10 * pixelsPerNm;

        for (let x = cx % spacing; x < width; x += spacing) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
        }
        for (let y = cy % spacing; y < height; y += spacing) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
        }

        ctx.strokeStyle = "rgba(160, 240, 180, 0.45)";
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, height); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(0, cy); ctx.lineTo(width, cy); ctx.stroke();

        ctx.fillStyle = "rgba(180, 255, 190, 0.9)";
        ctx.font = "bold 13px monospace";
        ctx.textAlign = "center";
        ctx.fillText("N", cx, 18);
        ctx.restore();
    }

    function drawRangeRings(ctx, cx, cy, radiusPx, options = {}) {
        ctx.save();
        ctx.strokeStyle = options.color || "rgba(180, 255, 190, 0.55)";
        ctx.lineWidth = options.lineWidth || 1.5;

        [0.25, 0.50, 0.75, 1.0].forEach((scale) => {
            ctx.beginPath();
            ctx.arc(cx, cy, radiusPx * scale, 0, Math.PI * 2);
            ctx.stroke();
        });

        ctx.strokeStyle = options.crossColor || "rgba(220, 240, 255, 0.70)";
        ctx.beginPath(); ctx.moveTo(cx - radiusPx, cy); ctx.lineTo(cx + radiusPx, cy); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(cx, cy - radiusPx); ctx.lineTo(cx, cy + radiusPx); ctx.stroke();
        ctx.restore();
    }

    function drawRoute(ctx, data, aircraft, cx, cy, pixelsPerNm) {
        const route = data?.route_points || [];
        if (route.length < 2) return;

        ctx.save();
        ctx.strokeStyle = "rgba(255, 80, 255, 0.95)";
        ctx.lineWidth = 2;
        ctx.beginPath();

        route.forEach((wp, index) => {
            const p = projectNorthUp(aircraft, wp.lat, wp.lon, cx, cy, pixelsPerNm);
            if (index === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
        });
        ctx.stroke();

        route.forEach((wp) => {
            const p = projectNorthUp(aircraft, wp.lat, wp.lon, cx, cy, pixelsPerNm);
            if (p.x < -20 || p.x > ctx.canvas.width + 20 || p.y < -20 || p.y > ctx.canvas.height + 20) return;
            ctx.fillStyle = "rgba(255, 80, 255, 0.95)";
            ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 11px monospace";
            ctx.fillText(wp.id || wp.ident || "WP", p.x + 7, p.y - 6);
        });
        ctx.restore();
    }

    function drawOwnship(ctx, cx, cy, headingDeg, options = {}) {
        ctx.save();
        ctx.translate(cx, cy);
        if (!options.headingUp) ctx.rotate(radians(headingDeg));

        ctx.fillStyle = options.color || "#ffffff";
        ctx.strokeStyle = options.stroke || "rgba(0, 0, 0, 0.85)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, -17);
        ctx.lineTo(8, 8);
        ctx.lineTo(0, 3);
        ctx.lineTo(-8, 8);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.restore();
    }

    function drawWeatherNorthUp(ctx, data, aircraft, cx, cy, pixelsPerNm) {
        const cells = weatherCellsFromData(data);
        let severe = number(data?.weather_radar?.severe_count, 0);
        let lightning = number(data?.weather_radar?.lightning_count, 0);

        if (!data?.weather_radar?.cells) {
            severe = 0;
            lightning = 0;
        }

        cells.forEach((storm) => {
            if (!data?.weather_radar?.cells) {
                if (storm.intensity >= 0.90) severe += 1;
                if (storm.lightning && storm.intensity > 0.50) lightning += 1;
            }
            drawStorm(ctx, cx + storm.eastNm * pixelsPerNm, cy - storm.northNm * pixelsPerNm, storm.radiusNm * pixelsPerNm, storm.intensity, storm.lightning, storm.id);
        });

        setText("wx-cell-count", String(number(data?.weather_radar?.cell_count, cells.length)));
        setText("wx-severe-count", String(severe));
        setText("wx-lightning-count", String(lightning));
        setText("wx-motion", data?.weather_radar?.motion || "LOCAL SIM");
    }

    function drawWeatherHeadingUp(ctx, data, aircraft, cx, cy, pixelsPerNm, radiusPx) {
        const cells = weatherCellsFromData(data);
        cells.forEach((storm) => {
            const p = projectHeadingUp({ eastNm: storm.eastNm, northNm: storm.northNm }, aircraft, cx, cy, pixelsPerNm);
            const distPx = Math.hypot(p.x - cx, p.y - cy);
            if (distPx > radiusPx + storm.radiusNm * pixelsPerNm) return;
            drawStorm(ctx, p.x, p.y, storm.radiusNm * pixelsPerNm, storm.intensity, storm.lightning, storm.id);
        });
    }

    function drawTerrain(ctx, aircraft, width, height, cx, cy, pixelsPerNm, rangeNm) {
        let worstClearance = 999999;
        const terrainUnder = terrainFt(aircraft.lat, aircraft.lon);

        for (let y = 0; y < height; y += TERRAIN_GRID_STEP_PX) {
            for (let x = 0; x < width; x += TERRAIN_GRID_STEP_PX) {
                const eastNm = (x - cx) / pixelsPerNm;
                const northNm = (cy - y) / pixelsPerNm;
                if (Math.hypot(eastNm, northNm) > rangeNm) continue;

                const ll = latLonFromOffset(aircraft, eastNm, northNm);
                const elev = terrainFt(ll.lat, ll.lon);
                const clearance = aircraft.altitudeFt - elev;
                worstClearance = Math.min(worstClearance, clearance);

                ctx.fillStyle = terrainColor(elev, aircraft.altitudeFt);
                ctx.fillRect(x, y, TERRAIN_GRID_STEP_PX + 1, TERRAIN_GRID_STEP_PX + 1);
            }
        }

        return { terrainUnder, worstClearance };
    }

    function updateTawsStatus(data, aircraft, terrainInfo) {
        const busTaws = data?.taws || {};
        const terrainUnder = Math.round(number(busTaws.terrain_under_ft, terrainInfo.terrainUnder));
        const clearance = Math.round(number(busTaws.clearance_ft, aircraft.altitudeFt - terrainInfo.terrainUnder));
        const worstClearance = number(busTaws.worst_clearance_ft, terrainInfo.worstClearance);
        const alertState = busTaws.alert_state || alertFromClearance(Math.min(clearance, worstClearance));

        const box = document.getElementById("taws-alert-box");
        if (box) {
            box.classList.remove("caution", "pull-up");
            if (alertState === "CAUTION TERRAIN") box.classList.add("caution");
            if (alertState === "TERRAIN PULL UP") box.classList.add("pull-up");
        }

        setText("taws-alert-state", alertState);
        setText("taws-side-alert", alertState);
        setText("taws-terrain-under", terrainUnder.toLocaleString() + " FT");
        setText("taws-side-terrain", terrainUnder.toLocaleString() + " FT");
        setText("taws-clearance", clearance.toLocaleString() + " FT");
        setText("taws-side-clearance", clearance.toLocaleString() + " FT");
        setText("taws-worst-clearance", Math.round(worstClearance).toLocaleString() + " FT");
        setText("taws-side-mode", busTaws.mode || "SIM ONLY");
        setText("taws-source", busTaws.source || "LOCAL DISPLAY FALLBACK");
    }

    function renderWeatherRadar(canvas, data, ctx, size, aircraft, rangeNm) {
        const radiusPx = Math.min(size.width, size.height) * 0.42;
        const pixelsPerNm = radiusPx / rangeNm;

        ctx.fillStyle = "#02070b";
        ctx.fillRect(0, 0, size.width, size.height);

        ctx.save();
        ctx.beginPath();
        ctx.arc(size.centerX, size.centerY, radiusPx, 0, Math.PI * 2);
        ctx.clip();

        const sweep = ctx.createRadialGradient(size.centerX, size.centerY, 0, size.centerX, size.centerY, radiusPx);
        sweep.addColorStop(0, "rgba(20, 90, 40, 0.24)");
        sweep.addColorStop(1, "rgba(0, 0, 0, 0.0)");
        ctx.fillStyle = sweep;
        ctx.fillRect(size.centerX - radiusPx, size.centerY - radiusPx, radiusPx * 2, radiusPx * 2);

        drawWeatherHeadingUp(ctx, data, aircraft, size.centerX, size.centerY, pixelsPerNm, radiusPx);
        ctx.restore();

        drawRangeRings(ctx, size.centerX, size.centerY, radiusPx);
        drawOwnship(ctx, size.centerX, size.centerY, 0, { headingUp: true, color: "#ff66ff", stroke: "#ffb3ff" });
        setText("cockpit-radar-brg", String(Math.round(aircraft.headingDeg)).padStart(3, "0") + "°");
    }

    function renderTawsWeather(canvas, data, ctx, size, aircraft, rangeNm) {
        const pixelsPerNm = Math.min(size.width, size.height) / (rangeNm * 2.1);
        const ringRadiusPx = rangeNm * pixelsPerNm;

        const bg = ctx.createLinearGradient(0, 0, 0, size.height);
        bg.addColorStop(0, "#07121a");
        bg.addColorStop(1, "#020609");
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, size.width, size.height);

        let terrainInfo = {
            terrainUnder: terrainFt(aircraft.lat, aircraft.lon),
            worstClearance: aircraft.altitudeFt - terrainFt(aircraft.lat, aircraft.lon),
        };

        if (layerEnabled("terrain")) {
            terrainInfo = drawTerrain(ctx, aircraft, size.width, size.height, size.centerX, size.centerY, pixelsPerNm, rangeNm);
        }

        drawGrid(ctx, size.centerX, size.centerY, size.width, size.height, pixelsPerNm);
        drawRangeRings(ctx, size.centerX, size.centerY, ringRadiusPx);

        if (layerEnabled("route")) drawRoute(ctx, data, aircraft, size.centerX, size.centerY, pixelsPerNm);
        if (layerEnabled("weather")) drawWeatherNorthUp(ctx, data, aircraft, size.centerX, size.centerY, pixelsPerNm);

        drawOwnship(ctx, size.centerX, size.centerY, aircraft.headingDeg);
        updateTawsStatus(data, aircraft, terrainInfo);
    }

    const renderers = {
        "weather-radar": renderWeatherRadar,
        "taws-weather": renderTawsWeather,
    };

    function draw(canvas, data) {
        if (!canvas || !data?.aircraft) return;

        setupLayerButtons();

        const size = getCanvasSize(canvas);
        if (!size) return;

        const mode = canvas.dataset.mbilDisplay;
        const renderer = renderers[mode];
        if (!renderer) return;

        const ctx = canvas.getContext("2d");
        const aircraft = aircraftFromData(data);
        const rangeNm = number(canvas.dataset.displayRangeNm, DEFAULT_RANGE_NM);

        renderer(canvas, data, ctx, size, aircraft, rangeNm);
    }

    function updateAll(data) {
        document.querySelectorAll("canvas[data-mbil-display]").forEach((canvas) => draw(canvas, data));
    }

    async function updateFromApi() {
        if (!document.querySelector("canvas[data-mbil-display]")) return;

        try {
            const response = await fetch("/api/state");
            const data = await response.json();
            updateAll(data);
        } catch (error) {
            console.error("MBIL display update failed:", error);
        }
    }

    function startPolling() {
        if (state.pollHandle) return;
        state.pollHandle = setInterval(updateFromApi, 500);
        updateFromApi();
    }

    window.MbilDisplays = {
        draw,
        updateAll,
        updateFromApi,
        startPolling,
        get storms() { return state.storms; },
    };

    // Compatibility wrappers so old cockpit.js calls do not break while refactoring.
    window.drawTawsWeatherPage = function (data) {
        const canvas = document.getElementById("taws-weather-canvas");
        if (canvas) draw(canvas, data);
    };

    window.drawCockpitWeatherRadar = function (data) {
        const canvas = document.getElementById("cockpit-weather-radar-canvas");
        if (canvas) draw(canvas, data);
    };

    startPolling();
})();
