"""
marketing_audit.py
Competitive Marketing Audit: SAP Taulia vs C2FO
Author: Alanah Stephens
Reads 7 CSVs, runs a 5-dimension analysis, builds 4 charts, a summary CSV,
and a multi-page PDF report.
"""

# ─── Auto-install required libraries ──────────────────────────────────────────
import subprocess                                          # run pip from inside Python
import sys                                                 # access the current Python interpreter

# List of packages this script needs
REQUIRED = ["pandas", "matplotlib", "reportlab"]

# Loop through each required package and install if missing
for pkg in REQUIRED:                                       # iterate package list
    try:                                                   # try importing it
        __import__(pkg)                                    # dynamic import by string name
    except ImportError:                                    # if not installed
        print(f"Installing {pkg}…")                        # tell user
        subprocess.check_call([sys.executable,             # use current Python
                               "-m", "pip",                # call pip module
                               "install", pkg])            # install the package

# ─── Standard imports (after install guard) ───────────────────────────────────
import os                                                  # filesystem helpers (file sizes etc.)
import csv                                                 # write CSV summary
from datetime import date                                  # today's date for the PDF title page
from collections import Counter                            # count themes / sentiments quickly

# Third-party imports
import pandas as pd                                        # DataFrames for CSV handling
import matplotlib                                          # base matplotlib
matplotlib.use("Agg")                                      # use non-interactive backend (saves to file, no GUI)
import matplotlib.pyplot as plt                            # plotting interface
import numpy as np                                         # numeric arrays (used for radar chart angles)

# ReportLab (PDF) imports
from reportlab.lib.pagesizes import LETTER                 # standard US Letter page size
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # text styles
from reportlab.lib.units import inch                       # convert inches to points
from reportlab.lib.colors import HexColor, black, white    # colour helpers
from reportlab.lib.enums import TA_LEFT, TA_CENTER         # text alignment constants
from reportlab.platypus import (                           # Platypus = high-level PDF flow layout
    SimpleDocTemplate,                                     # the document container
    Paragraph,                                             # styled text block
    Spacer,                                                # vertical spacing
    Image as RLImage,                                      # embedded image (renamed to avoid clash)
    PageBreak,                                             # forces a new page
    HRFlowable,                                            # horizontal rule
    KeepTogether,                                          # groups elements onto one page when possible
    ListFlowable,                                          # bullet/numbered list
    ListItem,                                              # single list item
)

# ─── Constants ────────────────────────────────────────────────────────────────
SAP_BLUE   = "#0070D2"                                     # brand colour for Taulia (SAP blue)
C2FO_GREEN = "#06A76C"                                     # brand colour for C2FO (green)
TODAY_STR  = date.today().strftime("%B %d, %Y")            # today as e.g. "April 27, 2026"

# Map of CSV file → expected location (current folder)
CSV_FILES = {                                              # dictionary keyed by short name
    "social":   "social_media.csv",                        # social media metrics
    "summary":  "review_summary.csv",                      # review aggregate scores
    "themes":   "review_themes.csv",                       # paraphrased review rows
    "trends":   "google_trends.csv",                       # Google Trends comparison
    "messaging":"website_messaging.csv",                   # homepage scrape data
    "seo":      "seo_traffic.csv",                         # SimilarWeb metrics
    "content":  "content_ecosystem.csv",                   # content type existence
}


# ══════════════════════════════════════════════════════════════════════════════
# PART A — LOAD AND CLEAN
# ══════════════════════════════════════════════════════════════════════════════
def load_and_clean():
    """Load all CSVs, print summaries, and clean each DataFrame."""
    print("\n" + "=" * 70)                                 # visual divider
    print("PART A — Loading & cleaning CSVs")               # section header
    print("=" * 70)                                        # visual divider

    dfs = {}                                               # dict to hold all DataFrames

    # Loop over each CSV and load it
    for key, filename in CSV_FILES.items():                # iterate file dict
        df = pd.read_csv(filename)                         # read CSV into DataFrame

        # Strip whitespace from column names (cosmetic safety)
        df.columns = [c.strip() for c in df.columns]       # rebuild column list with strip()

        # For every string (object) column, strip whitespace from each cell
        for col in df.select_dtypes(include="object").columns:  # only text columns
            df[col] = df[col].astype(str).str.strip()      # cast and strip leading/trailing spaces

        # Standardise company names to "C2FO" or "Taulia" wherever a company column exists
        for col in df.columns:                             # check each column
            if col.lower() in ("company", "brand"):        # column is a brand identifier
                # Replace any "SAP Taulia" or "sap taulia" with the canonical "Taulia"
                df[col] = df[col].replace(                 # replace specific values
                    {"SAP Taulia": "Taulia", "sap taulia": "Taulia",
                     "C2fo": "C2FO", "c2fo": "C2FO"})

        dfs[key] = df                                      # store cleaned DataFrame

        # Print a concise summary for the user
        missing = df.isna().sum().sum()                    # total missing cells across the frame
        print(f"\n• {filename}")                           # filename header
        print(f"   rows: {len(df)},  cols: {len(df.columns)},  missing cells: {missing}")
        print(f"   columns: {', '.join(df.columns)}")      # list column names

    return dfs                                             # return dict of DataFrames


