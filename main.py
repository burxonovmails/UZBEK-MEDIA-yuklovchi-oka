import telebot
import yt_dlp
import os
from flask import Flask
from threading import Thread

# --- RENDER UCHUN ---
app = Flask('')
@app.route('/')
def home(): return "Downloader Bot is Live!"

def run(): app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- SOZLAMALAR ---
TOKEN = "YANGI_BOT_TOKENINGIZ"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Salom! Menga YouTube, TikTok yoki Instagram linkini yuboring, men uni yuklab beraman.")

@bot.message_handler(func=lambda m: True)
def download_handler(message):
    url = message.text
    if "http" not in url:
        bot.send_message(message.chat.id, "❌ Iltimos, to'g'ri havola yuboring!")
        return

    msg = bot.send_message(message.chat.id, "⏳ Video tayyorlanmoqda, kuting...")

    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'max_filesize': 50 * 1024 * 1024, # 50 MB gacha cheklov (Render uchun xavfsiz)
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            with open(filename, 'rb') as video:
                bot.send_video(message.chat.id, video, caption="✅ Yuklab olindi!")
            
            os.remove(filename) # Joy bo'shatish uchun o'chiramiz
            bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Xatolik yuz berdi: {str(e)}", message.chat.id, msg.message_id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
