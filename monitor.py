import json
import re
import urllib.request

SEARCH_URL = "https://www.marktplaats.nl/l/auto-s/volkswagen/f/polo+benzine/1262+473/#f:172|constructionYearFrom:2009|constructionYearTo:2016|PriceCentsTo:200000|mileageTo:250001|postcode:6951MA"

SEEN_FILE = "seen.json"

headers = {
    "User-Agent": "Mozilla/5.0"
}

request = urllib.request.Request(SEARCH_URL, headers=headers)

with urllib.request.urlopen(request, timeout=30) as response:
    html = response.read().decode("utf-8")

# Zoek Marktplaats-advertentielinks
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

with open(SEEN_FILE, "w") as f:
    json.dump(sorted(current | seen), f, indent=2)
