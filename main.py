import telebot
import sqlite3
from datetime import datetime
import os
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import random

# List teks acak untuk footer
FOOTER_TEXTS = [
    "Buruan ambil sebelum kehabisan",
    "Jangan sampai kelewatan",
    "Promo terbatas, gaskeun",
    "Stok terbatas, buruan",
    "Keburu habis nih",
    "Jangan ketinggalan promonya",
    "Ambil sekarang juga",
    "Promo spesial hari ini",
    "Kesempatan terbatas",
    "Jangan sampai menyesal",
    "Buruan checkout",
    "Promo dadakan nih",
    "Stok masih ada",
    "Ambil sebelum kehabisan",
    "Promo gila-gilaan",
    "Flash sale terbatas",
    "Jangan sampai ketinggalan",
    "Buruan sebelum hangus",
    "Promo super mantap",
    "Kesempatan emas nih",
    "Jangan lewatkan kesempatan ini",
    "Ambil promonya sekarang",
    "Stok masih tersedia",
    "Harga spesial hari ini",
    "Promo kilat nih",
    "Buruan serbu",
    "Jangan sampai nyesel",
    "Promo super gila",
    "Kesempatan langka",
    "Ambil sebelum sold out",
    "Flash deal terbatas",
    "Stok tinggal dikit",
    "Promo mantul nih",
    "Buruan gas",
    "Jangan sampai telat",
    "Promo super hot",
    "Kesempatan bagus nih",
    "Ambil sebelum hilang",
    "Flash sale super",
    "Stok terbatas banget",
    "Promo gak akan terulang",
    "Buruan checkout gan",
    "Jangan sampai kelewat",
    "Promo super keren",
    "Kesempatan super nih",
    "Ambil sebelum lenyap",
    "Flash deal mantap",
    "Stok tinggal sedikit",
    "Promo super wow",
    "Buruan ambil sis",
    "Jangan sampai hangus",
    "Promo terbaik nih",
    "Kesempatan top nih",
    "Ambil sebelum habis",
    "Flash sale gila",
    "Stok limited edition",
    "Promo super dahsyat",
    "Buruan klik sis",
    "Jangan sampai habis",
    "Promo super mantul",
    "Kesempatan keren nih",
    "Ambil sebelum raib",
    "Flash deal super",
    "Stok super limited",
    "Promo gokil nih",
    "Buruan serbu gan",
    "Jangan sampai lewat",
    "Promo super gokil",
    "Kesempatan mantap nih",
    "Ambil sebelum punah",
    "Flash sale dahsyat",
    "Stok hampir habis",
    "Promo dahsyat nih",
    "Buruan ambil bro",
    "Jangan sampai missed",
    "Promo super heboh",
    "Kesempatan oke nih",
    "Ambil sekarang ya",
    "Flash deal keren",
    "Stok menipis nih",
    "Promo super jos",
    "Buruan checkout sis",
    "Jangan sampai zonk",
    "Promo mantap jiwa",
    "Kesempatan super mantul",
    "Ambil sebelum sold",
    "Flash sale super keren",
    "Stok tinggal dikit nih",
    "Promo super mantap jiwa",
    "Buruan ambil gan",
    "Jangan sampai batal",
    "Promo super dahsyat nih",
    "Kesempatan gokil nih",
    "Ambil sebelum expired",
    "Flash deal super mantap",
    "Stok super terbatas",
    "Promo super gokil abis",
    "Buruan checkout bro",
    "Jangan sampai gagal",
    "Promo super keren nih",
    "Kesempatan super gokil",
    "Ambil sebelum ludes",
    "Flash sale super mantul",
    "Stok limited banget"
]

# Initialize bot with your token
bot = telebot.TeleBot("8136429316:AAFKaVqJuib6SzbasIuvvohw22X4jepTCRI")
CHANNEL_ID = "@thr_spay"
ADMIN_USERNAME = "@aku_aldo"  # For display purposes with underscore
ADMIN_ID = 1704985763  # Your numeric Telegram ID

# Bot configuration (should be in a more robust location in production)
bot_config = {
    'is_maintenance': False,
    'maintenance_time': None
}

# Valid domains
VALID_DOMAINS = [
    "shopee.co.id",
    "event.shopee.co.id",
    "shopee.co.id/m/",
    "shopeepay.co.id",
    "app.u.shopeepay.co.id",
    "invite.shopee.co.id"
]

