"""The page prints counts straight from private/rows.json, and site/ ships only the free slice:
business names, phones, websites and owners are paid (README "## Free and paid").
Run from the repo root: python3 -m pytest -q tests
"""
import gzip, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.load(open(ROOT / "private" / "rows.json"))
ROWS = D["rows"]
PAGE = (ROOT / "site" / "index.html").read_text()
FREE = json.loads(re.search(r"\nconst FREE=(\{.*?\});\n", PAGE).group(1))
FULL = json.loads(gzip.open(ROOT / "private" / "bundle" / "full.json.gz", "rt").read())["rows"]
PAID = ["name", "named_by", "phone", "website", "gstatus", "owner", "entity", "filed", "sosurl", "by", "also"]
STAGE = {"Opening soon": 0, "Building out": 1, "Just opened": 2}


def test_rows_agree_with_themselves():
    for r in ROWS:
        assert STAGE[r["stage"]] == r["so"], r["addr"]
        assert r["latest"] and r["signals"], r["addr"]
        assert not r.get("phone") or re.fullmatch(r"\(\d{3}\) \d{3}-\d{4}", r["phone"]), r["phone"]
        assert not r.get("website") or re.match(r"https?://", r["website"]), r["website"]
        assert not r.get("sosurl") or r["sosurl"].startswith("https://mblsportal.sos.mn.gov/"), r["sosurl"]
        assert r["lat"] and r["lon"], r["addr"]


def test_page_counts_are_the_data():
    n = len(ROWS)
    cnt = lambda s: sum(r["stage"] == s for r in ROWS)
    reach = sum(bool(r.get("phone") or r.get("website")) for r in ROWS)
    glisted = sum(r.get("gstatus") not in ("", "none", None) for r in ROWS)
    assert FREE["total"] == n
    assert f"<h1>{n} Minneapolis businesses about to open" in PAGE
    assert f"<b>{cnt('Opening soon')} are at final inspection or waiting on a liquor license</b>, the last step before the doors open, and {cnt('Building out')} more are under construction." in PAGE
    assert f'stats:[["{cnt("Opening soon")}","at final inspection' in PAGE and f'["{cnt("Building out")}","building out now"]' in PAGE
    assert f'["{reach}","with a phone number or website to reach them"]' in PAGE
    assert f"{glisted} of {n} matched" in PAGE
    for k, v in FREE["counts"].items():
        assert v == sum(r["kind"] == k for r in ROWS), k
    assert len(FREE["dots"]) == sum(bool(r.get("lat")) for r in ROWS)


def test_site_ships_only_the_free_slice():
    assert len(FREE["rows"]) == 10 and len(FULL) == len(ROWS)
    keys = {k for r in FREE["rows"] for k in r}
    assert not keys & set(PAID), keys & set(PAID)
    for r in FREE["rows"]:
        assert any(f["addr"] == r["addr"] and f["signals"] == r["signals"] for f in FULL), r["addr"]
    # a business name the city never printed must not reach the public page through any field
    names = [f["name"].lower() for f in FULL if f.get("named_by") == "google" and f["name"]]
    blob = json.dumps(FREE).lower()
    assert not [x for x in names if x in blob], "a Google-sourced name leaked into the free slice"
    assert not list((ROOT / "site").rglob("*.gz")) and not (ROOT / "site" / "api" / "_full").exists()
    assert "_vercel/insights/script.js" in PAGE and "posthog" in PAGE
