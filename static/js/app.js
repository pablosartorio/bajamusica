/* ============================================================
   Sonido — lógica del frontend
   ============================================================ */

// ── Estado ──────────────────────────────────────────────────
const state = {
    results: [],            // resultados de la última búsqueda
    selected: new Set(),    // ids seleccionados
    format: "mp3",
    quality: "high",
    naming: "youtube",
    pollTimer: null,        // intervalo de polling (independiente del panel)
    job: null,              // { id, items, active, dest, format }
};

// ── Referencias al DOM ──────────────────────────────────────
const el = {
    query:          document.getElementById("query"),
    searchBtn:      document.getElementById("searchBtn"),
    clearBtn:       document.getElementById("clearBtn"),
    controls:       document.getElementById("controls"),
    formatToggle:   document.getElementById("formatToggle"),
    qualityToggle:  document.getElementById("qualityToggle"),
    namingToggle:   document.getElementById("namingToggle"),
    destDir:        document.getElementById("destDir"),
    browseBtn:      document.getElementById("browseBtn"),
    resultsBar:     document.getElementById("resultsBar"),
    resultsCount:   document.getElementById("resultsCount"),
    selectAllBtn:   document.getElementById("selectAllBtn"),
    results:        document.getElementById("results"),
    placeholder:    document.getElementById("placeholder"),
    placeholderText:document.getElementById("placeholderText"),
    playlistBanner: document.getElementById("playlistBanner"),
    playlistTitle:  document.getElementById("playlistTitle"),
    playlistCount:  document.getElementById("playlistCount"),
    actionbar:      document.getElementById("actionbar"),
    selectedCount:  document.getElementById("selectedCount"),
    downloadBtn:    document.getElementById("downloadBtn"),
    // descargas (panel inline)
    downloadsBtn:   document.getElementById("downloadsBtn"),
    downloads:      document.getElementById("downloads"),
    overallLabel:   document.getElementById("overallLabel"),
    overallFill:    document.getElementById("overallFill"),
    progressList:   document.getElementById("progressList"),
    destNote:       document.getElementById("destNote"),
    closeDownloads: document.getElementById("closeDownloads"),
    // historial (modal)
    historyBtn:     document.getElementById("historyBtn"),
    historyModal:   document.getElementById("historyModal"),
    historyBackdrop:document.getElementById("historyBackdrop"),
    historySub:     document.getElementById("historySub"),
    historyList:    document.getElementById("historyList"),
    closeHistory:   document.getElementById("closeHistory"),
    // varios
    toast:          document.getElementById("toast"),
};

const CHECK_SVG  = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
const FILE_SVG   = `<svg class="file-glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>`;
const FOLDER_SVG = `<svg class="file-glyph" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>`;

// ── Utilidades ──────────────────────────────────────────────
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
}

function isPlaylistUrl(q) {
    try {
        const url = new URL(q.trim());
        return (
            (url.hostname.includes("youtube.com") || url.hostname.includes("youtu.be")) &&
            url.searchParams.has("list")
        );
    } catch {
        return false;
    }
}

function fmtBytes(n) {
    if (n == null || n <= 0) return "";
    if (n < 1024) return `${n} B`;
    const units = ["KB", "MB", "GB"];
    let v = n, i = -1;
    do { v /= 1024; i++; } while (v >= 1024 && i < units.length - 1);
    return `${v.toFixed(v < 10 ? 1 : 0)} ${units[i]}`;
}

function fmtSpeed(bps) {
    const s = fmtBytes(bps);
    return s ? `${s}/s` : "";
}

function fmtEta(secs) {
    if (secs == null || secs < 0) return "";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
}

