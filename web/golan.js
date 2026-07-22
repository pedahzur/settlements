/* Dynamic Golan Heights map. Loads data/golan.json (emitted by
   pipeline.build_golan_map) and renders one circle marker per locality:
   radius scales with population in the chosen year, fill encodes the selected
   metric. Same stack as the West Bank map: pure Leaflet + vanilla JS, no build
   step, so it runs as a static GitHub Pages site. */

const state = { data: null, year: null, metric: "form",
                groups: new Set(["jewish"]), timer: null };

// CARTO Bold categorical colours for settlement form; sequential YlOrRd for
// population; diverging red->blue for growth.
const FORM_COLORS = {
  "Kibbutz": "#3969AC", "Moshav": "#11A579", "Moshav Shitufi": "#7F3C8D",
  "Community": "#F2B701", "Urban": "#E73F74", "Village": "#008695",
};
const RAMP_POP = ["#ffffb2","#fed976","#feb24c","#fd8d3c","#f03b20","#bd0026"];
const DIVERGE  = ["#b2182b","#ef8a62","#fddbc7","#d1e5f0","#67a9cf","#2166ac"];
const NO_DATA  = "#c7ccd1";
const GROUP_LABELS = { jewish: "Jewish localities", druze: "Druze/Alawite (comparison)" };

const firstYear = loc => { const ys = Object.keys(loc.pop); return ys.length ? Math.min(...ys.map(Number)) : null; };
const lastYear  = loc => { const ys = Object.keys(loc.pop); return ys.length ? Math.max(...ys.map(Number)) : null; };

function cagr(loc) {
  const y0 = firstYear(loc), y1 = lastYear(loc);
  if (y0 == null || y1 == null || y1 <= y0) return null;
  const p0 = loc.pop[y0], p1 = loc.pop[y1];
  if (!p0 || !p1) return null;
  return (Math.pow(p1 / p0, 1 / (y1 - y0)) - 1) * 100;
}

// Population in the selected year; carries the last earlier observation
// forward so a locality does not blink out on a missing year.
function popOf(loc, year) {
  if (loc.pop[year] != null) return loc.pop[year];
  let best = null, by = null;
  for (const y in loc.pop) { const yi = +y; if (yi <= year && (by == null || yi > by)) { by = yi; best = loc.pop[y]; } }
  return best;
}

const METRICS = {
  form:     { label: "Settlement form", kind: "cat",
              get: l => l.form, color: v => FORM_COLORS[v] || "#bbb" },
  pop:      { label: "Population (selected year)", kind: "seq", ramp: RAMP_POP,
              get: l => popOf(l, state.year), fmt: v => v?.toLocaleString() },
  cagr_pct: { label: "Growth 2003→2024 (CAGR %)", kind: "div", ramp: DIVERGE,
              get: l => cagr(l), fmt: v => v?.toFixed(1) + "%" },
};

const map = L.map("map", { preferCanvas: true }).setView([33.0, 35.78], 10);
L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
  attribution: '&copy; OpenStreetMap &copy; CARTO', subdomains: "abcd", maxZoom: 19
}).addTo(map);
const layer = L.layerGroup().addTo(map);

function quantile(sorted, q) {
  const pos = (sorted.length - 1) * q, base = Math.floor(pos), rest = pos - base;
  return sorted[base + 1] !== undefined ? sorted[base] + rest * (sorted[base+1]-sorted[base]) : sorted[base];
}

function colorFor(loc, vals) {
  const def = METRICS[state.metric], v = def.get(loc);
  if (v == null || (def.kind !== "cat" && isNaN(v))) return NO_DATA;
  if (def.kind === "cat") return def.color(v);
  if (def.kind === "div") {
    const idx = v <= -1 ? 0 : v < 0 ? 1 : v < 1 ? 2 : v < 2.5 ? 3 : v < 4 ? 4 : 5;
    return def.ramp[idx];
  }
  const breaks = def.ramp.map((_, i) => quantile(vals, i / (def.ramp.length - 1)));
  for (let i = def.ramp.length - 1; i >= 0; i--) if (v >= breaks[i]) return def.ramp[i];
  return def.ramp[0];
}

function radiusFor(loc) {
  const pop = popOf(loc, state.year);
  if (pop == null) return 4;                       // no published series (Nimrod)
  return Math.max(4, Math.min(28, 0.6 * Math.sqrt(pop)));
}

function popupHtml(loc) {
  const rows = [];
  const add = (k, v) => { if (v !== null && v !== undefined && v !== "") rows.push(`<tr><td class="k">${k}</td><td>${v}</td></tr>`); };
  add("Group", GROUP_LABELS[loc.group]);
  add("Form", loc.form);
  add("Founded", loc.founded);
  add("Elevation", loc.elevation != null ? loc.elevation + " m" : null);
  const pv = popOf(loc, state.year);
  add(`Population ${state.year}`, pv != null ? pv.toLocaleString() : "no published series");
  const y0 = firstYear(loc), y1 = lastYear(loc);
  if (y0 != null && y1 != null && y1 > y0) {
    add(`Population ${y0} → ${y1}`, `${loc.pop[y0].toLocaleString()} → ${loc.pop[y1].toLocaleString()}`);
    const g = cagr(loc);
    add("Growth (CAGR)", g != null ? g.toFixed(1) + "%" : null);
  }
  return `<b>${loc.name_en || ""}</b> ${loc.name_he ? `<span dir="rtl">${loc.name_he}</span>` : ""}` +
         `<table>${rows.join("")}</table>`;
}

