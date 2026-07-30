# Draft outreach — Mountain View area (mid-Peninsula, CA)

**Status: draft only. Nothing has been sent, and no sending is set up.**

One draft, from 12 practices searched and 6 flagged. Every claim below was
reproduced by hand — three serial curl runs and a real Chrome window — not taken
from the scanner. See `VERIFICATION.md` for the five that didn't survive.

Replace `[YOUR NAME]` and `[YOUR EMAIL]` before sending.

Demo link, live and public: **https://dental-demo-chi-rust.vercel.app**
(carries a banner stating Brooklyn Smiles is a fictional clinic).

---

## 1. Practice MV-H — Palo Alto, CA

- **To:** `info@practice-mv-h-alias.example` — the general inbox **published on their own
  website header**. Clay's Work Email enrichment on the owner returned no
  address, so this is not an enriched or guessed mailbox.
- **Owner:** Dr. Contact Lima, Diplomate of the American Board of
  Endodontics (Clay people search, corroborated by the site's own page title).
  Address him by name; send to the general inbox.
- **Signals:** both verified 2026-07-30 — serial timing, and a real browser.

> **Subject:** practice-mv-h-alias.example is taking 11–15 seconds to open
>
> Hi Dr. Lima,
>
> I was looking at endodontic practices on the Peninsula and found something on
> your site worth flagging, whether or not we ever speak.
>
> The address on your own contact details — practice-mv-h-alias.example — redirects to
> practice-mv-h.example, and that hop is slow. I timed it twice and got 15.2
> and 11.0 seconds before the page began to appear. Going to the long domain
> directly is faster but still slow: 5.4, 5.3 and 8.5 seconds across three tries,
> measured one at a time so nothing on my end was throttling it.
>
> That matters most for the short domain, because that's the one on your email
> signature, so it's the one a referring dentist is most likely to type. The delay
> is your server generating the page — the connection itself was consistently
> under 0.2 seconds — which usually points at hosting or an unoptimised CMS rather
> than anything you did.
>
> One other thing while I'm here: "Important Covid-19 Updates" is still the first
> item in your top navigation. It's a small thing, but it's the first impression a
> new referrer gets, and it reads as though the site hasn't been touched in a
> while.
>
> Both are fixable without a rebuild, and I'm happy to send your web person the
> exact numbers, no strings. If a refresh is on the table anyway, I build fast
> dental sites with online booking and referral forms — here's a live demo:
> https://dental-demo-chi-rust.vercel.app. Would a 15-minute call be useful?
>
> — [YOUR NAME]
> [YOUR EMAIL]

**Why this one is real.** Three serial requests to the main domain gave
time-to-first-byte of 5.40s, 5.30s and 8.48s, with connect time between 0.136s
and 0.193s throughout — so the delay is server-side page generation, not the
network. Two requests to `practice-mv-h-alias.example`, which 301s to the main site, gave
15.15s and 10.97s. The Covid banner was seen in Chrome and confirmed in the
served HTML (`covid-19-updates/`, link title "Important Covid-19 Updates").

**What was deliberately left out.** The scanner also flagged "no booking link".
That's wrong for this business — it's a referral-based endodontic practice with a
Referral Form and Patient Login in the header. Saying "you have no way to book"
would have been the kind of false claim that ends a conversation.

---

## Not sent, and why

**Practice MV-L** (`practice-mv-l.example`) — the scanner's **top-ranked
prospect at 40 points**, "slow first load: 3.3s". Hit serially it answers in
0.52–0.83s. The 3.3s was my own parallel sweep. Not a prospect.

**Practice MV-E** and **Practice MV-B** — same story at 2.1s
and 2.5s; 0.54s and 0.17–1.26s serially. Not prospects.

**Practice MV-D** and **Practice MV-K** — flagged only for a
stale copyright year. Too weak to build an email on.

**Practice MV-F** — HTTP 403 to an automated request. Recorded as
inconclusive, not a defect. Needs a human with a browser before anyone claims
anything about it.

**And the target city itself** — Clay has no dental practices tagged in Mountain
View, CA. This list is Palo Alto, Los Altos, Sunnyvale and Santa Clara.
