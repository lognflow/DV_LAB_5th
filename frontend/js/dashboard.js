/**
 * Global Deforestation Analytics - Interactive Frontend Controller
 */

const state = {
    continents: ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"],
    allContinents: [],
    allCountries: [],
    causes: [],
    focus_country: "All Countries",
    start_year: 1990,
    end_year: 2025,
    snapshot_year: 2020,
    cause: "All Causes",
    unit: "Million Hectares (Mha)",
    map_mode: "period_change",
    map_scope: "world",
    treemap_mode: "loss",
    primary_country: "Brazil",
    compare_countries: ["Brazil", "Indonesia", "Democratic Republic of Congo", "China", "Canada"],
    compare_metric: "Forest_Area_Mha",
    normalize_compare: true,
    country_secondary_view: "commodity",
    top_n: 10,
    recovery_countries: ["China", "India", "Vietnam", "France", "Spain", "Costa Rica"],
    regional_metric: "Forest_Area_Mha",
    activeTab: "overview",
    staleTabs: new Set(["overview", "country", "causes", "hotspots", "regional", "data"])
};

const PLOT_IDS = [
    "chart-overview-heatmap", "chart-overview-trend", "chart-overview-secondary", "chart-overview-treemap",
    "chart-country-zoom", "chart-country-deep", "chart-country-cause", "chart-country-secondary",
    "chart-compare-lines", "chart-compare-radar", "chart-compare-heatmap",
    "chart-causes-pie", "chart-causes-comm", "chart-causes-stacked", "chart-causes-sunburst", "chart-causes-all-heat",
    "chart-cause-spec-map", "chart-cause-spec-top", "chart-cause-spec-traj", "chart-cause-spec-share", "chart-cause-spec-heat",
    "chart-hotspots-loss", "chart-hotspots-gain", "chart-hotspots-dumbbell", "chart-hotspots-scatter", "chart-hotspots-recovery",
    "chart-regional-lines", "chart-regional-co2", "chart-regional-rli"
];

function setLoading(isLoading) {
    const bar = document.getElementById("loading-bar");
    if (bar) {
        bar.classList.toggle("hidden", !isLoading);
    }
}

function resizeAllPlots() {
    PLOT_IDS.forEach((id) => {
        const el = document.getElementById(id);
        if (el && el.data) {
            try {
                Plotly.Plots.resize(el);
            } catch (_) {}
        }
    });
}

function renderPlotly(containerId, figDict, onClickHandler = null) {
    const el = document.getElementById(containerId);
    if (!el || !figDict) return;

    const traces = figDict.data || [];
    const layout = Object.assign({}, figDict.layout || {}, {
        autosize: true
    });
    const config = {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ["lasso2d", "select2d"]
    };

    const isGeo = traces.some((t) => t && (t.type === "choropleth" || t.type === "scattergeo"));
    const drawPromise = isGeo
        ? Plotly.newPlot(el, traces, layout, config)
        : Plotly.react(el, traces, layout, config);

    drawPromise.then(() => {
        if (onClickHandler) {
            el.removeAllListeners && el.removeAllListeners("plotly_click");
            el.on("plotly_click", onClickHandler);
        }
    });
}

function updateStatusRibbon() {
    const scopeEl = document.getElementById("pill-scope");
    const yearsEl = document.getElementById("pill-years");
    const causeEl = document.getElementById("pill-cause");

    let scopeTxt = state.focus_country !== "All Countries"
        ? state.focus_country
        : (state.continents.length === 6 ? "Global (6 Continents)" : state.continents.join(", "));
    scopeEl.textContent = `Scope: ${scopeTxt}`;
    yearsEl.textContent = `${state.start_year}–${state.end_year} (Snap: ${state.snapshot_year})`;
    causeEl.textContent = `Cause: ${state.cause}`;
}

function markAllStale() {
    state.staleTabs = new Set(["overview", "country", "causes", "hotspots", "regional", "data"]);
    updateStatusRibbon();
}

