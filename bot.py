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
    cancel_appointment_prompt, cancel_appointment,
    show_appointments_owner, postpone_appointments,
    show_stats, back_to_menu, cancel_conv
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

(
    SELECTING_TIME,
    ENTERING_NAME,
    ENTERING_PHONE,
    CONFIRMING,
    CANCELLING
) = range(5)

# Bosh menyu tugmalari (Faqat usta/owner uchun)
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if user_id in OWNER_IDS:
        if text == "🔄 Navbatlar":
            await show_appointments_owner(update, context)
        elif text == "⏳ Kechiktirish":
            await postpone_appointments(update, context)
        elif text == "📊 Statistika":
            await show_stats(update, context)
        elif text == "❌ Bekor qilish":
            # Ustaga tushunarli bo'lishi uchun navbatlar ro'yxatini chiqaradi va o'sha yerdan bekor qilinadi
            await show_appointments_owner(update, context)

# Mantiqiy uzilishni oldini oluvchi funksiyalar
async def client_start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await book_appointment(update, context)

async def client_start_cancelling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await cancel_appointment_prompt(update, context)


def main():
    # Tokenni birinchi navbatda Railway muhitidan, u bo'lmasa config fayldan oladi
    BOT_TOKEN = os.getenv("BOT_TOKEN") or "8857688939:AAG-kxwE9MoaJKslr2hfwpDSI2aMQwZnXR8"

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # --- NAVBAT OLISH TIZIMI (Mijoz uchun) ---
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(book_appointment, pattern="^book$"),
            MessageHandler(filters.TEXT & filters.Regex("^✂️ Navbat olish$"), client_start_booking)
        ],
        states={
            SELECTING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_input)],
            ENTERING_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            CONFIRMING:     [CallbackQueryHandler(confirm_booking, pattern="^confirm_booking$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv), MessageHandler(filters.Regex("^Bekor qilish$"), cancel_conv)],
    )

    # --- NAVBATNI BEKOR QILISH TIZIMI (Mijoz uchun) ---
    cancel_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cancel_appointment_prompt, pattern="^cancel_my$"),
            MessageHandler(filters.TEXT & filters.Regex("^❌ Navbatni bekor qilish$"), client_start_cancelling)
        ],
        states={
            CANCELLING: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_appointment)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv), MessageHandler(filters.Regex("^Bekor qilish$"), cancel_conv)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(cancel_conv_handler)
    
    # Usta menyusi tugmalari uchun handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))

    app.add_handler(CallbackQueryHandler(show_appointments_owner, pattern="^owner_list$"))
    app.add_handler(CallbackQueryHandler(postpone_appointments, pattern="^postpone_all$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^owner_stats$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(cancel_appointment, pattern="^owner_cancel_"))

    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()