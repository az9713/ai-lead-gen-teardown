# Verification log — Phoenix / Scottsdale med spa run

Audit run: 2026-07-30. 19 clinics from Clay. **No prospect survived verification
out of the 14 the scanner flagged.** This is the first run where the answer is
zero, and the reason is worth more than a prospect would have been: two of the
three tools in the stack were producing false accusations, and this run is how
that was found.

## The headline: the verifier itself was broken

`verify.py` told me `practice-ao.example` was **"SERVER-SIDE SLOW — TTFB
21.25–21.27s with connect under 0.00s; safe to put in writing."** That is the
strongest verdict the script can issue, the one phrase in the whole framework
that authorises putting a claim in an email.

It was wrong. Here is the raw line it based that on:

```
run1: http_code=000 namelookup=0.015176 connect=0.000000 appconnect=0.000000
      starttransfer=21.251336 total=21.251339 size=0 url=https://practice-ao.example/
```

`http_code=000` and `size=0` mean **no response ever arrived**. curl reports
`connect=0.000000` when the TCP connect itself times out — the connection was
never established, so there is no connect time to report. `verdict()` only ever
read `starttransfer` and `connect`, so it read that zero as "connected
instantly", paired it with a 21-second first byte, and concluded the server was
thinking hard. The server was not thinking at all. Nothing was listening.

This is the most dangerous failure mode the project can have: not a missed
prospect, but a confident, evidence-attached, factually false claim about a real
business's website, cleared for sending. It survived two prior runs because
neither happened to hit a dead host — every domain in Austin and on the
mid-Peninsula answered on port 443.

**Fixed** in `verify.py`: `verdict()` now checks `http_code` before it looks at
any timing, and returns `NO RESPONSE` when a run reports `000`. A second new
branch returns `INCONCLUSIVE` for 401/403/429, which the rubric already required
of the scanner but the verifier had never enforced. Both cases are pinned in
`python verify.py --self-check`, using this run's actual numbers as the fixture.

## What is actually true about `practice-ao.example`

Verified in curl and in a real Chrome window, 2026-07-30:

| Check | Result |
|---|---|
| `https://practice-ao.example` | TCP connect times out after ~21s. Chrome shows an error page and never loads. |
| `https://www.practice-ao.example` | Same, ~21s. |
| `http://practice-ao.example` | **301** → a landing page on the acquirer's domain |
| That redirect target, in Chrome | **"Uh oh, page not found"** |
| the acquirer's domain, to any scripted request | **429** — WAF, inconclusive by the rubric |

So the defect is real and a customer would hit it: the practice's own domain
serves nothing over HTTPS, and the fallback redirect lands on a 404 on the
acquirer's site.

**It is still not a prospect.** The practice has been absorbed into a
multi-state dermatology group. There is no independent local
practice to sell a website to, and the entity that owns the broken redirect is a
chain whose own site blocks automated requests. Recorded in the scanner's
`OVERRIDES` map with that reasoning, which forces its score to zero — the same
mechanism the Austin run used for a practice whose Clay domain was stale.

## The copyright-year signal was noise, 9 times out of 9

The scanner flagged nine of nineteen sites for `copyright year looks stale`,
worth 10 points each. **Every one was an artifact.** The test was: does any year
between 1900 and 2015 appear anywhere in the body, and does the word "copyright"
appear anywhere in the body. Those two things need not be near each other, and
on a modern site they never are. What actually matched:

| Site | What the scanner actually found |
|---|---|
| `practice-ak.example` | the CSS class name `.ast-footer-copyright`; the "year" was a number in a stylesheet |
| `practice-al.example`, `practice-as.example` | footers that write the year with `new Date().getFullYear()` — always current |
| `practice-ba.example` | an unrendered template tag, `{{right_now.year}}` |
| `practice-az.example` | **FontAwesome's bundled licence comment**, "Copyright 2023 Fonticons, Inc." |
| `practice-ar.example` | the class name `<p class="copyright">` |
| `practice-bb.example` | a footer reading **© 2025** — current, and flagged anyway |
| `practice-at.example` | a bare "Copyright ©" with no year at all |
| `practice-aw.example` | on re-fetch, no stale year matched at all — it did not even reproduce |

**Fixed** in `phoenix/audit.py`: the year must now be attached to a copyright
symbol or the word itself, the page must not render its year dynamically, and
the whole signal is **demoted out of the score** into `needs_render_check` — a
lead for a human, never a fact. After the fix it fires on zero of nineteen.

This one had a real cost. `practice-bb.example`'s footer says 2025. An email
telling that owner their copyright year "looks stale" would have been read, and
correctly, as proof that nobody had looked at their site.

## Speed claims that did not reproduce serially (8 of 9)

Same story as both previous runs, at the same rate. The scanner's 3-worker
parallel sweep produces slow readings that vanish when the same host is fetched
one at a time, 5 seconds apart.

| Site | Scanner said | Three serial runs, fastest |
|---|---|---|
| `practice-aw.example` | slow, 8.3s | **0.57s** |
| `practice-aq.example` | slow, 4.7s | **0.33s** |
| `practice-ay.example` | slow, 3.5s | **0.35s** |
| `practice-al.example` | sluggish, 1.8s | **0.92s** |
| `practice-ar.example` | sluggish, 2.4s | **0.44s** |
| `practice-az.example` | sluggish, 1.9s | **0.70s** |
| `practice-aj.example` | sluggish, 1.7s | **0.57s** |
| `practice-au.example` | sluggish, 2.1s | **0.55s** |

`practice-aw.example` is the one to remember: the scanner measured **8.3 seconds** and the
truth was **0.57** — a factor of fifteen. Raw evidence for all nine domains,
including the three timed runs each, is in `verification-raw.txt`.

## Running totals across three runs

| Run | Found | Flagged | Survived |
|---|---:|---:|---:|
| Austin, TX (dental) | 37 | 20 | 2 |
| mid-Peninsula, CA (dental) | 12 | 6 | 1 |
| **Phoenix / Scottsdale, AZ (med spa)** | **19** | **14** | **0** |

68 practices scanned, 40 flagged, **3 real**. The scanner is wrong about 92% of
what it flags. That number has been stable across two verticals and three
metros, which is the strongest argument in this repo for why the verification
gate exists.

## What this says about the lead-gen premise

Three cities, two verticals, and the honest count of businesses with a
demonstrably broken website is three. The pitch that a scanner can sweep a
metro and hand you a list of prospects with real, nameable problems does not
survive contact with the sites themselves. Most small clinics are on Squarespace,
Wix, or a maintained WordPress build, and they load in under a second.

The structural gap named in the last two handoffs is now the more interesting
half of the funnel, not a footnote: **businesses with no domain at all never
enter it**, because `audit.py` drops any row without one. One of the 40 raw
Phoenix rows had no domain. That is the highest-intent signal available — there
is no website to be wrong about — and this pipeline is blind to it by
construction. Sourcing from Google Maps Places rather than Clay would fix it.

## Nothing was sent

No emails drafted, no contact attempted, in any of the three runs.
