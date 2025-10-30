# coding: utf-8

# ==========================================
# 1️⃣ استيراد المكتبات المطلوبة
# ==========================================
import os
import json
import time
import random

import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# لتحضير إمكانية ربط Google Sheets (اختياري - يُستخدم فقط إذا وفرت GOOGLE_CREDENTIALS)
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except Exception:
    # إذا لم تُثبّت المكتبات فسنستمر بدون ربط الشيت
    gspread = None
    ServiceAccountCredentials = None

# (اختياري) يمكن وجود ملف خارجي ل keep_alive إذا كنت تستخدم Replit أو خادم يحتاج إبقاء الجلسة حية
# from keep_alive import keep_alive


# ==========================================
# 2️⃣ إعداد متغيرات البيئة (Environment Variables)
# ==========================================
# يُفضّل تعيين هذه المتغيرات في بيئة التشغيل (مثلاً على Replit / Heroku / Docker)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = os.getenv("ADMIN_ID", None)
SHEET_URL = os.getenv("SHEET_URL", None)
# GOOGLE_CREDENTIALS يجب أن تكون JSON كسلسلة نصية في متغير بيئة واحد (أو يمكن تركها فارغة)
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS", None)


# ==========================================
# 3️⃣ إنشاء كائن البوت
# ==========================================
bot = telebot.TeleBot(BOT_TOKEN)


# ==========================================
# 4️⃣ إعداد الاتصال بـ Google Sheets (اختياري)
# ==========================================
# إذا وضعت بيانات الاعتماد في GOOGLE_CREDENTIALS وركبت المكتبات، سنحاول تهيئة الاتصال تلقائيًا.
sheet = None
if GOOGLE_CREDENTIALS and gspread and ServiceAccountCredentials:
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        credentials_dict = json.loads(GOOGLE_CREDENTIALS)
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(credentials)
        if SHEET_URL:
            sheet = client.open_by_url(SHEET_URL).sheet1
        else:
            sheet = None
    except Exception as e:
        # فشل تهيئة الشيت — سنستمر بدون ربط لكنه مفيد للتطوير لاحقًا
        sheet = None


# ==========================================
# 5️⃣ تعريف دوال معالجة الأوامر (Handlers) + ثوابت الأزرار
# ==========================================
# ====== نصوص الأزرار الثابتة ======
BTN_MAIN_BOOKS = "كتب عام 📚"
BTN_AZHAR_BOOKS = "كتب أزهر 🕌"
BTN_SCHOOL_BOOKS = "كتب مدرسية 🏫"

BTN_2ND = "الصف الثاني الثانوي 🎓"
BTN_3RD = "الصف الثالث الثانوي 🎓"

BTN_SCI = "علمي 🔬"
BTN_ADABY = "أدبي 📖"
BTN_SCIENCE = "علمي علوم 🧬"
BTN_MATHS = "علمي رياضة 📐"

BTN_BACK = "🔙 رجوع"
BTN_HOME = "🏠 القائمة الرئيسية"


# ==========================================
# 6️⃣ استخدام ReplyKeyboardMarkup: دوال إنشاء لوحات الأزرار
# ==========================================
def make_keyboard(button_rows):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for row in button_rows:
        kb.add(*[KeyboardButton(txt) for txt in row])
    return kb

def main_menu_kb():
    return make_keyboard([[BTN_MAIN_BOOKS, BTN_AZHAR_BOOKS], [BTN_SCHOOL_BOOKS]])

def grades_kb():
    return make_keyboard([[BTN_2ND, BTN_3RD], [BTN_BACK, BTN_HOME]])

def streams_kb_for(grade):
    if grade == "2nd":
        return make_keyboard([[BTN_SCI, BTN_ADABY], [BTN_BACK, BTN_HOME]])
    else:
        return make_keyboard([[BTN_ADABY, BTN_SCIENCE], [BTN_MATHS], [BTN_BACK, BTN_HOME]])

