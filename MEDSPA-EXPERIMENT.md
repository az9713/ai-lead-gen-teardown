# The med spa experiment — a third run, a new vertical, and zero emails

This is the full development record of the third run of the pipeline described in
[`README.md`](README.md): **medical spas and aesthetic clinics in Phoenix and
Scottsdale, Arizona**, paired with a demo site built as a hand-sculpted clay
diorama you scroll through rather than a conventional web page.

It is the first run that produced **no prospects at all**, and it is by some
distance the most useful of the three. Getting to zero required finding and
fixing two bugs in my own tooling, one of which had been silently authorising a
false accusation about a real business as safe to put in a cold email.

Everything below happened on 30 July 2026. No email was sent, in this run or in
either of the two before it.

---

## Why a third run, and why med spas

The first two runs were both dental — Austin, Texas, then the mid-Peninsula in
California. Two runs in one vertical cannot tell you whether a disappointing
result is a property of the vertical or a property of the method. Med spas were
chosen as a deliberately favourable test: they are high-margin, appearance-led,
marketing-heavy businesses. If any category of small business ought to care about
its website, and ought to have one worth criticising, it is this one.

Phoenix and Scottsdale were chosen for the same reason. The mid-Peninsula run had
already established that the data platform's coverage of small local businesses is
thin in places — it had **zero** dental practices tagged in Mountain View at all —
so a metro with a dense, wealthy, aesthetics-oriented market was the fair test.

## Step 1 — The lead search, and a finding about industry taxonomies

The obvious query shape, the one both dental runs used, is to filter on an
industry value:

```sql
select from companies where industry = "Dentists" and locations.any(...)
```

**This cannot work for med spas.** The platform's industry vocabulary has **457
allowed values**. `"Dentists"` is one of them. There is no `"Med Spas"`, no
`"Medical Aesthetics"`, no equivalent. This is not a gap in one dataset so much as
a general property of industry taxonomies: they encode the professions that
existed when the taxonomy was written, and med spas are a recent hybrid of
dermatology, cosmetics and retail wellness.

The fix is to stop asking what a company *is* and start asking what it *says about
itself*:

```sql
select from companies
where description contains ("med spa", "medspa", "medical aesthetics", "botox", "injectables")
  and locations.any(city contains ("Phoenix", "Scottsdale", "Tempe", "Mesa", "Chandler", "Gilbert")
                    and state_or_province = "Arizona")
```

That returned **40 unique companies**, 31 of them in Arizona. The vindication of
the approach is in where they landed: the matches were scattered across **seven
different industry labels** — Wellness and Fitness Services, Medical Practices,
Consumer Services, Personal Care Product Manufacturing, Alternative Medicine,
Education Administration, and even Higher Education. Any industry filter,
however carefully chosen, would have discarded most of the real prospects.

**Search quota, for anyone reproducing this.** Searches consume a *search-results*
quota, not enrichment credits — so an empty API-credits report proves nothing
about how much searching you have done. The free tier meters **results**: 50 per
request, 50 per search, **100 per month**. This one probe consumed roughly 40 of
the month's 100.

## Step 2 — Cutting 40 rows down to 19 real prospects

Keying on self-description has a predictable cost: it also matches everyone who
*talks about* the industry without *being* in it. The 40 rows included the
industry's suppliers and its schools.

Twenty-one rows were dropped, and the reasons are worth listing because they
generalise to any vertical sourced this way:

| Reason | Count | What they were |
|---|---:|---|
| Out of state | 9 | National chains and clinics headquartered in FL, CA, TX, NV, CO, SD — and one in Singapore |
| Training school | 4 | Laser and aesthetics academies that *teach* the procedures rather than perform them |
| Supplier, not clinic | 3 | Pharmaceutical and skincare-product manufacturers selling *into* clinics |
| Not a clinic at all | 3 | Marketing software, a web design agency, a podcast |
| Duplicate domain | 1 | A solo coaching listing sharing a domain with the clinic row that was kept |
| Wrong vertical | 1 | A pain management practice |