function buildPayload() {
    return {
        continents: state.continents,
        focus_country: state.focus_country,
        start_year: state.start_year,
        end_year: state.end_year,
        snapshot_year: state.snapshot_year,
        cause: state.cause,
        unit: state.unit,
        map_mode: state.map_mode,
        map_scope: state.map_scope,
        treemap_mode: state.treemap_mode,
        primary_country: state.primary_country,
        compare_countries: state.compare_countries,
        compare_metric: state.compare_metric,
        normalize_compare: state.normalize_compare,
        country_secondary_view: state.country_secondary_view,
        top_n: state.top_n,
        recovery_countries: state.recovery_countries,
        regional_metric: state.regional_metric
    };
}

function renderKPIs(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = items.map((k) => {
        const tone = k.tone || "neutral";
        const valClass = tone === "loss" ? "loss" : (tone === "gain" ? "gain" : "");
        return `
            <div class="kpi-card ${tone}">
                <div class="kpi-label">${escapeHtml(k.label)}</div>
                <div class="kpi-value ${valClass}">${escapeHtml(k.value)}</div>
                <div class="kpi-subtext">${escapeHtml(k.subtext || "")}</div>
            </div>
        `;
    }).join("");
}

function renderDataTable(containerId, columns, rows, formatters = {}) {
    const wrap = document.getElementById(containerId);
    if (!wrap) return;
    if (!rows || rows.length === 0) {
        wrap.innerHTML = `<div style="padding:1.2rem; color:#475569; font-weight:600;">Data Not Available for the current filter selection.</div>`;
        return;
    }

    const ths = columns.map((c) => `<th>${escapeHtml(c.label || c)}</th>`).join("");
    const trs = rows.map((row) => {
        const tds = columns.map((c) => {
            const key = c.key || c;
            let val = row[key];
            if (val === null || val === undefined) {
                return `<td>—</td>`;
            }
            let cls = "";
            if (typeof c.classFn === "function") {
                cls = c.classFn(val, row);
            }
            const formatted = typeof c.fmt === "function" ? c.fmt(val, row) : escapeHtml(String(val));
            return `<td class="${cls}">${formatted}</td>`;
        }).join("");
        return `<tr>${tds}</tr>`;
    }).join("");

    wrap.innerHTML = `
        <table class="data-table">
            <thead><tr>${ths}</tr></thead>
            <tbody>${trs}</tbody>
        </table>
    `;
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

async function fetchJson(url, payload = null) {
    setLoading(true);
    try {
        const opts = payload
            ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }
            : { method: "GET" };
        const resp = await fetch(url, opts);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    } finally {
        setLoading(false);
    }
}

/* ================= TAB LOADERS ================= */

async function loadOverviewTab() {
    const data = await fetchJson("/api/overview", buildPayload());
    renderKPIs("overview-kpis", data.kpis);

    renderPlotly("chart-overview-heatmap", data.charts.heatmap, (evt) => {
        const pt = evt.points && evt.points[0];
        if (!pt || !pt.location) return;
        const countryName = pt.text || pt.hovertext || pt.location;
        const banner = document.getElementById("map-click-banner");
        const statusInfo = Array.isArray(pt.customdata) ? ` — <strong>${escapeHtml(pt.customdata[1])}</strong>` : "";
        banner.innerHTML = `
            <div>Selected Country: <strong>${escapeHtml(countryName)} (${escapeHtml(pt.location)})</strong>${statusInfo}</div>
            <div style="display:flex; gap:8px;">
                <button type="button" class="btn-primary" id="btn-jump-country">🔍 Open Country Analytics</button>
                <button type="button" class="btn-secondary" id="btn-set-focus">📌 Set as Global Filter</button>
            </div>
        `;
        banner.classList.remove("hidden");

        document.getElementById("btn-jump-country").onclick = () => {
            state.primary_country = countryName;
            document.getElementById("sel-country-primary").value = countryName;
            switchTab("country");
        };
        document.getElementById("btn-set-focus").onclick = () => {
            state.focus_country = countryName;
            state.primary_country = countryName;
            document.getElementById("sel-focus-country").value = countryName;
            document.getElementById("sel-country-primary").value = countryName;
            markAllStale();
            loadActiveTab();
        };
    });

    renderPlotly("chart-overview-trend", data.charts.trend);
    renderPlotly("chart-overview-secondary", data.charts.secondary);
    renderPlotly("chart-overview-treemap", data.charts.treemap);
    state.staleTabs.delete("overview");
}

