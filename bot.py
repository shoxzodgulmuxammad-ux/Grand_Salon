import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from config import BOT_TOKEN, OWNER_IDS
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

# Bosh menyu tugmalari bosilganda ishlaydigan yangi funksiya
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔄 Navbatlar":
        # handlers.py ichidagi mavjud funksiyani chaqiramiz
        await show_appointments_owner(update, context)
        
    elif text == "⏳ Kechiktirish":
        # handlers.py ichidagi mavjud funksiyani chaqiramiz
        await postpone_appointments(update, context)
        
    elif text == "📊 Statistika":
        # handlers.py ichidagi mavjud funksiyani chaqiramiz
        await show_stats(update, context)
        
    elif text == "❌ Bekor qilish":
        # handlers.py ichidagi mavjud funksiyani chaqiramiz
        await cancel_appointment_prompt(update, context)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(book_appointment, pattern="^book$")],
        states={
            SELECTING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_input)],
            ENTERING_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            CONFIRMING:     [CallbackQueryHandler(confirm_booking, pattern="^confirm_booking$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    cancel_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(cancel_appointment_prompt, pattern="^cancel_my$")],
        states={
            CANCELLING: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_appointment)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(cancel_conv_handler)
    
    # Yangi qo'shilgan matnli tugmalar (Panel) uchun handler
    app.add_handler(MessageHandler(
        filters.Text(["🔄 Navbatlar", "⏳ Kechiktirish", "📊 Statistika", "❌ Bekor qilish"]), 
        handle_menu_buttons
    ))

    app.add_handler(CallbackQueryHandler(show_appointments_owner, pattern="^owner_list$"))
    app.add_handler(CallbackQueryHandler(postpone_appointments, pattern="^postpone_all$"))
    app.add_handler(CallbackQueryHandler(show_stats, pattern="^owner_stats$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(cancel_appointment, pattern="^owner_cancel_"))

    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()