/* Dynamic settlement map. Loads the consolidated data emitted by the pipeline
   (data/settlements.geojson, data/population_by_year.json, data/meta.json) and
   renders one circle marker per settlement: radius scales with population in the
   chosen year, fill encodes the selected metric. Pure Leaflet + vanilla JS, no
   build step — so it runs as a static GitHub Pages site. */

const DATA = "data/";
const state = { meta: null, features: [], popByYear: {}, year: null,
                metric: "latest_pop", types: new Set() };

// Sequential / categorical colour ramps.
const RAMP_BLUE = ["#eff3ff","#c6dbef","#9ecae1","#6baed6","#4292c6","#2171b5","#084594"];
const RAMP_RED  = ["#fee5d9","#fcae91","#fb6a4a","#de2d26","#a50f15"];
const DIVERGE   = ["#b2182b","#ef8a62","#fddbc7","#f7f7f7","#d1e5f0","#67a9cf","#2166ac"]; // neg→pos growth
const SE_RAMP   = ["#762a83","#9970ab","#c2a5cf","#e7d4e8","#d9f0d3","#a6dba0","#5aae61","#1b7837","#00441b","#003d20"]; // cluster 1..10
const TRAJ_COLORS = { successful:"#1a9850", surviving:"#fee08b", declining:"#d73027",
                      evacuated:"#777777" };
const TYPE_COLORS = { Settlement:"#2171b5", Outpost:"#e6550d",
                      "East Jerusalem":"#6a51a3", "Hebron Enclave":"#ce1256",
                      "Settlement (B'Tselem-only)":"#3182bd" };

// Metric registry: how to read a value and how to colour it.
const METRICS = {
  latest_pop:      { label: "Population (latest)", kind: "seq", ramp: RAMP_BLUE,
                     get: p => p.latest_pop, fmt: v => v?.toLocaleString() },
  cagr_pct:        { label: "Growth rate (CAGR %)", kind: "div", ramp: DIVERGE,
                     get: p => p.cagr_pct, fmt: v => v?.toFixed(1) + "%" },
  trajectory:      { label: "Trajectory typology", kind: "cat",
                     get: p => p.trajectory, color: v => TRAJ_COLORS[v] || "#bbb" },
  type:            { label: "Settlement type", kind: "cat",
                     get: p => p.type, color: v => TYPE_COLORS[v] || "#bbb" },
  dist_gl_km:      { label: "Distance from Green Line (km)", kind: "seq", ramp: RAMP_RED,
                     get: p => p.dist_gl_km, fmt: v => v?.toFixed(1) + " km" },
  right_bloc_share:{ label: "Right-bloc vote share", kind: "seq", ramp: RAMP_RED, needs: "has_voting",
                     get: p => p.right_bloc_share, fmt: v => (v*100).toFixed(1) + "%" },
  se_cluster:      { label: "Socio-economic cluster (1–10)", kind: "se", ramp: SE_RAMP, needs: "has_economic",
                     get: p => p.se_cluster, fmt: v => "cluster " + v },
  built_up_dunams: { label: "Built-up area (dunams)", kind: "seq", ramp: RAMP_BLUE, needs: "has_builtup",
                     get: p => p.built_up_dunams, fmt: v => v?.toLocaleString() + " du" },
};

const map = L.map("map", { preferCanvas: true }).setView([31.95, 35.15], 9);
L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  attribution: '&copy; OpenStreetMap &copy; CARTO', subdomains: "abcd", maxZoom: 19
}).addTo(map);
const layer = L.layerGroup().addTo(map);

function quantile(sorted, q) {
  const pos = (sorted.length - 1) * q, base = Math.floor(pos), rest = pos - base;
  return sorted[base + 1] !== undefined ? sorted[base] + rest * (sorted[base+1]-sorted[base]) : sorted[base];
}

function seqColor(v, vals, ramp) {
  if (v == null || isNaN(v)) return "#d7dce2";
  const breaks = ramp.map((_, i) => quantile(vals, i / (ramp.length - 1)));
  for (let i = ramp.length - 1; i >= 0; i--) if (v >= breaks[i]) return ramp[i];
  return ramp[0];
}

function colorFor(m, p, vals) {
  const def = METRICS[m], v = def.get(p);
  if (def.kind === "cat") return v == null ? "#d7dce2" : def.color(v);
  if (def.kind === "se")  return v == null || isNaN(v) ? "#d7dce2" : def.ramp[Math.max(0, Math.min(9, Math.round(v)-1))];
  if (def.kind === "div") {
    if (v == null || isNaN(v)) return "#d7dce2";
    const idx = v <= -3 ? 0 : v < 0 ? 1 : v < 3 ? 2 : v < 6 ? 3 : v < 10 ? 4 : v < 15 ? 5 : 6;
    return def.ramp[idx];
  }
  return seqColor(v, vals, def.ramp);
}

function radiusFor(p) {
  const pop = popOf(p, state.year);
  if (pop == null) return 3;                       // outposts have no population
  return Math.max(3, Math.min(34, 2.2 * Math.sqrt(pop) / 3.0));
}

function popOf(p, year) {
  const series = state.popByYear[String(p.settlement_id)];
  if (!series) return null;
  if (series[year] != null) return series[year];   // exact year
  let best = null, by = null;                        // else carry last <= year
  for (const y in series) { const yi = +y; if (yi <= year && (by == null || yi > by)) { by = yi; best = series[y]; } }
  return best;
}