That leaves **19 genuine, independent, local prospects** — 12 in Scottsdale, 5 in
Phoenix, 2 in Tempe, mostly in the 2–10 and 11–50 headcount bands.

For scale against the other runs: Austin dentists gave 35 unique companies, the
mid-Peninsula gave 12, Phoenix gave 19. Scottsdale carried the run.

The cut is recorded as an explicit, hand-checked keep-list in `select.py` rather
than a heuristic. Forty rows can be read carefully in one sitting; a classifier
would have been more code, less accurate, and impossible to audit. The reason
string attached to each decision is the part with lasting value.

## Step 3 — The scan, and 14 flags

The scanner (`audit.py`) fetches each domain, times it, and looks for defects a
customer would notice: unreachable sites, HTTP error pages, missing HTTPS, slow
first loads, near-empty homepages, stale copyright years. It runs **3 workers, not
10** — ten parallel requests trip prospects' firewalls and produce phantom 403s,
which is the scanner reporting its own rate limiting as the prospect's fault.

Of the 19 clinics, it flagged **14**:

- 1 as completely unreachable
- 8 for slow or sluggish first loads
- 9 for a stale copyright year (overlapping with the above)

At this point the run looked like its predecessors, and a less careful operator
would have had fourteen emails to write. Every single one of those flags turned
out to be false.

## Step 4 — Verification, where the run actually happened

The project's central rule is that **nothing the scanner says is treated as true**.
Every flag gets three serial fetches five seconds apart, time-to-first-byte
compared against connect time, and a real Chrome window for anything visual or
blocked. The full specification is in [`RUBRIC.md`](RUBRIC.md).

### The speed claims: 8 of 9 evaporated

| What the scanner measured | What three serial runs measured |
|---|---|
| slow, 8.3s | **0.57s** |
| slow, 4.7s | **0.33s** |
| slow, 3.5s | **0.35s** |
| sluggish, 1.8s | **0.92s** |
| sluggish, 2.4s | **0.44s** |
| sluggish, 1.9s | **0.70s** |
| sluggish, 1.7s | **0.57s** |
| sluggish, 2.1s | **0.55s** |

The worst case is the first row: the scanner measured 8.3 seconds against a true
0.57 — wrong by a factor of fifteen. These sites are not slow. The parallel sweep
is what made them look slow, exactly as in both previous runs, at the same rate,
even at only 3 workers against a 19-domain list.

### The one genuinely broken site — and why it still is not a prospect

One clinic's domain accepted **no connections on port 443 at all**. The TCP
connect timed out after about 21 seconds, in `curl` and in a real Chrome window
alike. Over plain HTTP it served a 301 redirect to a page on a different
company's domain, and that page rendered **"Uh oh, page not found."**

The defect is real, reproducible, and customer-visible: anyone typing the clinic's
address into a modern browser gets nothing, and the fallback lands on a 404.

It is still not a prospect. The practice had been **absorbed into a multi-state
dermatology group**, so there is no independent local owner to sell a website to,
and the acquirer's own site returned **429** to every automated request — which
the rubric classifies as inconclusive, because a firewall blocking a script is not
a broken website. It is recorded in the scanner's `OVERRIDES` map with that
reasoning, which forces its score to zero. That is the same mechanism the Austin
run used for a practice whose stored domain had gone stale.

### The copyright signal: wrong 9 times out of 9

The scanner's test was: does a year between 1900 and 2015 appear anywhere in the
page body, and does the word "copyright" appear anywhere in the page body. Those
two conditions need not be anywhere near each other, and on a modern site they
never are. What it had actually been matching:

| What matched | Why it is not a stale copyright year |
|---|---|
| `.ast-footer-copyright` | a CSS class name in a stylesheet |
| `<p class="copyright">` | likewise |
| `new Date().getFullYear()` | a footer that writes the current year in JavaScript — never stale |
| `{{right_now.year}}` | an unrendered template tag, same story |
| "Copyright 2023 Fonticons, Inc." | **the bundled FontAwesome icon library's own licence comment** |
| a numeric CSS value like `2000` | a width or z-index that happens to look like a year |
| a footer reading **© 2025** | current, and flagged anyway |

