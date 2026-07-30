# The lead selection rubric

How a business gets from "exists in a database" to "there is an email addressed to
them." Four layers. Only the first two are code; the last two are where most
prospects die, and where the judgment lives.

Everything here is what [`pipeline/audit.py`](pipeline/audit.py) actually does,
not an idealised description of it. Practice labels are the anonymised ones
described under [Redaction](README.md#redaction).

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

This layer is where the attrition happens: **18 of 20 flagged prospects died
here** in the first run, and 5 of 6 in a later one.

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
All dropped.

**4. Is it a defect, or a business model?**
A referral-based endodontic practice has no consumer booking widget because it
does not take consumer bookings. The scanner cannot tell the difference between
"missing feature" and "deliberately not that kind of business." A person can, and
must, before telling someone their website is incomplete.

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
