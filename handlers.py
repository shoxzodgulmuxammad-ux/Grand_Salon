from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from config import OWNER_IDS
import database as db

SELECTING_TIME = 0
ENTERING_NAME  = 1
ENTERING_PHONE = 2
CONFIRMING     = 3

def get_owner_keyboard():
    keyboard = [
        ["🔄 Navbatlar", "📊 Statistika"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_client_keyboard():
    keyboard = [
        ["✂️ Navbat olish"],
        ["❌ Navbatlarim / Bekor qilish"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_owner = (user_id in OWNER_IDS)

    if is_owner:
        all_appts = db.get_all_appointments()
        today = datetime.now().strftime("%Y-%m-%d")
        bugungi = [a for a in all_appts if a["status"] == "active" and a["time"].startswith(today)]
        
        text = (
            f"👋 Salom Ustoz! Xush kelibsiz.\n\n"
            f"📅 Bugun soat {datetime.now().strftime('%H:%M')} holatiga ko'ra xizmat ko'rsatishga tayyormiz.\n"
            f"📋 Bugungi aktiv navbatlar soni: {len(bugungi)} ta.\n\n"
            f"Kerakli bo'limni pastdagi menyudan tanlang 👇"
        )
        await update.message.reply_text(text, reply_markup=get_owner_keyboard())
    else:
        text = (
            "👋 Salom! Grand Salon botiga xush kelibsiz.\n\n"
            "Pastdagi tugmalar orqali o'zingizga qulay vaqtga navbat olishingiz yoki olingan navbatingizni bekor qilishingiz mumkin 👇"
        )
        await update.message.reply_text(text, reply_markup=get_client_keyboard())


async def book_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_appts = db.get_user_appointments(user_id)
    
    if user_appts:
        active_appt = user_appts[0]
        await update.message.reply_text(
            f"⚠️ Sizda allaqachon faol navbat bor:\n"
            f"📅 Vaqt: {active_appt['time']}\n\n"
            f"Yangi navbat olish uchun avvalgisini bekor qiling."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📝 Navbat olish jarayoni boshlandi.\n\n"
        "Iltimos, o'zingizga qulay bo'lgan kun va vaqtni quyidagi namunadek yozing:\n"
        "👉 `15.06 14:00` (Kun.Oy Soat:Min)\n\n"
        "Bekor qilish uchun /cancel buyrug'ini yuboring."
    )
    return SELECTING_TIME


async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    input_str = update.message.text.strip()
    current_year = datetime.now().year
    full_time_str = f"{current_year}.{input_str}"
    
    try:
        dt = datetime.strptime(full_time_str, "%Y.%d.%m %H:%M")
        if dt < datetime.now():
            await update.message.reply_text("❌ Kechirasiz, o'tib ketgan vaqtga navbat ololmaysiz. Qaytadan to'g'ri vaqt kiriting:")
            return SELECTING_TIME
        db_ready_time = dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri vaqt formati kiritildi!\nIltimos, namunadagidek yozing:\n👉 `15.06 14:00`")
        return SELECTING_TIME

    if db.get_appointment_by_time(db_ready_time):
        await update.message.reply_text("⚠️ Kechirasiz, bu vaqt allaqachon band. Boshqa vaqt kiriting:")
        return SELECTING_TIME

    context.user_data["book_time"] = db_ready_time
    await update.message.reply_text("😊 Juda yaxshi! Endi ismingizni kiriting:")
    return ENTERING_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❌ Ism juda qisqa. Iltimos, ismingizni to'g'ri kiriting:")
        return ENTERING_NAME
    context.user_data["book_name"] = name
    await update.message.reply_text("📞 Rahmat! Endi telefon raqamingizni kiriting (Masalan: +998901234567):")
    return ENTERING_PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    context.user_data["book_phone"] = phone
    time_str = context.user_data["book_time"]
    name = context.user_data["book_name"]

    try:
        dt_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        readable_time = dt_obj.strftime("%d.%m %H:%M")
    except:
        readable_time = time_str

    text = (
        f"📋 *Kiritilgan ma'lumotlarni tasdiqlang:* \n\n"
        f"👤 Ism: {name}\n"
        f"📅 Vaqt: {readable_time}\n"
        f"📞 Telefon: {phone}\n\n"
        f"Hamma ma'lumotlar to'g'rimi?"
    )
    keyboard = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_booking")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRMING


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    time_str = context.user_data.get("book_time")
    name = context.user_data.get("book_name")
    phone = context.user_data.get("book_phone")
    
    db.add_appointment(user_id=user.id, username=user.username or "", name=name, phone=phone, time_str=time_str)
    
    try:
        dt_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        readable_time = dt_obj.strftime("%d.%m %H:%M")
    except:
        readable_time = time_str

    await query.message.edit_text(f"🎉 *Tabriklaymiz! Navbatingiz muvaffaqiyatli olindi.*\n\n📅 Vaqt: {readable_time}\nSizni o'sha vaqtda kutamiz!", parse_mode="Markdown")
    
    for owner_id in OWNER_IDS:
        try:
            await context.bot.send_message(chat_id=owner_id, text=f"🔔 *Yangi navbat!*\n\n👤 {name}\n📅 Vaqt: {readable_time}\n📞 Tel: {phone}", parse_mode="Markdown")
        except:
            pass
    context.user_data.clear()
    return ConversationHandler.END


# MIJOZ FAOL NAVBATLARINI INLINE TUGMA BILAN BEKOR QILISHI UCHUN
async def show_client_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_appts = db.get_user_appointments(user_id)
    
    if not user_appts:
        await update.message.reply_text("❌ Sizda hozircha hech qanday faol navbat mavjud emas.")
        return
        
    await update.message.reply_text("📋 *Sizning faol navbatlaringiz:*")
    for appt in user_appts:
        try:
            dt_obj = datetime.strptime(appt['time'], "%Y-%m-%d %H:%M")
            readable_time = dt_obj.strftime("%d.%m %H:%M")
        except:
            readable_time = appt['time']

        text = (
            f"👤 Ism: {appt['name']}\n"
            f"📅 Vaqt: `{readable_time}`\n"
        )
        keyboard = [[InlineKeyboardButton("❌ Navbatni bekor qilish", callback_data=f"client_cancel_{appt['id']}")]]
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# USTA HAMMA NAVBATLARNI ALOHIDA TUGMALAR BILAN INLINE BOSHQARISHI UCHUN
async def show_appointments_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_obj = update.callback_query.message if update.callback_query else update.message
    if update.effective_user.id not in OWNER_IDS:
        await message_obj.reply_text("⛔ Bu funksiya faqat bot egasi uchun.")
        return

    all_appts = db.get_all_appointments()
    active_appts = [a for a in all_appts if a["status"] == "active"]
    if not active_appts:
        await message_obj.reply_text("📭 Hozircha hech qanday aktiv navbatlar mavjud emas.")
        return
        
    active_appts.sort(key=lambda x: x["time"])
    await message_obj.reply_text("📋 *AKTIV NAVBATLAR RO'YXATI* 👇")
    
    for a in active_appts:
        try:
            dt_obj = datetime.strptime(a['time'], "%Y-%m-%d %H:%M")
            readable_time = dt_obj.strftime("%d.%m %H:%M")
        except:
            readable_time = a['time']

        text = (
            f"🆔 Navbat ID: {a['id']}\n"
            f"👤 Mijoz: {a['name']}\n"
            f"📅 Vaqt: `{readable_time}`\n"
            f"📞 Tel: {a['phone']}\n"
        )
        
        # Tugmalar har bir mijoz uchun butunlay mustaqil ulanadi
        keyboard = [
            [InlineKeyboardButton("❌ Ushbu navbatni bekor qilish", callback_data=f"owner_cancel_{a['id']}")],
            [InlineKeyboardButton("⏳ Faqat shu navbatni ko'chirish (1 kunga)", callback_data=f"owner_postpone_{a['id']}")]
        ]
        await message_obj.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in OWNER_IDS:
        await update.message.reply_text("⛔ Bu funksiya faqat bot egasi uchun.")
        return

    all_appts = db.get_all_appointments()
    today = datetime.now().strftime("%Y-%m-%d")
    bugungi = [a for a in all_appts if a["status"] == "active" and a["time"].startswith(today)]
    jami_aktiv = [a for a in all_appts if a["status"] == "active"]
    bekor = [a for a in all_appts if a["status"] == "cancelled"]

    text = (
        f"📊 *STATISTIKA*\n\n"
        f"📅 Bugungi navbatlar: *{len(bugungi)} ta*\n"
        f"📌 Jami aktiv navbatlar: *{len(jami_aktiv)} ta*\n"
        f"❌ Bekor qilingan: *{len(bekor)} ta*\n"
        f"📁 Tizimdagi jami navbatlar: *{len(all_appts)} ta*\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Amal bekor qilindi.")
    return ConversationHandler.END