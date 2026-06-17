from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard-ui"])


_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Trading Research Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0a0e17; color: #e0e6f0; font-family: -apple-system, 'SF Mono', 'Fira Code', monospace; padding: 24px; }
  h1 { font-size: 20px; font-weight: 600; color: #8899bb; margin-bottom: 20px; letter-spacing: 0.5px; }
  h1 span { color: #4a9eff; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; margin-bottom: 20px; }
  .card { background: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 16px; }
  .card h2 { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #6b7a99; margin-bottom: 12px; }
  .row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; }
  .row .label { color: #8899bb; }
  .row .value { font-weight: 500; }
  .ok { color: #22c55e; }
  .warn { color: #f59e0b; }
  .bad { color: #ef4444; }
  .neutral { color: #94a3b8; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; color: #6b7a99; font-weight: 500; padding: 6px 4px; border-bottom: 1px solid #1e293b; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
  td { padding: 6px 4px; border-bottom: 1px solid #1a2233; }
  .flash { color: #22c55e; }
  .chip { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
  .chip-green { background: #052e16; color: #22c55e; }
  .chip-red { background: #450a0a; color: #ef4444; }
  .chip-yellow { background: #451a03; color: #f59e0b; }
  .chip-gray { background: #1e293b; color: #8899bb; }
  .empty { color: #4a5568; font-size: 12px; text-align: center; padding: 20px; }
  .loading { color: #6b7a99; font-size: 13px; text-align: center; padding: 40px; }
</style>
</head>
<body>

<h1>📊 <span>AI Trading Research</span> Dashboard</h1>

<div class="grid">
  <div class="card" id="daily-card">
    <h2>📋 Latest Research Run</h2>
    <div class="loading">Loading daily research...</div>
  </div>

  <div class="card" id="paper-card">
    <h2>📈 Paper Validation</h2>
    <div class="loading">Loading...</div>
  </div>

  <div class="card" id="evidence-card">
    <h2>🔬 Evidence vs Baseline</h2>
    <div class="loading">Loading...</div>
  </div>

  <div class="card" id="gate-card">
    <h2>🚦 Promotion Gate</h2>
    <div class="loading">Loading...</div>
  </div>
</div>

<div class="grid">
  <div class="card" id="segments-card">
    <h2>🏆 Winning Segments</h2>
    <div class="loading">Loading...</div>
  </div>

  <div class="card" id="actions-card">
    <h2>📌 Next Research Actions</h2>
    <div class="loading">Loading...</div>
  </div>

  <div class="card" id="loss-card">
    <h2>🔍 Worst Loss Drivers</h2>
    <div class="loading">Loading...</div>
  </div>

  <div class="card" id="threshold-card">
    <h2>🎯 Best Thresholds</h2>
    <div class="loading">Loading...</div>
  </div>
</div>

<script>
async function loadDashboard() {
  try {
    const res = await fetch('/api/daily-research/latest');
    const data = await res.json();
    renderDaily(data);
    if (data.phase_3_readiness_status) renderPaper(data);
    if (data.diagnostics_summary) renderEvidence(data.diagnostics_summary);
    renderGate(data);
    renderSegments(data);
    renderActions(data);
    renderLossDrivers(data);
    renderThresholds(data);
  } catch(e) {
    document.querySelectorAll('.loading').forEach(el => el.textContent = '❌ ' + e.message);
  }
}

function renderDaily(data) {
  const card = document.getElementById('daily-card');
  card.innerHTML = `<h2>📋 Latest Research Run</h2>` + (data.status === 'missing' ? `
    <div class="empty">No daily research run yet. Cron should fire at 13:00/14:30 BST today.</div>
  ` : `
    <div class="row"><span class="label">Run date</span><span class="value">${data.latest_run_date || '-'}</span></div>
    <div class="row"><span class="label">Mode</span><span class="value chip ${data.mode === 'live' ? 'chip-green' : 'chip-gray'}">${data.mode || '-'}</span></div>
    <div class="row"><span class="label">Universe</span><span class="value">${data.universe_preset || '-'}</span></div>
    <div class="row"><span class="label">Tickers</span><span class="value ${statusClass(data.tickers_completed, data.tickers_total)}">${data.tickers_completed || '?'} / ${data.tickers_total || '?'}</span></div>
    <div class="row"><span class="label">Provider calls</span><span class="value">${data.estimated_provider_calls || '-'}</span></div>
    <div class="row"><span class="label">Live data</span><span class="value ${data.live_data_enabled ? 'ok' : 'neutral'}">${data.live_data_enabled ? 'true' : 'false'}</span></div>
    <div class="row"><span class="label">Orders</span><span class="value ok">false</span></div>
    ${data.news_catalysts_fetched ? `<div class="row"><span class="label">News fetched</span><span class="value">${data.news_catalysts_fetched}</span></div>` : ''}
  `);
}

function renderPaper(data) {
  const card = document.getElementById('paper-card');
  const pv = data.paper_validation_summary || {};
  card.innerHTML = `<h2>📈 Paper Validation</h2>
    <div class="row"><span class="label">Total recommendations</span><span class="value">${pv.recommendations_total || '-'}</span></div>
    <div class="row"><span class="label">Closed trades</span><span class="value">${pv.closed_total || 0}</span></div>
    <div class="row"><span class="label">Win rate</span><span class="value">${fmtPct(pv.win_rate)}</span></div>
    <div class="row"><span class="label">Expectancy</span><span class="value ${expectancyClass(pv.expectancy_r)}">${fmtR(pv.expectancy_r)}</span></div>
  `;
}

function renderEvidence(ds) {
  const card = document.getElementById('evidence-card');
  card.innerHTML = `<h2>🔬 Evidence vs Baseline</h2>
    <div class="row"><span class="label">Evidence-backed</span><span class="value ${expectancyClass(ds.evidence_backed_expectancy_r)}">${fmtR(ds.evidence_backed_expectancy_r)}</span></div>
    <div class="row"><span class="label">Baseline</span><span class="value ${expectancyClass(ds.baseline_expectancy_r)}">${fmtR(ds.baseline_expectancy_r)}</span></div>
    <div class="row"><span class="label">Delta</span><span class="value ${deltaClass(ds.evidence_vs_baseline_delta_r)}">${fmtR(ds.evidence_vs_baseline_delta_r)}</span></div>
    <div class="row"><span class="label">Status</span><span class="value chip ${statusChip(ds.phase_3_readiness_status)}">${ds.phase_3_readiness_status || '-'}</span></div>
  `;
}

function renderGate(data) {
  const card = document.getElementById('gate-card');
  const pg = data.promotion_gate || {};
  const st = pg.promotion_status || 'no_data';
  const cls = st === 'candidate_for_backtest_confirmation' ? 'chip-green' : st === 'needs_more_data' ? 'chip-yellow' : 'chip-red';
  card.innerHTML = `<h2>🚦 Promotion Gate</h2>
    <div class="row"><span class="label">Status</span><span class="value chip ${cls}">${pg.promotion_status || 'no_data'}</span></div>
    <div class="row"><span class="label">Reason</span><span class="value">${pg.reason || '-'}</span></div>
    <div class="row"><span class="label">Orders</span><span class="value ok">false</span></div>
    <div class="row"><span class="label">Backtest req.</span><span class="value">${pg.requires_backtest_confirmation ? 'true' : 'false'}</span></div>
  `;
}

function renderSegments(data) {
  const card = document.getElementById('segments-card');
  const segs = (data.segment_threshold_recommendations || []).filter(s => s.trade_count >= 5).slice(0, 6);
  if (!segs.length) { card.innerHTML = `<h2>🏆 Winning Segments</h2><div class="empty">No segments yet</div>`; return; }
  card.innerHTML = `<h2>🏆 Winning Segments</h2>
    <table><thead><tr><th>Segment</th><th>#</th><th>Exp R</th><th>WR</th><th>Thr.</th></tr></thead>
    <tbody>${segs.map(s => `<tr><td>${s.segment}</td><td>${s.trade_count}</td><td class="${expectancyClass(s.expectancy_r)}">${fmtR(s.expectancy_r)}</td><td>${fmtPct(s.win_rate)}</td><td>${s.recommended_threshold}</td></tr>`).join('')}</tbody></table>
  `;
}

function renderActions(data) {
  const card = document.getElementById('actions-card');
  const actions = data.next_research_actions || [];
  if (!actions.length) { card.innerHTML = `<h2>📌 Next Research Actions</h2><div class="empty">None</div>`; return; }
  card.innerHTML = `<h2>📌 Next Research Actions</h2>` + actions.map(a => `
    <div class="row"><span class="label chip ${a.action.includes('block')||a.action.includes('deprioritize') ? 'chip-red' : a.action.includes('diagnose') ? 'chip-yellow' : 'chip-gray'}">${a.action}</span><span class="value" style="font-size:11px;color:#8899bb">${a.reason || ''}</span></div>
  `).join('');
}

function renderLossDrivers(data) {
  const card = document.getElementById('loss-card');
  const ds = data.diagnostics_summary || {};
  const worst = ds.worst_loss_drivers || [];
  if (!worst.length) { card.innerHTML = `<h2>🔍 Worst Loss Drivers</h2><div class="empty">None identified</div>`; return; }
  card.innerHTML = `<h2>🔍 Worst Loss Drivers</h2>` + worst.map(w => `
    <div class="row"><span class="label">${w.dimension}: ${w.segment}</span><span class="value bad">${fmtR(w.expectancy_r)} (${w.trade_count} trades)</span></div>
  `).join('');
}

function renderThresholds(data) {
  const card = document.getElementById('threshold-card');
  const sweep = data.aggregate_threshold_sweep || {};
  const bt = sweep.best_threshold || {};
  const thresh = (sweep.thresholds || []).slice(0, 8);
  if (!thresh.length) { card.innerHTML = `<h2>🎯 Best Thresholds</h2><div class="empty">No data</div>`; return; }
  card.innerHTML = `<h2>🎯 Best Thresholds</h2><div class="row" style="margin-bottom:6px"><span class="label">Best</span><span class="value chip chip-green">${bt.threshold || '-'} (${fmtR(bt.expectancy_r)})</span></div>
    <table><thead><tr><th>Thr.</th><th>#</th><th>Exp R</th><th>WR</th></tr></thead>
    <tbody>${thresh.map(t => `<tr><td class="${t.threshold === (bt.threshold) ? 'ok' : ''}">${t.threshold}</td><td>${t.trade_count}</td><td class="${expectancyClass(t.expectancy_r)}">${fmtR(t.expectancy_r)}</td><td>${fmtPct(t.win_rate)}</td></tr>`).join('')}</tbody></table>
  `;
}

function statusClass(completed, total) {
  if (completed === undefined) return 'neutral';
  return completed === total ? 'ok' : completed > 0 ? 'warn' : 'bad';
}
function statusChip(s) {
  if (!s) return 'chip-gray';
  if (s.includes('ready') || s.includes('started')) return 'chip-green';
  if (s.includes('diagnos') || s.includes('needs')) return 'chip-yellow';
  return 'chip-red';
}
function deltaClass(d) {
  if (d === null || d === undefined) return '';
  return d > 0 ? 'ok' : d < 0 ? 'bad' : 'neutral';
}
function expectancyClass(e) {
  if (e === null || e === undefined) return 'neutral';
  return e > 0 ? 'ok' : e < 0 ? 'bad' : 'neutral';
}
function fmtR(v) {
  if (v === null || v === undefined) return '-';
  const n = Number(v).toFixed(2);
  return (Number(v) > 0 ? '+' : '') + n + 'R';
}
function fmtPct(v) {
  if (v === null || v === undefined) return '-';
  return (v * 100).toFixed(0) + '%';
}

loadDashboard();
setInterval(loadDashboard, 60000);
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return _DASHBOARD_HTML
