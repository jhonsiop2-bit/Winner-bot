import requests
import base64
import time
import hashlib
import re
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ================= CONFIG =================
APP_ID = os.getenv("APP_ID")
SECRET = os.getenv("SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SCAN_TIME = 120
MIN_PRICE = 8
MAX_PRICE = 60

# ================= STORAGE =================
seen_products = set()

# ================= SELENIUM =================
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

# ================= TOKEN =================
token = None
token_exp = 0

def get_token():
    global token, token_exp

    if token and time.time() < token_exp:
        return token

    creds = base64.b64encode(f"{APP_ID}:{SECRET}".encode()).decode()

    r = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data="grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope"
    ).json()

    token = r.get("access_token")
    token_exp = time.time() + r.get("expires_in", 7200)

    return token

# ================= TELEGRAM =================
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass

# ================= SEARCH =================
def search(keyword):
    t = get_token()
    if not t:
        return []

    try:
        r = requests.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            headers={"Authorization": f"Bearer {t}"},
            params={
                "q": keyword,
                "limit": 25,
                "filter": f"price:[{MIN_PRICE}..{MAX_PRICE}]"
            }
        )

        return r.json().get("itemSummaries", [])

    except:
        return []

# ================= SCRAPE =================
def get_real_data(url):
    try:
        driver.get(url)
        time.sleep(2)

        html = driver.page_source.lower()

        sold = 0
        m = re.search(r'(\d+)\s*sold', html)
        if m:
            sold = int(m.group(1))

        trending = "trending" in html

        return sold, trending

    except:
        return 0, False

# ================= FILTER =================
def kill_bad(title):
    bad = [
        "apple","samsung","sony","nike",
        "used","refurbished","vintage",
        "bulk","lot","wholesale",
        "adapter","case","cover"
    ]
    title = title.lower()
    return any(w in title for w in bad)

# ================= SCORE =================
def score_item(price, fb, sold, trending):
    score = 0

    if 15 <= price <= 50:
        score += 2

    if 200 <= fb <= 910:
        score += 4

    if sold >= 5:
        score += 5
    elif sold >= 2:
        score += 3

    if trending:
        score += 3

    return score

# ================= KEYWORDS =================
KEYWORDS = [
    "back pain relief",
    "foot pain relief",
    "neck stretcher",
    "pet hair remover",
    "dog bed calming",
    "car scratch remover",
    "vegetable chopper",
    "meat chopper",
    "laptop stand",
    "phone holder"
]

# ================= MAIN =================
def run():
    print("🔥 SCANNING...")

    for kw in KEYWORDS:
        items = search(kw)

        for item in items:
            try:
                title = item.get("title","")
                link = item.get("itemWebUrl","")
                price = float(item.get("price",{}).get("value",0))
                seller = item.get("seller",{})
                fb = int(seller.get("feedbackScore",0) or 0)

                if kill_bad(title):
                    continue

                if not (200 <= fb <= 910):
                    continue

                sold, trending = get_real_data(link)
                score = score_item(price, fb, sold, trending)

                if score >= 8:
                    msg = f"""🔥 WINNER FOUND

{title}

💰 Price: {price}$
📦 Sold: {sold}
⭐ Score: {score}

{link}
"""
                    send(msg)
                    print("SENT:", title[:40])

            except:
                continue

# ================= LOOP =================
if __name__ == "__main__":
    send("🚀 GOLD BOT STARTED")

    while True:
        try:
            run()
            time.sleep(SCAN_TIME)
        except:
            time.sleep(30)