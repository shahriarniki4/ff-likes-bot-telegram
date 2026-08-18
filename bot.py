#!/usr/bin/env python3
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from guests_manager.count_guest import count
from send_like import send_likes

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ASKING_UID, ASKING_SERVER, ASKING_COUNT, ASKING_CONCURRENCY = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """🔥 **Free Fire Likes Bot**

Welcome! This bot helps you send likes to Free Fire profiles.

📋 **Commands:**
• `/likes` - Send likes to a profile
• `/status` - Check available guests
• `/help` - Show help
• `/capture` - Guest capture instructions

⚠️ Note: Capture guests first!"""
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📚 **Help & Instructions**

**Step 1:** Capture guests from Android device
**Step 2:** Convert guests using script
**Step 3:** Use `/likes` command in this bot

⚠️ Daily limit: 100 guests per profile per 24h
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def capture_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    capture_text = """📱 **Guest Capture Instructions**

1️⃣ Install Frida on Android device
2️⃣ Run: `python3 dev/frida_injections/frida_manager.py`
3️⃣ Launch Free Fire
4️⃣ Convert guests: `python3 guests_manager/save_guest.py`
"""
    await update.message.reply_text(capture_text, parse_mode=ParseMode.MARKDOWN)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        guest_count = count()
        status_text = f"""✅ **Bot Status**

👥 Available Guests: **{guest_count}**
📊 Daily Limit: 100 likes per profile
🏃 Ready to send likes!
"""
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def likes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏃 Enter target **UID** (numbers only):",
        parse_mode=ParseMode.MARKDOWN
    )
    return ASKING_UID

async def ask_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    if not uid.isdigit():
        await update.message.reply_text("❌ Please enter valid UID")
        return ASKING_UID
    
    context.user_data['target_uid'] = uid
    await update.message.reply_text(
        "🌍 Select server: BD | IND | BR | US | SA | NA",
        parse_mode=ParseMode.MARKDOWN
    )
    return ASKING_SERVER

async def ask_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    server = update.message.text.strip().upper()
    valid = ["BD", "IND", "BR", "US", "SA", "NA"]
    
    if server not in valid:
        await update.message.reply_text(f"❌ Invalid. Choose: {', '.join(valid)}")
        return ASKING_SERVER
    
    context.user_data['server'] = server
    await update.message.reply_text("📊 How many likes? (1-100):")
    return ASKING_COUNT

async def ask_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count_val = int(update.message.text.strip())
        if count_val < 1 or count_val > 100:
            await update.message.reply_text("❌ Enter 1-100")
            return ASKING_COUNT
        
        context.user_data['like_count'] = count_val
        await update.message.reply_text("Concurrent requests? (1-50):")
        return ASKING_CONCURRENCY
    except ValueError:
        await update.message.reply_text("❌ Invalid number")
        return ASKING_COUNT

async def ask_concurrency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conc = int(update.message.text.strip())
        if conc < 1 or conc > 50:
            await update.message.reply_text("❌ Enter 1-50")
            return ASKING_CONCURRENCY

        data = context.user_data
        await update.message.reply_text("⏳ Sending likes...")
        success, planned = await send_likes(
            data['target_uid'],
            data['server'],
            data['like_count'],
            conc,
        )
        await update.message.reply_text(
            f"""**Likes complete**

Target UID: {data['target_uid']}
Server: {data['server']}
Successful requests: {success}/{planned}

Use `/likes` again or `/status` to check.""",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data.clear()
        return ConversationHandler.END
    except ValueError as exc:
        await update.message.reply_text(f"❌ {exc}")
        return ASKING_CONCURRENCY
    except Exception:
        logger.exception("Like request failed")
        await update.message.reply_text(
            "❌ The request failed. Check the server logs and guest account data, then try again."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Use `/likes` to start again.")
    return ConversationHandler.END

def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('likes', likes_command)],
        states={
            ASKING_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_uid)],
            ASKING_SERVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_server)],
            ASKING_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_count)],
            ASKING_CONCURRENCY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_concurrency)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(CommandHandler('capture', capture_command))
    application.add_handler(conv_handler)
    
    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
