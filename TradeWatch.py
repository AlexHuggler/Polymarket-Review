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
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=20)
        if response.status_code not in {200, 204}:
            print(f"❌ Discord Error: Status {response.status_code} - {response.text}")
            return
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

def normalize_timestamp(raw_timestamp):
    try:
        timestamp = int(raw_timestamp)
    except (TypeError, ValueError):
        return 0

    if timestamp > 10**12:
        return int(timestamp / 1000)
    return timestamp

def is_trade_activity(activity):
    if activity.get("side") in {"BUY", "SELL"}:
        return True
    return activity.get("type") in {"TRADE", "MARKET_TRADE", "TRADE_FILLED"}

def process_trade(activity):
    # (Same logic as before, just ensuring we capture valid data)
    try:
        outcome = activity.get("outcome", "Unknown")
        market_name = activity.get("title", "Unknown Market")
        side = activity.get("side", "UNKNOWN").upper()
        size = float(activity.get("size", 0))
        price = float(activity.get("price", 0))
        value_usd = size * price
        timestamp = normalize_timestamp(activity.get("timestamp", 0))
        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S") if timestamp else "Unknown"
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
initial_trades = [activity for activity in initial_data if is_trade_activity(activity)]
last_seen_timestamp = normalize_timestamp(initial_trades[0].get("timestamp")) if initial_trades else 0
last_seen_ids = {activity.get("id") for activity in initial_trades if normalize_timestamp(activity.get("timestamp")) == last_seen_timestamp}

if last_seen_timestamp:
    print(f"✅ Connected. Last trade timestamp: {last_seen_timestamp}")

while True:
    activities = get_user_activity(TARGET_WALLET)
    if activities:
        trade_activities = [activity for activity in activities if is_trade_activity(activity)]
        new_trades = []
        for trade in trade_activities:
            trade_timestamp = normalize_timestamp(trade.get("timestamp"))
            trade_id = trade.get("id")
            if trade_timestamp > last_seen_timestamp:
                new_trades.append(trade)
            elif trade_timestamp == last_seen_timestamp and trade_id and trade_id not in last_seen_ids:
                new_trades.append(trade)

        if new_trades:
            for trade in sorted(new_trades, key=lambda item: normalize_timestamp(item.get("timestamp"))):
                print(f"New Trade: {trade.get('title')}")
                process_trade(trade)

            last_seen_timestamp = max(
                last_seen_timestamp,
                max(normalize_timestamp(trade.get("timestamp")) for trade in new_trades),
            )
            last_seen_ids = {
                trade.get("id")
                for trade in trade_activities
                if normalize_timestamp(trade.get("timestamp")) == last_seen_timestamp
            }

    time.sleep(CHECK_INTERVAL)
