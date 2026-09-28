#!/usr/bin/env python3
"""
Digital Footprint Scanner
=========================
Scans a Gmail mailbox (read-only) for account-related emails (welcome,
verify, subscription, ...) and lists the services that sent them, grouped
by category, with email counts and first/last seen dates.

Nothing is modified or stored: mail is opened read-only, only the From and
Date headers are fetched, and credentials are never written to disk.

Usage:
    python footprint_scanner.py                      # Inbox, all matches
    python footprint_scanner.py --all-mail           # search All Mail
    python footprint_scanner.py --limit 500          # newest 500 matches only
    python footprint_scanner.py --csv footprint.csv  # also export to CSV

Credentials come from GMAIL_USER / GMAIL_APP_PASSWORD environment variables,
or you are prompted (password input is hidden).
"""

import argparse
import csv
import email
import getpass
import imaplib
import os
import re
import sys
from datetime import timezone
from email.utils import parseaddr, parsedate_to_datetime

# --- CONFIGURATION ---
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BATCH_SIZE = 200

# Subject keywords that usually indicate you signed up for something
SUBJECT_KEYWORDS = [
    "welcome",
    "verify",
    "confirm your",
    "subscription",
    "your account",
    "activate",
    "registration",
]

# --- CATEGORY MAP ---
# Checked top to bottom; the first match wins.
# A keyword matches the domain's main name (the "netflix" in netflix.com)
# exactly, or as a substring if the keyword is 6+ characters long.
# Add your own keywords freely.
CATEGORY_KEYWORDS = {
    "Email & Marketing Services": [
        "amazonses", "sendgrid", "mailchimp", "mailgun", "mandrillapp",
        "sparkpost", "postmarkapp", "mcsv", "rsgsv", "klaviyo",
        "constantcontact", "hubspotemail",
    ],
    "Food & Drinks": [
        "zomato", "swiggy", "ubereats", "starbucks", "dominos", "grubhub",
        "doordash", "mcdonalds", "kfc", "pizzahut", "zepto", "blinkit",
        "bigbasket", "dunzo",
    ],
    "Entertainment & Movies": [
        "netflix", "spotify", "disney", "primevideo", "hulu", "youtube",
        "hotstar", "bookmyshow", "a24films", "audius", "twitch",
        "crunchyroll", "sonyliv", "zee5", "jiocinema", "imdb", "letterboxd",
    ],
    "Gaming": [
        "steam", "steampowered", "epicgames", "playstation", "xbox",
        "nintendo", "riotgames", "ubisoft", "roblox", "itch", "blizzard", "ea",
    ],
    "Sports & Fitness": [
        "nike", "strava", "espn", "adidas", "fitbit", "cultfit", "cult",
        "decathlon", "myfitnesspal", "garmin", "peloton",
    ],
    "Shopping & E-commerce": [
        "amazon", "ebay", "walmart", "aliexpress", "flipkart", "myntra",
        "meesho", "nykaa", "ajio", "etsy", "shopify", "alibaba", "snapdeal",
        "tatacliq",
    ],
    "Finance & Banking": [
        "paypal", "stripe", "chase", "revolut", "paytm", "phonepe",
        "razorpay", "acko", "hdfcbank", "icicibank", "sbi", "axisbank",
        "kotak", "zerodha", "groww", "wise", "camsonline", "cred", "upstox",
        "cashfree",
    ],
    "Crypto & Web3": [
        "binance", "coinbase", "bscscan", "etherscan", "alchemy", "metamask",
        "opensea", "kraken", "wazirx", "coindcx", "coingecko",
        "coinmarketcap", "ledger", "trustwallet", "infura", "moralis",
        "arcx", "polygon", "uniswap", "bybit",
    ],
    "AI Tools": [
        "anthropic", "claude", "openai", "chatgpt", "character", "blackbox",
        "perplexity", "midjourney", "huggingface", "replicate", "cohere",
        "mistral", "poe", "deepseek", "groq", "elevenlabs", "runwayml",
        "openrouter",
    ],
    "Cybersecurity & CTF": [
        "censys", "zoomeye", "shodan", "tryhackme", "hackthebox",
        "blueteamlabs", "bufferctf", "cipcyber", "hackerone", "bugcrowd",
        "virustotal", "portswigger", "immunefi", "cybrary", "offsec",
        "ctftime",
    ],
    "Developer Tools & APIs": [
        "github", "gitlab", "bitbucket", "stackoverflow", "npmjs", "docker",
        "vercel", "netlify", "heroku", "digitalocean", "cloudflare", "apify",
        "apilayer", "bubble", "postman", "replit", "codepen", "jetbrains",
        "hackerrank", "leetcode", "codeforces", "kaggle", "auth0", "auth0user", "twilio",
        "firebase", "supabase", "mongodb", "sentry", "rapidapi", "ngrok",
    ],
    "Hosting & Domains": [
        "000webhost", "alwaysdata", "hostinger", "godaddy", "namecheap",
        "bluehost", "siteground", "hostgator", "infinityfree", "freenom",
        "wix", "squarespace", "wordpress",
    ],
    "Education & Learning": [
        "alison", "brilliant", "classcentral", "cambly", "brightspace",
        "coursera", "udemy", "edx", "khanacademy", "duolingo", "byjus",
        "unacademy", "skillshare", "udacity", "academia", "nptel", "swayam",
        "quizlet",
    ],
    "Jobs & Careers": [
        "ambitionbox", "careerflow", "naukri", "indeed", "glassdoor",
        "linkedin", "foundit", "wellfound", "angellist", "upwork", "fiverr",
        "internshala", "accenture", "cognizant", "infosys", "wipro",
    ],
    "Social, Dating & Media": [
        "bumble", "tinder", "hinge", "blogger", "twitter", "facebook",
        "instagram", "reddit", "pinterest", "discord", "telegram", "medium",
        "quora", "snapchat", "tumblr", "whatsapp", "substack", "mastodon",
    ],
    "Health & Wellness": [
        "betterhelp", "calm", "headspace", "practo", "curefit", "1mg",
        "pharmeasy", "healthify", "lybrate", "noom",
    ],
    "Design & Creative": [
        "canva", "adobesign", "adobe", "autodesk", "beautiful", "figma",
        "dribbble", "behance", "unsplash", "freepik", "envato",
    ],
    "Travel & Transport": [
        "makemytrip", "goibibo", "airbnb", "booking", "uber", "olacabs",
        "irctc", "redbus", "cleartrip", "expedia", "skyscanner", "agoda",
        "goindigo", "airindia", "rapido",
    ],
    "Tech & Productivity": [
        "google", "microsoft", "notion", "slack", "zoom", "dropbox",
        "atlassian", "arc", "cisco", "brighttalk", "trello", "asana",
        "evernote", "todoist", "grammarly", "lastpass", "1password",
        "bitwarden", "apple", "samsung", "mozilla", "opera",
    ],
}
UNCATEGORIZED = "Uncategorized / Miscellaneous"

