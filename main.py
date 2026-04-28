import telebot
import yt_dlp
import os
import sqlite3
import threading
from telebot import types
from flask import Flask
from threading import Thread

# --- RENDER PORTINI BOSHQARISH ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Live!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- SOZLAMALAR ---
# O'zingizning to'liq tokeningizni qo'ying (Masalan: "123456:ABCDE...")
TOKEN = "8721093015:AAGpOgNz4npcO2fA-rNdMecN4T0mMlI-Y6A" 
bot = telebot.TeleBot(TOKEN, threaded=True)

# Baza (Tezlikni oshirish uchun kesh)
conn = sqlite3.connect('fast_music.db', check_same_thread=False)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS storage (query TEXT PRIMARY KEY, video_id TEXT, audio_id TEXT, title TEXT)')
conn.commit()

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# --- YTDL TURBO SOZLAMALARI ---
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 48 * 1024 * 1024, # Render uchun 48MB xavfsiz limit
}

# --- ASOSIY KOMANDALAR ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔍 Nom orqali qidirish"))
    bot.send_message(message.chat.id, "🚀 **Professional Downloader!**\n\nMusiqa nomini yozing yoki link yuboring:", 
                     parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔍 Nom orqali qidirish")
def search_mode(message):
    msg = bot.send_message(message.chat.id, "✍️ Musiqa va ijrochi nomini yozing:")
    bot.register_next_step_handler(msg, handle_query)

@bot.message_handler(func=lambda m: True)
def handle_query(message):
    query = message.text.strip().lower()
    chat_id = message.chat.id

    # 1. BAZADAN TEZKOR QIDIRISH (Kesh)
    cur.execute("SELECT video_id, audio_id, title FROM storage WHERE query = ?", (query,))
    res = cur.fetchone()
    
    if res:
        if "http" in query:
            if res[0]: bot.send_video(chat_id, res[0], caption=f"🎬 {res[2]}")
            if res[1]: bot.send_audio(chat_id, res[1], caption=f"🎵 {res[2]}")
        else:
            bot.send_audio(chat_id, res[1], caption=f"🎵 {res[2]}")
        return

    # 2. YUKLASH (Thread orqali)
    wait = bot.send_message(chat_id, "🔎")
    threading.Thread(target=download_core, args=(chat_id, query, wait.message_id)).start()

def download_core(chat_id, query, wait_id):
    is_link = "http" in query
    search_q = query if is_link else f"ytsearch1:{query}"
    
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(search_q, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            file_path = ydl.prepare_filename(entry)
            # Rasmda chiqqan syntax xatosi tuzatildi
            title = entry.get('title', "Noma'lum musiqa")
            
            audio_id, video_id = None, None
            
            # Musiqani yuborish
            with open(file_path, 'rb') as f:
                sent_audio = bot.send_audio(chat_id, f, caption=f"✅ {title}")
                audio_id = sent_audio.audio.file_id
            
            # Video link bo'lsa, videoni ham yuborish
            if is_link:
                try:
                    with open(file_path, 'rb') as f:
                        sent_video = bot.send_video(chat_id, f, caption=f"🎬 {title}")
                        video_id = sent_video.video.file_id
                except:
                    pass

            # BAZAGA SAQLASH
            cur.execute("INSERT OR REPLACE INTO storage (query, video_id, audio_id, title) VALUES (?, ?, ?, ?)", 
                        (query, video_id, audio_id, title))
            conn.commit()

            if os.path.exists(file_path):
                os.remove(file_path)
            bot.delete_message(chat_id, wait_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Topilmadi yoki juda katta. (Max: 50MB)", chat_id, wait_id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling(timeout=15, long_polling_timeout=5)
