// app/static/js/taws_weather.js
// 
// Local simulation-only TAWS / Weather display.
// Uses /api/state data passed from cockpit.js into drawTawsWeatherPage(data).
// No live weather. No real aviation use.

const tawsWeatherState = {
  stoms: [],
  initialized: false,
  lastStormSeedTime: 0,
};

const TAWS_RANGE_NM = 40;
const TERRAIN_GRID_STEP_PX = 8;

function tawsNumber(value, fallback = 0) {
  if (typeof value === "number") {
    return value;
  }
  if (value == null || value === undefined) {
    return fallback;
  }

  const parsed = Number(String(value).replace(/[^0-9.+-]/g, ""));

  if (Number.isNaN(parsed)) {
    return fallback;
  }

  return parsed;
}

function tawsClamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function tawsDegreesToRadians(deg) {
  return deg * Math.PI / 180.0;
}

function tawsGetAircraft(data) {
  const aircraft = data?.aircraft || {};

  return {
    lat: tawsNumber(aircraft.lat, 30.5),
    lon: tawsNumber(aircraft.lon, -87.2),
    altitudeFt: tawsNumber(aircraft.altitude, 4000),
    headingDeg: tawsNumber(aircraft.heading, 0),
    airspeedKts: tawsNumber(aircraft.airspeed, 220),
  };
}

function tawsSyntheticTerrainFt(lat, lon) {
  // Synthetic local terrain model for the MBIL route area.
  // This gives flat Gulf-region terrain in the east and rising terrain toward NM.
  const westRise = Math.max(0, (-lon - 98.0) * 420.);
  const wave1 = Math.sin(lat * 0.85) * 700.0;
  const wave2 = Math.cos(lon * 0.65) * 520.0;
  const ridge = Math.max(0, Math.sin((lat + lon) * 2.1)) * 1800.0;

  return Math.max(0, 250.0 + westRise + wave1 + wave2 + ridge);
}

function tawsTerrainColor(terrainFt, aircraftAltFt) {
  const clearance = aircraftAltFt - terrainFt;
  
  if (clearance <= 300) {
    return "rgba(255, 40, 40, 0.85)";
  }
  
  if (clearance <= 1000) {
    return "rgba(255, 215, 50, 0.80)";
  }
  
  if (clearance <= 2500) {
    return "rgba(30, 175, 65, 0.60)";
  }
  
  return "rgba(0, 70, 35, 0.35)";
}

function tawsAlertFromClearance(clearanceFt) {
  if (clearanceFt <= 300) {
    return "TERRAIN PULL UP";
  }
  if (clearanceFt <= 1000) {
    return "CAUTION TERRAIN";
  }

  return "CLEAR";
}

function tawsSetText(id, value) {
  const el = document.getElementById(id);

  if (el) {
    el.textContent = value;
  }
}

function tawsSetAlertState(alertState) {
  const box = document.getElementById("taws-alert-box");
  const main = document.getElementById("taws-alert-state");
  const side = document.getElementById("taws-side-alert");

  if (main) {
    main.textContent = alertState;
  }

  if (side) {
    side.textContent = alertState;
  }

  if (!box) {
    return;
  }

  box.classList.remove("caution", "pull-up");

  if (alertState === "CAUTION_TERRAIN") {
    box.classList.add("caution");
  }

  if (alertState === "TERRAIN PULL UP") {
    box.classList.add("pull-up");
  }
}

function tawsProjectRelative(aircraft, lat, lon, centerX, centerY, pixelsPerNm) {
  const avgLatRad = tawsDegreesToRadians(aircraft.lat);
  const northNm = (lat - aircraft.lat) * 60.0;
  const eastNm = (lon - aircraft.lon) * 60.0 * Math.cos(avgLatRad);

  return {
    x: centerX + eastNm * pixelsPerNm,
    y: centerY - northNm * pixelsPerNm,
    eastNm,
    northNm,
  };
}

