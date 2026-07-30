# The development journey

*How one cold-outreach pipeline actually got built, from the first sentence typed
into a terminal to the last file written — including the hour spent discovering
that most of what it found was wrong.*

This is written for someone who has never done lead generation and finds the
whole thing faintly mysterious: a stack of tools with names like Clay and
Higgsfield, credits and enrichment routines and signals, and somewhere at the end
an email that is supposed to make a stranger reply. That was me before this
project. So this document explains not just what happened, but what each moving
part *is* and why it exists.

Everything below is a real run on 30 July 2026. All numbers are measured. All
practice and person names have been replaced with synthetic labels — `Practice A`,
`Contact Golf` — and that replacement is done by [`redact.py`](redact.py), which
refuses to finish if a real name survives.

---

## 1. The play, in plain language

Cold outreach has an obvious problem: a stranger emails you offering to build you
a website, and you delete it, because they are one of forty people who emailed
you that week and none of them knew anything about you.

The play this pipeline implements gets around that by leading with a **specific,
checkable fact about the recipient's own business**. Not "I noticed your website
could be improved" — that is the same nothing everyone else sends — but "the
version of your domain without the www doesn't load at all, because it points at
a reserved IP address that can't host anything." That is a sentence only someone
who actually looked could write. It is useful whether or not they hire you. And
it earns the right to the second paragraph, which is where the pitch lives.

So the whole machine exists to answer one question at scale: **which businesses
near me have a specific, demonstrable, fixable problem with their web presence,
and who at those businesses should hear about it?**

That decomposes into five jobs, and each tool in the stack does exactly one:

1. **Get a list of businesses of a particular type in a particular place.** (Clay)
2. **Measure each of their websites and score the problems.** (a Python script —
   no product does this for you)
3. **Prove each problem is real, in a browser.** (Chrome, by hand — this is where
   the project nearly went wrong)
4. **Find a named human at the qualified businesses and get their work email.** (Clay again)
5. **Have something impressive to show them when they reply.** (Higgsfield for the
   media, Fable 5 for the site, Vercel for the URL)

A beginner's instinct is that step 1 is the hard part, because that's the part
that sounds like a superpower. It isn't. Step 1 took about four minutes. **Step 3
took the longest and produced the entire value of this project**, and no tool in
the stack does it for you.

## 2. The stack, demystified

**Claude Code** is a coding agent that runs in a terminal with access to your
filesystem, your shell, and any external tools you have connected. Here it wasn't
"helping write code" — it ran the whole project: installed the CLIs, wrote the
scanner, drove the browser, wrote the emails. The model was Fable 5 / Opus 5.

**Higgsfield** is a generative media service — you give it a text prompt, it
returns images or short video clips. It is metered in *credits*. In this project
it produced the entire visual identity of the demo site: a hero video and three
photographs of people who do not exist. This matters more than it sounds, because
the alternative for a solo operator is stock photography that looks like stock
photography, and a website pitching "we make you look modern" cannot look
generic.

**Clay** is a B2B data platform. Two capabilities matter here, and they are
billed from **two separate pools**, which is the single most confusing thing about
it for a newcomer:

- **Search** answers "give me companies/people matching this description." It is
  metered in *search results* and on the free tier you get **50 results per search
  and 100 results per month**. This runs out fast.
- **Enrichment routines** answer "given this person at this company, what is their
  work email / their address / their job postings." Metered in *credits*, of which
  the free tier has thousands. This run used 3.4 of 2,005.

Blowing through your search quota while barely touching your credit balance is
the normal shape of a first day with Clay. It happened here: ~97 of 100 monthly
search results were consumed, while credits went from 2,005 to 2,002.

**Vercel** hosts static sites at a public URL in about thirty seconds. It exists
in this pipeline for one reason: a cold email needs a link the recipient can open
without logging into anything.

**Chrome**, driven through a browser extension, is the fact-checker. It is the
only tool in the stack that sees a website the way a customer does.

## 3. The original prompt

The project started with one sentence:

> *i want to replicate the entire workflow ending up with draft emails with clay.
> please tell me if you have enough info to do so*

