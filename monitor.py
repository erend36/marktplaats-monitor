import json
import os
import re
import urllib.request
import urllib.error

SEARCH_URL = "https://www.marktplaats.nl/l/auto-s/volkswagen/f/polo+benzine/1262+473/"

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
    )
}


def fetch(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def get_value(patterns, html):
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)

        if match:
            value = match.group(1)

            # Nederlandse getalnotatie opschonen
            value = value.replace(".", "").replace(",", ".")
            value = re.sub(r"[^\d.]", "", value)

            try:
                return int(float(value))
            except ValueError:
                pass

    return None


def get_car_details(url):
    try:
        html = fetch(url)

        price = get_value([
            r'"price"\s*:\s*"?(?:EUR\s*)?([0-9.,]+)',
            r'"priceCents"\s*:\s*(\d+)',
            r'€\s*([0-9.]+)'
        ], html)

        # Als priceCents gevonden is en waarde duidelijk in centen staat
        if price and price > 100000:
            price = price // 100

        year = get_value([
            r'"constructionYear"\s*:\s*"?(20\d{2}|19\d{2})',
            r'"year"\s*:\s*"?(20\d{2}|19\d{2})',
            r'Bouwjaar[^0-9]{0,100}(20\d{2}|19\d{2})'
        ], html)

        mileage = get_value([
            r'"mileage"\s*:\s*"?([0-9.]+)',
            r'"mileageInKm"\s*:\s*"?([0-9.]+)',
            r'Kilometerstand[^0-9]{0,100}([0-9.]+)'
        ], html)

        return {
            "price": price,
            "year": year,
            "mileage": mileage
        }

    except Exception as e:
        print(f"Kon advertentie niet controleren: {url}")
        print(e)
        return None


def passes_filters(details):
    if not details:
        return False

    price = details["price"]
    year = details["year"]
    mileage = details["mileage"]

    # Ontbrekende gegevens = voor de zekerheid NIET melden
    if price is None or year is None or mileage is None:
        return False

    if price > MAX_PRICE:
        return False

    if year < MIN_YEAR or year > MAX_YEAR:
        return False

    if mileage > MAX_MILEAGE:
        return False

    return True


def send_email(ads):
    ads_html = ""

    for ad in ads:
        ads_html += f"""
        <hr>
        <h3>🚗 Nieuwe Volkswagen Polo</h3>
        <p>
            <strong>Prijs:</strong> €{ad['price']:,}<br>
            <strong>Bouwjaar:</strong> {ad['year']}<br>
            <strong>Kilometerstand:</strong> {ad['mileage']:,} km<br><br>
            <a href="{ad['url']}">Bekijk advertentie op Marktplaats</a>
        </p>
        """.replace(",", ".")

    data = {
        "sender": {
            "name": "Marktplaats Monitor",
            "email": MAIL_FROM
        },
        "to": [
            {
                "email": MAIL_TO
            }
        ],
        "subject": f"🚗 {len(ads)} nieuwe Polo advertentie(s)",
        "htmlContent": f"""
        <html>
        <body>
            <h2>Nieuwe Volkswagen Polo gevonden!</h2>

            <p>
                Deze advertentie voldoet aan jouw ingestelde filters:
          