async function loadCountryTab() {
    const data = await fetchJson("/api/country", buildPayload());
    const sc = data.scorecard;

    const dirClass = sc.direction === "DECREASED" ? "loss" : (sc.direction === "INCREASED" ? "gain" : "");
    const dirIcon = sc.direction === "DECREASED" ? "🔴" : (sc.direction === "INCREASED" ? "🟢" : "⚪");

    document.getElementById("country-scorecard-header").innerHTML = `
        <span class="badge-dir ${dirClass}">${dirIcon} ${escapeHtml(sc.direction)}</span>
        <span class="badge-info">${escapeHtml(sc.continent)} • ${escapeHtml(sc.sub_region)}</span>
        <span class="badge-info">Primary Cause: ${escapeHtml(sc.dominant_driver)}</span>
        <span class="badge-info">Top Commodity: ${escapeHtml(sc.dominant_commodity)}</span>
    `;

    renderKPIs("country-kpis", sc.metrics);
    renderPlotly("chart-country-zoom", data.charts.zoom_map);
    renderPlotly("chart-country-deep", data.charts.deep_dive);
    renderPlotly("chart-country-cause", data.charts.cause_timeline);
    renderPlotly("chart-country-secondary", data.charts.secondary);
    renderPlotly("chart-compare-lines", data.charts.compare_lines);
    renderPlotly("chart-compare-radar", data.charts.compare_radar);
    renderPlotly("chart-compare-heatmap", data.charts.compare_heatmap);
    renderCompareChips();
    state.staleTabs.delete("country");
}

async function loadCausesTab() {
    const data = await fetchJson("/api/causes", buildPayload());
    document.getElementById("cause-view-title").textContent = `Cause Analytics — ${data.cause_label}`;

    const allView = document.getElementById("causes-all-view");
    const specView = document.getElementById("causes-specific-view");

    if (data.mode === "all") {
        allView.classList.remove("hidden");
        specView.classList.add("hidden");
        renderPlotly("chart-causes-pie", data.charts.pie);
        renderPlotly("chart-causes-comm", data.charts.commodity);
        renderPlotly("chart-causes-stacked", data.charts.stacked);
        renderPlotly("chart-causes-sunburst", data.charts.sunburst);
        renderPlotly("chart-causes-all-heat", data.charts.heatmap);
    } else {
        allView.classList.add("hidden");
        specView.classList.remove("hidden");
        renderPlotly("chart-cause-spec-map", data.charts.map);
        renderPlotly("chart-cause-spec-top", data.charts.top);
        renderPlotly("chart-cause-spec-traj", data.charts.trajectory);
        renderPlotly("chart-cause-spec-share", data.charts.share);
        renderPlotly("chart-cause-spec-heat", data.charts.heatmap);

        renderDataTable("cause-table-wrap", [
            { key: "Code", label: "ISO3" },
            { key: "Entity", label: "Country" },
            { key: "Continent", label: "Continent" },
            { key: "Cause_Mha", label: "Cause Loss (Mha)", fmt: (v) => `${Number(v).toFixed(3)} Mha`, classFn: () => "cell-loss" },
            { key: "Share_of_Global_Cause", label: "% of Global Cause", fmt: (v) => `${Number(v).toFixed(1)}%` },
            { key: "Share_of_Country_Loss", label: "% of Country Total Loss", fmt: (v) => `${Number(v).toFixed(1)}%` }
        ], data.table);
    }
    state.staleTabs.delete("causes");
}

