import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os, json, time
from flask import Flask
import threading

# 🧠 إعداد التوكن ومتغيرات البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN or not ADMIN_ID:
    raise RuntimeError("❌ لازم تضيف BOT_TOKEN و ADMIN_ID في Secrets")

bot = telebot.TeleBot(BOT_TOKEN)
ADMIN_ID = int(ADMIN_ID)

# 🔗 رابط Google Sheet (استبدله برابط الشيت الحقيقي)
SHEET_URL = os.getenv("SHEET_URL")

# 🔧 إعداد الاتصال بـ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json_str = os.getenv("GOOGLE_CREDENTIALS")
if not creds_json_str:
    raise RuntimeError("❌ متغير GOOGLE_CREDENTIALS مش موجود في Secrets")

creds_dict = json.loads(creds_json_str)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(SHEET_URL).sheet1

# 📦 حفظ المستخدمين الجدد
@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "لا يوجد"
    name = user.first_name or "بدون اسم"

    users = sheet.col_values(1)

    if str(user_id) not in users:
        sheet.append_row([str(user_id), username, name, time.strftime("%Y-%m-%d %H:%M:%S")])
        bot.send_message(
            ADMIN_ID,
            f"🆕 مستخدم جديد بدأ استخدام البوت\n"
            f"👤 الاسم: {name}\n"
            f"📛 المستخدم: {username}\n"
            f"🪪 ID: {user_id}\n"
            f"📅 الوقت: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👥 إجمالي المستخدمين: {len(users)}"
        )
        print(f"✅ مستخدم جديد: {name} ({user_id})")

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📘 تحميل الكتاب"))
    bot.send_message(message.chat.id, "👋 مرحبًا بك! اضغط الزر بالأسفل لتحميل الملف.", reply_markup=markup)

# 📘 إرسال الملف
@bot.message_handler(func=lambda message: message.text == "📘 تحميل الكتاب")
def send_pdf(message):
    pdf_id = "BQACAgIAAxkBAAE9JnVpAyxKmWINvNUmJWOgEwyuly0_CQACdlAAAvqGgUpTy889n198UzYE"
    bot.send_document(message.chat.id, pdf_id, caption="📄 إليك الملف المطلوب")

# ✅ إعداد Flask لتشغيل السيرفر
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ البوت شغال 24/7 - كل حاجة تمام!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# 🚀 تشغيل Flask في خيط منفصل
threading.Thread(target=run_flask).start()

# 🚀 تشغيل البوت
print("🚀 البوت شغال ومستعد...")
bot.infinity_polling()
