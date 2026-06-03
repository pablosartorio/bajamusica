/* ============================================================
   Sonido · Cassette — lógica principal
   Conectado a la API Flask real (/search, /download, /progress…)
   ============================================================ */

const VU_SEGS        = 18;
const VU_SEGS_MASTER = 28;
const POLL_MS        = 500;

const state = {
  results:  [],
  selected: new Set(),
  format:   'mp3',
  quality:  'high',
  naming:   'youtube',
  pollTimer: null,
  job:      null,
};

const el = {
  query:      document.getElementById('query'),
  searchGo:   document.getElementById('searchGo'),
  plbanner:   document.getElementById('plbanner'),
  plTitle:    document.getElementById('plTitle'),
  plCount:    document.getElementById('plCount'),
  controls:   document.getElementById('controls'),
  destDir:    document.getElementById('destDir'),
  browseBtn:  document.getElementById('browseBtn'),
  rhead:      document.getElementById('rhead'),
  rcount:     document.getElementById('rcount'),
  selectAll:  document.getElementById('selectAll'),
  skeleton:   document.getElementById('skeleton'),
  tracks:     document.getElementById('tracks'),
  placeholder:document.getElementById('placeholder'),
  actionbar:  document.getElementById('actionbar'),
  barCount:   document.getElementById('barCount'),
  barGo:      document.getElementById('barGo'),
  scrim:      document.getElementById('scrim'),
  deck:       document.getElementById('deck'),
  deckClose:  document.getElementById('deckClose'),
  deckSub:    document.getElementById('deckSub'),
  deckList:   document.getElementById('deckList'),
  masterVU:   document.getElementById('masterVU'),
  masterPct:  document.getElementById('masterPct'),
  histTool:   document.getElementById('histTool'),
  histModal:  document.getElementById('histModal'),
  histScrim:  document.getElementById('histScrim'),
  histSub:    document.getElementById('histSub'),
  histList:   document.getElementById('histList'),
  histClose:  document.getElementById('histClose'),
  toast:      document.getElementById('toast'),
  deckReel:   document.getElementById('deckReel'),
};

const CHECK = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

// ── Utilidades ───────────────────────────────────────────────
function esc(str) {
  const d = document.createElement('div');
  d.textContent = str ?? '';
  return d.innerHTML;
}
function fmtBytes(n) {
  if (!n || n <= 0) return '';
  if (n < 1024) return `${n} B`;
  const u = ['KB','MB','GB']; let v = n, i = -1;
  do { v /= 1024; i++; } while (v >= 1024 && i < u.length - 1);
  return `${v.toFixed(v < 10 ? 1 : 0)} ${u[i]}`;
}
function fmtSpeed(bps) { const s = fmtBytes(bps); return s ? `${s}/s` : ''; }
function fmtEta(secs) {
  if (secs == null || secs < 0) return '';
  return `${Math.floor(secs / 60)}:${String(Math.floor(secs % 60)).padStart(2,'0')}`;
}
function isPlaylistUrl(q) {
  try {
    const u = new URL(q.trim());
    return (u.hostname.includes('youtube.com') || u.hostname.includes('youtu.be')) && u.searchParams.has('list');
  } catch { return false; }
}

// ── VU meters ────────────────────────────────────────────────
function buildVU(host, n = VU_SEGS) {
  host.innerHTML = '';
  for (let i = 0; i < n; i++) {
    const s = document.createElement('span');
    s.className = 'seg';
    host.appendChild(s);
  }
}
function setVU(host, pct, n = VU_SEGS) {
  const lit = Math.round((pct / 100) * n);
  [...host.children].forEach((s, i) => {
    s.classList.toggle('lit', i < lit);
    s.classList.toggle('hot', i < lit && i >= n - 3);
  });
}

// ── Toast ────────────────────────────────────────────────────
let toastT;
function showToast(msg, kind = '') {
  el.toast.textContent = msg;
  el.toast.className = 'toast ' + kind;
  el.toast.hidden = false;
  clearTimeout(toastT);
  toastT = setTimeout(() => { el.toast.hidden = true; }, kind === 'ok' ? 4000 : 5000);
}