// ── Búsqueda ────────────────────────────────────────────────
async function runSearch() {
    const q = el.query.value.trim();
    if (!q) return;

    setLoading(true);
    try {
        let results = [];
        let playlistInfo = null;

        if (isPlaylistUrl(q)) {
            const res = await fetch(`/expand_playlist?url=${encodeURIComponent(q)}`);
            const data = await res.json();
            if (data.error) {
                showToast(`Error al cargar playlist: ${data.error}`, "error");
                return;
            }
            results = data.results || [];
            playlistInfo = { title: data.title, count: results.length };
        } else {
            const res = await fetch(`/search?q=${encodeURIComponent(q)}`);
            const data = await res.json();
            if (data.error) {
                showToast(`Error en la búsqueda: ${data.error}`, "error");
                return;
            }
            results = data.results || [];
        }

        state.results = results;
        state.selected.clear();
        renderResults();

        if (playlistInfo) {
            state.results.forEach((r) => state.selected.add(r.id));
            document.querySelectorAll(".result").forEach((c) => c.classList.add("is-selected"));
            el.selectAllBtn.textContent = "Deseleccionar todo";
            showPlaylistBanner(playlistInfo.title, playlistInfo.count);
        } else {
            el.selectAllBtn.textContent = "Seleccionar todo";
            hidePlaylistBanner();
        }

        updateActionbar();
    } catch (err) {
        showToast("No se pudo conectar con el servidor.", "error");
    } finally {
        setLoading(false);
    }
}

function setLoading(on) {
    el.searchBtn.classList.toggle("is-loading", on);
    el.searchBtn.disabled = on;
}

// ── Banner de playlist ──────────────────────────────────────
function showPlaylistBanner(title, count) {
    el.playlistTitle.textContent = title;
    el.playlistCount.textContent = `${count} ${count === 1 ? "canción" : "canciones"}`;
    el.playlistBanner.hidden = false;
}
function hidePlaylistBanner() {
    el.playlistBanner.hidden = true;
}

// ── Render de resultados ────────────────────────────────────
function renderResults() {
    el.results.innerHTML = "";

    if (state.results.length === 0) {
        el.placeholder.hidden = false;
        el.placeholderText.textContent = "No se encontraron resultados. Probá con otra búsqueda.";
        el.controls.hidden = true;
        el.resultsBar.hidden = true;
        hidePlaylistBanner();
        return;
    }

    el.placeholder.hidden = true;
    el.controls.hidden = false;
    el.resultsBar.hidden = false;
    el.resultsCount.textContent =
        `${state.results.length} ${state.results.length === 1 ? "resultado" : "resultados"}`;

    state.results.forEach((item, i) => {
        const card = document.createElement("div");
        card.className = "result";
        card.dataset.id = item.id;
        card.style.animationDelay = `${Math.min(i, 12) * 0.03}s`;

        card.innerHTML = `
            <div class="result__thumb">
                <img src="${item.thumbnail}" alt="" loading="lazy"
                     onerror="this.style.display='none'">
                ${item.duration ? `<span class="result__duration">${escapeHtml(item.duration)}</span>` : ""}
            </div>
            <div class="result__info">
                <div class="result__title">${escapeHtml(item.title)}</div>
                <div class="result__channel">${escapeHtml(item.channel)}</div>
            </div>
            <div class="result__check">${CHECK_SVG}</div>
        `;

        card.addEventListener("click", () => toggleSelect(item.id, card));
        el.results.appendChild(card);
    });
}

// ── Selección ───────────────────────────────────────────────
function toggleSelect(id, card) {
    if (state.selected.has(id)) {
        state.selected.delete(id);
        card.classList.remove("is-selected");
    } else {
        state.selected.add(id);
        card.classList.add("is-selected");
    }
    updateActionbar();
}

function selectAll() {
    const allSelected = state.selected.size === state.results.length;
    state.selected.clear();

    document.querySelectorAll(".result").forEach((card) => {
        if (allSelected) {
            card.classList.remove("is-selected");
        } else {
            state.selected.add(card.dataset.id);
            card.classList.add("is-selected");
        }
    });

    el.selectAllBtn.textContent = allSelected ? "Seleccionar todo" : "Deseleccionar todo";
    updateActionbar();
}

