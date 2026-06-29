from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard-ui"])


_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Trading Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0a0e17; color: #e0e6f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px; }
  h1 { font-size: 20px; font-weight: 700; color: #e0e6f0; margin-bottom: 20px; letter-spacing: -0.3px; }
  h1 span { color: #4a9eff; }
  .banner { padding: 14px 18px; border-radius: 10px; margin-bottom: 20px; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 12px; }
  .banner-green { background: #052e16; border: 1px solid #166534; color: #22c55e; }
  .banner-yellow { background: #451a03; border: 1px solid #78350f; color: #f59e0b; }
  .banner-red { background: #450a0a; border: 1px solid #7f1d1d; color: #ef4444; }
  .banner-gray { background: #1e293b; border: 1px solid #334155; color: #94a3b8; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; margin-bottom: 14px; }
  .card { background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 18px; transition: border-color 0.2s; }
  .card:hover { border-color: #2a3a55; }
  .card h2 { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #6b7a99; margin-bottom: 12px; font-weight: 600; }
  .full { grid-column: 1 / -1; }
  .row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; font-size: 14px; border-bottom: 1px solid #0f1729; }
  .row:last-child { border-bottom: none; }
  .row .lbl { color: #8899bb; font-size: 13px; }
  .row .val { font-weight: 600; font-size: 14px; }
  .green { color: #22c55e; }
  .blue { color: #3b82f6; }
  .red { color: #ef4444; }
  .yellow { color: #f59e0b; }
  .gray { color: #94a3b8; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .badge-green { background: #052e16; color: #22c55e; }
  .badge-red { background: #450a0a; color: #ef4444; }
  .badge-yellow { background: #451a03; color: #f59e0b; }
  .badge-blue { background: #0c1f3f; color: #60a5fa; }
  .badge-gray { background: #1e293b; color: #94a3b8; }
  .stat { display: flex; align-items: center; gap: 6px; }
  .stat-num { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
  .stat-lbl { font-size: 11px; color: #6b7a99; text-transform: uppercase; letter-spacing: 0.5px; }
  .stats-row { display: flex; gap: 20px; margin-bottom: 10px; flex-wrap: wrap; }
  .trades-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; }
  .trades-table th { text-align: left; color: #6b7a99; font-weight: 500; padding: 6px 5px; border-bottom: 1px solid #1e293b; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
  .trades-table td { padding: 7px 5px; border-bottom: 1px solid #0f1729; }
  .trades-table tr:last-child td { border-bottom: none; }
  .trades-table .ticker-cell { font-weight: 700; color: #e0e6f0; }
  .pct-up { color: #22c55e; font-weight: 600; }
  .pct-down { color: #ef4444; font-weight: 600; }
  .pct-flat { color: #94a3b8; font-weight: 600; }
  .loading { color: #6b7a99; font-size: 14px; text-align: center; padding: 30px; }
  .empty { color: #4a5568; font-size: 13px; text-align: center; padding: 20px; }
  input { background: #1e293b; border: 1px solid #334155; color: #e0e6f0; padding: 10px 14px; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.2s; }
  input:focus { border-color: #4a9eff; }
  button { background: #2563eb; border: none; color: #fff; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: background 0.2s; }
  button:hover { background: #1d4ed8; }
</style>
</head>
<body>

<h1>📊 <span>AI Trading Research</span> Dashboard</h1>
<div id="banner" class="banner banner-gray"><span style="font-size:20px">⏳</span> Loading...</div>

<div class="grid">
  <div class="card" id="run-card"><h2>📋 Today's Run</h2><div class="loading">Loading...</div></div>
  <div class="card" id="result-card"><h2>📈 Results</h2><div class="loading">Loading...</div></div>
  <div class="card" id="edges-card"><h2>✅ What Works</h2><div class="loading">Loading...</div></div>
  <div class="card" id="problems-card"><h2>❌ What Doesn't</h2><div class="loading">Loading...</div></div>
</div>

<div class="grid">
  <div class="card" id="tickers-card"><h2>🏆 Best Tickers</h2><div class="loading">Loading...</div></div>
  <div class="card" id="weak-tickers-card"><h2>📉 Weakest Tickers</h2><div class="loading">Loading...</div></div>
  <div class="card" id="patterns-card"><h2>🕯️ Candle Patterns</h2><div class="loading">Loading...</div></div>
  <div class="card" id="gate-card"><h2>🚦 Status</h2><div class="loading">Loading...</div></div>
</div>

<div class="grid">
  <div class="card full" id="segments-card"><h2>🏆 Best Setups (with evidence)</h2><div class="loading">Loading...</div></div>
</div>

<div class="grid" style="align-items:center">
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:4px">
    <span style="color:#6b7a99;font-size:13px">📅 View date:</span>
    <input type="date" id="view-date" style="background:#1e293b;border:1px solid #334155;color:#e0e6f0;padding:6px 10px;border-radius:6px;font-size:13px">
    <button onclick="loadPortfolio()" style="background:#2563eb;border:none;color:#fff;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px">Go</button>
    <span style="color:#4a5568;font-size:12px;margin-left:8px">
      Available: <span id="avail-dates"></span>
    </span>
  </div>
</div>

<div class="grid">
  <div class="card" id="portfolio-summary-card"><h2>📊 Portfolio P&L</h2><div class="loading">Loading...</div></div>
  <div class="card" id="portfolio-trades-card"><h2>📝 Active Trades</h2><div class="loading">Loading...</div></div>
</div>

<div class="grid">
  <div class="card full" id="ta-card">
    <h2>🔬 Technical Analysis</h2>
    <div style="display:flex;gap:8px;margin-bottom:10px">
      <input id="ta-ticker" type="text" placeholder="Enter ticker (e.g. AAPL)" style="flex:1;background:#1e293b;border:1px solid #334155;color:#e0e6f0;padding:8px 12px;border-radius:6px;font-size:14px">
      <button onclick="runTA()" style="background:#2563eb;border:none;color:#fff;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:14px">Analyze</button>
    </div>
    <div id="ta-result"><div class="empty">Enter a ticker and click Analyze</div></div>
  </div>
</div>

<script>
async function load() {
  try {
    const res = await fetch('/api/daily-research/latest');
    const d = await res.json();
    if (d.status === 'missing') { renderEmpty(d); return; }

    const ev = d.diagnostics_summary || {};
    const pg = d.promotion_gate || {};
    const pv = d.paper_validation_summary || {};
    const r3s = ev.phase_3_readiness_status || '';

    // Banner
    const banner = document.getElementById('banner');
    let text, cls, icon;
    if (pg.promotion_status === 'blocked') {
      text = 'System blocked itself. Evidence underperforms baseline. Diagnostics needed before changes.';
      cls = 'banner-yellow'; icon = '🟡';
    } else if (r3s === 'needs_loss_driver_diagnostics') {
      text = 'Evidence-backed under baseline. Diagnosing loss drivers.';
      cls = 'banner-yellow'; icon = '🟡';
    } else if (r3s === 'paper_validation_started') {
      text = 'Research running. Paper validation in progress.';
      cls = 'banner-green'; icon = '🟢';
    } else {
      text = 'No issues.';
      cls = 'banner-green'; icon = '🟢';
    }
    banner.className = 'banner ' + cls;
    banner.innerHTML = '<span style="font-size:20px">' + icon + '</span> ' + text;

    // Run card
    document.getElementById('run-card').innerHTML = '<h2>📋 Today\\'s Run</h2>' +
      row('Date', d.latest_run_date || '-') +
      row('Tickers', (d.tickers_completed || '?') + '/' + (d.tickers_total || '?')) +
      row('News articles', d.news_catalysts_fetched || '-') +
      row('Trades simulated', pv.closed_total || 0) +
      row('Mode', '<span class="chip ' + (d.mode === 'live' ? 'chip-green' : 'chip-gray') + '">' + (d.mode || '-') + '</span>');

    // Results card
    const exp = pv.expectancy_r;
    document.getElementById('result-card').innerHTML = '<h2>📈 Results</h2>' +
      row('Avg return per trade (expectancy)', fmtR(exp), exp > 0 ? 'green' : 'red') +
      row('Win rate', fmtPct(pv.win_rate)) +
      row('Evidence-backed', fmtR(ev.evidence_backed_expectancy_r), ev.evidence_backed_expectancy_r !== null && ev.evidence_backed_expectancy_r <= 0 ? 'red' : 'green') +
      row('Baseline', fmtR(ev.baseline_expectancy_r), ev.baseline_expectancy_r !== null && ev.baseline_expectancy_r <= 0 ? 'red' : 'green') +
      row('Difference', fmtR(ev.evidence_vs_baseline_delta_r), deltaCls(ev.evidence_vs_baseline_delta_r));

    // Edges - what works
    const segs = (d.segment_threshold_recommendations || []).filter(s => s.trade_count >= 5).slice(0, 5);
    document.getElementById('edges-card').innerHTML = '<h2>✅ What Works</h2>' +
      (!segs.length ? '<div class="empty">No proven edges yet</div>' :
      segs.map(s => row(s.segment, fmtR(s.expectancy_r) + ' (' + s.trade_count + ' trades)', 'green')).join(''));

    // Problems - what doesn't
    const worst = (ev.worst_loss_drivers || []).slice(0, 4);
    document.getElementById('problems-card').innerHTML = '<h2>❌ What Doesn\\'t</h2>' +
      (!worst.length ? '<div class="empty">None identified</div>' :
      worst.map(w => row(w.dimension + ': ' + w.segment, fmtR(w.expectancy_r) + ' (' + w.trade_count + ' trades)', 'red')).join(''));

    // Full segment table
    const allSegs = (d.segment_threshold_recommendations || []).filter(s => s.trade_count >= 5);
    const ctxSegs = (d.market_context_segment_recommendations || []).filter(s => s.trade_count >= 5);
    let html = '';
    if (allSegs.length) {
      html += '<div style="font-size:11px;color:#6b7a99;margin-bottom:6px">Strategy + Catalyst</div>' +
        '<table><tr><th>Strategy</th><th>Catalyst</th><th>#</th><th>Exp R</th><th>Win</th></tr>' +
        allSegs.map(s => '<tr><td>' + s.strategy + '</td><td>' + s.catalyst_type + '</td><td>' + s.trade_count + '</td><td class="' + expCls(s.expectancy_r) + '">' + fmtR(s.expectancy_r) + '</td><td>' + fmtPct(s.win_rate) + '</td></tr>').join('') +
        '</table>';
    }
    if (ctxSegs.length) {
      html += '<div style="font-size:11px;color:#6b7a99;margin:10px 0 6px">Strategy + Catalyst + Market Context</div>' +
        '<table><tr><th>Strategy</th><th>Catalyst</th><th>Context</th><th>#</th><th>Exp R</th><th>Win</th></tr>' +
        ctxSegs.map(s => '<tr><td>' + s.strategy + '</td><td>' + s.catalyst_type + '</td><td>' + s.market_context + '</td><td>' + s.trade_count + '</td><td class="' + expCls(s.expectancy_r) + '">' + fmtR(s.expectancy_r) + '</td><td>' + fmtPct(s.win_rate) + '</td></tr>').join('') +
        '</table>';
    }
    document.getElementById('segments-card').innerHTML = '<h2>🏆 Best Setups (with evidence)</h2>' + (html || '<div class="empty">No segments with sufficient data</div>');

    // Tickers
    const top = (d.top_symbols || []).slice(0, 5);
    document.getElementById('tickers-card').innerHTML = '<h2>🏆 Best Tickers</h2>' +
      (!top.length ? '<div class="empty">None</div>' :
      '<table><tr><th>Ticker</th><th>Trades</th><th>Exp R</th><th>Win</th></tr>' +
      top.map(s => '<tr><td class="green">' + s.ticker + '</td><td>' + s.closed_total + '</td><td class="green">' + fmtR(s.expectancy_r) + '</td><td>' + fmtPct(s.win_rate) + '</td></tr>').join('') + '</table>');

    const weak = (d.weak_symbols || []).slice(0, 5);
    document.getElementById('weak-tickers-card').innerHTML = '<h2>📉 Weakest Tickers</h2>' +
      (!weak.length ? '<div class="empty">None</div>' :
      '<table><tr><th>Ticker</th><th>Trades</th><th>Exp R</th><th>Win</th></tr>' +
      weak.map(s => '<tr><td class="red">' + s.ticker + '</td><td>' + s.closed_total + '</td><td class="red">' + fmtR(s.expectancy_r) + '</td><td>' + fmtPct(s.win_rate) + '</td></tr>').join('') + '</table>');

    // Patterns
    const results = d.results || {};
    const hasItems = Object.keys(results).length > 0;
    let patternCounts = {};
    if (hasItems) {
      for (const t in results) {
        for (const item of (results[t].items || [])) {
          const cp = (item.recommendation || {}).chart_pattern;
          if (cp && cp.pattern && cp.pattern !== 'none') {
            const key = cp.direction + ' ' + cp.pattern;
            patternCounts[key] = (patternCounts[key] || 0) + 1;
          }
        }
      }
    }
    const patterns = Object.entries(patternCounts).sort((a,b) => b[1]-a[1]).slice(0, 6);
    document.getElementById('patterns-card').innerHTML = '<h2>🕯️ Candle Patterns</h2>' +
      (!hasItems ? '<div class="empty">Pattern data available in full artifact only</div>' :
      !patterns.length ? '<div class="empty">No patterns detected</div>' :
      patterns.map(p => row(p[0], p[1] + 'x', p[0].startsWith('bullish') ? 'green' : p[0].startsWith('bearish') ? 'red' : '')).join(''));

    // Gate
    const pgStatus = pg.promotion_status || 'no_data';
    const pgCls = pgStatus === 'candidate_for_backtest_confirmation' ? 'green' : pgStatus === 'needs_more_data' ? 'yellow' : 'red';
    document.getElementById('gate-card').innerHTML = '<h2>🚦 Status</h2>' +
      row('Promotion', '<span class="' + pgCls + '">' + (pgStatus || '-') + '</span>') +
      row('Reason', pg.reason || '-') +
      row('Orders enabled', '<span class="green">false</span>') +
      row('Backtest req.', pg.requires_backtest_confirmation ? 'true' : 'false');

  } catch(e) {
    document.getElementById('banner').innerHTML = '<span style="font-size:20px">❌</span> Failed to load: ' + e.message;
  }
}

function row(lbl, val, cls) { return '<div class="row"><span class="lbl">' + lbl + '</span><span class="val' + (cls ? ' ' + cls : '') + '">' + val + '</span></div>'; }
function fmtR(v) { return v === null || v === undefined ? '-' : (v > 0 ? '+' : '') + v.toFixed(2) + 'R'; }
function fmtPct(v) { return v === null || v === undefined ? '-' : (v * 100).toFixed(0) + '%'; }
function deltaCls(v) { return v === null || v === undefined ? '' : v > 0 ? 'green' : 'red'; }
function expCls(v) { return v === null || v === undefined ? '' : v > 0 ? 'green' : 'red'; }

function renderEmpty(d) {
  document.getElementById('banner').className = 'banner banner-gray';
  document.getElementById('banner').innerHTML = '<span style="font-size:20px">⏳</span> No research run yet. First run at 13:00 BST (08:00 ET).';
  document.querySelectorAll('.loading').forEach(el => el.textContent = 'Waiting...');
}

load();
loadPortfolio();
loadAvailableDates();
setInterval(load, 60000);
setInterval(loadPortfolio, 120000);

async function loadAvailableDates() {
  try {
    const res = await fetch('/api/screener/ta/scans');
    const d = await res.json();
    const dates = d.dates || [];
    const sel = document.getElementById('view-date');
    const lbl = document.getElementById('avail-dates');
    if (sel && dates.length) {
      sel.value = dates[dates.length - 1];
      sel.min = dates[0];
      sel.max = dates[dates.length - 1];
    }
    if (lbl) lbl.textContent = dates.join(', ');
  } catch(e) {}
}

async function loadPortfolio() {
  const dateInput = document.getElementById('view-date');
  const dateParam = dateInput && dateInput.value ? '?date=' + dateInput.value : '';
  try {
    const res = await fetch('/api/screener/ta/portfolio' + dateParam);
    if (!res.ok) { return; }
    const d = await res.json();
    const s = d.summary || {};

    if (d.historical) {
      // Show historical scan data
      const picks = d.top_recommendations || [];
      let rows = picks.map(r => '<tr><td style="font-weight:700">' + r.ticker + '</td><td class="gray">' + (r.sector||'') + '</td><td><span class="badge badge-blue">' + r.score + '</span></td><td class="gray">' + (r.screens||[]).slice(0,2).join(', ') + '</td></tr>').join('');
      document.getElementById('portfolio-summary-card').innerHTML = '<h2>📊 Historical Scan — ' + d.scan_date + '</h2><div class="stats-row"><div class="stat"><span class="stat-num gray">' + picks.length + '</span><span class="stat-lbl">Top Picks</span></div></div>';
      document.getElementById('portfolio-trades-card').innerHTML = '<h2>📝 Top Picks on ' + d.scan_date + '</h2><table class="trades-table"><thead><tr><th>Ticker</th><th>Sector</th><th>Score</th><th>Signal</th></tr></thead><tbody>' + rows + '</tbody></table>';
      return;
    }

    // Summary card with big stats
    const avgPnl = d.trades && d.trades.length ? d.trades.reduce((a,t) => a + (t.pnl_pct||0), 0) / d.trades.length : 0;
    const up = d.trades ? d.trades.filter(t => (t.pnl_pct||0) > 0).length : 0;
    const dn = d.trades ? d.trades.filter(t => (t.pnl_pct||0) < 0).length : 0;

    const avgCls = avgPnl > 0 ? 'green' : avgPnl < 0 ? 'red' : 'gray';
    document.getElementById('portfolio-summary-card').innerHTML =
      '<h2>📊 Portfolio P&L</h2>' +
      '<div class="stats-row">' +
        '<div class="stat"><span class="stat-num ' + avgCls + '">' + (avgPnl > 0 ? '+' : '') + avgPnl.toFixed(2) + '%</span><span class="stat-lbl">Avg P&L</span></div>' +
        '<div class="stat"><span class="stat-num blue">' + (s.open||0) + '</span><span class="stat-lbl">Open</span></div>' +
        '<div class="stat"><span class="stat-num gray">' + (s.closed||0) + '</span><span class="stat-lbl">Closed</span></div>' +
        '<div class="stat"><span class="stat-num green">' + (s.wins||0) + '</span><span class="stat-lbl">Wins</span></div>' +
        '<div class="stat"><span class="stat-num red">' + (s.losses||0) + '</span><span class="stat-lbl">Losses</span></div>' +
      '</div>' +
      '<div class="row"><span class="lbl">Win Rate</span><span class="val gray">' + (s.win_rate ? s.win_rate + '%' : '—') + '</span></div>' +
      '<div class="row"><span class="lbl">Expectancy R</span><span class="val ' + (s.expectancy_r > 0 ? 'green' : s.expectancy_r < 0 ? 'red' : 'gray') + '">' + (s.expectancy_r ? s.expectancy_r.toFixed(2) + 'R' : '0.00R') + '</span></div>';

    // Active trades as a TABLE with P&L
    const trades = d.trades || [];
    const active = trades.filter(t => t.status === 'open');
    if (!active.length) {
      document.getElementById('portfolio-trades-card').innerHTML = '<h2>📝 Active Trades</h2><div class="empty">No open trades</div>';
      return;
    }
    let rows = active.map(t => {
      const pnl = t.pnl_pct || 0;
      const pnlCls = pnl > 0 ? 'pct-up' : pnl < 0 ? 'pct-down' : 'pct-flat';
      const pnlStr = (pnl > 0 ? '+' : '') + pnl.toFixed(2) + '%';
      return '<tr>' +
        '<td class="ticker-cell">' + t.ticker + '</td>' +
        '<td>$' + t.entry.toFixed(2) + '</td>' +
        '<td>$' + (t.current_price || t.entry).toFixed(2) + '</td>' +
        '<td class="' + pnlCls + '">' + pnlStr + '</td>' +
        '<td class="gray">$' + t.stop_loss.toFixed(2) + '</td>' +
        '<td><span class="badge badge-blue">' + (t.screens||[]).slice(0,1).join(', ') + '</span></td>' +
      '</tr>';
    }).join('');
    document.getElementById('portfolio-trades-card').innerHTML =
      '<h2>📝 Active Trades</h2>' +
      '<table class="trades-table">' +
        '<thead><tr><th>Ticker</th><th>Entry</th><th>Current</th><th>P&L</th><th>Stop</th><th>Signal</th></tr></thead>' +
        '<tbody>' + rows + '</tbody></table>';
  } catch(e) {
    document.getElementById('portfolio-summary-card').innerHTML = '<h2>📊 Portfolio P&L</h2><div class="empty">Error</div>';
  }
}

async function runTA() {
  const ticker = document.getElementById('ta-ticker').value.trim().toUpperCase();
  const resultDiv = document.getElementById('ta-result');
  if (!ticker) { resultDiv.innerHTML = '<div class="empty">Please enter a ticker</div>'; return; }
  resultDiv.innerHTML = '<div class="loading">Analyzing ' + ticker + '...</div>';
  try {
    const res = await fetch('/api/technicals/' + ticker);
    const d = await res.json();
    const sig = d.signal || 'hold';
    const sigCls = sig.includes('buy') ? 'green' : sig.includes('sell') ? 'red' : 'gray';
    const sup = (d.support_levels || []).slice(0, 3);
    const resL = (d.resistance_levels || []).slice(0, 3);
    const ch = d.channel || {};
    resultDiv.innerHTML =
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">' +
        '<div><div class="row"><span class="lbl">Signal</span><span class="val ' + sigCls + '" style="font-size:16px;font-weight:700">' + sig.toUpperCase() + '</span></div>' +
        '<div class="row"><span class="lbl">Score</span><span class="val ' + sigCls + '">' + (d.score || 0) + '</span></div>' +
        '<div class="row"><span class="lbl">Price</span><span class="val">$' + (d.current_price || 0).toFixed(2) + '</span></div>' +
        '<div class="row"><span class="lbl">Channel</span><span class="val">' + (ch.type || '-') + ' (' + (ch.slope || 0) + ')</span></div>' +
        '<div class="row"><span class="lbl">Volume</span><span class="val">' + (d.volume_trend || '-') + '</span></div>' +
        '<div class="row"><span class="lbl">Divergence</span><span class="val">' + (d.volume_divergence || 'none') + '</span></div>' +
        '</div>' +
        '<div><div style="font-size:11px;color:#6b7a99;margin-bottom:4px">Supports</div>' +
        sup.map(s => '<div class="row"><span class="lbl">$' + s.level.toFixed(2) + '</span><span class="val gray">' + s.strength + ' (' + s.touches + 'x)</span></div>').join('') +
        '<div style="font-size:11px;color:#6b7a99;margin:8px 0 4px">Resistances</div>' +
        resL.map(r => '<div class="row"><span class="lbl">$' + r.level.toFixed(2) + '</span><span class="val gray">' + r.strength + ' (' + r.touches + 'x)</span></div>').join('') +
        '</div>' +
      '</div>' +
      '<div style="margin-top:8px;font-size:11px;color:#6b7a99">Pattern: ' + (d.candle_pattern?.pattern || 'none') + ' • Reasons: ' + (d.reasons || []).join(', ') + '</div>';
  } catch(e) {
    resultDiv.innerHTML = '<div class="empty">❌ Error: ' + e.message + '</div>';
  }
}
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return _DASHBOARD_HTML