// ── Búsqueda ─────────────────────────────────────────────────
async function runSearch() {
  const q = el.query.value.trim();
  if (!q) { el.query.focus(); return; }

  el.searchGo.disabled = true;
  el.searchGo.classList.add('loading');
  el.placeholder.hidden = true;
  el.tracks.innerHTML = '';
  el.rhead.hidden = true;
  el.skeleton.hidden = false;

  try {
    let results = [], playlistInfo = null;

    if (isPlaylistUrl(q)) {
      const res  = await fetch(`/expand_playlist?url=${encodeURIComponent(q)}`);
      const data = await res.json();
      if (data.error) { showToast(`Error al cargar playlist: ${data.error}`); return; }
      results = data.results || [];
      playlistInfo = { title: data.title, count: results.length };
    } else {
      const res  = await fetch(`/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      if (data.error) { showToast(`Error en la búsqueda: ${data.error}`); return; }
      results = data.results || [];
    }

    state.results = results;
    state.selected.clear();

    if (playlistInfo) {
      results.forEach(r => state.selected.add(r.id));
      el.plTitle.textContent = playlistInfo.title;
      el.plCount.textContent = results.length + ' temas';
      el.plbanner.hidden = false;
    } else {
      el.plbanner.hidden = true;
    }

    el.controls.hidden = results.length === 0;
    renderTracks();
    updateBar();

    if (playlistInfo) showToast('Playlist cargada · ' + results.length + ' temas', 'ok');
  } catch {
    showToast('No se pudo conectar con el servidor.');
  } finally {
    el.skeleton.hidden = true;
    el.searchGo.disabled = false;
    el.searchGo.classList.remove('loading');
  }
}

// ── Render de tracks ─────────────────────────────────────────
function renderTracks() {
  el.tracks.innerHTML = '';

  if (state.results.length === 0) {
    el.rhead.hidden = true;
    el.placeholder.hidden = false;
    return;
  }

  el.rhead.hidden = false;
  el.placeholder.hidden = true;
  el.rcount.textContent = state.results.length + ' temas encontrados';

  state.results.forEach((r, i) => {
    const sel = state.selected.has(r.id);
    const row = document.createElement('div');
    row.className = 'track' + (sel ? ' sel' : '');
    row.style.animationDelay = i * 24 + 'ms';
    row.dataset.id = r.id;

    const thumbSrc = r.thumbnail || window.PIXEL.cover(r.id);
    const fallback = `onerror="this.src='${window.PIXEL.cover(r.id)}'"`;

    row.innerHTML =
      `<span class="track__num">${String(i + 1).padStart(2, '0')}</span>` +
      `<span class="track__thumb">` +
        `<img src="${esc(thumbSrc)}" alt="" loading="lazy" ${fallback}>` +
        (r.duration ? `<span class="track__dur">${esc(r.duration)}</span>` : '') +
      `</span>` +
      `<span class="track__info">` +
        `<span class="track__title">${esc(r.title)}</span>` +
        `<span class="track__ch">${esc(r.channel)}</span>` +
      `</span>` +
      `<span class="track__size">${fmtBytes(r.bytes)}</span>` +
      `<span class="track__check">${CHECK}</span>`;

    row.addEventListener('click', () => toggleTrack(r.id));
    el.tracks.appendChild(row);
  });
}

function toggleTrack(id) {
  state.selected.has(id) ? state.selected.delete(id) : state.selected.add(id);
  const row = el.tracks.querySelector(`[data-id="${id}"]`);
  if (row) row.classList.toggle('sel', state.selected.has(id));
  updateBar();
}

function updateBar() {
  const n = state.selected.size;
  el.selectAll.textContent =
    n === state.results.length && n > 0 ? 'Deseleccionar todo' : 'Seleccionar todo';
  el.actionbar.hidden = n === 0;
  el.barCount.textContent = n + (n === 1 ? ' tema' : ' temas');
}

function wireSeg(sel, key) {
  document.querySelectorAll(`${sel} button`).forEach(b =>
    b.addEventListener('click', () => {
      document.querySelectorAll(`${sel} button`).forEach(x => x.classList.remove('on'));
      b.classList.add('on');
      state[key] = b.dataset.val;
    })
  );
}

// ── Seleccionar todo ─────────────────────────────────────────
function toggleSelectAll() {
  if (state.selected.size === state.results.length) {
    state.selected.clear();
  } else {
    state.results.forEach(r => state.selected.add(r.id));
  }
  renderTracks();
  updateBar();
}

// ── Carpeta ──────────────────────────────────────────────────
async function browseDir() {
  try {
    const res  = await fetch('/browse_dir');
    const data = await res.json();
    if (data.path) el.destDir.value = data.path;
    else if (data.error) showToast(data.error);
  } catch { showToast('No se pudo abrir el selector de carpeta.'); }
}

// ── Descarga ─────────────────────────────────────────────────
const STATE_PHASE = {
  downloading: 'download', converting: 'convert', tagging: 'convert',
  done: 'done', error: 'error', queued: 'queued',
};
const PHASE_LABEL = {
  queued: 'En cola', download: 'Bajando', convert: 'Convirtiendo', done: 'Listo', error: 'Error',
};

async function startDownload() {
  const items = state.results.filter(r => state.selected.has(r.id));
  if (!items.length) return;

  el.barGo.disabled = true;
  el.barGo.classList.add('loading');

  try {
    const res  = await fetch('/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items,
        format:   state.format,
        quality:  state.quality,
        naming:   state.naming,
        dest_dir: el.destDir.value.trim(),
      }),
    });
    const data = await res.json();
    if (data.error) { showToast(data.error); return; }

    state.job = { id: data.job_id, items, format: state.format };
    openDeck(items);
    pollProgress(data.job_id);
  } catch {
    showToast('No se pudo iniciar la descarga.');
  } finally {
    el.barGo.disabled = false;
    el.barGo.classList.remove('loading');
  }
}

// ── Deck (panel de descarga) ──────────────────────────────────
function openDeck(items) {
  el.scrim.hidden = false;
  el.deck.hidden  = false;
  el.deckSub.textContent = items.length + ' temas · ' + state.format.toUpperCase() + ' · ' + state.quality;

  buildVU(el.masterVU, VU_SEGS_MASTER);
  el.masterPct.textContent = '0%';
  el.deckList.innerHTML = '';

  items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'dtrack';
    row.dataset.id = item.id;
    row.innerHTML =
      `<div class="dtrack__top">` +
        `<span class="dtrack__title">${esc(item.title)}</span>` +
        `<span class="dtrack__state s-queued">En cola</span>` +
      `</div>` +
      `<div class="vu"></div>` +
      `<div class="dtrack__meta">Esperando turno…</div>` +
      `<div class="dtrack__err-msg" hidden></div>`;
    el.deckList.appendChild(row);
    buildVU(row.querySelector('.vu'));
  });
}

function closeDeck() {
  el.scrim.hidden = true;
  el.deck.hidden  = true;
}

// ── Polling de progreso ───────────────────────────────────────
function pollProgress(jobId) {
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/progress/${jobId}`);
      if (!res.ok) { clearInterval(state.pollTimer); return; }
      const job = await res.json();
      renderDeck(job);
      if (job.overall === 'done') {
        clearInterval(state.pollTimer);
        onJobDone(job);
      }
    } catch { clearInterval(state.pollTimer); }
  }, POLL_MS);
}

