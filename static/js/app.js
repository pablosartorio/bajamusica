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
    pollTimer: null,
};

// ── Referencias al DOM ──────────────────────────────────────
const el = {
    query:         document.getElementById("query"),
    searchBtn:     document.getElementById("searchBtn"),
    controls:      document.getElementById("controls"),
    formatToggle:  document.getElementById("formatToggle"),
    qualityToggle: document.getElementById("qualityToggle"),
    namingToggle:  document.getElementById("namingToggle"),
    destDir:       document.getElementById("destDir"),
    selectAllBtn:  document.getElementById("selectAllBtn"),
    results:       document.getElementById("results"),
    placeholder:   document.getElementById("placeholder"),
    actionbar:     document.getElementById("actionbar"),
    selectedCount: document.getElementById("selectedCount"),
    downloadBtn:   document.getElementById("downloadBtn"),
    progressPanel: document.getElementById("progressPanel"),
    progressList:  document.getElementById("progressList"),
    destNote:      document.getElementById("destNote"),
    closeProgress: document.getElementById("closeProgress"),
    toast:         document.getElementById("toast"),
};

const CHECK_SVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

// ── Búsqueda ────────────────────────────────────────────────
async function runSearch() {
    const q = el.query.value.trim();
    if (!q) return;

    setLoading(true);
    try {
        const res = await fetch(`/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        if (data.error) {
            showToast(`Error en la búsqueda: ${data.error}`);
            return;
        }
        state.results = data.results || [];
        state.selected.clear();
        renderResults();
        updateActionbar();
    } catch (err) {
        showToast("No se pudo conectar con el servidor.");
    } finally {
        setLoading(false);
    }
}

function setLoading(on) {
    el.searchBtn.classList.toggle("is-loading", on);
    el.searchBtn.disabled = on;
}

// ── Render de resultados ────────────────────────────────────
function renderResults() {
    el.results.innerHTML = "";

    if (state.results.length === 0) {
        el.placeholder.hidden = false;
        el.placeholder.querySelector("p").textContent = "No se encontraron resultados.";
        el.controls.hidden = true;
        return;
    }

    el.placeholder.hidden = true;
    el.controls.hidden = false;

    state.results.forEach((item, i) => {
        const card = document.createElement("div");
        card.className = "result";
        card.dataset.id = item.id;
        card.style.animationDelay = `${i * 0.03}s`;

        card.innerHTML = `
            <div class="result__thumb">
                <img src="${item.thumbnail}" alt="" loading="lazy"
                     onerror="this.style.display='none'">
                ${item.duration ? `<span class="result__duration">${item.duration}</span>` : ""}
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
    el.selectedCount.textContent =
        n === 1 ? "1 seleccionado" : `${n} seleccionados`;

    if (state.selected.size !== state.results.length) {
        el.selectAllBtn.textContent = "Seleccionar todo";
    }
}

// ── Descarga ────────────────────────────────────────────────
async function startDownload() {
    const items = state.results.filter((r) => state.selected.has(r.id));
    if (items.length === 0) return;

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
            showToast(data.error);
            return;
        }
        openProgressPanel(items);
        pollProgress(data.job_id);
    } catch (err) {
        showToast("No se pudo iniciar la descarga.");
    }
}

// ── Panel de progreso ───────────────────────────────────────
function openProgressPanel(items) {
    el.progressPanel.hidden = false;
    el.progressList.innerHTML = "";

    items.forEach((item) => {
        const row = document.createElement("div");
        row.className = "prog-item";
        row.dataset.id = item.id;
        row.innerHTML = `
            <div class="prog-item__top">
                <span class="prog-item__title">${escapeHtml(item.title)}</span>
                <span class="prog-item__state">En cola</span>
            </div>
            <div class="prog-bar"><div class="prog-bar__fill"></div></div>
            <div class="prog-item__error" hidden></div>
        `;
        el.progressList.appendChild(row);
    });
}

function pollProgress(jobId) {
    clearInterval(state.pollTimer);

    state.pollTimer = setInterval(async () => {
        try {
            const res = await fetch(`/progress/${jobId}`);
            if (!res.ok) return;
            const job = await res.json();
            renderProgress(job);

            if (job.overall === "done") {
                clearInterval(state.pollTimer);
            }
        } catch (err) {
            clearInterval(state.pollTimer);
        }
    }, 600);
}

const STATE_LABELS = {
    queued:      { txt: "En cola",      cls: "" },
    downloading: { txt: "Bajando",      cls: "" },
    converting:  { txt: "Convirtiendo", cls: "s-convert" },
    tagging:     { txt: "Etiquetando",  cls: "s-convert" },
    done:        { txt: "Listo",        cls: "s-done" },
    error:       { txt: "Error",        cls: "s-error" },
};

function renderProgress(job) {
    job.items.forEach((item) => {
        const row = el.progressList.querySelector(`[data-id="${item.id}"]`);
        if (!row) return;

        const stateEl = row.querySelector(".prog-item__state");
        const fill    = row.querySelector(".prog-bar__fill");
        const errEl   = row.querySelector(".prog-item__error");

        const label = STATE_LABELS[item.state] || STATE_LABELS.queued;
        stateEl.textContent = label.txt;
        stateEl.className = `prog-item__state ${label.cls}`;

        // barra
        fill.classList.remove("is-done", "is-error", "is-indeterminate");
        if (item.state === "done") {
            fill.classList.add("is-done");
            fill.style.width = "100%";
        } else if (item.state === "error") {
            fill.classList.add("is-error");
            fill.style.width = "100%";
        } else if (item.state === "converting") {
            fill.classList.add("is-indeterminate");
        } else {
            fill.style.width = `${item.percent}%`;
        }

        // error
        if (item.state === "error" && item.error) {
            errEl.hidden = false;
            errEl.textContent = item.error;
        }
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
function showToast(msg) {
    el.toast.textContent = msg;
    el.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.toast.hidden = true; }, 4500);
}

// ── Util ────────────────────────────────────────────────────
function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
}

// ── Eventos ─────────────────────────────────────────────────
el.searchBtn.addEventListener("click", runSearch);
el.query.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
});
el.selectAllBtn.addEventListener("click", selectAll);
el.downloadBtn.addEventListener("click", startDownload);
el.closeProgress.addEventListener("click", () => {
    el.progressPanel.hidden = true;
    clearInterval(state.pollTimer);
});

setupToggle(el.formatToggle,  "format");
setupToggle(el.qualityToggle, "quality");
setupToggle(el.namingToggle,  "naming");

// foco inicial en el buscador
el.query.focus();
