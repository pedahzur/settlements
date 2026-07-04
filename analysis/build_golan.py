import csv, json, os

base = "data"
ts_path = os.path.join(base, "cbs_golan_2003_2024.csv")
reg_path = os.path.join(base, "cbs_golan_registry_2024.csv")

# --- registry ---
reg = {}
with open(reg_path, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        try:
            semel = int(float(row["semel"]))
        except:
            continue
        name_en = (row["שם יישוב באנגלית"] or "").strip()
        founded = row["שנת ייסוד"].strip()
        form = row["צורת יישוב שוטפת"].strip()
        rel = row["דת יישוב"].strip()
        pop24 = row["סך הכל אוכלוסייה 2024"].strip()
        jewish = row["יהודים ואחרים"].strip()
        arab = row["ערבים"].strip()
        reg[semel] = dict(name=name_en, founded=founded, form=form, rel=rel,
                          pop24=pop24, jewish=jewish, arab=arab)

# form-code -> label (inferred + confirmed against known kibbutz/moshav foundings)
FORM = {"180":"Town","310":"Moshav","320":"Cooperative moshav",
        "330":"Kibbutz","370":"Community","270":"Druze town",
        "280":"Druze town","290":"Druze town","510":"Outpost"}

# Druze/Alawite towns (religion==2)
druze_semels = {s for s,v in reg.items() if v["rel"]=="2.0"}

# --- time series ---
series = {}  # semel -> {year:pop}
with open(ts_path, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        s = int(float(row["semel"]))
        y = int(row["year"])
        p = float(row["pop"])
        series.setdefault(s, {})[y] = p

years = list(range(2003, 2025))

def agg(semels):
    out = []
    for y in years:
        tot = 0.0
        for s in semels:
            if s in series and y in series[s]:
                tot += series[s][y]
        out.append(round(tot))
    return out

jewish_semels = [s for s in series if s not in druze_semels]
druze_present = [s for s in series if s in druze_semels]

jewish_series = agg(jewish_semels)
druze_series = agg(druze_present)

# per-locality summary (Jewish only, for trajectory table)
locs = []
for s in jewish_semels:
    v = reg.get(s, {})
    yrs = sorted(series[s].keys())
    first_y, last_y = yrs[0], yrs[-1]
    p_first, p_last = series[s][first_y], series[s][last_y]
    peak = max(series[s].values())
    n = last_y - first_y
    cagr = ((p_last/p_first)**(1/n)-1)*100 if p_first>0 and n>0 else 0
    decline_from_peak = (p_last/peak - 1)*100 if peak>0 else 0
    locs.append(dict(
        semel=s,
        name=v.get("name") or str(s),
        founded=v.get("founded","") or "",
        form=FORM.get(v.get("form","").replace(".0",""), v.get("form","")),
        pop24=round(p_last),
        pop03=round(series[s].get(2003, p_first)),
        first_year=first_y,
        cagr=round(cagr,2),
        peak=round(peak),
        decline_from_peak=round(decline_from_peak,1),
        multiplier=round(p_last/p_first,2) if p_first>0 else None,
    ))
locs.sort(key=lambda x: -x["pop24"])

druze_towns = []
for s in druze_present:
    v = reg.get(s,{})
    yrs = sorted(series[s].keys())
    druze_towns.append(dict(name=v.get("name") or str(s),
                            pop24=round(series[s][yrs[-1]]),
                            pop03=round(series[s].get(2003, series[s][yrs[0]]))))
druze_towns.sort(key=lambda x:-x["pop24"])

out = dict(
    years=years,
    jewish=jewish_series,
    druze=druze_series,
    jewish_2003=jewish_series[0], jewish_2024=jewish_series[-1],
    druze_2003=druze_series[0], druze_2024=druze_series[-1],
    n_jewish=len(jewish_semels), n_druze=len(druze_present),
    locs=locs,
    druze_towns=druze_towns,
)
print("Jewish 2003->2024:", jewish_series[0], "->", jewish_series[-1],
      "x%.2f"%(jewish_series[-1]/jewish_series[0]))
print("Druze  2003->2024:", druze_series[0], "->", druze_series[-1],
      "x%.2f"%(druze_series[-1]/druze_series[0]))
print("N jewish localities:", len(jewish_semels), "N druze:", len(druze_present))
print("Druze towns:", druze_towns)
print("Top 5 jewish:", [(l['name'],l['pop24'],l['cagr']) for l in locs[:5]])
print("Katzrin:", [l for l in locs if l['name']=='Qazrin'])
with open(os.path.join(os.path.dirname("analysis/x"),"golan_data.json"),"w",encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print("wrote golan_data.json")
