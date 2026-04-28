import telebot
import yt_dlp
import os
import threading
from telebot import types
from flask import Flask
from threading import Thread

# --- RENDER UCHUN VEB-SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Active!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- BOT SOZLAMALARI ---
TOKEN = "8721093015:AAGpOgNz4npcO2fA-rNdMecN4T0mMlI-Y6A" 
bot = telebot.TeleBot(TOKEN)
BOT_USERNAME = "@ozbemediarobot" # Sizning botingiz useri

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# --- OPTIMALLASHGAN SOZLAMALAR ---
YTDL_OPTS = {
    'format': 'best', 
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 50 * 1024 * 1024, # 50MB limit
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"👋 **Salom! Men {BOT_USERNAME} botiman.**\n\n"
                                      "🔗 Instagram, TikTok yoki YouTube linkini yuboring.\n"
                                      "🎵 Musiqa ajratib beraman!", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    query = message.text.strip()
    chat_id = message.chat.id
    wait = bot.send_message(chat_id, "⏳")
    threading.Thread(target=process_download, args=(chat_id, query, wait.message_id)).start()

def process_download(chat_id, query, wait_id):
    is_link = "http" in query
    search_q = query if is_link else f"ytsearch1:{query}"
    
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(search_q, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            file_path = ydl.prepare_filename(entry)
            title = entry.get('title', "Media")

            # 1. Videoni yuborish (agar link bo'lsa)
            if is_link:
                with open(file_path, 'rb') as f:
                    bot.send_video(chat_id, f, caption=f"🎬 {title}\n\n👤 {BOT_USERNAME}")
                
                # 2. MUSIQA SIFATIDA AJRATISH (Extract)
                # yt-dlp avtomatik audio formatini ham ko'ra oladi
                with open(file_path, 'rb') as f:
                    bot.send_audio(chat_id, f, caption=f"🎵 {title} (Audio)\n\n👤 {BOT_USERNAME}")
            else:
                # Faqat qidiruv bo'lsa, audio yuboramiz
                with open(file_path, 'rb') as f:
                    bot.send_audio(chat_id, f, caption=f"🎵 {title}\n\n👤 {BOT_USERNAME}")

            # Tozalash
            if os.path.exists(file_path):
                os.remove(file_path)
            bot.delete_message(chat_id, wait_id)

    except Exception as e:
        bot.edit_message_text("❌ Xatolik: Yuklab bo'lmadi yoki fayl juda katta.", chat_id, wait_id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