function cockpitRadarProjectHeadingUp(storm, aircraft, centerX, centerY, pixelsPerNm) {
  const headingRad = tawsDegreesToRadians(aircraft.headingDeg);

  const eastNm = storm.eastNm;
  const northNm = storm.northNm;

  const forwardNm = northNm * Math.cos(headingRad) + eastNm * Math.sin(headingRad);
  const rightNm = eastNm * Math.cos(headingRad) - northNm * Math.sin(headingRad);

  return {
    x: centerX + rightNm * pixelsPerNm,
    y: centerY - forwardNm * pixelsPerNm,
    forwardNm,
    rightNm,
  };
}

function drawCockpitRadarRings(ctx, centerX, centerY, radiusPx) {
  ctx.save();

  ctx.strokeStyle = "rgba(109, 255, 125, 0.72)";
  ctx.lineWidth = 1.5;

  [0.25, 0.50, 0.75, 1.0].forEach((scale) => {
    ctx.beginPath();
    ctx.arc(centerX, centerY, radiusPx * scale, 0, Math.PI * 2);
    ctx.stroke();
  });

  ctx.beginPath();
  ctx.moveTo(centerX - radiusPx, centerY);
  ctx.lineTo(centerX + radiusPx, centerY);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(centerX, centerY - radiusPx);
  ctx.lineTo(centerX, centerY + radiusPx);
  ctx.stroke();

  ctx.restore();
}

function drawCockpitRadarStorm(ctx, storm, aircraft, centerX, centerY, pixelsPerNm, radarRadiusPx) {
  const p = cockpitRadarProjectHeadingUp(storm, aircraft, centerX, centerY, pixelsPerNm);
  const distPx = Math.sqrt((p.x - centerX) ** 2 + (p.y - centerY) ** 2);

  if (distPx > radarRadiusPx + storm.radiusNm * pixelsPerNm) {
    return;
  }

  const radiusPx = storm.radiusNm * pixelsPerNm;

  const levels = [
    { scale: 1.00, intensity: storm.intensity * 0.45 },
    { scale: 0.66, intensity: storm.intensity * 0.70 },
    { scale: 0.34, intensity: storm.intensity },
  ];

  levels.forEach((level) => {
    ctx.beginPath();
    ctx.fillStyle = tawsWeatherColor(level.intensity);
    ctx.arc(p.x, p.y, radiusPx * level.scale, 0, Math.PI * 2);
    ctx.fill();
  });

  if (storm.lightning && storm.intensity > 0.50) {
    ctx.save();
    ctx.strokeStyle = "rgba(255, 255, 110, 0.95)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(p.x - 5, p.y - 12);
    ctx.lineTo(p.x + 2, p.y - 2);
    ctx.lineTo(p.x - 2, p.y - 2);
    ctx.lineTo(p.x + 6, p.y + 12);
    ctx.stroke();
    ctx.restore();
  }

  ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
  ctx.font = "bold 10px monospace";
  ctx.fillText(storm.id, p.x + radiusPx * 0.35, p.y - radiusPx * 0.35);
}

function drawCockpitRadarOwnship(ctx, centerX, centerY) {
  ctx.save();

  ctx.fillStyle = "#ff66ff";
  ctx.strokeStyle = "#ffb3ff";
  ctx.lineWidth = 1.5;

  ctx.beginPath();
  ctx.moveTo(centerX, centerY - 7);
  ctx.lineTo(centerX + 7, centerY + 5);
  ctx.lineTo(centerX, centerY + 2);
  ctx.lineTo(centerX - 7, centerY + 5);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  ctx.restore();
}

