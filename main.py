import requests
import base64
import time

# ================= CONFIG =================
APP_ID = "Najebnaj-ProHunt-PRD-8f606d196-11a90e20"
SECRET = "PRD-f606d196bb94-a8c6-4d14-8214-2a6a"
TELEGRAM_TOKEN = "8657814491:AAGTTLZXtkTQm750CuUznuNUUFRYfT3K4Ng"
CHAT_ID = "5989878697"

SCAN_TIME = 120
MIN_PRICE = 8
MAX_PRICE = 60

seen = set()

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
                "limit": 20,
                "filter": f"price:[{MIN_PRICE}..{MAX_PRICE}]"
            }
        )

        return r.json().get("itemSummaries", [])

    except:
        return []

# ================= SCORE =================
def score_item(price, fb):
    score = 0

    if 15 <= price <= 50:
        score += 3

    if 200 <= fb <= 2000:
        score += 4

    return score

# ================= FILTER =================
def kill_bad(title):
    bad = [
        "apple","samsung","sony","nike",
        "used","refurbished","vintage",
        "bulk","lot","wholesale"
    ]
    title = title.lower()
    return any(w in title for w in bad)

# ================= MAIN =================
def run():
    print("🔥 SCANNING...")

    keywords = [
        "back pain relief",
        "pet hair remover",
        "car scratch remover",
        "kitchen gadget",
        "laptop stand",
        "phone holder"
    ]

    for kw in keywords:
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

                key = title[:50]
                if key in seen:
                    continue

                score = score_item(price, fb)

                if score >= 5:
                    msg = f"""🔥 WINNER

{title}

💰 Price: {price}$
⭐ Seller Score: {fb}

{link}
"""
                    send(msg)
                    seen.add(key)
                    print("SENT:", title[:40])

            except:
                continue

# ================= LOOP =================
if __name__ == "__main__":
    send("🚀 BOT STARTED")

    while True:
        try:
            run()
            time.sleep(SCAN_TIME)
        except:
            time.sleep(30)