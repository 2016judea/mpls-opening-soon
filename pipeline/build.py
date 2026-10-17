"""Minneapolis businesses about to open (and so about to hire a first team).
Signals, all Minneapolis public records:
  1. commercial build-out permits that read as a NEW occupant (certificate of occupancy required,
     change of occupancy, a named new use, a tenant build-out), by stage;
  2. new on-sale liquor licenses (license numbers run in sequence; the newest are new places);
  3. a restaurant's first-ever health inspection.
Joined on address. Owner/manager from the MN Secretary of State for the business name the city
uses (free; cached in private/cache/sos.json). Writes private/rows.json.

    python3 pipeline/pull_permits.py && python3 pipeline/build.py
Reuses the logic of on-the-house/pipeline/permits/hospitality_pull.py (Blue Vector, 2026-10-05).
"""
import json, re, html, time, collections, datetime as dt, urllib.request, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
PRIV = ROOT / "private"; CACHE = PRIV / "cache"
B = "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services"
TODAY = dt.date.today(); RECENT = (TODAY - dt.timedelta(days=60)).isoformat()
NEWLIC = 420000  # liquor license numbers above this are the newest (hospitality_pull.py, 10/05)
def q(svc, where, fields="*"):
    out, off = [], 0
    while True:
        p = dict(where=where, outFields=fields, f="json", resultOffset=off, resultRecordCount=2000, returnGeometry="false")
        d = json.load(urllib.request.urlopen(urllib.request.Request(f"{B}/{svc}/FeatureServer/0/query", data=urllib.parse.urlencode(p).encode()), timeout=120))
        fs = [f["attributes"] for f in d.get("features", [])]; out += fs
        if not d.get("exceededTransferLimit") or not fs: return out
        off += len(fs)
D = lambda ms: dt.datetime.utcfromtimestamp(int(ms) / 1000).date().isoformat() if ms not in (None, "") else ""
DIRS = {"N", "S", "E", "W", "NE", "SE", "NW", "SW"}
SUF = {"AVENUE": "AVE", "STREET": "ST", "ROAD": "RD", "BOULEVARD": "BLVD", "PARKWAY": "PKWY", "DRIVE": "DR", "PLACE": "PL", "LANE": "LN"}
def key(a):
    a = re.sub(r"\s*#.*$", "", (a or "").upper()).replace(".", ""); a = re.sub(r",.*$", "", a)
    return " ".join([x for x in a.split() if x not in DIRS][:2])
def title(a):
    a = re.sub(r"\s*#.*$", "", a or "")
    return " ".join(w if w.upper() in DIRS else w.capitalize() for w in a.split())
TC = lambda x: re.sub(r"'S\b", "'s", x.title()).replace("Llc", "LLC") if x.isupper() else x
E = {}
def ev(addr, food=False):
    k = key(addr)
    # a liquor license or a restaurant inspection at an address whose permit is some OTHER tenant
    # (a tower: Bellecour's license and a mortgage firm's floors share "90 7TH") is its own row
    if food and k in E and E[k]["permit"] and (E[k]["permit"]["kind"] != "Food and drink" or re.search(r" - |'[A-Z]", E[k]["permit"]["what"])):
        k = k + " |food"
    return E.setdefault(k, dict(key=k, addr=title(addr), hood="", lat=None, lon=None, names=[], permit=None, liq=[], food=[]))

# 1 permits
CUT = re.compile(r"certificate of occupancy|CERTIFICATE OF OCCUPANCY|const type|CONST TYPE|Building Code|\(JJL\)|-ACW|\(DMH[^)]*\)|\*\*\*|special inspections|MECHANICAL PERMIT|A MECHANICAL|mechanical plans|PRIOR TO|SUBMIT|LETTER FROM|A LETTER|Shell permit|SEPARATE|Revision after issue", re.I)
what = lambda c: re.sub(r"\s+", " ", CUT.split(c or "")[0]).strip(" .-*")[:120]
NEWBIZ = re.compile(r"certificate of occupancy (is )?required:?\s*-?\s*(yes|an authorized)|CERTIFICATE OF OCCUPANCY IS REQUIRED|change of occupancy|\bnew (restaurant|eating|cafe|coffee|bar|retail|store|shop|grocery|salon|spa|clinic|office|gym|fitness|bakery|brewery|taproom|daycare|child|school|studio|business|dispensary|cannabis|hotel|tenant)|tenant (build[- ]?out|fit[- ]?out|improvement)|build[- ]?out|fit[- ]?out|t/i\b", re.I)
SKIP = re.compile(r"\bSFD\b|\bR-?[1-4]\b|group home|assisted living|dementia|apartment|housing|dwelling|residential|condo|life safety|chapel|church|police|\bIDF\b|single unit|unit build|demo(lition)? (of )?interior|interior demo|spec suite|future tenant|shell only|restroom|bathroom|stair|storefront window|propane|roof|elevator|sprinkler|fire alarm|parking|balcon|facade|façade|window replacement|structural repair|foundation|grab bar|ada ", re.I)
KINDS = [("Shop", r"dispensar|cannab|cannib"),
         ("Food and drink", r"restaurant|eating|cafe|café|coffee|bakery|\bbar\b|brew|taproom|kitchen|pizza|bagel|smoothie|tea\b|deli|food hall|occupancy:\s*A-2"),
         ("Child care and school", r"daycare|day care|child ?care|preschool|school|academy|learning|occupancy:\s*(E|I-4)\b"),
         ("Health care", r"clinic|medical|dental|dentist|treatment|therapy|health|chiropract|optometr|pharmacy|veterinar|hospital"),
         ("Salon, spa and fitness", r"salon|spa\b|barber|nail|fitness|gym|yoga|pilates|golf|climb|martial|dance|studio|massage"),
         ("Shop", r"retail|store|shop|grocery|market|dispensar|cannab|cannib|boutique|occupancy:\s*M\b"),
         ("Hotel", r"hotel|motel|lodging"),
         ("Office", r"office|suite|floor|occupancy:\s*B\b")]