function drawCockpitWeatherRadar(data) {

    const canvas = document.getElementById("cockpit-weather-radar-canvas");

    if (!canvas || !data || !data.aircraft) {

        return;

    }

    const rect = canvas.getBoundingClientRect();

    if (rect.width < 10 || rect.height < 10) {

        return;

    }

    canvas.width = Math.floor(rect.width);

    canvas.height = Math.floor(rect.height);

    const ctx = canvas.getContext("2d");

    const width = canvas.width;

    const height = canvas.height;

    const centerX = width / 2;

    const centerY = height / 2;

    const radarRadiusPx = Math.min(width, height) * 0.42;

    const pixelsPerNm = radarRadiusPx / 40.0;

    const aircraft = tawsGetAircraft(data);

    if (!tawsWeatherState.initialized) {

        tawsSeedStorms(aircraft);

    }

    tawsUpdateStormMotion();

    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = "#02070b";

    ctx.fillRect(0, 0, width, height);

    ctx.save();

    ctx.beginPath();

    ctx.arc(centerX, centerY, radarRadiusPx, 0, Math.PI * 2);

    ctx.clip();

    const sweep = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radarRadiusPx);

    sweep.addColorStop(0, "rgba(20, 90, 40, 0.24)");

    sweep.addColorStop(1, "rgba(0, 0, 0, 0.0)");

    ctx.fillStyle = sweep;

    ctx.fillRect(centerX - radarRadiusPx, centerY - radarRadiusPx, radarRadiusPx * 2, radarRadiusPx * 2);

    tawsWeatherState.storms.forEach((storm) => {

        drawCockpitRadarStorm(ctx, storm, aircraft, centerX, centerY, pixelsPerNm, radarRadiusPx);

    });

    ctx.restore();

    drawCockpitRadarRings(ctx, centerX, centerY, radarRadiusPx);

    drawCockpitRadarOwnship(ctx, centerX, centerY);

    tawsSetText("cockpit-radar-brg", String(Math.round(aircraft.headingDeg)).padStart(3, "0") + "°");

}

window.drawCockpitWeatherRadar = drawCockpitWeatherRadar;

function tawsNmOffsetToLatLon(aircraft, eastNm, northNm) {
  const avgLatRad = tawsDegreesToRadians(aircraft.lat);
  const lat = aircraft.lat + northNm / 60.0;
  const lon = aircraft.lon + eastNm / (60.0 * Math.cos(avgLatRad));
  
  return { lat, lon };
}

function tawsDrawBackground(ctx, width, height) {
  const grd = ctx.createLinearGradient(0, 0, 0, height);
  grd.addColorStop(0, "#07121a");
  grd.addColorStop(1, "#020609");

  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, width, height);
}

function tawsDrawGrid(ctx, centerX, centerY, width, height, pixelsPerNm) {
  ctx.save();

  ctx.strokeStyle = "rgba(120, 180, 220, 0.18)";
  ctx.lineWidth = 1;

  const spacingNm = 10;
  const spacingPx = spacingNm * pixelsPerNm;

  for (let x = centerX % spacingPx; x < width; x += spacingPx) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  for (let y = centerY % spacingPx; y < height; y += spacingPx) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  ctx.strokeStyle = "rgba(160, 240, 180, 0.45)";
  ctx.lineWidth = 1.5;

  ctx.beginPath();
  ctx.moveTo(centerX, 0);
  ctx.lineTo(centerX, height);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(0, centerY);
  ctx.lineTo(width, centerY);
  ctx.stroke();

  ctx.fillStyle = "rgba(180, 255, 190, 0.9)";
  ctx.font = "bold 13px monospace";
  ctx.textAlign = "center";
  ctx.fillText("N", centerX, 18);

  ctx.restore();
}

function tawsDrawRangeRings(ctx, centerX, centerY, pixelsPerNm) {
  ctx.save();

  ctx.strokeStyle = "rgba(180, 255, 190, 0.45)";
  ctx.lineWidth = 1.5;

  [10, 20, 40].forEach((nm) => {
    ctx.beginPath();
    ctx.arc(centerX, centerY, nm * pixelsPerNm, 0, Math.PI * 2);
    ctx.stroke();
  });

  ctx.fillStyle = "rgba(220, 255, 220, 0.75)";
  ctx.font = "11px monospace";
  ctx.fillText("10", centerX + 10 * pixelsPerNm + 4, centerY - 4);
  ctx.fillText("20", centerX + 20 * pixelsPerNm + 4, centerY - 4);
  ctx.fillText("40", centerX + 40 * pixelsPerNm + 4, centerY - 4);

  ctx.restore();
}