One flagged site's footer says 2025. An email telling that owner their copyright
year "looks stale" would have been read — correctly — as proof that nobody had
actually looked at their site.

**Fixed:** the year must now be attached to a copyright mark, pages that render
their year dynamically are exempt, and the whole signal is demoted out of the
score into `needs_render_check` — a lead for a human to check, never a fact. It
now fires on zero of nineteen.

## Step 5 — The bug that mattered: the verifier was clearing a false claim

This is the finding that justifies the run.

For the dead host, `verify.py` returned:

> **SERVER-SIDE SLOW — TTFB 21.25–21.27s with connect under 0.00s; safe to put in
> writing.**

That is the strongest verdict the script can issue — the single phrase in this
entire framework that authorises putting a claim in an email to a stranger.

Here is the evidence it said that from:

```
run1: http_code=000 namelookup=0.015176 connect=0.000000 appconnect=0.000000
      starttransfer=21.251336 total=21.251339 size=0
```

`http_code=000` and `size=0` mean **no response ever arrived**. `curl` reports
`connect=0.000000` when the TCP connect *itself* times out — the connection was
never established, so there is no connect time to report. The verdict function
read only `starttransfer` and `connect`. It took that zero as "connected
instantly", paired it with a 21-second first byte, and concluded the server was
generating the page slowly.

The server was not slow. Nothing was listening.

This is the worst failure mode the project can have. Not a missed prospect — a
confident, evidence-attached, factually false claim about a real business's
website, marked as cleared for sending. It had survived two entire runs undetected
for the dullest possible reason: every domain in Austin and on the mid-Peninsula
happened to answer on port 443. Phoenix was the first run to hit a host that
returned nothing, and that is the only reason it was found.

**Fixed:** `verdict()` now inspects `http_code` *before* it interprets any timing
and returns `NO RESPONSE` when a run reports `000`. A second new branch returns
`INCONCLUSIVE` for 401/403/429, which the rubric had always required of the
scanner but had never enforced in the verifier. Both are pinned as no-network test
fixtures built from this run's real captured numbers, so `python verify.py
--self-check` now proves six verdicts rather than four.

A differential test on the identical raw evidence:

```
OLD: SERVER-SIDE SLOW - TTFB 21.27-21.36s with connect under 0.00s; safe to put in writing
NEW: NO RESPONSE  - codes 000/000/000; the connection never completed, so these
                    timings are not a speed measurement.
```

## Step 6 — Two redaction leaks, caught before publication

Everything published here is generated by `redact.py`, which rewrites every real
identifier to a `.example` alias and **exits non-zero** if any of 227 known
identifiers survives, or if any hostname in the output is not an alias. Writing
this run up broke it twice:

1. **The acquirer's domain.** It appeared in the write-up as a full URL, was not a
   prospect, and so was not in the alias map. The structural hostname check caught
   it, and it was added to the map.
2. **Real dropped-business names.** The first version of `select.py` listed every
   dropped company by name in its `DROP` dictionary — and that dictionary is copied
   verbatim into the published JSON. Twenty-one real businesses would have been
   published in a file whose entire purpose is anonymity. It now carries counts and
   categories only; the named breakdown stays in the gitignored script.

**The automated check found the first. A manual `grep` of the output found the
second** — which is the same lesson as the redirect-domain leak fixed earlier in
this repo's history. A substring check only finds what you told it to look for.

There is a known remaining weakness, documented here rather than hidden: the
structural hostname check only inspects hostnames that appear inside a
`scheme://` URL. A bare domain written in prose is invisible to it.

## Step 7 — The demo site: a claymation scroll-world

The sales asset for this vertical is not a conventional page. It is a **two-scene
scroll-world**: a stop-motion clay diorama where your scroll position scrubs a
video timeline, so scrolling flies the camera into the model.

