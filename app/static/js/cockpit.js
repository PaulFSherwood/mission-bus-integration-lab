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

async function updateCockpit() {
  const response = await fetch("/api/state");
  const data = await response.json();
  document.title = data.aircraft.altitude;

  setText("mc1-role", data.mc1.role);
  setText("mc1-state", data.mc1.state);

  setText("mc2-role", data.mc2.role);
  setText("mc2-state", data.mc2.state);

  setText("aircraft-altitude", data.aircraft.altitude);
  setText("aircraft-airspeed", data.aircraft.airspeed);
  setText("aircraft-heading", data.aircraft.heading);
  setText("aircraft-vertical-speed", data.aircraft.vertical_speed);
  setText("aircraft-fuel", data.aircraft.fuel);
  setText("aircraft-engine-temp", data.aircraft.engine_temp);
}

setInterval(updateCockpit, 500);
updateCockpit();