def materials_kb(materials_list):
    rows = []
    temp = []
    for m in materials_list:
        temp.append(m)
        if len(temp) == 2:
            rows.append(temp)
            temp = []
    if temp:
        rows.append(temp)
    rows.append([BTN_BACK, BTN_HOME])
    return make_keyboard(rows)

def books_kb(books_list):
    rows = []
    temp = []
    for b in books_list:
        temp.append(b)
        if len(temp) == 2:
            rows.append(temp)
            temp = []
    if temp:
        rows.append(temp)
    rows.append([BTN_BACK, BTN_HOME])
    return make_keyboard(rows)


# ==========================================
# 7️⃣ تنفيذ عمليات معينة: قاعدة بيانات ملفّات ID والعمليات (بدون تغيير في المحتوى)
# ==========================================
# ====== قاعدة البيانات (أمثلة) ======
# كل كتاب عبارة عن قائمة من up to 4 file_id (يمكن أن تكون أقل في الواقع، لكن ينصح وضع 4).
# لاحظ أن file_id لكل كتاب يجب أن يكون فريداً حتى لو تكرر اسم الكتاب في صفوف مختلفة.
# ضع file_id الحقيقية لديك بدلاً من "file_id_xxx".

BOOKS = {
    # هيكل: (grade, category) -> streams/subjects -> books -> [file_id1,...,file_id4]
    # سنضع مدخلات لثاني وثالث ثانوي (عام/أزهر تستخدم نفس المحتوى هنا)
    ("2nd", "general"): {
        "علمي": {
            "عربي": {
                "الأضواء": ["file_id_2nd_عربي_الأضواء_1", "file_id_2nd_عربي_الأضواء_2", "file_id_2nd_عربي_الأضواء_3", "file_id_2nd_عربي_الأضواء_4"],
                "بيان": ["file_id_2nd_عربي_بيان_1", "file_id_2nd_عربي_بيان_2", "file_id_2nd_عربي_بيان_3", "file_id_2nd_عربي_بيان_4"],
                "كيان": ["file_id_2nd_عربي_كيان_1","file_id_2nd_عربي_كيان_2","file_id_2nd_عربي_كيان_3","file_id_2nd_عربي_كيان_4"],
                "البرهان": ["file_id_2nd_عربي_البرهان_1","file_id_2nd_عربي_البرهان_2","file_id_2nd_عربي_البرهان_3","file_id_2nd_عربي_البرهان_4"],
                "الامتحان": ["file_id_2nd_عربي_الامتحان_1","file_id_2nd_عربي_الامتحان_2","file_id_2nd_عربي_الامتحان_3","file_id_2nd_عربي_الامتحان_4"],
            },
            "إنجليزي": {
                "المعاصر": ["file_id_2nd_انجليزي_المعاصر_1","file_id_2nd_انجليزي_المعاصر_2","file_id_2nd_انجليزي_المعاصر_3","file_id_2nd_انجليزي_المعاصر_4"],
                "GEM": ["file_id_2nd_انجليزي_GEM_1","file_id_2nd_انجليزي_GEM_2","file_id_2nd_انجليزي_GEM_3","file_id_2nd_انجليزي_GEM_4"],
                "العمالقة": ["file_id_2nd_انجليزي_العمالقة_1","file_id_2nd_انجليزي_العمالقة_2","file_id_2nd_انجليزي_العمالقة_3","file_id_2nd_انجليزي_العمالقة_4"]
            },
            "فرنساوي": {
                "برافو": ["file_id_2nd_فرنساوي_برافو_1","file_id_2nd_فرنساوي_برافو_2","file_id_2nd_فرنساوي_برافو_3","file_id_2nd_فرنساوي_برافو_4"],
                "ميرسي": ["file_id_2nd_فرنساوي_ميرسي_1","file_id_2nd_فرنساوي_ميرسي_2","file_id_2nd_فرنساوي_ميرسي_3","file_id_2nd_فرنساوي_ميرسي_4"]
            },
            "كيمياء": {
                "أفوجادرو": ["file_id_2nd_كيمياء_أفوجادرو_1","file_id_2nd_كيمياء_أفوجادرو_2","file_id_2nd_كيمياء_أفوجادرو_3","file_id_2nd_كيمياء_أفوجادرو_4"],
                "الامتحان": ["file_id_2nd_كيمياء_الامتحان_1","file_id_2nd_كيمياء_الامتحان_2","file_id_2nd_كيمياء_الامتحان_3","file_id_2nd_كيمياء_الامتحان_4"],
            },
            "فيزياء": {
                "الوافي": ["file_id_2nd_فيزياء_الوافي_1","file_id_2nd_فيزياء_الوافي_2","file_id_2nd_فيزياء_الوافي_3","file_id_2nd_فيزياء_الوافي_4"],
                "التفوق": ["file_id_2nd_فيزياء_التفوق_1","file_id_2nd_فيزياء_التفوق_2","file_id_2nd_فيزياء_التفوق_3","file_id_2nd_فيزياء_التفوق_4"],
                "الامتحان": ["file_id_2nd_فيزياء_الامتحان_1","file_id_2nd_فيزياء_الامتحان_2","file_id_2nd_فيزياء_الامتحان_3","file_id_2nd_فيزياء_الامتحان_4"],
                "الوسام": ["file_id_2nd_فيزياء_الوسام_1","file_id_2nd_فيزياء_الوسام_2","file_id_2nd_فيزياء_الوسام_3","file_id_2nd_فيزياء_الوسام_4"],
                "نيوتن": ["file_id_2nd_فيزياء_نيوتن_1","file_id_2nd_فيزياء_نيوتن_2","file_id_2nd_فيزياء_نيوتن_3","file_id_2nd_فيزياء_نيوتن_4"]
            },
            "أحياء": {
                "الامتحان": ["file_id_2nd_أحياء_الامتحان_1","file_id_2nd_أحياء_الامتحان_2","file_id_2nd_أحياء_الامتحان_3","file_id_2nd_أحياء_الامتحان_4"],
                "التفوق": ["file_id_2nd_أحياء_التفوق_1","file_id_2nd_أحياء_التفوق_2","file_id_2nd_أحياء_التفوق_3","file_id_2nd_أحياء_التفوق_4"]
            },
            "تاريخ": {
                "الامتحان": ["file_id_2nd_تاريخ_الامتحان_1","file_id_2nd_تاريخ_الامتحان_2","file_id_2nd_تاريخ_الامتحان_3","file_id_2nd_تاريخ_الامتحان_4"]
            }
        },
        # لو في شعب أو بنية إضافية أضف هنا
    },

    ("3rd", "general"): {
        "أدبي": {
            "عربي": {
                "الامتحان": ["file_id_3rd_عربي_الامتحان_1","file_id_3rd_عربي_الامتحان_2","file_id_3rd_عربي_الامتحان_3","file_id_3rd_عربي_الامتحان_4"]
            },
            "إنجليزي": {
                "المعاصر": ["file_id_3rd_انجليزي_المعاصر_1","file_id_3rd_انجليزي_المعاصر_2","file_id_3rd_انجليزي_المعاصر_3","file_id_3rd_انجليزي_المعاصر_4"]
            },
            "فرنساوي": {
                "برافو": ["file_id_3rd_فرنساوي_برافو_1","file_id_3rd_فرنساوي_برافو_2","file_id_3rd_فرنساوي_برافو_3","file_id_3rd_فرنساوي_برافو_4"]
            },
            "جغرافيا": {
                "الامتحان": ["file_id_3rd_جغرافيا_الامتحان_1","file_id_3rd_جغرافيا_الامتحان_2","file_id_3rd_جغرافيا_الامتحان_3","file_id_3rd_جغرافيا_الامتحان_4"]
            },
            "تاريخ": {
                "الامتحان": ["file_id_3rd_تاريخ_الامتحان_1","file_id_3rd_تاريخ_الامتحان_2","file_id_3rd_تاريخ_الامتحان_3","file_id_3rd_تاريخ_الامتحان_4"]
            },
            "فلسفة": {
                "الامتحان": ["file_id_3rd_فلسفة_الامتحان_1","file_id_3rd_فلسفة_الامتحان_2","file_id_3rd_فلسفة_الامتحان_3","file_id_3rd_فلسفة_الامتحان_4"]
            }
        },
        "علمي_علوم": {
            "عربي": {"الامتحان": ["file_id_3rd_sc_عربي_الامتحان_1","file_id_3rd_sc_عربي_الامتحان_2","file_id_3rd_sc_عربي_الامتحان_3","file_id_3rd_sc_عربي_الامتحان_4"]},
            "إنجليزي": {"المعاصر": ["file_id_3rd_sc_انجليزي_المعاصر_1","file_id_3rd_sc_انجليزي_المعاصر_2","file_id_3rd_sc_انجليزي_المعاصر_3","file_id_3rd_sc_انجليزي_المعاصر_4"]},
            "فرنساوي": {"برافو": ["file_id_3rd_sc_فرنساوي_برافو_1","file_id_3rd_sc_فرنساوي_برافو_2","file_id_3rd_sc_فرنساوي_برافو_3","file_id_3rd_sc_فرنساوي_برافو_4"]},
            "كيمياء": {"الامتحان": ["file_id_3rd_sc_كيمياء_الامتحان_1","file_id_3rd_sc_كيمياء_الامتحان_2","file_id_3rd_sc_كيمياء_الامتحان_3","file_id_3rd_sc_كيمياء_الامتحان_4"]},
            "فيزياء": {"الامتحان": ["file_id_3rd_sc_فيزياء_الامتحان_1","file_id_3rd_sc_فيزياء_الامتحان_2","file_id_3rd_sc_فيزياء_الامتحان_3","file_id_3rd_sc_فيزياء_الامتحان_4"]},
            "أحياء": {"الامتحان": ["file_id_3rd_sc_أحياء_الامتحان_1","file_id_3rd_sc_أحياء_الامتحان_2","file_id_3rd_sc_أحياء_الامتحان_3","file_id_3rd_sc_أحياء_الامتحان_4"]},
            "جيولوجيا": {"المرجع": ["file_id_3rd_sc_جيولوجيا_المرجع_1","file_id_3rd_sc_جيولوجيا_المرجع_2","file_id_3rd_sc_جيولوجيا_المرجع_3","file_id_3rd_sc_جيولوجيا_المرجع_4"]}
        },
        "علمي_رياضة": {
            "عربي": {"الامتحان": ["file_id_3rd_math_عربي_الامتحان_1","file_id_3rd_math_عربي_الامتحان_2","file_id_3rd_math_عربي_الامتحان_3","file_id_3rd_math_عربي_الامتحان_4"]},
            "إنجليزي": {"المعاصر": ["file_id_3rd_math_انجليزي_المعاصر_1","file_id_3rd_math_انجليزي_المعاصر_2","file_id_3rd_math_انجليزي_المعاصر_3","file_id_3rd_math_انجليزي_المعاصر_4"]},
            "فرنساوي": {"برافو": ["file_id_3rd_math_فرنساوي_برافو_1","file_id_3rd_math_فرنساوي_برافو_2","file_id_3rd_math_فرنساوي_برافو_3","file_id_3rd_math_فرنساوي_برافو_4"]},
            "كيمياء": {"الامتحان": ["file_id_3rd_math_كيمياء_الامتحان_1","file_id_3rd_math_كيمياء_الامتحان_2","file_id_3rd_math_كيمياء_الامتحان_3","file_id_3rd_math_كيمياء_الامتحان_4"]},
            "فيزياء": {"الامتحان": ["file_id_3rd_math_فيزياء_الامتحان_1","file_id_3rd_math_فيزياء_الامتحان_2","file_id_3rd_math_فيزياء_الامتحان_3","file_id_3rd_math_فيزياء_الامتحان_4"]},
            # مواد الرياضة الخاصة (كل مادة لها كتاب واحد كما طلبت)
            "تفاضل وتكامل": {"الكتاب الوحيد": ["file_id_3rd_math_تفاضل_1","file_id_3rd_math_تفاضل_1","file_id_3rd_math_تفاضل_1","file_id_3rd_math_تفاضل_1"]},
            "جبر وهندسة": {"الكتاب الوحيد": ["file_id_3rd_math_جبر_1","file_id_3rd_math_جبر_1","file_id_3rd_math_جبر_1","file_id_3rd_math_جبر_1"]},
            "استاتيكا": {"الكتاب الوحيد": ["file_id_3rd_math_استاتيكا_1","file_id_3rd_math_استاتيكا_1","file_id_3rd_math_استاتيكا_1","file_id_3rd_math_استاتيكا_1"]},
            "ديناميكا": {"الكتاب الوحيد": ["file_id_3rd_math_ديناميكا_1","file_id_3rd_math_ديناميكا_1","file_id_3rd_math_ديناميكا_1","file_id_3rd_math_ديناميكا_1"]}
        }
    },

    # إذا أردت نسخة مخصصة لأزهر ضع مفاتيح ("2nd","azhar") و ("3rd","azhar") بنفس النمط
    ("2nd", "azhar"): {},  # يمكن تعبئتها لاحقًا
    ("3rd", "azhar"): {}
}


