// ─── State ───────────────────────────────────────────────────────────────
const S = { items: [], watchlist: [], filter: 'all', market: '' };

// ─── API ──────────────────────────────────────────────────────────────────
async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// ─── SVG Candle Chart ─────────────────────────────────────────────────────
// Draws two candles side-by-side: yesterday (dimmed) and today predicted (vivid).
function candleSVG(prev, pred, dir) {
  const W = 154, H = 68, bw = 18, gap = 12;
  const x1 = 14, x2 = x1 + bw + gap;

  const all = [prev.open, prev.high, prev.low, prev.close,
    pred.open, pred.high, pred.low, pred.close];
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const pad = Math.max((hi - lo) * 0.12, lo * 0.004);
  const min = lo - pad, max = hi + pad, range = max - min;
  const sy = v => H - ((v - min) / range) * H;

  const color = dir === 'bull' ? '#00e87a' : dir === 'bear' ? '#ff3b5c' : '#9ca3af';

  const candle = ({ open: o, high: h, low: l, close: c }, x, dimmed) => {
    const isBull = c >= o;
    const cc = dimmed ? (isBull ? '#22c55e' : '#ef4444') : color;
    const op = dimmed ? 0.42 : 1;
    const sw = dimmed ? 1 : 1.5;
    const by = sy(Math.max(o, c));
    const bh = Math.max(Math.abs(sy(o) - sy(c)), 2);
    return `
      <line x1="${x + bw / 2}" y1="${sy(h)}" x2="${x + bw / 2}" y2="${sy(l)}"
            stroke="${cc}" stroke-width="${sw}" opacity="${op}"/>
      <rect x="${x}" y="${by}" width="${bw}" height="${bh}" rx="1"
            fill="${isBull ? cc : 'none'}" stroke="${cc}"
            stroke-width="${sw}" opacity="${op}"/>`;
  };

  return `<svg viewBox="0 0 ${W} ${H + 18}" xmlns="http://www.w3.org/2000/svg"
               style="width:${W}px;height:${H + 18}px;overflow:visible;display:block">
    ${candle(prev, x1, true)}
    ${candle(pred, x2, false)}
    <text x="${x1 + bw / 2}" y="${H + 13}" text-anchor="middle"
          fill="#4a5568" font-size="9" font-family="monospace">昨日</text>
    <text x="${x2 + bw / 2}" y="${H + 13}" text-anchor="middle"
          fill="${color}" font-size="9" font-family="monospace">预测</text>
  </svg>`;
}

// ─── Helpers ─────────────────────────────────────────────────────────────
function changePct(item) {
  return ((item.predicted_kline.close - item.prev_kline.close)
    / item.prev_kline.close * 100);
}
const cur = item => item.market === 'CN' ? '¥' : '$';
const fmt = (item, v) => `${cur(item)}${v.toFixed(item.market === 'CN' && v > 100 ? 1 : 2)}`;

// ─── Card ─────────────────────────────────────────────────────────────────
function makeCard(item) {
  const dir = item.direction;
  const sign = dir === 'bull' ? '▲' : dir === 'bear' ? '▼' : '—';
  const chg = changePct(item);

  return `
    <div class="stock-card ${dir}${item.is_watch ? ' is-watch' : ''}"
         onclick="openModal('${item.symbol}')">
      ${item.is_watch ? '<div class="watch-tag">WATCHLIST</div>' : ''}
      <div class="card-top">
        <div class="card-meta">
          <div class="card-code">
            <span class="code-badge ${dir}">${item.market} · ${item.symbol}</span>
            <span class="sector-tag">${item.sector}</span>
          </div>
          <div class="card-name">${item.name}</div>
        </div>
        <div class="card-change">
          <span class="change-pct ${dir}">${sign} ${Math.abs(chg).toFixed(2)}%</span>
          <span class="change-price">${fmt(item, item.prev_kline.close)}</span>
        </div>
      </div>
      <div class="card-bottom">
        <div>${candleSVG(item.prev_kline, item.predicted_kline, dir)}</div>
        <div class="card-right">
          <div class="conf-label">置信度</div>
          <div class="conf-row">
            <div class="conf-track">
              <div class="conf-fill ${dir}" style="width:${item.confidence}%"></div>
            </div>
            <span class="conf-pct ${dir}">${Math.round(item.confidence)}%</span>
          </div>
          <div class="card-cta">查看分析 →</div>
        </div>
      </div>
    </div>`;
}

