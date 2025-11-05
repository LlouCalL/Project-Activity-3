const el = (id) => document.getElementById(id);

const showMessage = (text, type = "info") => {
  const m = el("message");
  m.style.display = "block";
  m.className = `message ${type}`;
  m.textContent = text;
};

const hideMessage = () => {
  const m = el("message");
  m.style.display = "none";
  m.textContent = "";
};

const kmToMiles = (km) => km / 1.609;

async function fetchJSON(url) {
  const resp = await fetch(url);
  const data = await resp.json();
  if (!resp.ok || data.error) {
    throw new Error(data.error || `HTTP ${resp.status}`);
  }
  return data;
}

async function geocodeLocation(location) {
  const res = await fetchJSON(`/api/geocode?q=${encodeURIComponent(location)}`);
  if (!res.hits || res.hits.length === 0) {
    throw new Error("No results for " + location);
  }
  return res.hits[0].point;
}

async function getRoute(from, to, vehicle, unit) {
  hideMessage();
  el("output").hidden = true;
  el("instructionsTable").querySelector("tbody").innerHTML = "";

  try {
    showMessage("Geocoding start location...");
    const o = await geocodeLocation(from);

    showMessage("Geocoding destination...");
    const d = await geocodeLocation(to);

    showMessage("Fetching route...");
    const routeData = await fetchJSON(
      `/api/route?orig=${o.lat},${o.lng}&dest=${d.lat},${d.lng}&vehicle=${vehicle}`
    );

    if (!routeData.paths || !routeData.paths.length) {
      throw new Error("No route found.");
    }

    const path = routeData.paths[0];
    const distanceKm = path.distance / 1000;
    const distance = unit === "mi" ? kmToMiles(distanceKm) : distanceKm;
    const distUnit = unit === "mi" ? "mi" : "km";
    const timeMs = path.time;
    const hr = Math.floor(timeMs / 3600000);
    const min = Math.floor((timeMs % 3600000) / 60000);
    const sec = Math.floor((timeMs % 60000) / 1000);

    el("routeTitle").textContent = `Route: ${from} → ${to}`;
    el("routeDistance").textContent = `Distance: ${distance.toFixed(2)} ${distUnit}`;
    el("routeTime").textContent = `Duration: ${hr}h ${min}m ${sec}s`;
    el("routeVehicle").textContent = `Vehicle: ${vehicle}`;

    const tbody = el("instructionsTable").querySelector("tbody");
    path.instructions.forEach((instr) => {
      const dKm = instr.distance / 1000;
      const dVal = unit === "mi" ? kmToMiles(dKm) : dKm;
      const row = `<tr><td>${instr.text}</td><td>${dVal.toFixed(2)} ${distUnit}</td></tr>`;
      tbody.insertAdjacentHTML("beforeend", row);
    });

    el("output").hidden = false;
    showMessage("Route retrieved successfully.", "success");
  } catch (err) {
    console.error(err);
    showMessage("Error: " + err.message, "error");
  }
}

el("getRouteBtn").addEventListener("click", () => {
  const from = el("from").value.trim();
  const to = el("to").value.trim();
  const vehicle = el("vehicle").value;
  const unit = el("unit").value;

  if (!from || !to) {
    showMessage("Please fill both starting location and destination.", "error");
    return;
  }
  getRoute(from, to, vehicle, unit);
});

el("clearBtn").addEventListener("click", () => {
  el("from").value = "";
  el("to").value = "";
  el("instructionsTable").querySelector("tbody").innerHTML = "";
  el("output").hidden = true;
  hideMessage();
});
