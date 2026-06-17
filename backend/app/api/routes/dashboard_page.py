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
  body { background: #0a0e17; color: #e0e6f0; font-family: -apple-system, 'SF Mono', Fira Code, monospace; padding: 20px; }
  h1 { font-size: 18px; font-weight: 600; color: #8899bb; margin-bottom: 16px; }
  h1 span { color: #4a9eff; }
  .banner { padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 10px; }
  .banner-green { background: #052e16; border: 1px solid #166534; color: #22c55e; }
  .banner-yellow { background: #451a03; border: 1px solid #78350f; color: #f59e0b; }
  .banner-red { background: #450a0a; border: 1px solid #7f1d1d; color: #ef4444; }
  .banner-gray { background: #1e293b; border: 1px solid #334155; color: #94a3b8; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 12px; margin-bottom: 12px; }
  .card { background: #111827; border: 1px solid #1e293b; border-radius: 8px; padding: 14px; }
  .card h2 { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #6b7a99; margin-bottom: 10px; }
  .full { grid-column: 1 / -1; }
  .row { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 13px; }
  .row .lbl { color: #8899bb; }
  .row .val { font-weight: 500; }
  .green { color: #22c55e; }
  .red { color: #ef4444; }
  .yellow { color: #f59e0b; }
  .gray { color: #94a3b8; }
  .chip { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
  .chip-green { background: #052e16; color: #22c55e; }
  .chip-red { background: #450a0a; color: #ef4444; }
  .chip-yellow { background: #451a03; color: #f59e0b; }
  .chip-gray { background: #1e293b; color: #8899bb; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; color: #6b7a99; font-weight: 500; padding: 5px 4px; border-bottom: 1px solid #1e293b; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
  td { padding: 5px 4px; border-bottom: 1px solid #1a2233; }
  .loading { color: #6b7a99; font-size: 13px; text-align: center; padding: 30px; }
  .empty { color: #4a5568; font-size: 12px; text-align: center; padding: 16px; }
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
setInterval(load, 60000);

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
