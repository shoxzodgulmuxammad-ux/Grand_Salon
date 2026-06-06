from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
from config import OWNER_IDS
import database as db

# Conversation states
SELECTING_TIME = 0
ENTERING_NAME  = 1
ENTERING_PHONE = 2
CONFIRMING     = 3
CANCELLING     = 4

# --- PASTKI PANEL (REPLY KEYBOARD) TUGMALARI ---
def get_owner_keyboard():
    # Faqat usta (bot egasi) ko'radigan 4 ta asosiy tugma
    keyboard = [
        ["🔄 Navbatlar", "⏳ Kechiktirish"],
        ["📊 Statistika", "❌ Bekor qilish"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_client_keyboard():
    # Oddiy mijozlar uchun doimiy pastki panel tugmalari
    keyboard = [
        ["✂️ Navbat olish"],
        ["❌ Navbatni bekor qilish"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_owner = (user_id in OWNER_IDS)

    if is_owner:
        # Usta uchun panel
        all_appts = db.get_all_appointments()
        today = datetime.now().strftime("%Y-%m-%d")
        bugungi = [a for a in all_appts if a["status"] == "active" and a["time"].startswith(today)]
        jami_aktiv = [a for a in all_appts if a["status"] == "active"]

        await update.message.reply_text(
            f"👋 *Assalomu alaykum, usta!*\n\n"
            f"📊 Bugungi navbatlar: *{len(bugungi)} ta*\n"
            f"📌 Jami aktiv navbatlar: *{len(jami_aktiv)} ta*\n\n"
            f"Boshqarish uchun pastdagi tugmalardan foydalaning 👇",
            parse_mode="Markdown",
            reply_markup=get_owner_keyboard()
        )
    else:
        # Oddiy mijozlar uchun doimiy pastki klaviatura bilan javob berish
        await update.message.reply_text(
            "✂️ *Sartarosh botiga xush kelibsiz!*\n\n"
            "Navbat olish yoki mavjud navbatingizni bekor qilish uchun *pastdagi doimiy tugmalardan* foydalaning 👇",
            parse_mode="Markdown",
            reply_markup=get_client_keyboard()
        )


async def book_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        message_obj = query.message
    else:
        message_obj = update.message

    await message_obj.reply_text(
        "🕐 *Vaqtni belgilang*\n\n"
        "Quyidagi formatda yozing:\n"
        "`KUN.OY SOAT:DAQIQA`\n\n"
        "Masalan: `15.06 14:00`",
        parse_mode="Markdown"
    )
    return SELECTING_TIME


async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    try:
        current_year = datetime.now().year
        dt = datetime.strptime(f"{text} {current_year}", "%d.%m %H:%M %Y")
    except ValueError:
        await update.message.reply_text(
            "❗ Noto'g'ri format. Iltimos quyidagicha yozing:\n"
            "`15.06 14:00`",
            parse_mode="Markdown"
        )
        return SELECTING_TIME

    if dt < datetime.now():
        await update.message.reply_text("⚠️ O'tib ketgan vaqtni tanlab bo'lmaydi. Qaytadan kiriting:")
        return SELECTING_TIME

    time_str = dt.strftime("%Y-%m-%d %H:%M")
    display_time = dt.strftime("%d.%m %H:%M")

    existing = db.get_appointment_by_time(time_str)
    if existing:
        await update.message.reply_text(
            "🚫 *Bu vaqtda odam bor!*\n\nIltimos, boshqa vaqtni tanlang:",
            parse_mode="Markdown"
        )
        return SELECTING_TIME

    context.user_data["time"] = time_str
    context.user_data["display_time"] = display_time

    await update.message.reply_text(
        f"✅ Vaqt tanlandi: *{display_time}*\n\nEndi *ismingizni* kiriting:",
        parse_mode="Markdown"
    )
    return ENTERING_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text("❗ Ism juda qisqa. Qaytadan kiriting:")
        return ENTERING_NAME

    context.user_data["name"] = name
    await update.message.reply_text(
        f"👤 Ism saqlandi: *{name}*\n\n"
        f"Endi *telefon raqamingizni* kiriting:\n"
        f"Masalan: `+998901234567`",
        parse_mode="Markdown"
    )
    return ENTERING_PHONE


async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    context.user_data["phone"] = phone

    keyboard = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm_booking")]]
    display_time = context.user_data.get("display_time", context.user_data.get("time"))

    await update.message.reply_text(
        f"📋 *Ma'lumotlaringizni tekshiring:*\n\n"
        f"🕐 Vaqt: *{display_time}*\n"
        f"👤 Ism: {context.user_data['name']}\n"
        f"📞 Telefon: {phone}\n\n"
        f"Tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMING


async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    name  = context.user_data.get("name")
    phone = context.user_data.get("phone")
    time  = context.user_data.get("time")
    display_time = context.user_data.get("display_time", time)

    if db.get_appointment_by_time(time):
        await query.message.reply_text(
            "🚫 Kechirasiz, bu vaqtni boshqa odam band qildi!\n"
            "Iltimos, qaytadan urinib ko'ring."
        )
        return ConversationHandler.END

    appt = db.add_appointment(
        user_id=user.id,
        username=user.username or "",
        name=name,
        phone=phone,
        time_str=time
    )

    await query.message.reply_text(
        f"🎉 *Navbat belgilandi!*\n\n"
        f"🕐 Vaqt: *{display_time}*\n"
        f"👤 Ism: {name}\n"
        f"📞 Telefon: {phone}\n\n"
        f"Navbat raqami: #{appt['id']}",
        parse_mode="Markdown"
    )

    for oid in OWNER_IDS:
        try:
            await query.get_bot().send_message(
                chat_id=oid,
                text=(
                    f"🔔 *Yangi navbat!*\n\n"
                    f"🕐 Vaqt: *{display_time}*\n"
                    f"👤 Ism: {name}\n"
                    f"📞 Telefon: {phone}\n"
                    f"📱 Telegram: @{user.username or 'yoq'}\n"
                    f"🆔 Navbat #{appt['id']}"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Egaga xabar yuborishda xato: {e}")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_appointment_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        message_obj = query.message
        user_id = update.effective_user.id
        appts = db.get_user_appointments(user_id)
        is_owner = False
    else:
        message_obj = update.message
        user_id = update.effective_user.id
        is_owner = (user_id in OWNER_IDS)
        if is_owner:
            appts = [a for a in db.get_all_appointments() if a["status"] == "active"]
        else:
            appts = db.get_user_appointments(user_id)

    if not appts:
        await message_obj.reply_text("ℹ️ Hech qanday aktiv navbat yo'q.")
        return ConversationHandler.END

    text = "📋 *Mavjud navbatlar:*\n\n"
    for a in appts:
        dt = datetime.strptime(a["time"], "%Y-%m-%d %H:%M")
        display = dt.strftime("%d.%m %H:%M")
        text += f"#{a['id']} — {display} ({a['name']})\n"

    text += "\nBekor qilmoqchi bo'lgan navbat *raqamini* kiriting (masalan: `1`):"
    await message_obj.reply_text(text, parse_mode="Markdown")
    return CANCELLING


async def cancel_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        appt_id = int(query.data.replace("owner_cancel_", ""))
        db.cancel_appointment_by_id(appt_id)
        await query.message.reply_text(f"✅ Navbat #{appt_id} bekor qilindi.")
        return

    text = update.message.text.strip()
    try:
        appt_id = int(text)
    except ValueError:
        await update.message.reply_text("❗ Faqat raqam kiriting. Masalan: `3`", parse_mode="Markdown")
        return CANCELLING

    user_id = update.effective_user.id
    is_owner = (user_id in OWNER_IDS)
    
    if is_owner:
        all_appts = db.get_all_appointments()
        ids = [a["id"] for a in all_appts if a["status"] == "active"]
        appts = all_appts
    else:
        appts = db.get_user_appointments(user_id)
        ids = [a["id"] for a in appts]

    if appt_id not in ids:
        await update.message.reply_text("❗ Bu raqamli navbat topilmadi yoki sizga tegishli emas.")
        return CANCELLING

    db.cancel_appointment_by_id(appt_id)
    await update.message.reply_text(f"✅ Navbat #{appt_id} bekor qilindi.")

    appt_info = next(a for a in appts if a["id"] == appt_id)
    dt = datetime.strptime(appt_info["time"], "%Y-%m-%d %H:%M")
    display = dt.strftime("%d.%m %H:%M")

    if is_owner:
        try:
            await context.bot.send_message(
                chat_id=appt_info["user_id"],
                text=f"❌ Hurmatli {appt_info['name']}, sizning *{display}* dagi navbatingiz usta tomonidan bekor qilindi.",
                parse_mode="Markdown"
            )
        except:
            pass
    else:
        for oid in OWNER_IDS:
            try:
                await context.bot.send_message(
                    chat_id=oid,
                    text=(
                        f"❌ *Mijoz navbatni bekor qildi*\n\n"
                        f"🕐 Vaqt: *{display}*\n"
                        f"👤 Ism: {appt_info['name']}\n"
                        f"📞 Telefon: {appt_info['phone']}"
                    ),
                    parse_mode="Markdown"
                )
            except:
                pass

    return ConversationHandler.END


async def show_appointments_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        message_obj = query.message
    else:
        message_obj = update.message

    if update.effective_user.id not in OWNER_IDS:
        await message_obj.reply_text("⛔ Bu funksiya faqat bot egasi uchun.")
        return

    appts = [a for a in db.get_all_appointments() if a["status"] == "active"]

    if not appts:
        await message_obj.reply_text("📭 Hozircha hech qanday navbat yo'q.")
        return

    appts_sorted = sorted(appts, key=lambda x: x["time"])
    text = "📋 *NAVBATLAR RO'YXATI*\n\n"
    keyboard = []

    for a in appts_sorted:
        dt = datetime.strptime(a["time"], "%Y-%m-%d %H:%M")
        display = dt.strftime("%d.%m %H:%M")
        text += (
            f"━━━━━━━━━━━━━━\n"
            f"🔢 #{a['id']}\n"
            f"🕐 {display}\n"
            f"👤 {a['name']}\n"
            f"📞 {a['phone']}\n"
        )
        keyboard.append([
            InlineKeyboardButton(f"❌ #{a['id']} ni bekor qil", callback_data=f"owner_cancel_{a['id']}")
        ])

    text += "━━━━━━━━━━━━━━"
    await message_obj.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def postpone_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        message_obj = query.message
    else:
        message_obj = update.message

    if update.effective_user.id not in OWNER_IDS:
        await message_obj.reply_text("⛔ Bu funksiya faqat bot egasi uchun.")
        return

    changed = db.postpone_all_to_tomorrow()

    if not changed:
        await message_obj.reply_text("📭 Kechiktiriladigan aktiv navbat yo'q.")
        return

    await message_obj.reply_text(f"✅ {len(changed)} ta navbat ertangi kunga ko'chirildi.")

    for item in changed:
        appt = item["appt"]
        old_dt = datetime.strptime(item["old_time"], "%Y-%m-%d %H:%M")
        new_dt = datetime.strptime(appt["time"], "%Y-%m-%d %H:%M")
        old_display = old_dt.strftime("%d.%m %H:%M")
        new_display = new_dt.strftime("%d.%m %H:%M")
        try:
            await context.bot.send_message(
                chat_id=appt["user_id"],
                text=(
                    f"📢 *Navbat kechiktirildi!*\n\n"
                    f"Hurmatli {appt['name']},\n"
                    f"Ustaning ishi chiqib qolganligi sababli navbatingiz kechiktirildi.\n\n"
                    f"⏰ Eski vaqt: *{old_display}*\n"
                    f"📅 Yangi vaqt: *{new_display}*\n\n"
                    f"Noqulaylik uchun uzr so'raymiz! ✂️"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Mijozga xabar yuborishda xato: {e}")


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Amal bekor qilindi.")
    return ConversationHandler.END


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        message_obj = query.message
    else:
        message_obj = update.message

    if update.effective_user.id not in OWNER_IDS:
        await message_obj.reply_text("⛔ Bu funksiya faqat bot egasi uchun.")
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
        f"📁 Jami barcha navbatlar: *{len(all_appts)} ta*\n\n"
    )

    if bugungi:
        text += "📋 *Bugungi navbatlar:*\n"
        for a in sorted(bugungi, key=lambda x: x["time"]):
            dt = datetime.strptime(a["time"], "%Y-%m-%d %H:%M")
            text += f"• {dt.strftime('%H:%M')} — {a['name']} ({a['phone']})\n"

    await message_obj.reply_text(text, parse_mode="Markdown")


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)