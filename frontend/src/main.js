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
  const mapEl = document.getElementById('map');
  mapEl.innerHTML = '';
  const map = L.map('map').setView([18.5204, 73.8567], 11); // default Pune
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(map);
  const data = await fetchHotspots();
  data.features.forEach(f => {
    const radius = Math.max(5, Math.min(25, f.count));
    L.circleMarker([f.lat, f.lng], { radius, color:'#ef4444', fillColor:'#ef4444', fillOpacity:0.4 }).addTo(map).bindPopup(`Zone ${f.zone_id}<br/>Jobs: ${f.count}`);
  });
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
          barThickness: 22,
        }]
      },
      options: {
        indexAxis: 'y',
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
          x: { beginAtZero: true, grid: { color: '#e5e7eb', borderDash: [4,4] }, ticks: { precision:0 } },
          y: { grid: { display: false } }
        },
        animation: { duration: 500, easing: 'easeOutQuart' }
      }
    });
  }
  sel.addEventListener('change', e => update(e.target.value));
  if (cities.length) { sel.value = cities[0]; await update(cities[0]); }
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
  const tabDemand = document.getElementById('tab-demand');
  const tab3pl = document.getElementById('tab-threepl');
  const tabRide = document.getElementById('tab-ride');
  const tabInc = document.getElementById('tab-incentives');
  const tabPay = document.getElementById('tab-payouts');
  const tabHot = document.getElementById('tab-hotspots');
  const tabCredit = document.getElementById('tab-credit');
  const tabMG = document.getElementById('tab-mg');
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

  // default view
  await initDemandTab();
}

main();


