import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

SELECTING_ATTACK_COUNT, ENTERING_NUMBERS = range(2)

SECTORS = [
    [9, 31, 14, 20, 1, 17, 34, 6],
    [26, 0, 32, 8, 23, 10, 5, 24],
    [15, 19, 24, 21, 2, 25],
    [12, 28, 7, 29, 18, 22],
]

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Attack", callback_data='attack')],
        [InlineKeyboardButton("About", callback_data='about')]
    ]
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'about':
        await query.edit_message_text("This bot is a special tool to only use under certain protocols. 🛰️")
    elif query.data == 'attack':
        keyboard = [
            [InlineKeyboardButton("Sectoral", callback_data='sectoral')],
            [InlineKeyboardButton("Other", callback_data='other')]
        ]
        await query.edit_message_text("Choose type of attack:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'other':
        await query.edit_message_text("Unfortunately this feature is still in development.")
    elif query.data == 'sectoral':
        await query.edit_message_text("How many attacks? (Choose 1–4)")
        return SELECTING_ATTACK_COUNT

async def get_attack_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(update.message.text)
        if n not in [1, 2, 3, 4]:
            raise ValueError
        context.user_data['n'] = n
        context.user_data['numbers'] = []
        await update.message.reply_text(f"Enter {n} numbers (one per message):")
        return ENTERING_NUMBERS
    except ValueError:
        await update.message.reply_text("Please enter a valid number between 1 and 4.")
        return SELECTING_ATTACK_COUNT

async def collect_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        num = int(update.message.text)
        context.user_data['numbers'].append(num)
        if len(context.user_data['numbers']) == context.user_data['n']:
            response = ""
            for i, sector in enumerate(SECTORS[:context.user_data['n']]):
                sector_str = ""
                for val in sector:
                    if val == 0:
                        emoji = "🟩"
                    elif val in RED_NUMBERS:
                        emoji = "🟥"
                    elif val in BLACK_NUMBERS:
                        emoji = "⬛"
                    else:
                        emoji = "❓"
                    sector_str += f"{emoji}{val} "
                response += f"Put on: {sector_str.strip()}\n"
            await update.message.reply_text(response)
            return ConversationHandler.END
        else:
            await update.message.reply_text("Enter next number:")
            return ENTERING_NUMBERS
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return ENTERING_NUMBERS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(os.environ["TOKEN"]).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback)],
        states={
            SELECTING_ATTACK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_attack_count)],
            ENTERING_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_numbers)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(handle_callback))
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