# ====== إدارة حالة المستخدم البسيطة (stack للسماح بالرجوع) ======
user_states = {}  # chat_id -> { "stack": [], "context": {...} }


# ====== دوال لإدارة الحالة والـ stack ======
def init_user(chat_id):
    user_states[chat_id] = {"stack": [], "context": {}}

def push_state(chat_id, name, payload=None):
    if chat_id not in user_states:
        init_user(chat_id)
    user_states[chat_id]["stack"].append((name, payload))
    # update context with current top values for convenience
    user_states[chat_id]["context"][name] = payload

def pop_state(chat_id):
    if chat_id not in user_states or not user_states[chat_id]["stack"]:
        return None
    popped = user_states[chat_id]["stack"].pop()
    # rebuild context
    ctx = {}
    for k, v in user_states[chat_id]["stack"]:
        ctx[k] = v
    user_states[chat_id]["context"] = ctx
    return popped

def reset_user(chat_id):
    init_user(chat_id)


# ====== دوال لعرض القوائم (بدون تغيير في المنطق) ======
def show_main_menu(chat_id):
    reset_user(chat_id)
    push_state(chat_id, "menu", "main")
    kb = main_menu_kb()
    bot.send_message(chat_id, "أهلاً! اختر الفئة التي تريدها من الأزرار أدناه 👇", reply_markup=kb)