def kind(text):
    for k, rx in KINDS:
        if re.search(rx, text or "", re.I): return k
    return "Other business"
P = json.load(open(PRIV / "permits_raw.json"))["rows"]
STG = {"Final Inspection": "Final inspection", "Inspection": "Under construction"}
for p in P:
    c = p["comments"] or ""
    if p["workType"] not in ("Remodel", "Addition", "New") or not p["Display"] or not NEWBIZ.search(c) or SKIP.search(what(c)):
        continue
    done = D(p["completeDate"])
    if p["milestone"] in STG: st = STG[p["milestone"]]
    elif p["milestone"] == "Closed" and done and done >= RECENT: st = "Finished"
    else: continue
    e = ev(p["Display"]); e["hood"] = p["Neighborhoods_Desc"] or e["hood"]
    if p["Latitude"]: e["lat"], e["lon"] = p["Latitude"], p["Longitude"]
    rank = {"Final inspection": 0, "Under construction": 1, "Finished": 2}[st]
    if not e["permit"] or rank < e["permit"]["rank"]:
        by = p["applicantName"] or ""
        e["permit"] = dict(rank=rank, stage=st, what=what(c), kind=(kind(what(c)) if kind(what(c)) != "Other business" else kind(c)), issued=D(p["issueDate"]), done=done, permit=p["permitNumber"], fees=p["totalFees"] or 0,
                           by=by if re.search(r"\b(INC|LLC|CONSTRUCTION|BUILDERS|COMPANY|CO|CORP|GROUP|CONTRACTING|DESIGN|BUILD)\b", by.upper()) else "")
# 2 new liquor licenses
for l in {l["licenseNumber"]: l for l in q("On_Sale_Liquor", "1=1")}.values():
    if int(l["licenseNumber"][3:]) <= NEWLIC or not l["address"]: continue
    e = ev(l["address"], food=True); e["hood"] = e["hood"] or (l["neighborhood"] or "").title()
    if e["lat"] is None: e["lat"], e["lon"] = l["lat"], l["long"]
    e["liq"].append(dict(name=l["licenseName"], num=l["licenseNumber"], status=l["licenseStatus"], date=D(l["issueDate"])))
    e["names"].append(("liquor", l["licenseName"]))
# 3 first-ever restaurant health inspection since Jul 1
first = {}
for f in q("Food_Inspections", "YearOfInspection>=2024", "HealthFacilityIDNumber,BusinessName,FacilityCategory,DateOfInspection,FullAddress,Neighborhood,Latitude,Longitude"):
    d = D(f["DateOfInspection"]); k = f["HealthFacilityIDNumber"]
    if k not in first or d < first[k][0]: first[k] = (d, f)
for d, f in first.values():
    if d < "2026-07-01" or f["FacilityCategory"] != "RESTAURANT" or not f["FullAddress"]: continue
    if re.search(r"child ?care|daycare|school|senior|academy|church|hospital|head start", f["BusinessName"], re.I): continue
    e = ev(f["FullAddress"], food=True); e["hood"] = e["hood"] or (f["Neighborhood"] or "").title()
    if e["lat"] is None and f["Latitude"]: e["lat"], e["lon"] = f["Latitude"], f["Longitude"]
    e["food"].append(dict(name=f["BusinessName"].strip(), date=d)); e["names"].append(("food", f["BusinessName"].strip()))
# names from the permit text when it says "- Name" or "'NAME'" are NOT parsed (mpls-permits: wrong 3 of 4 times)

# 4 MN Secretary of State, cached (hospitality_pull.py sos())
SC = json.load(open(CACHE / "sos.json")) if (CACHE / "sos.json").exists() else {}
norm = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"\b(llc|inc|co|corp|the|restaurant|cafe|café|and|&)\b", "", (s or "").lower()))
def text(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)
    return [l.strip() for l in html.unescape(re.sub(r"<[^>]+>", "\n", h)).split("\n") if l.strip()]
