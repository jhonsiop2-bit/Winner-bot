import requests
import base64
import time
import hashlib
import re

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# ================= CONFIG =================
APP_ID  = "Najebnaj-ProHunt-PRD-8f606d196-11a90e20"
SECRET  = "PRD-f606d196bb94-a8c6-4d14-8214-2a6a"

TELEGRAM_TOKEN = "8657814491:AAGTTLZXtkTQm750CuUznuNUUFRYfT3K4Ng"
CHAT_ID        = "5989878697"

SCAN_TIME = 120
MIN_PRICE = 8
MAX_PRICE = 60

# ================= STORAGE =================
try:
    with open("seen.txt", "r") as f:
        seen_products = set(f.read().splitlines())
except:
    seen_products = set()

phase = 1
token = None
token_exp = 0

# ================= SELENIUM =================
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ================= TOKEN =================
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
            data={"chat_id": CHAT_ID, "text": msg[:4000]}
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
                "sort": "bestMatch",
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

        m1 = re.search(r'(\d+)\s*sold', html)
        if m1:
            sold = int(m1.group(1))

        m2 = re.search(r'(\d+)\s*sold\s*today', html)
        if m2:
            sold += int(m2.group(1))

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

# ================= AI =================
def ai_decision(score, sold, trending):
    if sold >= 30 and trending:
        return "🔥 HOT WINNER"
    elif sold >= 10:
        return "⚠️ TEST"
    else:
        return "❌ SKIP"

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

# ================= AI GENERATOR =================
def generate_listing(title):
    clean = title.lower()

    # TITLE SAFE
    safe_title = clean.replace("for", "").replace("with", "")
    safe_title = safe_title[:70] + " Multi-Use Tool"
    safe_title = safe_title[:80]

    # DESCRIPTION
    description = (
        "🔥 Upgrade Your Daily Life\n\n"
        "This product solves real problems easily and efficiently.\n\n"
        "✅ Easy to use\n"
        "✅ High quality\n"
        "✅ Saves time\n"
        "✅ Smart design\n\n"
        "Perfect for everyday use."
    )

    # IMAGE PROMPTS
    prompts = {
        "main": f"Ultra realistic product photo of {title}, black premium background, bold text, 5:4 ratio",
        "lifestyle1": f"Real person using {title} at home, natural light",
        "lifestyle2": f"Close-up usage of {title}, showing benefit",
        "features": f"Infographic of {title} features, icons, clean design",
        "usage": f"Step by step using {title}, realistic hands",
        "variants": f"All color variations of {title}, displayed clean"
    }

    return safe_title, description, prompts

# ================= KEYWORDS =================
KEYWORDS = [
    "back pain relief",
    "foot pain relief",
    "neck stretcher",
    "pet hair remover",
    "dog calming bed",
    "car scratch remover",
    "sink clog remover",
    "vegetable chopper",
    "meat chopper",
    "laptop stand",
    "phone holder"
]

# ================= MAIN =================
def run():
    global phase

    print(f"\n🔥 PHASE {phase}")

    results = []

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

                key = " ".join(title.lower().split()[:3])
                if key in seen_products:
                    continue

                sold, trending = get_real_data(link)

                print(title[:40], "| SOLD:", sold, "| TREND:", trending)

                if sold < 2:
                    continue

                score = score_item(price, fb, sold, trending)
                decision = ai_decision(score, sold, trending)

                if decision == "❌ SKIP":
                    continue

                safe_title, desc, prompts = generate_listing(title)

                profit = round(price * 0.4, 2)

                results.append((score, title, price, profit, sold, trending, link, fb, key, decision, safe_title, desc, prompts))

            except:
                continue

    if not results:
        send("⚠️ No winners now")
        return

    results = sorted(results, reverse=True)

    send(f"🚀 PHASE {phase} RESULTS 🚀")

    for r in results[:3]:
        msg = (
            f"{r[9]}\n\n"
            f"🧠 TITLE:\n{r[10]}\n\n"
            f"📦 DESCRIPTION:\n{r[11]}\n\n"
            f"🎨 IMAGE MAIN:\n{r[12]['main']}\n\n"
            f"🔥 PRODUCT:\n{r[1][:60]}\n"
            f"💰 ${r[2]} | Profit ${r[3]}\n"
            f"📈 Sold: {r[4]} | Trend: {r[5]}\n\n"
            f"{r[6]}"
        )

        send(msg)

        seen_products.add(r[8])
        with open("seen.txt", "a") as f:
            f.write(r[8] + "\n")

        time.sleep(1)

    phase += 1

# ================= LOOP =================
if __name__ == "__main__":
    send("🚀 FINAL AI BOT STARTED")

    while True:
        try:
            run()
            time.sleep(SCAN_TIME)
        except:
            time.sleep(30)