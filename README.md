# Minneapolis Opening Soon

**Live:** https://mpls-opening-soon.vercel.app

Every Minneapolis business that is about to open or just opened, read from three public
records: a commercial build-out permit for a new occupant, a new on-sale liquor license, or a
restaurant's first-ever health inspection. Staged by how close each is to opening, with the
owner or manager from the Secretary of State filing where the city gives a name.

Built for recruiters and staffing firms: a business that doesn't exist yet has no staff yet.
First prospect: The Shortlist (Craigslist 9/23, *"I have also built out teams from zero for
companies entering new markets, so I know what it takes to staff something that does not exist yet"*).
Reuses the Blue Vector hospitality change-event pipeline (`on-the-house/pipeline/permits/hospitality_*.py`, 10/05), widened past restaurants.

## Free and paid

| | what | why |
|---|---|---|
| free | the count, the map of every business, counts by kind, and 10 real rows with stage and permit text | proves the stage signal on real addresses |
| **$5** | all 201 rows; business names (93), phone (64) and website (56) from Google Maps, owner or manager, entity and state filing link; builder; the **closest to opening** sort; the spreadsheet | a recruiter acts by reaching the owner before the first job post; that is the name, the owner and the stage sort |

## Price

$5 once. Set by Aidan on 2026-10-17 for all three products in this round. **A hypothesis:**
one placement at a flat fee is worth hundreds, so one conversation pays for the list many times
over. Revise on checkout-vs-payment evidence.

## The paywall

Same as `mpls-new-rentals` (ported from `msp-house-index` via `salon-rates`, `product-paywall`
skill): `site/` ships only the free slice; `private/bundle/full.json.gz` (gitignored) is uploaded
as `api/_full/` and served by `/api/data` behind an HMAC password minted at Stripe embedded
Checkout and emailed by the webhook. Comp: `python3 scripts/issue_password.py "comp:<label>"`.

## Run it

    python3 pipeline/pull_permits.py   # commercial permits since Oct 1, 2025
    python3 pipeline/build.py          # + liquor, food inspections, Secretary of State (cached)
    python3 pipeline/enrich_places.py  # phone, website, Google status; cached, paid only on a cache miss
    cd scripts && python3 publish.py && python3 deploy.py   # VERCEL_TOKEN in env

See `DATA_MODEL.md` for each field and the ones that could not be filled. MIT licence.
