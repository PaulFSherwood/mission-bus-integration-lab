let movingMapImage = null;
let movingMapImagePath = null;


function cleanWaypointIdent(value, fallback = "WP") {
   if (value === undefined || value === null) return fallback;
   let text = String(value).trim();

   function normalize(raw) {
      let t = String(raw || "").split("\0", 1)[0].trim().toUpperCase();
      t = t.replace(/[^A-Z0-9_-]/g, "");
      if (t.length > 8) return "";
      if (t.length >= 4 && new Set(t).size <= 1) return "";
      return /^[A-Z0-9][A-Z0-9_-]{1,7}$/.test(t) ? t : "";
   }

   let direct = normalize(text);
   if (direct) return direct;

   // X-Plane Web API can expose fixed string buffers as base64-ish text.
   // TE9YTFkAAAAAAAA -> LOXLY plus NUL padding.
   if (/^[A-Za-z0-9+/=]{4,}$/.test(text)) {
      try {
         const padded = text + "=".repeat((4 - text.length % 4) % 4);
         const decoded = atob(padded);
         const ident = normalize(decoded);
         if (ident) return ident;
      } catch (_) {
         // ignore and fall through
      }
   }

   return fallback;
}

function formatDistanceNm(value) {
   const n = Number(value);
   if (!Number.isFinite(n)) return "--";
   if (Math.abs(n) >= 1000) return Math.round(n).toLocaleString();
   if (Math.abs(n) >= 100) return n.toFixed(0);
   if (Math.abs(n) >= 10) return n.toFixed(1);
   return n.toFixed(2);
}

function formatRouteName(value) {
   const text = String(value || "").trim();
   if (!text) return "---";
   return text.length > 24 ? text.slice(0, 21) + "..." : text;
}

function getMovingMapImage(path) {
    if (!path) {
        return null;
    }

    if (movingMapImagePath !== path) {
        movingMapImagePath = path;
        movingMapImage = new Image();
        movingMapImage.src = path;
    }

    if (!movingMapImage.complete || movingMapImage.naturalWidth === 0) {
        return null;
    }

    return movingMapImage;
}

function numberOrZero(value) {
   const n = Number(value);
   return Number.isFinite(n) ? n : 0;
}

function getRoutePoints(data) {
   if (Array.isArray(data.route_points)) {
      return data.route_points;
   }

   if (data.sim && Array.isArray(data.sim.route_points)) {
      return data.sim.route_points;
   }

   if (data.route && Array.isArray(data.route.points)) {
      return data.route.points;
   }

   return [];
}


function getRouteIdent(point) {
   return cleanWaypointIdent(point?.id || point?.ident || point?.name || point?.label || "WP");
}

function getCurrentWaypoint(data) {
   return cleanWaypointIdent(
      data?.nav_display?.current_wp ||
      data?.route?.current_wp ||
      data?.sim?.current_wp ||
      "",
      ""
   );
}

function getNextWaypoint(data) {
   return cleanWaypointIdent(
      data?.nav_display?.next_wp ||
      data?.route?.next_wp ||
      data?.sim?.next_wp ||
      "",
      ""
   );
}

function sameWaypointIdent(a, b) {
   return cleanWaypointIdent(a, "").toUpperCase() === cleanWaypointIdent(b, "").toUpperCase();
}

function findRoutePointIndex(routePoints, ident) {
   if (!ident) return -1;
   return routePoints.findIndex((point) => sameWaypointIdent(getRouteIdent(point), ident));
}

function getActiveLegIndexes(routePoints, data) {
   const currentWp = getCurrentWaypoint(data);
   const nextWp = getNextWaypoint(data);
   const nextIndex = findRoutePointIndex(routePoints, nextWp);
   const currentIndex = findRoutePointIndex(routePoints, currentWp);

   if (currentIndex >= 0 && nextIndex >= 0 && Math.abs(nextIndex - currentIndex) === 1) {
      return { from: currentIndex, to: nextIndex };
   }

   if (nextIndex > 0) {
      return { from: nextIndex - 1, to: nextIndex };
   }

   return null;
}

function drawMovingMap(data) {
   const canvas = document.getElementById("moving-map-canvas");
   
   if (!canvas || !data.aircraft) {
      return;
   }

   const rect = canvas.getBoundingClientRect();

   if (rect.width < 10 || rect.height < 10) {
      return;
   }

   canvas.width = Math.floor(rect.width);
   canvas.height = Math.floor(rect.height);

   const ctx  = canvas.getContext("2d");

   const width = canvas.width;
   const height = canvas.height;
   const centerX = width / 2;
   const centerY = height / 2;

   const aircraftLat = numberOrZero(data.aircraft.lat);
   const aircraftLon = numberOrZero(data.aircraft.lon);
   const routePoints = getRoutePoints(data);

   ctx.clearRect(0, 0, width, height);

   // drawMapBackground(ctx, width, height);
   // drawMapRings(ctx, centerX, centerY, width, height);
   ctx.fillStyle = "#071018";
   ctx.fillRect(0, 0, width, height);

   const pixelsPerNm = 2.2;

   function project(lat, lon) {
      const avgLatRad = aircraftLat * Math.PI / 180.0;

      const northNm = (lat - aircraftLat) * 60.0;
      const eastNm = (lon - aircraftLon) * 60.0 * Math.cos(avgLatRad);

      return {
         x: centerX + eastNm * pixelsPerNm,
         y: centerY - northNm * pixelsPerNm,
      };
   }

   // drawMapImage(ctx, data, project);
   const mapWasDrawn = drawMapImage(ctx, data, project);

   if (!mapWasDrawn) {
      ctx.fillStyle = "#ffff66";
      ctx.font = "12px monospace";
      ctx.fillText("MAP IMAGE NOT LOADED", 10, height - 12);
   }

   drawMapRings(ctx, centerX, centerY, width, height);
   drawRoute(ctx, routePoints, project);
   drawActiveLeg(ctx, routePoints, project, data);
   drawWaypoints(ctx, routePoints, project, data);
   drawOwnship(ctx, centerX, centerY, data.aircraft.heading);   

}

function drawMapImage(ctx, data, project) {
    if (!data.map || !data.map.image) {
        return false;
    }

    const image = getMovingMapImage(data.map.image);

    if (!image) {
        return false;
    }

    const north = numberOrZero(data.map.north);
    const south = numberOrZero(data.map.south);
    const west = numberOrZero(data.map.west);
    const east = numberOrZero(data.map.east);

    const topLeft = project(north, west);
    const bottomRight = project(south, east);

    const x = topLeft.x;
    const y = topLeft.y;
    const w = bottomRight.x - topLeft.x;
    const h = bottomRight.y - topLeft.y;

    ctx.globalAlpha = 1.0;
    ctx.drawImage(image, x, y, w, h);

    return true;
}