async function loadHotspotsTab() {
    const data = await fetchJson("/api/hotspots", buildPayload());
    renderPlotly("chart-hotspots-loss", data.charts.top_loss);
    renderPlotly("chart-hotspots-gain", data.charts.top_gain);
    renderPlotly("chart-hotspots-dumbbell", data.charts.dumbbell);
    renderPlotly("chart-hotspots-scatter", data.charts.scatter);
    renderPlotly("chart-hotspots-recovery", data.charts.recovery);

    renderDataTable("hotspots-table-wrap", [
        { key: "ISO3", label: "ISO3" },
        { key: "Entity", label: "Country" },
        { key: "Continent", label: "Continent" },
        { key: "Area_Start_Mha", label: `Area ${state.start_year} (Mha)`, fmt: (v) => `${Number(v).toFixed(2)}` },
        { key: "Area_End_Mha", label: `Area ${state.end_year} (Mha)`, fmt: (v) => `${Number(v).toFixed(2)}` },
        {
            key: "Net_Change_Mha",
            label: "Net Change (Mha)",
            fmt: (v) => `${Number(v) >= 0 ? "+" : ""}${Number(v).toFixed(2)} Mha`,
            classFn: (v) => (v < 0 ? "cell-loss" : "cell-gain")
        },
        { key: "Pct_Change", label: "% Change", fmt: (v) => `${Number(v) >= 0 ? "+" : ""}${Number(v).toFixed(1)}%` },
        { key: "Dominant_Driver", label: "Primary Cause" }
    ], data.table);
    state.staleTabs.delete("hotspots");
}

async function loadRegionalTab() {
    const data = await fetchJson("/api/regional", buildPayload());
    renderPlotly("chart-regional-lines", data.charts.regional_lines);
    renderPlotly("chart-regional-co2", data.charts.co2);
    renderPlotly("chart-regional-rli", data.charts.rli);

    renderDataTable("regional-table-wrap", [
        { key: "Continent", label: "Continent" },
        { key: "Forest_Area_Mha", label: "Forest Area (Mha)", fmt: (v) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }) },
        {
            key: "Annual_Change_Mha",
            label: "Annual Change (Mha/yr)",
            fmt: (v) => `${Number(v) >= 0 ? "+" : ""}${Number(v).toFixed(3)}`,
            classFn: (v) => (v < 0 ? "cell-loss" : "cell-gain")
        },
        {
            key: "Direction",
            label: "Status",
            fmt: (v) => v === "DECREASED" ? "🔴 DECREASED" : (v === "INCREASED" ? "🟢 INCREASED" : "⚪ STABLE"),
            classFn: (v) => (v === "DECREASED" ? "cell-loss" : (v === "INCREASED" ? "cell-gain" : ""))
        },
        { key: "Forest_Share_pct", label: "Forest Share (%)", fmt: (v) => `${Number(v).toFixed(1)}%` },
        { key: "CO2_Emissions_Mt", label: "Land-Use CO₂ (Mt)", fmt: (v) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 1 }) }
    ], data.table);
    state.staleTabs.delete("regional");
}

async function loadDataExplorerTab() {
    const dataset = document.getElementById("sel-dataset").value;
    const q = document.getElementById("inp-data-search").value.trim();
    const contStr = encodeURIComponent(state.continents.join(","));
    const qStr = encodeURIComponent(q);

    const url = `/api/data?dataset=${dataset}&q=${qStr}&start_year=${state.start_year}&end_year=${state.end_year}&continents=${contStr}`;
    const dlUrl = `/api/download/${dataset}?q=${qStr}&start_year=${state.start_year}&end_year=${state.end_year}&continents=${contStr}`;
    document.getElementById("btn-download-csv").href = dlUrl;

    const data = await fetchJson(url);
    document.getElementById("data-count-label").textContent = `Showing ${data.rows.length.toLocaleString()} of ${data.total_rows.toLocaleString()} verified records.`;
    const cols = data.columns.map((c) => ({
        key: c,
        label: c,
        fmt: (v) => (typeof v === "number" ? Number(v).toLocaleString(undefined, { maximumFractionDigits: 3 }) : escapeHtml(String(v)))
    }));
    renderDataTable("explorer-table-wrap", cols, data.rows);
    state.staleTabs.delete("data");
}

