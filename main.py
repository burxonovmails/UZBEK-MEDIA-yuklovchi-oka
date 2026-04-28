import telebot
import yt_dlp
import os
import threading
from telebot import types
from flask import Flask
from threading import Thread

# --- RENDER VEB-SERVER ---
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

YTDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'max_filesize': 50 * 1024 * 1024,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
}

# --- MENU TUGMALARI ---
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔍 Nom orqali qidirish"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 
                     f"👋 **Salom! Men {BOT_USERNAME} botiman.**\n\nLink yuboring yoki quyidagi tugmani bosing:", 
                     parse_mode="Markdown", 
                     reply_markup=main_keyboard())

# --- QIDIRISH COMMANDASI ---
@bot.message_handler(func=lambda m: m.text == "🔍 Nom orqali qidirish")
def ask_search(message):
    msg = bot.send_message(message.chat.id, "🎶 Musiqa nomi yoki ijrochisini yozing:", 
                           reply_markup=types.ReplyKeyboardRemove())
    # Foydalanuvchining keyingi yozgan xabarini kutadi
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    query = message.text
    chat_id = message.chat.id
    
    if query == "/start": 
        start(message)
        return

    wait = bot.send_message(chat_id, "🔎 Qidirilmoqda...", reply_markup=main_keyboard())
    threading.Thread(target=download_core, args=(chat_id, f"ytsearch1:{query}", wait.message_id, False)).start()

# --- LINKLARNI TUTISH ---
@bot.message_handler(func=lambda m: "http" in m.text)
def handle_link(message):
    chat_id = message.chat.id
    wait = bot.send_message(chat_id, "📥 Link tahlil qilinmoqda...")
    threading.Thread(target=download_core, args=(chat_id, message.text, wait.message_id, True)).start()

# --- YUKLASH MARKAZI ---
def download_core(chat_id, query, wait_id, is_link):
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(query, download=True)
            entry = info['entries'][0] if 'entries' in info else info
            file_path = ydl.prepare_filename(entry)
            title = entry.get('title', "Musiqa")

            with open(file_path, 'rb') as f:
                if is_link:
                    # Link bo'lsa video va audio yuborish
                    bot.send_video(chat_id, f, caption=f"🎬 {title}\n\n👤 {BOT_USERNAME}")
                    f.seek(0) # Faylni boshidan o'qish
                    bot.send_audio(chat_id, f, caption=f"🎵 {title}\n\n👤 {BOT_USERNAME}")
                else:
                    # Qidiruv bo'lsa faqat audio
                    bot.send_audio(chat_id, f, caption=f"🎵 {title}\n\n👤 {BOT_USERNAME}")

            if os.path.exists(file_path):
                os.remove(file_path)
            bot.delete_message(chat_id, wait_id)

    except Exception:
        bot.edit_message_text("❌ Topilmadi yoki fayl juda katta (Max: 50MB).", chat_id, wait_id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