function drawMapBackground(ctx, width, height) {
   ctx.fillStyle = "#071018";
   ctx.fillRect(0, 0, width, height);

   ctx.strokeStyle = "rgba(120, 210, 255, 0.16)";
   ctx.lineWidth = 1;

   for (let x = 0; x < width; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
   }

   for (let y = 0; y < height; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
   }
}

function drawMapRings(ctx, centerX, centerY, width, height) {
   const maxRing = Math.min(width, height) * 0.42;

   ctx.strokeStyle = "rgba(170, 255, 170, 0.55)";

   for (const radius of [maxRing * 0.35, maxRing * 0.70, maxRing]) {
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI *2);
      ctx.stroke();
   }

   ctx.beginPath();
   ctx.moveTo(centerX, 0);
   ctx.lineTo(centerX, height);
   ctx.moveTo(0, centerY);
   ctx.lineTo(width, centerY);
   ctx.stroke();

   ctx.fillStyle = "#7dff7d";
   ctx.font = "12px monspace";
   ctx.fillText("N", centerX - 4, 16);
}

function drawRoute(ctx, routePoints, project) {
   if (routePoints.length < 2) {
      return;
   }

   ctx.strokeStyle = "rgba(255, 80, 255, 0.95)";
   ctx.lineWidth = 2;

   ctx.beginPath();

   routePoints.forEach((point, index) => {
      const lat = numberOrZero(point.lat);
      const lon = numberOrZero(point.lon);
      const pos = project(lat, lon);

      if (index === 0) {
         ctx.moveTo(pos.x, pos.y);
      } else {
         ctx.lineTo(pos.x, pos.y);
      }
   });
   ctx.stroke();
}


function drawActiveLeg(ctx, routePoints, project, data) {
   const leg = getActiveLegIndexes(routePoints, data);
   if (!leg) return;

   const from = routePoints[leg.from];
   const to = routePoints[leg.to];
   if (!from || !to) return;

   const a = project(numberOrZero(from.lat), numberOrZero(from.lon));
   const b = project(numberOrZero(to.lat), numberOrZero(to.lon));

   ctx.save();
   ctx.lineCap = "round";
   ctx.strokeStyle = "rgba(0, 0, 0, 0.85)";
   ctx.lineWidth = 6;
   ctx.beginPath();
   ctx.moveTo(a.x, a.y);
   ctx.lineTo(b.x, b.y);
   ctx.stroke();

   ctx.strokeStyle = "rgba(255, 255, 90, 0.98)";
   ctx.lineWidth = 3;
   ctx.beginPath();
   ctx.moveTo(a.x, a.y);
   ctx.lineTo(b.x, b.y);
   ctx.stroke();
   ctx.restore();
}

function drawWaypoints(ctx, routePoints, project, data) {
   const currentWp = getCurrentWaypoint(data);
   const nextWp = getNextWaypoint(data);

   routePoints.forEach((point) => {
      const ident = getRouteIdent(point);
      const pos = project(numberOrZero(point.lat), numberOrZero(point.lon));

      if (
         pos.x < -80 || 
         pos.x > ctx.canvas.width + 80 || 
         pos.y < -80 ||
         pos.y > ctx.canvas.height + 80
      ) {
         return;
      }

      const isNext = sameWaypointIdent(ident, nextWp);
      const isCurrent = sameWaypointIdent(ident, currentWp);

      ctx.save();
      ctx.fillStyle = isNext ? "#ffff66" : (isCurrent ? "#66ff66" : "#ff66ff");
      ctx.strokeStyle = "rgba(0, 0, 0, 0.95)";
      ctx.lineWidth = isNext ? 3 : 2;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, isNext ? 6 : 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.font = isNext ? "bold 11px monospace" : "11px monospace";
      ctx.lineWidth = 4;
      ctx.strokeStyle = "rgba(0, 0, 0, 0.9)";
      ctx.strokeText(ident, pos.x + 7, pos.y - 7);
      ctx.fillStyle = isNext ? "#ffff66" : "#ffffff";
      ctx.fillText(ident, pos.x + 7, pos.y - 7);
      ctx.restore();
   });
}

function drawOwnship( ctx, centerX, centerY, headingText) {
   const heading = parseInt(String(headingText).replace(/[^0-9.-]/g, ""), 10) || 0;
   const headingRad = heading * Math.PI / 180.0;

   ctx.save();
   ctx.translate(centerX, centerY);
   ctx.rotate(headingRad);

   ctx.strokeStyle = "#ffffff";
   ctx.fillStyle = "#ffffff";
   ctx.lineWidth = 2;

   ctx.beginPath();
   ctx.moveTo(0, -16);
   ctx.lineTo(9, 11);
   ctx.lineTo(0, 6);
   ctx.lineTo(-9, 11);
   ctx.closePath();
   ctx.stroke();

   ctx.restore();
}

function setText(id, value) {
  const el = document.getElementById(id);

  if(!el) {
    return;
  }
  el.textContent = value;
}

function showJsHeartbeat() {
  let box = document.getElementById("js-heartbeat");

  if (!box) {
    box = document.createElement("div");
    box.id = "js-heartbeat";
    box.style.position = "fixed";
    box.style.right = "12px";
    box.style.bottom = "12px";
    box.style.padding = "8px 12px";
    box.style.background = "#00334d";
    box.style.color = "#66d9ff";
    box.style.border = "1px solid #1fb6ff";
    box.style.zIndex = "9999";
    box.style.fontFamily = "monospace";
    document.body.appendChild(box);
  }
  box.textContent = "JS LIVE " + new Date().toLocaleTimeString();
}

function getValueByPath(data, path) {
   return path.split(".").reduce((obj, key) => {
      if (obj == undefined || obj == null) {
         return undefined;
      }
      return obj[key];
   }, data);
}

function formatBoundValue(value, format) {
   if (value === undefined || value === null) {
      return "---";
   }

   if (format === "nm1") {
      const n = Number(value);
      return Number.isFinite(n) ? n.toFixed(1) : "---";
   }

   if (format === "int") {
      const n = Number(value);
      return Number.isFinite(n) ? String(Math.round(n)) : "---";
   }

   return value;
}

