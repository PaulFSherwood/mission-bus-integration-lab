(() => {
  const stateHistory = [];
  const failState = { "pilot-pfd": "ok", radar: "ok", "map-nav": "ok", "copilot-pfd": "ok" };
  let mapImage = null;
  let mapImagePath = null;

  function $(id) { return document.getElementById(id); }
  function setText(id, value) { const el = $(id); if (el) el.textContent = value; }
  function num(v, d = 0) { const n = Number(String(v ?? "").replace(/[^0-9.+-]/g, "")); return Number.isFinite(n) ? n : d; }
  function fmtInt(v) { const n = Number(v); return Number.isFinite(n) ? Math.round(n).toLocaleString() : "---"; }
  function fmt3(v) { const n = Number(v); return Number.isFinite(n) ? String(Math.round(((n % 360) + 360) % 360)).padStart(3, "0") : "---"; }
  function fmtNm(v) { const n = Number(v); return Number.isFinite(n) ? n.toFixed(1) + " NM" : "---"; }
  function cleanIdent(v, fallback = "WP") {
    let t = String(v ?? "").split("\0", 1)[0].trim().toUpperCase().replace(/[^A-Z0-9_-]/g, "");
    if (!t || t.length > 10 || (t.length >= 4 && new Set(t).size <= 1)) return fallback;
    return t;
  }
  function getRoutePoints(data) {
    if (Array.isArray(data.route_points)) return data.route_points;
    if (data.sim && Array.isArray(data.sim.route_points)) return data.sim.route_points;
    if (data.route && Array.isArray(data.route.points)) return data.route.points;
    return [];
  }
  function getPointId(p) { return cleanIdent(p?.id || p?.ident || p?.name || p?.label || "WP"); }
  function currentWp(data) { return cleanIdent(data?.nav_display?.current_wp || data?.sim?.current_wp || "", ""); }
  function nextWp(data) { return cleanIdent(data?.nav_display?.next_wp || data?.sim?.next_wp || "", ""); }
  function resizeCanvas(canvas) {
    const r = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(100, Math.floor(r.width * dpr));
    const h = Math.max(100, Math.floor(r.height * dpr));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w: r.width, h: r.height };
  }

  function drawPfd(canvasId, data, label) {
    const canvas = $(canvasId); if (!canvas) return;
    const { ctx, w, h } = resizeCanvas(canvas);
    const pfd = data.pfd || {};
    const ap = data.autopilot || {};
    const pitch = num(pfd.pitch_deg ?? data.aircraft?.pitch_deg, 0);
    const roll = Math.max(-80, Math.min(80, num(pfd.roll_deg ?? data.aircraft?.roll_deg, 0)));
    const ias = num(pfd.airspeed_kts ?? data.aircraft?.airspeed, 0);
    const alt = num(pfd.altitude_ft ?? data.aircraft?.altitude, 0);
    const hdg = num(pfd.heading_deg ?? data.aircraft?.heading, 0);
    const vs = num(pfd.vertical_speed_fpm ?? data.aircraft?.vertical_speed, 0);

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#02070b"; ctx.fillRect(0, 0, w, h);

    // AP annunciator strip
    const modes = ap.modes || {};
    const anns = [ ["AP", ap.ap_engaged], ["FD", ap.fd_engaged], ["YD", ap.yd_engaged], ["HDG", modes.HDG], ["NAV", modes.NAV], ["ALT", modes.ALT], ["VS", modes.VS], ["FLC", modes.FLC], ["APR", modes.APR], ["GS", modes.GS] ];
    let x = 10;
    ctx.font = "10px monospace";
    anns.forEach(([name, on]) => { ctx.fillStyle = on ? "#6dff7d" : "#06101a"; ctx.strokeStyle = "#1c3348"; ctx.fillRect(x, 8, 24, 17); ctx.strokeRect(x, 8, 24, 17); ctx.fillStyle = on ? "#001000" : "#335063"; ctx.fillText(name, x + 4, 20); x += 27; });

    const cx = w / 2, cy = h * 0.48;
    const ballW = Math.min(w * 0.46, 180), ballH = h * 0.62;
    ctx.save();
    ctx.beginPath(); ctx.rect(cx - ballW / 2, 34, ballW, ballH); ctx.clip();
    ctx.translate(cx, cy + pitch * 3.2); ctx.rotate(-roll * Math.PI / 180);
    ctx.fillStyle = "#1d7ee8"; ctx.fillRect(-w, -h * 2, w * 2, h * 2);
    ctx.fillStyle = "#704313"; ctx.fillRect(-w, 0, w * 2, h * 2);
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-w, 0); ctx.lineTo(w, 0); ctx.stroke();
    ctx.strokeStyle = "rgba(255,255,255,.75)"; ctx.lineWidth = 1; ctx.font = "12px monospace"; ctx.fillStyle = "#fff";
    [-30,-20,-10,10,20,30].forEach(deg => { const y = -deg * 3.2; ctx.beginPath(); ctx.moveTo(-28, y); ctx.lineTo(28, y); ctx.stroke(); ctx.fillText(String(deg), 35, y + 4); });
    ctx.restore();

    // Fixed aircraft symbol
    ctx.strokeStyle = "#ff66ff"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(cx - 36, cy); ctx.lineTo(cx - 10, cy); ctx.moveTo(cx + 10, cy); ctx.lineTo(cx + 36, cy); ctx.stroke();
    ctx.strokeStyle = "#fff"; ctx.beginPath(); ctx.moveTo(cx - 8, cy + 8); ctx.lineTo(cx, cy - 8); ctx.lineTo(cx + 8, cy + 8); ctx.stroke();

    // Roll scale and pointer
    ctx.save(); ctx.translate(cx, 48); ctx.rotate(roll * Math.PI / 180); ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.moveTo(0, -9); ctx.lineTo(-6, 5); ctx.lineTo(6, 5); ctx.closePath(); ctx.fill(); ctx.restore();
    ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.beginPath(); ctx.arc(cx, 54, 70, Math.PI*1.08, Math.PI*1.92); ctx.stroke();

    // Tapes
    function tape(left, title, value, unit, step) {
      ctx.fillStyle = "#dff6ff"; ctx.font = "11px monospace"; ctx.fillText(title, left, 48);
      ctx.strokeStyle = "rgba(255,255,255,.55)"; ctx.strokeRect(left, 66, 56, h - 110);
      ctx.fillStyle = "#fff"; ctx.font = "12px monospace";
      for (let i=-3;i<=3;i++) ctx.fillText(fmtInt(value + i*step), left + 9, cy + i*24 + 4);
      ctx.fillStyle = "#101b25"; ctx.fillRect(left - 3, cy - 14, 64, 28); ctx.strokeStyle = "#fff"; ctx.strokeRect(left - 3, cy - 14, 64, 28); ctx.fillStyle = "#fff"; ctx.font = "bold 15px monospace"; ctx.fillText(fmtInt(value), left + 7, cy + 6);
      ctx.fillStyle = "#dff6ff"; ctx.font = "11px monospace"; ctx.fillText(unit, left + 18, 62);
    }
    tape(12, "IAS", ias, "KTS", 20);
    tape(w - 68, "ALT", alt, "FT", 200);

    ctx.fillStyle = "#6dff7d"; ctx.font = "12px monospace"; ctx.fillText("HDG " + fmt3(hdg) + "°", cx - 34, h - 18);
    ctx.fillStyle = "#fff"; ctx.fillText("VS " + (vs >= 0 ? "+" : "") + fmtInt(vs), w - 105, h - 18);
    ctx.fillStyle = "#ffd84d"; ctx.fillText("BRG " + fmt3(data.nav_display?.gps_bearing_deg) + " " + nextWp(data), 82, h - 18);
    ctx.fillStyle = "#31b7ff"; ctx.font = "bold 12px monospace"; ctx.fillText(label, 10, h - 6);
  }

  function drawRadar(canvasId, data) {
    const canvas = $(canvasId); if (!canvas) return;
    const { ctx, w, h } = resizeCanvas(canvas);
    const cx = w / 2, cy = h / 2 + 8;
    const range = num(data.radar_display?.range_nm || data.weather_radar?.range_nm, 40);
    ctx.clearRect(0,0,w,h); ctx.fillStyle="#02070b"; ctx.fillRect(0,0,w,h);
    const rMax = Math.min(w,h) * .40;
    ctx.strokeStyle = "rgba(120,255,140,.50)"; ctx.lineWidth = 1;
    [0.33,0.66,1].forEach(k=>{ctx.beginPath();ctx.arc(cx,cy,rMax*k,0,Math.PI*2);ctx.stroke();});
    ctx.beginPath(); ctx.moveTo(cx-rMax,cy); ctx.lineTo(cx+rMax,cy); ctx.moveTo(cx,cy-rMax); ctx.lineTo(cx,cy+rMax); ctx.stroke();
    ctx.fillStyle="#fff"; ctx.font="bold 18px monospace"; ctx.fillText("N", cx-6, cy-rMax-8);

    const heading = num(data.aircraft?.heading, 0);
    const cells = data.weather_radar?.cells || [];
    cells.forEach((cell, i) => {
      const bearing = num(cell.bearing_deg ?? cell.bearing ?? (i*95+20), i*90);
      const dist = num(cell.range_nm ?? cell.distance_nm ?? cell.distance ?? (8+i*8), 8+i*8);
      const rel = (bearing - heading) * Math.PI/180;
      const rr = Math.min(rMax, dist / range * rMax);
      const x = cx + Math.sin(rel)*rr, y = cy - Math.cos(rel)*rr;
      const intensity = String(cell.level || cell.intensity || "green").toLowerCase();
      const color = intensity.includes("red") || intensity.includes("severe") ? "rgba(255,60,40,.75)" : intensity.includes("yellow") || intensity.includes("mod") ? "rgba(255,230,70,.75)" : "rgba(0,210,90,.68)";
      ctx.fillStyle=color; ctx.beginPath(); ctx.arc(x,y,20+6*i,0,Math.PI*2); ctx.fill();
    });

    drawRouteOverlay(ctx, data, cx, cy, rMax, range, true);
    ctx.fillStyle="#ff66ff"; ctx.strokeStyle="#fff"; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(cx,cy-17); ctx.lineTo(cx+10,cy+11); ctx.lineTo(cx,cy+5); ctx.lineTo(cx-10,cy+11); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle="#6dff7d"; ctx.font="12px monospace"; ctx.fillText("RNG " + range + " NM", 12, 22); ctx.fillText("BRG " + fmt3(data.nav_display?.gps_bearing_deg), w-88, h-34); ctx.fillText("TO " + nextWp(data), w-92, h-18); ctx.fillText("HDG UP", w-74, h-4);
  }

  function getMapImage(path) {
    if (!path) return null;
    if (mapImagePath !== path) { mapImagePath = path; mapImage = new Image(); mapImage.src = path; }
    return mapImage && mapImage.complete && mapImage.naturalWidth ? mapImage : null;
  }

  function drawMap(canvasId, data) {
    const canvas = $(canvasId); if (!canvas) return;
    const { ctx, w, h } = resizeCanvas(canvas);
    const aircraft = data.aircraft || {}; const lat0 = Number(aircraft.lat || 0), lon0 = Number(aircraft.lon || 0);
    ctx.clearRect(0,0,w,h); ctx.fillStyle="#071018"; ctx.fillRect(0,0,w,h);
    const image = getMapImage(data.map?.image);
    if (image && data.map) {
      const pxPerNm = 2.2;
      const project = (lat, lon) => { const avg = lat0*Math.PI/180; const n=(lat-lat0)*60; const e=(lon-lon0)*60*Math.cos(avg); return {x:w/2+e*pxPerNm,y:h/2-n*pxPerNm}; };
      const tl = project(Number(data.map.north), Number(data.map.west));
      const br = project(Number(data.map.south), Number(data.map.east));
      ctx.drawImage(image, tl.x, tl.y, br.x-tl.x, br.y-tl.y);
    }
    const rMax=Math.min(w,h)*.40; ctx.strokeStyle="rgba(120,255,140,.42)"; [0.33,.66,1].forEach(k=>{ctx.beginPath();ctx.arc(w/2,h/2,rMax*k,0,Math.PI*2);ctx.stroke();}); ctx.beginPath();ctx.moveTo(w/2,0);ctx.lineTo(w/2,h);ctx.moveTo(0,h/2);ctx.lineTo(w,h/2);ctx.stroke(); ctx.fillStyle="#6dff7d"; ctx.font="12px monospace"; ctx.fillText("N", w/2-4, 16);
    drawRouteOverlay(ctx, data, w/2, h/2, rMax, 40, false);
    const hdg = num(data.aircraft?.heading,0)*Math.PI/180; ctx.save(); ctx.translate(w/2,h/2); ctx.rotate(hdg); ctx.strokeStyle="#fff"; ctx.lineWidth=2; ctx.beginPath(); ctx.moveTo(0,-16); ctx.lineTo(9,11); ctx.lineTo(0,5); ctx.lineTo(-9,11); ctx.closePath(); ctx.stroke(); ctx.restore();
    ctx.fillStyle="rgba(0,0,0,.65)"; ctx.fillRect(8,8,96,82); ctx.fillStyle="#fff"; ctx.font="12px monospace"; ctx.fillText("TRK " + fmt3(data.aircraft?.heading), 14, 24); ctx.fillText("GS " + (data.aircraft?.ground_speed || "---"), 14, 40); ctx.fillText("TO " + nextWp(data), 14, 56); ctx.fillText("DIS " + fmtNm(data.nav_display?.gps_distance_nm || data.sim?.gps_distance_nm), 14, 72);
  }

  function drawRouteOverlay(ctx, data, cx, cy, rMax, rangeNm, headingUp) {
    const pts = getRoutePoints(data); if (!pts.length) return;
    const aircraft = data.aircraft || {}; const lat0=Number(aircraft.lat||0), lon0=Number(aircraft.lon||0), heading=num(aircraft.heading,0);
    const pxPerNm = rMax / Math.max(1, rangeNm);
    const project = (p) => { const lat=Number(p.lat||lat0), lon=Number(p.lon||lon0); const avg=lat0*Math.PI/180; let n=(lat-lat0)*60; let e=(lon-lon0)*60*Math.cos(avg); if (headingUp) { const a=-heading*Math.PI/180; const ne=n*Math.cos(a)-e*Math.sin(a); const ee=n*Math.sin(a)+e*Math.cos(a); n=ne; e=ee; } return {x:cx+e*pxPerNm,y:cy-n*pxPerNm}; };
    ctx.lineCap="round"; ctx.lineJoin="round"; ctx.strokeStyle="rgba(0,0,0,.85)"; ctx.lineWidth=5; ctx.beginPath(); pts.forEach((p,i)=>{const q=project(p); if(i===0)ctx.moveTo(q.x,q.y); else ctx.lineTo(q.x,q.y);}); ctx.stroke();
    ctx.strokeStyle="rgba(255,80,255,.95)"; ctx.lineWidth=2; ctx.beginPath(); pts.forEach((p,i)=>{const q=project(p); if(i===0)ctx.moveTo(q.x,q.y); else ctx.lineTo(q.x,q.y);}); ctx.stroke();
    const nxt = nextWp(data); pts.forEach(p => { const q=project(p); const id=getPointId(p); const isNext=id===nxt; ctx.fillStyle=isNext?"#ffff66":"#ff66ff"; ctx.strokeStyle="#000"; ctx.lineWidth=isNext?3:2; ctx.beginPath();ctx.arc(q.x,q.y,isNext?5:4,0,Math.PI*2);ctx.fill();ctx.stroke(); ctx.font=isNext?"bold 11px monospace":"11px monospace"; ctx.strokeText(id,q.x+7,q.y-7); ctx.fillText(id,q.x+7,q.y-7); });
  }

  function setStatus(data) {
    const fresh = data.input?.fresh !== false;
    const stale = fresh ? "NO" : "YES";
    ["pilot","copilot"].forEach(p=>{ setText(`disp-${p}-source`, data.pfd?.source || "---"); setText(`disp-${p}-age`, (data.input?.bus_age_sec ?? "--") + " sec"); setText(`disp-${p}-stale`, stale); setText(`disp-${p}-status`, fresh ? "OK" : "STALE"); setText(`disp-${p}-rate`, "10 Hz"); });
    setText("disp-radar-source", data.radar_display?.source || data.weather_radar?.source || "---"); setText("disp-radar-range", (data.radar_display?.range_nm || 40) + " NM"); setText("disp-radar-returns", String(data.weather_radar?.cell_count ?? data.weather_radar?.cells?.length ?? "--")); setText("disp-radar-stale", stale); setText("disp-radar-status", fresh ? "OK" : "STALE"); setText("disp-radar-rate", "5 Hz");
    setText("disp-map-source", data.nav_display?.source || "---"); setText("disp-map-route", data.nav_display?.route || data.sim?.route || "---"); setText("disp-map-next", nextWp(data)); setText("disp-map-stale", stale); setText("disp-map-status", fresh ? "OK" : "STALE"); setText("disp-map-rate", "5 Hz");
    setText("display-flow-bus-a", "Bus A " + (data.bus1553?.bus_a || "---")); setText("display-flow-bus-b", "Bus B " + (data.bus1553?.bus_b || "---")); setText("display-flow-arinc", "ARINC " + ((data.arinc429?.label_count || 0) > 0 ? "ONLINE" : "---"));
    const failed = Object.values(failState).filter(v=>v==="failed").length; const degraded = Object.values(failState).filter(v=>v==="degraded").length; const ok = 4 - failed - degraded;
    setText("display-ok-count", ok); setText("display-stale-count", degraded + (fresh?0:1)); setText("display-failed-count", failed); setText("display-offline-count", 0);
    const alerts = [];
    if (!fresh) alerts.push("Display input stale"); if (failed) alerts.push(failed + " simulated display failure(s)"); if (degraded) alerts.push(degraded + " simulated degraded display(s)");
    const list = $("display-alert-list"); if (list) list.innerHTML = alerts.length ? alerts.map(a=>`<li>${a}</li>`).join("") : '<li class="good">No active display alerts</li>';
  }

  function updatePerf(data) {
    const now = performance.now();
    stateHistory.push(now); while (stateHistory.length && now - stateHistory[0] > 60000) stateHistory.shift();
    const rate = stateHistory.length > 1 ? (stateHistory.length - 1) / ((stateHistory[stateHistory.length-1]-stateHistory[0]) / 1000) : 0;
    setText("display-avg-rate", rate ? rate.toFixed(1) + " Hz" : "--"); setText("display-min-rate", rate ? Math.max(0, rate - 0.6).toFixed(1) + " Hz" : "--"); setText("display-max-rate", rate ? (rate + 0.6).toFixed(1) + " Hz" : "--"); setText("display-lag-avg", (data.input?.bus_age_sec ?? "--") + " sec");
  }

  async function updateDisplays() {
    if (!document.querySelector("[data-mbil-displays-page]")) return;
    try {
      const data = await (await fetch("/api/state", { cache: "no-store" })).json();
      drawPfd("disp-pilot-pfd", data, "PILOT"); drawPfd("disp-copilot-pfd", data, "COPILOT"); drawRadar("disp-radar", data); drawMap("disp-map", data); setStatus(data); updatePerf(data);
    } catch (e) { console.error("Displays update failed", e); }
  }

  function setupControls() {
    document.querySelectorAll("[data-display-fail]").forEach(btn => btn.addEventListener("click", () => { const k=btn.dataset.displayFail; failState[k] = failState[k] === "failed" ? "ok" : "failed"; document.querySelector(`[data-display-card='${k}']`)?.classList.toggle("failed", failState[k]==="failed"); }));
    document.querySelectorAll("[data-display-degrade]").forEach(btn => btn.addEventListener("click", () => { const k=btn.dataset.displayDegrade; failState[k] = failState[k] === "degraded" ? "ok" : "degraded"; document.querySelector(`[data-display-card='${k}']`)?.classList.toggle("degraded", failState[k]==="degraded"); }));
    $("display-clear-failures")?.addEventListener("click", () => { Object.keys(failState).forEach(k=>failState[k]="ok"); document.querySelectorAll("[data-display-card]").forEach(c=>c.classList.remove("failed","degraded")); });
    $("display-refresh-button")?.addEventListener("click", updateDisplays);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => { setupControls(); updateDisplays(); setInterval(updateDisplays, 500); });
  else { setupControls(); updateDisplays(); setInterval(updateDisplays, 500); }
})();
