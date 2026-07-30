"""Generate the public, redacted copy of the pipeline artifacts.

Reads the untouched originals in dental-demo/ and writes anonymised twins into
pipeline/. The originals are never modified, never renamed, and never committed
(see .gitignore) -- this script is the only thing standing between the two.

Every real practice becomes "Practice A".."Practice AK" on a practice-*.example
domain, and every real person becomes "Contact <NATO word>". Both alias schemes
are deliberately synthetic: a plausible-sounding fake name could collide with
a real business, and .example is reserved by RFC 2606 so the domains can never
resolve to anyone.

Run:  python redact.py                    (dental-demo/ -> pipeline/)
      python redact.py SRC OUT            (mountain-view/ -> pipeline-mountain-view/)

Whichever run is being redacted, the alias map is built from *all* of them, so a
letter identifies one practice across the whole repository and an identifier that
leaks from one run's files into another's is still caught.

ponytail: string substitution over the finished files, not a re-run of the
pipeline against anonymised inputs. Upgrade only if a signal ever needs the real
domain to be re-derived, which would defeat the point.
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else "dental-demo")
OUT = os.path.join(HERE, sys.argv[2] if len(sys.argv) > 2 else "pipeline")

# Files copied through the redactor, if present -- no one run produces all of
# them. Everything else in a source directory (index.html, assets/, vercel.json,
# empty .err files) carries no prospect data and is committed as-is or not at all.
TEXT_FILES = ["audit.py", "VERIFICATION.md", "draft-emails.md", "prospects.csv",
              "audit_results.json", "prospects_raw.json", "people_raw.json",
              "email_in.jsonl", "email_in2.jsonl",
              "email_results.jsonl", "email_results2.jsonl", "routines.json",
              "search.json", "search2.json", "people_search.json",
              # Raw curl output from verify.py. Domains get aliased like
              # everywhere else; the timings are the evidence and stay verbatim.
              "verification-raw.txt"]

# Story-critical entities get stable letters so the write-ups can refer to
# "Practice A" and mean the same practice every time. The mapping itself is an
# identifier, so it lives in a gitignored file rather than in this source.
# Without that file the labels are assigned purely in file order and the output
# is still fully anonymous - only the letters move.
KEYS = os.path.join(HERE, "redaction-keys.json")
_keys = json.load(io.open(KEYS, encoding="utf-8")) if os.path.exists(KEYS) else {}
PINNED = _keys.get("pinned", {})
# Domains that appear in the write-ups but not in the search results, e.g. a
# practice's real site discovered through its own work-email domain.
EXTRA_DOMAINS = _keys.get("extra", {})
# Name spellings the prose uses that the data platform does not: a write-up says
# "Ann Lee, PhD DDS" where the record says "ANN LEE, PHD, DDS". The real pairs
# live in the keys file, because a worked example here would be the identifier.
# The token self-check below is what finds these; this is where they get fixed.
NAME_OVERRIDES = _keys.get("names", {})

# The only hosts allowed to survive in the output: ours, and deliberately so.
PUBLIC_HOSTS = {"dental-demo-chi-rust.vercel.app"}

NATO = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf",
        "Hotel", "India", "Juliett", "Kilo", "Lima", "Mike", "November"]


def letters():
    """A, B, ... Z, AA, AB, ... - enough labels for any list size."""
    from string import ascii_uppercase as U
    for c in U:
        yield c
    for a in U:
        for b in U:
            yield a + b


def build_map():
    """Return (replacements, checks) - what to substitute, and what must vanish.

    Built from *every* run on this machine, not just the one being redacted. The
    runs share files: audit.py was carried from the first city to the second and
    still names practices from the first in its comments, and only a map that
    spans both catches that.
    """
    companies, people = [], []
    for run in sorted(os.listdir(HERE)):
        raw = os.path.join(HERE, run, "prospects_raw.json")
        if not os.path.exists(raw):
            continue
        rows = json.load(io.open(raw, encoding="utf-8"))["data"]
        # This script's own output looks exactly like an input. Feeding it back
        # would hand fresh letters to already-aliased practices.
        if any((r.get("domain") or "").endswith(".example") for r in rows):
            continue
        companies += rows
        ppl = os.path.join(HERE, run, "people_raw.json")
        if os.path.exists(ppl):
            doc = json.load(io.open(ppl, encoding="utf-8"))
            people += doc["data"] if isinstance(doc, dict) else doc

    # --- domains -> practice-x.example -------------------------------------
    seen, order = set(), []
    for r in companies:
        d = r.get("domain")
        if d and d not in seen:
            seen.add(d)
            order.append(d)
    for d in EXTRA_DOMAINS:
        if d not in seen:
            seen.add(d)
            order.append(d)

    gen = letters()
    used = set(PINNED.values()) | set(EXTRA_DOMAINS.values())
    dom_alias = {}
    for d in order:
        if d in PINNED:
            tag = PINNED[d]
        elif d in EXTRA_DOMAINS:
            tag = EXTRA_DOMAINS[d]
        else:
            tag = next(gen)
            while tag in used:
                tag = next(gen)
            used.add(tag)
        dom_alias[d] = tag

    # --- company display names -> "Practice X" -----------------------------
    # A data platform stores the legal name in caps with a corporate suffix while
    # the drafts use the readable form. Match every variant, or a redacted file
    # keeps the version a search engine would find.
    name_alias = {}
    for r in companies:
        d, n = r.get("domain"), r.get("name")
        if not (d and n):
            continue
        alias = f"Practice {dom_alias[d]}"
        base = re.sub(r",?\s+(P\.?C\.?|P\.?A\.?|PLLC|LLC|Inc\.?)$", "", n, flags=re.I)
        for v in {n, base, n.title(), base.title()}:
            name_alias.setdefault(v, alias)

    # --- people -> "Contact <NATO>" ----------------------------------------
    person_alias, i = {}, 0
    for p in people:
        n = p.get("name")
        if n and n not in person_alias:
            # Past the end of the alphabet, count round again rather than wrap -
            # two real people sharing one alias would silently merge them.
            lap = "" if i < len(NATO) else str(i // len(NATO) + 1)
            person_alias[n] = f"Contact {NATO[i % len(NATO)]}{lap}"
            i += 1

    rep = {}
    for d, tag in dom_alias.items():
        rep[d] = f"practice-{tag.lower()}.example"
    rep.update(name_alias)
    for variant, canonical in NAME_OVERRIDES.items():
        # Keyed by the spelling the record uses, so one entry survives a rerun
        # that reshuffles the letters.
        if canonical in name_alias:
            rep[variant] = name_alias[canonical]

    # Last names appear alone ("Dr. <surname>," in an email greeting) and buried
    # inside routine-run ids. Both need the same alias or the drafts stop making
    # sense to a reader.
    for real, alias in person_alias.items():
        surname, given = real.split()[-1], real.split()[0]
        word = alias.split()[-1]
        rep[real] = alias
        rep[given] = "Contact"
        # Every part of a name is an identifier on its own: a double-barrelled
        # surname shows up halved inside a routine-run id.
        for tok in re.findall(r"[A-Za-z]{3,}", surname):
            rep[tok] = word
        # Enrichment returns initial+surname mailboxes, where the surname sits
        # mid-token and no word-boundary rule can reach it.
        rep[(given[0] + surname.split("-")[0]).lower()] = word.lower()

    # Enriched work emails need no rule of their own: firstname.lastname@domain
    # is covered by the given-name, surname and domain substitutions above.
    checks = list(dom_alias) + list(name_alias) + list(person_alias)
    for real in person_alias:           # a lone name part is still an identifier
        checks += re.findall(r"[A-Za-z]{3,}", real)
    # A practice's surname-shaped token is an identifier even where the practice
    # is only half-named: a lone surname still points at the practice domain
    # built from it.
    checks += list(NAME_OVERRIDES)
    return rep, sorted(set(checks))


def redact(text, rep):
    """Substitute longest keys first so 'x-center.com' never loses to 'x.com'.

    Everything is case-insensitive: a first name that appears title-cased in a
    people record turns up lowercased inside a work-email address.
    """
    for key in sorted(rep, key=len, reverse=True):
        # A short surname must not eat the middle of an unrelated English word.
        bound = r"\b" if re.fullmatch(r"[A-Za-z][A-Za-z'-]*", key) else ""
        text = re.sub(bound + re.escape(key) + bound, rep[key], text,
                      flags=re.IGNORECASE)
    # A LinkedIn slug spells the practice out in full, and prospects.csv carries
    # one per row - the alias map never sees it because it isn't the domain.
    text = re.sub(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w%-]+",
                  "[linkedin url redacted]", text, flags=re.IGNORECASE)
    # Clay routine ids are scoped to one workspace and identify it. The catalogue
    # of routine *names* is the useful part for a reader, so keep those.
    text = re.sub(r"(function|workflow):t_[A-Za-z0-9]+",
                  lambda m: m.group(1) + ":t_REDACTED", text)
    # Same for saved-search ids, which are handles onto one workspace's results.
    text = re.sub(r"search_[A-Za-z0-9]+", "search_REDACTED", text)
    # Tidy the mailboxes the substitutions leave mixed-case.
    return re.sub(r"[\w.+-]+(?=@practice-[\w-]+\.example)",
                  lambda m: m.group(0).lower(), text)


def scrub_json(text, name):
    """Field-level rules the string pass can't express."""
    doc = json.loads(text)
    rows = doc["data"] if isinstance(doc, dict) and "data" in doc else doc
    if isinstance(rows, list):
        for r in rows:
            if not isinstance(r, dict):
                continue
            # A prospect's own marketing blurb is searchable verbatim, so the
            # alias would not hide them. Clay's routine descriptions are product
            # documentation and stay - they are the useful part of that file.
            if "description" in r and name.startswith("prospects_raw"):
                r["description"] = "[redacted marketing description]"
            for k in ("linkedin_url", "clay_company_id", "clay_profile_id",
                      "createdBy"):
                if k in r:
                    r[k] = None
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def main():
    rep, checks = build_map()
    # ponytail: empty the directory rather than rmtree it - Windows refuses to
    # remove a directory any shell is sitting in, and the files are the point.
    os.makedirs(OUT, exist_ok=True)
    for stale in os.listdir(OUT):
        os.unlink(os.path.join(OUT, stale))

    for name in TEXT_FILES:
        if not os.path.exists(f"{SRC}/{name}"):
            continue
        raw = io.open(f"{SRC}/{name}", encoding="utf-8").read()
        out = redact(raw, rep)
        if name.endswith(".json"):
            out = redact(scrub_json(out, name), rep)
        io.open(f"{OUT}/{name}", "w", encoding="utf-8", newline="\n").write(out)
        print(f"  {name:<22} {len(raw):>7} -> {len(out):>7} bytes")

    # Self-check: no real identifier may survive anywhere in the output.
    # This is the whole safety guarantee, so it fails loudly rather than warns.
    leaked = []
    for name in sorted(os.listdir(OUT)):
        body = io.open(f"{OUT}/{name}", encoding="utf-8").read()
        for term in checks:
            bound = r"\b" if re.fullmatch(r"[A-Za-z][A-Za-z'-]*", term) else ""
            if re.search(bound + re.escape(term) + bound, body, re.IGNORECASE):
                leaked.append((name, term))
        for addr in re.findall(r"[\w.+-]+@[\w.-]+\.\w+", body):
            if not addr.endswith(".example"):
                leaked.append((name, addr))
        # A practice's own site is not the only domain it owns. Three Austin
        # practices redirect to a second domain that never appears in the
        # `domain` field, so no alias covered it and it published intact. Trust
        # nothing that is not either a .example alias or knowingly public.
        for host in re.findall(r"https?://([\w.-]+)", body):
            host = re.sub(r"^www\.", "", host).rstrip(".")
            if host and not host.endswith(".example") and host not in PUBLIC_HOSTS:
                leaked.append((name, host))
        for url in re.findall(r"linkedin\.com/\S+", body):
            leaked.append((name, url))
    if leaked:
        for n, t in leaked:
            print(f"LEAK  {n}: {t}", file=sys.stderr)
        sys.exit(f"\n{len(leaked)} real identifier(s) survived redaction - not safe to commit")
    print(f"\nOK - {len(checks)} real identifiers checked, "
          f"none present in {os.path.basename(OUT)}/")


if __name__ == "__main__":
    main()