function tawsDrawTerrain(ctx, aircraft, width, height, centerX, centerY, pixelsPerNm) {
  let worstClearance = 999999;
  let terrainUnderAircraft = tawsSyntheticTerrainFt(aircraft.lat, aircraft.lon);
  
  for (let y = 0; y < height; y += TERRAIN_GRID_STEP_PX) {
    for (let x = 0; x < width; x += TERRAIN_GRID_STEP_PX) {
      const eastNm = (x - centerX) / pixelsPerNm;
      const northNm = (centerY - y) / pixelsPerNm;
      
      const distNm = Math.sqrt(eastNm * eastNm + northNm * northNm);
      
      if (distNm > TAWS_RANGE_NM) {
        continue;
      }
      
      const point = tawsNmOffsetToLatLon(aircraft, eastNm, northNm);
      const terrainFt = tawsSyntheticTerrainFt(point.lat, point.lon);
      const clearance = aircraft.altitudeFt - terrainFt;
      
      worstClearance = Math.min(worstClearance, clearance);
      
      ctx.fillStyle = tawsTerrainColor(terrainFt, aircraft.altitudeFt);
      ctx.fillRect(x, y, TERRAIN_GRID_STEP_PX + 1, TERRAIN_GRID_STEP_PX + 1);
    }
  }
  
  return {
  terrainUnderAircraft,
  worstClearance,
  };
}

function tawsSeedStorms(aircraft) {
  tawsWeatherState.storms = [
    {
      id: "WX01",
      eastNm: 15,
      northNm: 10,
      radiusNm: 12,
      intensity: 0.55,
      driftEastNmPerSec: 0.015,
      driftNorthNmPerSec: -0.006,
      lightning: true,
    },
    {
      id: "WX02",
      eastNm: -20,
      northNm: -8,
      radiusNm: 9,
      intensity: 0.85,
      driftEastNmPerSec: 0.010,
      driftNorthNmPerSec: 0.008,
      lightning: true,
    },
    {
      id: "WX03",
      eastNm: 5,
      northNm: -24,
      radiusNm: 7,
      intensity: 0.35,
      driftEastNmPerSec: -0.006,
      driftNorthNmPerSec: 0.012,
      lightning: false,
    },
  ];
  
  tawsWeatherState.initialized = true;
  tawsWeatherState.lastStormSeedTime = performance.now();
}

function tawsWeatherColor(intensity) {
  if (intensity >= 0.90) {
    return "rgba(190, 50, 255, 0.82)";
  }
  
  if (intensity >= 0.72) {
    return "rgba(255, 45, 40, 0.78)";
  }
  
  if (intensity >= 0.48) {
    return "rgba(255, 220, 50, 0.76)";
  }
  
  return "rgba(0, 190, 80, 0.70)";
}

function tawsDrawStormCell(ctx, storm, centerX, centerY, pixelsPerNm) {
  const x = centerX + storm.eastNm * pixelsPerNm;
  const y = centerY - storm.northNm * pixelsPerNm;
  const radiusPx = storm.radiusNm * pixelsPerNm;
  
  const coreLevels = [
    { scale: 1.00, intensity: storm.intensity * 0.45 },
    { scale: 0.68, intensity: storm.intensity * 0.70 },
    { scale: 0.38, intensity: storm.intensity },
  ];
  
  coreLevels.forEach((level) => {
    ctx.beginPath();
    ctx.fillStyle = tawsWeatherColor(level.intensity);
    ctx.arc(x, y, radiusPx * level.scale, 0, Math.PI * 2);
    ctx.fill();
  });
  
  ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(x, y, radiusPx, 0, Math.PI * 2);
  ctx.stroke();
  
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.font = "bold 11px monospace";
  ctx.fillText(storm.id, x + radiusPx * 0.4, y - radiusPx * 0.4);
  
  if (storm.lightning && storm.intensity > 0.50) {
    ctx.save();
    ctx.strokeStyle = "rgba(255, 255, 100, 0.95)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x - 5, y - 12);
    ctx.lineTo(x + 2, y - 2);
    ctx.lineTo(x - 2, y - 2);
    ctx.lineTo(x + 6, y + 12);
    ctx.stroke();
    ctx.restore();
  }
}

