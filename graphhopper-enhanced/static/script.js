let map;
let routeLayer;
let highlightLayer;

document.getElementById("routeForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const from = document.getElementById("from").value.trim();
  const to = document.getElementById("to").value.trim();
  const vehicle = document.getElementById("vehicle").value;
  const unit = document.getElementById("unit").value;

  const errorBox = document.getElementById("error");
  const results = document.getElementById("results");
  errorBox.classList.add("hidden");
  results.classList.add("hidden");

  try {
    const res = await fetch("/get_route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from, to, vehicle, unit }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Route not found");

    document.getElementById("distance").textContent = data.distance;
    document.getElementById("time").textContent = data.time;
    document.getElementById("vehicleType").textContent = data.vehicle;

    results.classList.remove("hidden");

    const coords = data.points.coordinates.map((p) => [p[1], p[0]]);
    showMap(coords);

    const instructionsDiv = document.getElementById("instructions");
    instructionsDiv.innerHTML = "<h3>Turn-by-Turn Instructions</h3>";

    data.instructions.forEach((step, i) => {
      const div = document.createElement("div");
      div.classList.add("instruction-box");
      div.dataset.interval = JSON.stringify(step.interval);
      div.innerHTML = `
        <p><strong>Step ${i + 1}:</strong> ${step.text}</p>
        <p class="small"><em>${step.distance}</em></p>
      `;
      instructionsDiv.appendChild(div);
    });

    document.querySelectorAll(".instruction-box").forEach((box) => {
      box.addEventListener("mouseenter", () =>
        highlightSegment(box.dataset.interval, coords)
      );
      box.addEventListener("mouseleave", removeHighlight);
    });

    loadAnalytics();
  } catch (err) {
    errorBox.textContent = `Error: ${err.message}`;
    errorBox.classList.remove("hidden");
  }
});

document.getElementById("clear").addEventListener("click", () => {
  document.getElementById("routeForm").reset();
  document.getElementById("results").classList.add("hidden");
  document.getElementById("error").classList.add("hidden");
  if (map && routeLayer) routeLayer.remove();
  if (highlightLayer) highlightLayer.remove();
});

function showMap(coords) {
  const start = coords[0];
  const end = coords[coords.length - 1];

  if (!map) {
    map = L.map("map").setView(start, 10);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);
  }

  if (routeLayer) routeLayer.remove();

  routeLayer = L.polyline(coords, { color: "blue", weight: 5 }).addTo(map);
  L.marker(start).addTo(map).bindPopup("Start");
  L.marker(end).addTo(map).bindPopup("Destination");
  map.fitBounds(routeLayer.getBounds(), { padding: [40, 40] });
}

function highlightSegment(intervalData, coords) {
  if (highlightLayer) highlightLayer.remove();
  const interval = JSON.parse(intervalData);
  const segmentCoords = coords.slice(interval[0], interval[1] + 1);
  highlightLayer = L.polyline(segmentCoords, { color: "yellow", weight: 8 }).addTo(map);
}

function removeHighlight() {
  if (highlightLayer) highlightLayer.remove();
}


async function loadAnalytics() {
  try {
    const res = await fetch("/analytics");
    const data = await res.json();

    const routeLabels = data.top_routes.map(r => r.route);
    const routeCounts = data.top_routes.map(r => r.count);
    const vehicleLabels = Object.keys(data.vehicle_usage);
    const vehicleCounts = Object.values(data.vehicle_usage);

    new Chart(document.getElementById("routeChart"), {
      type: "bar",
      data: {
        labels: routeLabels,
        datasets: [{
          label: "Most Frequent Routes",
          data: routeCounts
        }]
      }
    });

    new Chart(document.getElementById("vehicleChart"), {
      type: "pie",
      data: {
        labels: vehicleLabels,
        datasets: [{
          label: "Vehicle Usage",
          data: vehicleCounts
        }]
      }
    });

  } catch (err) {
    console.error("Analytics error:", err);
  }
}
