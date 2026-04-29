"""
auto_collect.py
Marketing audit data collection script: C2FO vs SAP Taulia
Covers Google Trends, homepage messaging, and content ecosystem checks.
"""

# ── Standard library ──────────────────────────────────────────────────────────
import time                          # pause between requests to avoid rate-limits
import csv                           # write results to CSV files

# ── Third-party ───────────────────────────────────────────────────────────────
import requests                      # HTTP requests for scraping and URL checks
from bs4 import BeautifulSoup        # HTML parsing
from pytrends.request import TrendReq # Google Trends unofficial API wrapper
import pandas as pd                  # DataFrame handling (pytrends returns DataFrames)

# ── Shared browser-like headers ───────────────────────────────────────────────
# Many sites block the default "python-requests" user-agent; mimic a real browser.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",   # request English content
}

# ── Helper: safe GET ──────────────────────────────────────────────────────────
def safe_get(url, timeout=15):
    """Return (response, error_string).  error_string is None on success."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout,
                            allow_redirects=True)   # follow 301/302 redirects
        return resp, None                            # success path
    except requests.exceptions.Timeout:
        return None, f"TIMEOUT fetching {url}"      # server took too long
    except requests.exceptions.ConnectionError:
        return None, f"CONNECTION ERROR for {url}"  # DNS / network failure
    except Exception as exc:
        return None, f"ERROR fetching {url}: {exc}" # catch-all


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Google Trends comparison
# ══════════════════════════════════════════════════════════════════════════════
def collect_google_trends():
    print("\n─── STEP 1: Google Trends ───────────────────────────────────")

    try:
        # Build a TrendReq session (hl = host language, tz = UTC offset in mins)
        pytrends = TrendReq(hl="en-US", tz=0)

        # Define the two keywords to compare
        keywords = ["C2FO", "SAP Taulia"]

        # Build payload: worldwide (geo=""), past 12 months, web search
        pytrends.build_payload(
            kw_list=keywords,       # keywords to compare
            cat=0,                  # 0 = all categories
            timeframe="today 12-m", # past 12 months
            geo="",                 # "" = worldwide
            gprop=""                # "" = web search (not news/images/etc.)
        )

        # ── Interest over time ────────────────────────────────────────────────
        print("  Fetching interest-over-time data…")
        iot = pytrends.interest_over_time()   # returns a DataFrame indexed by date

        if iot.empty:
            # Google sometimes returns empty results for low-volume or blocked queries
            print("  ⚠ Interest-over-time: Google returned no data. "
                  "MANUAL STEP → visit https://trends.google.com and download "
                  "the CSV for 'C2FO' vs 'SAP Taulia', worldwide, past 12 months.")
            iot_rows = []
        else:
            # Convert DataFrame rows to plain list-of-dicts for CSV writing
            iot_rows = [
                {"section": "interest_over_time",
                 "date": str(idx.date()),           # readable date string
                 "C2FO": row["C2FO"],               # trend score 0–100
                 "SAP Taulia": row["SAP Taulia"]}   # trend score 0–100
                for idx, row in iot.iterrows()
            ]
            print(f"  ✓ Interest-over-time: {len(iot_rows)} weekly data points")

        # Pause to avoid triggering Google's rate-limiter between API calls
        time.sleep(5)

        ibr_rows = []   # default to empty; populated below if the call succeeds

        # ── Interest by region ────────────────────────────────────────────────
        try:
            print("  Fetching interest-by-region data…")
            ibr = pytrends.interest_by_region(
                resolution="COUNTRY",   # aggregate by country (not sub-region)
                inc_low_vol=True,        # include countries with low search volume
                inc_geo_code=False       # omit ISO country codes from output
            )

            if ibr.empty:
                print("  ⚠ Interest-by-region: no data returned. "
                      "MANUAL STEP → download region CSV from Google Trends manually.")
            else:
                ibr_rows = [
                    {"section": "interest_by_region",
                     "date": "aggregated",              # region data has no date axis
                     "C2FO": row["C2FO"],
                     "SAP Taulia": row["SAP Taulia"]}
                    for idx, row in ibr.iterrows()
                    if row["C2FO"] > 0 or row["SAP Taulia"] > 0  # skip zero rows
                ]
                print(f"  ✓ Interest-by-region: {len(ibr_rows)} countries with data")

        except Exception as ibr_exc:
            # Rate-limited or blocked — save IOT data anyway (collected above)
            print(f"  ⚠ Interest-by-region FAILED ({ibr_exc}). "
                  "Saving interest-over-time data only.")
            print("  MANUAL STEP → on Google Trends, switch to the 'Interest by region' "
                  "tab and download that CSV manually.")

        # ── Write CSV ─────────────────────────────────────────────────────────
        # Combine both datasets; write whatever we have (IOT may exist even if IBR failed)
        all_rows = iot_rows + ibr_rows

        if all_rows:
            with open("google_trends.csv", "w", newline="") as f:
                writer = csv.DictWriter(f,
                    fieldnames=["section", "date", "C2FO", "SAP Taulia"])
                writer.writeheader()             # column headers on first row
                writer.writerows(all_rows)       # data rows
            print("  ✓ Saved → google_trends.csv")
        else:
            print("  ✗ google_trends.csv NOT written (no data). See manual steps above.")

    except Exception as exc:
        # Catch any pytrends / network error and give a manual fallback
        print(f"  ✗ Google Trends FAILED: {exc}")
        print("  MANUAL STEP → visit https://trends.google.com, search "
              "'C2FO' vs 'SAP Taulia', set timeframe to Past 12 months, "
              "Worldwide, then download the CSV files manually.")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Homepage messaging scrape
# ══════════════════════════════════════════════════════════════════════════════
def collect_homepage_messaging():
    print("\n─── STEP 2: Homepage Messaging ──────────────────────────────")

    # Targets: brand name → homepage URL
    sites = {
        "C2FO":    "https://c2fo.com",
        "Taulia":  "https://taulia.com",
    }

    rows = []   # will hold one dict per site

    for brand, url in sites.items():
        print(f"  Scraping {brand} ({url})…")

        resp, err = safe_get(url)   # fetch the page

        if err:
            # Network-level failure — tell user what to collect manually
            print(f"  ✗ {brand}: {err}")
            print(f"    MANUAL STEP → open {url} in a browser and note: "
                  "page title, meta description, H1, CTA button text, nav items.")
            rows.append({
                "brand": brand, "url": url,
                "title": "FETCH_FAILED", "meta_description": "FETCH_FAILED",
                "h1": "FETCH_FAILED", "cta_buttons": "FETCH_FAILED",
                "nav_items": "FETCH_FAILED",
            })
            continue   # move to next site

        # Check for JavaScript-only rendering (minimal HTML body is a telltale sign)
        if len(resp.text) < 2000:
            # Some SPAs return a nearly empty HTML shell; BS4 can't parse JS
            print(f"  ⚠ {brand}: Page appears JavaScript-rendered (body too short).")
            print(f"    MANUAL STEP → open {url} in a browser and note the "
                  "title, meta description, H1, CTA buttons, and nav items.")

        # Parse with lxml for speed; fall back to html.parser if unavailable
        soup = BeautifulSoup(resp.text, "lxml")

        # ── <title> tag ───────────────────────────────────────────────────────
        title_tag = soup.find("title")               # find the first <title>
        title = title_tag.get_text(strip=True) if title_tag else "NOT FOUND"

        # ── Meta description ──────────────────────────────────────────────────
        # Check both name="description" and property="og:description"
        meta_desc_tag = (
            soup.find("meta", attrs={"name": "description"}) or
            soup.find("meta", attrs={"property": "og:description"})
        )
        meta_desc = (
            meta_desc_tag.get("content", "NOT FOUND").strip()
            if meta_desc_tag else "NOT FOUND"
        )

        # ── H1 heading ────────────────────────────────────────────────────────
        h1_tag = soup.find("h1")                     # primary page heading
        h1 = h1_tag.get_text(strip=True) if h1_tag else "NOT FOUND"

        # ── CTA buttons ───────────────────────────────────────────────────────
        # Heuristic: buttons or links whose text/class contains "CTA" keywords
        cta_keywords = {"get started", "request demo", "sign up", "contact",
                        "start", "try", "free", "demo", "learn more", "book"}
        cta_texts = []
        for tag in soup.find_all(["a", "button"]):   # check anchors and buttons
            text = tag.get_text(strip=True).lower()  # normalise to lowercase
            if any(kw in text for kw in cta_keywords) and len(text) < 60:
                cta_texts.append(tag.get_text(strip=True))   # keep original case

        # Deduplicate while preserving order, limit to top 5 CTAs
        seen = set()
        unique_ctas = []
        for t in cta_texts:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_ctas.append(t)
                if len(unique_ctas) >= 5:     # cap at 5 to keep CSV readable
                    break

        cta_str = " | ".join(unique_ctas) if unique_ctas else "NOT FOUND"

        # ── Navigation items ──────────────────────────────────────────────────
        # Try common nav landmark patterns in order of specificity
        nav_items = []
        nav_container = (
            soup.find("nav") or                          # semantic <nav> element
            soup.find(attrs={"role": "navigation"}) or  # ARIA role
            soup.find(id=lambda x: x and "nav" in x.lower()) or  # id contains "nav"
            soup.find(class_=lambda x: x and "nav" in " ".join(x).lower()
                      if isinstance(x, list) else "nav" in x.lower())  # class contains "nav"
        )

        if nav_container:
            for link in nav_container.find_all("a"):    # all anchor tags inside nav
                text = link.get_text(strip=True)
                if text and len(text) < 50:              # skip empty or overly long text
                    nav_items.append(text)

        # Deduplicate nav items
        nav_items = list(dict.fromkeys(nav_items))      # preserves insertion order
        nav_str = " | ".join(nav_items[:10]) if nav_items else "NOT FOUND"  # cap at 10

        print(f"    Title:    {title[:80]}")
        print(f"    H1:       {h1[:80]}")
        print(f"    CTA(s):   {cta_str[:80]}")
        print(f"    Nav:      {nav_str[:80]}")

        rows.append({
            "brand": brand,
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "h1": h1,
            "cta_buttons": cta_str,
            "nav_items": nav_str,
        })

        time.sleep(2)   # polite delay between site requests

    # ── Write CSV ─────────────────────────────────────────────────────────────
    with open("website_messaging.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "brand", "url", "title", "meta_description",
            "h1", "cta_buttons", "nav_items"
        ])
        writer.writeheader()
        writer.writerows(rows)
    print("  ✓ Saved → website_messaging.csv")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Content ecosystem check
# ══════════════════════════════════════════════════════════════════════════════
def collect_content_ecosystem():
    print("\n─── STEP 3: Content Ecosystem ───────────────────────────────")

    # Content paths to probe on each domain
    content_paths = [
        "/blog",
        "/newsroom",
        "/resources",
        "/case-studies",
        "/webinars",
        "/podcast",
        "/events",
        "/glossary",
    ]

    # Base URLs for each brand
    bases = {
        "c2fo":   "https://c2fo.com",
        "taulia": "https://taulia.com",
    }

    rows = []   # one row per content_type

    for path in content_paths:
        content_type = path.lstrip("/")   # strip leading slash for display

        row = {"content_type": content_type}   # start building the result row

        for brand, base in bases.items():
            full_url = base + path           # e.g. https://c2fo.com/blog
            print(f"  Checking {full_url}…", end=" ")

            resp, err = safe_get(full_url)   # attempt the HTTP GET

            if err:
                # Network error — can't determine existence
                print(f"ERROR ({err})")
                row[f"{brand}_exists"] = "ERROR"
                row[f"{brand}_url"]    = full_url
                print(f"    MANUAL STEP → visit {full_url} and note whether it exists.")
            else:
                # 200 = page exists; 404 = not found; other codes noted
                exists = resp.status_code == 200
                print(f"{'✓ EXISTS' if exists else f'✗ {resp.status_code}'}")
                row[f"{brand}_exists"] = "yes" if exists else "no"
                row[f"{brand}_url"]    = resp.url   # final URL after redirects

            time.sleep(1)   # small pause between each URL check

        rows.append(row)

    # ── Write CSV ─────────────────────────────────────────────────────────────
    with open("content_ecosystem.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "content_type",
            "c2fo_exists",   "c2fo_url",
            "taulia_exists", "taulia_url",
        ])
        writer.writeheader()
        writer.writerows(rows)
    print("  ✓ Saved → content_ecosystem.csv")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  Marketing Audit — Automated Data Collection")
    print("  C2FO vs SAP Taulia")
    print("=" * 60)

    collect_google_trends()      # Step 1
    collect_homepage_messaging() # Step 2
    collect_content_ecosystem()  # Step 3

    print("\n" + "=" * 60)
    print("  Collection complete. Output files:")
    print("    google_trends.csv      — Trends comparison data")
    print("    website_messaging.csv  — Homepage title / H1 / CTA / nav")
    print("    content_ecosystem.csv  — Content page existence checks")
    print("=" * 60)