function tawsUpdateStormMotion() {
  if (!tawsWeatherState.initialized) {
    return;
  }
  
  const now = performance.now();
  const dtSec = Math.min(2.0, Math.max(0.0, (now - tawsWeatherState.lastStormSeedTime) / 1000.0));
  tawsWeatherState.lastStormSeedTime = now;
  
  tawsWeatherState.storms.forEach((storm) => {
    storm.eastNm += storm.driftEastNmPerSec * dtSec;
    storm.northNm += storm.driftNorthNmPerSec * dtSec;
    
    if (storm.eastNm > 50) storm.eastNm = -50;
    if (storm.eastNm < -50) storm.eastNm = 50;
    if (storm.northNm > 50) storm.northNm = -50;
    if (storm.northNm < -50) storm.northNm = 50;
  });
}

function tawsDrawWeather(ctx, aircraft, centerX, centerY, pixelsPerNm) {
  if (!tawsWeatherState.initialized) {
    tawsSeedStorms(aircraft);
  }
  
  tawsUpdateStormMotion();
  
  let severeCount = 0;
  let lightningCount = 0;
  
  tawsWeatherState.storms.forEach((storm) => {
    if (storm.intensity >= 0.90) severeCount += 1;
    if (storm.lightning && storm.intensity > 0.50) lightningCount += 1;
    
    tawsDrawStormCell(ctx, storm, centerX, centerY, pixelsPerNm);
  });
  
  tawsSetText("wx-cell-count", String(tawsWeatherState.storms.length));
  tawsSetText("wx-severe-count", String(severeCount));
  tawsSetText("wx-lightning-count", String(lightningCount));
}

function tawsDrawRoute(ctx, data, aircraft, centerX, centerY, pixelsPerNm) {
  const routePoints = data?.route_points || [];
  
  if (!routePoints || routePoints.length < 2) {
    return;
  }

  ctx.save();
  
  ctx.strokeStyle = "rgba(255, 80, 255, 0.95)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  
  routePoints.forEach((wp, index) => {
    const p = tawsProjectRelative(aircraft, wp.lat, wp.lon, centerX, centerY, pixelsPerNm);
    
    if (index === 0) {
      ctx.moveTo(p.x, p.y);
    } else {
      ctx.lineTo(p.x, p.y);
    }
  });

  ctx.stroke();
  
  routePoints.forEach((wp) => {
    const p = tawsProjectRelative(aircraft, wp.lat, wp.lon, centerX, centerY, pixelsPerNm);
  
    if (p.x < -20 || p.x > ctx.canvas.width + 20 || p.y < -20 || p.y > ctx.canvas.height + 20) {
      return;
    }

    ctx.fillStyle = "rgba(255, 80, 255, 0.95)";
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
    ctx.fill();
    
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 11px monospace";
    ctx.fillText(wp.id || wp.ident || "WP", p.x + 7, p.y - 6);
  });

  ctx.restore();
}

