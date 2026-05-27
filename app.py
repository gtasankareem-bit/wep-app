import telebot
from yt_dlp import YoutubeDL
import os

# --- إعدادات البوت (تعديل هذه البيانات ضروري) ---
API_TOKEN = '8688043249:AAEdFK6QxLfK5G8TlrP8XsbXd70h_zG0o3s' # جيبه من @BotFather
ADMIN_ID = 7174983919  # حط هنا الـ ID بتاعك (جيبه من بوت @userinfobot)
USERS_FILE = "users.txt" # ملف لحفظ المستخدمين (سيتم إنشاؤه تلقائياً)

bot = telebot.TeleBot(API_TOKEN)

# وظيفة لحفظ المستخدمين الجدد في ملف نصي
def save_user(user_id):
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE, "w").close()
    with open(USERS_FILE, "r+") as f:
        users = f.read().splitlines()
        if str(user_id) not in users:
            f.write(str(user_id) + "\n")

# --- لوحة التحكم (تظهر للأدمن فقط عند كتابة /admin) ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        with open(USERS_FILE, "r") as f:
            count = len(f.read().splitlines())
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("عدد المستخدمين 📊", "إذاعة رسالة 📢")
        bot.send_message(message.chat.id, f"أهلاً يا مدير! عندك {count} مستخدم.\nاختر أمر من القائمة:", reply_markup=markup)
    else:
        bot.reply_to(message, "هذا الأمر مخصص لمدير البوت فقط.")

@bot.message_handler(func=lambda message: message.text == "عدد المستخدمين 📊")
def show_users(message):
    if message.from_user.id == ADMIN_ID:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                count = len(f.read().splitlines())
        else:
            count = 0
        bot.reply_to(message, f"إجمالي الناس اللي استخدمت البوت: {count}")

@bot.message_handler(func=lambda message: message.text == "إذاعة رسالة 📢")
def broadcast_ask(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "ارسل الآن الرسالة التي تريد إذاعتها للجميع (نص فقط):")
        bot.register_next_step_handler(msg, broadcast_send)

def broadcast_send(message):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = f.read().splitlines()
        success = 0
        for user in users:
            try:
                bot.send_message(user, message.text)
                success += 1
            except:
                pass
        bot.send_message(ADMIN_ID, f"✅ تمت الإذاعة بنجاح لـ {success} مستخدم.")
    else:
        bot.send_message(ADMIN_ID, "لا يوجد مستخدمين لإرسال الرسالة لهم.")

# --- الأوامر الأساسية ---
@bot.message_handler(commands=['start'])
def start(message):
    save_user(message.from_user.id)
    bot.reply_to(message, "أهلاً بك! أنا بوت تحميل الفيديوهات.\nارسل لي رابط فيديو من (TikTok, Instagram, YouTube, Facebook) وسأقوم بتحميله لك.")

# --- وظيفة معالجة الروابط والتحميل ---
@bot.message_handler(func=lambda m: True)
def download_video(message):
    url = message.text
    if "http" not in url:
        return

    wait_msg = bot.reply_to(message, "جاري معالجة الرابط.. ثواني من فضلك ⏳")
    
    try:
        # إعدادات مكتبة yt-dlp
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'video_{message.chat.id}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # إرسال الفيديو للمستخدم
        with open(filename, 'rb') as video:
            bot.send_video(message.chat.id, video, caption="تم التحميل بنجاح ✅")
        
        # حذف الفيديو من الاستضافة لتوفير المساحة
        if os.path.exists(filename):
            os.remove(filename)
            
        bot.delete_message(message.chat.id, wait_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل.\nتأكد من أن الرابط صحيح أو أن الموقع مدعوم.\n\nالوصف: {str(e)[:100]}", message.chat.id, wait_msg.message_id)

# تشغيل البوت
print("البوت يعمل الآن...")
bot.polling()
