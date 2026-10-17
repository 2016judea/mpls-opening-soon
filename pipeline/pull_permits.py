"""Minneapolis commercial permits (build-outs, new buildings, remodels) since Oct 1, 2025.
Writes private/permits_raw.json. See the mpls-permits skill for the traps this filters."""
import json, urllib.request, urllib.parse, datetime as dt, sys
from pathlib import Path
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "private" / "permits_raw.json"
U = "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/CCS_Permits/FeatureServer/0/query"
W = "permitType='Commercial' AND occupancyType IN ('Comm','Mixed') AND issueDate >= date '2025-10-01'"
F = "permitNumber,permitType,occupancyType,workType,status,milestone,comments,issueDate,completeDate,applicantName,totalFees,Display,APN,Latitude,Longitude,Neighborhoods_Desc"
out, off = [], 0
while True:
    p = dict(where=W, outFields=F, f="json", resultOffset=off, resultRecordCount=2000, returnGeometry="false")
    d = json.load(urllib.request.urlopen(urllib.request.Request(U, data=urllib.parse.urlencode(p).encode()), timeout=120))
    fs = [f["attributes"] for f in d.get("features", [])]
    out += fs
    if not d.get("exceededTransferLimit") or not fs:
        break
    off += len(fs)
json.dump({"pulled": dt.date.today().isoformat(), "rows": out}, open(OUT, "w"))
print("commercial permits", len(out))
