# Verification log — every signal that was checked by hand

Audit run: 2026-07-30. 35 unique Austin dental practices from Clay.

The automated scanner's first pass produced 20 "prospects". After verification,
**2** were real. This file records what happened to the rest, because the failure
modes repeat and are worth knowing before running this on a bigger list.

## Confirmed real (2)

| Practice | Signal | How it was verified |
|---|---|---|
| Practice A | Bare `practice-a.example` doesn't load; only `www` works | `nslookup` → `192.0.2.1` (RFC 5737 reserved, unroutable). Chrome failed to navigate. `www` returns 200. |
| Practice B | Server-side load 4.4–8.0s | 3 serial curl runs, no concurrency. TTFB 4.40 / 6.47 / 7.83s, connect time <0.36s throughout. |

## False positives, by cause

### 1. Anti-bot blocking read as "site broken" (4+ practices)
`practice-d.example` returned a hard **403 on three consecutive serial requests**
with a Chrome user-agent — and rendered perfectly in real Chrome. A bare curl
user-agent got 200 where the *spoofed* Chrome UA got 403: the WAF blocks scripts
pretending to be browsers, which is exactly what the scanner was.

**Fix applied:** 401/403/429 are now classed `INCONCLUSIVE`, never a defect.

### 2. My own concurrency caused the failures (2 practices)
`practice-e.example` and `practice-d.example` reported "unreachable"/"403" at 10 parallel
workers. Serially, both return 200 in ~1.3s. The scanner was rate-limiting itself
and then reporting the symptom as the prospect's fault.

**Fix applied:** 3 workers, plus a 5-second cooldown before any re-check. Re-checking
immediately just re-triggers the same block.

### 3. Python's TLS stricter than every browser (1 practice)
`practice-g.example` was reported unreachable via `CERTIFICATE_VERIFY_FAILED`.
curl and browsers accept the chain and get 200. Python's `ssl` module rejects
incomplete chains that real clients tolerate.

**Fix applied:** fetch via curl instead of urllib.

### 4. Client-rendered pages look empty to an HTML scraper (2+ practices)
`practice-f.example` was flagged "no online booking link". The live page has a
prominent **"24/7 Online Scheduling"** button — injected by JavaScript, absent from
the served HTML. Same cause for "no viewport meta tag".

**Fix applied:** these two are now recorded as `needs_render_check` — leads to
verify, excluded from the ranking score. Fixing this properly needs a headless
browser, which is the upgrade path if content signals start mattering.

### 5. Benign TLS teardown read as connection failure (1 practice)
`practice-e.example` returned curl exit 56 (`server closed abruptly, missing
close_notify`) *alongside a complete HTTP 200 response*. The scanner trusted the
exit code over the status code.

**Fix applied:** trust the HTTP status when one is present, whatever curl's exit code.

### 6. Clay's stored domain was simply wrong (1 practice)
`practice-c.example` genuinely doesn't resolve, and the scanner ranked
it the #1 prospect at 100 points. But the practice's real site is
`practice-c-live.example` — HTTP 200 in 0.85s. The giveaway was Clay's own
enrichment returning `alpha@practice-c-live.example`.

**No automated fix.** A dead domain in a CRM does not mean a dead business. Recorded
in the `OVERRIDES` map in `audit.py`.

## Note on the source video

Samin's video email says of this same practice: *"the bare domain times out, and the
www version returns a 403 Forbidden... Anyone finding you on Google right now is
likely hitting a dead end."*

The bare-domain half is correct — we reproduced it independently. The www 403 is the
same anti-bot artifact documented above: `www.practice-a.example` renders a working
site with a Book Online button in real Chrome. So the email overstates the problem —
it tells a dentist their whole site is unreachable when roughly everyone reaching it
via a normal link sees a working site.

The narrow claim (bare domain broken) is real and worth sending. The broad one isn't.
