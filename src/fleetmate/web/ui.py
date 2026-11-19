"""Single-page responsive HTML/CSS/JS UI for FleetMate Portal."""

PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>FleetMate Portal — GeoLoc, Places &amp; Controls</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <style>
    :root {
      --bg: #0b111e;
      --panel: #131c2e;
      --panel-2: #19243a;
      --border: #263552;
      --text: #e6edf7;
      --muted: #8fa3c4;
      --accent: #3b82f6;
      --green: #10b981;
      --amber: #f59e0b;
      --red: #ef4444;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }
    a { color: #7db4ff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .container { max-width: 1400px; margin: 0 auto; padding: 16px; }
    header {
      display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between;
      background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px 18px;
      margin-bottom: 16px;
    }
    .title-group h1 { margin: 0; font-size: 1.25rem; display: flex; align-items: center; gap: 10px; }
    .sub { color: var(--muted); font-size: 0.85rem; margin-top: 2px; }
    .badge {
      display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 0.75rem; font-weight: 600;
      background: rgba(59,130,246,0.18); color: #93c5fd; border: 1px solid rgba(59,130,246,0.35);
    }
    .badge.ok { background: rgba(16,185,129,0.18); color: #6ee7b7; border-color: rgba(16,185,129,0.35); }
    .badge.warn { background: rgba(245,158,11,0.18); color: #fcd34d; border-color: rgba(245,158,11,0.35); }
    .nav-links { display: flex; flex-wrap: wrap; gap: 8px; }
    .nav-btn {
      background: var(--panel-2); color: var(--text); border: 1px solid var(--border);
      padding: 6px 11px; border-radius: 8px; font-size: 0.82rem; font-weight: 500;
    }
    .nav-btn:hover { border-color: var(--accent); text-decoration: none; }
    .kpis {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-bottom: 16px;
    }
    .kpi {
      background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px;
    }
    .kpi-label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
    .kpi-val { font-size: 1.35rem; font-weight: 700; margin-top: 4px; }
    .kpi-sub { font-size: 0.78rem; color: var(--muted); margin-top: 2px; }
    .tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    .tab-btn {
      background: var(--panel); color: var(--muted); border: 1px solid var(--border);
      padding: 8px 14px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.86rem;
    }
    .tab-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
    .tab-pane { display: none; }
    .tab-pane.active { display: block; }
    .grid-2 { display: grid; grid-template-columns: 1.35fr 1fr; gap: 16px; }
    @media (max-width: 960px) { .grid-2 { grid-template-columns: 1fr; } }
    .card {
      background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px;
      margin-bottom: 16px;
    }
    .card h2 { margin: 0 0 12px 0; font-size: 1rem; display: flex; justify-content: space-between; align-items: center; }
    #map { height: 470px; width: 100%; border-radius: 10px; border: 1px solid var(--border); background: #0f172a; }
    #map.dark-tiles .leaflet-tile-pane { filter: invert(92%) hue-rotate(180deg) brightness(95%) contrast(92%); }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 600; font-size: 0.76rem; text-transform: uppercase; }
    tr:hover td { background: rgba(255,255,255,0.02); }
    .table-wrap { overflow-x: auto; max-height: 460px; overflow-y: auto; }
    form.gf-form { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .full { grid-column: 1 / -1; }
    label { display: block; font-size: 0.76rem; color: var(--muted); margin-bottom: 4px; }
    input, select {
      width: 100%; padding: 8px 10px; border-radius: 7px; border: 1px solid var(--border);
      background: var(--bg); color: var(--text); font-size: 0.86rem;
    }
    button {
      padding: 7px 12px; border-radius: 7px; border: 1px solid var(--border); cursor: pointer;
      font-weight: 600; font-size: 0.82rem; background: var(--panel-2); color: var(--text);
    }
    button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
    button.danger { background: rgba(239,68,68,0.16); border-color: rgba(239,68,68,0.4); color: #fca5a5; }
    button:hover { opacity: 0.92; }
    .btn-row { display: flex; flex-wrap: wrap; gap: 8px; }
    .ctrl-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
    .ctrl-card { background: var(--panel-2); border: 1px solid var(--border); border-radius: 10px; padding: 12px; }
    .ctrl-card h3 { margin: 0 0 8px 0; font-size: 0.88rem; color: #cbd5e1; }
    .toast {
      position: fixed; right: 18px; bottom: 18px; background: #111827; color: #fff;
      border: 1px solid var(--accent); padding: 10px 14px; border-radius: 9px; font-size: 0.86rem;
      display: none; z-index: 9999; max-width: 380px; box-shadow: 0 10px 30px rgba(0,0,0,0.45);
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="title-group">
        <h1>
          <span id="carName">FleetMate</span>
          <span class="badge ok" id="stateBadge">loading</span>
          <span class="badge" id="geofenceBadge">No Geofence</span>
        </h1>
        <div class="sub" id="subline">Zero-dependency Fleet Telemetry Portal &bull; Imperial Units</div>
      </div>
      <div class="nav-links" id="grafanaLinks"></div>
    </header>

    <div class="kpis">
      <div class="kpi"><div class="kpi-label">Battery &amp; Range</div><div class="kpi-val" id="kpiBat">--</div><div class="kpi-sub" id="kpiRange">--</div></div>
      <div class="kpi"><div class="kpi-label">Odometer</div><div class="kpi-val" id="kpiOdo">--</div><div class="kpi-sub" id="kpiTrips">--</div></div>
      <div class="kpi"><div class="kpi-label">Temperatures</div><div class="kpi-val" id="kpiTemp">--</div><div class="kpi-sub" id="kpiTempSub">Inside / Outside</div></div>
      <div class="kpi"><div class="kpi-label">Tire Pressures</div><div class="kpi-val" id="kpiTpms">--</div><div class="kpi-sub">FL / FR / RL / RR (psi)</div></div>
      <div class="kpi"><div class="kpi-label">Energy &amp; Cost</div><div class="kpi-val" id="kpiEnergy">--</div><div class="kpi-sub" id="kpiCost">--</div></div>
    </div>

    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('geoloc', this)">GeoLoc Map &amp; Geo-Fences</button>
      <button class="tab-btn" onclick="switchTab('places', this)">Visited Places</button>
      <button class="tab-btn" onclick="switchTab('drives', this)">Recent Drives</button>
      <button class="tab-btn" onclick="switchTab('charges', this)">Recent Charges</button>
      <button class="tab-btn" onclick="switchTab('controls', this)">Remote Controls</button>
    </div>

    <div id="tab-geoloc" class="tab-pane active">
      <div class="grid-2">
        <div class="card">
          <h2>
            <span>Live Vehicle GeoLoc &amp; Geofences</span>
            <span class="btn-row">
              <button onclick="centerOnCar()">Center Vehicle</button>
              <button onclick="refreshAll()">Refresh</button>
            </span>
          </h2>
          <div id="map"></div>
          <div class="sub" style="margin-top:8px;">Tip: Click anywhere on the map to fill Latitude &amp; Longitude in the Geo-Fence editor.</div>
        </div>
        <div>
          <div class="card">
            <h2 id="gfFormTitle">Create / Edit Geo-Fence</h2>
            <form class="gf-form" onsubmit="saveGeofence(event)">
              <input type="hidden" id="gfId" />
              <div class="full">
                <label>Name</label>
                <input id="gfName" required placeholder="e.g. Casita, Office, Supercharger" />
              </div>
              <div>
                <label>Latitude</label>
                <input id="gfLat" type="number" step="0.000001" required />
              </div>
              <div>
                <label>Longitude</label>
                <input id="gfLon" type="number" step="0.000001" required />
              </div>
              <div>
                <label>Radius (meters)</label>
                <input id="gfRadius" type="number" min="5" max="5000" value="30" required />
              </div>
              <div>
                <label>Billing Type</label>
                <select id="gfBilling">
                  <option value="per_kwh">per_kwh ($/kWh)</option>
                  <option value="per_minute">per_minute ($/min)</option>
                </select>
              </div>
              <div>
                <label>Cost per Unit ($)</label>
                <input id="gfRate" type="number" step="0.0001" placeholder="0.1450" />
              </div>
              <div>
                <label>Session Fee ($)</label>
                <input id="gfFee" type="number" step="0.01" placeholder="0.00" />
              </div>
              <div class="full btn-row">
                <button type="submit" class="primary">Save Geo-Fence</button>
                <button type="button" onclick="useCarCoords()">Use Car GPS</button>
                <button type="button" onclick="resetGfForm()">Clear</button>
              </div>
            </form>
          </div>
          <div class="card">
            <h2><span>Configured Geo-Fences (<span id="gfCount">0</span>)</span></h2>
            <div class="table-wrap" style="max-height:240px;">
              <table>
                <thead><tr><th>Name</th><th>Radius</th><th>Rate</th><th>Actions</th></tr></thead>
                <tbody id="gfTableBody"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div id="tab-places" class="tab-pane">
      <div class="card">
        <h2>
          <span>Visited Places (<span id="placesCount">0</span>)</span>
          <input id="placeFilter" oninput="renderPlaces()" placeholder="Filter places..." style="max-width:240px;" />
        </h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Place / Address</th><th>City / State</th><th>Drives</th><th>Charges</th><th>kWh</th><th>Actions</th></tr></thead>
            <tbody id="placesTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div id="tab-drives" class="tab-pane">
      <div class="card">
        <h2>Recent Drives</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Date</th><th>Route</th><th>Distance</th><th>Duration</th><th>Max Speed</th><th>Outside Temp</th></tr></thead>
            <tbody id="drivesTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div id="tab-charges" class="tab-pane">
      <div class="card">
        <h2>Recent Charges</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Date</th><th>Location</th><th>Energy</th><th>SoC</th><th>Duration</th><th>Cost</th></tr></thead>
            <tbody id="chargesTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <div id="tab-controls" class="tab-pane">
      <div class="card">
        <h2>Tesla Fleet API Remote Controls <span class="badge warn">Commands: $0.001 | Wake: $0.02 ($10/mo free credit)</span></h2>
        <div class="ctrl-grid">
          <div class="ctrl-card">
            <h3>Access &amp; Security</h3>
            <div class="btn-row">
              <button onclick="sendCmd('lock')">Lock ($0.001)</button>
              <button onclick="sendCmd('unlock')">Unlock ($0.001)</button>
              <button onclick="sendCmd('sentry_on')">Sentry On</button>
              <button onclick="sendCmd('sentry_off')">Sentry Off</button>
              <button onclick="sendCmd('flash_lights')">Flash</button>
              <button onclick="sendCmd('honk_horn')">Honk</button>
              <button onclick="sendCmd('wake')">Wake ($0.02)</button>
            </div>
          </div>
          <div class="ctrl-card">
            <h3>Closures &amp; Windows</h3>
            <div class="btn-row">
              <button onclick="sendCmd('windows_vent')">Vent Windows</button>
              <button onclick="sendCmd('windows_close')">Close Windows</button>
              <button onclick="sendCmd('open_frunk')">Open Frunk</button>
              <button onclick="sendCmd('open_trunk')">Open Trunk</button>
            </div>
          </div>
          <div class="ctrl-card">
            <h3>Climate &amp; Heaters</h3>
            <div class="btn-row" style="margin-bottom:8px;">
              <button onclick="sendCmd('climate_on')">Climate On</button>
              <button onclick="sendCmd('climate_off')">Climate Off</button>
              <button onclick="sendCmd('wheel_heater_on')">Wheel Heater On</button>
              <button onclick="sendCmd('wheel_heater_off')">Wheel Heater Off</button>
            </div>
            <div class="btn-row" style="margin-bottom:8px;">
              <input id="tempInput" type="number" min="59" max="86" value="70" style="width:80px;" />
              <button class="primary" onclick="sendCmd('climate_temp_f', Number(document.getElementById('tempInput').value))">Set &deg;F</button>
            </div>
            <div class="btn-row">
              <button onclick="sendCmd('seat_heater_driver', 3)">Driver Seat 3</button>
              <button onclick="sendCmd('seat_heater_driver', 0)">Driver Off</button>
              <button onclick="sendCmd('seat_heater_passenger', 3)">Pass Seat 3</button>
              <button onclick="sendCmd('seat_heater_passenger', 0)">Pass Off</button>
            </div>
          </div>
          <div class="ctrl-card">
            <h3>Charging &amp; Software</h3>
            <div class="btn-row" style="margin-bottom:8px;">
              <button onclick="sendCmd('charge_start')">Start Charge</button>
              <button onclick="sendCmd('charge_stop')">Stop Charge</button>
              <button onclick="sendCmd('charge_port_open')">Open Port</button>
              <button onclick="sendCmd('charge_port_close')">Close Port</button>
            </div>
            <div class="btn-row" style="margin-bottom:8px;">
              <input id="limitInput" type="number" min="50" max="100" value="80" style="width:74px;" />
              <button onclick="sendCmd('charge_limit', Number(document.getElementById('limitInput').value))">Limit %</button>
              <input id="ampsInput" type="number" min="5" max="48" value="32" style="width:74px;" />
              <button onclick="sendCmd('charge_amps', Number(document.getElementById('ampsInput').value))">Amps A</button>
            </div>
            <button onclick="sendCmd('schedule_software_update')">Schedule SW Update</button>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="toast" id="toast"></div>

  <script>
    const KM_TO_MI = 0.621371;
    const BAR_TO_PSI = 14.5038;
    const cToF = (c) => c == null ? null : (c * 9 / 5 + 32);
    const esc = (s) => String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));

    let state = { snapshot: null, geofences: [], places: [], drives: [], charges: [], positions: [] };
    let map, carMarker, pathLayer, gfLayer, placesLayer;
    let mapCenteredOnce = false;

    function toast(msg) {
      const el = document.getElementById('toast');
      el.textContent = msg;
      el.style.display = 'block';
      clearTimeout(toast._t);
      toast._t = setTimeout(() => { el.style.display = 'none'; }, 4200);
    }

    function switchTab(id, btn) {
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + id).classList.add('active');
      if (btn) btn.classList.add('active');
      if (id === 'geoloc' && map) setTimeout(() => map.invalidateSize(), 120);
    }

    function initMap() {
      const mapEl = document.getElementById('map');
      mapEl.classList.add('dark-tiles');
      map = L.map('map').setView([26.087, -80.248], 13);

      const darkStreets = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        { attribution: '&copy; Esri &amp; Contributors', maxNativeZoom: 18, maxZoom: 20 }
      );
      const dayStreets = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        { attribution: '&copy; Esri &amp; Contributors', maxNativeZoom: 18, maxZoom: 20 }
      );
      const darkGray = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
        { attribution: '&copy; Esri', maxNativeZoom: 16, maxZoom: 20 }
      );
      const satellite = L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        { attribution: '&copy; Esri &amp; Earthstar Geographics', maxNativeZoom: 18, maxZoom: 20 }
      );

      pathLayer = L.layerGroup().addTo(map);
      gfLayer = L.layerGroup().addTo(map);
      placesLayer = L.layerGroup().addTo(map);

      darkStreets.addTo(map);
      L.control.layers({
        'Dark Streets': darkStreets,
        'Dark Gray': darkGray,
        'Street Map': dayStreets,
        'Satellite': satellite
      }, {
        'Latest Drive Track': pathLayer,
        'Geo-Fences': gfLayer,
        'Visited Places': placesLayer
      }).addTo(map);

      map.on('baselayerchange', (e) => {
        mapEl.classList.toggle('dark-tiles', e.name === 'Dark Streets');
      });
      map.on('click', (e) => {
        document.getElementById('gfLat').value = e.latlng.lat.toFixed(6);
        document.getElementById('gfLon').value = e.latlng.lng.toFixed(6);
        toast('Map coordinates selected: ' + e.latlng.lat.toFixed(5) + ', ' + e.latlng.lng.toFixed(5));
      });
    }

    async function api(path, opts = {}) {
      const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || data.message || ('HTTP ' + res.status));
      return data;
    }

    async function refreshAll() {
      try {
        const [snap, gf, pl, dr, ch] = await Promise.all([
          api('/api/snapshot'),
          api('/api/geofences'),
          api('/api/places'),
          api('/api/drives'),
          api('/api/charges'),
        ]);
        state.snapshot = snap;
        state.geofences = gf.geofences || [];
        state.places = pl.places || [];
        state.drives = dr.drives || [];
        state.charges = ch.charges || [];
        renderAll();
      } catch (err) {
        toast('Refresh error: ' + err.message);
      }
    }

    function renderAll() {
      const snap = state.snapshot || {};
      const car = snap.car || {};
      const pos = snap.position || {};
      const cnt = snap.counts || {};
      document.getElementById('carName').textContent = car.name || 'FleetMate';
      document.getElementById('stateBadge').textContent = snap.live_state || 'online';
      document.getElementById('geofenceBadge').textContent = (snap.matched_geofence && snap.matched_geofence.name) || 'Away';

      const gBase = (snap.grafana_url || '').replace(/\\/$/, '');
      if (gBase) {
        document.getElementById('grafanaLinks').innerHTML = [
          ['Visited', '/d/RG_DxSmgk/visited'],
          ['Locations', '/d/ZzhF-aRWz/locations'],
          ['Drives', '/d/Y8upc6ZRk/drives'],
          ['Charges', '/d/TSmNYvRRk/charges'],
          ['Executive TCO', '/d/tesla-tco-executive/428a7be']
        ].map(([label, p]) => `<a class="nav-btn" target="_blank" rel="noopener" href="${esc(gBase + p)}">${esc(label)}</a>`).join('');
      }

      document.getElementById('kpiBat').textContent = pos.battery_level != null ? `${pos.battery_level}%` : '--';
      const idealMi = pos.ideal_battery_range_km != null ? Math.round(pos.ideal_battery_range_km * KM_TO_MI) : '--';
      const ratedMi = pos.rated_battery_range_km != null ? Math.round(pos.rated_battery_range_km * KM_TO_MI) : '--';
      document.getElementById('kpiRange').textContent = `Ideal ${idealMi} mi / Rated ${ratedMi} mi`;

      document.getElementById('kpiOdo').textContent = pos.odometer != null ? `${Math.round(pos.odometer * KM_TO_MI).toLocaleString()} mi` : '--';
      const totalMi = cnt.total_km != null ? Math.round(cnt.total_km * KM_TO_MI).toLocaleString() : '0';
      document.getElementById('kpiTrips').textContent = `${cnt.drives_count || 0} drives (${totalMi} mi) / ${cnt.charges_count || 0} charges`;

      const inF = cToF(pos.inside_temp);
      const outF = cToF(pos.outside_temp);
      document.getElementById('kpiTemp').textContent = `${inF != null ? inF.toFixed(0) + '°F' : '--'} / ${outF != null ? outF.toFixed(0) + '°F' : '--'}`;

      const t = [pos.tpms_pressure_fl, pos.tpms_pressure_fr, pos.tpms_pressure_rl, pos.tpms_pressure_rr]
        .map(v => v != null ? Math.round(v * BAR_TO_PSI) : '--');
      document.getElementById('kpiTpms').textContent = t.join(' / ');

      document.getElementById('kpiEnergy').textContent = `${Number(cnt.total_kwh || 0).toFixed(1)} kWh`;
      document.getElementById('kpiCost').textContent = `Logged cost: $${Number(cnt.total_cost || 0).toFixed(2)}`;

      renderMap();
      renderGeofences();
      renderPlaces();
      renderDrives();
      renderCharges();
    }

    function renderMap() {
      if (!map) return;
      pathLayer.clearLayers();
      gfLayer.clearLayers();
      placesLayer.clearLayers();

      const positions = ((state.snapshot && state.snapshot.positions) || []).filter(
        p => p.latitude != null && p.longitude != null
      );
      let segment = [];
      let prev = null;
      const flushSegment = () => {
        if (segment.length > 1) {
          L.polyline(segment, { color: '#3b82f6', weight: 3.5, opacity: 0.8 }).addTo(pathLayer);
        }
        segment = [];
      };
      for (const p of positions) {
        if (prev) {
          const dtMs = Math.abs(new Date(p.date) - new Date(prev.date));
          const dLat = Math.abs(p.latitude - prev.latitude);
          const dLon = Math.abs(p.longitude - prev.longitude);
          if (p.drive_id !== prev.drive_id || dtMs > 180000 || dLat > 0.025 || dLon > 0.025) {
            flushSegment();
          }
        }
        segment.push([p.latitude, p.longitude]);
        prev = p;
      }
      flushSegment();

      const pos = state.snapshot && state.snapshot.position;
      if (pos && pos.latitude != null && pos.longitude != null) {
        if (carMarker) map.removeLayer(carMarker);
        carMarker = L.circleMarker([pos.latitude, pos.longitude], {
          radius: 9, color: '#ffffff', weight: 2, fillColor: '#10b981', fillOpacity: 0.95
        }).addTo(map).bindPopup(`<b>${esc((state.snapshot.car && state.snapshot.car.name) || 'Vehicle')}</b><br/>Battery: ${pos.battery_level ?? '--'}%`);
        if (!mapCenteredOnce) {
          map.setView([pos.latitude, pos.longitude], 14);
          mapCenteredOnce = true;
        }
      }

      state.geofences.forEach(g => {
        L.circle([g.latitude, g.longitude], {
          radius: Number(g.radius || 25),
          color: '#f59e0b', fillColor: '#f59e0b', fillOpacity: 0.16, weight: 2
        }).addTo(gfLayer).bindPopup(`<b>Geo-Fence: ${esc(g.name)}</b><br/>Radius: ${g.radius} m`);
      });

      state.places.slice(0, 60).forEach(p => {
        L.circleMarker([p.latitude, p.longitude], {
          radius: 4, color: '#60a5fa', fillColor: '#60a5fa', fillOpacity: 0.65, weight: 1
        }).addTo(placesLayer).bindPopup(`<b>${esc(p.name || p.display_name)}</b><br/>Drives: ${p.drive_visits}, Charges: ${p.charge_visits}`);
      });
    }

    function centerOnCar() {
      const pos = state.snapshot && state.snapshot.position;
      if (pos && pos.latitude != null) map.setView([pos.latitude, pos.longitude], 15);
    }

    function renderGeofences() {
      document.getElementById('gfCount').textContent = state.geofences.length;
      document.getElementById('gfTableBody').innerHTML = state.geofences.map(g => {
        const rate = g.cost_per_unit != null ? `$${Number(g.cost_per_unit).toFixed(4)}/${g.billing_type === 'per_minute' ? 'min' : 'kWh'}` : '--';
        return `<tr>
          <td><a href="#" onclick="focusMap(${g.latitude},${g.longitude});return false;">${esc(g.name)}</a></td>
          <td>${g.radius} m</td>
          <td>${rate}</td>
          <td class="btn-row">
            <button onclick='editGeofence(${JSON.stringify(g)})'>Edit</button>
            <button class="danger" onclick="deleteGeofence(${g.id})">Del</button>
          </td>
        </tr>`;
      }).join('');
    }

    function focusMap(lat, lon) {
      switchTab('geoloc', document.querySelector('.tab-btn'));
      map.setView([lat, lon], 16);
    }

    function useCarCoords() {
      const pos = state.snapshot && state.snapshot.position;
      if (!pos || pos.latitude == null) return toast('No GPS coordinates available');
      document.getElementById('gfLat').value = Number(pos.latitude).toFixed(6);
      document.getElementById('gfLon').value = Number(pos.longitude).toFixed(6);
    }

    function editGeofence(g) {
      document.getElementById('gfFormTitle').textContent = 'Edit Geo-Fence #' + g.id;
      document.getElementById('gfId').value = g.id;
      document.getElementById('gfName').value = g.name || '';
      document.getElementById('gfLat').value = g.latitude;
      document.getElementById('gfLon').value = g.longitude;
      document.getElementById('gfRadius').value = g.radius || 25;
      document.getElementById('gfBilling').value = g.billing_type || 'per_kwh';
      document.getElementById('gfRate').value = g.cost_per_unit ?? '';
      document.getElementById('gfFee').value = g.session_fee ?? '';
      focusMap(g.latitude, g.longitude);
    }

    function resetGfForm() {
      document.getElementById('gfFormTitle').textContent = 'Create / Edit Geo-Fence';
      document.getElementById('gfId').value = '';
      document.getElementById('gfName').value = '';
      document.getElementById('gfRate').value = '';
      document.getElementById('gfFee').value = '';
    }

    async function saveGeofence(ev) {
      ev.preventDefault();
      const id = document.getElementById('gfId').value;
      const rateRaw = document.getElementById('gfRate').value;
      const feeRaw = document.getElementById('gfFee').value;
      const payload = {
        name: document.getElementById('gfName').value.trim(),
        latitude: Number(document.getElementById('gfLat').value),
        longitude: Number(document.getElementById('gfLon').value),
        radius: Number(document.getElementById('gfRadius').value),
        billing_type: document.getElementById('gfBilling').value,
        cost_per_unit: rateRaw === '' ? null : Number(rateRaw),
        session_fee: feeRaw === '' ? null : Number(feeRaw),
      };
      try {
        if (id) {
          await api('/api/geofences/' + id, { method: 'PUT', body: JSON.stringify(payload) });
          toast('Geo-Fence updated');
        } else {
          await api('/api/geofences', { method: 'POST', body: JSON.stringify(payload) });
          toast('Geo-Fence created');
        }
        resetGfForm();
        await refreshAll();
      } catch (err) {
        toast('Save failed: ' + err.message);
      }
    }

    async function deleteGeofence(id) {
      if (!confirm('Delete geo-fence #' + id + '?')) return;
      try {
        await api('/api/geofences/' + id, { method: 'DELETE' });
        toast('Geo-Fence deleted');
        await refreshAll();
      } catch (err) {
        toast('Delete failed: ' + err.message);
      }
    }

    function prefillPlaceGeofence(p) {
      switchTab('geoloc', document.querySelector('.tab-btn'));
      resetGfForm();
      document.getElementById('gfName').value = p.name || p.city || 'Place';
      document.getElementById('gfLat').value = Number(p.latitude).toFixed(6);
      document.getElementById('gfLon').value = Number(p.longitude).toFixed(6);
      map.setView([p.latitude, p.longitude], 16);
    }

    function renderPlaces() {
      const q = (document.getElementById('placeFilter').value || '').toLowerCase();
      const filtered = state.places.filter(p =>
        !q || (p.display_name || '').toLowerCase().includes(q) || (p.name || '').toLowerCase().includes(q) || (p.city || '').toLowerCase().includes(q)
      );
      document.getElementById('placesCount').textContent = filtered.length;
      document.getElementById('placesTableBody').innerHTML = filtered.map(p => `<tr>
        <td><b>${esc(p.name || p.display_name)}</b><div class="sub">${esc(p.display_name)}</div></td>
        <td>${esc([p.city, p.state].filter(Boolean).join(', '))}</td>
        <td>${p.drive_visits}</td>
        <td>${p.charge_visits}</td>
        <td>${Number(p.total_kwh || 0).toFixed(1)}</td>
        <td class="btn-row">
          <button onclick="focusMap(${p.latitude},${p.longitude})">Map</button>
          <button class="primary" onclick='prefillPlaceGeofence(${JSON.stringify(p)})'>+ Geo-Fence</button>
        </td>
      </tr>`).join('');
    }

    function renderDrives() {
      document.getElementById('drivesTableBody').innerHTML = state.drives.map(d => {
        const mi = d.distance != null ? (Number(d.distance) * KM_TO_MI).toFixed(1) + ' mi' : '--';
        const mph = d.speed_max != null ? Math.round(Number(d.speed_max) * KM_TO_MI) + ' mph' : '--';
        const tempF = d.outside_temp_avg != null ? cToF(Number(d.outside_temp_avg)).toFixed(0) + '°F' : '--';
        return `<tr>
          <td>${esc((d.start_date || '').replace('T', ' ').slice(0, 16))}</td>
          <td>${esc(d.start_location)} &rarr; ${esc(d.end_location)}</td>
          <td>${mi}</td>
          <td>${d.duration_min ?? '--'} min</td>
          <td>${mph}</td>
          <td>${tempF}</td>
        </tr>`;
      }).join('');
    }

    function renderCharges() {
      document.getElementById('chargesTableBody').innerHTML = state.charges.map(c => `<tr>
        <td>${esc((c.start_date || '').replace('T', ' ').slice(0, 16))}</td>
        <td>${esc(c.location)}</td>
        <td>${Number(c.charge_energy_added || 0).toFixed(2)} kWh</td>
        <td>${c.start_battery_level ?? '--'}% &rarr; ${c.end_battery_level ?? '--'}%</td>
        <td>${c.duration_min ?? '--'} min</td>
        <td>$${Number(c.cost || 0).toFixed(2)}</td>
      </tr>`).join('');
    }

    async function sendCmd(action, value = null) {
      try {
        toast('Sending ' + action + '...');
        const res = await api('/api/command', {
          method: 'POST',
          body: JSON.stringify({ action, value })
        });
        toast((res.ok ? 'OK: ' : 'ERR: ') + (res.message || action));
      } catch (err) {
        toast('Command error: ' + err.message);
      }
    }

    initMap();
    refreshAll();
    setInterval(refreshAll, 30000);
  </script>
</body>
</html>
"""