The subject is **Cholla & Clay Aesthetics**, a fictional clinic. The name was
checked against real businesses in the metro before use, the phone number is in
the 555-01xx block reserved for fiction, and the address is on an invented street.

### Production, and what it cost

Two still frames were generated, then three video clips: a dive into scene one, a
connector, and a dive into scene two. Measured on the starter plan by diffing the
credit balance before and after — **61.78 → 35.28, so 26.5 credits for two stills
and three clips, with zero re-rolls**:

| Model | Billed | Supports an end image? |
|---|---:|---|
| `nano_banana_pro` still (1k) | 2 | — |
| `minimax_hailuo` (6s) | 6 | ❌ |
| `kling3_0_turbo` | 7.5 | ❌ |
| **`kling3_0` (5s)** | **7.5** | ✅ |
| `seedance_2_0_mini` | 12.5 | ✅ |
| `seedance_2_0` | 22.5 | ✅ |

Three practical findings:

- **The cost estimator is a ceiling, not a price.** It quoted `kling3_0` at 10 for
  a 5-second clip; the billed charge was 7.5, confirmed by both the balance
  movement and the transaction log.
- **The "cheap draft tier" was the expensive one.** The scroll-world skill's own
  documentation treats `seedance_2_0_mini` as the budget option. At 12.5 it costs
  two thirds more than `kling3_0`.
- The architecture requires an **end image** to lock each clip's final frame,
  which is what eliminated the two cheaper models. Verified against the model
  catalogue rather than assumed.

Smaller traps worth recording: the video model defaults to **sound on**, output is
**1284×716** rather than a clean 1280×720 (encode what `ffprobe` reports, never
upscale), and a connector's start image must be the previous clip's **last** frame
uploaded as a fresh asset — passing the previous job's id silently supplies that
video's *first* frame instead and breaks the seam.

### Seam quality

The illusion depends entirely on consecutive clips sharing an identical boundary
frame. Measured by PSNR against a 33 dB benchmark:

| Boundary | PSNR |
|---|---:|
| dive 1 → connector | 39.99 dB |
| connector → dive 2 | 40.24 dB |
| connector end vs. scene-two still | 37.78 dB |
| dive 2 start vs. scene-two still | 39.24 dB |

All four seams frame-lock comfortably. The stitched preview runs 15.125 seconds.

### The connector re-sculpts instead of travelling — and the copy had to follow

The connector was intended to lift up and fly across to a second room. Instead it
pulls up correctly and then **transforms the room in place**: the bench becomes a
cabinet, the reception counter becomes a treatment bed.

It could not have done otherwise. Both stills place their diorama at the same spot
on the same table, and the end image dictates the destination framing, so there
was nowhere to fly *to*. Rather than spend ~17 credits re-rolling for the literal
hop, it was kept — clay re-moulding itself is a legible, deliberate-looking effect,
arguably better than the hop would have been.

**The consequence is a writing constraint, and it is the interesting part.** The
page copy must never promise a journey between places, because the footage does
not deliver one. So the hero reads "Everything here was sculpted by hand… scroll,
and the clay opens up," and the finale reads "The same care, at the table." Both
describe a change of state. Neither describes travel.

### The page

The page is a single HTML file plus a vanilla-JavaScript scrub engine — no build
step, no framework. The scroll-driven fixed video layer is the engine's job; the
only additions are the palette, sampled from the rendered clay, and the amber
banner.

**The banner is non-negotiable.** This is a public URL that a stranger would open
from a cold email, and without it the demo reads as a real clinic being claimed as
a client. It is pinned above every piece of the engine's own fixed furniture and
never scrolls away.

One honest limitation: a proper footer was built and then removed, because the
engine sets the document height from its own scroll track and anything after that
track cannot be reached by scrolling. The address moved into the finale copy,
where the engine actually renders it.

The generated clips carry **C2PA content credentials** identifying them as
`trainedAlgorithmicMedia`. These were deliberately left intact. Stripping them
would remove an AI-provenance signal from media published on the open web.

---

