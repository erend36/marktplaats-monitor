import json
import os
import re
import urllib.request

SEARCH_URL = "https://www.marktplaats.nl/l/auto-s/volkswagen/f/polo+benzine/1262+473/#f:172|constructionYearFrom:2009|constructionYearTo:2016|PriceCentsTo:200000|mileageTo:250001|postcode:6951MA"

SEEN_FILE = "seen.json"

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
MAIL_FROM = os.environ.get("MAIL_FROM")
MAIL_TO = os.environ.get("MAIL_TO")


def send_email(new_ads):
    links_html = ""

    for link in new_ads:
        full_url = "https://www.marktplaats.nl" + link
        links_html += f'''
        <p>
            🚗 <strong>Nieuwe Volkswagen Polo gevonden!</strong><br>
            <a href="{full_url}">Bekijk advertentie op Marktplaats</a>
        </p>
        '''

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
        "subject": f"🚗 {len(new_ads)} nieuwe Volkswagen Polo advertentie(s)",
        "htmlContent": f"""
        <html>
        <body>
            <h2>Nieuwe Marktplaats advertentie gevonden</h2>
            <p>Er zijn {len(new_ads)} nieuwe advertenties gevonden die aan jouw zoekopdracht voldoen.</p>
            {links_html}
        </body>
        </html>
        """
    }

    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(data).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        print("E-mail verzonden:", response.status)


headers = {
    "User-Agent": "Mozilla/5.0"
}

request = urllib.request.Request(SEARCH_URL, headers=headers)

with urllib.request.urlopen(request, timeout=30) as response:
    html = response.read().decode("utf-8")

links = re.findall(
    r'href="(/v/[^"]+)"',
    html
)

links = list(dict.fromkeys(links))

try:
    with open(SEEN_FILE, "r") as f:
        seen = set(json.load(f))
except (FileNotFoundError, json.JSONDecodeError):
    seen = set()

current = set(links)
new_ads = current - seen

print(f"Advertenties gevonden: {len(current)}")
print(f"Nieuwe advertenties: {len(new_ads)}")

for link in new_ads:
    print("NIEUW:", "https://www.marktplaats.nl" + link)

# Alleen mail versturen als er daadwerkelijk iets nieuws is
if new_ads:
    send_email(new_ads)

with open(SEEN_FILE, "w") as f:
    json.dump(sorted(current | seen), f, indent=2)
