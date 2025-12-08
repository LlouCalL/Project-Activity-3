let routeChartInstance = null;
let vehicleChartInstance = null;

async function loadAnalytics() {
    try {
        const res = await fetch("/analytics");
        const data = await res.json();

        // ----- ROUTE FREQUENCY (BAR CHART) -----
        const routeLabels = data.top_routes.map(r => r.route);
        const routeCounts = data.top_routes.map(r => r.count);

        if (routeChartInstance) routeChartInstance.destroy();
        routeChartInstance = new Chart(document.getElementById("routeChart"), {
            type: "bar",
            data: {
                labels: routeLabels,
                datasets: [{
                    label: "Most Frequent Routes",
                    data: routeCounts,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: true } }
            }
        });

        // ----- VEHICLE USAGE (PIE CHART) -----
        const vehicleLabels = Object.keys(data.vehicle_usage);
        const vehicleCounts = Object.values(data.vehicle_usage);

        if (vehicleChartInstance) vehicleChartInstance.destroy();
        vehicleChartInstance = new Chart(document.getElementById("vehicleChart"), {
            type: "pie",
            data: {
                labels: vehicleLabels,
                datasets: [{
                    label: "Vehicle Usage",
                    data: vehicleCounts
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: "bottom" } }
            }
        });

    } catch (err) {
        console.error("Analytics error:", err);
    }
}

// Load analytics on page load
window.onload = loadAnalytics;
