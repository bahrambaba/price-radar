#!/usr/bin/env python3
"""
Real-time Price Radar Bot
Fetches live prices from chandshode.com and sends to Telegram.
"""

import requests
import json
import re
import os
from datetime import datetime


def fetch_prices():
    """Fetch live prices from chandshode.com"""
    try:
        resp = requests.get(
            "https://chandshode.com",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        resp.raise_for_status()
        
        html = resp.text
        
        # Extract JSON-LD data
        match = re.search(
            r'<script type="application/ld\+json">(\[.*?\])</script>',
            html,
            re.DOTALL
        )
        
        if not match:
            print("Error: Could not find price data")
            return None
        
        data = json.loads(match.group(1))
        
        prices = {}
        for item in data:
            if item.get("@type") == "ItemList":
                for li in item.get("itemListElement", []):
                    product = li.get("item", {})
                    name = product.get("name", "")
                    price = product.get("offers", {}).get("lowPrice", 0)
                    currency = product.get("offers", {}).get("priceCurrency", "")
                    prices[name] = {"price": price, "currency": currency}
        
        return prices
        
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return None


def format_price(price, currency):
    """Format price with proper separators and decimals"""
    if currency == "USD":
        return f"{price:,.2f} $"
    else:
        # Convert to Toman
        toman = price / 10
        if toman >= 1_000_000_000:
            return f"{toman / 1_000_000_000:,.2f} میلیارد تومان"
        elif toman >= 1_000_000:
            return f"{toman / 1_000_000:,.2f} میلیون تومان"
        elif toman >= 1_000:
            return f"{toman:,.0f} تومان"
        else:
            return f"{toman:,.0f} تومان"


def format_message(prices):
    """Format message for display"""
    import jdatetime
    from datetime import timezone, timedelta
    
    # Iran timezone (UTC+3:30)
    iran_tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(iran_tz)
    jalali = jdatetime.datetime.fromgregorian(datetime=now)
    
    jalali_months = [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ]
    
    date_str = f"{jalali.day} {jalali_months[jalali.month - 1]} {jalali.year}"
    time_str = now.strftime("%H:%M")
    
    # Build message
    msg = f"📊 رادار قیمت لحظه‌ای\n"
    msg += f"📅 {date_str} - 🕐 {time_str}\n"
    msg += f"{'=' * 30}\n\n"
    
    # Track items
    items = [
        ("دلار", "دلار"),
        ("دلار تتر", "دلار تتر"),
        ("یورو", "یورو"),
        ("پوند", "پوند"),
        ("سکه امامی", "سکه امامی"),
        ("سکه بهار آزادی", "سکه بهار آزادی"),
        ("نیم سکه", "نیم سکه"),
        ("ربع سکه", "ربع سکه"),
        ("سکه یک گرمی", "سکه یک گرمی"),
        ("طلای ۱۸ عیار", "طلای ۱۸ عیار"),
        ("طلای ۲۴ عیار", "طلای ۲۴ عیار"),
        ("طلای آب‌شده نقدی", "طلای آب‌شده نقدی"),
        ("انس طلا", "انس طلا"),
    ]
    
    for display_name, search_name in items:
        if search_name in prices:
            p = prices[search_name]
            formatted = format_price(p["price"], p["currency"])
            msg += f"• {display_name}: {formatted}\n"
    
    msg += f"\n{'=' * 30}\n"
    msg += f"🌐 منبع: chandshode.com"
    
    return msg


def send_to_telegram(message):
    """Send message to Telegram"""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    if not bot_token or not chat_id:
        print("Telegram credentials not set")
        print("Message:")
        print(message)
        return False
    
    # Ensure chat_id is string
    chat_id = str(chat_id).strip()
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": message
    }
    
    try:
        resp = requests.post(url, json=data, timeout=10)
        result = resp.json()
        
        print(f"Response status: {resp.status_code}")
        print(f"Response: {result}")
        
        if result.get("ok"):
            print("Message sent to Telegram successfully")
            return True
        else:
            error_code = result.get("error_code", "Unknown")
            description = result.get("description", "Unknown error")
            print(f"Telegram error {error_code}: {description}")
            
            # Provide helpful hints
            if error_code == 400:
                if "chat not found" in description.lower():
                    print("HINT: Bot is not a member of the group or chat_id is wrong")
                elif "bot was blocked" in description.lower():
                    print("HINT: Bot was blocked by the user")
                elif "not enough rights" in description.lower():
                    print("HINT: Bot doesn't have permission to send messages")
            elif error_code == 401:
                print("HINT: Bot token is invalid")
            elif error_code == 403:
                print("HINT: Bot is not allowed to send messages to this chat")
            
            return False
            
    except Exception as e:
        print(f"Error sending to Telegram: {e}")
        return False


def main():
    print("Fetching prices from chandshode.com...")
    prices = fetch_prices()
    
    if not prices:
        print("Failed to fetch prices")
        return
    
    print(f"Found {len(prices)} items")
    
    message = format_message(prices)
    print("\n" + message)
    
    # Send to Telegram
    print("\nSending to Telegram...")
    send_to_telegram(message)
    
    # Save to file
    os.makedirs("output", exist_ok=True)
    with open("output/latest_prices.txt", "w", encoding="utf-8") as f:
        f.write(message)
    
    print("\nSaved to output/latest_prices.txt")
    print("\nDone!")


if __name__ == "__main__":
    main()