function bindText(data) {
   const elements = document.querySelectorAll("[data-bind]");

   elements.forEach((el) => {
      const path = el.getAttribute("data-bind");
      const format = el.getAttribute("data-format");
      const value = getValueByPath(data, path);

      if (value !== undefined && value !== null) {
         el.textContent = formatBoundValue(value, format);
      }
   });
}

function compactPayload(payload) {
    if (!payload) {
        return "";
    }

    return Object.entries(payload)
        .map(([key, value]) => {
            if (Array.isArray(value)) {
                return key + "=" + value.length + " items";
            }

            if (typeof value === "object" && value !== null) {
                return key + "=" + JSON.stringify(value);
            }

            return key + "=" + value;
        })
        .join(" | ");
}

function statusClass(status) {
    if (status === "OK") {
        return "status-ok";
    }

    if (status === "STALE") {
        return "status-stale";
    }

    return "status-fail";
}

function busClass(bus) {
    if (bus === "BUS_A") {
        return "bus-a";
    }

    if (bus === "BUS_B") {
        return "bus-b";
    }

    return "";
}

function latestMessageByType(messages, typeName) {
    return messages.find((msg) => {
        const type = msg.message_type ?? msg.type;
        return type === typeName;
    });
}

function latestMessageByBus(messages, busName) {
    return messages.find((msg) => msg.bus === busName);
}

function messageStatusClass(status) {
    if (status === "OK") {
        return "good";
    }

    if (status === "STALE") {
        return "warn";
    }

    if (status === "NO_RESPONSE" || status === "FAILED") {
        return "bad";
    }

    return "warn";
}

function setSensorText(id, value) {
    const el = document.getElementById(id);

    if (el) {
        el.textContent = value;
    }
}

function setSensorStatus(id, status) {
    const el = document.getElementById(id);

    if (!el) {
        return;
    }

    const displayStatus = status === "OK" ? "HEALTHY" : status;
    el.textContent = displayStatus;

    el.classList.remove("good", "warn", "bad");
    el.classList.add(messageStatusClass(status));
}

async function updateSensorsPage() {
    if (!document.querySelector(".sensors-page-shell")) {
        return;
    }

    try {
        const response = await fetch("/api/messages");
        const data = await response.json();
        const messages = data.messages || [];

        const airData = latestMessageByType(messages, "AIR_DATA");
        const navData = latestMessageByType(messages, "NAV_DATA");
        const engineData = latestMessageByType(messages, "ENGINE_DATA");
        const fuelData = latestMessageByType(messages, "FUEL_DATA");
        const weatherData = latestMessageByType(messages, "WEATHER_RADAR");
        const busA = latestMessageByBus(messages, "BUS_A");
        const busB = latestMessageByBus(messages, "BUS_B");

        updateSensorHealthHistory(messages);
        updateSensorStatusTable(messages);
        updateSensorEventTable(messages);

        setSensorStatus("air-data-status", airData?.status || "UNKNOWN");
        setSensorStatus("nav-status", navData?.status || "UNKNOWN");
        setSensorStatus("engine-status", engineData?.status || "WARN");
        setSensorStatus("fuel-status", fuelData?.status || "UNKNOWN");

        setSensorStatus("air-data-overview-status", airData?.status || "UNKNOWN");
        setSensorStatus("nav-overview-status", navData?.status || "UNKNOWN");
        setSensorStatus("engine-overview-status", engineData?.status || "WARN");
        setSensorStatus("fuel-overview-status", fuelData?.status || "UNKNOWN");

        setSensorText("air-data-last-update", airData ? airData.tick : "--");
        setSensorText("nav-last-update", navData ? navData.tick : "--");
        setSensorText("engine-last-update", engineData ? engineData.tick : "--");
        setSensorText("fuel-last-update", fuelData ? fuelData.tick : "--");
        setSensorText("bus-a-last-update", busA ? busA.tick : "--");
        setSensorText("bus-b-last-update", busB ? busB.tick : "--");
        setSensorText("oat-last-update", airData ? airData.tick : "--");

        const busACount = messages.filter((msg) => msg.bus === "BUS_A").length;
        const busBCount = messages.filter((msg) => msg.bus === "BUS_B").length;

        setSensorText("bus-a-rate", busACount + " recent");
        setSensorText("bus-b-rate", busBCount + " recent");

        const healthy = [airData, navData, fuelData, busA, busB].filter((msg) => msg && msg.status === "OK").length;
        const warn = engineData && engineData.status === "OK" ? 1 : 1;
        const fault = messages.filter((msg) => msg.status === "NO_RESPONSE").length;

        setSensorText("sensor-healthy-count", healthy);
        setSensorText("sensor-warn-count", warn);
        setSensorText("sensor-fault-count", fault);
        setSensorText("sensor-unknown-count", 0);
    } catch (error) {
        console.error("Sensors update failed:", error);
    }
}

function updateSensorStatusTable(messages) {
    const body = document.getElementById("sensor-status-body");

    if (!body) {
        return;
    }

    const rows = [
        ["AIR DATA RT", latestMessageByType(messages, "AIR_DATA"), "1 tick"],
        ["NAV RT", latestMessageByType(messages, "NAV_DATA"), "1 tick"],
        ["ENGINE RT", latestMessageByType(messages, "ENGINE_DATA"), "2 ticks"],
        ["FUEL RT", latestMessageByType(messages, "FUEL_DATA"), "2 ticks"],
        ["WEATHER RADAR RT", latestMessageByType(messages, "WEATHER_RADAR"), "5 ticks"],
        ["BUS A MONITOR", latestMessageByBus(messages, "BUS_A"), "live"],
        ["BUS B MONITOR", latestMessageByBus(messages, "BUS_B"), "live"],
    ];

    body.innerHTML = rows.map(([name, msg, rate]) => {
        const status = msg?.status || "UNKNOWN";
        const displayStatus = status === "OK" ? "HEALTHY" : status;
        const css = messageStatusClass(status);
        const tick = msg?.tick ?? "--";

        return `
            <tr>
                <td>${name}</td>
                <td class="${css}">${displayStatus}</td>
                <td>${tick}</td>
                <td>${rate}</td>
            </tr>
        `;
    }).join("");
}