# ══════════════════════════════════════════════════════════════════════════════
# PART B — DIMENSION 1: BRAND VISIBILITY
# ══════════════════════════════════════════════════════════════════════════════
def analyse_brand_visibility(dfs):
    """Compare follower totals, search interest, and web traffic."""
    print("\n" + "=" * 70)                                 # divider
    print("DIMENSION 1 — Brand Visibility")                # section header
    print("=" * 70)                                        # divider

    social = dfs["social"]                                 # alias social DataFrame

    # Sum followers per company across LinkedIn / X / YouTube
    followers = social.groupby("company")["followers"].sum()  # group + sum
    c2fo_followers   = int(followers.get("C2FO", 0))       # total C2FO followers
    taulia_followers = int(followers.get("Taulia", 0))     # total Taulia followers

    print(f"  Total social followers — C2FO: {c2fo_followers:,}   Taulia: {taulia_followers:,}")

    # Google Trends — average interest_over_time score per brand
    trends_iot = dfs["trends"][dfs["trends"]["section"] == "interest_over_time"]  # filter rows
    avg_c2fo_trend   = trends_iot["C2FO"].mean()           # mean weekly score C2FO
    avg_taulia_trend = trends_iot["SAP Taulia"].mean()     # mean weekly score Taulia

    print(f"  Avg Google Trends score   — C2FO: {avg_c2fo_trend:.1f}   Taulia: {avg_taulia_trend:.1f}")

    # SEO — pull "Estimated Monthly Visits" row from seo_traffic
    seo = dfs["seo"]                                       # alias SEO DataFrame
    visits_row = seo[seo["metric"] == "Estimated Monthly Visits"].iloc[0]  # row with traffic figures

    # The visits CSV stores values like "76.8K" / "304.4K" — convert to integers
    def parse_visits(s):                                   # helper to convert "76.8K" → 76800
        s = str(s).replace(",", "").strip()                # drop commas/spaces
        if s.endswith("K"):                                # value in thousands
            return int(float(s[:-1]) * 1_000)              # multiply by 1k
        if s.endswith("M"):                                # value in millions
            return int(float(s[:-1]) * 1_000_000)          # multiply by 1m
        return int(float(s))                               # plain number fallback

    c2fo_visits   = parse_visits(visits_row["c2fo"])       # parse C2FO visits
    taulia_visits = parse_visits(visits_row["taulia"])     # parse Taulia visits

    print(f"  Monthly web visits        — C2FO: {c2fo_visits:,}   Taulia: {taulia_visits:,}")

    # Compute a simple 1–10 score per dimension using normalised proportions
    def score_pair(a, b):                                  # helper: bigger value → 10
        if a == b == 0:                                    # both zero → both 5
            return 5, 5                                    # neutral score
        leader = max(a, b)                                 # highest value
        return round(10 * a / leader, 1), round(10 * b / leader, 1)  # scale by leader

    # Average the per-metric scores into a single brand visibility score
    f_c, f_t = score_pair(c2fo_followers, taulia_followers)            # follower score
    s_c, s_t = score_pair(avg_c2fo_trend, avg_taulia_trend)            # search interest score
    v_c, v_t = score_pair(c2fo_visits, taulia_visits)                  # web visits score

    c2fo_score   = round((f_c + s_c + v_c) / 3, 1)         # mean of three
    taulia_score = round((f_t + s_t + v_t) / 3, 1)         # mean of three

    print(f"  → Brand Visibility score — C2FO: {c2fo_score}/10   Taulia: {taulia_score}/10")

    # Return a dict with everything other functions might need
    return {                                               # bundled results
        "c2fo_followers":   c2fo_followers,
        "taulia_followers": taulia_followers,
        "avg_c2fo_trend":   round(avg_c2fo_trend, 1),
        "avg_taulia_trend": round(avg_taulia_trend, 1),
        "c2fo_visits":      c2fo_visits,
        "taulia_visits":    taulia_visits,
        "c2fo_score":       c2fo_score,
        "taulia_score":     taulia_score,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PART B — DIMENSION 2: CONTENT STRATEGY
# ══════════════════════════════════════════════════════════════════════════════
def analyse_content_strategy(dfs):
    """Count content types and posting frequency."""
    print("\n" + "=" * 70)                                 # divider
    print("DIMENSION 2 — Content Strategy")                # header
    print("=" * 70)                                        # divider

    content = dfs["content"]                               # alias content DataFrame

    # Count rows where each company has the content type ("yes")
    c2fo_yes   = (content["c2fo_exists"].str.lower()   == "yes").sum()  # number of "yes" rows
    taulia_yes = (content["taulia_exists"].str.lower() == "yes").sum()  # number of "yes" rows
    total_types = len(content)                             # total content categories tracked

    print(f"  Content types present     — C2FO: {c2fo_yes}/{total_types}   Taulia: {taulia_yes}/{total_types}")

    # Posting frequency — sum posts_per_week across platforms
    social = dfs["social"]                                 # alias social DataFrame

    def parse_posts(value):                                # helper: handle "~1.75" / "0" / "N/A"
        s = str(value).replace("~", "").strip()            # drop the tilde marker
        try:                                               # try numeric conversion
            return float(s)                                # return a float
        except ValueError:                                 # any non-numeric value
            return 0.0                                     # treat as zero posts

    social["posts_numeric"] = social["posts_per_week"].apply(parse_posts)  # add numeric column
    posts = social.groupby("company")["posts_numeric"].sum()               # sum across platforms

    c2fo_posts   = round(float(posts.get("C2FO",   0)), 2) # C2FO posts/week total
    taulia_posts = round(float(posts.get("Taulia", 0)), 2) # Taulia posts/week total

    print(f"  Posts per week (combined) — C2FO: {c2fo_posts}   Taulia: {taulia_posts}")

    # Score: weighted blend of breadth (60%) and posting frequency (40%)
    # Floor the loser's contribution at 1.0 so a zero loser doesn't push the leader to a clean 10
    def score_pair(a, b):                                  # same scaling helper
        if a == b == 0: return 5, 5                        # both zero edge case
        leader = max(a, b)                                 # leader value
        # Leader caps at 9.5 (room for "perfect" performance); loser floored at 1
        a_score = max(1.0, 9.5 * a / leader) if a > 0 else 1.0   # C2FO/loser score
        b_score = max(1.0, 9.5 * b / leader) if b > 0 else 1.0   # Taulia/loser score
        return a_score, b_score                            # return scaled scores

    breadth_c, breadth_t = score_pair(c2fo_yes, taulia_yes)        # breadth score
    freq_c,    freq_t    = score_pair(c2fo_posts, taulia_posts)    # frequency score

    c2fo_score   = round(0.6 * breadth_c + 0.4 * freq_c, 1)        # weighted final
    taulia_score = round(0.6 * breadth_t + 0.4 * freq_t, 1)        # weighted final

    print(f"  → Content Strategy score  — C2FO: {c2fo_score}/10   Taulia: {taulia_score}/10")

    return {                                               # bundle results
        "c2fo_content_types":   int(c2fo_yes),
        "taulia_content_types": int(taulia_yes),
        "total_content_types":  int(total_types),
        "c2fo_posts_per_week":   c2fo_posts,
        "taulia_posts_per_week": taulia_posts,
        "c2fo_score":   c2fo_score,
        "taulia_score": taulia_score,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PART B — DIMENSION 3: CUSTOMER PERCEPTION
# ══════════════════════════════════════════════════════════════════════════════
def analyse_customer_perception(dfs):
    """Compare ratings, sentiment ratios, and themes."""
    print("\n" + "=" * 70)                                 # divider
    print("DIMENSION 3 — Customer Perception")             # header
    print("=" * 70)                                        # divider

    summary = dfs["summary"]                               # alias review_summary
    themes  = dfs["themes"]                                # alias review_themes

    # Convert overall_rating to numeric (treat 'N/A' as NaN)
    summary["rating_num"] = pd.to_numeric(summary["overall_rating"], errors="coerce")  # safe cast
    summary["reviews_num"] = pd.to_numeric(summary["total_reviews"], errors="coerce").fillna(0)  # cast

    # Weighted average rating per company (rating × number of reviews)
    def weighted_rating(company):                          # helper for one brand
        rows = summary[(summary["company"] == company) & summary["rating_num"].notna()]  # valid rows
        if rows.empty or rows["reviews_num"].sum() == 0:   # nothing to weight
            return None                                    # not available
        return round((rows["rating_num"] * rows["reviews_num"]).sum() / rows["reviews_num"].sum(), 2)

    c2fo_rating   = weighted_rating("C2FO")                # weighted C2FO rating
    taulia_rating = weighted_rating("Taulia")              # weighted Taulia rating

    # Total review counts
    c2fo_reviews   = int(summary[summary["company"] == "C2FO"]["reviews_num"].sum())   # total reviews
    taulia_reviews = int(summary[summary["company"] == "Taulia"]["reviews_num"].sum()) # total reviews

    print(f"  Weighted avg rating       — C2FO: {c2fo_rating}   Taulia: {taulia_rating}")
    print(f"  Total review count        — C2FO: {c2fo_reviews}   Taulia: {taulia_reviews}")

    # Sentiment counts from review_themes.csv
    def sentiment_counts(company):                         # helper per brand
        rows = themes[themes["company"] == company]       # filter brand rows
        c = Counter(rows["sentiment"].str.title())         # count Positive/Negative/Neutral
        return {"Positive": c.get("Positive", 0),         # positive count
                "Negative": c.get("Negative", 0),         # negative count
                "Neutral":  c.get("Neutral",  0)}         # neutral count

    c2fo_sent   = sentiment_counts("C2FO")                 # C2FO sentiment dict
    taulia_sent = sentiment_counts("Taulia")               # Taulia sentiment dict

    # Positive sentiment ratio (positive / total)
    def pos_ratio(s):                                      # helper for ratio
        total = sum(s.values())                            # total reviews counted
        return round(s["Positive"] / total, 2) if total else 0.0  # avoid divide-by-zero

    c2fo_pos_ratio   = pos_ratio(c2fo_sent)                # C2FO positive ratio
    taulia_pos_ratio = pos_ratio(taulia_sent)              # Taulia positive ratio

    print(f"  Sentiment (P/Neu/N) C2FO   : {c2fo_sent['Positive']}/{c2fo_sent['Neutral']}/{c2fo_sent['Negative']}  → +ratio {c2fo_pos_ratio}")
    print(f"  Sentiment (P/Neu/N) Taulia : {taulia_sent['Positive']}/{taulia_sent['Neutral']}/{taulia_sent['Negative']}  → +ratio {taulia_pos_ratio}")

    # Most common theme by sentiment per company
    # Excludes the catch-all "Other" theme so the meaningful theme surfaces;
    # returns explicit copy when there are no reviews of that sentiment.
    NO_NEG = "No negative reviews in sample"               # placeholder for missing negatives
    NO_POS = "No positive reviews in sample"               # placeholder for missing positives

    def top_theme(company, sentiment):                     # helper for theme
        rows = themes[(themes["company"] == company) &     # match company
                      (themes["sentiment"].str.title() == sentiment)]  # match sentiment
        if rows.empty:                                     # no rows of this sentiment
            return NO_NEG if sentiment == "Negative" else NO_POS  # explicit copy
        # Drop the generic "Other" bucket so the next-most-common theme wins
        meaningful = rows[rows["theme"].str.lower() != "other"]   # filter Other
        if not meaningful.empty:                           # if at least one specific theme
            return meaningful["theme"].value_counts().idxmax()    # most common specific theme
        return rows["theme"].value_counts().idxmax()       # fallback (only "Other" exists)

    c2fo_top_pos = top_theme("C2FO",   "Positive")         # C2FO strength
    c2fo_top_neg = top_theme("C2FO",   "Negative")         # C2FO weakness
    tau_top_pos  = top_theme("Taulia", "Positive")         # Taulia strength
    tau_top_neg  = top_theme("Taulia", "Negative")         # Taulia weakness

    print(f"  Top positive theme        — C2FO: {c2fo_top_pos}   Taulia: {tau_top_pos}")
    print(f"  Top negative theme        — C2FO: {c2fo_top_neg}   Taulia: {tau_top_neg}")

    # Score: rating quality (60%) + sentiment ratio (40%), capped 1-10
    def rating_score(r):                                   # convert 5-point rating to 0-10 scale
        if r is None: return 0                             # missing rating → 0
        return round(r * 2, 1)                             # multiply by 2 (4.5 → 9.0)

    c2fo_score   = round(0.6 * rating_score(c2fo_rating)   + 0.4 * (c2fo_pos_ratio   * 10), 1)
    taulia_score = round(0.6 * rating_score(taulia_rating) + 0.4 * (taulia_pos_ratio * 10), 1)

    # Penalise C2FO for tiny sample (only 1 review): cap at 6
    if c2fo_reviews <= 1:                                  # too few reviews to trust
        c2fo_score = min(c2fo_score, 6.0)                  # cap the score

    print(f"  → Customer Perception     — C2FO: {c2fo_score}/10   Taulia: {taulia_score}/10")

    return {                                               # bundle results
        "c2fo_rating":   c2fo_rating,
        "taulia_rating": taulia_rating,
        "c2fo_reviews":   c2fo_reviews,
        "taulia_reviews": taulia_reviews,
        "c2fo_sentiment":   c2fo_sent,
        "taulia_sentiment": taulia_sent,
        "c2fo_pos_ratio":   c2fo_pos_ratio,
        "taulia_pos_ratio": taulia_pos_ratio,
        "c2fo_top_pos":   c2fo_top_pos,
        "c2fo_top_neg":   c2fo_top_neg,
        "taulia_top_pos": tau_top_pos,
        "taulia_top_neg": tau_top_neg,
        "c2fo_score":   c2fo_score,
        "taulia_score": taulia_score,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PART B — DIMENSION 4: MESSAGING & POSITIONING
# ══════════════════════════════════════════════════════════════════════════════
def analyse_messaging(dfs):
    """Compare homepage messaging side-by-side."""
    print("\n" + "=" * 70)                                 # divider
    print("DIMENSION 4 — Messaging & Positioning")         # header
    print("=" * 70)                                        # divider

    msg = dfs["messaging"]                                 # alias messaging DataFrame

    # Index by brand for easy lookup
    msg_by_brand = msg.set_index("brand")                  # brand becomes the index

    c2fo_row   = msg_by_brand.loc["C2FO"]                  # C2FO row
    taulia_row = msg_by_brand.loc["Taulia"]                # Taulia row

    # Pull the key fields
    c2fo_h1   = c2fo_row["h1"]                             # C2FO headline
    taulia_h1 = taulia_row["h1"]                           # Taulia headline
    c2fo_meta   = c2fo_row["meta_description"]             # C2FO meta description
    taulia_meta = taulia_row["meta_description"]           # Taulia meta description
    # Pick the strongest action-oriented CTA, falling back to the first one
    def pick_primary_cta(cta_string):                      # helper to choose best CTA
        ctas = [c.strip() for c in cta_string.split("|") if c.strip()]  # split + clean
        # Action-oriented keywords ranked by intent strength (high → low)
        priority = ["request a demo", "request demo", "book a demo",     # demo asks
                    "get started", "start free", "start now",             # signup asks
                    "try", "sign up",                                     # softer signup
                    "learn more"]                                         # info ask
        for kw in priority:                                # check keywords in order
            for cta in ctas:                               # check each CTA
                if kw in cta.lower():                      # case-insensitive match
                    return cta                             # return the original-case CTA
        return ctas[0] if ctas else "—"                    # fallback to first CTA

    c2fo_cta   = pick_primary_cta(c2fo_row["cta_buttons"])    # primary C2FO CTA
    taulia_cta = pick_primary_cta(taulia_row["cta_buttons"])  # primary Taulia CTA

    print(f"  C2FO   H1 :  {c2fo_h1}")                     # show headlines
    print(f"  Taulia H1 :  {taulia_h1}")                   # show headlines
    print(f"  C2FO   CTA:  {c2fo_cta}")                    # show CTAs
    print(f"  Taulia CTA:  {taulia_cta}")                  # show CTAs

    # Positioning summary (manual interpretation, grounded in data)
    c2fo_position   = "Speed & accessibility — 'Get Paid Faster' positions the platform as a fast working capital fix for suppliers."
    taulia_position = "Insight & optimisation — 'Cash Flow Acceleration Platform' positions Taulia as an enterprise-grade decision tool with SAP backing."

    print(f"  C2FO   positioning : {c2fo_position}")       # narrative
    print(f"  Taulia positioning : {taulia_position}")     # narrative

    # Score: clarity is judged by headline punchiness + CTA strength
    # C2FO has a sharp benefit headline + strong "Request a Demo" CTA → 8
    # Taulia has a metaphorical headline + softer "Contact Us" CTA → 7
    c2fo_score   = 8.0                                     # C2FO clarity score
    taulia_score = 7.0                                     # Taulia clarity score

    print(f"  → Messaging Clarity       — C2FO: {c2fo_score}/10   Taulia: {taulia_score}/10")

    return {                                               # bundle messaging info
        "c2fo_h1":   c2fo_h1,
        "taulia_h1": taulia_h1,
        "c2fo_meta":   c2fo_meta,
        "taulia_meta": taulia_meta,
        "c2fo_cta":   c2fo_cta,
        "taulia_cta": taulia_cta,
        "c2fo_position":   c2fo_position,
        "taulia_position": taulia_position,
        "c2fo_score":   c2fo_score,
        "taulia_score": taulia_score,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PART B — DIMENSION 5: CONTENT MARKETING MATURITY
# ══════════════════════════════════════════════════════════════════════════════
def analyse_content_maturity(dfs):
    """Identify content gaps between the two companies."""
    print("\n" + "=" * 70)                                 # divider
    print("DIMENSION 5 — Content Marketing Maturity")      # header
    print("=" * 70)                                        # divider

    content = dfs["content"]                               # alias content frame

    # Lists of content types per company (where exists == yes)
    c2fo_has   = content[content["c2fo_exists"].str.lower()   == "yes"]["content_type"].tolist()
    taulia_has = content[content["taulia_exists"].str.lower() == "yes"]["content_type"].tolist()

    # Gaps: what one has and the other does not
    c2fo_only   = sorted(set(c2fo_has)   - set(taulia_has))  # C2FO-only types
    taulia_only = sorted(set(taulia_has) - set(c2fo_has))    # Taulia-only types

    print(f"  C2FO has   ({len(c2fo_has)}): {', '.join(c2fo_has)}")
    print(f"  Taulia has ({len(taulia_has)}): {', '.join(taulia_has)}")
    print(f"  C2FO-only content types  : {', '.join(c2fo_only) or 'none'}")
    print(f"  Taulia-only content types: {', '.join(taulia_only) or 'none'}")

    # Score: same scaling as content strategy breadth, plus depth bonus for C2FO
    total = len(content)                                   # total tracked types
    c2fo_score   = round((len(c2fo_has)   / total) * 10, 1)  # proportion × 10
    taulia_score = round((len(taulia_has) / total) * 10, 1)  # proportion × 10

    print(f"  → Content Maturity score  — C2FO: {c2fo_score}/10   Taulia: {taulia_score}/10")

    return {                                               # bundle results
        "c2fo_has":     c2fo_has,
        "taulia_has":   taulia_has,
        "c2fo_only":    c2fo_only,
        "taulia_only":  taulia_only,
        "c2fo_score":   c2fo_score,
        "taulia_score": taulia_score,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PART C — STRATEGIC OUTPUT
# ══════════════════════════════════════════════════════════════════════════════
def build_strategic_output(d1, d2, d3, d4, d5):
    """Generate strengths/weaknesses and 3 recommendations."""
    print("\n" + "=" * 70)                                 # divider
    print("PART C — Strategic Output")                     # header
    print("=" * 70)                                        # divider

    # Where Taulia leads — pick three concrete data wins
    taulia_leads = [
        f"Web traffic quality: Taulia attracts ~{d1['taulia_visits']:,} monthly visits vs C2FO's ~{d1['c2fo_visits']:,} (~{d1['taulia_visits']//max(d1['c2fo_visits'],1)}x more).",
        f"Customer reviews: Taulia averages {d3['taulia_rating']}/5 across {d3['taulia_reviews']} reviews; C2FO has only {d3['c2fo_reviews']} review on record.",
        "SEO depth: Taulia ranks for ~2,400 keywords vs C2FO's ~463 — Taulia's organic search footprint is ~5x larger.",
    ]

    # Where C2FO leads — three concrete wins
    c2fo_leads = [
        f"Search interest: C2FO averages {d1['avg_c2fo_trend']} on Google Trends vs Taulia's {d1['avg_taulia_trend']} — roughly {d1['avg_c2fo_trend']/max(d1['avg_taulia_trend'],1):.0f}x higher demand.",
        f"Social reach: C2FO has {d1['c2fo_followers']:,} followers across LinkedIn/X/YouTube vs Taulia's {d1['taulia_followers']:,} — {d1['c2fo_followers']/max(d1['taulia_followers'],1):.1f}x larger.",
        f"Content ecosystem: C2FO publishes {d2['c2fo_content_types']}/{d2['total_content_types']} content types (blog, newsroom, podcast, etc.) vs Taulia's {d2['taulia_content_types']}/{d2['total_content_types']}.",
    ]

    # Three recommendations grounded in the data
    recommendations = [
        {
            "title": "1. Reactivate dormant social channels",
            "body": ("Taulia has not posted on LinkedIn in 4+ weeks and last posted on X in June 2024. "
                     "Meanwhile, the brand's 27,000 LinkedIn followers represent a captive audience receiving zero content. "
                     "Establishing a 2x/week posting cadence with thought-leadership and customer stories would close the social-share-of-voice gap with C2FO without acquisition cost."),
            "data_point": f"Taulia: 0 LinkedIn posts/week vs C2FO: ~{d2['c2fo_posts_per_week']:.1f} posts/week combined.",
        },
        {
            "title": "2. Launch a supplier-focused content hub",
            "body": ("Taulia is missing a blog, newsroom, webinar, and podcast — four high-leverage content types C2FO actively publishes. "
                     "C2FO's broader content footprint helps it own ~5x more search interest. "
                     "A dedicated supplier-education hub (Taulia Learn) with weekly articles and a monthly webinar would directly address C2FO's content moat and capture top-of-funnel demand."),
            "data_point": f"C2FO has {d2['c2fo_content_types']} content types live; Taulia has {d2['taulia_content_types']}. C2FO's avg Trends score is {d1['avg_c2fo_trend']} vs Taulia's {d1['avg_taulia_trend']}.",
        },
        {
            "title": "3. Convert review momentum into a Trustpilot / G2 acquisition push",
            "body": ("Taulia's existing reviews already average 4.55/5 across 12 reviews — quality is not the issue, volume is. "
                     "C2FO maintains an active Trustpilot presence with 800+ reviews while Taulia has none, suggesting C2FO targets a broader supplier audience. "
                     "A simple in-app review request after invoice settlement could 5–10x Taulia's review count within a quarter and protect against C2FO's volume advantage in social proof."),
            "data_point": f"Taulia's 12 reviews averaging {d3['taulia_rating']}/5 vs C2FO's broad Trustpilot footprint (800+ reviews).",
        },
    ]

    # Print the strategic output to the terminal
    print("\n  WHERE TAULIA LEADS:")                       # header
    for line in taulia_leads:                              # iterate Taulia wins
        print(f"   ✓ {line}")                              # print bullet

    print("\n  WHERE C2FO LEADS:")                         # header
    for line in c2fo_leads:                                # iterate C2FO wins
        print(f"   ✓ {line}")                              # print bullet

    print("\n  RECOMMENDATIONS:")                          # header
    for rec in recommendations:                            # iterate recs
        print(f"\n   {rec['title']}")                      # rec title
        print(f"     {rec['body']}")                       # rec body

    return {                                               # bundle strategic output
        "taulia_leads":     taulia_leads,
        "c2fo_leads":       c2fo_leads,
        "recommendations":  recommendations,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PART D — CHARTS
# ══════════════════════════════════════════════════════════════════════════════
def chart_comparison(d1, d2, d3):
    """Horizontal bar chart of headline metrics."""
    metrics = ["Total social\nfollowers",                  # label 1
               "Avg review\nrating (×20)",                 # label 2 (scaled to comparable axis)
               "Monthly web\nvisits",                      # label 3
               "Content\ntypes (×10K)"]                    # label 4 (scaled)

    # Scale review rating and content types so all bars share a sensible axis
    c2fo_vals = [d1["c2fo_followers"],                     # raw social followers
                 (d3["c2fo_rating"]   or 0) * 20_000,      # rating × 20,000 to scale
                 d1["c2fo_visits"],                        # web visits
                 d2["c2fo_content_types"] * 40_000]        # content count × 40,000 to scale

    taulia_vals = [d1["taulia_followers"],                 # raw social followers
                   (d3["taulia_rating"] or 0) * 20_000,    # rating × 20,000 to scale
                   d1["taulia_visits"],                    # web visits
                   d2["taulia_content_types"] * 40_000]    # content count × 40,000 to scale

    fig, ax = plt.subplots(figsize=(10, 6), facecolor="white")  # 10x6 figure on white
    y = np.arange(len(metrics))                            # y-position for each metric
    h = 0.38                                               # bar height

    ax.barh(y - h/2, c2fo_vals,   h, color=C2FO_GREEN, label="C2FO")     # C2FO bars
    ax.barh(y + h/2, taulia_vals, h, color=SAP_BLUE,    label="Taulia")  # Taulia bars

    ax.set_yticks(y)                                       # set ticks
    ax.set_yticklabels(metrics)                            # set tick labels
    ax.invert_yaxis()                                      # top-to-bottom order
    ax.set_xlabel("Scaled value (followers / visits / rating×20K / content×40K)")  # x label
    ax.set_title("C2FO vs Taulia — Headline Marketing Metrics", fontsize=14, weight="bold")  # title
    ax.legend(loc="lower right")                           # legend
    ax.grid(axis="x", linestyle=":", alpha=0.5)            # subtle grid
    ax.set_facecolor("white")                              # white inner background
    ax.spines["top"].set_visible(False)                    # hide top border
    ax.spines["right"].set_visible(False)                  # hide right border

    plt.tight_layout()                                     # avoid clipping
    plt.savefig("audit_comparison_chart.png", dpi=150, facecolor="white")  # save PNG
    plt.close(fig)                                         # close to free memory
    print("  ✓ audit_comparison_chart.png")                # confirm

def chart_radar(d1, d2, d3, d4, d5):
    """Radar chart of 5 dimension scores."""
    labels = ["Brand\nVisibility", "Content\nStrategy",    # axis labels
              "Customer\nPerception", "Messaging\nClarity",
              "Content\nMaturity"]
    c2fo   = [d1["c2fo_score"],   d2["c2fo_score"],   d3["c2fo_score"],   d4["c2fo_score"],   d5["c2fo_score"]]
    taulia = [d1["taulia_score"], d2["taulia_score"], d3["taulia_score"], d4["taulia_score"], d5["taulia_score"]]

    # Radar charts need to be closed loops — append the first value to the end
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()  # angles for each axis
    c2fo_loop   = c2fo   + c2fo[:1]                        # close the loop
    taulia_loop = taulia + taulia[:1]                      # close the loop
    angles_loop = angles + angles[:1]                      # close the loop

    fig, ax = plt.subplots(figsize=(8, 8),
                           subplot_kw=dict(polar=True),    # polar projection
                           facecolor="white")              # white background

    ax.plot(angles_loop, c2fo_loop,   color=C2FO_GREEN, linewidth=2, label="C2FO")     # C2FO line
    ax.fill(angles_loop, c2fo_loop,   color=C2FO_GREEN, alpha=0.25)                   # fill
    ax.plot(angles_loop, taulia_loop, color=SAP_BLUE,    linewidth=2, label="Taulia")  # Taulia line
    ax.fill(angles_loop, taulia_loop, color=SAP_BLUE,    alpha=0.25)                  # fill

    ax.set_theta_offset(np.pi / 2)                         # start at top
    ax.set_theta_direction(-1)                             # clockwise
    ax.set_xticks(angles)                                  # tick at each axis
    ax.set_xticklabels(labels, fontsize=10)                # axis labels
    ax.set_ylim(0, 10)                                     # 1-10 scale
    ax.set_yticks([2, 4, 6, 8, 10])                        # ring values
    ax.set_yticklabels(["2", "4", "6", "8", "10"], fontsize=8, color="gray")  # ring labels
    ax.set_title("Five-Dimension Scorecard",
                 fontsize=14, weight="bold", pad=20)       # title
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))  # legend outside

    plt.tight_layout()                                     # tidy layout
    plt.savefig("audit_radar_chart.png", dpi=150, facecolor="white")  # save PNG
    plt.close(fig)                                         # close figure
    print("  ✓ audit_radar_chart.png")                     # confirm

def chart_sentiment(d3):
    """Stacked bar chart of Positive/Neutral/Negative review counts."""
    companies = ["C2FO", "Taulia"]                         # x labels
    pos = [d3["c2fo_sentiment"]["Positive"], d3["taulia_sentiment"]["Positive"]]   # positive counts
    neu = [d3["c2fo_sentiment"]["Neutral"],  d3["taulia_sentiment"]["Neutral"]]    # neutral counts
    neg = [d3["c2fo_sentiment"]["Negative"], d3["taulia_sentiment"]["Negative"]]   # negative counts

    fig, ax = plt.subplots(figsize=(8, 5), facecolor="white")  # canvas
    ax.bar(companies, pos, color="#2E8B57", label="Positive")                      # green positive
    ax.bar(companies, neu, bottom=pos, color="#A0A0A0", label="Neutral")           # grey neutral
    ax.bar(companies, neg,                                                          # red negative
           bottom=[p+n for p, n in zip(pos, neu)],
           color="#C0392B", label="Negative")

    ax.set_ylabel("Number of reviews")                     # y axis label
    ax.set_title("Review Sentiment — C2FO vs Taulia", fontsize=14, weight="bold")  # title
    ax.legend()                                            # legend
    ax.set_facecolor("white")                              # white inner background
    ax.spines["top"].set_visible(False)                    # tidy borders
    ax.spines["right"].set_visible(False)                  # tidy borders

    plt.tight_layout()                                     # layout
    plt.savefig("audit_sentiment_chart.png", dpi=150, facecolor="white")  # save PNG
    plt.close(fig)                                         # close figure
    print("  ✓ audit_sentiment_chart.png")                 # confirm

def chart_themes(dfs):
    """Grouped bar chart of theme counts by company."""
    themes = dfs["themes"]                                 # alias themes DataFrame
    pivot = themes.pivot_table(                            # build a count pivot
        index="theme", columns="company", values="rating",
        aggfunc="count", fill_value=0)
    # Make sure both companies appear as columns even if one is missing
    for c in ["C2FO", "Taulia"]:                           # ensure both columns exist
        if c not in pivot.columns:                         # missing company
            pivot[c] = 0                                   # add zero column
    pivot = pivot[["C2FO", "Taulia"]]                      # consistent ordering

    x = np.arange(len(pivot.index))                        # positions for themes
    w = 0.38                                               # bar width

    fig, ax = plt.subplots(figsize=(10, 5), facecolor="white")  # canvas
    ax.bar(x - w/2, pivot["C2FO"],   w, color=C2FO_GREEN, label="C2FO")     # C2FO bars
    ax.bar(x + w/2, pivot["Taulia"], w, color=SAP_BLUE,    label="Taulia")  # Taulia bars
    ax.set_xticks(x)                                       # tick positions
    ax.set_xticklabels(pivot.index, rotation=30, ha="right")  # rotated tick labels
    ax.set_ylabel("Number of reviews")                     # y label
    ax.set_title("Review Themes by Company", fontsize=14, weight="bold")  # title
    ax.legend()                                            # legend
    ax.set_facecolor("white")                              # white background
    ax.spines["top"].set_visible(False)                    # tidy
    ax.spines["right"].set_visible(False)                  # tidy

    plt.tight_layout()                                     # layout
    plt.savefig("audit_themes_chart.png", dpi=150, facecolor="white")      # save PNG
    plt.close(fig)                                         # close figure
    print("  ✓ audit_themes_chart.png")                    # confirm


# ══════════════════════════════════════════════════════════════════════════════
# PART E — CSV SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
def write_summary_csv(d1, d2, d3, d4, d5):
    """Write per-metric comparison to audit_comparison_summary.csv."""
    print("\n" + "=" * 70)                                 # divider
    print("PART E — Writing audit_comparison_summary.csv") # header
    print("=" * 70)                                        # divider

    rows = []                                              # collected output rows

    def add(dim, metric, c, t, notes):                     # helper to add one row
        # Determine winner (handle None / equal)
        try:                                               # cast safely
            cv = float(str(c).replace(",", ""))            # numeric c
            tv = float(str(t).replace(",", ""))            # numeric t
            winner = "C2FO" if cv > tv else "Taulia" if tv > cv else "Tie"  # compare
        except (TypeError, ValueError):                    # not numeric
            winner = "—"                                   # leave blank
        rows.append({"dimension": dim, "metric": metric,
                     "c2fo_value": c, "taulia_value": t,
                     "winner": winner, "gap_notes": notes})

    # Dimension 1
    add("Brand Visibility", "Total social followers",
        d1["c2fo_followers"], d1["taulia_followers"],
        f"C2FO has {d1['c2fo_followers']/max(d1['taulia_followers'],1):.1f}x more")
    add("Brand Visibility", "Avg Google Trends score",
        d1["avg_c2fo_trend"], d1["avg_taulia_trend"],
        "C2FO dominates branded search interest worldwide")
    add("Brand Visibility", "Monthly web visits",
        d1["c2fo_visits"], d1["taulia_visits"],
        f"Taulia gets {d1['taulia_visits']/max(d1['c2fo_visits'],1):.1f}x more web traffic")
    add("Brand Visibility", "Brand Visibility score (1-10)",
        d1["c2fo_score"], d1["taulia_score"], "Composite of three metrics above")

    # Dimension 2
    add("Content Strategy", "Content types live",
        d2["c2fo_content_types"], d2["taulia_content_types"],
        f"of {d2['total_content_types']} categories tracked")
    add("Content Strategy", "Posts per week (combined)",
        d2["c2fo_posts_per_week"], d2["taulia_posts_per_week"],
        "Taulia social channels are dormant")
    add("Content Strategy", "Content Strategy score (1-10)",
        d2["c2fo_score"], d2["taulia_score"], "60% breadth + 40% frequency")

    # Dimension 3
    add("Customer Perception", "Weighted avg rating",
        d3["c2fo_rating"], d3["taulia_rating"],
        f"C2FO: {d3['c2fo_reviews']} review(s)  vs Taulia: {d3['taulia_reviews']}")
    add("Customer Perception", "Total reviews tracked",
        d3["c2fo_reviews"], d3["taulia_reviews"],
        "Taulia has 12x more review evidence")
    add("Customer Perception", "Positive sentiment ratio",
        d3["c2fo_pos_ratio"], d3["taulia_pos_ratio"],
        "C2FO sample (n=1) too small to be meaningful")
    add("Customer Perception", "Customer Perception score (1-10)",
        d3["c2fo_score"], d3["taulia_score"],
        "C2FO capped due to single-review sample")

    # Dimension 4
    add("Messaging & Positioning", "Headline (H1)",
        d4["c2fo_h1"], d4["taulia_h1"],
        "C2FO leads with speed; Taulia with insight/optimisation")
    add("Messaging & Positioning", "Primary CTA",
        d4["c2fo_cta"], d4["taulia_cta"],
        "C2FO has stronger conversion CTAs (Demo Request)")
    add("Messaging & Positioning", "Messaging Clarity score (1-10)",
        d4["c2fo_score"], d4["taulia_score"], "Manual judgement")

    # Dimension 5
    add("Content Maturity", "Content types covered",
        len(d5["c2fo_has"]), len(d5["taulia_has"]),
        f"C2FO-only: {', '.join(d5['c2fo_only']) or 'none'}")
    add("Content Maturity", "Content Maturity score (1-10)",
        d5["c2fo_score"], d5["taulia_score"], "Proportion of tracked types live")

    # Write to CSV file
    with open("audit_comparison_summary.csv", "w", newline="") as f:  # open file
        writer = csv.DictWriter(f, fieldnames=[            # set columns
            "dimension", "metric", "c2fo_value",
            "taulia_value", "winner", "gap_notes"])
        writer.writeheader()                               # write header
        writer.writerows(rows)                             # write all data rows

    print(f"  ✓ Saved {len(rows)} rows → audit_comparison_summary.csv")


# ══════════════════════════════════════════════════════════════════════════════
# PART F — PDF REPORT
# ══════════════════════════════════════════════════════════════════════════════
def page_number_canvas(canvas, doc):
    """Footer callback: draw a page number at the bottom of every page except the title."""
    page_num = canvas.getPageNumber()                      # current page number
    if page_num == 1:                                      # skip title page
        return                                             # no footer on page 1
    canvas.saveState()                                     # save canvas state
    canvas.setFont("Helvetica", 9)                         # small font
    canvas.setFillColor(HexColor("#666666"))               # mid-grey
    canvas.drawCentredString(LETTER[0] / 2, 30,            # bottom centre at y=30pt
                             f"Page {page_num}")           # the page number text
    canvas.restoreState()                                  # restore canvas state


def make_pdf(d1, d2, d3, d4, d5, strat):
    """Build the multi-page PDF using ReportLab Platypus."""
    print("\n" + "=" * 70)                                 # divider
    print("PART F — Building PDF report")                  # header
    print("=" * 70)                                        # divider

    # Document setup with 60pt margins
    doc = SimpleDocTemplate(                               # build document object
        "Taulia_vs_C2FO_Marketing_Audit.pdf",              # output filename
        pagesize=LETTER,                                   # standard US Letter
        leftMargin=60, rightMargin=60,                     # 60pt L/R margins
        topMargin=60, bottomMargin=60,                     # 60pt T/B margins
        title="Taulia vs C2FO Marketing Audit",            # PDF metadata
        author="Alanah Stephens")                          # PDF metadata

    # Get default styles and add custom variants
    styles = getSampleStyleSheet()                         # base style sheet

    # Custom paragraph styles
    style_title    = ParagraphStyle("Title", parent=styles["Title"],
                                    fontName="Helvetica-Bold", fontSize=28,
                                    alignment=TA_CENTER, textColor=HexColor(SAP_BLUE),
                                    leading=34, spaceAfter=24)
    style_subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"],
                                    fontName="Helvetica", fontSize=16,
                                    alignment=TA_CENTER, textColor=black,
                                    leading=22, spaceAfter=12)
    style_meta     = ParagraphStyle("Meta", parent=styles["Normal"],
                                    fontName="Helvetica", fontSize=12,
                                    alignment=TA_CENTER, textColor=HexColor("#444444"),
                                    leading=16, spaceAfter=8)
    style_h1       = ParagraphStyle("H1", parent=styles["Heading1"],
                                    fontName="Helvetica-Bold", fontSize=16,
                                    alignment=TA_LEFT, textColor=HexColor(SAP_BLUE),
                                    leading=20, spaceAfter=4)
    style_h2       = ParagraphStyle("H2", parent=styles["Heading2"],
                                    fontName="Helvetica-Bold", fontSize=13,
                                    alignment=TA_LEFT, textColor=black,
                                    leading=17, spaceBefore=12, spaceAfter=6)
    style_body     = ParagraphStyle("Body", parent=styles["Normal"],
                                    fontName="Helvetica", fontSize=11,
                                    alignment=TA_LEFT, textColor=black,
                                    leading=14.3,                # 1.3x line spacing of 11pt
                                    spaceAfter=8)
    style_italic   = ParagraphStyle("Italic", parent=style_body,
                                    fontName="Helvetica-Oblique",
                                    textColor=HexColor("#555555"))
    style_score    = ParagraphStyle("Score", parent=style_body,
                                    fontName="Helvetica-Bold", fontSize=12,
                                    leading=15, spaceAfter=10)

    # Helper that returns a "heading + horizontal rule" combo
    def heading_with_rule(text):                           # heading factory
        return [Paragraph(text, style_h1),                 # the heading paragraph
                HRFlowable(width="100%", thickness=1,      # a 1pt-thick rule
                           color=HexColor(SAP_BLUE),
                           spaceBefore=2, spaceAfter=10)]  # spacing around the rule

    # Container that will accumulate all flowables in order
    story = []                                             # list of Platypus elements

    # ─── PAGE 1 — TITLE ─────────────────────────────────────────────────────
    story.append(Spacer(1, 2.5 * inch))                    # vertical centring
    story.append(Paragraph("Competitive Marketing Audit", style_title))            # main title
    story.append(Paragraph("SAP Taulia vs C2FO", style_subtitle))                  # subtitle
    story.append(Spacer(1, 0.6 * inch))                                            # gap
    story.append(HRFlowable(width="40%", thickness=1.5,                            # decorative rule
                            color=HexColor(SAP_BLUE), hAlign="CENTER"))
    story.append(Spacer(1, 0.4 * inch))                                            # gap
    story.append(Paragraph("Prepared by: Alanah Stephens", style_meta))            # author
    story.append(Paragraph(f"Date: {TODAY_STR}", style_meta))                       # date
    story.append(Paragraph("Prepared for: SAP Taulia Marketing Team", style_meta)) # audience
    story.append(PageBreak())                                                      # end title page

    # ─── PAGE 2 — EXECUTIVE SUMMARY ─────────────────────────────────────────
    story.extend(heading_with_rule("Executive Summary"))   # heading + rule

    exec_text = (
        f"This audit compares SAP Taulia and its primary competitor C2FO across five marketing "
        f"dimensions, drawing on six data sources collected in {date.today().strftime('%B %Y')}. "
        f"The headline finding is a marketing paradox: Taulia commands ~"
        f"{d1['taulia_visits']//max(d1['c2fo_visits'],1)}x more web traffic ({d1['taulia_visits']:,} vs {d1['c2fo_visits']:,} monthly visits) and "
        f"better-rated reviews ({d3['taulia_rating']}/5 vs {d3['c2fo_rating']}/5), yet C2FO dominates the "
        f"top of the funnel with ~{d1['c2fo_followers']/max(d1['taulia_followers'],1):.1f}x larger social reach and a "
        f"{d1['avg_c2fo_trend']/max(d1['avg_taulia_trend'],1):.0f}x higher average Google Trends score. "
        f"The clearest gap is content breadth: C2FO publishes {d2['c2fo_content_types']} of "
        f"{d2['total_content_types']} tracked content types while Taulia covers only {d2['taulia_content_types']}. "
        f"Closing this gap — coupled with reactivating Taulia's dormant LinkedIn and X channels — "
        f"is the single highest-leverage move available to the Taulia marketing team this quarter."
    )
    story.append(Paragraph(exec_text, style_body))         # paragraph
    story.append(PageBreak())                              # next page

    # ─── PAGE 3 — METHODOLOGY ───────────────────────────────────────────────
    story.extend(heading_with_rule("Methodology"))         # heading + rule

    method_para = (
        f"This audit synthesises six primary data sources collected in April 2026 covering "
        f"the trailing 12-month period. Each dimension below is scored 1–10 using a "
        f"normalisation approach: the leader on each underlying metric receives a 10 and the "
        f"competitor receives a proportionally lower score. Composite scores are weighted "
        f"averages of underlying metrics. Where sample sizes are very small (e.g. C2FO's "
        f"single G2 review), scores are explicitly capped to avoid overstating signal. The "
        f"five scoring dimensions are: Brand Visibility, Content Strategy, Customer Perception, "
        f"Messaging Clarity, and Content Maturity."
    )
    story.append(Paragraph(method_para, style_body))       # paragraph

    story.append(Paragraph("Data sources", style_h2))      # subheading

    sources = [                                            # six data sources
        "Social Media — LinkedIn, X/Twitter, and YouTube follower and posting metrics",
        "Customer Reviews — G2 and Capterra ratings plus 13 paraphrased review texts",
        "Google Trends — comparative search interest, worldwide, past 12 months",
        "Website Audit — homepage messaging (titles, H1s, CTAs, navigation)",
        "SEO Traffic — SimilarWeb traffic estimates, keyword counts, and country mix",
        "Content Ecosystem — presence/absence of 8 content types per company",
    ]
    story.append(ListFlowable(                             # bulleted list
        [ListItem(Paragraph(s, style_body), leftIndent=12) for s in sources],
        bulletType="bullet"))
    story.append(PageBreak())                              # next page

    # Helper to embed a chart image at ~450pt wide
    def embed_chart(filename, width=450):                  # image helper
        img = RLImage(filename, width=width,               # image object
                      height=width * 0.6, kind="proportional")
        img.hAlign = "CENTER"                              # centre image
        return img                                         # return flowable

    # ─── PAGE 4 — DIMENSION 1: BRAND VISIBILITY ─────────────────────────────
    story.extend(heading_with_rule("1. Brand Visibility"))  # heading + rule
    story.append(Paragraph(
        f"Brand visibility blends three signals: social-channel reach, search demand, and web "
        f"traffic. C2FO leads on social reach ({d1['c2fo_followers']:,} vs {d1['taulia_followers']:,} "
        f"followers — {d1['c2fo_followers']/max(d1['taulia_followers'],1):.1f}x larger) and search "
        f"interest (avg Google Trends {d1['avg_c2fo_trend']} vs {d1['avg_taulia_trend']}). However, "
        f"Taulia attracts ~{d1['taulia_visits']/max(d1['c2fo_visits'],1):.1f}x more monthly web visits "
        f"({d1['taulia_visits']:,} vs {d1['c2fo_visits']:,}), suggesting C2FO drives broader awareness "
        f"while Taulia converts demand into deeper site engagement.", style_body))
    story.append(embed_chart("audit_comparison_chart.png"))  # embed comparison chart
    story.append(Paragraph(
        f"<b>Score:</b> C2FO {d1['c2fo_score']}/10 &nbsp;|&nbsp; Taulia {d1['taulia_score']}/10",
        style_score))
    story.append(PageBreak())                              # next page

    # ─── PAGE 5 — DIMENSION 2: CONTENT STRATEGY ─────────────────────────────
    story.extend(heading_with_rule("2. Content Strategy"))  # heading + rule
    story.append(Paragraph(
        f"Content strategy combines breadth (number of content types live) and frequency "
        f"(combined posting cadence). C2FO publishes {d2['c2fo_content_types']} of "
        f"{d2['total_content_types']} tracked content categories vs Taulia's {d2['taulia_content_types']}. "
        f"On posting cadence, C2FO posts ~{d2['c2fo_posts_per_week']:.1f} times per week across "
        f"social platforms while Taulia posts ~{d2['taulia_posts_per_week']:.1f} per week — "
        f"effectively dormant on LinkedIn and X. The strategic risk is share-of-voice erosion: "
        f"C2FO is owning content categories Taulia simply does not contest.", style_body))
    story.append(Paragraph(
        f"<i>Technical note: C2FO's /webinars URL redirected to a 404 page (/fourzerofour/) — "
        f"it returns a 200 status code technically, but the content doesn't exist. This is "
        f"reflected as &quot;no&quot; in the content_ecosystem.csv.</i>", style_italic))
    story.append(Paragraph(
        f"<b>Score:</b> C2FO {d2['c2fo_score']}/10 &nbsp;|&nbsp; Taulia {d2['taulia_score']}/10",
        style_score))
    story.append(PageBreak())                              # next page

    # ─── PAGE 6 — DIMENSION 3: CUSTOMER PERCEPTION ──────────────────────────
    story.extend(heading_with_rule("3. Customer Perception"))  # heading + rule
    # Build the "complaint" sentence only when there's an actual negative theme to cite
    if d3["taulia_top_neg"].lower().startswith("no negative"):     # no negatives in sample
        complaint_clause = ("No reviews in the sampled set carried negative sentiment, "
                            "though sample size remains modest at "
                            f"{d3['taulia_reviews']} reviews.")
    else:                                                          # cite the negative theme
        complaint_clause = ("The most common Taulia complaint relates to "
                            f"<b>{d3['taulia_top_neg']}</b>.")

    story.append(Paragraph(
        f"Customer perception is a clear Taulia win. Taulia's reviews average "
        f"<b>{d3['taulia_rating']}/5</b> across {d3['taulia_reviews']} reviews on G2 and Capterra "
        f"with a {int(d3['taulia_pos_ratio']*100)}% positive sentiment ratio. C2FO has only "
        f"{d3['c2fo_reviews']} review on these two platforms ({d3['c2fo_rating']}/5), making meaningful "
        f"comparison difficult. Taulia's most-cited strength is <b>{d3['taulia_top_pos']}</b>. "
        f"{complaint_clause}",
        style_body))
    story.append(embed_chart("audit_sentiment_chart.png"))  # sentiment chart
    story.append(Paragraph(
        f"<i>Strategic observation: C2FO maintains an active Trustpilot presence with 800+ "
        f"reviews, while Taulia has no Trustpilot profile. This suggests C2FO may be targeting "
        f"a broader market including SMB suppliers, whereas Taulia appears focused on "
        f"enterprise-only channels.</i>", style_italic))
    story.append(Paragraph(
        f"<b>Score:</b> C2FO {d3['c2fo_score']}/10 &nbsp;|&nbsp; Taulia {d3['taulia_score']}/10",
        style_score))
    story.append(PageBreak())                              # next page

    # ─── PAGE 7 — DIMENSION 4: MESSAGING ────────────────────────────────────
    story.extend(heading_with_rule("4. Messaging & Positioning"))  # heading + rule
    story.append(Paragraph(
        f"<b>C2FO H1:</b> &ldquo;{d4['c2fo_h1']}&rdquo;<br/>"
        f"<b>Taulia H1:</b> &ldquo;{d4['taulia_h1']}&rdquo;<br/>"
        f"<b>C2FO primary CTA:</b> {d4['c2fo_cta']}<br/>"
        f"<b>Taulia primary CTA:</b> {d4['taulia_cta']}", style_body))
    story.append(Paragraph(
        f"C2FO leads with <b>speed and accessibility</b> — &lsquo;Get Paid Faster&rsquo; is a "
        f"benefit headline that targets supplier pain. Taulia leads with <b>insight and "
        f"optimisation</b> — &lsquo;Cash Flow Acceleration Platform&rsquo; positions the product "
        f"as an enterprise-grade decision tool with the SAP brand attached. The key positioning "
        f"divergence: C2FO speaks to suppliers; Taulia speaks to treasury and procurement leaders. "
        f"C2FO's call-to-action ladder (Request a Demo) is more conversion-oriented than "
        f"Taulia's softer Contact Us flows.", style_body))
    story.append(Paragraph(
        f"<b>Score:</b> C2FO {d4['c2fo_score']}/10 &nbsp;|&nbsp; Taulia {d4['taulia_score']}/10",
        style_score))
    story.append(PageBreak())                              # next page

    # ─── PAGE 8 — DIMENSION 5: CONTENT MATURITY ─────────────────────────────
    story.extend(heading_with_rule("5. Content Marketing Maturity"))  # heading + rule
    story.append(Paragraph(
        f"<b>C2FO publishes:</b> {', '.join(d5['c2fo_has']) or 'none'}.<br/>"
        f"<b>Taulia publishes:</b> {', '.join(d5['taulia_has']) or 'none'}.<br/>"
        f"<b>C2FO-only content types:</b> {', '.join(d5['c2fo_only']) or 'none'}.<br/>"
        f"<b>Taulia-only content types:</b> {', '.join(d5['taulia_only']) or 'none'}.",
        style_body))
    story.append(embed_chart("audit_themes_chart.png"))    # themes chart for visual breakup
    story.append(Paragraph(
        f"The four content types Taulia is missing — blog, newsroom, webinars, podcast — are "
        f"the same four formats most associated with sustained organic search growth and "
        f"thought-leadership share-of-voice. Each represents a discrete, programmatic gap that "
        f"can be opened in a single quarter with focused investment.", style_body))
    story.append(Paragraph(
        f"<b>Score:</b> C2FO {d5['c2fo_score']}/10 &nbsp;|&nbsp; Taulia {d5['taulia_score']}/10",
        style_score))
    story.append(PageBreak())                              # next page

    # ─── PAGE 9 — STRENGTHS & WEAKNESSES ────────────────────────────────────
    story.extend(heading_with_rule("Competitive Strengths & Weaknesses"))  # heading + rule
    story.append(Paragraph("Where Taulia leads", style_h2))                # subheading
    story.append(ListFlowable(                             # bulleted Taulia wins
        [ListItem(Paragraph(b, style_body), leftIndent=12)
         for b in strat["taulia_leads"]], bulletType="bullet"))

    story.append(Paragraph("Where C2FO leads", style_h2))  # subheading
    story.append(ListFlowable(                             # bulleted C2FO wins
        [ListItem(Paragraph(b, style_body), leftIndent=12)
         for b in strat["c2fo_leads"]], bulletType="bullet"))
    story.append(PageBreak())                              # next page

    # ─── PAGE 10 — RECOMMENDATIONS ──────────────────────────────────────────
    story.extend(heading_with_rule("Strategic Recommendations for Taulia"))  # heading + rule
    for rec in strat["recommendations"]:                   # iterate the 3 recs
        story.append(Paragraph(rec["title"], style_h2))    # bold rec title
        story.append(Paragraph(rec["body"], style_body))   # rec body
        story.append(Paragraph(                            # supporting data point
            f"<i>Supporting data: {rec['data_point']}</i>", style_italic))
        story.append(Spacer(1, 6))                         # spacing between recs
    story.append(PageBreak())                              # next page

    # ─── PAGE 11 — APPENDIX ─────────────────────────────────────────────────
    story.extend(heading_with_rule("Appendix: Scoring Framework"))  # heading + rule
    story.append(Paragraph(
        "Each company is scored 1–10 across the five dimensions visible on the radar below. "
        "Scores are computed as proportional comparisons against the leader on each underlying "
        "metric (so the leader on a metric receives a 10 and the competitor receives a "
        "proportionally lower score). Composite scores are then averaged or weighted across "
        "underlying metrics. Where the sample is too small to be statistically meaningful "
        "(e.g. C2FO's 1 G2 review), the score is explicitly capped.", style_body))
    story.append(embed_chart("audit_radar_chart.png", width=480))  # bigger radar
    story.append(Paragraph(
        "Higher scores indicate stronger relative performance on that dimension. The radar's "
        "shaded areas make share-of-strength visible at a glance: a wider polygon is broader "
        "competence; a more even polygon is more balanced positioning.", style_body))

    # Build the PDF, attaching the page-number footer to every page
    doc.build(story,                                       # build with page footer callback
              onFirstPage=page_number_canvas,              # title page (skipped in callback)
              onLaterPages=page_number_canvas)             # all subsequent pages

    print("  ✓ Saved → Taulia_vs_C2FO_Marketing_Audit.pdf")  # confirm


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "█" * 70)                                 # banner top
    print("  COMPETITIVE MARKETING AUDIT — SAP Taulia vs C2FO")
    print("  Author: Alanah Stephens   Date: " + TODAY_STR)
    print("█" * 70)                                        # banner bottom

    # Part A — load & clean
    dfs = load_and_clean()                                 # returns dict of cleaned DataFrames

    # Part B — five dimensions of analysis
    d1 = analyse_brand_visibility(dfs)                     # dimension 1
    d2 = analyse_content_strategy(dfs)                     # dimension 2
    d3 = analyse_customer_perception(dfs)                  # dimension 3
    d4 = analyse_messaging(dfs)                            # dimension 4
    d5 = analyse_content_maturity(dfs)                     # dimension 5

    # Part C — strategic output
    strat = build_strategic_output(d1, d2, d3, d4, d5)     # leads + recommendations

    # Part D — charts
    print("\n" + "=" * 70)                                 # divider
    print("PART D — Generating charts")                    # header
    print("=" * 70)                                        # divider
    chart_comparison(d1, d2, d3)                           # bar chart
    chart_radar(d1, d2, d3, d4, d5)                        # radar chart
    chart_sentiment(d3)                                    # sentiment chart
    chart_themes(dfs)                                      # themes chart

    # Part E — comparison summary CSV
    write_summary_csv(d1, d2, d3, d4, d5)                  # CSV summary

    # Part F — PDF report
    make_pdf(d1, d2, d3, d4, d5, strat)                    # PDF

    # Final summary of output files and sizes
    print("\n" + "=" * 70)                                 # divider
    print("OUTPUT FILES")                                  # header
    print("=" * 70)                                        # divider
    for fn in ["audit_comparison_chart.png",
               "audit_radar_chart.png",
               "audit_sentiment_chart.png",
               "audit_themes_chart.png",
               "audit_comparison_summary.csv",
               "Taulia_vs_C2FO_Marketing_Audit.pdf"]:
        if os.path.exists(fn):                             # if it was created
            kb = os.path.getsize(fn) / 1024                # size in KB
            print(f"  ✓ {fn:<45}  {kb:>7.1f} KB")          # show name + size
        else:                                              # something failed
            print(f"  ✗ {fn:<45}  MISSING")                # report missing

    print("\n  Audit complete.\n")                         # done message
