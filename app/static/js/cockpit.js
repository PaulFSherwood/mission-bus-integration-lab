let movingMapImage = null;
let movingMapImagePath = null;

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

function drawWaypoints(ctx, routePoints, project, data) {
   const currentWp = data.sim ? data.sim.current_wp : "";
   const nextWp = data.sim ? data.sim.next_wp : "";

   routePoints.forEach((point) => {
      const ident = point.id || point.ident || point.name || "WP";
      const pos = project(numberOrZero(point.lat), numberOrZero(point.lon));

      if (
         pos.x < -80 || 
         pos.x > ctx.canvas.width + 80 || 
         pos.y < -80 ||
         pos.y > ctx.canvas.height + 80
      ) {
         return;
      }

      if (ident === nextWp) {
         ctx.fillStyle = "#ffff66";
      } else if (ident === currentWp) {
         ctx.fillStyle = "#66ff66";
      } else {
         ctx.fillStyle = "#ff66ff";
      }

      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 4, 0, Math.PI * 2);
      ctx.fill();

      ctx.font = "11px monospace";
      ctx.fillText(ident, pos.x + 7, pos.y - 7);
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
    console.warn("Missing element id:", id);
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
    documnet.body.appendChild(box);
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

function bindText(data) {
   const elements = document.querySelectorAll("[data-bind]");

   elements.forEach((el) => {
      const path = el.getAttribute("data-bind");
      const value = getValueByPath(data, path);

      if (value !== undefined && value !== null) {
         el.textContent = value;
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

async function updateCockpit() {
   try {
      const response = await fetch("/api/state");
      const data = await response.json();

      bindText(data);
      updateBusMessages(data);
      drawMovingMap(data);
   } catch (error) {
      console.error("Cockpit update failed:", error);
   }

  const response = await fetch("/api/state");
  const data = await response.json();
  document.title = "Mission Bus Lab";

  setText("mc1-role", data.mc1.role);
  setText("mc1-state", data.mc1.state);

  setText("mc2-role", data.mc2.role);
  setText("mc2-state", data.mc2.state);

//   setText("current_wp", data.current_wp);
//   setText("next_wp", data.next_wp);

  setText("aircraft-altitude", data.aircraft.altitude);
  setText("aircraft-airspeed", data.aircraft.airspeed);
  setText("aircraft-heading", data.aircraft.heading);
  setText("aircraft-vertical-speed", data.aircraft.vertical_speed);
  setText("aircraft-fuel", data.aircraft.fuel);
  setText("aircraft-engine-temp", data.aircraft.engine_temp);
}

setInterval(updateCockpit, 500);
updateCockpit();

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