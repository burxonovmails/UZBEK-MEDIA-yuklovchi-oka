import telebot
import yt_dlp
import os
import threading
from telebot import types
from flask import Flask
from threading import Thread

# --- RENDER SERVERINI UYG'OQ TUTiSH ---
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

# --- OPTIMALLASHGAN QIDIRUV (RIZANOVA VA CHET EL UCHUN) ---
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 50 * 1024 * 1024,
    'default_search': 'ytsearch1:', 
    # Qidiruvni yanada aniq qilish uchun:
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

if not os.path.exists('downloads'):
    os.makedirs('downloads')

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔍 Nom orqali qidirish"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f"👋 Salomlar , Hohlagan musiqangiz yoki ijtimoiy tarmoqdagi videolaringizni biz bilan 1 soniya ichida YUKLAB oling.", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔍 Nom orqali qidirish")
def ask_search(message):
    msg = bot.send_message(message.chat.id, "🎶 Musiqa nomi yoki ijrochisini yozing (Masalan: Jaloliddin Ahmadaliyev yoki Eminem):")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text.strip()
    if query == "/start": return start(message)
    
    # O'zbek musiqalarini RizaNova va boshqa rasmiy kanallardan afzal ko'rish uchun:
    search_query = f"ytsearch1:{query} official audio" 
    
    wait = bot.send_message(message.chat.id, "🔎 Qidirilmoqda, biroz kuting...")
    threading.Thread(target=download_core, args=(message.chat.id, search_query, wait.message_id)).start()

@bot.message_handler(func=lambda m: "http" in m.text)
def handle_link(message):
    wait = bot.send_message(message.chat.id, "📥")
    threading.Thread(target=download_core, args=(message.chat.id, message.text, wait.message_id)).start()

def download_core(chat_id, query, wait_id):
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(query, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            
            # Faylni topish
            file_path = ydl.prepare_filename(entry).replace('.webm', '.mp3').replace('.m4a', '.mp3')
            title = entry.get('title', "Musiqa")

            with open(file_path, 'rb') as f:
                bot.send_audio(chat_id, f, caption=f"🎵 {title}\n\n👤 {BOT_USERNAME}")

            if os.path.exists(file_path): os.remove(file_path)
            bot.delete_message(chat_id, wait_id)

    except Exception:
        bot.edit_message_text("❌ Kechirasiz, qidiruv natija bermadi. Iltimos, boshqacha yozib ko'ring.", chat_id, wait_id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
