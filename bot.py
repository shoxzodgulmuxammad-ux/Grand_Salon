import os
import logging                                                                                
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from config import OWNER_IDS
from handlers import (
    start, book_appointment, handle_time_input,
    handle_name, handle_phone, confirm_booking,
    show_client_appointments, show_appointments_owner, 
    show_stats, cancel_conv
)
import database as db
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

(SELECTING_TIME, ENTERING_NAME, ENTERING_PHONE, CONFIRMING) = range(4)

# --- BARCHA INLINE CALLBACK HARAKATLARINI TUTISH ---
async def handle_inline_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id

    # 1. USTA NAVBATNI BEKOR QILSA (Mijozga xabar boradigan qismi qo'shildi)
    if data.startswith("owner_cancel_"):
        if user_id not in OWNER_IDS: return
        appt_id = int(data.split("_")[-1])
        
        # O'chirishdan oldin mijozning ma'lumotlarini bazadan olib turamiz
        all_appts = db.get_all_appointments()
        target_appt = None
        for a in all_appts:
            if a["id"] == appt_id:
                target_appt = a
                break
        
        # Bazada holatni bekor qilinganga o'zgartiramiz
        db.cancel_appointment_by_id(appt_id)
        await query.message.edit_text(f"✅ ID: {appt_id} raqamli navbat muvaffaqiyatli bekor qilindi.")
        
        # MIJOZGA XABAR YUBORISH QISMI:
        if target_appt:
            try:
                try:
                    dt_obj = datetime.strptime(target_appt['time'], "%Y-%m-%d %H:%M")
                    readable_time = dt_obj.strftime("%d.%m %H:%M")
                except:
                    readable_time = target_appt['time']

                await context.bot.send_message(
                    chat_id=target_appt["user_id"],
                    text=f"❌ *DIQQAT, NAVBATINGIZ BEKOR QILINDI!*\n\nHurmatli {target_appt['name']}, soat *{readable_time}* dagi navbatingiz usta tomonidan bekor qilindi.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Mijozga xabar yuborishda xatolik: {e}")
        
    # 2. Usta bitta navbatni alohida ko'chirsa
    elif data.startswith("owner_postpone_"):
        if user_id not in OWNER_IDS: return
        appt_id = int(data.split("_")[-1])
        res = db.postpone_appointment_by_id(appt_id)
        if res:
            appt = res["appt"]
            try:
                dt_obj = datetime.strptime(appt['time'], "%Y-%m-%d %H:%M")
                readable_new = dt_obj.strftime("%d.%m %H:%M")
            except:
                readable_new = appt['time']
                
            await query.message.edit_text(f"⏳ ID: {appt_id} raqamli navbat ertangi kunga ({readable_new}) ko'chirildi.")
            
            # Faqat o'sha o'zgargan mijozga xabar yuborish
            try:
                await context.bot.send_message(
                    chat_id=appt["user_id"],
                    text=f"⚠️ *DIQQAT, NAVBATINGIZ KO'CHIRILDI!*\n\nHurmatli {appt['name']}, usta sizning navbatingizni ertangi kunga, ya'ni *{readable_new}* vaqtiga kechiktirdi.\nTushunganingiz uchun rahmat!",
                    parse_mode="Markdown"
                )
            except:
                pass
        else:
            await query.message.reply_text("❌ Navbatni ko'chirishda xatolik yuz berdi.")

    # 3. Mijoz o'z navbatini inline tugma bilan bekor qilsa
    elif data.startswith("client_cancel_"):
        appt_id = int(data.split("_")[-1])
        db.cancel_appointment_by_id(appt_id)
        await query.message.edit_text("✅ Navbatingiz muvaffaqiyatli bekor qilindi.")
        
        # Ustaga bildirishnoma borishi
        for owner_id in OWNER_IDS:
            try:
                await context.bot.send_message(
                    chat_id=owner_id,
                    text=f"⚠️ *Navbat bekor qilindi!*\nID: {appt_id} raqamli navbat mijoz tomonidan o'zi bekor qilindi."
                )
            except:
                pass


# Ekran ostidagi asosiy menyu tugmalari
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if user_id in OWNER_IDS:
        if text == "🔄 Navbatlar":
            await show_appointments_owner(update, context)
        elif text == "📊 Statistika":
            await show_stats(update, context)
    else:
        if text == "❌ Navbatlarim / Bekor qilish":
            await show_client_appointments(update, context)


def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("Xatolik: Railway Variables ichida BOT_TOKEN topilmadi!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Navbat olish muloqoti
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & filters.Regex("^✂️ Navbat olish$"), book_appointment)
        ],
        states={
            SELECTING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_input)],
            ENTERING_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            CONFIRMING:     [CallbackQueryHandler(confirm_booking, pattern="^confirm_booking$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    # Pastki panel handlerlari
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(🔄 Navbatlar|📊 Statistika|❌ Navbatlarim / Bekor qilish)$"), handle_menu_buttons))
    
    # Callback inline tugmalari handleri
    app.add_handler(CallbackQueryHandler(handle_inline_actions, pattern="^(owner_cancel_|owner_postpone_|client_cancel_)"))

    print("✅ Bot xatosiz va inline rejimda ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()