## Why zero emails, when three prospects were found

This is the accounting that matters, and the two numbers come from different
places.

**The three prospects are the total across all three runs, and none of them are
from this one.**

| Run | Businesses scanned | Scanner flagged | Survived verification |
|---|---:|---:|---:|
| Austin, TX — dental | 37 | 20 | **2** |
| mid-Peninsula, CA — dental | 12 | 6 | **1** |
| Phoenix / Scottsdale, AZ — med spa | 19 | 14 | **0** |
| **Total** | **68** | **40** | **3** |

So: 68 businesses examined, 40 accused by the scanner, **3 with a defect that
survived being checked**. The scanner is wrong about **92%** of what it flags, and
that figure has now held steady across two verticals and three metropolitan areas.

**Why the three prospects produced no emails**, in order of how much each matters:

1. **Zero of them are med spas.** All three came from the two dental runs. This
   run contributed none, so there was nobody in Phoenix to write to. A draft would
   have required inventing a problem, which is the precise failure the whole
   verification apparatus exists to prevent.
2. **The three that did survive have drafts, and the drafts were never sent.**
   `pipeline/draft-emails.md` holds two, the mid-Peninsula run holds one. All are
   marked draft-only, all still contain `[YOUR NAME]` and `[YOUR EMAIL]`
   placeholders, and **no sending was ever configured** — no mailbox, no sending
   domain, no sequence, no API key. Three prospects, three drafts, zero sent.
3. **Contact data was the quiet second bottleneck.** Work-email enrichment
   returned nothing for the mid-Peninsula prospect; the draft falls back to a
   general inbox published on the practice's own website header. A verified
   problem you cannot deliver to anyone is not a lead either.

The blunt reading: the pipeline works, and what it reliably produces is not leads
but *disproved* leads. Its real output is the verification log.

## What this says about the premise

Three cities, two verticals, 68 businesses, and the honest count of demonstrably
broken websites is three. The pitch behind this workflow — sweep a metro, receive
a list of businesses with real, nameable website problems — does not survive
contact with the websites themselves. Most small clinics are on Squarespace, Wix,
or a maintained WordPress build, and they load in well under a second. There is no
epidemic of broken small-business websites to arbitrage, at least not in these
three metros.

Choosing a favourable vertical did not help. Med spas are exactly the sort of
business that ought to have generated hits, and they generated fewer than dental
did.

### The gap that is actually worth pursuing

**Businesses with no website at all never enter the funnel.** The scanner drops
any row without a domain before it does anything else — one of the 40 raw Phoenix
rows was exactly this, and it was discarded silently.

That is the highest-intent signal available in this entire framework, and it needs
no verification gate whatsoever, because there is nothing to be wrong about. You
cannot falsely accuse someone of not having a website. Sourcing from a maps or
places API rather than a B2B database would surface precisely these businesses:
a name, a phone number, a street address, and no site.

Everything in this repository points at that gap. None of it has been built yet.

---

## Files from this run

| Path | What |
|---|---|
| [`pipeline-phoenix/VERIFICATION.md`](pipeline-phoenix/VERIFICATION.md) | The full verification log, with raw evidence |
| [`pipeline-phoenix/audit_results.json`](pipeline-phoenix/audit_results.json) | Every scanned clinic and every signal |
| [`pipeline-phoenix/verification-raw.txt`](pipeline-phoenix/verification-raw.txt) | Unedited `curl` output for all nine re-checked domains |
| [`pipeline-phoenix/audit.py`](pipeline-phoenix/audit.py) | The scanner as it ran, with the fixed copyright check |
| [`verify.py`](verify.py) | The verifier, with the `NO RESPONSE` fix and its self-check |
| [`medspa-demo/`](medspa-demo/) | The claymation scroll-world demo site |
| [`medspa-demo/provenance.json`](medspa-demo/provenance.json) | Every prompt, model, generation id, credit charge and PSNR figure for the media |

All prospect names and domains in the published files are `.example` aliases. The
unredacted originals are gitignored and stay on disk.