// ─── Modal ────────────────────────────────────────────────────────────────
function openModal(symbol) {
  const item = S.items.find(x => x.symbol === symbol);
  if (!item) return;

  const dir = item.direction;
  const color = dir === 'bull' ? '#00e87a' : dir === 'bear' ? '#ff3b5c' : '#9ca3af';
  const label = dir === 'bull' ? '▲ 看涨' : dir === 'bear' ? '▼ 看跌' : '— 中性';

  const ohlc = ['open', 'high', 'low', 'close'].map((k, i) => {
    const lbls = ['预测开', '预测高', '预测低', '预测收'];
    return `<div>
      <div class="ohlc-lbl">${lbls[i]}</div>
      <div class="ohlc-val" style="color:${color}">${fmt(item, item.predicted_kline[k])}</div>
    </div>`;
  }).join('');

  const reasons = item.reasons.map((r, i) => `
    <div class="reason-row">
      <div class="reason-num" style="background:${color}18;border:1px solid ${color}30;color:${color}">${i + 1}</div>
      <div class="reason-txt">${r}</div>
    </div>`).join('');

  const risks = item.risks.map(r => `
    <div class="risk-row">
      <div class="risk-dot"></div>
      <div class="risk-txt">${r}</div>
    </div>`).join('');

  const scoreRows = [
    { lbl: '技术信号', val: item.technical_score, wt: '35%' },
    { lbl: 'LLM 分析', val: item.llm_score, wt: '30%' },
    { lbl: '历史上下文', val: item.context_score, wt: '25%' },
    { lbl: '宏观背景', val: item.macro_score, wt: '10%' },
  ].map(({ lbl, val, wt }) => `
    <div class="score-box">
      <div class="score-hd">
        <span class="score-lbl">${lbl}</span>
        <span class="score-wt">${wt}</span>
      </div>
      <div class="score-val" style="color:${color}">${val.toFixed(1)}</div>
      <div class="score-bar">
        <div class="score-fill" style="width:${val}%;background:${color}"></div>
      </div>
    </div>`).join('');

  document.getElementById('modalBody').innerHTML = `
    <div class="m-meta" style="color:${color}">${item.market} · ${item.symbol} · ${item.sector} · ${item.pattern}</div>
    <div class="m-title">${item.name}</div>

    <div class="m-signal-box" style="background:${color}0c;border:1px solid ${color}28">
      <div class="m-signal-label" style="color:${color}">
        信号：${label} &nbsp;·&nbsp; 综合评分 ${item.score.toFixed(1)} &nbsp;·&nbsp; 置信度 ${Math.round(item.confidence)}%
      </div>
      <div class="ohlc-grid">${ohlc}</div>
    </div>

    <div class="m-section">// 分析依据</div>${reasons}
    <div class="m-section">// 主要风险</div>${risks}

    <div class="m-section">// 价格区间参考</div>
    <div class="zones-grid">
      <div class="zone-box">
        <div class="zone-lbl">建议买入区间</div>
        <div class="zone-val" style="color:${color}">
          ${fmt(item, item.entry_zone.low)} – ${fmt(item, item.entry_zone.high)}
        </div>
      </div>
      <div class="zone-box">
        <div class="zone-lbl">止损参考</div>
        <div class="zone-val" style="color:#ff3b5c">${fmt(item, item.stop_loss)}</div>
      </div>
      <div class="zone-box">
        <div class="zone-lbl">止盈参考</div>
        <div class="zone-val" style="color:#00e87a">${fmt(item, item.take_profit)}</div>
      </div>
    </div>

    <div class="m-section">// 评分拆解</div>
    <div class="score-grid">${scoreRows}</div>

    <div class="m-disclaimer">⚠ 本预测仅供参考，不构成投资建议。市场有风险，入市需谨慎。</div>`;

  document.getElementById('modalOverlay').classList.add('open');
}

function closeModal() {
  document.getElementById('modalOverlay').classList.remove('open');
}

// expose for inline onclick
window.openModal = openModal;
window.removeWatch = removeWatch;

// ─── Render ───────────────────────────────────────────────────────────────
function visible() {
  return S.items.filter(item => {
    if (S.filter === 'bull' && item.direction !== 'bull') return false;
    if (S.filter === 'bear' && item.direction !== 'bear') return false;
    if (S.filter === 'watch' && !item.is_watch) return false;
    return true;
  });
}