def setup_database():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  link TEXT,
                  caption TEXT,
                  image_text TEXT,
                  timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_limits 
                 (user_id INTEGER PRIMARY KEY,
                  post_count INTEGER DEFAULT 0,
                  last_reset DATE)''')
    conn.commit()
    conn.close()

def check_user_limit(user_id):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    today = datetime.now().date()
    
    c.execute("SELECT post_count, last_reset FROM user_limits WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if not result:
        c.execute("INSERT INTO user_limits (user_id, post_count, last_reset) VALUES (?, 0, ?)", 
                 (user_id, today))
        conn.commit()
        conn.close()
        return True
        
    post_count, last_reset = result
    last_reset = datetime.strptime(last_reset, '%Y-%m-%d').date()
    
    if last_reset < today:
        c.execute("UPDATE user_limits SET post_count = 0, last_reset = ? WHERE user_id = ?",
                 (today, user_id))
        conn.commit()
        conn.close()
        return True
        
    if post_count >= 10:  # Batas 10 post per hari
        conn.close()
        return False
        
    c.execute("UPDATE user_limits SET post_count = post_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True

def is_valid_shopee_link(link):
    return any(domain in link.lower() for domain in VALID_DOMAINS)

def extract_text_from_image(photo):
    try:
        # Download photo
        file_info = bot.get_file(photo.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Convert to image
        image = Image.open(BytesIO(downloaded_file))
        
        # Pre-process image
        image = image.convert('L')  # Convert to grayscale
        
        # Extract text with custom config
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)
        
        if not text.strip():
            return None
            
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return None

def escape_markdown(text):
    chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text

def owner_required(func):
    def wrapper(message):
        if message.from_user.id == ADMIN_ID:
            return func(message)
        else:
            bot.reply_to(message, "Perintah ini hanya untuk admin.")
    return wrapper

@bot.message_handler(commands=['maintenance'])
@owner_required
def set_maintenance(message):
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            bot.reply_to(message, "❌ Format: /maintenance <waktu maintenance>")
            return

        maintenance_time = args[1]
        bot_config['is_maintenance'] = True
        bot_config['maintenance_time'] = maintenance_time

        bot.reply_to(message, f"✅ Bot dalam mode maintenance\nWaktu maintenance: {maintenance_time}")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['online'])
@owner_required
def set_online(message):
    try:
        bot_config['is_maintenance'] = False
        bot_config['maintenance_time'] = None
        bot.reply_to(message, "✅ Bot kembali online!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

def check_maintenance(message):
    if bot_config['is_maintenance'] and message.from_user.id != ADMIN_ID:
        bot.reply_to(
            message,
            f"⚠️ Bot sedang dalam pemeliharaan\n"
            f"Dimulai dari: {bot_config['maintenance_time']}\n"
            f"Silakan coba lagi nanti!"
        )
        return True
    return False

@bot.message_handler(commands=['pesan'])
def send_message_to_owner(message):
    if check_maintenance(message):
        return
    msg = bot.reply_to(message, "✍️ Tulis pesan yang ingin Anda sampaikan ke owner:")
    bot.register_next_step_handler(msg, process_owner_message)

def process_owner_message(message):
    try:
        user_info = f"Pesan dari User ID: {message.from_user.id}"
        if message.from_user.username:
            user_info += f" (@{message.from_user.username})"
            
        # Add reply markup
        markup = telebot.types.InlineKeyboardMarkup()
        reply_btn = telebot.types.InlineKeyboardButton("Balas", callback_data=f"reply_{message.from_user.id}")
        markup.add(reply_btn)
            
        owner_message = f"💌 {user_info}\n\n{message.text}"
        bot.send_message(ADMIN_ID, owner_message, reply_markup=markup)
        bot.reply_to(message, "✅ Pesan telah terkirim ke owner!")
    except Exception as e:
        bot.reply_to(message, "❌ Gagal mengirim pesan ke owner.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def reply_to_user(call):
    if call.from_user.id != ADMIN_ID:
        return
        
    user_id = call.data.split('_')[1]
    msg = bot.reply_to(call.message, "✍️ Tulis balasan untuk user:")
    bot.register_next_step_handler(msg, send_reply_to_user, user_id)

# Track active conversations
active_conversations = {}

def send_reply_to_user(message, user_id):
    try:
        sent_msg = bot.send_message(user_id, f"💬 Balasan dari Owner:\n\n{message.text}")
        # Add reaction buttons
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(
            telebot.types.InlineKeyboardButton("❤️", callback_data=f"react_love_{sent_msg.message_id}"),
            telebot.types.InlineKeyboardButton("Balas", callback_data=f"reply_{user_id}")
        )
        bot.edit_message_reply_markup(user_id, sent_msg.message_id, reply_markup=markup)
        bot.reply_to(message, "✅ Balasan terkirim!")
        
        # Start conversation mode
        active_conversations[int(user_id)] = True
        
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal mengirim balasan: {str(e)}")

@bot.message_handler(commands=['pesan'])
def send_direct_message(message):
    if message.from_user.id == ADMIN_ID:
        # For owner: /pesan <user_id> <message>
        try:
            args = message.text.split(maxsplit=2)
            if len(args) < 3:
                bot.reply_to(message, "Format: /pesan <user_id> <pesan>")
                return
            user_id = int(args[1])
            msg_text = args[2]
            send_reply_to_user(types.Message(text=msg_text), user_id)
            active_conversations[user_id] = True
        except:
            bot.reply_to(message, "❌ Format salah atau user ID tidak valid")
    else:
        # For users
        if check_maintenance(message):
            return
        msg = bot.reply_to(message, "✍️ Tulis pesan yang ingin Anda sampaikan ke owner:")
        bot.register_next_step_handler(msg, process_owner_message)

@bot.message_handler(commands=['stop'])
def stop_conversation(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        try:
            args = message.text.split()
            target_id = int(args[1]) if len(args) > 1 else None
            if target_id and target_id in active_conversations:
                del active_conversations[target_id]
                bot.reply_to(message, f"✅ Obrolan dengan user {target_id} dihentikan")
            else:
                bot.reply_to(message, "❌ User ID tidak valid atau tidak dalam obrolan")
        except:
            bot.reply_to(message, "Format: /stop <user_id>")
    elif user_id in active_conversations:
        del active_conversations[user_id]
        bot.reply_to(message, "✅ Obrolan dengan owner dihentikan")

@bot.callback_query_handler(func=lambda call: call.data.startswith('react_'))
def handle_reaction(call):
    try:
        reaction = call.data.split('_')[1]
        msg_id = call.data.split('_')[2]
        user = call.from_user.first_name
        
        if call.from_user.id == ADMIN_ID:
            # Owner can add reactions to messages
            reaction_type = ["👍", "❤️"] if reaction == "love" else ["👍"]
            try:
                bot.set_message_reaction(
                    chat_id=call.message.chat.id,
                    message_id=int(msg_id),
                    reaction=[{"type": "emoji", "emoji": r} for r in reaction_type]
                )
                bot.answer_callback_query(call.id, "✅ Reaksi ditambahkan!")
            except:
                bot.answer_callback_query(call.id, "❌ Gagal menambahkan reaksi")
        else:
            # Regular users see the old behavior
            reactions = {
                'like': '👍 Disukai',
                'love': '❤️ Dicintai'
            }
            bot.answer_callback_query(call.id, f"Anda bereaksi: {reactions[reaction]}")
            bot.send_message(ADMIN_ID, f"🔔 {user} {reactions[reaction]} pesan Anda (ID: {msg_id})")
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Gagal bereaksi")

@bot.message_handler(func=lambda message: message.from_user.id in active_conversations)
def handle_conversation(message):
    if message.from_user.id == ADMIN_ID:
        # Forward owner's message to the last user
        last_user = list(active_conversations.keys())[-1]
        send_reply_to_user(message, last_user)
    else:
        # Forward user's message to owner
        process_owner_message(message)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if check_maintenance(message):
        return
    is_admin = message.from_user.id == ADMIN_ID
    help_text = "🚀 *Selamat datang di Shopee Link Poster\\!*\n\n" \
                "*Perintah Umum:*\n" \
                "/start \\- Mulai bot\n" \
                "/help \\- Tampilkan bantuan\n" \
                "/privacy \\- Kebijakan privasi\n" \
                "/pesan \\- Kirim pesan ke owner\n\n" \
                "*Cara Penggunaan:*\n" \
                "\\- Kirim link Shopee langsung\n" \
                "\\- Kirim foto yang berisi link Shopee"
                
    if is_admin:
        help_text += "\n\n*Perintah Admin:*\n" \
                    "/owner \\- Info pemilik bot\n" \
                    "/stats \\- Statistik bot\n" \
                    "/maintenance \\- Mode maintenance\n" \
                    "/online \\- Mode online\n" \
                    "/list \\- Daftar user\n" \
                    "/bc \\- Broadcast pesan"
    bot.reply_to(message, help_text, parse_mode='MarkdownV2')

@bot.message_handler(commands=['owner'])
def show_owner(message):
    if check_maintenance(message):
        return
    owner_text = "👨‍💻 *Owner Bot*\n\n" \
                 "Owner: @aku\\_aldo\n" \
                 "Channel: @thr\\_spay\n\n" \
                 "Untuk pertanyaan dan kerjasama silakan hubungi owner\\."
    bot.reply_to(message, owner_text, parse_mode='MarkdownV2')

@bot.message_handler(commands=['privacy'])
def show_privacy(message):
    if check_maintenance(message):
        return
    privacy_text = "🔒 *Kebijakan Privasi Bot*\n\n" \
                   "1\\. Data yang dikumpulkan:\n" \
                   "   \\- User ID Telegram\n" \
                   "   \\- Link yang dibagikan\n" \
                   "   \\- Caption postingan\n\n" \
                   "2\\. Penggunaan data:\n" \
                   "   \\- Memposting ke channel\n" \
                   "   \\- Statistik penggunaan\n" \
                   "   \\- Mencegah spam\n\n" \
                   "3\\. Penghapusan data:\n" \
                   "   Hubungi @aku\\_aldo untuk menghapus data Anda\\."
    bot.reply_to(message, privacy_text, parse_mode='MarkdownV2')

@bot.message_handler(commands=['list'])
@owner_required
def list_users(message):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM posts")
    users = c.fetchall()
    conn.close()
    
    user_count = len(users)
    user_list = '\n'.join([f"- {user[0]}" for user in users])
    response = f"📊 Total Users: {user_count}\n\nDaftar User ID:\n{user_list}"
    bot.reply_to(message, response)

@bot.message_handler(commands=['bc'])
@owner_required
def broadcast_message(message):
    markup = telebot.types.InlineKeyboardMarkup()
    text_btn = telebot.types.InlineKeyboardButton("Text", callback_data="bc_text")
    photo_btn = telebot.types.InlineKeyboardButton("Photo", callback_data="bc_photo")
    button_msg_btn = telebot.types.InlineKeyboardButton("Button Message", callback_data="bc_button")
    markup.row(text_btn, photo_btn)
    markup.row(button_msg_btn)
    
    bot.reply_to(message, "Pilih jenis broadcast:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("bc_"))
def broadcast_callback(call):
    if call.from_user.id != ADMIN_ID:
        return
        
    broadcast_type = call.data[3:]
    if broadcast_type == "button":
        msg = bot.send_message(call.from_user.id, 
            "Kirim pesan dengan format:\n"
            "teks\n"
            "---\n"
            "text_tombol1|url1\n"
            "text_tombol2|url2")
        bot.register_next_step_handler(msg, process_button_broadcast)
    elif broadcast_type == "photo":
        msg = bot.send_message(call.from_user.id, 
            "Kirim foto dengan caption format:\n"
            "teks\n"
            "---\n"
            "text_tombol1|url1\n"
            "text_tombol2|url2")
        bot.register_next_step_handler(msg, process_photo_button_broadcast)
    elif broadcast_type == "text":
        msg = bot.send_message(call.from_user.id, "Kirim pesan yang ingin disebarkan:")
        bot.register_next_step_handler(msg, process_broadcast)

def process_photo_button_broadcast(message):
    try:
        if not message.photo:
            bot.reply_to(message, "❌ Mohon kirim foto dengan caption!")
            return
            
        # Parse caption format
        if not message.caption:
            bot.reply_to(message, "❌ Mohon sertakan caption dengan format yang benar!")
            return
            
        content = message.caption.split("\n---\n")
        if len(content) != 2:
            bot.reply_to(message, "❌ Format caption salah!")
            return
            
        text = content[0]
        buttons = content[1].strip().split("\n")
        
        # Create inline keyboard
        markup = telebot.types.InlineKeyboardMarkup()
        for button in buttons:
            try:
                text_btn, url = button.split("|")
                markup.add(telebot.types.InlineKeyboardButton(text_btn.strip(), url=url.strip()))
            except:
                continue
                
        # Get all users
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT user_id FROM posts")
        users = c.fetchall()
        conn.close()

        success = 0
        failed = 0
        
        # Send messages
        for user in users:
            try:
                bot.send_photo(user[0], message.photo[-1].file_id, caption=text, reply_markup=markup)
                success += 1
            except:
                failed += 1

        report = f"✅ Broadcast foto dengan tombol selesai!\n\n" \
                 f"Berhasil: {success}\n" \
                 f"Gagal: {failed}\n" \
                 f"Total user: {len(users)}"
        bot.reply_to(message, report)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error dalam broadcast: {str(e)}")

def process_button_broadcast(message):
    try:
        # Parse message format
        content = message.text.split("\n---\n")
        if len(content) != 2:
            bot.reply_to(message, "❌ Format pesan salah!")
            return
            
        text = content[0]
        buttons = content[1].strip().split("\n")
        
        # Create inline keyboard
        markup = telebot.types.InlineKeyboardMarkup()
        for button in buttons:
            try:
                text_btn, url = button.split("|")
                markup.add(telebot.types.InlineKeyboardButton(text_btn.strip(), url=url.strip()))
            except:
                continue
                
        # Get all users
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT user_id FROM posts")
        users = c.fetchall()
        conn.close()

        success = 0
        failed = 0
        
        # Send messages
        for user in users:
            try:
                bot.send_message(user[0], text, reply_markup=markup)
                success += 1
            except:
                failed += 1

        report = f"✅ Broadcast button message selesai!\n\n" \
                 f"Berhasil: {success}\n" \
                 f"Gagal: {failed}\n" \
                 f"Total user: {len(users)}"
        bot.reply_to(message, report)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Error dalam broadcast: {str(e)}")

def process_broadcast(message):
    try:
        # Get all unique users
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT user_id FROM posts")
        users = c.fetchall()
        conn.close()

        success = 0
        failed = 0
        
        # Send the broadcast message
        for user in users:
            try:
                if message.content_type == 'text':
                    bot.send_message(user[0], message.text)
                elif message.content_type == 'photo':
                    bot.send_photo(user[0], message.photo[-1].file_id, caption=message.caption)
                elif message.content_type == 'video':
                    bot.send_video(user[0], message.video.file_id, caption=message.caption)
                success += 1
            except Exception:
                failed += 1

        # Send report
        report = f"✅ Broadcast selesai!\n\n" \
                 f"Berhasil: {success}\n" \
                 f"Gagal: {failed}\n" \
                 f"Total user: {len(users)}"
        bot.reply_to(message, report)

    except Exception as e:
        bot.reply_to(message, f"❌ Error dalam broadcast: {str(e)}")

@bot.message_handler(commands=['stats'])
def get_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Perintah ini hanya untuk admin.")
        return

    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    
    # Get basic stats
    c.execute("SELECT COUNT(*) FROM posts")
    total_posts = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM posts") 
    unique_users = c.fetchone()[0]
    
    # Get today's stats
    today = datetime.now().date()
    c.execute("SELECT COUNT(*) FROM posts WHERE date(timestamp) = date('now')")
    posts_today = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM posts WHERE date(timestamp) = date('now')")
    active_users = c.fetchone()[0]
    
    # Get top posters
    c.execute("""
        SELECT user_id, COUNT(*) as post_count 
        FROM posts 
        GROUP BY user_id 
        ORDER BY post_count DESC 
        LIMIT 5
    """)
    top_posters = c.fetchall()
    
    conn.close()

    stats = f"📊 Statistik Bot:\n\n" \
           f"Total posts: {total_posts}\n" \
           f"Pengguna unik: {unique_users}\n" \
           f"\nHari ini:\n" \
           f"Posts: {posts_today}\n" \
           f"User aktif: {active_users}\n" \
           f"\nTop posters:\n" + \
           "\n".join([f"User {user_id}: {count} posts" for user_id, count in top_posters])
           
    bot.reply_to(message, stats)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not check_user_limit(message.from_user.id):
        bot.reply_to(message, "❌ Anda telah mencapai batas posting hari ini (10 post/hari).")
        return
    try:
        # Get text from image
        extracted_text = extract_text_from_image(message.photo[-1])

        if not extracted_text:
            bot.reply_to(message, "❌ Tidak dapat membaca teks dari foto.")
            return

        # Find Shopee links in extracted text
        words = extracted_text.split()
        shopee_link = None
        for word in words:
            if is_valid_shopee_link(word):
                shopee_link = word
                break

        if not shopee_link:
            bot.reply_to(message, "❌ Tidak menemukan link Shopee yang valid dalam foto.")
            return

        # Store photo and link
        user_data = {
            'user_id': message.from_user.id,
            'link': shopee_link,
            'photo': message.photo[-1].file_id
        }

        # Ask for caption
        msg = bot.reply_to(message, "✍️ Silakan kirim caption untuk postingan ini:")
        bot.register_next_step_handler(msg, process_caption_with_photo, user_data)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(func=lambda message: any(domain in message.text.lower() for domain in VALID_DOMAINS))
def handle_link(message):
    if check_maintenance(message):
        return
    if not check_user_limit(message.from_user.id):
        bot.reply_to(message, "❌ Anda telah mencapai batas posting hari ini (10 post/hari).")
        return
    if not is_valid_shopee_link(message.text):
        bot.reply_to(message, "❌ Mohon kirim link Shopee yang valid.")
        return

    user_data = {'user_id': message.from_user.id, 'link': message.text}
    msg = bot.reply_to(message, "✍️ Silakan kirim caption untuk link ini:")
    bot.register_next_step_handler(msg, process_caption, user_data)

def process_caption_with_photo(message, user_data):
    try:
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, link, caption, timestamp) VALUES (?, ?, ?, ?)",
                  (user_data['user_id'], user_data['link'], message.text, datetime.now()))
        conn.commit()
        conn.close()

        # Format message with spoiler for both photo and link
        escaped_link = escape_markdown(user_data['link'])
        escaped_caption = escape_markdown(message.text)

        # Send photo with spoiler
        bot.send_photo(
            CHANNEL_ID,
            user_data['photo'],
            caption=f"*{escaped_caption}*\n\n"
                   f"||{escaped_link}||\n\n"
                   f"_Dikirim melalui_ @thrspaybot\n"
                   f"*\\~ {escape_markdown(random.choice(FOOTER_TEXTS))} \\~*",
            parse_mode='MarkdownV2',
            has_spoiler=True
        )

        bot.reply_to(message, "✅ Berhasil posting ke channel!")
        bot.send_message(ADMIN_ID, f"Postingan baru dari user {message.from_user.id}\nCaption: {message.text}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error posting ke channel: {str(e)}")
        bot.send_message(ADMIN_ID, f"Error dalam postingan user {message.from_user.id}: {str(e)}")

def process_caption(message, user_data):
    try:
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, link, caption, timestamp) VALUES (?, ?, ?, ?)",
                  (user_data['user_id'], user_data['link'], message.text, datetime.now()))
        conn.commit()
        conn.close()

        escaped_link = escape_markdown(user_data['link'])
        escaped_caption = escape_markdown(message.text)

        post_text = f"*{escaped_caption}*\n\n" \
                    f"||{escaped_link}||\n\n" \
                    f"_Dikirim melalui_ @thrspaybot\n" \
                    f"*\\~ {escape_markdown(random.choice(FOOTER_TEXTS))} \\~*"

        bot.send_message(CHANNEL_ID, post_text, parse_mode='MarkdownV2')
        bot.reply_to(message, "✅ Berhasil posting ke channel!")
        bot.send_message(ADMIN_ID, f"Postingan baru dari user {message.from_user.id}\nCaption: {message.text}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error posting ke channel: {str(e)}")
        bot.send_message(ADMIN_ID, f"Error dalam postingan user {message.from_user.id}: {str(e)}")

if __name__ == "__main__":
    setup_database()
    print("Bot started...")
    bot.infinity_polling()