function updateActionbar() {
    const n = state.selected.size;
    el.actionbar.hidden = n === 0;
    el.selectedCount.textContent = n === 1 ? "1 seleccionado" : `${n} seleccionados`;

    if (state.selected.size !== state.results.length) {
        el.selectAllBtn.textContent = "Seleccionar todo";
    } else if (state.results.length > 0) {
        el.selectAllBtn.textContent = "Deseleccionar todo";
    }
}

// ── Selector de carpeta ─────────────────────────────────────
async function browseDir() {
    try {
        const res = await fetch("/browse_dir");
        const data = await res.json();
        if (data.path) {
            el.destDir.value = data.path;
        } else if (data.error) {
            showToast(data.error, "error");
        }
    } catch {
        showToast("No se pudo abrir el selector de carpeta.", "error");
    }
}

// ── Descarga ────────────────────────────────────────────────
async function startDownload() {
    const items = state.results.filter((r) => state.selected.has(r.id));
    if (items.length === 0) return;

    setDownloadLoading(true);
    try {
        const res = await fetch("/download", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                items,
                format:   state.format,
                quality:  state.quality,
                naming:   state.naming,
                dest_dir: el.destDir.value.trim(),
            }),
        });
        const data = await res.json();
        if (data.error) {
            showToast(data.error, "error");
            return;
        }

        state.job = {
            id: data.job_id,
            items,
            active: true,
            dest: el.destDir.value.trim() || el.destDir.placeholder,
            format: state.format,
        };
        buildProgressList(state.job);
        showDownloads();
        pollProgress(data.job_id);
    } catch (err) {
        showToast("No se pudo iniciar la descarga.", "error");
    } finally {
        setDownloadLoading(false);
    }
}

function setDownloadLoading(on) {
    el.downloadBtn.classList.toggle("is-loading", on);
    el.downloadBtn.disabled = on;
}

// ── Panel de descargas (inline) ─────────────────────────────
function buildProgressList(job) {
    el.progressList.innerHTML = "";
    el.overallFill.classList.remove("is-done");
    el.overallFill.style.width = "0%";
    el.overallLabel.textContent = `0 de ${job.items.length} listos`;

    el.destNote.hidden = !job.dest;
    el.destNote.innerHTML = job.dest
        ? `${FOLDER_SVG}<span class="meta-name">${escapeHtml(job.dest)}</span>`
        : "";

    job.items.forEach((item) => {
        const row = document.createElement("div");
        row.className = "prog-item";
        row.dataset.id = item.id;
        row.innerHTML = `
            <div class="prog-item__top">
                <span class="prog-item__title">${escapeHtml(item.title)}</span>
                <span class="prog-item__state">En cola</span>
            </div>
            <div class="prog-bar"><div class="prog-bar__fill"></div></div>
            <div class="prog-item__meta"></div>
            <div class="prog-item__error" hidden></div>
        `;
        el.progressList.appendChild(row);
    });
}