async function loadActiveTab() {
    updateStatusRibbon();
    if (state.activeTab === "overview") return loadOverviewTab();
    if (state.activeTab === "country") return loadCountryTab();
    if (state.activeTab === "causes") return loadCausesTab();
    if (state.activeTab === "hotspots") return loadHotspotsTab();
    if (state.activeTab === "regional") return loadRegionalTab();
    if (state.activeTab === "data") return loadDataExplorerTab();
}

function switchTab(tabName) {
    state.activeTab = tabName;
    document.querySelectorAll(".tab-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.tab === tabName);
    });
    document.querySelectorAll(".tab-panel").forEach((p) => {
        p.classList.toggle("active", p.id === `tab-${tabName}`);
    });
    if (state.staleTabs.has(tabName)) {
        loadActiveTab().then(() => setTimeout(resizeAllPlots, 60));
    } else {
        setTimeout(resizeAllPlots, 60);
    }
}

/* ================= SIDEBAR & FILTER INITIALIZATION ================= */

function populateContinentPills() {
    const wrap = document.getElementById("continent-pills");
    wrap.innerHTML = state.allContinents.map((c) => {
        const active = state.continents.includes(c) ? "active" : "";
        return `<button type="button" class="continent-pill ${active}" data-cont="${escapeHtml(c)}">${escapeHtml(c)}</button>`;
    }).join("");

    wrap.querySelectorAll(".continent-pill").forEach((btn) => {
        btn.addEventListener("click", () => {
            const c = btn.dataset.cont;
            if (state.continents.includes(c)) {
                if (state.continents.length > 1) {
                    state.continents = state.continents.filter((x) => x !== c);
                }
            } else {
                state.continents.push(c);
            }
            populateContinentPills();
            populateCountryDropdowns();
            markAllStale();
            loadActiveTab();
        });
    });
}

function populateCountryDropdowns() {
    const filtered = state.allCountries.filter((c) => state.continents.includes(c.Continent));
    const focusSel = document.getElementById("sel-focus-country");
    const primSel = document.getElementById("sel-country-primary");
    const addCompSel = document.getElementById("sel-add-compare");

    focusSel.innerHTML = `<option value="All Countries">All Countries (Aggregate)</option>` +
        filtered.map((c) => `<option value="${escapeHtml(c.Entity)}">${escapeHtml(c.Entity)} (${c.ISO3})</option>`).join("");
    if (!filtered.some((c) => c.Entity === state.focus_country)) {
        state.focus_country = "All Countries";
    }
    focusSel.value = state.focus_country;

    primSel.innerHTML = filtered.map((c) => `<option value="${escapeHtml(c.Entity)}">${escapeHtml(c.Entity)} (${c.ISO3})</option>`).join("");
    if (!filtered.some((c) => c.Entity === state.primary_country) && filtered.length > 0) {
        state.primary_country = filtered[0].Entity;
    }
    primSel.value = state.primary_country;

    addCompSel.innerHTML = state.allCountries.map((c) => `<option value="${escapeHtml(c.Entity)}">${escapeHtml(c.Entity)}</option>`).join("");
}

function renderCompareChips() {
    const wrap = document.getElementById("compare-chips");
    wrap.innerHTML = state.compare_countries.map((c) => `
        <span class="country-chip">
            ${escapeHtml(c)}
            <button type="button" data-remove="${escapeHtml(c)}" title="Remove">&times;</button>
        </span>
    `).join("");

    wrap.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
            if (state.compare_countries.length <= 1) return;
            state.compare_countries = state.compare_countries.filter((x) => x !== btn.dataset.remove);
            markAllStale();
            loadCountryTab();
        });
    });
}

