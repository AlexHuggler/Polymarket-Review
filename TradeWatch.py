import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1451014587456426227/BhLNOQBL9rtHQ09fQvx-Ugp2pZtIiXEIgtyQKbykWX_V4WgUnacVTtDJ1kGwq-DoPeeu"
TARGET_WALLET = "0x16b29c50f2439faf627209b2ac0c7bbddaa8a881"
CHECK_INTERVAL = 60

# --- POLYMARKET API ---
ACTIVITY_URL = "https://data-api.polymarket.com/activity"

def send_discord_alert(embed_data):
    try:
        payload = {"username": "Whale Watcher", "embeds": [embed_data]}
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print("✅ Alert sent to Discord!")
    except Exception as e:
        print(f"❌ Discord Error: {e}")

def get_user_activity(wallet):
    params = {"user": wallet, "limit": 10, "sortBy": "TIMESTAMP", "sortDirection": "DESC"}
    try:
        # Added timeout to prevent hanging
        response = requests.get(ACTIVITY_URL, params=params, timeout=40)

        # DEBUG: Print status if it's not 200
        if response.status_code != 200:
            print(f"⚠️ API Error: Status {response.status_code} - {response.text}")
            return []

        return response.json()
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Cannot reach Polymarket. (Are you in Colab/Blocked?)")
        return []
    except Exception as e:
        print(f"⚠️ Unexpected Error: {e}")
        return []

def process_trade(activity):
    # (Same logic as before, just ensuring we capture valid data)
    try:
        outcome = activity.get("outcome", "Unknown")
        market_name = activity.get("title", "Unknown Market")
        side = activity.get("side", "UNKNOWN").upper()
        size = float(activity.get("size", 0))
        price = float(activity.get("price", 0))
        value_usd = size * price
        timestamp = activity.get("timestamp", 0)
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
        market_slug = activity.get("slug", "")

        color = 5763719 if side == "BUY" else 15548997

        embed = {
            "title": f"🚨 {side} {outcome}",
            "description": f"**{market_name}**",
            "color": color,
            "fields": [
                {"name": "💰 Value", "value": f"${value_usd:,.0f}", "inline": True},
                {"name": "🏷️ Price", "value": f"{price:.3f}¢", "inline": True},
                {"name": "⏰ Time", "value": time_str, "inline": True}
            ],
            "url": f"https://polymarket.com/market/{market_slug}"
        }
        send_discord_alert(embed)
    except Exception as e:
        print(f"Error parsing trade: {e}")

# --- MAIN LOOP ---
print(f"👀 Watching Wallet: {TARGET_WALLET}")
print("NOTE: If this fails immediately, you are likely blocked by your network/cloud provider.")
print("Running...")

initial_data = get_user_activity(TARGET_WALLET)
last_seen_id = initial_data[0].get("id") if initial_data else None

if last_seen_id:
    print(f"✅ Connected. Last trade ID: {last_seen_id}")

while True:
    activities = get_user_activity(TARGET_WALLET)
    if activities:
        latest_id = activities[0].get("id")
        if latest_id != last_seen_id:
            # Process new trades
            new_trades = [a for a in activities if a.get("id") != last_seen_id and a.get("id") > (last_seen_id or "")]
            # (Simple fallback if ID comparison is tricky with strings, just take top ones)
            if not new_trades and latest_id != last_seen_id:
                 new_trades = [activities[0]]

            for trade in new_trades:
                print(f"New Trade: {trade.get('title')}")
                process_trade(trade)

            last_seen_id = latest_id

    time.sleep(CHECK_INTERVAL)
