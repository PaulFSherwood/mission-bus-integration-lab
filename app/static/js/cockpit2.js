function setText(id, value) {
  const el = document.getElementById(id);

  if (!el) {
    console.log("Missing id:", id);
    return;
  }
  el.textContent = value;
}

async function updateCockpit() {
  try {
    const response = await fetch("/api/state");
    const data = await response.json();

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
  } catch (error) {
    console.error("Cockpit update failed:", error);
  }
}

setInterval(updateCockpit, 500);
updateCockpit();
