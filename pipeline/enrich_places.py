#!/usr/bin/env python3
"""Fill business name, phone, website and Google status on private/rows.json (run after build.py).

Two lookups, both cached to private/cache/places/ so nothing is ever bought twice:
  named rows   -> Outscraper Maps search "<name>, <address>, Minneapolis, MN" (~$0.003/record)
  unnamed rows -> Google Places Nearby Search, 40 m around the row, by distance (~$0.035/call),
                  and named rows Outscraper could not match fall back to it.
An address query alone returns the building, never the tenant (probed 2026-10-17), hence Nearby.

A candidate is accepted only when its street address is the row's (same number, same street).
Then: a named row also needs the name to agree; an unnamed row needs exactly ONE open business
at that address (a tower with ten tenants is ambiguous, so blank) whose Google type fits the
row's kind. A wrong name on a paid row is worse than a blank.

    python3 pipeline/enrich_places.py --dry-run   # what it would buy
    python3 pipeline/enrich_places.py             # needs OUTSCRAPER_API_KEY, GOOGLE_PLACES_API_KEY
"""
import json, os, re, sys, hashlib, urllib.request, difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIV = ROOT / "private"
CACHE = PRIV / "cache" / "places"; CACHE.mkdir(parents=True, exist_ok=True)
CAP_USD = 15.0
RATE = {"outscraper": 0.003 * 5, "google": 0.035}  # worst case per call (outscraper: limit 5 records)
DRY = "--dry-run" in sys.argv


def env(k):
    v = os.environ.get(k)
    if not v:
        for line in open(Path.home() / "Desktop/bricks/.env"):
            if line.startswith(k + "="): v = line.split("=", 1)[1].strip().strip('"')
    if not v: sys.exit(f"{k} missing from env and ~/Desktop/bricks/.env")
    return v


spent = {"outscraper": 0, "google": 0}


def cached(provider, payload, fetch):
    h = hashlib.sha1(json.dumps([provider, payload], sort_keys=True).encode()).hexdigest()[:16]
    f = CACHE / f"{provider}_{h}.json"
    if f.exists(): return json.load(open(f))["res"]
    if DRY: spent[provider] += 1; return None
    if sum(spent[p] * RATE[p] for p in spent) + RATE[provider] > CAP_USD: sys.exit("would exceed the $15 cap")
    res = fetch(); spent[provider] += 1
    json.dump({"provider": provider, "payload": payload, "res": res}, open(f, "w"))
    return res


def outscraper(q):
    from outscraper import ApiClient
    return ApiClient(api_key=env("OUTSCRAPER_API_KEY")).google_maps_search([q], limit=5, language="en", region="US")[0]


MASK = "places.id,places.displayName,places.formattedAddress,places.shortFormattedAddress,places.nationalPhoneNumber,places.websiteUri,places.businessStatus,places.primaryType,places.types"