def show_grades(chat_id, category):
    # category: "general", "azhar", "school"
    push_state(chat_id, "category", category)
    push_state(chat_id, "menu", "grades")
    kb = grades_kb()
    bot.send_message(chat_id, "اختر الصف الدراسي:", reply_markup=kb)

def show_streams(chat_id, grade):
    # grade: "2nd" or "3rd"
    push_state(chat_id, "grade", grade)
    push_state(chat_id, "menu", "streams")
    kb = streams_kb_for(grade)
    bot.send_message(chat_id, "اختر نوع الشعبة:", reply_markup=kb)

def show_materials(chat_id, grade, category, stream_key):
    # stream_key is like "علمي" or "أدبي" or "علمي_علوم" or "علمي_رياضة"
    push_state(chat_id, "stream", stream_key)
    push_state(chat_id, "menu", "materials")

    # Special case: كتب مدرسية -> بعد اختيار المادة رسالة "سوف تتوفر الكتب قريبًا"
    if category == "school":
        # for school, we still show materials list based on generic 3rd-science for demo
        # but per spec, after اختيار المادة we send coming-soon message.
        # We'll show a materials menu limited to a helpful selection; user asked to use same system.
        # We'll reuse the 3rd general materials lists as a template.
        if grade == "2nd":
            sample_materials = ["عربي 🗣️","إنجليزي 🇬🇧","فرنساوي 🇫🇷","كيمياء ⚗️","فيزياء 🔋","أحياء 🧬","تاريخ 🕰️"]
        else:
            sample_materials = ["عربي 🗣️","إنجليزي 🇬🇧","فرنساوي 🇫🇷","كيمياء ⚗️","فيزياء 🔋","تفاضل وتكامل ➗","جبر وهندسة 📏","استاتيكا ⚖️","ديناميكا 🔄"]
        kb = materials_kb(sample_materials)
        bot.send_message(chat_id, "اختر المادة (ملاحظة: كتب المدرسية ستتوفر قريبًا):", reply_markup=kb)
        return

    # For general or azhar category: load materials from BOOKS structure
    # map stream_key to internal key in BOOKS for 3rd grade where we used 'علمي_علوم', 'علمي_رياضة'
    if grade == "2nd":
        key = ("2nd", category)
        # expected BOOKS[("2nd","general")] contains dict with key "علمي"
        try:
            stream_dict = BOOKS[key][stream_key]
        except Exception:
            bot.send_message(chat_id, "عذرًا، لا توجد كتب مُسجّلة لهذه الشعبة بعد. سيتم إضافتها قريبًا.", reply_markup=types.ReplyKeyboardMarkup([[BTN_BACK, BTN_HOME]], resize_keyboard=True))
            return
        materials_list = list(stream_dict.keys())
        # add emojis next to known items (optional)
        materials_list = [m + (" 🗣️" if "عربي" in m else "") for m in materials_list]
    else:
        # 3rd
        key = ("3rd", category)
        # for 3rd, stream_key can be BTN_ADABY text, BTN_SCIENCE, BTN_MATHS -> map to BOOKS keys
        if stream_key == BTN_ADABY:
            internal = "أدبي"
        elif stream_key == BTN_SCIENCE:
            internal = "علمي_علوم"
        else:
            internal = "علمي_رياضة"
        try:
            stream_dict = BOOKS[key][internal]
        except Exception:
            bot.send_message(chat_id, "عذرًا، لا توجد كتب مُسجّلة لهذه الشعبة بعد. سيتم إضافتها قريبًا.", reply_markup=types.ReplyKeyboardMarkup([[BTN_BACK, BTN_HOME]], resize_keyboard=True))
            return
        materials_list = list(stream_dict.keys())
        # add small emojis per material for nicer view (optional)
        materials_list = [m + (" 🗺️" if "جغرافيا" in m else "") for m in materials_list]

    kb = materials_kb(materials_list)
    bot.send_message(chat_id, "اختر المادة:", reply_markup=kb)

