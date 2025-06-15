import sys
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

TOKEN = "7894143384:AAGgSoRwwCqxIWJNc4o202MgAffwqznPOXk"
OWNER_ID = 1079698307  # replace with your actual Telegram user ID

# Lists of numbers (Roulette layout)
SECTORS = [
    [9, 31, 14, 20, 1, 17, 34, 6],
    [26, 0, 32, 8, 23, 10, 5, 24],
    [15, 19, 24, 21, 2, 25],
    [12, 28, 7, 29, 18, 22],
]

# States
ASK_COUNT, ASK_NUMBERS = range(2)

# Emoji map (red/black/green)
COLOR_MAP = {
    0: "🟩",
    # Reds
    1: "🟥", 3: "🟥", 5: "🟥", 7: "🟥", 9: "🟥", 12: "🟥", 14: "🟥",
    16: "🟥", 18: "🟥", 19: "🟥", 21: "🟥", 23: "🟥", 25: "🟥", 27: "🟥",
    30: "🟥", 32: "🟥", 34: "🟥", 36: "🟥",
    # Blacks
    **{n: "⬛" for n in range(1, 37) if n not in [0, 1, 3, 5, 7, 9, 12, 14, 16, 18,
                                                19, 21, 23, 25, 27, 30, 32, 34, 36]}
}

user_attack_count = {}

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Attack", callback_data="attack")],
        [InlineKeyboardButton("About", callback_data="about")]
    ]
    await update.message.reply_text("Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("This bot is a special tool to only use...")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    keyboard = [
        [InlineKeyboardButton("Sectoral", callback_data="sectoral")],
        [InlineKeyboardButton("Other", callback_data="other")]
    ]
    await update.callback_query.edit_message_text("Choose an attack type:", reply_markup=InlineKeyboardMarkup(keyboard))

async def other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    keyboard = [[InlineKeyboardButton("Shutdown Bot", callback_data="shutdown")]]
    await update.callback_query.edit_message_text(
        "Unfortunately this feature is still in development.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != OWNER_ID:
        await query.answer("🚫 Not authorized.")
        return

    await query.answer()
    await query.edit_message_text("Shutting down... 🛑")
    await context.bot.close()
    await context.application.shutdown()
    sys.exit()

async def sectoral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("How many attacks? (1 to 4)")
    return ASK_COUNT

async def ask_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(update.message.text)
        if n < 1 or n > 4:
            raise ValueError()
        user_attack_count[update.effective_chat.id] = n
        await update.message.reply_text(f"Send {n} number(s), separated by space (e.g. 9 14 20)")
        return ASK_NUMBERS
    except ValueError:
        await update.message.reply_text("Please enter a valid number between 1 and 4.")
        return ASK_COUNT

async def receive_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        nums = list(map(int, update.message.text.strip().split()))
        n = user_attack_count.get(update.effective_chat.id, 0)
        if len(nums) != n:
            await update.message.reply_text(f"You need to send exactly {n} number(s).")
            return ASK_NUMBERS

        messages = []
        for i, num in enumerate(nums):
            for sector in SECTORS:
                if num in sector:
                    color_list = [f"{COLOR_MAP.get(x, '❓')} {x}" for x in sector]
                    messages.append(f"Put on: {' | '.join(color_list)}")
                    break
        await update.message.reply_text("\n\n".join(messages), reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    except Exception:
        await update.message.reply_text("Something went wrong. Please try again.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Set up app
app = Application.builder().token(TOKEN).build()

# Command handler
app.add_handler(CommandHandler("start", start))

# Callback buttons
app.add_handler(CallbackQueryHandler(about, pattern="^about$"))
app.add_handler(CallbackQueryHandler(attack, pattern="^attack$"))
app.add_handler(CallbackQueryHandler(sectoral, pattern="^sectoral$"))
app.add_handler(CallbackQueryHandler(other, pattern="^other$"))
app.add_handler(CallbackQueryHandler(shutdown, pattern="^shutdown$"))

# Conversation for Sectoral input
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(sectoral, pattern="^sectoral$")],
    states={
        ASK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_numbers)],
        ASK_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_numbers)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(conv_handler)

# Run the bot
app.run_polling()
