#!/usr/bin/env python3
"""Write site/index.html (free slice) and private/bundle/full.json.gz (the paid list) from
private/rows.json (pipeline/build.py). Every number on the page is computed here."""
import json, datetime as dt
from sitekit import render
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
D = json.load(open(ROOT / "private" / "rows.json"))
rows = D["rows"]
KINDS = ["Food and drink", "Shop", "Salon, spa and fitness", "Health care", "Child care and school", "Office", "Hotel", "Other business"]
ORDER = [k for k in KINDS if any(r["kind"] == k for r in rows)]
STAGES = ["Opening soon", "Building out", "Just opened"]
PAID = ["name", "named_by", "phone", "website", "gstatus", "owner", "entity", "filed", "sosurl", "by", "also"]
cnt = lambda s: sum(r["stage"] == s for r in rows)
own = sum(bool(r["owner"]) for r in rows); named = sum(bool(r["name"]) for r in rows)
phone = sum(bool(r.get("phone")) for r in rows); web = sum(bool(r.get("website")) for r in rows)
reach = sum(bool(r.get("phone") or r.get("website")) for r in rows); glisted = sum(r.get("gstatus") not in ("", "none", None) for r in rows)
pulled = dt.date.fromisoformat(D["pulled"]).strftime("%b %-d, %Y")
srt = sorted(rows, key=lambda r: r["latest"], reverse=True)
pick = lambda st, m: [r for r in srt if r["stage"] == st and r["pwhat"]][:m]
sample = pick("Opening soon", 4) + pick("Building out", 4) + pick("Just opened", 2)
RIVER = [[45.052,-93.2885],[45.03,-93.2805],[45.012,-93.2745],[44.998,-93.2685],[44.988,-93.2625],[44.9815,-93.2575],[44.977,-93.2475],[44.972,-93.2385],[44.967,-93.2295],[44.962,-93.2225],[44.953,-93.2065],[44.946,-93.2005],[44.935,-93.2005],[44.917,-93.2035],[44.905,-93.1995],[44.889,-93.1935]]
COLS = [("stage","Stage"),("name","Business"),("named_by","Name from (blank = the city)"),("phone","Phone (Google Maps)"),("website","Website (Google Maps)"),("gstatus","Google Maps status"),("kind","Kind"),("addr","Address"),("hood","Neighborhood"),("signals","What changed"),("latest","Latest signal"),("pwhat","Permit description"),("by","Builder on the permit"),("owner","Owner or manager (MN Secretary of State)"),("entity","Business entity"),("filed","Entity filed"),("sosurl","State filing link"),("also","Other names at this address"),("permit","Permit #")]
cfg = """{chipKey:"kind",chipOrder:%s,river:%s,csv:"minneapolis-opening-soon.csv",cols:%s,
 stats:[["%d","at final inspection or a pending liquor license: opening soon"],["%d","building out now"],["%d","with a phone number or website to reach them"]],
 legend:[["var(--hot)","Opening soon"],["var(--accent)","Building out"],["var(--done)","Just opened"]],
 dotColor:%s,
 color:r=>r.so===0?"var(--hot)":r.so===1?"var(--accent)":"var(--done)",
 title:r=>FULL&&r.name?r.name:r.addr, what:r=>r.pwhat?("Permit: "+r.pwhat):r.signals,
 tag:r=>`<span class="tag ${r.so===0?"hot":""}">${r.stage}</span>`,
 meta:r=>[FULL&&r.name?r.addr:"",r.kind,r.hood,r.latest?("Latest "+fmt(r.latest)):""],
 paid:r=>[r.phone?`<a href="tel:${esc(r.phone.replace(/[^0-9+]/g,""))}">${esc(r.phone)}</a>`:"",r.website?`<a href="${esc(r.website)}" target="_blank" rel="noopener">Website</a>`:"",r.gstatus&&r.gstatus!=="none"?`Google Maps: ${esc(r.gstatus)}`:"",r.owner?`Owner: ${esc(r.owner)}`:"",r.entity?`Entity: ${esc(r.entity)}`+(r.filed?` (filed ${esc(r.filed)})`:""):"",r.sosurl?`<a href="${esc(r.sosurl)}" target="_blank" rel="noopener">State filing</a>`:"",r.by?`Builder: ${esc(r.by)}`:"",r.signals&&r.pwhat?esc(r.signals):""].filter(Boolean).join(" · "),
 sorts:[["newest","Newest signal first",false],["open","Closest to opening",true],["hood","By neighborhood",true]],
 sortFn:{newest:r=>r.sort((a,b)=>b.latest.localeCompare(a.latest)),open:r=>r.sort((a,b)=>(a.so-b.so)||b.latest.localeCompare(a.latest)),hood:r=>r.sort((a,b)=>a.hood.localeCompare(b.hood)||a.so-b.so)},
 lockText:n=>`${n} more businesses, their names, phone numbers, websites and owners, and the closest-to-opening sort`}""" % (
    json.dumps(ORDER), json.dumps(RIVER), json.dumps(COLS), cnt("Opening soon"), cnt("Building out"), reach, json.dumps(["var(--accent)"] * len(ORDER)))