# Optional: better domain parsing (handles amazon.co.uk, flipkart.co.in, ...)
try:
    import tldextract

    # suffix_list_urls=() -> use the bundled snapshot, no network fetch
    _extract = tldextract.TLDExtract(suffix_list_urls=())
except ImportError:
    _extract = None

# Fallback for common two-part suffixes when tldextract isn't installed
_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu"}


def registered_domain(host):
    """Return the registered domain, e.g. 'mail.netflix.com' -> 'netflix.com'."""
    host = host.lower().strip().strip(">")
    if _extract:
        ext = _extract(host)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        return host
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in _SECOND_LEVEL and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    if len(parts) > 2:
        return ".".join(parts[-2:])
    return host


def sender_domain(from_header):
    """Extract the registered domain from a raw From header."""
    _, addr = parseaddr(from_header)
    match = re.search(r"@([\w.\-]+)$", addr)
    if not match:
        return None
    return registered_domain(match.group(1))


def parse_date(value):
    """Parse an email Date header into an aware UTC datetime (or None)."""
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(str(value))
    except (TypeError, ValueError, IndexError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def keyword_matches(keyword, name):
    """Exact match on the domain name, or substring for longer keywords."""
    if name == keyword:
        return True
    return len(keyword) >= 6 and keyword in name


def get_category(domain):
    name = domain.lower().split(".")[0] if domain else ""
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword_matches(k, name) for k in keywords):
            return category
    return UNCATEGORIZED


def build_search_query(keywords):
    """Build a valid IMAP OR-chain: OR takes exactly two operands."""
    terms = [f'SUBJECT "{k}"' for k in keywords]
    query = terms[0]
    for term in terms[1:]:
        query = f"OR {query} {term}"
    return f"({query})"


def record(stats, from_header, date_header):
    """Add one email to the per-domain stats."""
    dom = sender_domain(from_header)
    if not dom:
        return
    entry = stats.setdefault(dom, {"count": 0, "first": None, "last": None})
    entry["count"] += 1
    dt = parse_date(date_header)
    if dt:
        if entry["first"] is None or dt < entry["first"]:
            entry["first"] = dt
        if entry["last"] is None or dt > entry["last"]:
            entry["last"] = dt


