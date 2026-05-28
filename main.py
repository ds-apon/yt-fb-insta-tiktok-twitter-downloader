import os
import yt_dlp

from telegram.ext import CommandHandler

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
🎬 <b>Universal Downloader Bot</b>

📥 Supported Platforms:

• YouTube
• Instagram
• Facebook
• TikTok
• Twitter/X

⚡ Features:

✅ Smart Quality Detection
✅ 720p / 1080p Download
✅ MP3 Audio Download
✅ Fast Processing
✅ High Quality Video

📎 Just send any video link to start downloading.
"""

    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Updates Channel",
                url="https://t.me/xoxo_universe"
            )
        ],
        [
            InlineKeyboardButton(
                "👨‍💻 Owner",
                url="https://t.me/ds_apon"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# Store user session data
user_data_store = {}

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# =========================
# GET AVAILABLE QUALITIES
# =========================
def get_video_qualities(url):
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
    }

    qualities = set()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])

        for f in formats:
            height = f.get("height")

            if height:
                qualities.add(height)

    return sorted(qualities)


# =========================
# HANDLE USER LINK
# =========================
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    loading = await update.message.reply_text(
        "🔍 Detecting available qualities..."
    )

    try:
        qualities = get_video_qualities(url)

        if not qualities:
            await loading.edit_text("❌ No video qualities found.")
            return

        # Save data
        user_data_store[update.effective_user.id] = {
            "url": url,
            "qualities": qualities,
        }

        keyboard = []

        row = []

        for q in qualities:
            if q >= 144:
                row.append(
                    InlineKeyboardButton(
                        f"{q}p",
                        callback_data=f"video:{q}"
                    )
                )

                # 2 buttons per row
                if len(row) == 2:
                    keyboard.append(row)
                    row = []

        if row:
            keyboard.append(row)

        # MP3 button
        keyboard.append([
            InlineKeyboardButton(
                "🎵 MP3",
                callback_data="audio:mp3"
            )
        ])

        markup = InlineKeyboardMarkup(keyboard)

        await loading.edit_text(
            "📥 Choose quality:",
            reply_markup=markup
        )

    except Exception as e:
        await loading.edit_text(f"❌ Error:\n{e}")


# =========================
# BUTTON HANDLER
# =========================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    data = user_data_store.get(user_id)

    if not data:
        await query.message.reply_text("⚠ Session expired.")
        return

    url = data["url"]

    action, value = query.data.split(":")

    downloading_msg = await query.message.reply_text(
        "⬇ Downloading..."
    )

    try:
        # =====================
        # VIDEO DOWNLOAD
        # =====================
        if action == "video":

            quality = value

            ydl_opts = {
                "format": (
                    f"bestvideo[height<={quality}]"
                    f"+bestaudio/"
                    f"best[height<={quality}]"
                ),
                "merge_output_format": "mp4",
                "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                "quiet": True,
                "noplaylist": True,
            }

        # =====================
        # AUDIO DOWNLOAD
        # =====================
        else:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
                "quiet": True,
                "noplaylist": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            file_path = ydl.prepare_filename(info)

        # Fix mp3 path
        if action == "audio":
            file_path = os.path.splitext(file_path)[0] + ".mp3"

        # Send file
        if action == "audio":
            await query.message.reply_audio(
                audio=open(file_path, "rb")
            )
        else:
            await query.message.reply_video(
                video=open(file_path, "rb")
            )

        # Delete file
        os.remove(file_path)

        await downloading_msg.delete()

    except Exception as e:
        await downloading_msg.edit_text(
            f"❌ Download failed:\n{e}"
        )


# =========================
# START BOT
# =========================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_link
    )
)

app.add_handler(
    CallbackQueryHandler(button_handler)
)

print("✅ Bot Running...")

app.add_handler(CommandHandler("start", start))

app.run_polling()