function renderDeck(job) {
  let effSum = 0;

  job.items.forEach(item => {
    const phase = STATE_PHASE[item.state] || 'queued';
    const pct   = item.state === 'done' || item.state === 'error' ? 100 : (item.percent || 0);
    effSum += pct;

    const row = el.deckList.querySelector(`.dtrack[data-id="${item.id}"]`);
    if (!row) return;

    const stEl  = row.querySelector('.dtrack__state');
    const vuEl  = row.querySelector('.vu');
    const meta  = row.querySelector('.dtrack__meta');
    const errEl = row.querySelector('.dtrack__err-msg');

    stEl.className = 'dtrack__state s-' + phase;
    stEl.textContent = PHASE_LABEL[phase];
    row.classList.toggle('conv', phase === 'convert');
    row.classList.toggle('done', phase === 'done');
    row.classList.toggle('err',  phase === 'error');

    setVU(vuEl, pct);

    errEl.hidden = true;
    if (phase === 'download') {
      const parts = [];
      if (item.total) parts.push(`${fmtBytes(item.downloaded)} / ${fmtBytes(item.total)}`);
      const sp = fmtSpeed(item.speed); if (sp) parts.push(sp);
      const eta = fmtEta(item.eta);   if (eta) parts.push(`faltan ${eta}`);
      meta.textContent = parts.join('  ▸  ') || 'Bajando…';
    } else if (phase === 'convert') {
      meta.textContent = `Convirtiendo a ${(job.format || state.format).toUpperCase()}…`;
    } else if (phase === 'done') {
      meta.textContent = item.filename ? `✓ ${item.filename}` : '✓ Guardado';
    } else if (phase === 'error') {
      meta.textContent = '';
      if (item.error) { errEl.hidden = false; errEl.textContent = item.error; }
    } else {
      meta.textContent = 'Esperando turno…';
    }
  });

  const total = job.items.length || 1;
  const overallPct = Math.round(effSum / total);
  setVU(el.masterVU, overallPct, VU_SEGS_MASTER);
  el.masterPct.textContent = overallPct + '%';
}

