import telebot
import yt_dlp
import os
import threading
import sqlite3
from telebot import types
from flask import Flask
from threading import Thread

# --- RENDER SERVERINI "UYG'OQ" TUTISH ---
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
TOKEN = "8721093015:AAGpOgNz4npcO2fA-rNdMecN4T0mMlI-Y6A" # BotFather'dan olingan token
bot = telebot.TeleBot(TOKEN)
BOT_USERNAME = "@uzbemediarobot"

# --- BAZA (TEZKORLIK UCHUN) ---
conn = sqlite3.connect('cache.db', check_same_thread=False)
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS storage (query TEXT, file_id TEXT, title TEXT)')
conn.commit()

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# --- YUKLASH SOZLAMALARI (TURBO) ---
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'socket_timeout': 10,
    'source_address': '0.0.0.0',
    'default_search': 'ytsearch1:',
}

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔍 Nom orqali qidirish"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"👋 Salom! Men {BOT_USERNAME} botiman.", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔍 Nom orqali qidirish")
def ask_search(message):
    msg = bot.send_message(message.chat.id, "🎶 Musiqa nomini yozing:")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text.strip().lower()
    if query == "/start": return start(message)

    # 1. BAZADAN TEKSHIRISH (Agar oldin qidirilgan bo'lsa)
    cur.execute("SELECT file_id, title FROM storage WHERE query = ?", (query,))
    res = cur.fetchone()
    if res:
        bot.send_audio(message.chat.id, res[0], caption=f"🎵 {res[1]}\n\n👤 {BOT_USERNAME}")
        return

    wait = bot.send_message(message.chat.id, "🔎")
    threading.Thread(target=download_core, args=(message.chat.id, f"ytsearch1:{query}", wait.message_id, query)).start()

@bot.message_handler(func=lambda m: "http" in m.text)
def handle_link(message):
    wait = bot.send_message(message.chat.id, "📥 Link tahlil qilinmoqda...")
    threading.Thread(target=download_core, args=(message.chat.id, message.text, wait.message_id, None)).start()

def download_core(chat_id, search_q, wait_id, original_query):
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(search_q, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            file_path = ydl.prepare_filename(entry)
            title = entry.get('title', "Media")

            with open(file_path, 'rb') as f:
                sent = bot.send_audio(chat_id, f, caption=f"🎵 {title}\n\n👤 {BOT_USERNAME}")
                
                # BAZAGA SAQLASH (Keyingi safar tezroq yuborish uchun)
                if original_query:
                    cur.execute("INSERT INTO storage VALUES (?, ?, ?)", (original_query, sent.audio.file_id, title))
                    conn.commit()

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, wait_id)

    except Exception:
        bot.edit_message_text("❌ Topilmadi. Iltimos, aniqroq yozing.", chat_id, wait_id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