def show_books(chat_id, grade, category, stream_key, material_raw):
    # material_raw may include emoji suffixs added earlier e.g. "عربي 🗣️" -> strip emoji tags
    material = material_raw.split()[0]  # take first token (works for names without spaces); safer strip emojis
    # better strip emojis: remove anything after first space if present
    material = material_raw.split(" ")[0]

    push_state(chat_id, "material", material)
    push_state(chat_id, "menu", "books")

    # For school category: per spec show coming soon message after selecting material
    if category == "school":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(types.KeyboardButton(BTN_BACK), types.KeyboardButton(BTN_HOME))
        bot.send_message(chat_id, "سوف تتوفر الكتب قريبًا 📚", reply_markup=kb)
        return

    # Determine the proper key path in BOOKS
    if grade == "2nd":
        key = ("2nd", category)
        try:
            book_dict = BOOKS[key][stream_key][material]
        except Exception:
            bot.send_message(chat_id, "عذرًا، لم يتم العثور على كتب لهذه المادة بعد. سيتم إضافتها قريبًا.", reply_markup=types.ReplyKeyboardMarkup([[BTN_BACK, BTN_HOME]], resize_keyboard=True))
            return
    else:
        key = ("3rd", category)
        if stream_key == BTN_ADABY:
            internal = "أدبي"
        elif stream_key == BTN_SCIENCE:
            internal = "علمي_علوم"
        else:
            internal = "علمي_رياضة"
        try:
            book_dict = BOOKS[key][internal][material]
        except Exception:
            bot.send_message(chat_id, "عذرًا، لم يتم العثور على كتب لهذه المادة بعد. سيتم إضافتها قريبًا.", reply_markup=types.ReplyKeyboardMarkup([[BTN_BACK, BTN_HOME]], resize_keyboard=True))
            return

    # book_dict is mapping book_name -> [file_id...]
    book_names = list(book_dict.keys())
    kb = books_kb(book_names)
    bot.send_message(chat_id, "اختر الكتاب الذي تريد تنزيله من الأسفل:", reply_markup=kb)

