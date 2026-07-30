# Verification log — Mountain View area run

Audit run: 2026-07-30. 12 practices from Clay. **1 prospect survived verification
out of 6 the scanner flagged.**

## First, a finding about the target city

**Clay has no dental practices tagged in Mountain View, CA at all.** The exact
query the Austin run used —

```sql
select from companies where industry = "Dentists"
  and locations.any(city contains "Mountain View" and state_or_province = "California")
```

— returned **0 rows** with `exhaustionReason: no_more_results`, which is Clay
saying "there are none", not "you hit a limit". Widening to the four neighbouring
cities in one query (`city contains ("Mountain View", "Palo Alto", "Los Altos",
"Sunnyvale", "Santa Clara")`) returned 12 practices, all with domains, and **none
of them in Mountain View**.

Worth knowing before you pick a city: Clay's company database is thin on small
local businesses in some places. Austin returned 37 dental practices; the whole
mid-Peninsula returned 12. A city being wealthy and dense is no guarantee its
small businesses are in the dataset.

## Confirmed real (1)

| Practice | Signal | How it was verified |
|---|---|---|
| Practice MV-H | Server-side load 5.3–8.5s, worse via their own alias domain | 3 serial curl runs: TTFB 5.40 / 5.30 / 8.48s, connect 0.14–0.19s throughout. Their alias `practice-mv-h-alias.example` — the domain on their published email address — redirects to the main site and took **15.15s and 10.97s**. |
| ″ | "Important Covid-19 Updates" banner still in the main navigation in 2026 | Seen in a real Chrome window, and present in the served HTML (`covid-19-updates/` link, title `Important Covid-19 Updates`). |

## False positives (5 of 6 flagged)

### Speed claims that did not reproduce serially (3)

The scanner runs 3 workers in parallel. Every one of these looked slow in that
sweep and is fine when hit one at a time — the same self-inflicted failure the
Austin run documented, still biting even at 3 workers on a 12-domain list.

| Domain | Scanner said | Serial reality (3 runs) |
|---|---|---|
| `practice-mv-l.example` | slow first load: 3.3s | 0.52 / 0.83 / 0.52s |
| `practice-mv-e.example` | sluggish first load: 2.1s | 0.57 / 0.54 / 0.54s |
| `practice-mv-b.example` | sluggish first load: 2.5s | 1.26 / 0.39 / 0.17s |

`practice-mv-l.example` was the **top-ranked prospect at 40 points**. It is not a
prospect. Had this gone out unchecked, it would have told an endodontist their
site was slow when it answers in half a second.

### Signals too weak to email about (2)

`practice-mv-d.example` and `practice-mv-k.example` were flagged only for "copyright year looks
stale". A stale footer year is not a business problem. Same policy as the Austin
run: dropped, not emailed.

## Recorded but not used

- `practice-mv-f.example` — returned **HTTP 403 to the scanner**. Classified
  `INCONCLUSIVE`, never a defect. This is the anti-bot pattern from the Austin
  run; it means "a human should look", not "their site is broken".
- `practice-mv-h.example` — flagged "no booking link in served HTML". Left as
  `needs_render_check` and **kept out of the email**. The site is a referral-based
  endodontic practice with a "Referral Form" and "Patient Login" in the header, so
  the absence of a consumer booking widget is a business model, not a defect.

## Score

6 practices had no detectable issues. 6 were flagged. 1 was real.
