import html as html_module
import json
import os
import re
import urllib.error
import urllib.request


# ============================================================
# INSTELLINGEN
# ============================================================

SEARCH_URL = (
    "https://www.marktplaats.nl/l/auto-s/volkswagen/"
    "f/polo+benzine/1262+473/"
)

SEEN_FILE = "seen.json"

MAX_PRICE = 2000
MIN_YEAR = 2009
MAX_YEAR = 2016
MAX_MILEAGE = 250001

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
MAIL_FROM = os.environ.get("MAIL_FROM")
MAIL_TO = os.environ.get("MAIL_TO")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"
}


# ============================================================
# PAGINA OPHALEN
# ============================================================

def fetch(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


# ============================================================
# GETAL UIT HTML HALEN
# ============================================================

def extract_number(page_html, patterns):
    for pattern in patterns:
        match = re.search(pattern, page_html, re.IGNORECASE | re.DOTALL)

        if not match:
            continue

        value = match.group(1)
        value = html_module.unescape(value)
        value = value.strip()

        # Nederlandse duizendtallen verwijderen
        value = value.replace(".", "")
        value = value.replace(",", ".")

        # Alleen cijfers en eventueel decimaalteken overhouden
        value = re.sub(r"[^\d.]", "", value)

        if not value:
            continue

        try:
            return int(float(value))
        except ValueError:
            continue

    return None


# ============================================================
# GEGEVENS VAN ADVERTENTIE UITLEZEN
# ============================================================

def get_car_details(url):
    try:
        page_html = fetch(url)

        # Prijs in centen, bijvoorbeeld 200000 = €2.000
        price_cents = extract_number(
            page_html,
            [
                r'"priceCents"\s*:\s*"?(\d+)"?',
                r'&quot;priceCents&quot;\s*:\s*"?(\d+)"?'
            ]
        )

        if price_cents is not None:
            price = price_cents // 100
        else:
            # Alternatieve prijsvelden zijn doorgaans al in euro's
            price = extract_number(
                page_html,
                [
                    r'"price"\s*:\s*"?([0-9.,]+)"?',
                    r'&quot;price&quot;\s*:\s*"?([0-9.,]+)"?',
                    r'itemprop="price"[^>]*content="([0-9.,]+)"',
                    r'€\s*([0-9.]+)'
                ]
            )

        year = extract_number(
            page_html,
            [
                r'"constructionYear"\s*:\s*"?(19\d{2}|20\d{2})"?',
                r'&quot;constructionYear&quot;\s*:\s*"?(19\d{2}|20\d{2})"?',
                r'"year"\s*:\s*"?(19\d{2}|20\d{2})"?',
                r'Bouwjaar.{0,150}?(19\d{2}|20\d{2})'
            ]
        )

        mileage = extract_number(
            page_html,
            [
    