function render() {
  layer.clearLayers();
  const def = METRICS[state.metric];
  const visible = state.data.localities.filter(l => state.groups.has(l.group));
  const vals = visible.map(l => def.get(l)).filter(v => v != null && !isNaN(v)).sort((a,b)=>a-b);
  for (const loc of visible) {
    L.circleMarker([loc.lat, loc.lon], {
      radius: radiusFor(loc), color: "#33414f", weight: .5, opacity: .7,
      fillColor: colorFor(loc, vals), fillOpacity: .82,
    }).bindPopup(popupHtml(loc)).addTo(layer);
  }

  const totals = [];
  for (const g of ["jewish", "druze"]) {
    if (!state.groups.has(g)) continue;
    const sum = state.data.localities.filter(l => l.group === g)
      .reduce((acc, l) => acc + (popOf(l, state.year) || 0), 0);
    totals.push(`${GROUP_LABELS[g]}: <b>${sum.toLocaleString()}</b>`);
  }
  document.getElementById("total").innerHTML =
    totals.length ? `Population in ${state.year} — ${totals.join(" · ")}` : "";
  document.getElementById("count").textContent =
    `${visible.length} of ${state.data.localities.length} localities shown`;
  drawLegend(vals);
}

function drawLegend(vals) {
  const def = METRICS[state.metric], el = document.getElementById("legend");
  let html = `<label>${def.label}</label>`;
  const row = (col, txt) => `<div class="row"><span class="sw" style="background:${col}"></span>${txt}</div>`;
  if (def.kind === "cat") {
    const seen = [...new Set(state.data.localities.filter(l => state.groups.has(l.group))
      .map(l => def.get(l)).filter(Boolean))];
    html += seen.map(v => row(def.color(v), v)).join("");
  } else if (def.kind === "div") {
    [["#b2182b","decline"],["#fddbc7","≈0%"],["#67a9cf","2.5–4%"],["#2166ac","4%+"]]
      .forEach(([c,t]) => html += row(c,t));
  } else if (vals.length) {
    def.ramp.forEach((c,i) => {
      const lo = quantile(vals, i/def.ramp.length), hi = quantile(vals, (i+1)/def.ramp.length);
      html += row(c, def.fmt(lo) + (i===def.ramp.length-1 ? "+" : " – " + def.fmt(hi)));
    });
  }
  html += row(NO_DATA, "no data");
  el.innerHTML = html;
}

function setYear(y) {
  state.year = y;
  document.getElementById("year").value = y;
  document.getElementById("yearval").textContent = y;
  render();
}

function stopAnimation() {
  if (state.timer) { clearInterval(state.timer); state.timer = null; }
  const btn = document.getElementById("play");
  btn.textContent = "▶"; btn.classList.remove("on");
}

function buildControls() {
  const d = state.data;

  const sel = document.getElementById("metric");
  for (const [k, def] of Object.entries(METRICS)) {
    const o = document.createElement("option"); o.value = k; o.textContent = def.label; sel.appendChild(o);
  }
  sel.value = state.metric;
  sel.onchange = e => { state.metric = e.target.value; render(); };

  const yr = document.getElementById("year");
  yr.min = d.min_year; yr.max = d.max_year;
  yr.oninput = e => { stopAnimation(); setYear(+e.target.value); };

  // Play button: sweep the years, then stop on the last one.
  const btn = document.getElementById("play");
  btn.onclick = () => {
    if (state.timer) { stopAnimation(); return; }
    btn.textContent = "❚❚"; btn.classList.add("on");
    if (state.year >= d.max_year) setYear(d.min_year);
    state.timer = setInterval(() => {
      if (state.year >= d.max_year) { stopAnimation(); return; }
      setYear(state.year + 1);
    }, 500);
  };

  const box = document.getElementById("groups");
  for (const g of ["jewish", "druze"]) {
    const c = document.createElement("span");
    c.className = "chip" + (state.groups.has(g) ? " on" : "");
    c.textContent = GROUP_LABELS[g];
    c.onclick = () => { if (state.groups.has(g)) { state.groups.delete(g); c.classList.remove("on"); }
                        else { state.groups.add(g); c.classList.add("on"); } render(); };
    box.appendChild(c);
  }

  document.getElementById("foot").innerHTML =
    `Built ${d.built}. ${d.n_jewish} Jewish localities (Nimrod has no published ` +
    `CBS series) and ${d.n_druze} Druze/Alawite comparison localities, ` +
    `years ${d.min_year}–${d.max_year}. Source: Israel CBS locality file — see ` +
    `<a href="https://github.com/pedahzur/settlements/blob/main/SOURCES.md">SOURCES.md</a>.`;
}

fetch("data/golan.json").then(r => r.json()).then(d => {
  state.data = d;
  buildControls();
  setYear(d.max_year);
}).catch(err => {
  document.getElementById("foot").innerHTML =
    `<b style="color:#b2182b">Could not load data.</b> ${err}`;
});