function showDownloads() {
    el.downloads.hidden = false;
    el.downloadsBtn.hidden = false;
    el.downloads.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function hideDownloads() {
    el.downloads.hidden = true;
}
function toggleDownloads() {
    if (el.downloads.hidden) showDownloads();
    else hideDownloads();
}

function pollProgress(jobId) {
    clearInterval(state.pollTimer);
    state.pollTimer = setInterval(async () => {
        try {
            const res = await fetch(`/progress/${jobId}`);
            if (!res.ok) { clearInterval(state.pollTimer); return; }
            const job = await res.json();
            renderProgress(job);
            if (job.overall === "done") {
                clearInterval(state.pollTimer);
                onJobDone(job);
            }
        } catch (err) {
            clearInterval(state.pollTimer);
        }
    }, 500);
}

const STATE_LABELS = {
    queued:      { txt: "En cola",      cls: "" },
    downloading: { txt: "Bajando",      cls: "s-download" },
    converting:  { txt: "Convirtiendo", cls: "s-convert" },
    tagging:     { txt: "Etiquetando",  cls: "s-convert" },
    done:        { txt: "Listo",        cls: "s-done" },
    error:       { txt: "Error",        cls: "s-error" },
};

function renderProgress(job) {
    let done = 0, errors = 0, effSum = 0;

    job.items.forEach((item) => {
        if (item.state === "done") done++;
        else if (item.state === "error") errors++;
        effSum += (item.state === "done" || item.state === "error") ? 100 : (item.percent || 0);

        const row = el.progressList.querySelector(`.prog-item[data-id="${item.id}"]`);
        if (row) updateProgRow(row, item, job);
    });

    const total = job.items.length || 1;
    el.overallFill.style.width = `${Math.round(effSum / total)}%`;

    const allDone = (done + errors) === job.items.length;
    if (allDone) el.overallFill.classList.add("is-done");

    el.overallLabel.textContent = allDone
        ? `Completado · ${done} de ${job.items.length}${errors ? ` · ${errors} con error` : ""}`
        : `${done} de ${job.items.length} listos${errors ? ` · ${errors} con error` : ""}`;
}

function updateProgRow(row, item, job) {
    const stateEl = row.querySelector(".prog-item__state");
    const fill    = row.querySelector(".prog-bar__fill");
    const metaEl  = row.querySelector(".prog-item__meta");
    const errEl   = row.querySelector(".prog-item__error");

    const label = STATE_LABELS[item.state] || STATE_LABELS.queued;
    stateEl.textContent = label.txt;
    stateEl.className = `prog-item__state ${label.cls}`;

    row.classList.toggle("is-done", item.state === "done");
    row.classList.toggle("is-error", item.state === "error");

    // — barra sólida, siempre con un ancho concreto —
    fill.className = "prog-bar__fill";
    if (item.state === "done") {
        fill.classList.add("is-done");
        fill.style.width = "100%";
    } else if (item.state === "error") {
        fill.classList.add("is-error");
        fill.style.width = "100%";
    } else {
        // queued=0, downloading=%, converting/tagging=99 (lo fija el backend)
        fill.style.width = `${item.percent || 0}%`;
    }

    // — meta (velocidad / ETA / tamaño / archivo) —
    errEl.hidden = true;
    metaEl.classList.remove("is-done");
    metaEl.innerHTML = "";

    if (item.state === "error") {
        if (item.error) {
            errEl.hidden = false;
            errEl.textContent = item.error;
        }
    } else if (item.state === "done") {
        metaEl.classList.add("is-done");
        metaEl.innerHTML = `${FILE_SVG}<span class="meta-name">${escapeHtml(item.filename || "Guardado")}</span>`;
    } else if (item.state === "converting") {
        metaEl.textContent = `Convirtiendo a ${(job.format || "mp3").toUpperCase()}…`;
    } else if (item.state === "tagging") {
        metaEl.textContent = "Buscando metadatos…";
    } else if (item.state === "downloading") {
        const parts = [];
        if (item.total) parts.push(`${fmtBytes(item.downloaded)} / ${fmtBytes(item.total)}`);
        const sp = fmtSpeed(item.speed);
        if (sp) parts.push(sp);
        const eta = fmtEta(item.eta);
        if (eta) parts.push(`faltan ${eta}`);
        metaEl.innerHTML = parts.length
            ? parts.map(escapeHtml).join('<span class="dot">·</span>')
            : "Bajando…";
    } else {
        metaEl.textContent = "En cola";
    }
}

function onJobDone(job) {
    if (state.job) state.job.active = false;
    const done = job.items.filter((i) => i.state === "done").length;
    const errors = job.items.filter((i) => i.state === "error").length;

    if (errors && !done) {
        showToast(errors === 1 ? "No se pudo bajar el archivo." : `No se pudo bajar ninguno de los ${errors}.`, "error");
    } else if (errors) {
        showToast(`Listo: ${done} ${done === 1 ? "archivo" : "archivos"} · ${errors} con error.`, "ok");
    } else {
        showToast(`Listo: ${done} ${done === 1 ? "archivo guardado" : "archivos guardados"}.`, "ok");
    }
}

// ── Historial (modal) ───────────────────────────────────────
async function openHistory() {
    el.historyList.innerHTML = '<p class="hist-empty">Cargando…</p>';
    el.historySub.textContent = "";
    el.historyModal.hidden = false;
    try {
        const res = await fetch("/history");
        const data = await res.json();
        renderHistory(data.entries || []);
    } catch (err) {
        el.historyList.innerHTML = `<p class="hist-empty">Error al cargar el historial.</p>`;
    }
}
function closeHistory() {
    el.historyModal.hidden = true;
}

function renderHistory(entries) {
    el.historyList.innerHTML = "";
    el.historySub.textContent = entries.length
        ? `${entries.length} ${entries.length === 1 ? "tarea" : "tareas"}`
        : "";

    if (!entries.length) {
        el.historyList.innerHTML =
            '<p class="hist-empty">Todavía no hay descargas registradas.</p>';
        return;
    }

    entries.forEach((entry) => {
        const div = document.createElement("div");
        div.className = "hist-entry";

        const date = new Date(entry.created * 1000);
        const dateStr = date.toLocaleDateString("es-AR", {
            day: "numeric", month: "short", year: "numeric",
        });
        const doneCount = entry.items.filter((it) => it.state === "done").length;
        const total = entry.items.length;
        const label =
            total === 1
                ? escapeHtml(entry.items[0].title)
                : `${doneCount} de ${total} archivos`;

        div.innerHTML = `
            <div class="hist-entry__main">
                <span class="hist-entry__label">${label}</span>
                <span class="hist-badge">${escapeHtml(entry.format.toUpperCase())}</span>
            </div>
            <div class="hist-entry__meta">
                <span class="hist-entry__date">${dateStr}</span>
                <span class="hist-entry__dir" title="${escapeHtml(entry.dest_dir)}">${escapeHtml(entry.dest_dir)}</span>
            </div>
        `;
        el.historyList.appendChild(div);
    });
}

// ── Toggles ─────────────────────────────────────────────────
function setupToggle(container, key) {
    container.addEventListener("click", (e) => {
        const btn = e.target.closest(".seg");
        if (!btn) return;
        container.querySelectorAll(".seg").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state[key] = btn.dataset[key];
    });
}

// ── Toast ───────────────────────────────────────────────────
let toastTimer = null;
function showToast(msg, kind = "error") {
    el.toast.textContent = msg;
    el.toast.className = `toast toast--${kind}`;
    el.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.toast.hidden = true; }, kind === "ok" ? 4000 : 5000);
}

// ── Campo de búsqueda: botón limpiar ────────────────────────
function syncClearBtn() {
    el.clearBtn.hidden = el.query.value.length === 0;
}

// ── Eventos ─────────────────────────────────────────────────
el.searchBtn.addEventListener("click", runSearch);
el.query.addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
el.query.addEventListener("input", syncClearBtn);
el.clearBtn.addEventListener("click", () => {
    el.query.value = "";
    syncClearBtn();
    el.query.focus();
});
el.selectAllBtn.addEventListener("click", selectAll);
el.downloadBtn.addEventListener("click", startDownload);
el.browseBtn.addEventListener("click", browseDir);

el.downloadsBtn.addEventListener("click", toggleDownloads);
el.closeDownloads.addEventListener("click", hideDownloads);

el.historyBtn.addEventListener("click", openHistory);
el.closeHistory.addEventListener("click", closeHistory);
el.historyBackdrop.addEventListener("click", closeHistory);
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !el.historyModal.hidden) closeHistory();
});

setupToggle(el.formatToggle,  "format");
setupToggle(el.qualityToggle, "quality");
setupToggle(el.namingToggle,  "naming");

el.query.focus();