function updateSensorEventTable(messages) {
    const body = document.getElementById("sensor-events-body");

    if (!body) {
        return;
    }

    const interesting = messages
        .filter((msg) => msg.status !== "OK" || msg.message_type === "ENGINE_DATA" || msg.message_type === "WEATHER_RADAR")
        .slice(0, 10);

    if (interesting.length === 0) {
        body.innerHTML = '<tr><td>--</td><td>All Sensors</td><td class="good">OK</td><td>No sensor events</td></tr>';
        return;
    }

    body.innerHTML = interesting.map((msg) => {
        const type = msg.message_type ?? msg.type ?? "UNKNOWN";
        const rt = msg.rt ?? msg.source ?? "UNKNOWN";
        const status = msg.status ?? "OK";
        const css = messageStatusClass(status);

        let details = "Nominal";

        if (type === "ENGINE_DATA") {
            details = "Engine temp " + (msg.payload?.engine_temp_c ?? "--") + " °C";
        } else if (type === "WEATHER_RADAR") {
            details = "Returns " + (msg.payload?.returns?.length ?? 0);
        } else if (status !== "OK") {
            details = "Status " + status;
        }

        return `
            <tr>
                <td>${msg.tick}</td>
                <td>${rt}</td>
                <td class="${css}">${status}</td>
                <td>${details}</td>
            </tr>
        `;
    }).join("");
}

setInterval(updateSensorsPage, 500);
updateSensorsPage();

async function updateBusMessages() {
    const tableBody = document.getElementById("bus-message-body");

    if (!tableBody) {
        return;
    }

    try {
        const response = await fetch("/api/messages");
        const data = await response.json();
        const messages = data.messages || [];

        const countEl = document.getElementById("bus-message-count");
        const statusEl = document.getElementById("bus-monitor-status");

        if (countEl) {
            countEl.textContent = messages.length;
        }

        if (statusEl) {
            statusEl.textContent = "live - " + messages.length + " recent messages";
        }

        if (messages.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="10">No messages yet.</td></tr>';
            return;
        }

        tableBody.innerHTML = messages.map((msg) => {
            const controller = msg.controller ?? msg.bc ?? msg.source ?? "";
            const rt = msg.rt ?? msg.remote_terminal ?? msg.destination ?? "";
            const subaddress = msg.subaddress ?? msg.sa ?? "";
            const direction = msg.direction ?? msg.dir ?? "";
            const wordCount = msg.word_count ?? msg.words ?? "";
            const messageType = msg.message_type ?? msg.type ?? "";
            const status = msg.status ?? "OK";
            const payloadText = compactPayload(msg.payload);
        
            return `
                <tr>
                    <td>${msg.tick ?? ""}</td>
                    <td class="${busClass(msg.bus)}">${msg.bus ?? ""}</td>
                    <td>${controller}</td>
                    <td>${rt}</td>
                    <td>${subaddress}</td>
                    <td>${direction}</td>
                    <td>${wordCount}</td>
                    <td>${messageType}</td>
                    <td class="${statusClass(status)}">${status}</td>
                    <td class="payload-cell">${payloadText}</td>
                </tr>
            `;
        }).join("");

    } catch (error) {
        console.error("Bus message update failed:", error);

        const statusEl = document.getElementById("bus-monitor-status");

        if (statusEl) {
            statusEl.textContent = "error reading /api/messages";
        }
    }
}

setInterval(updateBusMessages, 500);
updateBusMessages();



let cockpitRadarRangeNm = Number(localStorage.getItem("mbilCockpitRadarRangeNm") || "40") || 40;
let cockpitRadarOverlaySeq = 0;
let cockpitPageStarted = false;
const cockpitRadarReadoutCache = { bearing: "---", nextWp: "---" };

function numericFromDisplay(value, fallback = 0) {
   if (value === undefined || value === null) return fallback;
   const n = Number(String(value).replace(/[^0-9.+-]/g, ""));
   return Number.isFinite(n) ? n : fallback;
}

function bearingDegBetween(lat1, lon1, lat2, lon2) {
   const r = Math.PI / 180.0;
   const p1 = Number(lat1) * r;
   const p2 = Number(lat2) * r;
   const dLon = (Number(lon2) - Number(lon1)) * r;
   const y = Math.sin(dLon) * Math.cos(p2);
   const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dLon);
   const brg = Math.atan2(y, x) / r;
   return ((brg % 360) + 360) % 360;
}

function radarBearingFromState(data) {
   const direct = data?.nav_display?.gps_bearing_deg ?? data?.sim?.gps_bearing_deg ?? data?.sim?.bearing_deg;
   if (direct !== undefined && direct !== null && direct !== "") {
      const n = Number(String(direct).replace(/[^0-9.+-]/g, ""));
      if (Number.isFinite(n)) return n;
   }

   const routePoints = getRoutePoints(data);
   const nextWp = getNextWaypoint(data);
   const nextIndex = findRoutePointIndex(routePoints, nextWp);
   const aircraft = data?.aircraft || {};

   if (nextIndex >= 0 && aircraft.lat !== undefined && aircraft.lon !== undefined) {
      return bearingDegBetween(aircraft.lat, aircraft.lon, routePoints[nextIndex].lat, routePoints[nextIndex].lon);
   }

   return null;
}

function textOrDash(value) {
   if (value === undefined || value === null || value === "") return "---";
   return String(value);
}

function fmt3(value) {
   const n = Number(value);
   if (!Number.isFinite(n)) return "---";
   return String(Math.round(((n % 360) + 360) % 360)).padStart(3, "0");
}

