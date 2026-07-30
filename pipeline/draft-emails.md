# Draft outreach — Austin dentists

**Status: drafts only. Nothing has been sent, and no sending is set up.**

Every factual claim below was reproduced by hand (real Chrome or serial curl),
not just taken from the scanner. Claims the scanner made that did **not** survive
verification were dropped — see `VERIFICATION.md`.

Replace `[YOUR NAME]` and `[YOUR EMAIL]` before sending.

The demo link is live and public: **https://dental-demo-chi-rust.vercel.app**
It carries a banner stating Brooklyn Smiles is a fictional clinic, so a prospect
reads it as a design sample rather than a real practice you're claiming as a client.

---

## 1. Practice A — Austin, TX

**To:** contact.golf@practice-a.example (Contact Golf, General Dentist)
**Source:** Clay people search + Clay "Work Email" routine (verified provider result)
**Signal:** verified in Chrome and by DNS lookup on 2026-07-30

> **Subject:** practice-a.example (without the www) doesn't load — quick heads up
>
> Hi Dr. Golf,
>
> I was looking at Austin dental practices this week and hit something on your site
> worth flagging, whether or not we ever speak.
>
> `www.practice-a.example` works fine. But the bare `practice-a.example` — no www —
> doesn't load at all. It currently points at 192.0.2.1, which is a reserved address
> that can't host a website, so the request just hangs until the browser gives up.
> I checked in Chrome and it never resolves.
>
> That matters because most people type a domain without the www, and plenty of
> directory listings and printed materials drop it too. Anyone who does that right
> now sees a blank error page.
>
> It's usually a five-minute DNS fix — one A record or a redirect from the bare
> domain to the www version. Happy to send your host the exact details, no strings.
>
> If a refresh is on the table anyway, I build fast dental sites with online booking
> and can share a live demo: https://dental-demo-chi-rust.vercel.app. Either way, I'd fix the DNS first.
>
> — [YOUR NAME]
> [YOUR EMAIL]

**Why this one is real:** `nslookup practice-a.example` returns `192.0.2.1`
(TEST-NET-1, reserved by RFC 5737 for documentation — it can never serve traffic).
Chrome failed to load it; the tab stayed on the previous page. `www` returns a
normal, decent-looking site.

---

## 2. Practice B — Austin, TX

**To:** no contact found — Clay's people search returned nobody at practice-b.example.
Needs a manual look (practice site staff page or LinkedIn) before this can go out.
**Signal:** verified by serial timing, 3 consecutive runs

> **Subject:** practice-b.example is taking 4–8 seconds to load
>
> Hi [NAME],
>
> Quick note from looking at Austin endodontic practices: practice-b.example is slow to
> respond. I timed it three times from a normal connection and got 4.5s, 6.6s and 8.0s
> before the first byte of the page arrived — the delay is server-side, not images or
> connection setup.
>
> For context, Google treats anything past ~2.5s as a poor experience, and referring
> dentists checking you out on a phone are the ones most likely to bounce.
>
> That pattern usually points at slow hosting or an unoptimised CMS rather than
> anything you did. Worth asking your host about, and it's often fixable without a
> rebuild.
>
> If you'd rather start fresh, I build fast dental sites with online booking —
> here's a live demo: https://dental-demo-chi-rust.vercel.app. Would a 15-minute call be useful?
>
> — [YOUR NAME]
> [YOUR EMAIL]

**Why this one is real:** three serial requests (no concurrency, so no rate limiting)
gave TTFB of 4.40s, 6.47s and 7.83s. Connect time stayed under 0.36s throughout, so
the delay is the server generating the page.

---

## Not sent, and why

**Practice C** — the scanner ranked this the #1 prospect
("domain does not resolve"). It's wrong. Clay's stored domain
`practice-c.example` is dead, but the practice's actual site is
`practice-c-live.example`, which loads in 0.85s. The Clay-enriched work email
`alpha@practice-c-live.example` gave it away. Telling this practice their site was
down would have been embarrassing and false.

**Practice D, Practice E, Practice G, Daylight Dental** —
all flagged by the scanner as broken or unfit; all confirmed working in a real
browser. Their "faults" were anti-bot blocking and client-side rendering, not defects.

**The ~15 practices flagged only for "copyright year looks stale"** — too weak to
build an email on. A stale footer year is not a business problem.