def get(u):
    time.sleep(0.6); return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode("utf-8", "replace")
def sos(name):
    k = norm(name)
    if not k or len(k) < 4: return None
    if name in SC: return SC[name]
    res = None
    try:
        s = re.sub(r"\b(LLC|L\.L\.C\.|INC\.?|CORP\.?)\b", "", name, flags=re.I).strip(" ,.")
        h = get("https://mblsportal.sos.mn.gov/Business/BusinessSearch?" + urllib.parse.urlencode(dict(BusinessName=s, IncludePriorNames="False", Status="Active", Type="BeginsWith")))
        hits = []
        for tr in h.split("<tr")[1:]:
            m = re.search(r'href="(/Business/SearchDetails\?filingGuid=[^"]+)"', tr); tl = text("<x" + tr)
            if m and tl and norm(tl[0]) == k: hits.append((("Assumed" in tr), m))
        hits.sort(key=lambda x: x[0])
        for _, m in hits[:3]:
            t = text(get("https://mblsportal.sos.mn.gov" + html.unescape(m.group(1))))
            after = lambda label: t[t.index(label) + 1] if label in t else ""
            bn = after("Minnesota Business Name") or after("Business Name")
            if norm(bn) != k: continue
            people = [(lab, t[i + 1]) for lab in ("Manager", "Chief Executive Officer", "Name Holder") for i, x in enumerate(t) if x == lab and i + 1 < len(t)]
            res = dict(entity=bn, filed=after("Filing Date"), people=people[:3], url="https://mblsportal.sos.mn.gov" + html.unescape(m.group(1))); break
    except Exception:
        res = None
    SC[name] = res; json.dump(SC, open(CACHE / "sos.json", "w"), indent=1); return res

rows = []
for e in E.values():
    p = e["permit"]
    if not (p or e["liq"] or e["food"]) or e["lat"] is None: continue
    pend = any(x["status"] == "Pending" for x in e["liq"])
    dates = [x["date"] for x in e["liq"] + e["food"]] + ([p["done"] or p["issued"]] if p else [])
    if p and p["stage"] == "Final inspection" or pend: stage, so = "Opening soon", 0
    elif p and p["stage"] == "Under construction": stage, so = "Building out", 1
    else: stage, so = "Just opened", 2
    names = [n for _, n in sorted(e["names"], key=lambda x: {"liquor": 0, "food": 1}[x[0]])]
    name = TC(names[0]) if names else ""
    s = None; s2 = None
    for n in dict.fromkeys(names):
        s = sos(n)
        if s:
            hold = [v for l, v in s["people"] if l == "Name Holder"]
            if hold and not [1 for l, _ in s["people"] if l in ("Manager", "Chief Executive Officer")]: s2 = sos(hold[0])
            break
    people = [f"{TC(n)} ({l.replace('Chief Executive Officer', 'CEO').lower()})" for src in (s, s2) if src for l, n in src["people"] if l in ("Manager", "Chief Executive Officer") and " " in n.strip()]
    sig = []
    if p: sig.append(f"{p['stage']} on a build-out permit" + (f", finished {p['done']}" if p["stage"] == "Finished" else ""))
    for x in {x["num"]: x for x in e["liq"]}.values(): sig.append(f"New liquor license ({x['status'].lower()}) {x['date']}")
    for x in e["food"]: sig.append(f"First health inspection {x['date']}")
    k = (p or {}).get("kind") or ("Food and drink" if (e["liq"] or e["food"]) else "Other business")
    if (e["liq"] or e["food"]) and k == "Office": k = "Food and drink"
    rows.append(dict(stage=stage, so=so, kind=k, name=name, addr=e["addr"], hood=(e["hood"] or "").replace("'S ", "'s "), lat=round(e["lat"], 5), lon=round(e["lon"], 5),
                     signals=" · ".join(dict.fromkeys(sig)), latest=max([d for d in dates if d] or [""]), pwhat=(p or {}).get("what", ""), permit=(p or {}).get("permit", ""),
                     fees=(p or {}).get("fees", 0), by=(p or {}).get("by", ""), owner="; ".join(dict.fromkeys(people)),
                     entity=((s2 or s or {}).get("entity", "")), filed=(s or {}).get("filed", ""), sosurl=(s or {}).get("url", ""),
                     also="; ".join(dict.fromkeys(TC(n) for n in names if TC(n) != name))))
json.dump({"pulled": TODAY.isoformat(), "rows": rows}, open(PRIV / "rows.json", "w"))
print("rows", len(rows), collections.Counter(r["stage"] for r in rows), collections.Counter(r["kind"] for r in rows))
print("named", sum(bool(r["name"]) for r in rows), "owner", sum(bool(r["owner"]) for r in rows), "entity", sum(bool(r["entity"]) for r in rows))
