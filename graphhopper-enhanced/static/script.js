let map;
let routeLayer;

// Keep last route for saving
let lastRouteData = null;

// Elements
const results = document.getElementById("results");
const errorBox = document.getElementById("error");
const saveBtn = document.getElementById("saveRouteBtn");
const viewBtn = document.getElementById("viewFavoritesBtn");
const modalRoot = document.getElementById("modal-root");


// ===============================
//  SUBMIT: Get Route
// ===============================
document.getElementById("routeForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const from = document.getElementById("from").value.trim();
  const to = document.getElementById("to").value.trim();
  const vehicle = document.getElementById("vehicle").value;
  const unit = document.getElementById("unit").value;

  errorBox.classList.add("hidden");
  results.classList.add("hidden");
  saveBtn.classList.add("hidden");
  viewBtn.classList.add("hidden");

  try {
    const res = await fetch("/get_route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from, to, vehicle, unit }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Route not found");

    // Store last route for saving
    lastRouteData = { ...data, from, to, vehicle, unit };

    // Fill summary
    document.getElementById("distance").textContent = data.distance;
    document.getElementById("time").textContent = data.time;
    document.getElementById("vehicleType").textContent = data.vehicle;

    results.classList.remove("hidden");

    const coords = data.points.coordinates.map((p) => [p[1], p[0]]);
    showMap(coords);

    // Build instructions
    const instructionsDiv = document.getElementById("instructions");
    instructionsDiv.innerHTML = "<h3>Turn-by-Turn Instructions</h3>";

    data.instructions.forEach((step, i) => {
      const div = document.createElement("div");
      div.classList.add("instruction-box");
      div.innerHTML = `
        <p><strong>Step ${i + 1}:</strong> ${step.text}</p>
        <p class="small"><em>${step.distance}</em></p>
      `;
      instructionsDiv.appendChild(div);
    });

    // SHOW THE BUTTONS AFTER ROUTE IS LOADED
    saveBtn.classList.remove("hidden");
    viewBtn.classList.remove("hidden");

  } catch (err) {
    errorBox.textContent = `Error: ${err.message}`;
    errorBox.classList.remove("hidden");
  }
});


// ===============================
//  CLEAR
// ===============================
document.getElementById("clear").addEventListener("click", () => {
  document.getElementById("routeForm").reset();
  results.classList.add("hidden");
  errorBox.classList.add("hidden");
  saveBtn.classList.add("hidden");
  viewBtn.classList.add("hidden");

  lastRouteData = null;

  if (map && routeLayer) routeLayer.remove();
});


// ===============================
//  MAP
// ===============================
function showMap(coords) {
  const start = coords[0];

  if (!map) {
    map = L.map("map").setView(start, 10);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);
  }

  if (routeLayer) routeLayer.remove();
  routeLayer = L.polyline(coords, { color: "blue", weight: 5 }).addTo(map);
  map.fitBounds(routeLayer.getBounds(), { padding: [40, 40] });
}



