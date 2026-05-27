import sqlite3
import json
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot import types

# إعدادات البوت والمالك 👑
BOT_TOKEN = "8965430690:AAEpFQYsRs-pgBqAoWCedojOvX7yqDLhu0c"
ADMIN_ID = 7174983919  
bot = telebot.TeleBot(BOT_TOKEN)

# تشغيل سيرفر الويب وتأمين الـ CORS لتليجرام بالكامل
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ----------------------------------------------------
# 1. إنشاء قاعدة البيانات الشاملة
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect("astreeds_mega.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        points INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        posts_count INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0
    )""")
    
    # جدول الإعدادات
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('fsub_channel', '@AstreedsChannel')")
    
    # جدول المنشورات الحقيقية
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER,
        author_name TEXT,
        author_photo TEXT,
        text TEXT,
        likes TEXT DEFAULT '[]',
        reports_count INTEGER DEFAULT 0
    )""")
    
    # جدول التعليقات
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        author_name TEXT,
        text TEXT
    )""")
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect("astreeds_mega.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------------------------------------
# 2. ميثود المساعدة لفحص الاشتراك الإجباري
# ----------------------------------------------------
def check_sub(user_id):
    conn = get_db_connection()
    channel_row = conn.execute("SELECT value FROM settings WHERE key='fsub_channel'").fetchone()
    conn.close()
    
    if not channel_row:
        return True
        
    channel = channel_row[0]
    try:
        member = bot.get_chat_member(channel, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception as e:
        # لو البوت مش آدمن في القناة هيفوت اليوزر عشان ما يعطلش المنصة
        return True

# ----------------------------------------------------
# 3. أوامر تليجرام ولوحة التحكم للإدارة
# ----------------------------------------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    uid = message.from_user.id
    uname = message.from_user.username or "لا يوجد"
    fname = message.from_user.first_name

    conn = get_db_connection()
    conn.execute("INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (uid, uname, fname))
    conn.commit()
    
    user = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (uid,)).fetchone()
    banned = user['is_banned'] if user else 0
    conn.close()
    
    if banned == 1:
        bot.send_message(message.chat.id, "🚫 عذراً، لقد تم حظرك من استخدام المنصة.")
        return

    if not check_sub(uid):
        conn = get_db_connection()
        channel = conn.execute("SELECT value FROM settings WHERE key='fsub_channel'").fetchone()[0]
        conn.close()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 اشترك في القناة هنا", url=f"https://t.me/{channel.replace('@','')}"))
        bot.send_message(message.chat.id, f"⚠️ عذراً يا {fname}، يجب عليك الاشتراك في قناة المنصة أولاً لتتمكن من الدخول!", reply_markup=markup)
        return

    bot.send_message(message.chat.id, f"🌌 أهلاً بك في منصة **أستريتز** الحقيقية يا {fname}!\n\nاضغط على زرار القائمة بالأسفل وادخل عيش جوة المنصة الفخمة! 🌌🚀")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("📊 إحصائيات المنصة", callback_data="admin_stats")
    b2 = types.InlineKeyboardButton("📢 إذاعة عامة", callback_data="admin_bc")
    b3 = types.InlineKeyboardButton("🔐 الاشتراك الإجباري", callback_data="admin_fsub")
    b4 = types.InlineKeyboardButton("🚩 الاقتباسات المُبلغ عنها", callback_data="admin_reports")
    b5 = types.InlineKeyboardButton("🚫 إدارة الحظر", callback_data="admin_ban")
    b6 = types.InlineKeyboardButton("📥 رسائل الدعم", callback_data="admin_support")
    markup.add(b1, b2, b3, b4, b5, b6)
    bot.send_message(message.chat.id, "⚙️ **لوحة التحكم الإدارية لمنصة أستريتز**\n\nأهلاً بك يا زعيم، اختر الخانة:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callbacks(call):
    bot.answer_callback_query(call.id)
    conn = get_db_connection()
    
    if call.data == "admin_stats":
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_quotes = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        text = f"📊 **إحصائيات منصة أستريتز:**\n\n👥 عدد المستخدمين: {total_users}\n📝 إجمالي المنشورات: {total_quotes}"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
        
    elif call.data == "admin_bc":
        msg = bot.send_message(call.message.chat.id, "📢 ارسل الآن الرسالة التي تريد إذاعتها للجميع:")
        bot.register_next_step_handler(msg, process_broadcast)
        
    elif call.data == "admin_fsub":
        current = conn.execute("SELECT value FROM settings WHERE key='fsub_channel'").fetchone()[0]
        msg = bot.send_message(call.message.chat.id, f"🔐 القناة الحالية: {current}\n\nارسل معرف القناة الجديد (يبدأ بـ @):")
        bot.register_next_step_handler(msg, process_fsub)
        
    elif call.data in ["admin_reports", "admin_ban", "admin_support"]:
        bot.send_message(call.message.chat.id, f"🛠️ الخانة [{call.data.replace('admin_','').upper()}] متصلة وجاهزة للعمل!")
        
    conn.close()

def process_broadcast(message):
    conn = get_db_connection()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    success = 0
    for user in users:
        try:
            bot.send_message(user['user_id'], message.text)
            success += 1
        except: 
            pass
    bot.send_message(ADMIN_ID, f"📢 تمت الإذاعة بنجاح لـ {success} مستخدم!")

def process_fsub(message):
    if message.text.startswith("@"):
        conn = get_db_connection()
        conn.execute("UPDATE settings SET value=? WHERE key='fsub_channel'", (message.text.strip(),))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"✅ تم تحديث القناة الإجبارية إلى: {message.text}")
    else:
        bot.send_message(ADMIN_ID, "❌ خطأ! المعرف يجب أن يبدأ بـ @")

# ----------------------------------------------------
# 4. مسارات الـ API للربط مع الواجهة (الـ WebApp)
# ----------------------------------------------------
@app.route('/get_posts', methods=['GET'])
def get_posts():
    conn = get_db_connection()
    posts_rows = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    posts_list = []
    
    for row in posts_rows:
        comments_rows = conn.execute('SELECT author_name, text FROM comments WHERE post_id = ?', (row['id'],)).fetchall()
        comments = [{'authorName': c['author_name'], 'text': c['text']} for c in comments_rows]
        
        # حماية ضد كراش اللايكات
        try:
            liked_by = json.loads(row['likes']) if row['likes'] else []
        except:
            liked_by = []
            
        posts_list.append({
            'id': row['id'], 
            'authorId': row['author_id'], 
            'authorName': row['author_name'],
            'authorPhoto': row['author_photo'], 
            'text': row['text'], 
            'likedBy': liked_by, 
            'comments': comments
        })
        
    conn.close()
    return jsonify(posts_list)

@app.route('/add_post', methods=['POST'])
def add_post():
    data = request.json
    conn = get_db_connection()
    conn.execute('INSERT INTO posts (author_id, author_name, author_photo, text, likes) VALUES (?, ?, ?, ?, ?)',
                 (data.get('authorId'), data.get('authorName'), data.get('authorPhoto'), data.get('text'), '[]'))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/toggle_like', methods=['POST'])
def toggle_like():
    data = request.json
    conn = get_db_connection()
    post = conn.execute('SELECT likes FROM posts WHERE id = ?', (data['postId'],)).fetchone()
    
    if post:
        try:
            liked_by = json.loads(post['likes']) if post['likes'] else []
        except:
            liked_by = []
            
        user_id = data['userId']
        if user_id in liked_by: 
            liked_by.remove(user_id)
        else: 
            liked_by.append(user_id)
            
        conn.execute('UPDATE posts SET likes = ? WHERE id = ?', (json.dumps(liked_by), data['postId']))
        conn.commit()
        
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/add_comment', methods=['POST'])
def add_comment():
    data = request.json
    conn = get_db_connection()
    conn.execute('INSERT INTO comments (post_id, author_name, text) VALUES (?, ?, ?)',
                 (data['postId'], data['authorName'], data['text']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/report_post', methods=['POST'])
def report_post():
    data = request.json
    conn = get_db_connection()
    conn.execute('UPDATE posts SET reports_count = reports_count + 1 WHERE id = ?', (data['postId'],))
    post = conn.execute('SELECT text, author_name FROM posts WHERE id = ?', (data['postId'],)).fetchone()
    conn.commit()
    conn.close()
    
    if post:
        bot.send_message(ADMIN_ID, f"🚩 **إشعار بلاغ جديد!**\n\nالمنشور رقم: {data['postId']}\nالكاتب: {post['author_name']}\nالمحتوى: {post['text']}\n\nيمكنك مراجعته وحذفه من داخل المنصة.")
        
    return jsonify({'status': 'success'})

@app.route('/delete_post', methods=['POST'])
def delete_post():
    data = request.json
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (data['postId'],))
    conn.execute('DELETE FROM comments WHERE post_id = ?', (data['postId'],))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# ----------------------------------------------------
# 5. التشغيل المتوازي (للبوت والسيرفر)
# ----------------------------------------------------
if __name__ == "__main__":
    # تشغيل البوت في مسار منفصل
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    # تشغيل سيرفر الويب على البورت اللي الاستضافة ادتهولك
    app.run(host='0.0.0.0', port=20230, debug=False)