def send_book_file(chat_id, grade, category, stream_key, material, book_name):
    # احصل على file_id عشوائي من قائمة الكتاب وأرسله
    # ابحث في structure كما في show_books
    try:
        if grade == "2nd":
            key = ("2nd", category)
            files = BOOKS[key][stream_key][material][book_name]
        else:
            key = ("3rd", category)
            if stream_key == BTN_ADABY:
                internal = "أدبي"
            elif stream_key == BTN_SCIENCE:
                internal = "علمي_علوم"
            else:
                internal = "علمي_رياضة"
            files = BOOKS[key][internal][material][book_name]
    except Exception:
        bot.send_message(chat_id, "حدث خطأ في استرجاع ملف الكتاب. يرجى المحاولة لاحقًا.", reply_markup=types.ReplyKeyboardMarkup([[BTN_BACK, BTN_HOME]], resize_keyboard=True))
        return
    if not files:
        bot.send_message(chat_id, "لا يتوفر ملف لهذا الكتاب حالياً.", reply_markup=types.ReplyKeyboardMarkup([[BTN_BACK, BTN_HOME]], resize_keyboard=True))
        return

    file_id = random.choice(files)  # يختار واحداً من الأربعة تلقائياً
    bot.send_message(chat_id, f"جاري إرسال الكتاب: {book_name} 📚")
    try:
        bot.send_document(chat_id, file_id)
    except Exception as e:
        # قد يكون file_id غير صحيح أثناء الإعداد — أعلم المطور
        bot.send_message(chat_id, f"تعذّر إرسال الملف (file_id خاطئ أو غير متاح). الرجاء التحقق من file_id. \n\nخطأ داخلي: {e}",
                         reply_markup=types.ReplyKeyboardMarkup([[BTN_BACK, BTN_HOME]], resize_keyboard=True))


