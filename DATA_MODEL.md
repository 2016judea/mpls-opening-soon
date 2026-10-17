# Data model: Minneapolis Opening Soon

Written from the need alone (BUSINESS.md rule 5), then checked against what exists, 2026-10-17.

**The need.** A recruiter who staffs new businesses (first prospect: The Shortlist, Craigslist
9/23: *"I have also built out teams from zero for companies entering new markets, so I know what
it takes to staff something that does not exist yet."*) wants the businesses about to open,
before they post a single job, and who decides.

## Ideal model

**Opening business** (one per new occupant at an address)

| field | answers |
|---|---|
| business name, kind (restaurant, shop, clinic, studio, office...) | who, and is it a kind I staff |
| address, neighborhood, lat/lon | where |
| stage: opening soon / building out / just opened | how close to the first hire |
| signals + dates: build-out permit, new liquor license, first health inspection | why we think it is new, and how fresh |
| expected opening date | when the team has to be in place |
| headcount to hire / open job posts | how big the search is |
| owner or manager, entity | who to call |
| phone, email, website | how to reach them |

## Reality, field by field

| field | source | filled? |
|---|---|---|
| address, stage, signals, dates, permit text, builder | Minneapolis permit register, on-sale liquor list, food inspections | yes, all 201 rows |
| kind | read from the permit text / occupancy code | yes (10 rows "Other business") |
| business name | the city's liquor or health record names it (89), plus 4 from a single matching Google listing; permits do not (parsing names from permit text was wrong 3 of 4 times, so it isn't done) | 93 of 201 |
| owner/manager, entity, state filing | MN Secretary of State, exact-name match | entity 66, a named manager or CEO 14 |
| expected opening date | not published | **no**: proxied by stage (final inspection = last step) |
| headcount / open job posts | not in any public record we hold | **no** |
| phone, website, Google status | Google Maps: Outscraper by name + address for the 89 named rows, Google Places Nearby (40 m) for the rest, cached in `private/cache/places/`; accepted only on the same street address (and agreeing name, or a single business of the right kind) | phone 64, website 56, matched 71 of 201 (2026-10-17, ~$4.93). Named rows match 67 of 89; unnamed only 4 of 112, because towers hold many tenants and a space not yet open still shows its old occupant on Google |

Verdict: build, with the gap stated. The stage signal (what the recruiter can't get anywhere
else) fills completely; contact fills for the named minority. Phone and website were filled from Google Maps on 2026-10-17 (Aidan approved the spend).
