# The lead selection rubric

How a business gets from "exists in a database" to "there is an email addressed to
them." Four layers. Only the first two are code; the last two are where most
prospects die, and where the judgment lives.

Everything here is what [`pipeline/audit.py`](pipeline/audit.py) actually does,
not an idealised description of it. Practice labels are the anonymised ones
described under [Redaction](README.md#redaction).

It has been run twice, against two metropolitan areas, with the same scanner and
the same thresholds:

| Run | Area | Found | Flagged | Survived verification |
|---|---|---:|---:|---:|
| First — [`pipeline/`](pipeline/) | Austin, TX | 37 | 20 | 2 |
| Second — [`pipeline-mountain-view/`](pipeline-mountain-view/) | Mid-Peninsula, CA | 12 | 6 | 1 |

The second run is the more useful one for judging the rubric, because nothing was
tuned between them. Where the two disagree is noted below.

---

## Layer 1 — Who enters the funnel at all

The Clay search defines the universe:

```sql
select from companies
where industry = "Dentists"                        -- exact enum value
  and locations.any(city contains ("...") and state_or_province = "...")
```

Two details matter more than they look:

- **`industry` is a fixed enum.** `"Dentists"` is a real value in Clay's
  vocabulary. Get the string wrong and you get zero rows, not a fuzzy match.
- **`city` is not a top-level field.** It lives inside the `locations` tuple
  array, so it has to be reached through `locations.any(...)`. `contains` also
  accepts a parenthesised list — `city contains ("Palo Alto", "Los Altos")` — to
  cover several cities in a single search, which matters when your plan meters
  searches.

And one detail that only showed up on the second run:

- **The database may simply not cover your city.** The exact query above, with
  `city contains "Mountain View"`, returned **zero rows** with
  `exhaustionReason: no_more_results` — Clay saying "there are none", not "you hit
  a limit". Widening to four neighbouring cities returned 12 practices, none of
  them in Mountain View. Austin returned 37. A city being wealthy and dense is no
  guarantee its small businesses are in the dataset, and the run is named after a
  city that contributed nothing to it. Check coverage before committing to an
  area. Full detail in
  [`pipeline-mountain-view/VERIFICATION.md`](pipeline-mountain-view/VERIFICATION.md).

Then `audit.py` applies two more filters before anything is measured:

- **The company must have a domain.** Rows without one are dropped.
- **Duplicate domains are dropped.** A chain with five locations is one prospect,
  not five.

> **The most consequential line in the whole rubric is that first filter.** A
> business with no website at all cannot enter this funnel — it has no domain to
> drop. That is the single highest-intent signal in the framework this project
> replicates, and both runs so far have been structurally blind to it. See
> [What this rubric is missing](#what-this-rubric-is-missing).

## Layer 2 — The score

Every surviving domain is fetched and scored. Higher is a stronger prospect; the
call list is this table sorted descending.

| Points | Signal | The actual test |
|---:|---|---|
| **100** | Site unreachable | Both the bare domain *and* `www.` fail to fetch |
| **80** | HTTP error page | Status ≥ 400, excluding the blocked codes below |
| **45** | No HTTPS | Final URL after all redirects is still `http://` |
| **40** | Near-empty homepage | Response body under 2,000 bytes — parked or broken |
| **30** | Slow first load | Over 3.0 seconds |
| **25** | Bare domain fails | Only the `www.` form resolves |
| **12** | Sluggish first load | Between 1.5 and 3.0 seconds |
| **10** | Stale copyright year | A year in 1900–2015 near the word "copyright" |

### The two timing rows are the weakest in the table

**Slow first load** and **sluggish first load** are scored from a single timed
fetch taken during a parallel sweep, and they are where nearly every false
positive comes from. In the second run all three timing flags evaporated on
serial re-check:

| Scanner said | Serial reality, 3 runs |
|---|---|
| slow first load: 3.3s | 0.52 / 0.83 / 0.52s |
| sluggish first load: 2.1s | 0.57 / 0.54 / 0.54s |
| sluggish first load: 2.5s | 1.26 / 0.39 / 0.17s |

The first of those was the **top-ranked prospect of the entire run at 40 points**.
It answers in half a second. Sent unchecked, the email would have told an
endodontist their website was slow while it was not.

Note what this is not: it is not the 10-worker problem the first run diagnosed and
fixed. This was **3 workers against a 12-domain list** — a load so light it should
not have mattered, and it still produced a phantom top-ranked lead. Treat a timing
score as a reason to go and measure, never as a measurement. Layer 3 exists
almost entirely for these two rows.

### Deliberately worth zero

These are not oversights. Each one exists because it produced a false accusation
about a real business, documented in
[`pipeline/VERIFICATION.md`](pipeline/VERIFICATION.md).

| Observation | Classification | Why it scores nothing |
|---|---|---|
| HTTP **401 / 403 / 429** | `INCONCLUSIVE`, returns immediately | A firewall blocking a script is not a broken website. One practice served a hard 403 to a spoofed-Chrome user agent on three consecutive serial requests and rendered perfectly in a real browser. |
| **No viewport meta tag** | `needs_render_check` | Read from served HTML, so a client-rendered page looks broken when it isn't. |
| **No booking link** | `needs_render_check` | Same cause. One practice was flagged for this while shipping a prominent "24/7 Online Scheduling" button, injected by JavaScript. |
| Domain in the **`OVERRIDES` map** | Disqualified, score forced to 0 | A human checked it in a browser and the automated verdict was wrong. The entry carries the reason. |

`needs_render_check` items are recorded as **leads for a human to look at**, never
as facts, and never as score. Resolving them properly needs a headless browser —
that is the documented upgrade path if content signals start mattering.

## Layer 3 — The verification gate

Nothing from Layer 2 is treated as true.

**Automatic, in code.** Any signal containing `unreachable`, `error page`,
`HTTPS` or `bare domain` triggers a serial re-check after a **5-second cooldown**.
The cooldown is load-bearing: re-checking immediately just re-triggers the same
rate limiting that caused the phantom failure. Signals that fail to reproduce are
moved to an `unconfirmed` field and stop counting.

The scan itself runs at **3 workers, not 10**. Ten parallel requests tripped
prospects' firewalls and produced phantom 403s — the scanner reporting its own
rate limiting as the prospect's fault.

**By hand, before anything reaches a draft:**

1. **Three serial runs.** Never concurrent. If a signal only appears under
   parallel load, it is yours, not theirs.
2. **Time-to-first-byte compared against connect time.** This is what separates a
   slow server from a slow network. A confirmed slow prospect showed TTFB of
   4.40 / 6.47 / 7.83s with connect time under 0.36s throughout — the server is
   generating the page slowly, and that claim is safe to put in writing.
3. **A real Chrome window** for anything visual, blocked, or client-rendered. It
   is the only tool in the stack that sees what a customer sees, and it settled
   every disputed signal in both runs.

Steps 1 and 2 are now a script — [`verify.py`](verify.py) — which does the three
serial fetches and writes curl's own output to `verification-raw.txt`, carried
into the published copy by `redact.py` with the domains aliased and the timings
untouched. It exists because of an honest gap: both runs published conclusions
like "TTFB 5.40 / 5.30 / 8.48s" with no way for a reader to see the output behind
them. Anything measured from here on ships with its receipts. The Austin and
mid-Peninsula numbers predate it and remain summaries.

The script makes exactly one judgement, and refuses the email in three of its
four outcomes: `NOT SLOW` if any run came back under 1.5s, `NETWORK, NOT SERVER`
if connect time was also high, `INCONCLUSIVE` if a fetch reported nothing, and
`SERVER-SIDE SLOW` only when time-to-first-byte stayed high across all three runs
while connect stayed low.

This layer is where the attrition happens: **18 of 20 flagged prospects died
here** in the first run, and **5 of 6** in the second. Two runs, two cities, and
the scanner has yet to be right more than about a tenth of the time. That ratio is
the argument for the whole layer.

## Layer 4 — Is it emailable?

A signal can be real, reproducible, and still not belong in an email. Four
questions, no code:

**1. Is the claim narrow?**
"The bare domain points at a reserved IP and won't load" ships. "Your site is
down" does not — the `www.` form works fine for almost everyone. This is the
exact correction this project made to the source video's sample email.

**2. Would it survive being written next to its evidence?**
Every draft carries its raw measurements directly underneath it. If a claim looks
thin sitting next to its own numbers, it does not go out.

**3. Is it a business problem, or merely true?**
A stale copyright year is real, reproducible, and does not matter. Around fifteen
practices in the first run and two in the second were flagged for nothing else.
All dropped, both times, without exception.

**4. Is it a defect, or a business model?**
A referral-based endodontic practice has no consumer booking widget because it
does not take consumer bookings. The scanner cannot tell the difference between
"missing feature" and "deliberately not that kind of business." A person can, and
must, before telling someone their website is incomplete. This is a live example,
not a hypothetical: it is the one prospect the second run did email, and the
booking flag was cut from the draft while the timing claim stayed —
see [`pipeline-mountain-view/draft-emails.md`](pipeline-mountain-view/draft-emails.md).

Finally, a prospect needs a **legitimate recipient**: a named human plus an
address that was either returned by verified enrichment or published by the
business itself. A guessed mailbox pattern is not a contact. A draft with no
recipient ships as a draft with no recipient, and says so.

## What this rubric is missing

The framework this project replicates lists signals that are not implemented
here, all of them higher-intent than anything in the Layer 2 table:

- **No website at all.** Excluded by construction at Layer 1. This is the gap.
- **Strong Google reviews paired with a weak site** — high trust, poor conversion,
  which is the most persuasive pitch available.
- **A recent move**, leaving stale addresses across the web.
- **Broken booking or contact forms**, as opposed to merely absent ones.

A practice with 4.8 stars and no website is a better lead than one whose homepage
takes 3.1 seconds. Effort is better spent adding those signals than tuning the
point values above.
