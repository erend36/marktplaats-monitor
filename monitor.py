import json
import os
import urllib.error
import urllib.parse
import urllib.request


# ============================================================
# INSTELLINGEN
# ============================================================

API_URL = "https://www.marktplaats.nl/lrp/api/search"
SEEN_FILE = "seen.json"

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
MAIL_FROM = os.environ.get("MAIL_FROM")
MAIL_TO = os.environ.get("MAIL_TO")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Referer": "https://www.marktplaats.nl/",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}


# ============================================================
# MARKTPLAATS-ZOEKOPDRACHT
# De filters worden door Marktplaats zelf toegepast.
# ============================================================

def build_search_url():
    parameters = [
        ("query", "Volkswagen Polo"),
        ("postcode", "6951MA"),
        ("limit", "100"),
        ("offset", "0"),
        ("sortBy", "SORT_INDEX"),
        ("sortOrder", "DECREASING"),

        # Maximaal EUR 2.000
        ("attributeRanges[]", "PriceCents:null:200000"),

        # Bouwjaar 2009 t/m 2016
        ("attributeRanges[]", "constructionYear:2009:2016"),

        # Maximaal 250.001 kilometer
        ("attributeRanges[]", "mileage:null:250001"),

        # Filters uit jouw Marktplaats-URL
        ("attributesById[]", "172"),
        ("attributesById[]", "1262"),
        ("attributesById[]", "473")
    ]

    return API_URL + "?" + urllib.parse.urlencode(parameters)


# ============================================================
# JSON OPHALEN
# ============================================================

def fetch_json(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


# ============================================================
# ADVERTENTIEGEGEVENS
# ============================================================

def get_ad_id(ad):
    return str(
        ad.get("itemId")
        or ad.get("id")
        or ad.get("listingId")
        or ""
    )


def get_ad_title(ad):
    return (
        ad.get("title")
        or ad.get("description")
        or "Volkswagen Polo"
    )


def get_ad_url(ad):
    url = (
        ad.get("vipUrl")
        or ad.get("url")
        or ad.get("canonicalUrl")
        or ""
    )

    if url.startswith("/"):
        return "https://www.marktplaats.nl" + url

    if url.startswith("http"):
        return url

    ad_id = get_ad_id(ad)

    if ad_id:
        return "https://www.marktplaats.nl/v/" + ad_id

    return "https://www.marktplaats.nl/"


def get_price(ad):
    price_info = ad.get("priceInfo") or {}

    price_cents = (
        price_info.get("priceCents")
        or ad.get("priceCents")
    )

    if price_cents is None:
        return "Prijs niet vermeld"

    try:
        price_euros = int(price_cents) / 100
        return "EUR " + f"{price_euros:,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "Prijs niet vermeld"


def get_location(ad):
    location = ad.get("location") or {}

    return (
        location.get("cityName")
        or location.get("city")
        or ad.get("locationName")
        or ""
    )


# ============================================================
# GEZIENE ADVERTENTIES
# ============================================================

def load_seen():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as file:
            content = json.load(file)

            if isinstance(content, list):
                return set(str(item) for item in content)

    except FileNotFoundError:
        pass

    except json.JSONDecodeError:
        print("WAARSCHUWING: seen.json kon niet worden gelezen.")

    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sorted(seen),
            file,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# E-MAIL VIA BREVO
# ============================================================

def send_email(new_ads):
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY ontbreekt")

    if not MAIL_FROM:
        raise RuntimeError("MAIL_FROM ontbreekt")

    if not MAIL_TO:
        raise RuntimeError("MAIL_TO ontbreekt")

    advertisement_blocks = ""

    for ad in new_ads:
        title = get_ad_title(ad)
        price = get_price(ad)
        location = get_location(ad)
        url = get_ad_url(ad)

        advertisement_blocks += (
            "<div style='padding:16px;margin-bottom:16px;"
            "border:1px solid #dddddd;border-radius:8px;'>"
            "<h3 style='margin-top:0;'>"
            + title +
            "</h3>"
            "<p><strong>Prijs:</strong> "
            + price +
            "<br>"
        )

        if location:
            advertisement_blocks += (
                "<strong>Locatie:</strong> "
                + location +
                "<br>"
            )

        advertisement_blocks += (
            "</p>"
            "<p><a href='"
            + url +
            "'>Bekijk advertentie op Marktplaats</a></p>"
            "</div>"
        )

    html_content = (
        "<html>"
        "<body style='font-family:Arial,sans-serif;color:#222222;'>"
        "<h2>Nieuwe Volkswagen Polo gevonden</h2>"
        "<p>Marktplaats heeft een nieuwe advertentie gevonden binnen "
        "jouw opgeslagen filters:</p>"
        "<ul>"
        "<li>Volkswagen Polo benzine</li>"
        "<li>Prijs maximaal EUR 2.000</li>"
        "<li>Bouwjaar 2009 t/m 2016</li>"
        "<li>Maximaal 250.001 kilometer</li>"
        "</ul>"
        + advertisement_blocks +
        "</body>"
        "</html>"
    )

    payload = {
        "sender": {
            "name": "Marktplaats Monitor",
            "email": MAIL_FROM
        },
        "to": [
            {
                "email": MAIL_TO
            }
        ],
        "subject": (
            str(len(new_ads))
            + " nieuwe Volkswagen Polo advertentie(s)"
        ),
        "htmlContent": html_content
    }

    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = response.read().decode("utf-8")
            print("E-mail verzonden. Status:", response.status)
            print(result)

    except urllib.error.HTTPError as error:
        result = error.read().decode("utf-8", errors="ignore")
        print("Brevo-fout. Status:", error.code)
        print(result)
        raise


# ============================================================
# HOOFDPROGRAMMA
# ============================================================

def main():
    search_url = build_search_url()

    print("Gefilterde Marktplaats-zoekopdracht ophalen...")
    print("Prijs maximaal: EUR 2.000")
    print("Bouwjaar: 2009 t/m 2016")
    print("Kilometerstand maximaal: 250.001")

    result = fetch_json(search_url)

    listings = result.get("listings", [])

    if not isinstance(listings, list):
        raise RuntimeError(
            "Marktplaats gaf geen geldige lijst met advertenties terug."
        )

    print("Gefilterde advertenties gevonden:", len(listings))

    current_ads = {}

    for ad in listings:
        ad_id = get_ad_id(ad)

        if ad_id:
            current_ads[ad_id] = ad

    current_ids = set(current_ads.keys())
    seen = load_seen()

    new_ids = current_ids - seen
    new_ads = [current_ads[ad_id] for ad_id in new_ids]

    print("Nieuwe advertenties:", len(new_ads))

    for ad in new_ads:
        print(
            "NIEUW:",
            get_price(ad),
            "-",
            get_ad_title(ad),
            "-",
            get_ad_url(ad)
        )

    if new_ads:
        send_email(new_ads)
    else:
        print("Geen nieuwe advertenties. Geen mail verstuurd.")

    seen.update(current_ids)
    save_seen(seen)

    print("Controle succesvol afgerond.")


if __name__ == "__main__":
    main()