function toggleLeftSidebar() {
    const shell = document.getElementById("app-shell");
    const collapsed = shell.classList.toggle("sidebar-collapsed");
    document.getElementById("toggle-menu-icon").textContent = collapsed ? "▶" : "◀";
    document.getElementById("toggle-menu-text").textContent = collapsed ? "Show Menu" : "Hide Menu (Full Screen)";
    setTimeout(resizeAllPlots, 310);
}

async function initDashboard() {
    const meta = await fetchJson("/api/filters");
    state.allContinents = meta.continents;
    state.continents = [...meta.continents];
    state.allCountries = meta.countries;
    state.causes = meta.causes;

    populateContinentPills();
    populateCountryDropdowns();

    // Years dropdowns
    const startSel = document.getElementById("sel-start-year");
    const endSel = document.getElementById("sel-end-year");
    const snapRange = document.getElementById("rng-snapshot-year");
    for (let y = meta.year_min; y <= meta.year_max; y++) {
        startSel.add(new Option(String(y), String(y)));
        endSel.add(new Option(String(y), String(y)));
    }
    startSel.value = String(state.start_year);
    endSel.value = String(state.end_year);

    // Cause selects (sidebar + inline inside Tab 3)
    const causeSel = document.getElementById("sel-cause");
    const causeInline = document.getElementById("sel-cause-inline");
    meta.causes.forEach((c) => {
        causeSel.add(new Option(c.id, c.id));
        causeInline.add(new Option(c.id, c.id));
    });
    causeSel.value = state.cause;
    causeInline.value = state.cause;

    // Bind events
    document.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    document.getElementById("btn-toggle-menu").addEventListener("click", toggleLeftSidebar);
    document.getElementById("btn-collapse-sidebar-inner").addEventListener("click", toggleLeftSidebar);

    document.getElementById("btn-browser-fullscreen").addEventListener("click", () => {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => {});
        } else {
            document.exitFullscreen().catch(() => {});
        }
        setTimeout(resizeAllPlots, 300);
    });

    document.addEventListener("keydown", (e) => {
        if (e.key.toLowerCase() === "m" && !["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) {
            toggleLeftSidebar();
        }
    });

    document.getElementById("sel-focus-country").addEventListener("change", (e) => {
        state.focus_country = e.target.value;
        if (state.focus_country !== "All Countries") {
            state.primary_country = state.focus_country;
            document.getElementById("sel-country-primary").value = state.focus_country;
        }
        markAllStale();
        loadActiveTab();
    });

    document.getElementById("sel-country-primary").addEventListener("change", (e) => {
        state.primary_country = e.target.value;
        if (state.focus_country !== "All Countries") {
            state.focus_country = state.primary_country;
            document.getElementById("sel-focus-country").value = state.primary_country;
        }
        markAllStale();
        loadCountryTab();
    });

    function syncYearControls() {
        let s = Number(startSel.value);
        let e = Number(endSel.value);
        if (s > e) {
            [s, e] = [e, s];
            startSel.value = String(s);
            endSel.value = String(e);
        }
        state.start_year = s;
        state.end_year = e;
        snapRange.min = String(s);
        snapRange.max = String(e);
        if (state.snapshot_year < s) state.snapshot_year = s;
        if (state.snapshot_year > e) state.snapshot_year = e;
        snapRange.value = String(state.snapshot_year);
        document.getElementById("lbl-year-range").textContent = `${s} – ${e}`;
        document.getElementById("lbl-snapshot-year").textContent = String(state.snapshot_year);
        markAllStale();
        loadActiveTab();
    }
    startSel.addEventListener("change", syncYearControls);
    endSel.addEventListener("change", syncYearControls);

    snapRange.addEventListener("input", (e) => {
        state.snapshot_year = Number(e.target.value);
        document.getElementById("lbl-snapshot-year").textContent = String(state.snapshot_year);
    });
    snapRange.addEventListener("change", () => {
        markAllStale();
        loadActiveTab();
    });

    function onCauseChange(val) {
        state.cause = val;
        causeSel.value = val;
        causeInline.value = val;
        if (val !== "All Causes") {
            document.getElementById("sel-map-mode").value = "cause_loss";
            state.map_mode = "cause_loss";
        } else if (state.map_mode === "cause_loss") {
            document.getElementById("sel-map-mode").value = "period_change";
            state.map_mode = "period_change";
        }
        markAllStale();
        loadActiveTab();
    }
    causeSel.addEventListener("change", (e) => onCauseChange(e.target.value));
    causeInline.addEventListener("change", (e) => onCauseChange(e.target.value));

    document.querySelectorAll(".unit-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".unit-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            state.unit = btn.dataset.unit;
            markAllStale();
            loadActiveTab();
        });
    });

    document.getElementById("sel-map-mode").addEventListener("change", (e) => {
        state.map_mode = e.target.value;
        loadOverviewTab();
    });
    document.getElementById("sel-map-scope").addEventListener("change", (e) => {
        state.map_scope = e.target.value;
        markAllStale();
        loadActiveTab();
    });

    document.querySelectorAll("#treemap-mode-btns .seg-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#treemap-mode-btns .seg-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            state.treemap_mode = btn.dataset.val;
            loadOverviewTab();
        });
    });

    document.querySelectorAll("#country-sec-btns .seg-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll("#country-sec-btns .seg-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            state.country_secondary_view = btn.dataset.val;
            loadCountryTab();
        });
    });

    document.getElementById("sel-compare-metric").addEventListener("change", (e) => {
        state.compare_metric = e.target.value;
        document.getElementById("chk-normalize-compare").disabled = (state.compare_metric !== "Forest_Area_Mha");
        loadCountryTab();
    });
    document.getElementById("chk-normalize-compare").addEventListener("change", (e) => {
        state.normalize_compare = e.target.checked;
        loadCountryTab();
    });
    document.getElementById("btn-add-compare").addEventListener("click", () => {
        const val = document.getElementById("sel-add-compare").value;
        if (val && !state.compare_countries.includes(val) && state.compare_countries.length < 6) {
            state.compare_countries.push(val);
            loadCountryTab();
        }
    });

    document.getElementById("rng-top-n").addEventListener("input", (e) => {
        state.top_n = Number(e.target.value);
        document.getElementById("lbl-top-n").textContent = String(state.top_n);
    });
    document.getElementById("rng-top-n").addEventListener("change", () => loadHotspotsTab());

    document.getElementById("sel-regional-metric").addEventListener("change", (e) => {
        state.regional_metric = e.target.value;
        loadRegionalTab();
    });

    let searchTimer = null;
    document.getElementById("sel-dataset").addEventListener("change", () => loadDataExplorerTab());
    document.getElementById("inp-data-search").addEventListener("input", () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => loadDataExplorerTab(), 250);
    });

    document.getElementById("btn-reset-filters").addEventListener("click", () => {
        state.continents = [...state.allContinents];
        state.focus_country = "All Countries";
        state.start_year = 1990;
        state.end_year = 2025;
        state.snapshot_year = 2020;
        state.cause = "All Causes";
        state.unit = "Million Hectares (Mha)";
        state.map_mode = "period_change";
        state.map_scope = "world";

        populateContinentPills();
        populateCountryDropdowns();
        startSel.value = "1990";
        endSel.value = "2025";
        snapRange.min = "1990";
        snapRange.max = "2025";
        snapRange.value = "2020";
        causeSel.value = "All Causes";
        causeInline.value = "All Causes";
        document.getElementById("sel-map-mode").value = "period_change";
        document.getElementById("sel-map-scope").value = "world";
        document.getElementById("lbl-year-range").textContent = "1990 – 2025";
        document.getElementById("lbl-snapshot-year").textContent = "2020";
        document.querySelectorAll(".unit-btn").forEach((b) => b.classList.toggle("active", b.dataset.unit === state.unit));
        markAllStale();
        loadActiveTab();
    });

    window.addEventListener("resize", () => resizeAllPlots());

    // Initial load
    await loadActiveTab();
}

document.addEventListener("DOMContentLoaded", initDashboard);

