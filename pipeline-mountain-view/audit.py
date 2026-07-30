"""Audit prospect dental sites for the outreach signals Clay can't measure.

Clay gives us the practice + domain; page speed, uptime, mobile-readiness and
booking links have to be measured by actually fetching the site.

ponytail: stdlib urllib + threads, no requests/playwright. Upgrade to a real
headless browser only if we start needing rendered-DOM signals (JS-injected
booking widgets would be the trigger).
"""
import io, json, re, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
TIMEOUT = 12
BOOKING = re.compile(r"(book|appointment|schedule|request an? (visit|appt))", re.I)

# ponytail: shell out to curl rather than urllib. Python's ssl module rejects
# incomplete cert chains that every real browser accepts, which produced a
# false "site unreachable" on a practice whose site loads fine. curl's CA
# handling is the closest cheap proxy for what a prospect's customer sees.
CURL_ERRORS = {6: "DNS does not resolve", 7: "connection refused",
               28: "timed out", 35: "TLS handshake failed",
               51: "bad TLS certificate", 60: "untrusted TLS certificate"}


def fetch(url):
    """Return (status, seconds, body, final_url) or (None, seconds, error, None)."""
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        path = tmp.name
    p = subprocess.run(
        ["curl", "-sSL", "--max-time", str(TIMEOUT), "-A", UA, "-o", path,
         "-w", "%{http_code} %{time_total} %{url_effective}", url],
        capture_output=True, text=True)
    try:
        # Trust the HTTP code over curl's exit code. curl 56 ("server closed
        # abruptly / missing close_notify") is a benign TLS-teardown quirk that
        # still delivers a full 200 response - reporting it as "site down" to a
        # prospect whose site works would be a false accusation.
        code, secs, final = 0, 0.0, url
        if p.stdout.strip():
            parts = p.stdout.strip().split(" ", 2)
            if len(parts) == 3:
                code, secs, final = int(parts[0]), float(parts[1]), parts[2]
        if code == 0:
            reason = CURL_ERRORS.get(p.returncode, f"curl error {p.returncode}")
            return None, 0.0, reason, None
        body = io.open(path, encoding="utf-8", errors="replace").read(300_000)
        return code, secs, body, final
    finally:
        try:
            __import__("os").unlink(path)
        except OSError:
            pass


# Domains where a human checked the site in a real browser and the automated
# verdict was wrong. Clay's stored domain is not always the practice's live one.
OVERRIDES = {
    "practice-c.example": (
        "NOT A PROSPECT - Clay's domain is stale. The practice's live site is "
        "practice-c-live.example (HTTP 200 in 0.85s), confirmed via the work "
        "email alpha@practice-c-live.example."),
}


def audit(row):
    domain = row["domain"]
    if domain in OVERRIDES:
        return {"name": row["name"], "domain": domain, "score": 0,
                "signals": [OVERRIDES[domain]], "disqualified": True,
                "linkedin_url": row.get("linkedin_url"), "size": row.get("size")}
    out = {"name": row["name"], "domain": domain,
           "linkedin_url": row.get("linkedin_url"), "size": row.get("size"),
           "signals": [], "score": 0}

    status, secs, body, final = fetch(f"https://{domain}")
    if status is None:  # bare domain failed - try www, as Samin's example did
        status2, secs2, body2, final2 = fetch(f"https://www.{domain}")
        if status2 is None:
            out.update(reachable=False, status=None, load_s=None,
                       error=f"bare: {body} / www: {body2}")
            out["signals"].append(f"site unreachable - {body} (www also fails: {body2})")
            out["score"] += 100
            return out
        status, secs, body, final = status2, secs2, body2, final2
        out["signals"].append("bare domain fails, only www resolves")
        out["score"] += 25

    out.update(reachable=True, status=status, load_s=round(secs, 2), final_url=final)

    # 401/403/429 to a scripted request almost always means "WAF blocked a
    # spoofed browser", not "the site is broken" - practice-d.example served a
    # hard 403 here while rendering perfectly in real Chrome. Never bill that as
    # a defect; mark it inconclusive and let a human look.
    if status in (401, 403, 429):
        out["signals"].append(f"HTTP {status} to automated request - INCONCLUSIVE, verify in a browser")
        out["inconclusive"] = True
        return out

    if status >= 400:
        out["signals"].append(f"HTTP {status} error page")
        out["score"] += 80
        return out

    if secs > 3.0:
        out["signals"].append(f"slow first load: {secs:.1f}s")
        out["score"] += 30
    elif secs > 1.5:
        out["signals"].append(f"sluggish first load: {secs:.1f}s")
        out["score"] += 12

    # These two read raw HTML, so a client-rendered site looks broken when it
    # isn't: practice-f.example ships a big "24/7 Online Scheduling" button that
    # never appears in the served markup. Record them as leads to check, never as
    # facts, and keep them out of the score that ranks who we contact.
    if 'name="viewport"' not in body and "name='viewport'" not in body:
        out.setdefault("needs_render_check", []).append("no viewport meta in served HTML")

    if not BOOKING.search(body):
        out.setdefault("needs_render_check", []).append("no booking link in served HTML")

    if len(body) < 2000:
        out["signals"].append("near-empty homepage (parked or broken?)")
        out["score"] += 40

    if re.search(r"\b(19|20)(0\d|1[0-5])\b", body) and "copyright" in body.lower():
        out["signals"].append("copyright year looks stale")
        out["score"] += 10

    if final and final.startswith("http://"):
        out["signals"].append("no HTTPS - browsers show 'Not secure'")
        out["score"] += 45

    return out


def main():
    rows = json.load(io.open("prospects_raw.json", encoding="utf-8"))["data"]
    seen, uniq = set(), []
    for r in rows:  # same domain can appear twice (multi-location practices)
        if r.get("domain") and r["domain"] not in seen:
            seen.add(r["domain"])
            uniq.append(r)

    # ponytail: 3 workers, not 10. Ten parallel hits tripped prospects' WAFs and
    # produced phantom 403s. A slower sweep is the whole fix.
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(audit, uniq))

    # Confirmation pass: anything claiming the site is broken gets re-checked
    # serially. A signal that won't reproduce doesn't go in an email.
    # The cooldown is load-bearing: re-checking immediately just re-triggers the
    # same rate limiting that caused the phantom failure in the first place.
    hard = ("unreachable", "error page", "HTTPS", "bare domain")
    for r in results:
        if any(k in s for s in r["signals"] for k in hard):
            time.sleep(5)
            again = audit(next(u for u in uniq if u["domain"] == r["domain"]))
            kept = [s for s in r["signals"] if s in again["signals"]]
            if kept != r["signals"]:
                r["unconfirmed"] = [s for s in r["signals"] if s not in kept]
                r["signals"], r["score"] = again["signals"], again["score"]

    results.sort(key=lambda r: -r["score"])
    json.dump(results, io.open("audit_results.json", "w", encoding="utf-8"), indent=2)

    print(f"audited {len(results)} practices\n")
    for r in results:
        if r["score"] > 0:
            print(f'{r["score"]:>4}  {r["name"][:38]:<38} {r["domain"][:32]:<32} {"; ".join(r["signals"])[:70]}')
    clean = sum(1 for r in results if r["score"] == 0)
    print(f"\n{clean} practices had no detectable issues (not prospects)")


if __name__ == "__main__":
    main()