function renderCards() {
  const items = visible();
  document.getElementById('cardGrid').innerHTML = items.length
    ? items.map(makeCard).join('')
    : '<div class="loading-msg">暂无符合条件的标的</div>';
}

function renderWatchlist() {
  const el = document.getElementById('watchItems');
  if (!S.watchlist.length) {
    el.innerHTML = '<div class="watch-empty">还没有自选股<br/>输入代码开始关注</div>';
    return;
  }
  el.innerHTML = S.watchlist.map(code => {
    const m = S.items.find(x => x.symbol === code);
    const cc = m?.direction === 'bull' ? '#00e87a' : m?.direction === 'bear' ? '#ff3b5c' : '#9ca3af';
    const chg = m ? `<span class="wi-chg" style="color:${cc}">
      ${m.direction === 'bull' ? '▲' : m.direction === 'bear' ? '▼' : '—'}
      ${Math.abs(changePct(m)).toFixed(2)}%
    </span>` : '<span class="wi-chg" style="color:#2d3748">暂无数据</span>';
    return `<div class="watch-item">
      <div>
        <div class="wi-code">${code}</div>
        <div class="wi-name">${m ? m.name : '—'}</div>
      </div>
      <div class="wi-right">
        ${chg}
        <button class="wi-del" onclick="removeWatch('${code}')">✕</button>
      </div>
    </div>`;
  }).join('');
}

function updateSummary(data) {
  document.getElementById('summaryBull').textContent = `▲ ${data.bull_count ?? 0} 看涨`;
  document.getElementById('summaryBear').textContent = `▼ ${data.bear_count ?? 0} 看跌`;
}

// ─── Data ─────────────────────────────────────────────────────────────────
async function fetchAll() {
  const q = S.market ? `?market=${S.market}` : '';
  const [data, wl] = await Promise.all([
    api(`/api/v1/predictions${q}`),
    api('/api/v1/watchlist'),
  ]);
  S.items = data.items;
  S.watchlist = wl.watchlist;
  updateSummary(data);
  renderCards();
  renderWatchlist();
}

async function addWatch() {
  const input = document.getElementById('watchInput');
  const symbol = input.value.trim();
  if (!symbol) return;
  try {
    const wl = await api('/api/v1/watchlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol }),
    });
    S.watchlist = wl.watchlist;
    input.value = '';
    flash(`✓ 已添加 ${symbol.toUpperCase()}`);
    await fetchAll();
  } catch {
    flash('添加失败，请检查代码格式');
  }
}

async function removeWatch(symbol) {
  await api(`/api/v1/watchlist/${symbol}`, { method: 'DELETE' });
  await fetchAll();
}

function flash(msg) {
  const el = document.getElementById('watchMsg');
  el.textContent = msg;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.textContent = ''; }, 2800);
}

// ─── Clock ────────────────────────────────────────────────────────────────
function tick() {
  const n = new Date();
  document.getElementById('clockLabel').textContent =
    `${n.toLocaleDateString('zh-CN')}  ${n.toLocaleTimeString('zh-CN')}`;
}

// ─── Events ───────────────────────────────────────────────────────────────
function initEvents() {
  // Filter tabs
  document.querySelectorAll('.filter-btn').forEach(btn =>
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      S.filter = btn.dataset.filter;
      renderCards();
    })
  );

  // Market buttons
  document.querySelectorAll('.market-btn').forEach(btn =>
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.market-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      S.market = btn.dataset.market;
      await fetchAll();
    })
  );

  // Sidebar
  document.getElementById('sidebarToggle').addEventListener('click', () => {
    const open = document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('sidebarToggle').classList.toggle('open', open);
  });

  // Watchlist
  document.getElementById('watchAdd').addEventListener('click', addWatch);
  document.getElementById('watchInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') addWatch();
  });

  // Modal
  document.getElementById('modalClose').addEventListener('click', closeModal);
  document.getElementById('modalOverlay').addEventListener('click', e => {
    if (e.target.id === 'modalOverlay') closeModal();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
}

// ─── Init ─────────────────────────────────────────────────────────────────
(async function init() {
  tick();
  setInterval(tick, 1000);
  initEvents();
  await fetchAll();
}());