function tawsDrawOwnship(ctx, centerX, centerY, headingDeg) {
  ctx.save();
  
  ctx.translate(centerX, centerY);
  ctx.rotate(tawsDegreesToRadians(headingDeg));
  
  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = "rgba(0, 0, 0, 0.85)";
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

function tawsLoadLayerSetting(name, defaultValue) {
  const raw = localStorage.getItem("mbil_taws_" + name);
  
  if (raw === null) {
    return defaultValue;
  }
  
  return raw === "true";
}

function tawsSaveLayerSetting(name, value) {
  localStorage.setItem("mbil_taws_" + name, value ? "true" : "false");
}

function tawsSetupLayerButtons() {
  const buttons = [
    ["terrain", "taws-layer-terrain"],
    ["weather", "taws-layer-weather"],
    ["route", "taws-layer-route"],
  ];
  
  buttons.forEach(([name, id]) => {
    const button = document.getElementById(id);
    
    if (!button || button.dataset.ready === "1") {
      return;
    }
  
    const enabled = tawsLoadLayerSetting(name, true);
    button.classList.toggle("active", enabled);
    
    button.addEventListener("click", () => {
    const nowEnabled = !button.classList.contains("active");
    button.classList.toggle("active", nowEnabled);
    tawsSaveLayerSetting(name, nowEnabled);
    });
  
    button.dataset.ready = "1";
  });
}

function tawsLayerEnabled(name) {
  const id = {
    terrain: "taws-layer-terrain",
    weather: "taws-layer-weather",
    route: "taws-layer-route",
  }[name];
  
  const button = document.getElementById(id);
  
  if (!button) {
    return true;
  }
  
  return button.classList.contains("active");
}

function drawTawsWeatherPage(data) {
  const canvas = document.getElementById("taws-weather-canvas");
  
  if (!canvas || !data || !data.aircraft) {
    return;
  }
  
  tawsSetupLayerButtons();
  
  const rect = canvas.getBoundingClientRect();
  
  if (rect.width < 10 || rect.height < 10) {
    return;
  }
  
  canvas.width = Math.floor(rect.width);
  canvas.height = Math.floor(rect.height);
  
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const centerX = width / 2;
  const centerY = height / 2;
  const pixelsPerNm = Math.min(width, height) / (TAWS_RANGE_NM * 2.1);
  
  const aircraft = tawsGetAircraft(data);
  
  tawsDrawBackground(ctx, width, height);
  
  let terrainInfo = {
    terrainUnderAircraft: tawsSyntheticTerrainFt(aircraft.lat, aircraft.lon),
    worstClearance: aircraft.altitudeFt - tawsSyntheticTerrainFt(aircraft.lat, aircraft.lon),
  };
  
  if (tawsLayerEnabled("terrain")) {
    terrainInfo = tawsDrawTerrain(ctx, aircraft, width, height, centerX, centerY, pixelsPerNm);
  }
  
  tawsDrawGrid(ctx, centerX, centerY, width, height, pixelsPerNm);
  tawsDrawRangeRings(ctx, centerX, centerY, pixelsPerNm);
  
  if (tawsLayerEnabled("route")) {
    tawsDrawRoute(ctx, data, aircraft, centerX, centerY, pixelsPerNm);
  }
  
  if (tawsLayerEnabled("weather")) {
    tawsDrawWeather(ctx, aircraft, centerX, centerY, pixelsPerNm);
  }
  
  tawsDrawOwnship(ctx, centerX, centerY, aircraft.headingDeg);
  
  const terrainUnder = Math.round(terrainInfo.terrainUnderAircraft);
  const clearance = Math.round(aircraft.altitudeFt - terrainInfo.terrainUnderAircraft);
  const alertState = tawsAlertFromClearance(Math.min(clearance, terrainInfo.worstClearance));
  
  tawsSetAlertState(alertState);
  
  tawsSetText("taws-terrain-under", terrainUnder.toLocaleString() + " FT");
  tawsSetText("taws-clearance", clearance.toLocaleString() + " FT");
  tawsSetText("taws-side-terrain", terrainUnder.toLocaleString() + " FT");
  tawsSetText("taws-side-clearance", clearance.toLocaleString() + " FT");
}

// Make function globally available for cockpit.js guard-call.
window.drawTawsWeatherPage = drawTawsWeatherPage;

async function updateTawsWeatherFromApi() {
  const tawsCanvas = document.getElementById("taws-weather-canvas");
  const cockpitRadarCanvas = document.getElementById("cockpit-weather-radar-canvas");

  if (!tawsCanvas && !cockpitRadarCanvas) {
    return;
  }

  try {
    const response = await fetch("/api/state");
    const data = await response.json();

    if (tawsCanvas) {
      drawTawsWeatherPage(data);
    }
    if (cockpitRadarCanvas) {
      drawCockpitWeatherRadar(data);
    }
  } catch (error) {
    console.error("TAWS / Weather update failed:", error);
  }
}

setInterval(updateTawsWeatherFromApi, 500);
updateTawsWeatherFromApi();
