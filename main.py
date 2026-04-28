import telebot
import yt_dlp
import os
import sqlite3
import threading
from telebot import types
from flask import Flask
from threading import Thread

# --- RENDER PORT SOZLAMASI ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online and Running!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- SOZLAMALAR ---
TOKEN = "8721093015:AAGpOgNz4npcO2fA-rNdMecN4T0mMlI-Y6A"
bot = telebot.TeleBot(TOKEN, threaded=True)

# Baza (Tezkorlik siri: file_id orqali yuborish)
conn = sqlite3.connect('pro_music.db', check_same_thread=False)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS storage (query TEXT PRIMARY KEY, video_id TEXT, audio_id TEXT, title TEXT)')
conn.commit()

if not os.path.exists('downloads'): os.makedirs('downloads')

# --- YTDL TURBO SOZLAMALARI ---
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 45 * 1024 * 1024, # Render Free uchun xavfsiz limit (45MB)
}

# --- MENYU ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔍 Nom orqali qidirish"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "🚀 **Professional Downloader Bot!**\n\nLink yuboring yoki musiqa nomini yozing:", 
                     parse_mode="Markdown", reply_markup=main_menu())

# --- QIDIRUVNI BOSHLASH ---
@bot.message_handler(func=lambda m: m.text == "🔍 Nom orqali qidirish")
def search_btn(message):
    msg = bot.send_message(message.chat.id, "✍️ Musiqa nomi va ijrochisini yozing:")
    bot.register_next_step_handler(msg, process_input)

@bot.message_handler(func=lambda m: True)
def process_input(message):
    query = message.text.strip()
    chat_id = message.chat.id
    
    # 1. BAZADAN TEZKOR QIDIRISH (0.1 soniya)
    cur.execute("SELECT video_id, audio_id, title FROM storage WHERE query = ?", (query.lower(),))
    res = cur.fetchone()
    if res:
        if "http" in query:
            if res[0]: bot.send_video(chat_id, res[0], caption=f"🎬 {res[2]} (Bazadan)")
            if res[1]: bot.send_audio(chat_id, res[1], caption=f"🎵 {res[2]} (Bazadan)")
        else:
            bot.send_audio(chat_id, res[1], caption=f"🎵 {res[2]} (Bazadan)")
        return

    # 2. AGAR BAZADA YO'Q BO'LSA - YUKLASH
    wait = bot.send_message(chat_id, "🔎") # Tezkor reaksiya
    threading.Thread(target=core_downloader, args=(chat_id, query, wait.message_id)).start()

def core_downloader(chat_id, query, wait_id):
    is_link = "http" in query
    search_q = query if is_link else f"ytsearch1:{query}"
    
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(search_q, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            file_path = ydl.prepare_filename(entry)
            title = entry.get('title', 'Musiqa')
            
            video_id, audio_id = None, None
            
            # Musiqa yuborish
            with open(file_path, 'rb') as f:
                sent_audio = bot.send_audio(chat_id, f, title=title, caption=f"✅ {title}")
                audio_id = sent_audio.audio.file_id
            
            # Agar foydalanuvchi link yuborgan bo'lsa, videoni ham yuborishga harakat qiladi
            if is_link:
                try:
                    with open(file_path, 'rb') as f:
                        sent_video = bot.send_video(chat_id, f, caption=f"🎬 {title}")
                        video_id = sent_video.video.file_id
                except: pass

            # BAZAGA QO'SHISH
            cur.execute("INSERT OR REPLACE INTO storage (query, video_id, audio_id, title) VALUES (?, ?, ?, ?)", 
                        (query.lower(), video_id, audio_id, title))
            conn.commit()

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, wait_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Xatolik: {str(e)[:50]}...", chat_id, wait_id)

if __name__ == "__main__":
    keep_alive()
    print("Bot is ready!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