def nearby(lat, lon):
    body = json.dumps({"maxResultCount": 20, "rankPreference": "DISTANCE",
                       "locationRestriction": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": 40.0}}}).encode()
    req = urllib.request.Request("https://places.googleapis.com/v1/places:searchNearby", data=body, headers={
        "Content-Type": "application/json", "X-Goog-Api-Key": env("GOOGLE_PLACES_API_KEY"), "X-Goog-FieldMask": MASK})
    return json.load(urllib.request.urlopen(req, timeout=30)).get("places", [])


# ---- address and name matching
WORDS = {"north": "n", "south": "s", "east": "e", "west": "w", "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
         "street": "st", "avenue": "ave", "av": "ave", "boulevard": "blvd", "road": "rd", "drive": "dr", "parkway": "pkwy", "place": "pl",
         "lane": "ln", "court": "ct", "terrace": "ter", "first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th"}
DIRS = {"n", "s", "e", "w", "ne", "nw", "se", "sw"}
SUFFIX = {"st", "ave", "blvd", "rd", "dr", "pkwy", "pl", "ln", "ct", "ter", "hwy", "mall", "way", "cir"}


def street(a):
    """'117 Lake St W' -> (117, {'lake'}, {'w'}); None if no house number."""
    a = (a or "").split(",")[0].lower().replace(".", "").strip()
    a = re.split(r"\s(?:#|suite\b|ste\b|unit\b|apt\b|fl\b|floor\b|\d+(?:st|nd|rd|th)\s+fl)", a)[0]
    m = re.match(r"\s*(\d+)(?:\s*-\s*(\d+))?\s+(.*)", a)
    if not m: return None
    toks = [WORDS.get(t, t) for t in re.findall(r"[a-z0-9]+", m.group(3))]
    lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
    return (lo, hi), {t for t in toks if t not in DIRS and t not in SUFFIX}, {t for t in toks if t in DIRS}


def same_address(row_addr, g_addr):
    """g_addr may lead with a building name ('U.S. Bank Plaza, 220 South 6th St, ...'): try each part."""
    return any(_same(row_addr, part) for part in (g_addr or "").split(","))


def _same(row_addr, g_addr):
    a, b = street(row_addr), street(g_addr)
    if not a or not b or a[1] != b[1] or not a[1]: return False
    if a[2] and b[2] and a[2] != b[2]: return False
    n = a[0][0]
    return b[0][0] <= n <= b[0][1] or a[0][0] <= b[0][0] <= a[0][1]


GENERIC = {"llc", "inc", "co", "the", "and", "of", "mpls", "minneapolis", "restaurant", "bar", "cafe", "kitchen", "grill", "company", "corp", "dba", "mn", "llp",
           # words two different businesses share (Skyway Pho -> Skyway Wok, Bole Ethiopian Cuisine -> All Nigerian Cuisine)
           "cuisine", "skyway", "uptown", "northeast", "north", "south", "loop", "food", "foods", "street", "market", "deli", "pizza",
           "coffee", "tacos", "house", "club", "pub", "bakery", "catering", "hospitality", "operators", "enterprises", "group", "holdings"}


def core(n): return [t for t in re.findall(r"[a-z0-9]+", (n or "").lower().replace("'", "")) if t not in GENERIC]


def same_name(a, b):
    ta, tb = core(a), core(b)
    if not ta or not tb: return False
    if set(ta) & set(tb) and any(len(t) >= 4 for t in set(ta) & set(tb)): return True
    return difflib.SequenceMatcher(None, "".join(ta), "".join(tb)).ratio() >= 0.8


KIND_TYPES = {
    "Food and drink": {"restaurant", "bar", "cafe", "bakery", "coffee_shop", "meal_takeaway", "food", "brewery", "night_club", "pub", "wine_bar", "ice_cream_shop", "deli", "food_store", "liquor_store"},
    "Shop": {"store", "clothing_store", "home_goods_store", "furniture_store", "convenience_store", "grocery_store", "supermarket", "book_store", "jewelry_store", "shoe_store", "florist", "pet_store", "electronics_store", "hardware_store", "cell_phone_store", "liquor_store"},
    "Salon, spa and fitness": {"beauty_salon", "hair_salon", "hair_care", "nail_salon", "spa", "gym", "fitness_center", "yoga_studio", "barber_shop", "beauty_salon", "massage", "tattoo_shop", "skin_care_clinic", "sports_activity_location"},
    "Health care": {"doctor", "dentist", "hospital", "health", "pharmacy", "physiotherapist", "medical_lab", "chiropractor", "dental_clinic", "medical_clinic", "wellness_center"},
    "Child care and school": {"school", "preschool", "child_care_agency", "primary_school", "secondary_school", "university"},
    "Hotel": {"lodging", "hotel"},
}
NOT_A_BUSINESS = {"premise", "subpremise", "street_address", "route", "parking", "atm", "bus_stop", "transit_station", "apartment_building", "apartment_complex", "condominium_complex", "housing_complex", "point_of_interest"}


def g_norm(p):
    return dict(name=(p.get("displayName") or {}).get("text", ""), addr=p.get("shortFormattedAddress") or p.get("formattedAddress", ""),
                phone=p.get("nationalPhoneNumber", ""), site=p.get("websiteUri", ""), status=p.get("businessStatus", ""),
                types=set(p.get("types") or []), primary=p.get("primaryType", ""), src="google")


def o_norm(p):
    t = {x.strip().lower().replace(" ", "_") for x in (p.get("subtypes") or "").split(",") if x.strip()}
    return dict(name=p.get("name", ""), addr=p.get("street") or p.get("full_address") or "", phone=p.get("phone") or "", site=p.get("website") or p.get("site") or "",
                status=p.get("business_status") or "", types=t, primary=(p.get("type") or "").lower().replace(" ", "_"), src="outscraper")


def is_business(c):
    real = c["types"] - NOT_A_BUSINESS
    return bool(real) and c["primary"] not in ("building", "premise", "subpremise", "street_address")


def fits_kind(c, kind):
    """Exact Google type in the kind's set. Office / Other business never pass: an office tower's
    one Google listing is as likely the landlord's garage as the new tenant (2026-10-17 spot check)."""
    return bool((c["types"] | {c["primary"]}) & KIND_TYPES.get(kind, set()))


STATUS = {"OPERATIONAL": "operational", "FUTURE_OPENING": "opening soon", "CLOSED_TEMPORARILY": "temporarily closed"}


def pick(row, cands):
    at = [c for c in cands if same_address(row["addr"], c["addr"]) and is_business(c) and c["status"] != "CLOSED_PERMANENTLY"]
    if row["name"]:
        hit = [c for c in at if same_name(row["name"], c["name"]) or any(same_name(n, c["name"]) for n in row["also"].split("; ") if n)]
        return (hit[0], "named") if hit else (None, "no name match at the address" if at else "nothing at the address")
    names = {c["name"].lower() for c in at}
    if not at: return None, "nothing at the address"
    if len(names) > 1: return None, f"ambiguous: {len(names)} businesses at the address"
    c = at[0]
    if not fits_kind(c, row["kind"]): return None, "one business, kind does not fit"
    # until the doors are open, the listing there is the outgoing occupant unless Google already
    # shows the new one as opening soon (810 38th St E: permit "new dispensary", listing a nutrition club)
    if row["stage"] != "Just opened" and c["status"] != "FUTURE_OPENING": return None, "not open yet: listing is likely the old occupant"
    return c, "address"


def phone_fmt(p):
    """Outscraper gives '+1 612-788-1383', Google '(612) 788-1383': one format on the page."""
    d = re.sub(r"\D", "", p or "")
    d = d[1:] if len(d) == 11 and d[0] == "1" else d
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else (p or "")


def main():
    D = json.load(open(PRIV / "rows.json"))
    rows = D["rows"]; why = {}
    for r in rows:
        if r.pop("named_by", "") == "google": r["name"] = ""  # re-runs start from the city's names
        r["phone"] = r["website"] = r["gstatus"] = ""
        c, reason = None, ""
        if r["name"]:
            res = cached("outscraper", f"{r['name']}, {r['addr']}, Minneapolis, MN", lambda: outscraper(f"{r['name']}, {r['addr']}, Minneapolis, MN"))
            if res is None: continue
            c, reason = pick(r, [o_norm(p) for p in res])
        if not c:
            res = cached("google", [r["lat"], r["lon"]], lambda: nearby(r["lat"], r["lon"]))
            if res is None: continue
            c, reason = pick(r, [g_norm(p) for p in res])
        why[reason] = why.get(reason, 0) + 1
        r["phone"], r["website"], r["gstatus"] = (phone_fmt(c["phone"]), c["site"], STATUS.get(c["status"], "")) if c else ("", "", "none")
        if c and not r["name"]: r["name"], r["named_by"] = c["name"], "google"
    print("calls this run", spent, "worst-case $%.2f" % sum(spent[p] * RATE[p] for p in spent))
    if DRY: return
    json.dump(D, open(PRIV / "rows.json", "w"))
    print("matched", sum(r["gstatus"] not in ("", "none") for r in rows), "of", len(rows), why)
    print("name", sum(bool(r["name"]) for r in rows), "phone", sum(bool(r["phone"]) for r in rows), "website", sum(bool(r["website"]) for r in rows))


if __name__ == "__main__":
    main()
