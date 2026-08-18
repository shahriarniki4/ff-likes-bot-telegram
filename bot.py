#!/usr/bin/env python3
import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.constants import ParseMode

from storage import GuestDataError, count_guests
from send_like import LikeSendResult, send_likes

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = os.getenv("PORT")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

ASKING_UID, ASKING_SERVER, ASKING_COUNT, ASKING_CONCURRENCY = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """🔥 <b>Free Fire Likes Bot</b>

Welcome! This bot helps you send likes to Free Fire profiles.

📋 <b>Commands</b>
• /likes - Send likes to a profile
• /status - Check available guests
• /help - Show help
• /capture - Guest capture instructions

⚠️ Note: Capture guests first!"""
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📚 <b>Help &amp; Instructions</b>

<b>Step 1:</b> Capture guests from an Android device
<b>Step 2:</b> Convert guests using the script
<b>Step 3:</b> Use /likes in this bot

⚠️ Daily limit: 100 guests per profile per 24h
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def capture_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    capture_text = """📱 <b>Guest Capture Instructions</b>

1️⃣ Install Frida on the Android device
2️⃣ Run: <code>python3 dev/frida_injections/frida_manager.py</code>
3️⃣ Launch Free Fire
4️⃣ Convert guests: <code>python3 guests_manager/save_guest.py</code>
"""
    await update.message.reply_text(capture_text, parse_mode=ParseMode.HTML)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        guest_count = count_guests()
    except GuestDataError as exc:
        await update.message.reply_text(f"❌ {exc}")
        return

    if guest_count == 0:
        await update.message.reply_text(
            "⚠️ <b>No guest accounts configured</b>\n\n"
            "On a hosted server the guest file is not included in the repository. "
            "Set the <code>GUESTS_JSON</code> environment variable to the contents of "
            "<code>guests_manager/guests_converted.json</code>, or mount a volume and set "
            "<code>DATA_DIR</code>.",
            parse_mode=ParseMode.HTML,
        )
        return

    await update.message.reply_text(
        f"✅ <b>Bot Status</b>\n\n"
        f"👥 Available Guests: <b>{guest_count}</b>\n"
        f"📊 Daily Limit: 100 likes per profile\n"
        f"🏃 Ready to send likes!",
        parse_mode=ParseMode.HTML,
    )


async def likes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏃 Enter target <b>UID</b> (numbers only):",
        parse_mode=ParseMode.HTML,
    )
    return ASKING_UID


async def ask_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    if not uid.isdigit():
        await update.message.reply_text("❌ Please enter a valid UID")
        return ASKING_UID

    context.user_data["target_uid"] = uid
    await update.message.reply_text("🌍 Select server: BD | IND | BR | US | SA | NA")
    return ASKING_SERVER


async def ask_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    server = update.message.text.strip().upper()
    valid = ["BD", "IND", "BR", "US", "SA", "NA"]

    if server not in valid:
        await update.message.reply_text(f"❌ Invalid. Choose: {', '.join(valid)}")
        return ASKING_SERVER

    context.user_data["server"] = server
    await update.message.reply_text("📊 How many likes? (1-100):")
    return ASKING_COUNT


async def ask_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count_val = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid number")
        return ASKING_COUNT

    if count_val < 1 or count_val > 100:
        await update.message.reply_text("❌ Enter 1-100")
        return ASKING_COUNT

    context.user_data["like_count"] = count_val
    await update.message.reply_text("Concurrent requests? (1-50):")
    return ASKING_CONCURRENCY


async def ask_concurrency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conc = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid number, enter 1-50")
        return ASKING_CONCURRENCY

    if conc < 1 or conc > 50:
        await update.message.reply_text("❌ Enter 1-50")
        return ASKING_CONCURRENCY

    data = context.user_data
    await update.message.reply_text("⏳ Sending likes...")

    try:
        result = await send_likes(
            data["target_uid"],
            data["server"],
            data["like_count"],
            conc,
        )
    except (ValueError, RuntimeError, GuestDataError) as exc:
        # Configuration and input problems are actionable, so show them as-is.
        await update.message.reply_text(f"❌ {exc}")
        context.user_data.clear()
        return ConversationHandler.END
    except Exception:
        logger.exception("Like request failed")
        await update.message.reply_text(
            "❌ The request failed. Check the server logs and guest account data, then try again."
        )
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(_format_like_result(result))
    context.user_data.clear()
    return ConversationHandler.END


def _format_like_result(result: LikeSendResult) -> str:
    """Render only the verified before/after result for Telegram."""
    if result.sent_amount > 0:
        message = f"""𝐋𝐢𝐤𝐞𝐬 𝐒𝐞𝐧𝐭 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥𝐥𝐲 🔥

👤 𝐍𝐚𝐦𝐞 : {result.player.name}
🆔 𝐔𝐈𝐃 : {result.player.uid}
🌐 𝐑𝐞𝐠𝐢𝐨𝐧 : {result.player.region}

📊 𝐋𝐢𝐤𝐞𝐬 𝐁𝐞𝐟𝐨𝐫𝐞 : {result.before}
➕ 𝐋𝐢𝐤𝐞𝐬 𝐀𝐝𝐝𝐞𝐝 : {result.sent_amount}
🎯 𝐋𝐢𝐤𝐞𝐬 𝐀𝐟𝐭𝐞𝐫 : {result.after}"""
    else:
        message = f"""𝐋𝐢𝐤𝐞𝐬 𝐍𝐨𝐭 𝐒𝐞𝐧𝐭 ❌

👤 𝐍𝐚𝐦𝐞 : {result.player.name}
🆔 𝐔𝐈𝐃 : {result.player.uid}
🌐 𝐑𝐞𝐠𝐢𝐨𝐧 : {result.player.region}

📊 𝐋𝐢𝐤𝐞𝐬 𝐁𝐞𝐟𝐨𝐫𝐞 : {result.before}
➕ 𝐋𝐢𝐤𝐞𝐬 𝐀𝐝𝐝𝐞𝐝 : 0
🎯 𝐋𝐢𝐤𝐞𝐬 𝐀𝐟𝐭𝐞𝐫 : {result.before}"""

    if result.api_failures:
        failures = "\n".join(
            f"- Guest {failure.guest_uid}: "
            f"{failure.status_code or 'request error'} — {failure.response}"
            for failure in result.api_failures
        )
        message += f"\n\nAPI response details:\n{failures}"

    if result.verification_error:
        message += f"\n\nVerification error: {result.verification_error}"

    return message


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled. Use /likes to start again.")
    return ConversationHandler.END


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server API
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # silence per-request logging
        return


def _start_health_server(port: int) -> None:
    """Hosts that expect an open HTTP port (Render, Koyeb, Cloud Run) need this."""
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logger.info("Health check server listening on port %s", port)


def main():
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured. Set it in the hosting "
            "environment variables (not only in a local .env file)."
        )

    if PORT and PORT.isdigit():
        _start_health_server(int(PORT))

    if count_guests() == 0:
        logger.warning(
            "No guest accounts are configured. Set GUESTS_JSON or DATA_DIR on the host, "
            "otherwise /likes cannot work."
        )

    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("likes", likes_command)],
        states={
            ASKING_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_uid)],
            ASKING_SERVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_server)],
            ASKING_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_count)],
            ASKING_CONCURRENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_concurrency)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("capture", capture_command))
    application.add_handler(conv_handler)

    logger.info("Bot is starting...")
    # drop_pending_updates avoids replaying a backlog after a redeploy.
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