// ===============================
//  SAVE FAVORITE ROUTE
// ===============================
saveBtn.addEventListener("click", async () => {
  const name = prompt("Name this route:");

  if (!name || !lastRouteData) return;

  const payload = {
    name,
    from: lastRouteData.from,
    to: lastRouteData.to,
    vehicle: lastRouteData.vehicle.toLowerCase(),
    unit: lastRouteData.unit,
    distance: lastRouteData.distance,
    time: lastRouteData.time,
  };

  const res = await fetch("/favorites", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const result = await res.json();

  if (!res.ok) {
    alert(result.error || "Failed to save route");
    return;
  }

  alert("Route saved!");
});



// ===============================
//  VIEW FAVORITES (Modal)
// ===============================
viewBtn.addEventListener("click", loadFavorites);

async function loadFavorites() {
  const res = await fetch("/favorites");
  const favorites = await res.json();

  showModal(`
    <h2>Saved Routes</h2>
    ${
      favorites.length === 0
        ? "<p>No saved routes yet.</p>"
        : favorites
            .map(
              (f) => `
      <div class="favorite-item">
        <strong>${f.name}</strong><br>
        <small>${f.origin} → ${f.destination}</small><br>
        <small>${f.distance}, ${f.time}</small><br>
        <button class="btn danger" onclick="deleteFavorite(${f.id})">
          Delete
        </button>
      </div>
    `
            )
            .join("")
    }
    <button class="btn primary" onclick="closeModal()">Close</button>
  `);
}



// ===============================
//  DELETE FAVORITE
// ===============================
async function deleteFavorite(id) {
  await fetch(`/favorites/${id}`, { method: "DELETE" });
  loadFavorites(); // reload list
}



// ===============================
//  MODAL FUNCTIONS
// ===============================
function showModal(html) {
  modalRoot.innerHTML = `
    <div class="modal">
      <div class="modal-content">
        ${html}
      </div>
    </div>
  `;
}

function closeModal() {
  modalRoot.innerHTML = "";
}

// Allow deleteFavorite from HTML
window.deleteFavorite = deleteFavorite;


// ===============================
//  SWAP LOCATIONS
// ===============================
const swapBtn = document.getElementById("swapBtn");

if (swapBtn) {
  swapBtn.addEventListener("click", () => {
    const fromInput = document.getElementById("from");
    const toInput = document.getElementById("to");

    // 1. Get current values
    const tempOrigin = fromInput.value;
    const tempDest = toInput.value;

    // 2. Swap them
    fromInput.value = tempDest;
    toInput.value = tempOrigin;

    // 3. Optional: Add a visual rotation effect via class
    swapBtn.style.transform = "rotate(180deg)";
    setTimeout(() => {
      swapBtn.style.transform = "rotate(0deg)";
    }, 300);
  });
}

// ===============================
//  ANALYTICS DASHBOARD
// ===============================
const analyticsBtn = document.getElementById("viewAnalyticsBtn");

if (analyticsBtn) {
  analyticsBtn.addEventListener("click", loadAnalytics);
}

async function loadAnalytics() {
  try {
    const res = await fetch("/analytics_data");
    const data = await res.json();

    // 1. Open Modal with Canvas elements for Chart.js
    showModal(`
      <h2 style="text-align:center; margin-bottom: 1.5rem;">Analytics Dashboard</h2>
      
      <div class="chart-container">
        <h3>Most Frequent Routes</h3>
        <canvas id="routesChart"></canvas>
      </div>

      <div class="chart-container" style="margin-top: 2rem;">
        <h3>Vehicle Preferences</h3>
        <canvas id="vehicleChart"></canvas>
      </div>

      <button class="btn primary" onclick="closeModal()" style="margin-top: 1.5rem; width: 100%;">Close</button>
    `);

    // 2. Render the charts (needs a slight delay for DOM to update)
    requestAnimationFrame(() => renderCharts(data));

  } catch (err) {
    console.error(err);
    alert("Could not load analytics data.");
  }
}

function renderCharts(data) {
  // Chart 1: Top Routes (Bar Chart)
  new Chart(document.getElementById("routesChart"), {
    type: "bar",
    data: {
      labels: data.top_routes.map(r => r.label),
      datasets: [{
        label: "Requests",
        data: data.top_routes.map(r => r.count),
        backgroundColor: "#00c6ff",
        borderRadius: 5
      }]
    },
    options: {
      responsive: true,
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
        x: { ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } }
      }
    }
  });

  // Chart 2: Vehicle Usage (Doughnut Chart)
  new Chart(document.getElementById("vehicleChart"), {
    type: "doughnut",
    data: {
      labels: data.vehicles.map(v => v.label.toUpperCase()),
      datasets: [{
        data: data.vehicles.map(v => v.count),
        backgroundColor: ["#ff6384", "#36a2eb", "#ffce56", "#4bc0c0"],
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom' }
      }
    }
  });
}