function onJobDone(job) {
  const done   = job.items.filter(i => i.state === 'done').length;
  const errors = job.items.filter(i => i.state === 'error').length;
  if (errors && !done) {
    showToast(errors === 1 ? 'No se pudo bajar el archivo.' : `No se pudo bajar ninguno de los ${errors}.`);
  } else if (errors) {
    showToast(`Listo: ${done} archivos · ${errors} con error.`, 'ok');
  } else {
    showToast(`¡Listo! ${done} ${done === 1 ? 'archivo guardado' : 'archivos guardados'}.`, 'ok');
  }
}

// ── Historial ─────────────────────────────────────────────────
async function openHistory() {
  el.histList.innerHTML = '<p class="hist-empty">Cargando…</p>';
  el.histSub.textContent = '';
  el.histModal.hidden = false;
  try {
    const res  = await fetch('/history');
    const data = await res.json();
    renderHistory(data.entries || []);
  } catch {
    el.histList.innerHTML = '<p class="hist-empty">Error al cargar el historial.</p>';
  }
}

function closeHistory() { el.histModal.hidden = true; }

function renderHistory(entries) {
  el.histList.innerHTML = '';
  el.histSub.textContent = entries.length
    ? `${entries.length} ${entries.length === 1 ? 'tarea' : 'tareas'}`
    : '';

  if (!entries.length) {
    el.histList.innerHTML = '<p class="hist-empty">Todavía no hay descargas registradas.</p>';
    return;
  }

  entries.forEach(entry => {
    const div = document.createElement('div');
    div.className = 'hist-entry';
    const date = new Date(entry.created * 1000).toLocaleDateString('es-AR', {
      day: 'numeric', month: 'short', year: 'numeric',
    });
    const done  = entry.items.filter(i => i.state === 'done').length;
    const total = entry.items.length;
    const label = total === 1 ? esc(entry.items[0].title) : `${done} de ${total} archivos`;
    div.innerHTML =
      `<div class="hist-entry__main">` +
        `<span class="hist-entry__label">${label}</span>` +
        `<span class="hist-badge">${esc(entry.format.toUpperCase())}</span>` +
      `</div>` +
      `<div class="hist-entry__meta">` +
        `<span>${date}</span>` +
        `<span class="hist-entry__dir" title="${esc(entry.dest_dir)}">${esc(entry.dest_dir)}</span>` +
      `</div>`;
    el.histList.appendChild(div);
  });
}

// ── Init ─────────────────────────────────────────────────────
buildVU(el.masterVU, VU_SEGS_MASTER);

window.PIXEL.mountCassette(document.getElementById('brandCassette'));
window.PIXEL.mountCassette(document.getElementById('heroCassette'));
window.PIXEL.mountCassette(document.getElementById('placeholderCassette'));
window.PIXEL.mountReel(el.deckReel);

el.searchGo.addEventListener('click', runSearch);
el.query.addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });
el.selectAll.addEventListener('click', toggleSelectAll);
el.barGo.addEventListener('click', startDownload);
el.browseBtn.addEventListener('click', browseDir);
el.deckClose.addEventListener('click', closeDeck);
el.scrim.addEventListener('click', closeDeck);
el.histTool.addEventListener('click', openHistory);
el.histClose.addEventListener('click', closeHistory);
el.histScrim.addEventListener('click', closeHistory);
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { if (!el.histModal.hidden) closeHistory(); else if (!el.deck.hidden) closeDeck(); }
});

wireSeg('#segFormat',  'format');
wireSeg('#segQuality', 'quality');
wireSeg('#segNaming',  'naming');

el.query.focus();