function fmtInt(value) {
   const n = Number(value);
   if (!Number.isFinite(n)) return "---";
   return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function setClassBool(id, active, armed = false) {
   const el = document.getElementById(id);
   if (!el) return;
   el.classList.toggle("active", !!active);
   el.classList.toggle("armed", !active && !!armed);
}

function updateAutopilotAnnunciators(prefix, autopilot) {
   const modes = autopilot?.modes || {};
   setClassBool(prefix + "-ap-ap", autopilot?.ap_engaged);
   setClassBool(prefix + "-ap-fd", autopilot?.fd_engaged);
   setClassBool(prefix + "-ap-yd", autopilot?.yd_engaged);
   setClassBool(prefix + "-ap-hdg", modes.HDG);
   setClassBool(prefix + "-ap-nav", modes.NAV);
   setClassBool(prefix + "-ap-alt", modes.ALT);
   setClassBool(prefix + "-ap-vs", modes.VS);
   setClassBool(prefix + "-ap-flc", modes.FLC);
   setClassBool(prefix + "-ap-apr", modes.APR);
   setClassBool(prefix + "-ap-gs", modes.GS);
}

function buildTape(center, step, count, decimals = 0) {
   const values = [];
   const half = Math.floor(count / 2);
   for (let i = half; i >= -half; i--) {
      const value = center + i * step;
      values.push(Number.isFinite(value) ? value.toFixed(decimals) : "---");
   }
   return values.join("<br>");
}

function updatePfd(prefix, data) {
   const aircraft = data.aircraft || {};
   const pfd = data.pfd || {};
   const autopilot = data.autopilot || {};

   const altitudeFt = Number.isFinite(Number(pfd.altitude_ft)) ? Number(pfd.altitude_ft) : numericFromDisplay(aircraft.altitude, 0);
   const airspeedKts = Number.isFinite(Number(pfd.airspeed_kts)) ? Number(pfd.airspeed_kts) : numericFromDisplay(aircraft.airspeed, 0);
   const gsKts = numericFromDisplay(aircraft.ground_speed || aircraft.airspeed, airspeedKts);
   const headingDeg = Number.isFinite(Number(pfd.heading_deg)) ? Number(pfd.heading_deg) : numericFromDisplay(aircraft.heading, 0);
   const vsFpm = Number.isFinite(Number(pfd.vertical_speed_fpm)) ? Number(pfd.vertical_speed_fpm) : numericFromDisplay(aircraft.vertical_speed, 0);
   const pitchDeg = Number.isFinite(Number(pfd.pitch_deg)) ? Number(pfd.pitch_deg) : Number(aircraft.pitch_deg || 0);
   const rollDeg = Number.isFinite(Number(pfd.roll_deg)) ? Number(pfd.roll_deg) : Number(aircraft.roll_deg || 0);

   setText(prefix + "-airspeed-box", fmtInt(airspeedKts));
   setText(prefix + "-altitude-box", fmtInt(altitudeFt));
   setText(prefix + "-heading-box", fmt3(headingDeg));
   setText(prefix + "-gs-box", fmtInt(gsKts));
   setText(prefix + "-vs-box", (vsFpm >= 0 ? "+" : "") + fmtInt(vsFpm));

   const airScale = document.getElementById(prefix + "-airspeed-scale");
   if (airScale) airScale.innerHTML = buildTape(Math.round(airspeedKts / 10) * 10, 20, 7, 0);

   const altScale = document.getElementById(prefix + "-altitude-scale");
   if (altScale) altScale.innerHTML = buildTape(Math.round(altitudeFt / 100) * 100, 200, 7, 0);

   const world = document.getElementById(prefix + "-attitude-world");
   if (world) {
      const pitchPx = Math.max(-75, Math.min(75, pitchDeg * 4.0));
      const roll = Math.max(-80, Math.min(80, rollDeg));
      world.style.transform = `translateY(${pitchPx}px) rotate(${-roll}deg)`;
   }

   const bankPointer = document.getElementById(prefix + "-bank-pointer");
   if (bankPointer) {
      const roll = Math.max(-80, Math.min(80, rollDeg));
      bankPointer.style.transform = `translateX(-50%) rotate(${roll}deg)`;
   }

   updateAutopilotAnnunciators(prefix, autopilot);

   setText(prefix + "-hdg-bug", autopilot.selected_heading_deg !== null && autopilot.selected_heading_deg !== undefined ? fmt3(autopilot.selected_heading_deg) + "°" : "---");
   setText(prefix + "-alt-bug", autopilot.selected_altitude_ft !== null && autopilot.selected_altitude_ft !== undefined ? fmtInt(autopilot.selected_altitude_ft) : "---");
   setText(prefix + "-spd-bug", autopilot.selected_airspeed_kts !== null && autopilot.selected_airspeed_kts !== undefined ? fmtInt(autopilot.selected_airspeed_kts) : "---");

   const brg = pfd.bearing_pointer_deg ?? data.nav_display?.gps_bearing_deg ?? data.sim?.gps_bearing_deg;
   const brgSrc = cleanWaypointIdent(pfd.bearing_pointer_source ?? data.nav_display?.next_wp ?? data.sim?.next_wp ?? "GPS", "GPS");
   setText(prefix + "-bearing-pointer", brg !== undefined && brg !== null ? `BRG ${fmt3(brg)} ${brgSrc}` : "BRG ---");
}

function setStatusClass(id, status) {
   const el = document.getElementById(id);
   if (!el) return;
   const normalized = String(status || "UNKNOWN").toUpperCase();
   el.textContent = normalized;
   el.classList.remove("good", "warn", "bad", "good-pill", "warn-pill", "bad-pill");
   if (normalized === "OK" || normalized === "ONLINE" || normalized === "HEALTHY" || normalized === "PRIMARY" || normalized === "STANDBY") {
      el.classList.add(id.endsWith("pill") ? "good-pill" : "good");
   } else if (normalized === "STALE" || normalized === "WARN" || normalized === "WARNING" || normalized === "NO DATA") {
      el.classList.add(id.endsWith("pill") ? "warn-pill" : "warn");
   } else {
      el.classList.add(id.endsWith("pill") ? "bad-pill" : "bad");
   }
}

function updateMissionComputersCockpit(data) {
   const mcs = data.mission_computers || {};
   const mc1 = mcs.mc1 || data.mc1 || {};
   const mc2 = mcs.mc2 || data.mc2 || {};

   function update(prefix, mc) {
      setText(prefix + "-role", mc.role || "---");
      setText(prefix + "-state", mc.state || "---");
      setText(prefix + "-heartbeat-cockpit", mc.heartbeat || "--");
      setText(prefix + "-bus-a", mc.bus_a || data.bus1553?.bus_a || "---");
      setText(prefix + "-bus-b", mc.bus_b || data.bus1553?.bus_b || "---");
      const inputs = mc.inputs || {};
      const outputs = mc.outputs || {};
      setText(prefix + "-air-data", inputs.air_data || "---");
      setText(prefix + "-ins", inputs.nav || "---");
      setText(prefix + "-engine", inputs.engine || "---");
      setText(prefix + "-fuel", inputs.fuel || "---");
      setText(prefix + "-display", outputs.displays || "---");
      setText(prefix + "-autopilot", outputs.autopilot || "---");
      setText(prefix + "-other-mc", outputs.other_mc || "---");
   }

   update("mc1", mc1);
   update("mc2", mc2);
}

function updateSystemStatusCockpit(data) {
   setStatusClass("bus-a-pill", data.bus1553?.bus_a || "NO DATA");
   setStatusClass("bus-b-pill", data.bus1553?.bus_b || "NO DATA");
   const arincOnline = (data.arinc429?.label_count || 0) > 0 ? "ONLINE" : "NO DATA";
   setStatusClass("arinc-pill", arincOnline);

   setText("input-source-label", data.input?.source || data.input?.active || "---");
   setText("route-source-label", data.nav_display?.route_source || data.sim?.route_source || "---");
   setText("taws-source-label", data.taws?.source || "---");
   setText("weather-source-label", data.weather_radar?.source || "---");
   setText("cockpit-radar-source", data.weather_radar?.source || "---");

   const stableNextWp = getNextWaypoint(data);
   if (stableNextWp) cockpitRadarReadoutCache.nextWp = stableNextWp;

   const stableBearing = radarBearingFromState(data);
   if (stableBearing !== null && stableBearing !== undefined) {
      cockpitRadarReadoutCache.bearing = fmt3(stableBearing) + "°";
   }

   setText("cockpit-radar-next-wp", cockpitRadarReadoutCache.nextWp);
   setText("cockpit-radar-brg", cockpitRadarReadoutCache.bearing);

   const fresh = data.input?.fresh !== false;
   setStatusClass("pilot-pfd-status", fresh ? "OK" : "STALE");
   setStatusClass("copilot-pfd-status", fresh ? "OK" : "STALE");
   setStatusClass("map-nav-status", data.nav_display ? "OK" : "NO DATA");
   setStatusClass("cockpit-radar-status", data.weather_radar ? "OK" : "NO DATA");
}

function updateCockpitAlerts(data) {
   const list = document.getElementById("cockpit-alert-list");
   const count = document.getElementById("cockpit-alert-count");
   if (!list) return;

   const alerts = [];
   if (data.input && data.input.fresh === false) alerts.push(["warn", "Input exchange stale"]);
   if (data.taws && data.taws.alert_state && data.taws.alert_state !== "CLEAR") alerts.push([data.taws.alert_state.includes("PULL") ? "bad" : "warn", data.taws.alert_state]);
   if (data.bus1553?.bus_a !== "ONLINE") alerts.push(["warn", "Bus A no data"]);
   if (data.bus1553?.bus_b !== "ONLINE") alerts.push(["warn", "Bus B no data"]);
   if (!data.autopilot?.valid) alerts.push(["warn", "Autopilot data unavailable"]);

   if (alerts.length === 0) alerts.push(["good", "Cockpit buses nominal"]);
   if (count) count.textContent = alerts.length;

   const now = new Date().toLocaleTimeString();
   list.innerHTML = alerts.slice(0, 5).map(([css, text]) => {
      return `<li><time>${now}</time><b class="${css}">${text}</b></li>`;
   }).join("");
}

function updateCockpitRadarRangeUi() {
   const canvas = document.getElementById("cockpit-weather-radar-canvas");
   if (canvas) {
      canvas.dataset.displayRangeNm = String(cockpitRadarRangeNm);
   }
   setText("cockpit-radar-range-label", cockpitRadarRangeNm + " NM");
   document.querySelectorAll("[data-radar-range]").forEach((el) => {
      el.classList.toggle("active-range", Number(el.dataset.radarRange) === cockpitRadarRangeNm);
   });
}

function setupCockpitRadarRangeButtons() {
   if (window.__mbilCockpitRadarRangeDelegated) {
      updateCockpitRadarRangeUi();
      return;
   }

   window.__mbilCockpitRadarRangeDelegated = true;
   document.addEventListener("click", (event) => {
      const el = event.target.closest("[data-radar-range]");
      if (!el) return;

      event.preventDefault();
      cockpitRadarRangeNm = Number(el.dataset.radarRange) || 40;
      localStorage.setItem("mbilCockpitRadarRangeNm", String(cockpitRadarRangeNm));
      updateCockpitRadarRangeUi();

      if (window.MbilDisplays && typeof window.MbilDisplays.updateFromApi === "function") {
         window.MbilDisplays.updateFromApi();
      } else {
         updateCockpit();
      }
   });

   updateCockpitRadarRangeUi();
}

function drawCockpitRadarNavOverlay(data) {
   const canvas = document.getElementById("cockpit-weather-radar-canvas");
   if (!canvas || !data.aircraft) return;

   const ctx = canvas.getContext("2d");
   const width = canvas.width;
   const height = canvas.height;
   if (!width || !height) return;

   const centerX = width / 2;
   const centerY = height / 2;
   const maxRadius = Math.min(width, height) * 0.78;
   const pxPerNm = maxRadius / cockpitRadarRangeNm;
   const aircraftLat = Number(data.aircraft.lat || 0);
   const aircraftLon = Number(data.aircraft.lon || 0);
   const headingDeg = numericFromDisplay(data.aircraft.heading, 0);
   const routePoints = getRoutePoints(data);
   const currentWp = getCurrentWaypoint(data);
   const nextWp = getNextWaypoint(data);

   if (!routePoints.length) return;

   function projectRadar(lat, lon) {
      const avgLatRad = aircraftLat * Math.PI / 180.0;
      const northNm = (lat - aircraftLat) * 60.0;
      const eastNm = (lon - aircraftLon) * 60.0 * Math.cos(avgLatRad);
      // Cockpit radar nav overlay is NORTH UP so it matches the MAP / NAV panel.
      // Weather returns may be produced by the radar renderer, but the flight-plan
      // overlay must use the same north-up projection as the map page.
      return {
         x: centerX + eastNm * pxPerNm,
         y: centerY - northNm * pxPerNm,
         rangeNm: Math.sqrt(northNm * northNm + eastNm * eastNm),
      };
   }

   function drawRoutePolyline(strokeStyle, lineWidth) {
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      let started = false;

      routePoints.forEach((point) => {
         const pos = projectRadar(numberOrZero(point.lat), numberOrZero(point.lon));
         if (pos.rangeNm > cockpitRadarRangeNm * 1.25) {
            started = false;
            return;
         }
         if (!started) {
            ctx.moveTo(pos.x, pos.y);
            started = true;
         } else {
            ctx.lineTo(pos.x, pos.y);
         }
      });

      ctx.stroke();
   }

   ctx.save();
   ctx.globalAlpha = 1.0;
   ctx.globalCompositeOperation = "source-over";

   // Draw the flight plan after weather returns so it stays on top.
   drawRoutePolyline("rgba(0, 0, 0, 0.95)", 6);
   drawRoutePolyline("rgba(255, 80, 255, 0.98)", 3);

   const leg = getActiveLegIndexes(routePoints, data);
   if (leg) {
      const from = routePoints[leg.from];
      const to = routePoints[leg.to];
      if (from && to) {
         const a = projectRadar(numberOrZero(from.lat), numberOrZero(from.lon));
         const b = projectRadar(numberOrZero(to.lat), numberOrZero(to.lon));
         if (a.rangeNm <= cockpitRadarRangeNm * 1.25 || b.rangeNm <= cockpitRadarRangeNm * 1.25) {
            ctx.lineCap = "round";
            ctx.strokeStyle = "rgba(0, 0, 0, 0.95)";
            ctx.lineWidth = 7;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();

            ctx.strokeStyle = "rgba(255, 255, 90, 1.0)";
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
         }
      }
   }

   routePoints.forEach((point) => {
      const ident = getRouteIdent(point);
      const pos = projectRadar(numberOrZero(point.lat), numberOrZero(point.lon));
      if (pos.rangeNm > cockpitRadarRangeNm * 1.25) return;

      const isNext = sameWaypointIdent(ident, nextWp);
      const isCurrent = sameWaypointIdent(ident, currentWp);
      ctx.fillStyle = isNext ? "#ffff66" : (isCurrent ? "#66ff66" : "#ff66ff");
      ctx.strokeStyle = "rgba(0,0,0,0.95)";
      ctx.lineWidth = isNext ? 4 : 3;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, isNext ? 6 : 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.font = isNext ? "bold 11px monospace" : "11px monospace";
      ctx.lineWidth = 4;
      ctx.strokeStyle = "rgba(0,0,0,0.95)";
      ctx.strokeText(ident, pos.x + 8, pos.y - 8);
      ctx.fillStyle = isNext ? "#ffff66" : "#ffffff";
      ctx.fillText(ident, pos.x + 8, pos.y - 8);
   });

   // Since this overlay is NORTH UP, redraw the ownship with actual heading.
   // This prevents the radar from looking like a heading-up display while
   // the route overlay is north-up.
   ctx.save();
   ctx.translate(centerX, centerY);
   ctx.rotate(headingDeg * Math.PI / 180.0);
   ctx.fillStyle = "#ff66ff";
   ctx.strokeStyle = "rgba(255,255,255,0.95)";
   ctx.lineWidth = 2;
   ctx.beginPath();
   ctx.moveTo(0, -15);
   ctx.lineTo(9, 11);
   ctx.lineTo(0, 6);
   ctx.lineTo(-9, 11);
   ctx.closePath();
   ctx.fill();
   ctx.stroke();
   ctx.restore();

   ctx.restore();
}

function drawCockpitRadarNavOverlayStable(data) {
   // Route/waypoint drawing is now owned by app/static/js/taws_weather.js.
   // Keeping a second cockpit-only canvas overlay caused the route and BRG
   // text to blink because the shared display renderer and cockpit page were
   // both redrawing the same canvas.
   return;
}

async function updateCockpit() {
   try {
      const response = await fetch("/api/state");
      const data = await response.json();

      document.title = "Mission Bus Lab";
      bindText(data);
      drawMovingMap(data);
      updateCockpitRadarRangeUi();

      if (window.MbilDisplays && typeof window.MbilDisplays.updateAll === "function") {
         window.MbilDisplays.updateAll(data);
      }
      drawCockpitRadarNavOverlayStable(data);

      updatePfd("pilot", data);
      updatePfd("copilot", data);
      updateMissionComputersCockpit(data);
      updateSystemStatusCockpit(data);
      updateCockpitAlerts(data);

      setText("aircraft-altitude", data.aircraft?.altitude || "---");
      setText("aircraft-airspeed", data.aircraft?.airspeed || "---");
      setText("aircraft-heading", String(data.aircraft?.heading || "---").includes("°") ? data.aircraft.heading : (data.aircraft?.heading || "---") + "°");
      setText("aircraft-vertical-speed", data.aircraft?.vertical_speed || "---");
      setText("aircraft-fuel", data.aircraft?.fuel || "---");
      setText("aircraft-engine-temp", data.aircraft?.engine_temp || "---");
   } catch (error) {
      console.error("Cockpit update failed:", error);
   }
}

function startCockpitPage() {
   if (cockpitPageStarted) return;
   cockpitPageStarted = true;
   setupCockpitRadarRangeButtons();
   setInterval(updateCockpit, 500);
   updateCockpit();
}

if (document.readyState === "loading") {
   document.addEventListener("DOMContentLoaded", startCockpitPage);
} else {
   startCockpitPage();
}

function updateMissionComputerHeartbeat(data) {
   const mc1Heartbeat = document.getElementById("mc1-heartbeat");
   const mc2Heartbeat = document.getElementById("mc2-heartbeat");
   
   if (!data || !data.sim) {
      return;
   }

   const seconds = data.sim.tick / 10.0;
   const formatted = "00:00:" + seconds.toFixed(2).padStart(5, "0");

   if (mc1Heartbeat) {
      mc1Heartbeat.textContent = formatted;
   }
   if (mc2Heartbeat) {
      mc2Heartbeat.textContent = formatted;
   }
}

function drawMcHeartbeat(canvasId, color) {
   const canvas = document.getElementById(canvasId);

   if (!canvas) {
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
   const midY = height / 2;

   ctx.clearRect(0, 0, width, height);

   ctx.strokeStyle = color;
   ctx.lineWidth = 2;
   ctx.beginPath();

   for (let x = 0; x < width; x += 4) {
      const t = (Date.now() / 120) + x;
      let y = midY + Math.sin(t * 0.18) * 6;

      if (x % 34 < 5) {
         y -= 14;
      }

      if (x === 0) {
         ctx.moveTo(x, y);
         } else {
            ctx.lineTo(x, y);
         }
      }

      ctx.stroke();
}

function updateMissionComputersPage(data) {
   if (!document.querySelector(".mc2-page-shell")) {
      return;
   }

   const seconds = data.sim.tick / 10.0;
   const formatted = "00:00:" + seconds.toFixed(2).padStart(5, "0");

   const mc1Uptime = document.getElementById("mc1-uptime");
   const mc2Uptime = document.getElementById("mc2-uptime");
   const mc1Heartbeat = document.getElementById("mc1-heartbeat");
   const mc2Heartbeat = document.getElementById("mc2-heartbeat");
   const mc2HeartbeatCount = document.getElementById("mc2-heartbeat-count");

   if (mc1Uptime) mc1Uptime.textContent = formatted;
   if (mc2Uptime) mc2Uptime.textContent = formatted;
   if (mc1Heartbeat) mc1Heartbeat.textContent = "00:00:00.12";
   if (mc2Heartbeat) mc2Heartbeat.textContent = "00:00:00.14";
   if (mc2HeartbeatCount) mc2HeartbeatCount.textContent = Math.max(0, data.sim.tick - 5);

   drawMcHeartbeat("mc1-heartbeat-canvas", "#6dff7d");
   drawMcHeartbeat("mc2-heartbeat-canvas", "#ffd84d");
}

const SENSOR_HISTORY_LENGTH = 48;

const sensorHistory = {
   AIR_DATA_RT: [],
   NAV_RT: [],
   ENGINE_RT: [],
   FUEL_RT: [],
   OAT_SENSOR: [],
   BUS_A: [],
   BUS_B: [],
};

let lastSensorHistoryTick = null;

function historyStatusFromMessage(msg) {
   if (!msg) {
      return "unknown";
   }

   const status = msg.status || "UNKNOWN";

   if (status === "OK" || status === "HEALTHY") {
      return "ok";
   }

   if (msg.status === "STALE" || msg.status === "WARN" || status === "WARNING") {
      return "warn";
   }

   if (msg.status === "NO_RESPONSE" || msg.status === "FAILED" || status === "FAULT") {
      return "fault";
   }

   return "unknown";
}

function pushSensorHistory(sensorName, status) {
   if (!sensorHistory[sensorName]) {
      sensorHistory[sensorName] = [];
   }

   sensorHistory[sensorName].push(status);

   while (sensorHistory[sensorName].length > SENSOR_HISTORY_LENGTH) {
      sensorHistory[sensorName].shift();
   }
}

function renderSensorHistoryRows() {
   document.querySelectorAll("[data-history-sensor]").forEach((row) =>  {
      const sensorName = row.dataset.historySensor;
      const values = sensorHistory[sensorName] || [];

      let fillValue = "unknown";

      if (values.length > 0) {
         fillValue = values[values.length - 1];
      }

      const padded = [];

      for (let i = values.length; i < SENSOR_HISTORY_LENGTH; i++) {
         padded.push("unknown");
      }

      padded.push(...values);

      row.innerHTML = padded.map((status) => {
         return `<span class="history-tick ${status}"></span>`;
      }).join("");
   });
}

function updateSensorHealthHistory(messages) {
   if (!document.querySelector(".sensors-page-shell")) {
      return;
   }

   if (!messages || messages.length === 0) {
      renderSensorHistoryRows();
      return;
   }

   const newestTick = Math.max(...messages.map((msg) => Number(msg.tick || 0)));

   if (newestTick === lastSensorHistoryTick) {
      return;
   }

   lastSensorHistoryTick = newestTick;

   const latest = {
      AIR_DATA_RT: latestMessageByType(messages, "AIR_DATA"),
      NAV_RT: latestMessageByType(messages, "NAV_DATA"),
      ENGINE_RT: latestMessageByType(messages, "ENGINE_DATA"),
      FUEL_RT: latestMessageByType(messages, "FUEL_DATA"),
      OAT_SENSOR: latestMessageByType(messages, "AIR_DATA"),
      STATIC_SENSOR: latestMessageByType(messages, "AIR_DATA"),
      BUS_A: latestMessageByBus(messages, "BUS_A"),
      BUS_B: latestMessageByBus(messages, "BUS_B"),
   }

   Object.entries(latest).forEach(([sensorName, msg]) => {
      let status = historyStatusFromMessage(msg);

      if (msg && newestTick - Number(msg.tick || 0) > 5) {
         status = "warn";
      }

      pushSensorHistory(sensorName, status);
   });

   renderSensorHistoryRows();
}

const faultButtonState = {};

async function postFault(url, enabled) {
   const response = await fetch(url, {
      method: "POST",
      headers: {
         "Content-Type": "application/json",
      }, 
      body: JSON.stringify({ enabled }),
   });

   return await response.json();
}

function renderFaultStatus(faults) {
   if (!faults || !faults.remote_terminals) {
      return;
   }

   Object.entries(faults.remote_terminals).forEach(([rtName, info]) => {
      const el = document.getElementById("fault-status-" + rtName);
      
      if (!el) {
         return;
      }

      el.classList.remove("ok", "stale", "failed");

      if (info.failed) {
         el.textContent = "NO_RESPONSE";
         el.classList.add("failed");
      } else if (info.stale) {
         el.textContent = "STALE";
         el.classList.add("stale");
      } else {
         el.textContent = "OK";
         el.classList.add("ok");
      }
   });

   document.querySelectorAll("[data-fault-rt]").forEach((button) => {
      const rt = button.dataset.faultRt;
      const type = button.dataset.faultType;
      const info = faults.remote_terminals[rt];
      
      button.classList.remove("active-stale", "active-failed");
      
      if (!info) {
         return;
      }

      if (type === "stale" && info.stale) {
         button.classList.add("active-stale");
      }

      if (type === "failed" && info.failed) {
         button.classList.add("active-failed");
      }
   });
}

async function refreshFaultStatus() {
   if (!document.querySelector(".fault-page-shell")) {
      return;
   }

   const response = await fetch("/api/faults");
   const data = await response.json();

   renderFaultStatus(data);
}

function setupFaultInjectionPage() {
   if (!document.querySelector(".fault-page-shell")) {
      return;
   }

   document.querySelectorAll("[data-fault-rt]").forEach((button) => {
      button.addEventListener("click", async () => {
         const rt = button.dataset.faultRt;
         const type = button.dataset.faultType;
         const key = rt + ":" + type;
         
         faultButtonState[key] = !faultButtonState[key];
         
         const url = `/api/faults/rt/${rt}/${type}`;
         const result = await postFault(url, faultButtonState[key]);
         
         renderFaultStatus(result.faults);
      });
   });

   const clearButton = document.getElementById("clear-all-faults");

   if (clearButton) {
      clearButton.addEventListener("click", async () => {
         await fetch("/api/faults/clear", { method: "POST" });
         
         Object.keys(faultButtonState).forEach((key) => {
            faultButtonState[key] = false;
         });

         refreshFaultStatus();
      });
   }

   refreshFaultStatus();
}

setupFaultInjectionPage();
setInterval(refreshFaultStatus, 1000);