function popupHtml(p) {
  const rows = [];
  const add = (k, v) => { if (v !== null && v !== undefined && v !== "") rows.push(`<tr><td class="k">${k}</td><td>${v}</td></tr>`); };
  add("Type", p.type);
  add("Regional council", p.regional_council);
  add("Pattern", p.urban_pattern);
  add("Established", p.year_established);
  add("Dist. Green Line", p.dist_gl_km != null ? p.dist_gl_km + " km" : null);
  const pv = popOf(p, state.year);
  add(`Population ${state.year}`, pv != null ? pv.toLocaleString() : null);
  add("Latest population", p.latest_pop != null ? `${p.latest_pop.toLocaleString()} (${p.latest_pop_year})` : null);
  add("Growth (CAGR)", p.cagr_pct != null ? p.cagr_pct.toFixed(1) + "%" : null);
  add("Trajectory", p.trajectory);
  add("Right-bloc vote", p.right_bloc_share != null ? (p.right_bloc_share*100).toFixed(1) + "% (K" + p.latest_knesset + ")" : null);
  add("Leading party", p.top_party);
  add("Socio-econ cluster", p.se_cluster != null ? `${p.se_cluster} (rank ${p.se_rank ?? "—"})` : null);
  add("Built-up area", p.built_up_dunams != null ? p.built_up_dunams.toLocaleString() + " dunams" : null);
  return `<b>${p.name_en || ""}</b> ${p.name_he ? `<span dir="rtl">${p.name_he}</span>` : ""}` +
         `<table>${rows.join("")}</table>`;
}

function render() {
  layer.clearLayers();
  const def = METRICS[state.metric];
  const visible = state.features.filter(f => state.types.has(f.properties.type));
  const vals = visible.map(f => def.get(f.properties)).filter(v => v != null && !isNaN(v)).sort((a,b)=>a-b);
  let shown = 0;
  for (const f of visible) {
    const p = f.properties, c = f.geometry.coordinates;
    L.circleMarker([c[1], c[0]], {
      radius: radiusFor(p), color: "#33414f", weight: .5, opacity: .7,
      fillColor: colorFor(state.metric, p, vals), fillOpacity: .82,
    }).bindPopup(popupHtml(p)).addTo(layer);
    shown++;
  }
  document.getElementById("count").textContent = `${shown} of ${state.features.length} entities shown`;
  drawLegend(vals);
}

function drawLegend(vals) {
  const def = METRICS[state.metric], el = document.getElementById("legend");
  let html = `<label>${def.label}</label>`;
  const row = (col, txt) => `<div class="row"><span class="sw" style="background:${col}"></span>${txt}</div>`;
  if (def.kind === "cat") {
    const seen = [...new Set(state.features.map(f => def.get(f.properties)).filter(Boolean))];
    html += seen.map(v => row(def.color(v), v)).join("");
  } else if (def.kind === "se") {
    [1,3,5,7,10].forEach(k => html += row(def.ramp[k-1], "cluster " + k + (k===1?" (lowest)":k===10?" (highest)":"")));
  } else if (def.kind === "div") {
    [["#b2182b","decline"],["#fddbc7","≈0%"],["#67a9cf","fast growth"]].forEach(([c,t]) => html += row(c,t));
  } else if (vals.length) {
    const ramp = def.ramp;
    ramp.forEach((c,i) => {
      const lo = quantile(vals, i/(ramp.length)), hi = quantile(vals, (i+1)/(ramp.length));
      html += row(c, def.fmt(lo) + (i===ramp.length-1 ? "+" : " – " + def.fmt(hi)));
    });
  }
  html += row("#d7dce2", "no data");
  el.innerHTML = html;
}

function buildControls() {
  // Metric dropdown (skip metrics whose data isn't present this build).
  const sel = document.getElementById("metric");
  for (const [k, def] of Object.entries(METRICS)) {
    if (def.needs && !state.meta[def.needs]) continue;
    const o = document.createElement("option"); o.value = k; o.textContent = def.label; sel.appendChild(o);
  }
  sel.value = state.metric;
  sel.onchange = e => { state.metric = e.target.value; render(); };

  // Year slider.
  const yr = document.getElementById("year");
  yr.min = state.meta.min_year; yr.max = state.meta.max_year; yr.value = state.meta.max_year;
  state.year = +state.meta.max_year;
  document.getElementById("yearval").textContent = state.year;
  yr.oninput = e => { state.year = +e.target.value; document.getElementById("yearval").textContent = state.year; render(); };

  // Type chips.
  const types = [...new Set(state.features.map(f => f.properties.type))];
  const box = document.getElementById("types");
  types.forEach(t => {
    state.types.add(t);
    const c = document.createElement("span"); c.className = "chip on"; c.textContent = t;
    c.onclick = () => { if (state.types.has(t)) { state.types.delete(t); c.classList.remove("on"); }
                        else { state.types.add(t); c.classList.add("on"); } render(); };
    box.appendChild(c);
  });

  document.getElementById("foot").innerHTML =
    `Built ${state.meta.built}. ${state.meta.settlement_count} mapped entities, ` +
    `years ${state.meta.min_year}–${state.meta.max_year}. ` +
    `Sources: Peace Now, B'Tselem, Israel CBS, Central Elections Committee, UN OCHA — see ` +
    `<a href="https://github.com/pedahzur/settlements/blob/main/SOURCES.md">SOURCES.md</a>. ` +
    `Refreshed weekly.`;
}

Promise.all([
  fetch(DATA + "meta.json").then(r => r.json()),
  fetch(DATA + "settlements.geojson").then(r => r.json()),
  fetch(DATA + "population_by_year.json").then(r => r.json()),
]).then(([meta, geo, pby]) => {
  state.meta = meta; state.features = geo.features; state.popByYear = pby;
  buildControls();
  render();
}).catch(err => {
  document.getElementById("foot").innerHTML =
    `<b style="color:#b2182b">Could not load data.</b> ${err}`;
});
