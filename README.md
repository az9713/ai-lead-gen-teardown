# A cold-outreach lead-gen pipeline, start to finish — including everything that went wrong

This repository is a complete, honest record of one real run of an AI-assisted
lead generation pipeline: build a demo website with AI-generated media, use a
B2B data platform to find local businesses whose own websites have problems,
verify those problems by hand, and write cold emails that lead with the problem
rather than the pitch.

It was run on 30 July 2026 against dental practices in Austin, Texas, following
the workflow demonstrated in [this video by Samin
Yasar](https://www.youtube.com/watch?v=1ofs469cmDE). Everything was built by
Claude Code (Fable 5 / Opus 5) driving the tools listed below.

**The headline result is the failure rate, not the success rate.** The automated
scanner produced 20 prospects. After checking every claim by hand, **2 survived**
and 18 were artifacts of my own tooling — my scanner being wrong about other
people's businesses. If you take one thing from this repo, take
[`pipeline/VERIFICATION.md`](pipeline/VERIFICATION.md).

**Nothing was ever sent.** The two emails are drafts. No mailbox, no sending
domain, no campaign was configured at any point.

---

## Start here

| If you want… | Read |
|---|---|
| The whole story, written for someone new to lead gen | **[`JOURNEY.md`](JOURNEY.md)** |
| The finished deliverable — the two cold emails | [`pipeline/draft-emails.md`](pipeline/draft-emails.md) |
| The most useful file here — why 18 of 20 leads were fake | [`pipeline/VERIFICATION.md`](pipeline/VERIFICATION.md) |
| The scanner, with a comment on every guard and why it exists | [`pipeline/audit.py`](pipeline/audit.py) |
| The demo website that acts as the sales asset | [`dental-demo/index.html`](dental-demo/index.html) — live at **https://dental-demo-chi-rust.vercel.app** |

## What's in here

```
dental-demo/          The sales asset: a single-file demo dental clinic site
  index.html            Tailwind via CDN, Inter, no build step, one file
  assets/               AI-generated: a 5s looping video + 3 stills (179 KB total)
  vercel.json           The entire deploy config

pipeline/             The lead-gen run, anonymised (see "Redaction" below)
  prospects_raw.json    What the B2B search returned: 37 practices
  audit.py              The site scanner that turns domains into signals
  audit_results.json    Its raw output over 35 unique domains
  prospects.csv         The scored, human-readable prospect list
  people_raw.json       Decision-makers found at the qualified practices
  routines.json         The enrichment routines available in the workspace
  email_in*.jsonl       Work-email enrichment requests
  email_results*.jsonl  …and what came back (2 hits from 9 people)
  VERIFICATION.md       Every signal checked by hand, and the 6 ways it lied
  draft-emails.md       The deliverable: 2 drafts, plus "not sent, and why"

redact.py             Generates pipeline/ from the private originals
JOURNEY.md            The full write-up: every phase, every wrong turn
```

## The tools, and what each one actually did

- **Claude Code (Fable 5 / Opus 5)** — the agent that ran everything. Wrote the
  site, wrote the scanner, drove the other tools, and did the verification.
- **[Higgsfield](https://higgsfield.ai)** — AI image and video generation. Made
  the hero video and three photographs for the demo site. Cost: 7.5 credits for
  the 5-second video, on a 102-credit starter plan.
- **[Clay](https://www.clay.com)** — B2B data. Supplied the company list, the
  people at those companies, and the verified work emails. Free tier: 50 results
  per search, 100 searches per month.
- **Vercel** — hosting for the demo site, so the cold email can contain a link a
  stranger can open.
- **Chrome (via the Claude in Chrome extension)** — the verification layer. This
  turned out to be the single most important tool in the stack, because it is
  the only one that sees what a customer sees.
- **WSL Ubuntu** — because Clay ships no Windows binary. See `JOURNEY.md`.

## Redaction

The pipeline was run against **real dental practices and real named people**.
Publishing that would mean putting scraped contact data and unflattering
judgments about identifiable small businesses on the open web, so:

- Every practice appears as `Practice A`…`Practice AK` on a `practice-*.example`
  domain. `.example` is reserved by RFC 2606 and can never resolve to anyone.
- Every person appears as `Contact Alpha`, `Contact Bravo`, and so on.
- Aliases are deliberately synthetic rather than realistic-sounding, because a
  plausible fake name can collide with a real business somewhere.
- Marketing descriptions, LinkedIn URLs, platform record IDs and workspace-scoped
  routine IDs are stripped.

`redact.py` does this and then **fails loudly** if any of the 127 real
identifiers survives anywhere in `pipeline/`. The unredacted originals stay on
the machine that produced them and are excluded by `.gitignore`, as is
`redaction-keys.json` — the alias mapping is itself an identifier, so it is not
published either. Without that file the script still runs and still anonymises
everything; only which practice gets which letter changes.

One thing redaction does not hide: the run targeted dentists in Austin, Texas,
and the measurements are real. Someone determined enough could re-run a similar
search and guess at the mapping. The city is kept because it is already public —
it is the demo city from the source video — and because the method is
uninterpretable without it.

## Reproducing this

```bash
python redact.py            # regenerate pipeline/ from the originals + self-check
cd dental-demo && python -m http.server 8899    # preview the demo site
cd dental-demo && vercel deploy --prod --yes    # redeploy it
```

`pipeline/audit.py` expects a `prospects_raw.json` next to it in the same shape
Clay returns, and needs `curl` on the PATH. Nothing else has dependencies.

## Two things worth knowing before you copy this

**The demo site carries a banner saying the clinic is fictional, and it stays.**
"Brooklyn Smiles" has an invented phone number, address and testimonials. On a
public URL that a prospect opens from a cold email, without the banner it reads
as a client you are claiming. With it, it reads as a work sample. Keep it.

**Do not put an unverified signal in an outreach email.** This is the whole
lesson of this repository. An automated scan telling a business owner their site
is broken, when it works fine and your scraper was simply being blocked, is
worse than not emailing at all.
