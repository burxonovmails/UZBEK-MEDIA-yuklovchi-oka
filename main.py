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
# Diqqat: Tokenni BotFather berganidek to'liq qo'ying!
TOKEN = "8721093015:AAGpOgNz4npcO2fA-rNdMecN4T0mMlI-Y6A" 
bot = telebot.TeleBot(TOKEN)

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# --- INSTAGRAM VA YOUTUBE UCHUN OPTIMALLASHGAN ---
YTDL_OPTS = {
    'format': 'best', # Instagram/TikTok uchun eng yaxshi format
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 50 * 1024 * 1024, # 50MB (Telegram limiti)
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 **Salom! Men professional yuklovchi botman.**\n\n"
                                      "🔗 Instagram, TikTok yoki YouTube linkini yuboring.\n"
                                      "🎵 Yoki musiqa nomini yozing.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    query = message.text.strip()
    chat_id = message.chat.id
    
    # Tezkor reaksiya
    wait = bot.send_message(chat_id, "⏳")
    
    # Yuklashni alohida oqimga (thread) beramiz
    threading.Thread(target=process_download, args=(chat_id, query, wait.message_id)).start()

def process_download(chat_id, query, wait_id):
    is_link = "http" in query
    search_q = query if is_link else f"ytsearch1:{query}"
    
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            # Ma'lumotlarni olish
            info = ydl.extract_info(search_q, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            file_path = ydl.prepare_filename(entry)
            title = entry.get('title', "Media")

            # Faylni jo'natish (Video yoki Audio)
            with open(file_path, 'rb') as f:
                if is_link:
                    # Agar link bo'lsa, video sifatida yuboramiz
                    bot.send_video(chat_id, f, caption=f"🎬 {title}\n@botingiz_nomi")
                else:
                    # Agar qidiruv bo'lsa, audio sifatida yuboramiz
                    bot.send_audio(chat_id, f, caption=f"🎵 {title}\n@botingiz_nomi")

            # Tozalash (Serverda joy band qilmaslik uchun)
            if os.path.exists(file_path):
                os.remove(file_path)
            bot.delete_message(chat_id, wait_id)

    except Exception as e:
        error_text = str(e)
        if "File is too large" in error_text or "filesize" in error_text:
            bot.edit_message_text("❌ Fayl juda katta (limit 50MB).", chat_id, wait_id)
        else:
            bot.edit_message_text("❌ Xatolik: Yuklab bo'lmadi. Link yopiq yoki noto'g'ri.", chat_id, wait_id)

if __name__ == "__main__":
    keep_alive() # Render uchun veb-serverni yoqish
    print("Bot yondi!")
    bot.infinity_polling()
