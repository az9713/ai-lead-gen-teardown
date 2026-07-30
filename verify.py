"""Re-check a scanner signal by hand, and keep the receipts.

Layer 3 of RUBRIC.md, as a script. The scanner measures a domain once, under
parallel load, and is wrong about it most of the time. This fetches the same
domain three times, one at a time, and writes what curl actually reported into
`verification-raw.txt` next to the run's data.

That file is the point. Both runs so far published their conclusions -- "TTFB
5.40 / 5.30 / 8.48s, connect 0.14-0.19s" -- with no way for a reader to see the
output those numbers came from. A claim about someone else's business should
come with its evidence attached.

Run:  python verify.py mountain-view practice.example other.example
      python verify.py --self-check          (no network, proves the parser)

The raw file lands in a gitignored run directory and is carried into the public
copy by redact.py, which rewrites the domains and leaves the timings alone.

ponytail: shells out to curl rather than measuring in Python. curl is already a
hard dependency of audit.py, and its timing fields are the thing being quoted.
Re-deriving them from urllib would be a different measurement wearing the same
name.
"""
import os, subprocess, sys, time

RUNS = 3          # three serial fetches - the rubric's rule, not a tunable
COOLDOWN = 5      # seconds between fetches; back-to-back requests re-trigger
                  # the same rate limiting that produces phantom slow readings
TIMEOUT = 30

# Asking curl for the fields that separate a slow server from a slow network.
FMT = ("http_code=%{http_code} namelookup=%{time_namelookup} "
       "connect=%{time_connect} appconnect=%{time_appconnect} "
       "starttransfer=%{time_starttransfer} total=%{time_total} "
       "size=%{size_download} url=%{url_effective}")


def probe(domain):
    """One serial fetch. Returns curl's own line, verbatim and unparsed."""
    r = subprocess.run(
        ["curl", "-sS", "-o", os.devnull, "-L", "--max-time", str(TIMEOUT),
         "-w", FMT, f"https://{domain}"],
        capture_output=True, text=True)
    # A failed fetch is evidence too - record the error rather than dropping it.
    return r.stdout.strip() or f"curl_error={r.stderr.strip()}"


def parse(line):
    """curl's -w line -> dict. Values stay strings except the ones we compare."""
    # An error message is free text with spaces in it, so it cannot go through
    # the key=value split - it would come back as "could" and lose the rest.
    if line.startswith("curl_error="):
        return {"curl_error": line[len("curl_error="):]}
    out = {}
    for pair in line.split():
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[k] = v
    return out


def verdict(rows):
    """The only judgement this script makes, and it is deliberately narrow.

    Server-side slowness means time-to-first-byte stayed high while connect
    stayed low across every run. One slow reading out of three is the parallel
    sweep's own noise, which is the failure this whole script exists to catch.
    """
    ttfb, conn = [], []
    for r in rows:
        try:
            ttfb.append(float(r["starttransfer"]))
            conn.append(float(r["connect"]))
        except (KeyError, ValueError):
            return "INCONCLUSIVE - a fetch did not report timings"
    if min(ttfb) < 1.5:
        return f"NOT SLOW - fastest run {min(ttfb):.2f}s; do not email about speed"
    if max(conn) > 1.0:
        return f"NETWORK, NOT SERVER - connect up to {max(conn):.2f}s; not their fault"
    return (f"SERVER-SIDE SLOW - TTFB {min(ttfb):.2f}-{max(ttfb):.2f}s with "
            f"connect under {max(conn):.2f}s; safe to put in writing")


def check(domains, out_path):
    lines = [f"# serial re-check, {RUNS} runs each, {COOLDOWN}s apart",
             f"# recorded {time.strftime('%Y-%m-%dT%H:%M:%S')} local",
             f"# curl -w format: {FMT}", ""]
    for d in domains:
        lines.append(f"## {d}")
        rows = []
        for i in range(RUNS):
            if i:
                time.sleep(COOLDOWN)
            raw = probe(d)
            lines.append(f"run{i + 1}: {raw}")
            rows.append(parse(raw))
        v = verdict(rows)
        lines.append(f"verdict: {v}")
        lines.append("")
        print(f"  {d:<34} {v}")
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    print(f"\nraw evidence -> {out_path}")


def self_check():
    """No network. Proves the parser and every branch of the verdict."""
    slow = [{"starttransfer": "5.40", "connect": "0.14"},
            {"starttransfer": "5.30", "connect": "0.19"},
            {"starttransfer": "8.48", "connect": "0.13"}]
    assert verdict(slow).startswith("SERVER-SIDE SLOW"), verdict(slow)

    # The second run's top-ranked prospect: 3.3s under parallel load, fine
    # serially. This is the case the script exists to stop.
    phantom = [{"starttransfer": "0.52", "connect": "0.11"},
               {"starttransfer": "0.83", "connect": "0.12"},
               {"starttransfer": "0.52", "connect": "0.11"}]
    assert verdict(phantom).startswith("NOT SLOW"), verdict(phantom)

    network = [{"starttransfer": "3.10", "connect": "2.90"},
               {"starttransfer": "3.40", "connect": "3.10"},
               {"starttransfer": "3.20", "connect": "3.00"}]
    assert verdict(network).startswith("NETWORK"), verdict(network)

    assert verdict([{"starttransfer": "x", "connect": "1"}]).startswith("INCONCLUSIVE")
    assert verdict([{}]).startswith("INCONCLUSIVE")

    p = parse("http_code=200 connect=0.14 url=https://a.example/")
    assert p["http_code"] == "200" and p["url"] == "https://a.example/", p
    assert parse("curl_error=could not resolve host") == {
        "curl_error": "could not resolve host"}
    print("self-check OK - parser and all four verdicts")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    if args[0] == "--self-check":
        return self_check()
    if len(args) < 2:
        sys.exit("usage: python verify.py RUN_DIR domain [domain...]")
    run_dir, domains = args[0], args[1:]
    if not os.path.isdir(run_dir):
        sys.exit(f"no such run directory: {run_dir}")
    check(domains, os.path.join(run_dir, "verification-raw.txt"))


if __name__ == "__main__":
    main()