def scan(user, password, folder, limit):
    print("🔄 Connecting to mailbox...")
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(user, password)
    except imaplib.IMAP4.error as e:
        sys.exit(f"❌ Login failed: {e}\n   Use a Gmail App Password and make sure IMAP is enabled.")
    except OSError as e:
        sys.exit(f"❌ Could not reach {IMAP_SERVER}: {e}")

    stats = {}
    try:
        status, _ = mail.select(folder, readonly=True)  # readonly: never changes mail state
        if status != "OK":
            sys.exit(f"❌ Could not open folder {folder}")

        query = build_search_query(SUBJECT_KEYWORDS)
        print(f"🔍 Searching {folder} for account emails (this might take a moment)...")
        status, data = mail.search(None, query)
        if status != "OK":
            sys.exit("❌ Error searching emails.")

        ids = data[0].split()
        print(f"📋 Found {len(ids)} potential emails.")
        if limit:
            ids = ids[-limit:]
            print(f"   Analyzing the most recent {len(ids)}.")

        for start in range(0, len(ids), BATCH_SIZE):
            batch = ids[start:start + BATCH_SIZE]
            # PEEK avoids setting the \Seen flag
            status, msg_data = mail.fetch(
                b",".join(batch), "(BODY.PEEK[HEADER.FIELDS (FROM DATE)])"
            )
            if status != "OK":
                continue
            for part in msg_data:
                if isinstance(part, tuple):
                    msg = email.message_from_bytes(part[1])
                    from_header = msg.get("From")
                    if from_header:
                        record(stats, str(from_header), msg.get("Date"))
            print(f"   ...processed {min(start + BATCH_SIZE, len(ids))}/{len(ids)}")
    finally:
        try:
            mail.logout()
        except Exception:
            pass

    return stats


def group_by_category(stats):
    """Return {category: [(domain, entry), ...]} sorted by email count (desc)."""
    grouped = {cat: [] for cat in CATEGORY_KEYWORDS}
    grouped[UNCATEGORIZED] = []
    for dom, entry in stats.items():
        grouped[get_category(dom)].append((dom, entry))
    for items in grouped.values():
        items.sort(key=lambda x: (-x[1]["count"], x[0]))
    return grouped


def date_range(entry):
    if entry["first"] and entry["last"]:
        return f"{entry['first']:%Y-%m} → {entry['last']:%Y-%m}"
    return ""


def print_report(stats):
    grouped = group_by_category(stats)

    print("\n" + "=" * 44)
    print("🎯 YOUR DIGITAL FOOTPRINT REPORT")
    print("=" * 44)
    for category, items in grouped.items():
        if not items:
            continue
        print(f"\n📂 {category} ({len(items)}):")
        for dom, entry in items:
            n = entry["count"]
            rng = date_range(entry)
            extra = f", {rng}" if rng else ""
            print(f"  • {dom}  ({n} email{'s' if n != 1 else ''}{extra})")

    print("\n" + "-" * 44)
    print("SUMMARY")
    for category, items in grouped.items():
        if items:
            print(f"  {category}: {len(items)}")
    print(f"  Total unique senders: {len(stats)}")
    print("\nNote: senders are not always accounts (newsletters and promos also match).")


def export_csv(stats, path):
    grouped = group_by_category(stats)
    # utf-8-sig so Excel opens it correctly
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "category", "email_count", "first_seen", "last_seen"])
        for category, items in grouped.items():
            for dom, entry in items:
                writer.writerow([
                    dom,
                    category,
                    entry["count"],
                    f"{entry['first']:%Y-%m-%d}" if entry["first"] else "",
                    f"{entry['last']:%Y-%m-%d}" if entry["last"] else "",
                ])
    print(f"\n💾 Saved {len(stats)} rows to {path}")
    print("   ⚠️  This file describes your personal accounts. Don't upload or share it.")


def main():
    parser = argparse.ArgumentParser(description="Scan Gmail for your digital footprint.")
    parser.add_argument("--all-mail", action="store_true", help="search [Gmail]/All Mail instead of Inbox")
    parser.add_argument("--limit", type=int, default=0, help="only analyze the newest N matches (0 = all)")
    parser.add_argument("--csv", metavar="FILE", help="also export the results to a CSV file")
    args = parser.parse_args()

    user = os.environ.get("GMAIL_USER") or input("Gmail address: ").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD") or getpass.getpass("App password (hidden): ")
    folder = '"[Gmail]/All Mail"' if args.all_mail else "INBOX"

    stats = scan(user, password, folder, args.limit)
    print_report(stats)
    if args.csv:
        export_csv(stats, args.csv)


if __name__ == "__main__":
    main()