# ==========================================
# 5️⃣ (تكملة) هاندلرز الرسائل (Handlers) — نفس منطق الكود الأصلي
# ==========================================
@bot.message_handler(commands=['start', 'help'])
def handle_start(message):
    chat_id = message.chat.id
    show_main_menu(chat_id)

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # init state if missing
    if chat_id not in user_states:
        init_user(chat_id)

    # Special buttons: Home and Back
    if text == BTN_HOME:
        show_main_menu(chat_id)
        return
    if text == BTN_BACK:
        # pop current menu and show previous
        popped = pop_state(chat_id)
        # if nothing to pop or at root, show main
        if not user_states[chat_id]["stack"]:
            show_main_menu(chat_id)
            return
        # determine what to show based on new top-of-stack
        # peek top
        top_name, top_payload = user_states[chat_id]["stack"][-1]
        # top_name can be "menu", "category", "grade", "stream", "material"
        # show appropriate menu
        if top_name == "menu" and top_payload == "main":
            show_main_menu(chat_id)
        elif top_name == "category":
            # go back to grades selection for that category
            show_grades(chat_id, top_payload)
        elif top_name == "menu" and top_payload == "grades":
            # show grades (category is set below in context)
            category = user_states[chat_id]["context"].get("category", "general")
            show_grades(chat_id, category)
        elif top_name == "grade":
            # show streams for that grade
            grade = top_payload
            # category is context category
            show_streams(chat_id, grade)
        elif top_name == "menu" and top_payload == "streams":
            # show streams again
            grade = user_states[chat_id]["context"].get("grade", "2nd")
            show_streams(chat_id, grade)
        elif top_name == "stream":
            # show materials
            grade = user_states[chat_id]["context"].get("grade")
            category = user_states[chat_id]["context"].get("category","general")
            stream = top_payload
            show_materials(chat_id, grade, category, stream)
        elif top_name == "menu" and top_payload == "materials":
            # show materials for current stream
            grade = user_states[chat_id]["context"].get("grade")
            category = user_states[chat_id]["context"].get("category","general")
            stream = user_states[chat_id]["context"].get("stream")
            show_materials(chat_id, grade, category, stream)
        else:
            show_main_menu(chat_id)
        return

    # Top-level selections
    if text == BTN_MAIN_BOOKS:
        show_grades(chat_id, "general")
        return
    if text == BTN_AZHAR_BOOKS:
        show_grades(chat_id, "azhar")
        return
    if text == BTN_SCHOOL_BOOKS:
        show_grades(chat_id, "school")
        return

    # Choose grade
    if text == BTN_2ND:
        # grade selected -> show streams
        # find category from context (must be set)
        category = user_states[chat_id]["context"].get("category", "general")
        show_streams(chat_id, "2nd")
        return
    if text == BTN_3RD:
        category = user_states[chat_id]["context"].get("category", "general")
        show_streams(chat_id, "3rd")
        return

    # streams selection
    if text in (BTN_SCI, BTN_ADABY, BTN_SCIENCE, BTN_MATHS):
        # show materials based on grade and category
        grade = user_states[chat_id]["context"].get("grade")
        category = user_states[chat_id]["context"].get("category", "general")
        # map BTN_SCIENCE text to internal if needed
        show_materials(chat_id, grade, category, text)
        return

    # If current menu is materials: user chose a material
    # We try to detect if the message corresponds to a material button by checking current state
    current_menu = user_states[chat_id]["stack"][-1][0] if user_states[chat_id]["stack"] else None
    if current_menu == "menu" and user_states[chat_id]["stack"][-1][1] == "materials":
        # text should be material; show books or coming-soon for school
        grade = user_states[chat_id]["context"].get("grade")
        category = user_states[chat_id]["context"].get("category", "general")
        stream = user_states[chat_id]["context"].get("stream")
        # For safety, strip trailing emoji tokens if present
        material_clean = text.split(" ")[0]
        show_books(chat_id, grade, category, stream, material_clean)
        return

    # If current menu is books: user chose a book
    if current_menu == "menu" and user_states[chat_id]["stack"][-1][1] == "books":
        # retrieve context
        grade = user_states[chat_id]["context"].get("grade")
        category = user_states[chat_id]["context"].get("category", "general")
        stream = user_states[chat_id]["context"].get("stream")
        material = user_states[chat_id]["context"].get("material")
        # the displayed book name may match key
        book_name = text
        # send file
        send_book_file(chat_id, grade, category, stream, material, book_name)
        return

    # Fallback: unknown input
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton(BTN_HOME))
    bot.send_message(chat_id, "عذرًا، لم أفهم اختيارك. اضغط 🏠 للعودة للقائمة الرئيسية أو استخدم الأزرار في الأسفل.", reply_markup=kb)


# ==========================================
# 8️⃣ تشغيل السيرفر (اختياري) — placeholder
# ==========================================
# إذا كنت تستخدم Replit أو خدمة مشابهة وتريد إبقاء السيرفر حياً:
# keep_alive()


# ==========================================
# 9️⃣ بدء تشغيل البوت
# ==========================================
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