The second half of that sentence is worth noticing, and is a habit worth copying.
Asking an agent to declare its gaps *before* it starts is much cheaper than
letting it guess and discovering forty minutes later that it assumed something
false. It came back with four questions, of which the load-bearing ones were:
what state is the Clay account in (answer: brand new, nothing installed), which
vertical (dentists, matching the source video), and whether to build the website
first or start prospecting first.

Website first was the right call, and not for technical reasons. The website *is*
the offer. Until it exists, the emails have nothing to link to, and an email with
a `[DEMO URL]` placeholder in it is not a deliverable.

## 4. The first wall: the tool didn't run at all

Clay ships a command-line tool. Installing it failed immediately:
`unsupported OS: MINGW64_NT-10.0-26200`.

Checking the actual release on GitHub explained why. The published binaries are
`clay-darwin-arm64`, `clay-darwin-x64`, `clay-linux-arm64`, `clay-linux-x64` —
and that is the whole list. **There is no Windows build.** The tutorial being
followed never hits this because it was recorded on a Mac.

The way through was WSL (Windows Subsystem for Linux) — a real Linux environment
running inside Windows. The Linux binary was downloaded on the Windows side
(WSL's own `curl` threw a TLS error), checksum-verified against Clay's published
`d92494a5…` before being made executable, and copied in. Sign-in uses a browser
OAuth flow that calls back to `127.0.0.1:32889` *inside* WSL, so the next check
was whether Windows could reach that port at all. It could — an HTTP 404 from
that address is the good outcome, because 404 means something is listening.

Two beginner-relevant lessons hide in this half hour. The first: **a tutorial's
tooling assumptions are invisible until they break**, and "works on the
presenter's machine" is doing a lot of load-bearing work in every tutorial you
will ever follow. The second: the OAuth screen had a greyed-out **Authorize**
button, which looked like a bug and was not — the workspace picker was below the
fold inside a scrollable modal. Granting an OAuth app access to a workspace was
also left as a human click on purpose. An agent should not be the one deciding to
hand a third party access to your data.

## 5. Higgsfield: making things that don't exist

With Clay authorised, the slow work went first. Generative video takes minutes,
so it was queued before anything else and the Clay setup continued while it
rendered — a small scheduling habit that saves real time.

Four jobs were submitted from the brief in the source video: a looping video of
tiny workers in blue polishing a giant tooth, a cutout of a woman in a blue
sweater laughing, and two friendly patient headshots, all on the same calm blue
so they read as one brand. The first attempt returned an HTTP 502 from
Higgsfield's endpoint — a retryable server-side error, not a bad prompt — and
succeeded on retry roughly a minute later. The three stills finished first; the
5-second video cost **7.5 credits** out of a 102-credit starter balance and
finished a few minutes later.

Then the unglamorous part that most write-ups skip. The raw assets totalled
**16.9 MB**. Compressed with ImageMagick to WebP, they came to **179 KB** —
about a 95× reduction with no visible quality loss at the sizes used. This is not
housekeeping. The entire sales pitch of this campaign is *your website is slow*.
Arriving on a demo site that takes six seconds to load would end the conversation
before it started.

What Higgsfield buys a solo operator is worth stating plainly: a coherent visual
identity, made to order, in minutes, for pennies. The traditional alternatives
are a photoshoot you cannot afford or stock images your prospect has seen on four
other dentists' websites.

## 6. Building the site, and looking at it

The demo site is **one HTML file**. Tailwind comes from a CDN, the font from
Google Fonts, and there is no build step, no framework, no `node_modules`. It
opens in a browser by double-clicking it. That is not a shortcut taken under time
pressure — for a static marketing page it is simply the correct amount of
machinery, and it means the artifact is still openable years from now.

The step that mattered was the one after writing it. The page was served locally
and **actually looked at** in Chrome, which immediately surfaced two real defects
that no amount of reading the source would have caught: the call-to-action
button's text wrapped out of its pill shape, and clicking a nav link scrolled the
target heading *underneath* the fixed navigation bar. Both were two-line fixes
(`shrink-0 whitespace-nowrap`, and `scroll-margin-top` on anchored sections).

This is the same lesson that is about to arrive in a much more expensive form:
**generated output that was never looked at is not finished work.**

## 7. Clay, properly: how you actually ask for a list

Clay's search takes a SQL-like query. The first attempt was the obvious one:

```sql
select from companies where industry = "Dentists" and city = "Austin" limit 50
```

It failed validation, and the reason is worth internalising. `city` is not a
top-level field on a company. A company has a *list* of locations, and you have
to reach inside it:

```sql
select from companies
where industry = "Dentists"
  and locations.any(city contains "Austin" and state_or_province = "Texas")
limit 50
```

`industry` is an enum with a fixed vocabulary — `"Dentists"` is a real value in
it — and getting that exact string right is the difference between 37 results and
zero. The general principle: **read the schema before writing the query.** Clay
ships its own 156 KB query reference through the CLI, which is what settled it.

That query returned **37 practices**, of which **35 had unique domains** (chains
appear once per location). Each record carries name, domain, industry, employee
band, revenue band, a LinkedIn URL and a marketing description.

Two things went wrong here that are pure operational experience:

**The plan limit is per-search *and* per-month.** Asking for `--limit 50` on a
free account returns a validation error, not a truncated list. Between the
company search and the later people search, ~97 of the month's 100 results were
gone by lunchtime. Plan your queries before you run them; the free tier is enough
for one careful city, not for browsing.

**Everything written to WSL's `/tmp` vanished.** The WSL virtual machine restarted
mid-session and took the first 20 paid search results with it. They had to be
re-fetched, out of a quota that does not refill. Since then every Clay output is
written straight to the Windows filesystem through `/mnt/c/...`. If a result cost
you quota, treat it as precious the moment it arrives.

## 8. The part no product does for you

Clay tells you a practice exists and gives you its domain. It does not tell you
whether that domain loads, how long it takes, whether it's on HTTPS, or whether
there's a way to book an appointment. Those are the actual sales signals, and
measuring them means fetching all 35 sites yourself.

That is [`pipeline/audit.py`](pipeline/audit.py) — about 170 lines of standard
library Python that fetches each domain, times it, and turns what it sees into
scored signals: unreachable (100 points), HTTP error page (80), no HTTPS (45),
near-empty homepage (40), slow first load over 3s (30), bare domain fails and
only `www` works (25), sluggish load over 1.5s (12), stale copyright year (10).
Sorted by score, that's your call list.

Read that file if you read nothing else in the repo, because **almost every line
in it is a scar**. Each guard is there because it caught a specific false
positive, and each carries a comment saying which. It did not start that way. It
started as a clean, obvious scanner that produced 20 prospects, and every one of
those comments was added over the following hour as the prospects fell over one
by one.

## 9. Verification: where the project earned its keep

The first clean run produced **20 prospects**. Two survived. Here is what
happened to the other eighteen — six distinct failure modes, all of which will
happen to you too.

**Anti-bot blocking read as "site broken."** `Practice D` returned a hard HTTP 403
on three consecutive requests, and rendered perfectly in real Chrome. The tell was
backwards from intuition: a plain `curl` user-agent got 200, while a *spoofed
Chrome* user-agent got 403. The site's firewall wasn't blocking bots in general —
it was blocking scripts pretending to be browsers, which is precisely what the
scanner was. Emailing that dentist "your site is down" would have been flatly
false. The fix: 401, 403 and 429 are now classified `INCONCLUSIVE` and can never
contribute to a score.

**The scanner causing the failures it reported.** Two practices came back
"unreachable" and "403" while running at 10 parallel workers. Hit serially, both
returned 200 in about 1.3 seconds. The scanner was rate-limiting itself and then
reporting the symptom as the prospect's fault. The fix was to drop to 3 workers
and add a 5-second cooldown before any re-check — re-checking immediately just
re-triggers the same block, so the confirmation pass was confirming its own
mistake.

**Python being stricter than every browser.** `Practice G` was reported
unreachable with `CERTIFICATE_VERIFY_FAILED`. Both `curl` and Chrome accept that
certificate chain and get a 200. Python's `ssl` module rejects incomplete chains
that real clients tolerate. The fix was to stop using Python's HTTP stack and
shell out to `curl`, on the principle that **the measurement should approximate
what the prospect's customer experiences**, not what your language's TLS
implementation prefers.

**Client-rendered pages looking empty.** `Practice F` was flagged "no online
booking link." The live page has a large "24/7 Online Scheduling" button —
injected by JavaScript, and genuinely absent from the HTML the server sends. The
same cause produced a phantom "not mobile friendly." Both checks now record
`needs_render_check` — a lead for a human to look at — and are excluded from the
score entirely. Doing this properly needs a headless browser; that is the
documented upgrade path if content signals ever start mattering.

**A benign TLS teardown read as a connection failure.** One practice produced
`curl` exit code 56 — "server closed abruptly, missing close_notify" — *alongside
a complete HTTP 200 response*. The scanner trusted the exit code over the status
code. It now trusts the HTTP status whenever one is present.

**The CRM's stored domain was simply wrong.** This is the most instructive one.
The scanner's number-one prospect, at a maximum 100 points, was `Practice C`:
"domain does not resolve." That was true. But it was the wrong domain. The
practice's actual website is a slightly different name — the stored one had an
extra word — and it loads in 0.85 seconds. What gave it away was Clay's own
enrichment coming back with a work email on the *live* domain, contradicting the
company record from the same platform. **A dead domain in a database does not
mean a dead business.** There is no automated fix for this; it lives in an
`OVERRIDES` map in the scanner with a note explaining why, so that re-runs stay
honest.

### The part that reaches back to the source material

The tutorial this project followed includes a sample email about one practice —
the same one that surfaced here independently as `Practice A`. That email says:
*"the bare domain times out, and the www version returns a 403 Forbidden… Anyone
finding you on Google right now is likely hitting a dead end."*

Half of that is true. The bare domain genuinely fails, and this run reproduced it
independently: it resolves to `192.0.2.1`, an address reserved by RFC 5737 for
documentation, which can never host anything. Chrome will not load it.

But the `www` 403 is the anti-bot artifact described above. In a real browser,
`www.` renders a working site with a Book Online button. Sending that email as
written tells a dentist their entire web presence is dead when nearly everyone
arriving via a normal link sees a working website — and the moment they check,
you have proven you didn't.

The narrow claim is real and worth sending. The broad one isn't. Only the narrow
one went in the draft. **Do not copy a tutorial's output verbatim. Reproduce its
findings.**

## 10. Finding a human

A company is not a recipient. Clay's people search, filtered to the two verified
practices, returned **10 named staff** with titles and tenures. Note that this
search deliberately returns **no email addresses** — that is a separate,
separately-billed step, and it is where the free-tier confusion described in
section 2 bites.

Getting emails means running an **enrichment routine**: a named function in your
Clay workspace that takes structured input and returns a field. The workspace had
18 available, listed in [`pipeline/routines.json`](pipeline/routines.json) —
Company Address, Company Job Openings, Company News, and the one that mattered,
**Work Email**. They run asynchronously in bulk: submit a JSONL file of
`{"id": ..., "inputs": {...}}` records, get a run ID back, poll until complete.
This one took about four minutes for nine people.

The yield is the number to remember. **Nine people submitted, two verified work
emails returned.** The rest came back as empty results — not errors, just no
verified address available. That is normal, and it is why a campaign needs a list
far longer than its target reply count. Total cost: 3.4 credits from a balance of
2,005.

One of those two emails is the one that exposed the wrong-domain problem in
section 9, which is a nice illustration of a general principle: **evidence from
one part of the pipeline is the best check on another part.**

## 11. The deliverable

[`pipeline/draft-emails.md`](pipeline/draft-emails.md) holds two drafts.

The first is complete and could be sent today. It tells `Practice A` that the
non-www version of their domain doesn't load, explains in one sentence why
(a reserved IP that cannot host a website), explains in one sentence why it
matters (people type domains without the www; so do directory listings and
printed materials), and says it is usually a five-minute DNS fix and offers the
details for free. Only *then*, in the last paragraph, does it mention that a
rebuild is a thing on offer, with a link to the demo.

The second is honest about being incomplete. `Practice B`'s site takes 4.4 to 8.0
seconds to deliver its first byte — measured three times serially, with connect
time under 0.36s throughout, which is what proves the delay is the server
generating the page rather than a slow connection or heavy images. That claim is
solid. But Clay's people search found nobody at that domain, so the draft has no
recipient and says so. **Shipping it with a blank `[NAME]` and a note is more
useful than pretending it's ready.**

Both drafts carry their evidence underneath them — the raw measurements, and how
they were taken. If a claim in an email can't survive being written down next to
its evidence, it shouldn't be in the email.

The file ends with a section called **"Not sent, and why"**, naming every prospect
that was dropped and the reason. In practice that is the most re-readable part of
the whole repository, because it is the part that stops you making the same
mistake next month.

## 12. Hosting, and a banner that is doing real work

A demo link in a cold email has to open for a stranger with no login. That ruled
out anything private and pointed at Vercel: `vercel deploy --prod --yes` from the
site folder, done in seconds, live at
**https://dental-demo-chi-rust.vercel.app**. It was then verified the way
deployments should be verified — not by trusting the CLI's success message, but by
fetching the URL and the 3 MB hero video from outside and confirming HTTP 200 with
no authentication wall, then opening it in a browser and looking at it.

Before it went public, one thing changed. The demo is branded "Brooklyn Smiles"
and carries an invented phone number, a street address and two patient
testimonials. On a private machine that's a mockup. On a public URL that a
prospect opens, it reads as a real clinic — implicitly, as *your client*. So the
page now carries an amber banner above the navigation: *"Design demo — 'Brooklyn
Smiles' is a fictional clinic. Contact details and reviews on this page are sample
content, not a real business."*

That banner is not just a legal fig leaf; it is better outreach. Without it, a
prospect who gets curious and searches for Brooklyn Smiles finds nothing and
quietly concludes you were bluffing. With it, the link is unambiguously a work
sample, and the awkward question never gets asked.

## 13. What it cost

| | Before | After | Used |
|---|---|---|---|
| Clay search results (monthly, free tier) | 100 | ~3 | **~97** |
| Clay enrichment credits | 2,005 | 2,002 | 3.4 |
| Higgsfield credits | 102 | ~94 | 7.5 (the 5s video) |
| Vercel | — | — | free tier |
| Wall-clock, end to end | | | ~50 minutes |

The asymmetry is the lesson. **Search quota is the scarce resource** and it is
consumed by exploration — by running the query again because the first one was
malformed, by re-fetching results a VM restart ate. Enrichment credits, the thing
that sounds expensive, were effectively free at this scale.

## 14. What a beginner should actually take away

**The list is not the hard part.** Getting 37 dental practices in Austin took one
query and about four minutes. Everything valuable happened afterwards.

**Your scanner will be wrong about other people's businesses, confidently.**
Twenty leads became two. Firewalls block you and it looks like an outage; your own
concurrency causes timeouts and it looks like their slow server; JavaScript-built
pages look empty to an HTML parser; a database's stored domain can simply be
stale. Every one of those, sent as-is, is an email telling a business owner
something false about their own company.

**Verify in a real browser.** Not a second script — a browser. It is the only
thing in the stack that sees what a customer sees, and it settled every single
one of the six failure modes above.

**Say the narrow true thing, not the broad impressive one.** "Your bare domain
points at a reserved IP and won't load" is checkable and correct. "Your site is
down" was neither.

**Write down what you rejected and why.** `VERIFICATION.md` took twenty minutes to
write and is the most valuable file here, because the failure modes repeat every
time you run this on a new city.

**Two good leads beat twenty bad ones.** A campaign of twenty emails, eighteen of
which contain a false claim about the recipient's business, does not produce 10%
of twenty replies. It produces a reputation.

## 15. What was not built

The source video covers five use cases. This project completed the first two —
the website and the Clay outreach — and stopped at draft emails, on purpose.
Claymation motion ads, an AI video editor, and a personal agent OS were not
attempted.

Also not built, deliberately: **any sending capability.** No mailbox is connected,
no sending domain is warmed, no campaign is configured. The pipeline ends with two
markdown drafts and a human decision, which is the correct place for it to end.
