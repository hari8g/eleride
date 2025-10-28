import Chart from 'chart.js/auto';

const API = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL)
  || (typeof window !== 'undefined' && window.__API_URL__)
  || 'http://localhost:8000';

async function health() {
  try {
    const res = await fetch(`${API}/healthz`);
    const data = await res.json();
    return data.status || 'unknown';
  } catch (e) {
    return 'unreachable';
  }
}

async function fetchJobs() {
  const res = await fetch(`${API}/jobs?limit=100`);
  if (!res.ok) return [];
  return res.json();
}

async function fetchStores() {
  const res = await fetch(`${API}/stores/`);
  if (!res.ok) return [];
  return res.json();
}

async function fetchStoreSummary(store) {
  const res = await fetch(`${API}/stores/${encodeURIComponent(store)}/summary`);
  if (!res.ok) return null;
  return res.json();
}

function renderStatus(text) {
  const el = document.getElementById('status');
  el.textContent = `Backend status: ${text}`;
}

function renderJobsTable(jobs) {
  const tbody = document.querySelector('#jobs-table tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  jobs.forEach(j => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${j.id}</td>
      <td>${j.external_job_id}</td>
      <td>${new Date(j.timestamp).toLocaleString()}</td>
      <td>${j.energy_kwh?.toFixed?.(2) ?? ''}</td>
      <td>${j.price_usd != null ? j.price_usd.toFixed(2) : ''}</td>
      <td>${j.zone ?? ''}</td>
    `;
    tbody.appendChild(tr);
  });
}

let chart;
function renderZoneChart(jobs) {
  const el = document.getElementById('zone-chart');
  if (!el) return;
  const counts = {};
  jobs.forEach(j => {
    const z = j.zone ?? 'NA';
    counts[z] = (counts[z] || 0) + 1;
  });
  const labels = Object.keys(counts);
  const data = labels.map(l => counts[l]);
  if (chart) chart.destroy();
  chart = new Chart(el, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Jobs', data, backgroundColor: '#3b82f6' }] },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
  });
}

// Demand tab
let demandChart;
async function fetchDemand(city) {
  const res = await fetch(`${API}/demand/forecast?city=${encodeURIComponent(city)}`);
  if (!res.ok) return {};
  return res.json();
}

async function fetchInsights(city) {
  const res = await fetch(`${API}/demand/insights?city=${encodeURIComponent(city)}`);
  if (!res.ok) return {};
  return res.json();
}

function renderDemandTable(rows) {
  const tbody = document.querySelector('#demand-table tbody');
  tbody.innerHTML = '';
  rows.forEach(r => {
    const tr = document.createElement('tr');
    const score = Number(r.demand_score || 0);
    const color = r.color || (score >= 70 ? 'green' : score >= 55 ? 'yellow' : 'red');
    const p25 = Number(r.p25 || 0).toLocaleString('en-IN');
    const p75 = Number(r.p75 || 0).toLocaleString('en-IN');
    const earn = Number(r.store_earning_index || 0).toLocaleString('en-IN');
    const ramp = Number(r.new_rider_ramp_score || 0).toLocaleString('en-IN');
    tr.className = 'table-sm';
    tr.innerHTML = `
      <td>
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="dot ${color}"></span>
          <div>
            <div style="font-weight:600;">${r.store}</div>
            <div class="badge">Shift: ${r.best_shift}</div>
          </div>
        </div>
      </td>
      <td style="min-width:160px;">
        <div style="display:flex; align-items:center; gap:8px;">
          <div class="bar" style="flex:1;">
            <div class="bar-fill" style="width:${score}%;"></div>
          </div>
          <div style="width:40px; text-align:right;">${score}</div>
        </div>
        <div style="opacity:.7; font-size:12px;">${r.stars}</div>
      </td>
      <td><span class="chip">₹${p25} – ₹${p75}</span></td>
      <td>₹${earn}</td>
      <td>₹${ramp}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderDemandChart(rows) {
  const el = document.getElementById('demand-chart');
  if (!el) return;
  const labels = rows.map(r => r.store);
  const data = rows.map(r => r.demand_score);
  if (demandChart) demandChart.destroy();
  demandChart = new Chart(el, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Demand Score', data, backgroundColor: '#10b981' }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, max: 100 } } }
  });
}

function renderTopStoreCard(rows) {
  const card = document.getElementById('top-store-card');
  if (!card) return;
  if (!rows || !rows.length) { card.innerHTML = '<div>No data</div>'; return; }
  const [top] = rows;
  const score = Number(top.demand_score || 0);
  const color = top.color || (score >= 70 ? 'green' : score >= 55 ? 'yellow' : 'red');
  const p25 = Number(top.p25 || 0).toLocaleString('en-IN');
  const p75 = Number(top.p75 || 0).toLocaleString('en-IN');
  card.innerHTML = `
    <div style="display:flex; align-items:center; gap:12px;">
      <span class="dot ${color}"></span>
      <div>
        <div style="font-weight:700; font-size:18px;">Top Store: ${top.store}</div>
        <div class="badge">Best Shift: ${top.best_shift}</div>
      </div>
    </div>
    <div style="display:flex; align-items:center; gap:16px;">
      <div>
        <div style="font-weight:600;">Demand Score</div>
        <div style="display:flex; gap:8px; align-items:center; min-width:220px;">
          <div class="bar" style="flex:1;">
            <div class="bar-fill" style="width:${score}%;"></div>
          </div>
          <div>${score} ${top.stars || ''}</div>
        </div>
      </div>
      <div>
        <div style="font-weight:600;">Weekly INR</div>
        <div class="chip">₹${p25} – ₹${p75}</div>
      </div>
    </div>
  `;
}

async function initDemandTab() {
  const res = await fetch(`${API}/demand/forecast`);
  if (!res.ok) return;
  const data = await res.json();
  const cities = Object.keys(data);
  const sel = document.getElementById('city-select');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const [obj, ext] = await Promise.all([fetchDemand(city), fetchInsights(city)]);
    const rows = obj[city] || [];
    const extRows = ext[city] || rows;
    renderDemandTable(rows);
    renderDemandChart(rows.slice(0, 12));
    renderTopStoreCard(rows);
    const pick = (rows && rows[0]) ? rows[0] : (extRows[0] || null);
    if (pick) {
      document.getElementById('insights-store').textContent = pick.store;
      const findRow = (arr, store) => (arr || []).find(r => r.store === store) || {};
      const ir = findRow(extRows, pick.store);
      const fmt = (v) => v == null ? '—' : (typeof v === 'number' ? Number(v).toLocaleString('en-IN') : v);
      document.getElementById('ins-orders-per-rider').textContent = fmt(ir.orders_per_rider_week);
      document.getElementById('ins-idle').textContent = fmt(ir.idle_time_risk);
      document.getElementById('ins-reco').textContent = fmt(ir.recommended_riders_day);
      document.getElementById('ins-riders-week').textContent = fmt(ir.riders_week);
      document.getElementById('ins-playbook').textContent = ir.playbook || '—';
    }
    const list = document.getElementById('insights-list');
    list.innerHTML = '';
    (extRows || []).forEach(r => {
      const score = Number(r.demand_score || 0);
      const color = r.color || (score >= 70 ? 'green' : score >= 55 ? 'yellow' : 'red');
      const item = document.createElement('div');
      item.style.border = '1px solid #e5e7eb';
      item.style.borderRadius = '8px';
      item.style.padding = '8px';
      item.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="dot ${color}"></span>
            <div style="font-weight:600;">${r.store}</div>
          </div>
          <div style="display:flex; align-items:center; gap:8px; min-width:220px;">
            <div class="bar" style="flex:1;">
              <div class="bar-fill" style="width:${score || 0}%"></div>
            </div>
            <div>${score || '—'} ${r.stars || ''}</div>
          </div>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:6px;">
          <span class="chip">Shift: ${r.best_shift || '—'}</span>
          <span class="chip">Orders/Rider (week): ${r.orders_per_rider_week ?? '—'}</span>
          <span class="chip">Idle Risk: ${r.idle_time_risk ?? '—'}</span>
          <span class="chip">Reco Riders/day: ${r.recommended_riders_day ?? '—'}</span>
          <span class="chip">Riders/week: ${r.riders_week ?? '—'}</span>
          <span class="chip">INR P25–P75: ₹${(r.p25 ?? 0).toLocaleString('en-IN')} – ₹${(r.p75 ?? 0).toLocaleString('en-IN')}</span>
        </div>
        <div style="opacity:.8; margin-top:6px;">${r.playbook || ''}</div>
      `;
      list.appendChild(item);
    });
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// 3PL tab
let threeplChart;
function renderThreeplTable(rows) {
  const tbody = document.querySelector('#threepl-table tbody');
  tbody.innerHTML = '';
  const targetPerRider = 22;
  const assumedPayoutPerOrder = 200; // INR
  const daysPerWeek = 6.5;
  rows.forEach(r => {
    const tr = document.createElement('tr');
    let ordersDay = r.orders_per_day ?? null;
    if (ordersDay == null && r.store_earning_index != null) {
      ordersDay = (Number(r.store_earning_index) / assumedPayoutPerOrder) / daysPerWeek;
    }
    let reco = r.recommended_riders_day ?? null;
    if (reco == null && ordersDay != null) {
      reco = ordersDay / targetPerRider;
    }
    const current = r.riders_week ? (Number(r.riders_week)/daysPerWeek) : null;
    const gap = (reco != null && current != null) ? (reco - current) : null;
    tr.innerHTML = `
      <td>${r.store}</td>
      <td>${r.demand_score ?? '—'}</td>
      <td>${ordersDay != null ? Number(ordersDay).toFixed(1) : '—'}</td>
      <td>${reco != null ? Number(reco).toFixed(1) : '—'}</td>
      <td>${current != null ? current.toFixed(1) : '—'}</td>
      <td>${gap != null ? gap.toFixed(1) : '—'}</td>
      <td>${r.best_shift || '—'}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderThreeplChart(rows) {
  const el = document.getElementById('threepl-chart');
  const targetPerRider = 22;
  const assumedPayoutPerOrder = 200;
  const daysPerWeek = 6.5;
  const data = rows.map(r => {
    let ordersDay = r.orders_per_day ?? null;
    if (ordersDay == null && r.store_earning_index != null) {
      ordersDay = (Number(r.store_earning_index) / assumedPayoutPerOrder) / daysPerWeek;
    }
    let reco = r.recommended_riders_day ?? null;
    if (reco == null && ordersDay != null) {
      reco = ordersDay / targetPerRider;
    }
    const current = r.riders_week ? (Number(r.riders_week)/daysPerWeek) : null;
    return (reco != null && current != null) ? (reco - current) : 0;
  });
  if (threeplChart) threeplChart.destroy();
  threeplChart = new Chart(el, {
    type: 'bar',
    data: { labels: rows.map(r => r.store), datasets: [{ label: 'Capacity gap (riders/day)', data, backgroundColor: '#f59e0b' }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
  });
}

async function initThreeplTab() {
  const res = await fetch(`${API}/demand/insights`);
  if (!res.ok) return;
  const data = await res.json();
  const cities = Object.keys(data);
  const sel = document.getElementById('city-select-3pl');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const r = await fetch(`${API}/demand/insights?city=${encodeURIComponent(city)}`);
    const obj = r.ok ? await r.json() : {};
    const rows = obj[city] || [];
    renderThreeplTable(rows);
    renderThreeplChart(rows);
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// Incentives & Payouts tabs (read from /analytics/pack)
async function fetchPack(city) {
  const r = await fetch(`${API}/analytics/pack?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

let incChart, payChart;
async function initIncentivesTab() {
  const all = await fetch(`${API}/analytics/pack`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-inc');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchPack(city);
    const rows = (obj[city]?.incentives) || [];
    const tbody = document.querySelector('#inc-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.store}</td>
        <td>₹${Number(r.base_pay||0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.incentive_total||0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.surge_payout||0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.peak_hour_payout||0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.minimum_guarantee||0).toLocaleString('en-IN')}</td>
      `;
      tbody.appendChild(tr);
    });
    const labels = rows.map(r => r.store);
    const dataset = rows.map(r => Number(r.incentive_total||0));
    const ctx = document.getElementById('inc-chart');
    if (incChart) incChart.destroy();
    incChart = new Chart(ctx, { type:'bar', data:{ labels, datasets:[{ label:'Incentives (₹)', data:dataset, backgroundColor:'#8b5cf6'}] }, options:{ indexAxis:'y', plugins:{legend:{display:false}}}});
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

async function initPayoutsTab() {
  const all = await fetch(`${API}/analytics/pack`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-pay');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchPack(city);
    const rows = (obj[city]?.payouts) || [];
    const tbody = document.querySelector('#pay-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.store}</td>
        <td>₹${Number(r.final_with_gst||0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.management_fee||0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.deductions_amount||0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.total_cash_adjustment||0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.net_after_adj||0).toLocaleString('en-IN')}</td>
      `;
      tbody.appendChild(tr);
    });
    const labels = rows.map(r => r.store);
    const dataset = rows.map(r => Number(r.final_with_gst||0));
    const ctx = document.getElementById('pay-chart');
    if (payChart) payChart.destroy();
    payChart = new Chart(ctx, { type:'bar', data:{ labels, datasets:[{ label:'Final with GST (₹)', data:dataset, backgroundColor:'#10b981'}] }, options:{ indexAxis:'y', plugins:{legend:{display:false}}}});
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// Per-ride tab
async function fetchPerRide(city) {
  const r = await fetch(`${API}/earnings/per-ride?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

// Hotspots
async function fetchHotspots() {
  const r = await fetch(`${API}/hotspots/`);
  if (!r.ok) return { features: [] };
  return r.json();
}

async function initHotspotsTab() {
  // Lazy-load Leaflet from CDN
  if (!window.L) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(link);
    await new Promise(res => { const s = document.createElement('script'); s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; s.onload = res; document.body.appendChild(s); });
  }
  // Import h3-js via ESM dynamically to avoid MIME issues
  let h3;
  try {
    h3 = (await import('https://cdn.skypack.dev/h3-js@4.1.0')).default;
  } catch (e) {
    console.warn('Failed to import h3-js via ESM, falling back to markers', e);
    h3 = null;
  }
  const mapEl = document.getElementById('map');
  mapEl.innerHTML = '';
  let map;
  try {
    map = L.map('map').setView([18.5204, 73.8567], 11); // default Pune
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(map);
    // ensure proper sizing when tab becomes visible
    setTimeout(() => map.invalidateSize(), 0);
    setTimeout(() => map.invalidateSize(), 300);
  } catch (e) {
    console.error('Leaflet init error', e);
    return;
  }
  const data = await fetchHotspots();
  if (h3) {
    const res = 7; // H3 resolution (lower->bigger hexes)
    const hexToCount = new Map();
    let maxCount = 0;
    (data.features || []).forEach(f => {
      const cell = h3.latLngToCell(f.lat, f.lng, res);
      const c = (hexToCount.get(cell) || 0) + (Number(f.count) || 1);
      hexToCount.set(cell, c);
      if (c > maxCount) maxCount = c;
    });

  function colorFor(v, vmax) {
    const t = Math.max(0, Math.min(1, vmax ? v / vmax : 0));
    // interpolate yellow (#fde047) -> red (#ef4444)
    const r1=253,g1=224,b1=71, r2=239,g2=68,b2=68;
    const r = Math.round(r1 + (r2-r1)*t), g = Math.round(g1 + (g2-g1)*t), b = Math.round(b1 + (b2-b1)*t);
    return `rgb(${r},${g},${b})`;
  }

    const polygons = [];
    hexToCount.forEach((cnt, cell) => {
      const boundary = h3.cellToBoundary(cell, true).map(([lat,lng]) => [lat, lng]);
      const col = colorFor(cnt, maxCount);
      const poly = L.polygon(boundary, { color: col, fillColor: col, weight: 1, fillOpacity: 0.5 })
        .bindPopup(`Jobs: ${cnt}`)
        .addTo(map);
      polygons.push(poly);
    });
    if (polygons.length) {
      const group = L.featureGroup(polygons);
      try { map.fitBounds(group.getBounds().pad(0.1)); } catch {}
      return;
    }
  }
  // fallback markers or message
  if ((data.features || []).length) {
    (data.features || []).forEach(f => {
      const radius = Math.max(4, Math.min(18, f.count || 1));
      L.circleMarker([f.lat, f.lng], { radius, color:'#ef4444', fillColor:'#ef4444', fillOpacity:0.35 }).addTo(map);
    });
  } else {
    const note = L.control({position:'topright'});
    note.onAdd = function() { const d = L.DomUtil.create('div'); d.style.background='#fff'; d.style.padding='6px 8px'; d.style.border='1px solid #e5e7eb'; d.style.borderRadius='6px'; d.textContent='No hotspot data available'; return d; };
    note.addTo(map);
  }
}

// Credit Profiles
async function fetchCredit(city) {
  const r = await fetch(`${API}/credit/profiles?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

let creditChart;
async function initCreditTab() {
  const all = await fetch(`${API}/credit/profiles`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-credit');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchCredit(city);
    const rows = obj[city] || [];
    // table
    const tbody = document.querySelector('#credit-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.cee_name || r.cee_id}</td>
        <td>${r.store}</td>
        <td>${r.credit_score ?? '—'}</td>
        <td>${r.band || '—'}</td>
        <td>₹${Number(r.earning_median || 0).toLocaleString('en-IN')}</td>
        <td>${Number(r.orders_per_day || 0).toFixed(1)}</td>
        <td>${Number(r.attendance_per_week || 0).toFixed(1)}</td>
      `;
      tbody.appendChild(tr);
    });
    // chart
    const buckets = { 'A+':0,'A':0,'B':0,'C':0,'D':0 };
    rows.forEach(r => { if (r.band && buckets.hasOwnProperty(r.band)) buckets[r.band]++; });
    const labels = Object.keys(buckets);
    const data = labels.map(k => buckets[k]);
    const ctx = document.getElementById('credit-chart');
    if (creditChart) creditChart.destroy();
    const bandColors = {
      'A+': '#16a34a', // green
      'A':  '#22c55e',
      'B':  '#f59e0b', // amber
      'C':  '#f97316', // orange
      'D':  '#ef4444', // red
    };
    const colors = labels.map(l => bandColors[l] || '#3b82f6');
    const borders = labels.map(l => (bandColors[l] || '#3b82f6'));
    creditChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Drivers',
          data,
          backgroundColor: colors,
          borderColor: borders,
          borderWidth: 1,
          borderRadius: 8,
          barThickness: 18,
        }]
      },
      options: {
        indexAxis: 'y',
        layout: { padding: 0 },
        plugins: {
          legend: { display: false },
          title: { display: true, text: 'Credit Bands Distribution', color: '#111827', font: { size: 14, weight: '600' } },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.parsed.x} drivers`
            }
          }
        },
        scales: {
          x: { beginAtZero: true, offset: false, grid: { color: '#e5e7eb', borderDash: [4,4] }, ticks: { precision:0, padding: 0 } },
          y: { offset: false, grid: { display: false }, ticks: { padding: 0 } }
        },
        animation: { duration: 400, easing: 'easeOutQuart' }
      }
    });
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// Launch Planner
async function fetchLaunchStores() {
  const r = await fetch(`${API}/launch/stores`);
  if (!r.ok) return [];
  return r.json();
}
async function fetchLaunchPlan(store) {
  const r = await fetch(`${API}/launch/${encodeURIComponent(store)}/plan`);
  if (!r.ok) return null;
  return r.json();
}
async function fetchLaunchTasks(store) {
  const r = await fetch(`${API}/launch/${encodeURIComponent(store)}/tasks`);
  if (!r.ok) return [];
  return r.json();
}

let launchStaffChart, launchRoiChart, launchEnergyChart;
async function initLaunchTab() {
  const sel = document.getElementById('launch-store');
  const meta = document.getElementById('launch-meta');
  const stores = await fetchLaunchStores();
  sel.innerHTML = stores.map(s => `<option value="${s.store}">${s.store} (${s.city||'—'})</option>`).join('');
  const reproc = document.getElementById('launch-reprocess');
  if (reproc) {
    reproc.onclick = async () => {
      const btn = reproc; btn.disabled = true; btn.textContent = 'Rebuilding...';
      try {
        const r = await fetch(`${API}/launch/reprocess`, { method: 'POST' });
        if (r.ok) {
          // reload stores and refresh selection
          const ns = await fetchLaunchStores();
          sel.innerHTML = ns.map(s => `<option value="${s.store}">${s.store} (${s.city||'—'})</option>`).join('');
          if (ns.length) { sel.value = ns[0].store; await update(ns[0].store); }
        }
      } catch (e) {
        console.warn('reprocess failed', e);
      } finally {
        btn.disabled = false; btn.textContent = 'Rebuild from XLS';
      }
    };
  }
  async function update(store) {
    const plan = await fetchLaunchPlan(store);
    if (!plan) return;
    meta.textContent = `City: ${plan.city || '—'} | Opening: ${plan.opening_date || '—'}`;
    // readiness cards
    const cards = document.getElementById('launch-cards');
    cards.innerHTML = '';
    const safeNum = (v, d=0)=>{ const n=Number(v); return Number.isFinite(n)? n : d; };
    const fmtINR = (v)=> `₹${safeNum(v,0).toLocaleString('en-IN')}`;
    const addChip = (label, val) => { const s=document.createElement('span'); s.className='chip'; s.innerHTML=`${label}: <strong>${val}</strong>`; cards.appendChild(s); };
    addChip('Readiness', safeNum((stores.find(x=>x.store===store)||{}).readiness_score ?? null,'—'));
    addChip('Riders/day', safeNum(plan.staffing?.riders_per_day,'—'));
    addChip('Buffer %', `${safeNum(plan.staffing?.buffer_pct,0)}%`);
    addChip('Orders/rider', safeNum(plan.staffing?.target_orders_per_rider,'—'));
    // (insights removed per request)
    // staffing bar
    const sLabels = (plan.staffing?.shifts || []).map(x=>x.name);
    const sData = (plan.staffing?.shifts || []).map(x=> safeNum(x.riders));
    const ctxS = document.getElementById('launch-staff-chart');
    if (launchStaffChart) launchStaffChart.destroy();
    if (sLabels.length && sData.some(v=>v>0)) {
      launchStaffChart = new Chart(ctxS, { type:'bar', data:{ labels:sLabels, datasets:[{ label:'Riders', data:sData, backgroundColor:'#10b981'}]}, options:{ plugins:{legend:{display:false}}}});
    }
    // energy
    const e = document.getElementById('launch-energy');
    e.innerHTML = '';
    const kwhDay = safeNum(plan.energy?.energy_kwh_day, 0);
    const swapsDay = safeNum(plan.energy?.swaps_day, 0);
    addChip('Energy kWh/day', kwhDay);
    addChip('Swaps/day', swapsDay);
    const ctxE = document.getElementById('launch-energy-chart');
    if (launchEnergyChart) launchEnergyChart.destroy();
    if (ctxE && (kwhDay > 0 || swapsDay > 0)) {
      launchEnergyChart = new Chart(ctxE, {
        type: 'bar',
        data: { labels: ['Energy'], datasets: [
          { label: 'kWh/day', data: [kwhDay], backgroundColor: '#06b6d4' },
          { label: 'Swaps/day', data: [swapsDay], backgroundColor: '#f97316' },
        ]},
        options: { indexAxis: 'y', plugins:{ legend:{ display:true } }, scales:{ x:{ beginAtZero:true } } }
      });
    }
    // ROI line
    const labels = ['+1w','+2w','+3w','+4w'];
    const ctxR = document.getElementById('launch-roi-chart');
    if (launchRoiChart) launchRoiChart.destroy();
    const roi = (plan.roi?.weekly_inr || []).map(v=> safeNum(v));
    if (roi.length && roi.some(v=>v>0)) {
      launchRoiChart = new Chart(ctxR, { type:'line', data:{ labels, datasets:[{ label:'Weekly INR', data:roi, borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,.15)', fill:true, tension:.2}]}});
    }
    // SLA
    const slaT = document.querySelector('#launch-sla tbody');
    slaT.innerHTML = `<tr><td class="num">${safeNum(plan.sla?.target_min,'—')}</td><td class="num">${safeNum(plan.sla?.predicted_min,'—')}</td></tr>`;
    // Tasks
    const tasks = await fetchLaunchTasks(store);
    const tb = document.querySelector('#launch-tasks tbody');
    tb.innerHTML = '';
    tasks.forEach(t => { const tr=document.createElement('tr'); tr.innerHTML = `<td>${t.task}</td><td>${t.owner}</td><td>${t.due}</td><td>${t.status}</td>`; tb.appendChild(tr); });
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (stores.length) { sel.value = stores[0].store; await update(stores[0].store); }
}
// MG Guidance
async function fetchMG(city) {
  const r = await fetch(`${API}/mg/guidance?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

async function initMGTab() {
  const all = await fetch(`${API}/mg/guidance`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-mg');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchMG(city);
    const rows = obj[city] || [];
    const tbody = document.querySelector('#mg-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.cee_name || r.cee_id}</td>
        <td>${r.store}</td>
        <td>₹${Number(r.mg_target_per_day || 0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.current_per_day || 0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.mg_gap || 0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.per_ride_median || 0).toLocaleString('en-IN')}</td>
        <td>${r.extra_orders}</td>
        <td>${r.extra_shifts}</td>
        <td>${r.recommendation}</td>
      `;
      tbody.appendChild(tr);
    });
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// Energy Demand tab
async function fetchEnergy(city) {
  const r = await fetch(`${API}/energy/demand?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

async function initEnergyTab() {
  const all = await fetch(`${API}/energy/demand`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-energy');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchEnergy(city);
    const rows = obj[city] || [];
    const tbody = document.querySelector('#energy-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.store}</td>
        <td>${r.orders_week ?? '—'}</td>
        <td>${r.avg_dist_km_per_order ?? '—'}</td>
        <td>${r.energy_kwh_week ?? '—'}</td>
        <td>${r.est_swaps_week ?? '—'}</td>
      `;
      tbody.appendChild(tr);
    });

    // charts
    const labels = rows.map(r => r.store);
    const kwh = rows.map(r => Number(r.energy_kwh_week || 0));
    const swaps = rows.map(r => Number(r.est_swaps_week || 0));
    const ctxK = document.getElementById('energy-kwh-chart');
    const ctxS = document.getElementById('energy-swaps-chart');
    if (window._energyK) window._energyK.destroy();
    if (window._energyS) window._energyS.destroy();
    window._energyK = new Chart(ctxK, { type:'bar', data:{ labels, datasets:[{ label:'kWh/week', data:kwh, backgroundColor:'#06b6d4'}]}, options:{ indexAxis:'y', plugins:{legend:{display:false}}}});
    window._energyS = new Chart(ctxS, { type:'bar', data:{ labels, datasets:[{ label:'Swaps/week', data:swaps, backgroundColor:'#f97316'}]}, options:{ indexAxis:'y', plugins:{legend:{display:false}}}});
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// Maintenance tab
async function fetchMaint(city) {
  const r = await fetch(`${API}/maintenance/risk?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

// Underwriting
async function fetchUW(city) {
  const r = await fetch(`${API}/underwriting/credit?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

async function initUWTab() {
  const all = await fetch(`${API}/underwriting/credit`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-uw');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchUW(city);
    const rows = obj[city] || [];
    const tbody = document.querySelector('#uw-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.cee_name || r.cee_id}</td>
        <td>${r.store || '—'}</td>
        <td>${r.credit_score ?? '—'}</td>
        <td>₹${Number(r.monthly_median_inr || 0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.recommended_limit_inr || 0).toLocaleString('en-IN')}</td>
        <td>${(Number(r.pd || 0)*100).toFixed(1)}%</td>
        <td>${(Number(r.lgd || 0)*100).toFixed(0)}%</td>
        <td>₹${Number(r.ead || 0).toLocaleString('en-IN')}</td>
        <td>₹${Number(r.expected_loss_inr || 0).toLocaleString('en-IN')}</td>
      `;
      tbody.appendChild(tr);
    });
    const labels = rows.slice(0,15).map(r => r.cee_name || r.cee_id);
    const el = rows.slice(0,15).map(r => Number(r.expected_loss_inr || 0));
    const ctx = document.getElementById('uw-el-chart');
    if (window._uw) window._uw.destroy();
    window._uw = new Chart(ctx, { type:'bar', data:{ labels, datasets:[{ label:'Expected Loss (₹)', data:el, backgroundColor:'#f59e0b', barThickness:18}]}, options:{ indexAxis:'y', layout:{ padding:0 }, plugins:{legend:{display:true}}, scales:{ x:{ beginAtZero:true, offset:false, ticks:{ padding:0 }, grid:{ color:'#e5e7eb', borderDash:[4,4]} }, y:{ offset:false, grid:{ display:false }, ticks:{ padding:0 } } } }});

    const pdVals = rows.slice(0,15).map(r => Number(r.pd || 0) * 100);
    const ctxpd = document.getElementById('uw-pd-chart');
    if (window._uwpd) window._uwpd.destroy();
    window._uwpd = new Chart(ctxpd, { type:'bar', data:{ labels, datasets:[{ label:'PD (%)', data:pdVals, backgroundColor:'#3b82f6', barThickness:18}]}, options:{ indexAxis:'y', layout:{ padding:0 }, plugins:{legend:{display:true}}, scales:{ x:{ beginAtZero:true, max:25, offset:false, ticks:{ padding:0 }, grid:{ color:'#e5e7eb', borderDash:[4,4]} }, y:{ offset:false, grid:{ display:false }, ticks:{ padding:0 } } } }});
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// Cashflow
async function fetchCF(city) {
  const r = await fetch(`${API}/cashflow/forecast?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

async function initCFTab() {
  const all = await fetch(`${API}/cashflow/forecast`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-cf');
  const selStore = document.getElementById('store-select-cf');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchCF(city);
    const rows = obj[city] || {};
    const stores = Object.keys(rows);
    const tbody = document.querySelector('#cf-table tbody');
    tbody.innerHTML = '';
    stores.forEach(s => {
      const it = rows[s];
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${s}</td>
        <td>₹${it.past.map(x => Number(x).toLocaleString('en-IN')).join(', ')}</td>
        <td>₹${it.forecast.map(x => Number(x).toLocaleString('en-IN')).join(', ')}</td>
        <td>${it.rationale || '—'}</td>
      `;
      tbody.appendChild(tr);
    });
    // populate store selector and draw selected store
    selStore.innerHTML = stores.map(s => `<option value="${s}">${s}</option>`).join('');
    const selected = selStore.value || stores[0];
    if (selected) {
      const it = rows[selected];
      const labels = ['-3w','-2w','-1w','0','+1w','+2w','+3w','+4w'];
      const data = [...it.past, ...it.forecast];
      const ctx = document.getElementById('cf-chart');
      if (window._cf) window._cf.destroy();
      window._cf = new Chart(ctx, { type:'line', data:{ labels, datasets:[{ label:selected, data, borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,.15)', tension:.2, fill:true }] }, options:{ plugins:{legend:{display:true}}}});
    }
  }
  sel.addEventListener('change', e => update(e.target.value));
  selStore.addEventListener('change', async e => {
    const city = sel.value;
    const obj = await fetchCF(city);
    const rows = obj[city] || {};
    const selected = e.target.value;
    if (rows[selected]) {
      const it = rows[selected];
      const labels = ['-3w','-2w','-1w','0','+1w','+2w','+3w','+4w'];
      const data = [...it.past, ...it.forecast];
      const ctx = document.getElementById('cf-chart');
      if (window._cf) window._cf.destroy();
      window._cf = new Chart(ctx, { type:'line', data:{ labels, datasets:[{ label:selected, data, borderColor:'#3b82f6', backgroundColor:'rgba(59,130,246,.15)', tension:.2, fill:true }] }, options:{ plugins:{legend:{display:true}}}});
    }
  });
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// Expansion
async function fetchEXP(city) {
  const r = await fetch(`${API}/expansion/opps?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

async function initEXPTab() {
  const all = await fetch(`${API}/expansion/opps`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-exp');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchEXP(city);
    const rows = obj[city] || [];
    const tbody = document.querySelector('#exp-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.store}</td>
        <td>${r.roi_score}</td>
        <td>${r.capacity_gap ?? '—'}</td>
        <td>${r.demand_score ?? '—'}</td>
        <td>₹${Number(r.expected_gmv_week || 0).toLocaleString('en-IN')}</td>
        <td>${r.rationale || '—'}</td>
      `;
      tbody.appendChild(tr);
    });
    const labels = rows.slice(0,15).map(r => r.store);
    const roi = rows.slice(0,15).map(r => r.roi_score);
    const ctx = document.getElementById('exp-chart');
    if (window._exp) window._exp.destroy();
    window._exp = new Chart(ctx, { type:'bar', data:{ labels, datasets:[{ label:'ROI score', data:roi, backgroundColor:'#10b981'}]}, options:{ indexAxis:'y', plugins:{legend:{display:false}}, scales:{x:{beginAtZero:true, max:100}}}});
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

// Retention
async function fetchRET(city) {
  const r = await fetch(`${API}/retention/at-risk?city=${encodeURIComponent(city)}`);
  if (!r.ok) return {};
  return r.json();
}

async function initRETTab() {
  const all = await fetch(`${API}/retention/at-risk`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-ret');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchRET(city);
    const rows = obj[city] || [];
    const tbody = document.querySelector('#ret-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.store}</td>
        <td>${r.risk}</td>
        <td>${r.actions}</td>
      `;
      tbody.appendChild(tr);
    });
    const labels = rows.slice(0,15).map(r => r.store);
    const risk = rows.slice(0,15).map(r => r.risk);
    const ctx = document.getElementById('ret-chart');
    if (window._ret) window._ret.destroy();
    window._ret = new Chart(ctx, { type:'bar', data:{ labels, datasets:[{ label:'Churn risk (%)', data:risk, backgroundColor:'#ef4444'}]}, options:{ indexAxis:'y', plugins:{legend:{display:false}}, scales:{x:{beginAtZero:true, max:100}}}});
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}
async function initMaintTab() {
  const all = await fetch(`${API}/maintenance/risk`);
  if (!all.ok) return;
  const cities = Object.keys(await all.json());
  const sel = document.getElementById('city-select-maint');
  sel.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  async function update(city) {
    const obj = await fetchMaint(city);
    const rows = obj[city] || [];
    const tbody = document.querySelector('#maint-table tbody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${r.store}</td>
        <td>${r.downtime_risk ?? '—'}</td>
        <td>${r.est_tickets_week ?? '—'}</td>
        <td>${r.notes || '—'}</td>
      `;
      tbody.appendChild(tr);
    });
    const labels = rows.map(r => r.store);
    const risk = rows.map(r => Number(r.downtime_risk || 0));
    const ctx = document.getElementById('maint-risk-chart');
    if (window._maint) window._maint.destroy();
    window._maint = new Chart(ctx, { type:'bar', data:{ labels, datasets:[{ label:'Downtime risk (%)', data:risk, backgroundColor:'#ef4444'}]}, options:{ indexAxis:'y', scales:{x:{beginAtZero:true, max:100}}, plugins:{legend:{display:false}}}});
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
}

function renderRideStats(row) {
  const wrap = document.getElementById('ride-stats');
  wrap.innerHTML = '';
  const add = (label, val) => {
    const span = document.createElement('span');
    span.className = 'chip';
    span.innerHTML = `${label}: <strong>₹${Number(val || 0).toLocaleString('en-IN')}</strong>`;
    wrap.appendChild(span);
  };
  add('Avg', row.per_ride_avg);
  add('Median', row.per_ride_median);
  add('P25', row.p25);
  add('P75', row.p75);
  const s = document.createElement('span');
  s.className = 'chip';
  s.textContent = `Std: ${Number(row.per_ride_std || 0).toFixed(1)}`;
  wrap.appendChild(s);
  const n = document.createElement('span');
  n.className = 'chip';
  n.textContent = `Samples: ${row.num_samples ?? 0}`;
  wrap.appendChild(n);
}

function renderRideRange(row) {
  const p25 = Number(row.p25 || 0);
  const med = Number(row.per_ride_median || 0);
  const p75 = Number(row.p75 || 0);
  const max = Math.max(p75, med, p25, 1);
  document.getElementById('ride-range-p25').style.width = `${(p25/max)*100}%`;
  document.getElementById('ride-range-med').style.width = `${(med/max)*100}%`;
  document.getElementById('ride-range-p75').style.width = `${(p75/max)*100}%`;
}

function renderRideTable(rows) {
  const tbody = document.querySelector('#ride-table tbody');
  tbody.innerHTML = '';
  rows.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.store}</td>
      <td>₹${Number(r.per_ride_avg || 0).toLocaleString('en-IN')}</td>
      <td>₹${Number(r.per_ride_median || 0).toLocaleString('en-IN')}</td>
      <td>₹${Number(r.p25 || 0).toLocaleString('en-IN')}</td>
      <td>₹${Number(r.p75 || 0).toLocaleString('en-IN')}</td>
      <td>${Number(r.per_ride_std || 0).toFixed(1)}</td>
      <td>${r.num_samples ?? 0}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function initRideTab() {
  const citiesRes = await fetch(`${API}/demand/forecast`);
  const cities = citiesRes.ok ? Object.keys(await citiesRes.json()) : [];
  const selCity = document.getElementById('city-select-ride');
  selCity.innerHTML = cities.map(c => `<option value="${c}">${c}</option>`).join('');
  const selStore = document.getElementById('store-select-ride');
  async function update(city) {
    const obj = await fetchPerRide(city);
    const rows = obj[city] || [];
    renderRideTable(rows);
    selStore.innerHTML = rows.map(r => `<option value="${r.store}">${r.store}</option>`).join('');
    if (rows.length) { renderRideStats(rows[0]); renderRideRange(rows[0]); }
  }
  selCity.addEventListener('change', e => update(e.target.value));
  selStore.addEventListener('change', async e => {
    const city = selCity.value;
    const store = e.target.value;
    const obj = await fetchPerRide(city);
    const rows = obj[city] || [];
    const row = rows.find(r => r.store === store) || rows[0];
    if (row) { renderRideStats(row); renderRideRange(row); }
  });
  if (cities.length) { selCity.value = cities[0]; await update(cities[0]); }
}

async function refresh() {
  const jobs = await fetchJobs();
  renderJobsTable(jobs);
  renderZoneChart(jobs);
}

async function main() {
  renderStatus('checking...');
  renderStatus(await health());
  await refresh();

  const btnDemand = document.getElementById('tab-btn-demand');
  const btn3pl = document.getElementById('tab-btn-3pl');
  const btnRide = document.getElementById('tab-btn-ride');
  const btnInc = document.getElementById('tab-btn-incentives');
  const btnPay = document.getElementById('tab-btn-payouts');
  const btnHot = document.getElementById('tab-btn-hotspots');
  const btnCredit = document.getElementById('tab-btn-credit');
  const btnMG = document.getElementById('tab-btn-mg');
  const btnEnergy = document.getElementById('tab-btn-energy');
  const btnMaint = document.getElementById('tab-btn-maint');
  const btnUW = document.getElementById('tab-btn-uw');
  const btnCF = document.getElementById('tab-btn-cf');
  const btnEXP = document.getElementById('tab-btn-exp');
  const btnRET = document.getElementById('tab-btn-ret');
  const btnBeckn = document.getElementById('tab-btn-beckn');
  const btnLaunch = document.getElementById('tab-btn-launch');
  const tabDemand = document.getElementById('tab-demand');
  const tab3pl = document.getElementById('tab-threepl');
  const tabRide = document.getElementById('tab-ride');
  const tabInc = document.getElementById('tab-incentives');
  const tabPay = document.getElementById('tab-payouts');
  const tabHot = document.getElementById('tab-hotspots');
  const tabCredit = document.getElementById('tab-credit');
  const tabMG = document.getElementById('tab-mg');
  const tabEnergy = document.getElementById('tab-energy');
  const tabMaint = document.getElementById('tab-maint');
  const tabUW = document.getElementById('tab-uw');
  const tabCF = document.getElementById('tab-cf');
  const tabEXP = document.getElementById('tab-exp');
  const tabRET = document.getElementById('tab-ret');
  const tabBeckn = document.getElementById('tab-beckn');
  const tabLaunch = document.getElementById('tab-launch');
  function activate(tab) {
    const activeStyle = 'background:#f9fafb;';
    const inactiveStyle = 'background:#fff;';
    if (tab === 'demand') {
      tabDemand.style.display = 'block'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none';
      btnDemand.setAttribute('style', btnDemand.getAttribute('style').replace('background:#fff;', activeStyle));
      btn3pl.setAttribute('style', btn3pl.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnRide.setAttribute('style', btnRide.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnInc.setAttribute('style', btnInc.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnPay.setAttribute('style', btnPay.getAttribute('style').replace('background:#f9fafb;', inactiveStyle));
    } else if (tab === 'threepl') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'block'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none';
      btn3pl.setAttribute('style', btn3pl.getAttribute('style').replace('background:#fff;', activeStyle));
      btnDemand.setAttribute('style', btnDemand.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnRide.setAttribute('style', btnRide.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnInc.setAttribute('style', btnInc.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnPay.setAttribute('style', btnPay.getAttribute('style').replace('background:#f9fafb;', inactiveStyle));
    } else if (tab === 'ride') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'block'; tabInc.style.display = 'none'; tabPay.style.display = 'none';
      btnRide.setAttribute('style', btnRide.getAttribute('style').replace('background:#fff;', activeStyle));
      btnDemand.setAttribute('style', btnDemand.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btn3pl.setAttribute('style', btn3pl.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnInc.setAttribute('style', btnInc.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnPay.setAttribute('style', btnPay.getAttribute('style').replace('background:#f9fafb;', inactiveStyle));
    } else if (tab === 'incentives') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'block'; tabPay.style.display = 'none';
      btnInc.setAttribute('style', btnInc.getAttribute('style').replace('background:#fff;', activeStyle));
      btnDemand.setAttribute('style', btnDemand.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btn3pl.setAttribute('style', btn3pl.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnRide.setAttribute('style', btnRide.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnPay.setAttribute('style', btnPay.getAttribute('style').replace('background:#f9fafb;', inactiveStyle));
    } else if (tab === 'payouts') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'block';
      btnPay.setAttribute('style', btnPay.getAttribute('style').replace('background:#fff;', activeStyle));
      btnDemand.setAttribute('style', btnDemand.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btn3pl.setAttribute('style', btn3pl.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnRide.setAttribute('style', btnRide.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnInc.setAttribute('style', btnInc.getAttribute('style').replace('background:#f9fafb;', inactiveStyle));
    } else if (tab === 'hotspots') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'block'; tabCredit.style.display = 'none';
      btnHot.setAttribute('style', btnHot.getAttribute('style').replace('background:#fff;', activeStyle));
      btnDemand.setAttribute('style', btnDemand.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btn3pl.setAttribute('style', btn3pl.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnRide.setAttribute('style', btnRide.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnInc.setAttribute('style', btnInc.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnPay.setAttribute('style', btnPay.getAttribute('style').replace('background:#f9fafb;', inactiveStyle));
    } else if (tab === 'credit') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'block'; tabMG.style.display = 'none';
      btnCredit.setAttribute('style', btnCredit.getAttribute('style').replace('background:#fff;', activeStyle));
      btnDemand.setAttribute('style', btnDemand.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btn3pl.setAttribute('style', btn3pl.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnRide.setAttribute('style', btnRide.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnInc.setAttribute('style', btnInc.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnPay.setAttribute('style', btnPay.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnHot.setAttribute('style', btnHot.getAttribute('style').replace('background:#f9fafb;', inactiveStyle));
    } else if (tab === 'mg') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'block';
      btnMG.setAttribute('style', btnMG.getAttribute('style').replace('background:#fff;', activeStyle));
      btnDemand.setAttribute('style', btnDemand.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btn3pl.setAttribute('style', btn3pl.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnRide.setAttribute('style', btnRide.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnInc.setAttribute('style', btnInc.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnPay.setAttribute('style', btnPay.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnHot.setAttribute('style', btnHot.getAttribute('style').replace('background:#f9fafb;', inactiveStyle)); btnCredit.setAttribute('style', btnCredit.getAttribute('style').replace('background:#f9fafb;', inactiveStyle));
    } else if (tab === 'energy') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'none'; tabEnergy.style.display = 'block'; tabMaint.style.display = 'none';
      btnEnergy.setAttribute('style', btnEnergy.getAttribute('style').replace('background:#fff;', activeStyle));
    } else if (tab === 'maint') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'none'; tabEnergy.style.display = 'none'; tabMaint.style.display = 'block';
      btnMaint.setAttribute('style', btnMaint.getAttribute('style').replace('background:#fff;', activeStyle));
    } else if (tab === 'uw') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'none'; tabEnergy.style.display = 'none'; tabMaint.style.display = 'none'; tabUW.style.display = 'block';
      btnUW.setAttribute('style', btnUW.getAttribute('style').replace('background:#fff;', activeStyle));
    } else if (tab === 'cf') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'none'; tabEnergy.style.display = 'none'; tabMaint.style.display = 'none'; tabUW.style.display = 'none'; tabCF.style.display = 'block';
      btnCF.setAttribute('style', btnCF.getAttribute('style').replace('background:#fff;', activeStyle));
    } else if (tab === 'exp') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'none'; tabEnergy.style.display = 'none'; tabMaint.style.display = 'none'; tabUW.style.display = 'none'; tabCF.style.display = 'none'; tabEXP.style.display = 'block';
      btnEXP.setAttribute('style', btnEXP.getAttribute('style').replace('background:#fff;', activeStyle));
    } else if (tab === 'ret') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'none'; tabEnergy.style.display = 'none'; tabMaint.style.display = 'none'; tabUW.style.display = 'none'; tabCF.style.display = 'none'; tabEXP.style.display = 'none'; tabRET.style.display = 'block';
      btnRET.setAttribute('style', btnRET.getAttribute('style').replace('background:#fff;', activeStyle));
    } else if (tab === 'beckn') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'none'; tabEnergy.style.display = 'none'; tabMaint.style.display = 'none'; tabUW.style.display = 'none'; tabCF.style.display = 'none'; tabEXP.style.display = 'none'; tabRET.style.display = 'none'; tabBeckn.style.display = 'block';
      btnBeckn.setAttribute('style', btnBeckn.getAttribute('style').replace('background:#fff;', activeStyle));
    } else if (tab === 'launch') {
      tabDemand.style.display = 'none'; tab3pl.style.display = 'none'; tabRide.style.display = 'none'; tabInc.style.display = 'none'; tabPay.style.display = 'none'; tabHot.style.display = 'none'; tabCredit.style.display = 'none'; tabMG.style.display = 'none'; tabEnergy.style.display = 'none'; tabMaint.style.display = 'none'; tabUW.style.display = 'none'; tabCF.style.display = 'none'; tabEXP.style.display = 'none'; tabRET.style.display = 'none'; tabBeckn.style.display = 'none'; tabLaunch.style.display = 'block';
      btnLaunch.setAttribute('style', btnLaunch.getAttribute('style').replace('background:#fff;', activeStyle));
    }
  }
  btnDemand.addEventListener('click', async () => { activate('demand'); await initDemandTab(); });
  btn3pl.addEventListener('click', async () => { activate('threepl'); await initThreeplTab(); });
  btnRide.addEventListener('click', async () => { activate('ride'); await initRideTab(); });
  btnInc.addEventListener('click', async () => { activate('incentives'); await initIncentivesTab(); });
  btnPay.addEventListener('click', async () => { activate('payouts'); await initPayoutsTab(); });
  btnHot.addEventListener('click', async () => { activate('hotspots'); await initHotspotsTab(); });
  btnCredit.addEventListener('click', async () => { activate('credit'); await initCreditTab(); });
  btnMG.addEventListener('click', async () => { activate('mg'); await initMGTab(); });
  btnEnergy.addEventListener('click', async () => { activate('energy'); await initEnergyTab(); });
  btnMaint.addEventListener('click', async () => { activate('maint'); await initMaintTab(); });
  btnUW.addEventListener('click', async () => { activate('uw'); await initUWTab(); });
  btnCF.addEventListener('click', async () => { activate('cf'); await initCFTab(); });
  btnEXP.addEventListener('click', async () => { activate('exp'); await initEXPTab(); });
  btnRET.addEventListener('click', async () => { activate('ret'); await initRETTab(); });
  btnBeckn.addEventListener('click', async () => { activate('beckn'); });
  btnLaunch.addEventListener('click', async () => { activate('launch'); await initLaunchTab(); });

  // Beckn admin button handlers
  const log = (m) => { const el = document.getElementById('beckn-log'); el.textContent = (el.textContent + (el.textContent ? '\n' : '') + m).slice(-4000); };
  const post = async (p) => { const r = await fetch(`${API}${p}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ context:{}, message:{} }) }); log(p+': '+r.status+' '+(await r.text()).slice(0,500)); };
  const b1 = document.getElementById('beckn-btn-search'); if (b1) b1.onclick = () => post('/beckn/bpp/search');
  const b2 = document.getElementById('beckn-btn-select'); if (b2) b2.onclick = () => post('/beckn/bpp/select');
  const b3 = document.getElementById('beckn-btn-confirm'); if (b3) b3.onclick = () => post('/beckn/bpp/confirm');
  const b4 = document.getElementById('beckn-btn-status'); if (b4) b4.onclick = () => post('/beckn/bpp/status');

  // Populate launch stores in Beckn admin
  try {
    const r = await fetch(`${API}/launch/stores`);
    if (r.ok) {
      const rows = await r.json();
      const tb = document.querySelector('#launch-table tbody');
      if (tb) {
        tb.innerHTML = '';
        rows.forEach(x => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${x.store}</td>
            <td>${x.city || '—'}</td>
            <td>${x.opening_date || '—'}</td>
            <td class="num">${x.readiness_score}</td>
            <td>${x.risk || '—'}</td>
          `;
          tb.appendChild(tr);
        });
      }
    }
  } catch {}

  // default view
  await initDemandTab();
}

main();


