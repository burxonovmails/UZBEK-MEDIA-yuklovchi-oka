import telebot
import yt_dlp
import os
import threading
from telebot import types
from flask import Flask
from threading import Thread

# --- RENDER SERVERINI UYG'OQ TUTISH ---
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
BOT_USERNAME = "@uzbemediarobot"

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# --- VIDEO VA AUDIO UCHUN UMUMIY SOZLAMALAR ---
YTDL_OPTS_VIDEO = {
    'format': 'best', # Eng yaxshi video format
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'max_filesize': 50 * 1024 * 1024,
    'quiet': True
}

YTDL_OPTS_AUDIO = {
    'format': 'bestaudio/best', # Faqat musiqa
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'max_filesize': 50 * 1024 * 1024,
    'quiet': True
}

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔍 Nom orqali qidirish"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"👋 Salom! Men musiqa va video yuklovchi okaman.", reply_markup=main_keyboard())

# --- NOM ORQALI QIDIRISH (FAQAT AUDIO) ---
@bot.message_handler(func=lambda m: m.text == "🔍 Nom orqali qidirish")
def ask_search(message):
    msg = bot.send_message(message.chat.id, "🎶 Musiqa nomi yoki ijrochisini yozing:")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text.strip()
    if query == "/start": return start(message)
    wait = bot.send_message(message.chat.id, "🔎")
    threading.Thread(target=download_logic, args=(message.chat.id, f"ytsearch1:{query}", wait.message_id, False)).start()

# --- LINK ORQALI YUKLASH (VIDEO + AUDIO) ---
@bot.message_handler(func=lambda m: "http" in m.text)
def handle_link(message):
    wait = bot.send_message(message.chat.id, "🔎")
    threading.Thread(target=download_logic, args=(message.chat.id, message.text, wait.message_id, True)).start()

def download_logic(chat_id, query, wait_id, is_link):
    opts = YTDL_OPTS_VIDEO if is_link else YTDL_OPTS_AUDIO
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            file_path = ydl.prepare_filename(entry)
            title = entry.get('title', "Media")

            with open(file_path, 'rb') as f:
                if is_link:
                    # Link bo'lsa ham video, ham audio yuboradi
                    bot.send_video(chat_id, f, caption=f"🎬 {title}\n\n👤 {BOT_USERNAME}")
                    f.seek(0)
                    bot.send_audio(chat_id, f, caption=f"🎵 {title}\n\n👤 {BOT_USERNAME}")
                else:
                    # Qidiruv bo'lsa faqat audio
                    bot.send_audio(chat_id, f, caption=f"🎵 {title}\n\n👤 {BOT_USERNAME}")

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, wait_id)
    except Exception:
        bot.edit_message_text("❌ Xatolik: Yuklab bo'lmadi yoki fayl juda katta.", chat_id, wait_id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