LIGHT = '--bg:#f4f3f7;--panel:#e9e7ef;--ink:#17151f;--ink2:#36333f;--muted:#666270;--rule:#d5d2de;--accent:#3d3a8f;--onaccent:#f4f3f7;--hot:#d0542b;--done:#928ea0;--ghost:#c7c4d1;--water:#93acc4;--tagbg:#e3e1ea;--tagfg:#4a4757;--hotbg:#f6dccf;--hotfg:#94370f;--display:"Bricolage Grotesque",system-ui,sans-serif;--body:"Inter",system-ui,sans-serif;--h1w:700;'
DARK = '--bg:#121118;--panel:#1a1922;--ink:#e9e7f1;--ink2:#c4c1d1;--muted:#8f8b9d;--rule:#2b2936;--accent:#a3a0f0;--onaccent:#121118;--hot:#f0895f;--done:#6c6879;--ghost:#2f2d3a;--water:#3d5a76;--tagbg:#22202c;--tagfg:#b2aec1;--hotbg:#46240f;--hotfg:#f6b896;'
counts = render(rows=rows, sample=sample, paid_fields=PAID, chip_key="kind", chip_order=ORDER, cfg_js=cfg, site="mpls-opening-soon", subs={
 "__TITLE__": "Minneapolis Opening Soon",
 "__DESC__": f"{len(rows)} Minneapolis businesses about to open or just opened, from build-out permits, new liquor licenses and first health inspections.",
 "__FONTS__": "family=Bricolage+Grotesque:opsz,wght@12..96,700&family=Inter:wght@400;500;600",
 "__LIGHT__": LIGHT, "__DARK__": DARK,
 "__EYEBROW__": f"For recruiters and staffing firms · Minneapolis public records · updated {pulled}",
 "__H1__": f"{len(rows)} Minneapolis businesses about to open, and about to hire",
 "__LEDE__": f"A business that doesn't exist yet has no staff yet. These are the Minneapolis restaurants, shops, clinics, studios and offices building out a new space, taking out a new liquor license, or getting their first health inspection. <b>{cnt('Opening soon')} are at final inspection or waiting on a liquor license</b>, the last step before the doors open, and {cnt('Building out')} more are under construction.",
 "__MAPLABEL__": "Map of Minneapolis with each business as a dot",
 "__NOTE__": f"<p>Sources, all public: the City of Minneapolis building permit register, on-sale liquor license list and food inspection records, pulled {pulled}, and business filings at the Minnesota Secretary of State. Phone, website and status from Google Maps, looked up {pulled}.</p><p>How each signal is read. A build-out counts when the permit requires a new certificate of occupancy, changes the occupancy, or names a new use or tenant; roof, restroom, stair and spec-suite work is left out. Opening soon: the permit is at final inspection, or a new liquor license is pending. A new liquor license is one among the newest the city has issued (numbers run in sequence). A first health inspection means the kitchen had none on record since January 2024. Just opened: the permit closed in the last 60 days, or one of the other two signals with no open permit. The owner is the manager or chief executive on the state filing for the name the city uses; blank when no exact match came back. A Google Maps listing is used only when its street address is the same as the record and, where the city names the business, the names agree. Where the city gives no name, it is used only when one business of the right kind is listed at that address and the business has already opened. Otherwise the phone and website are left blank rather than guessed: {glisted} of {len(rows)} matched.</p><p>Minneapolis only. Saint Paul stopped publishing permits in mid-2025. From Aidan Jude at Brick &amp; Mortar (aidan@brickandmortar.dev).</p>"})
print("rows", len(rows), {s: cnt(s) for s in STAGES}, counts, "named", named, "owner", own, "sample", len(sample), "phone", phone, "website", web, "reach", reach, "google matched", glisted)
