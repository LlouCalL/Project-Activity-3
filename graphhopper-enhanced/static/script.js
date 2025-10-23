const el = (id) => document.getElementById(id);

const showMessage = (text, type = 'info') => {
  const m = el('message');
  m.style.display = 'block';
  m.innerHTML =
    type === 'error'
      ? `<div class="error">${text}</div>`
      : type === 'success'
      ? `<div class="success">${text}</div>`
      : `<div>${text}</div>`;
};

const hideMessage = () => {
  el('message').style.display = 'none';
};

const kmToMiles = (km) => km / 1.61;

async function geocode(location, apiKey) {
  const url = `https://graphhopper.com/api/1/geocode?${new URLSearchParams({
    q: location,
    limit: 1,
    key: apiKey,
  })}`;
  const resp = await fetch(url);
  const json = await resp.json();
  return { status: resp.status, json };
}

async function getRoute(origLat, origLng, destLat, destLng, vehicle, apiKey) {
  const base = 'https://graphhopper.com/api/1/route?';
  const params = new URLSearchParams({ key: apiKey, vehicle });
  const points = `&point=${encodeURIComponent(
    origLat + ',' + origLng
  )}&point=${encodeURIComponent(destLat + ',' + destLng)}`;
  const url = base + params.toString() + points;
  const resp = await fetch(url);
  const json = await resp.json();
  return { status: resp.status, json };
}

el('getRouteBtn').addEventListener('click', async () => {
  hideMessage();
  el('output').hidden = true;
  el('instructionsTable').querySelector('tbody').innerHTML = '';

  const apiKey = el('apiKey').value.trim();
  const from = el('from').value.trim();
  const to = el('to').value.trim();
  const vehicle = el('vehicle').value;
  const unit = el('unit').value;

  if (!apiKey) {
    showMessage('Please enter your GraphHopper API key.', 'error');
    return;
  }
  if (!from || !to) {
    showMessage('Please fill both Starting Location and Destination.', 'error');
    return;
  }

  try {
    showMessage('Geocoding start location...');
    const g1 = await geocode(from, apiKey);
    if (g1.status !== 200 || !g1.json.hits.length) {
      showMessage('Error geocoding start location.', 'error');
      return;
    }
    const o = g1.json.hits[0];
    const origLat = o.point.lat;
    const origLng = o.point.lng;
    const origName = [o.name, o.state || '', o.country || '']
      .filter(Boolean)
      .join(', ');

    showMessage('Geocoding destination...');
    const g2 = await geocode(to, apiKey);
    if (g2.status !== 200 || !g2.json.hits.length) {
      showMessage('Error geocoding destination.', 'error');
      return;
    }
    const d = g2.json.hits[0];
    const destLat = d.point.lat;
    const destLng = d.point.lng;
    const destName = [d.name, d.state || '', d.country || '']
      .filter(Boolean)
      .join(', ');

    el('geocodeInfo').textContent = `From: ${origName} → To: ${destName}`;

    showMessage('Requesting route...');
    const routeResp = await getRoute(
      origLat,
      origLng,
      destLat,
      destLng,
      vehicle,
      apiKey
    );

    if (routeResp.status !== 200) {
      showMessage('Routing API failed: ' + routeResp.json.message, 'error');
      return;
    }

    const path = routeResp.json.paths[0];
    const distanceMeters = path.distance;
    const distanceKm = distanceMeters / 1000;
    const distanceDisplay =
      unit === 'mi'
        ? kmToMiles(distanceKm).toFixed(2) + ' mi'
        : distanceKm.toFixed(2) + ' km';

    const timeMs = path.time;
    const hr = Math.floor(timeMs / 3600000);
    const min = Math.floor((timeMs % 3600000) / 60000);
    const sec = Math.floor((timeMs % 60000) / 1000);

    el('routeTitle').textContent = `Route: ${from} → ${to}`;
    el('routeDistance').textContent = `Distance: ${distanceDisplay}`;
    el('routeTime').textContent = `Duration: ${hr}h ${min}m ${sec}s`;
    el('routeVehicle').textContent = `Vehicle: ${vehicle}`;

    const tbody = el('instructionsTable').querySelector('tbody');
    path.instructions.forEach((instr) => {
      const instrText = instr.text || '(no text)';
      const instrKm = instr.distance / 1000;
      const instrDist =
        unit === 'mi'
          ? kmToMiles(instrKm).toFixed(2) + ' mi'
          : instrKm.toFixed(2) + ' km';
      const row = `<tr><td>${instrText}</td><td>${instrDist}</td></tr>`;
      tbody.insertAdjacentHTML('beforeend', row);
    });

    el('output').hidden = false;
    showMessage('Route retrieved successfully.', 'success');
  } catch (err) {
    console.error(err);
    showMessage('Error: ' + err.message, 'error');
  }
});

el('clearBtn').addEventListener('click', () => {
  el('from').value = '';
  el('to').value = '';
  el('instructionsTable').querySelector('tbody').innerHTML = '';
  el('output').hidden = true;
  hideMessage();
});


