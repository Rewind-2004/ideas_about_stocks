const state = {
  items: [],
  watchlist: [],
  selected: null,
};

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function renderList() {
  const ul = document.getElementById('signalList');
  ul.innerHTML = '';
  state.items.forEach((item) => {
    const li = document.createElement('li');
    if (item.is_watch) li.classList.add('watch');
    li.textContent = `${item.symbol} ${item.name} | ${item.direction.toUpperCase()} | ${item.score}`;
    li.onclick = () => renderDetail(item);
    ul.appendChild(li);
  });
}

function listToHtml(id, arr) {
  const ul = document.getElementById(id);
  ul.innerHTML = '';
  arr.forEach((text) => {
    const li = document.createElement('li');
    li.textContent = text;
    ul.appendChild(li);
  });
}

function renderDetail(item) {
  state.selected = item;
  document.getElementById('detailTitle').textContent = `${item.symbol} ${item.name} (${item.market})`;

  const badges = document.getElementById('badges');
  badges.innerHTML = '';
  const main = document.createElement('span');
  main.className = `badge ${item.direction}`;
  main.textContent = item.direction.toUpperCase();
  badges.appendChild(main);

  if (item.is_watch) {
    const watch = document.createElement('span');
    watch.className = 'badge watch';
    watch.textContent = 'WATCH';
    badges.appendChild(watch);
  }

  document.getElementById('scores').textContent = JSON.stringify(
    {
      score: item.score,
      confidence: item.confidence,
      technical: item.technical_score,
      llm: item.llm_score,
      context: item.context_score,
      macro: item.macro_score,
      pattern: item.pattern,
      sector: item.sector,
    },
    null,
    2,
  );

  document.getElementById('zones').textContent = JSON.stringify(
    {
      entry_zone: item.entry_zone,
      stop_loss: item.stop_loss,
      take_profit: item.take_profit,
    },
    null,
    2,
  );

  document.getElementById('kline').textContent = JSON.stringify(item.predicted_kline, null, 2);

  listToHtml('reasons', item.reasons);
  listToHtml('risks', item.risks);
}

async function refreshWatchlist() {
  const data = await api('/api/v1/watchlist');
  state.watchlist = data.watchlist;
  document.getElementById('watchlistText').textContent = `已关注: ${state.watchlist.join(', ') || '无'}`;
}

async function refreshPredictions() {
  const market = document.getElementById('marketFilter').value;
  const query = market ? `?market=${market}` : '';
  const data = await api(`/api/v1/predictions${query}`);
  document.getElementById('meta').textContent = `交易日: ${data.date} | 条目: ${data.count}`;
  state.items = data.items;
  renderList();
  if (state.items[0]) renderDetail(state.items[0]);
}

async function addWatch() {
  const input = document.getElementById('watchSymbol');
  const symbol = input.value.trim();
  if (!symbol) return;
  await api('/api/v1/watchlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol }),
  });
  input.value = '';
  await Promise.all([refreshWatchlist(), refreshPredictions()]);
}

function initEvents() {
  document.getElementById('marketFilter').onchange = refreshPredictions;
  document.getElementById('addWatchBtn').onclick = addWatch;
}

(async function init() {
  initEvents();
  await Promise.all([refreshWatchlist(), refreshPredictions()]);
})();
