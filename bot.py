import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from collections import deque
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Predefined attacks
SECTORAL_ATTACKS = {
    "Left 6": [22, 18, 29, 7, 28, 12],
    "Right 6": [15, 19, 4, 21, 2, 25],
    "Vertical": [0, 5, 8, 10, 23, 24, 26, 32],
    "Orfelins": [1, 6, 9, 14, 17, 20, 31, 34],
    "Two Towers": [27, 30, 36, 11, 13]  # Removed duplicates
}

SIXTEEN_LIST = [0, 1, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23, 30, 31, 32, 33]

# European roulette wheel order (0-36)
WHEEL_ORDER = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10,
    5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26
]

# Russian number mapping (0-36)
RUSSIAN_NUMBERS = {
    'ноль': 0, 'нуль': 0, '0': 0,
    'один': 1, '1': 1, 'одна': 1, 'одно': 1,
    'два': 2, '2': 2, 'две': 2,
    'три': 3, '3': 3,
    'четыре': 4, '4': 4,
    'пять': 5, '5': 5,
    'шесть': 6, '6': 6,
    'семь': 7, '7': 7,
    'восемь': 8, '8': 8,
    'девять': 9, '9': 9,
    'десять': 10, '10': 10,
    'одиннадцать': 11, '11': 11,
    'двенадцать': 12, '12': 12,
    'тринадцать': 13, '13': 13,
    'четырнадцать': 14, '14': 14,
    'пятнадцать': 15, '15': 15,
    'шестнадцать': 16, '16': 16,
    'семнадцать': 17, '17': 17,
    'восемнадцать': 18, '18': 18,
    'девятнадцать': 19, '19': 19,
    'двадцать': 20, '20': 20,
    'двадцатьодин': 21, 'двадцать один': 21, '21': 21,
    'двадцатьдва': 22, 'двадцать два': 22, '22': 22,
    'двадцатьтри': 23, 'двадцать три': 23, '23': 23,
    'двадцатьчетыре': 24, 'двадцать четыре': 24, '24': 24,
    'двадцатьпять': 25, 'двадцать пять': 25, '25': 25,
    'двадцатьшесть': 26, 'двадцать шесть': 26, '26': 26,
    'двадцатьсемь': 27, 'двадцать семь': 27, '27': 27,
    'двадцатьвосемь': 28, 'двадцать восемь': 28, '28': 28,
    'двадцатьдевять': 29, 'двадцать девять': 29, '29': 29,
    'тридцать': 30, '30': 30,
    'тридцатьодин': 31, 'тридцать один': 31, '31': 31,
    'тридцатьдва': 32, 'тридцать два': 32, '32': 32,
    'тридцатьтри': 33, 'тридцать три': 33, '33': 33,
    'тридцатьчетыре': 34, 'тридцать четыре': 34, '34': 34,
    'тридцатьпять': 35, 'тридцать пять': 35, '35': 35,
    'тридцатьшесть': 36, 'тридцать шесть': 36, '36': 36
}

# Define colors for visualization
REDS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
COLOR_EMOJIS = {
    'GREEN': '🟩',
    'RED': '🟥',
    'BLACK': '⬛'
}

class UserSession:
    def __init__(self):
        self.recent_numbers = deque(maxlen=50)
        self.active_attacks = []
        self.spins_since_attack = 0
        self.state = "AWAITING_HISTORY"
        self.attack_history = []

# Global session storage
user_sessions = {}

def get_session(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = UserSession()
    return user_sessions[chat_id]

def parse_input(text):
    """Parse input with support for Russian numbers"""
    numbers = []
    for item in re.split(r'[,;.\s]+', text.strip()):
        if not item:
            continue
            
        # Try converting directly to integer
        if item.isdigit():
            num = int(item)
            if 0 <= num <= 36:
                numbers.append(num)
            continue
            
        # Try matching Russian number
        item_lower = item.lower()
        for rus, num in RUSSIAN_NUMBERS.items():
            if rus in item_lower:
                numbers.append(num)
                break
    return numbers

def colorize_number(num):
    """Add color emoji to number"""
    if num == 0:
        return f"{COLOR_EMOJIS['GREEN']} {num}"
    elif num in REDS:
        return f"{COLOR_EMOJIS['RED']} {num}"
    else:
        return f"{COLOR_EMOJIS['BLACK']} {num}"

def format_numbers(numbers):
    """Format numbers with colors"""
    return '  '.join(colorize_number(num) for num in numbers)

def get_sectoral_score(recent, sector):
    """Calculate sector score with recency weighting"""
    score = 0
    for i, num in enumerate(list(recent)[:20]):
        if num in SECTORAL_ATTACKS[sector]:
            weight = 1.5 if i < 5 else 1.0
            score += weight
    return score

def get_side_score(recent):
    """Find best consecutive triple on wheel with neighbors"""
    positions = {num: idx for idx, num in enumerate(WHEEL_ORDER)}
    best_score = 0
    best_triple = None
    
    # Check last 20 spins
    spins = list(recent)[:20]
    for i in range(len(spins) - 2):
        a, b, c = spins[i], spins[i+1], spins[i+2]
        idx_a, idx_b, idx_c = positions.get(a), positions.get(b), positions.get(c)
        
        if None in (idx_a, idx_b, idx_c):
            continue
            
        # Check consecutive positions (handle wheel wrap)
        sorted_idxs = sorted([idx_a, idx_b, idx_c])
        is_consecutive = (
            (sorted_idxs[1] - sorted_idxs[0] == 1 and 
             sorted_idxs[2] - sorted_idxs[1] == 1) or
            (sorted_idxs[0] == 0 and 
             sorted_idxs[1] == len(WHEEL_ORDER)-2 and 
             sorted_idxs[2] == len(WHEEL_ORDER)-1)
        )
        
        if is_consecutive:
            triple = (a, b, c)
            score = (20 - i)  # More recent = higher score
            if score > best_score:
                best_score = score
                best_triple = triple
    
    if best_triple:
        # Find neighbors
        idx = positions[best_triple[0]]
        prev_idx = (idx - 1) % len(WHEEL_ORDER)
        next_idx = (idx + 3) % len(WHEEL_ORDER)
        return best_score, [WHEEL_ORDER[prev_idx]] + list(best_triple) + [WHEEL_ORDER[next_idx]]
    return 0, []

def get_sixteen_score(recent):
    """Check for two 16-list numbers with ≥3 numbers between"""
    last_10 = list(recent)[:10]
    sixteen_positions = [i for i, num in enumerate(last_10) if num in SIXTEEN_LIST]
    
    for i in range(len(sixteen_positions)):
        for j in range(i+1, len(sixteen_positions)):
            gap = sixteen_positions[j] - sixteen_positions[i] - 1
            if gap >= 3:
                # Higher score for more recent hits
                return 20 - sixteen_positions[j]  
    return 0

def select_attacks(recent):
    """Select top 2 attacks based on recent spins"""
    candidates = []
    
    # Sectoral attacks
    for sector in SECTORAL_ATTACKS:
        score = get_sectoral_score(recent, sector)
        if 4 <= score <= 15:
            candidates.append({
                'type': 'sectoral',
                'name': sector,
                'numbers': SECTORAL_ATTACKS[sector],
                'score': score
            })
    
    # 3 Side-by-Side attack
    side_score, side_numbers = get_side_score(recent)
    if side_score > 0:
        candidates.append({
            'type': '3 side by side',
            'name': '3 Side by Side',
            'numbers': side_numbers,
            'score': side_score
        })
    
    # 16 Numbers attack
    sixteen_score = get_sixteen_score(recent)
    if sixteen_score > 0:
        candidates.append({
            'type': '16 numbers',
            'name': '16 Numbers',
            'numbers': SIXTEEN_LIST,
            'score': sixteen_score
        })
    
    # Select top 2 by score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:2]

def check_win(attack, spins_count):
    """Check if win condition is met for an attack"""
    if attack['type'] == 'sectoral':
        if len(attack['numbers']) == 6:
            return spins_count <= 11
        else:  # 8 numbers
            return spins_count <= 8
    elif attack['type'] == '3 side by side':
        return spins_count <= 13
    else:  # 16 numbers
        return spins_count <= 3

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and request history"""
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    session.__init__()  # Reset session
    
    welcome_msg = (
        "🎰 *Roulette Strategy Bot* 🎰\n\n"
        "Send the last 20-50 numbers (comma separated, most recent *LAST*):\n\n"
        "Examples:\n"
        "`12, 5, 32, 0, 19, 21`\n"
        "`ноль, тридцать два, пятнадцать, двадцать один`"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_msg,
        parse_mode='Markdown'
    )

async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process initial number history"""
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    
    # Parse input
    numbers = parse_input(update.message.text)
    
    # Validate input
    if not numbers:
        await update.message.reply_text("❌ Invalid input. Please enter numbers between 0-36.")
        return
        
    if len(numbers) < 20:
        await update.message.reply_text(f"❌ Only {len(numbers)} numbers provided. Minimum 20 required.")
        return
        
    # Store history (most recent last → most recent first)
    session.recent_numbers.extendleft(reversed(numbers))
    session.state = "READY"
    
    # Select attacks
    attacks = select_attacks(session.recent_numbers)
    
    if not attacks:
        session.state = "AWAITING_ATTACK"
        await update.message.reply_text(
            "⚠️ No suitable attacks found. Please send the next number:"
        )
        return
        
    # Store active attacks
    session.active_attacks = attacks
    session.spins_since_attack = 0
    session.attack_history = attacks.copy()
    
    # Prepare response
    response = "🎯 *Recommended Attacks:*\n\n"
    for i, attack in enumerate(attacks, 1):
        response += (
            f"⚔️ *Attack #{i}: {attack['name']}*\n"
            f"Type: `{attack['type']}`\n"
            f"Numbers:\n{format_numbers(attack['numbers'])}\n\n"
        )
    
    response += "Now send new numbers one by line:"
    
    await update.message.reply_text(
        response,
        parse_mode='Markdown'
    )

async def handle_new_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process new roulette numbers"""
    chat_id = update.effective_chat.id
    session = get_session(chat_id)
    
    # Parse input
    numbers = parse_input(update.message.text)
    if not numbers:
        await update.message.reply_text("❌ Invalid number. Please try again.")
        return
        
    number = numbers[0]
    
    # Add to history (most recent first)
    session.recent_numbers.appendleft(number)
    
    # Handle attack selection phase
    if session.state == "AWAITING_ATTACK":
        attacks = select_attacks(session.recent_numbers)
        
        if not attacks:
            await update.message.reply_text("⚠️ Still no attacks. Send next number:")
            return
            
        session.active_attacks = attacks
        session.spins_since_attack = 0
        session.attack_history = attacks.copy()
        session.state = "MONITORING"
        
        response = "🎯 *Attack Triggered!*\n\n"
        for i, attack in enumerate(attacks, 1):
            response += (
                f"⚔️ *Attack #{i}: {attack['name']}*\n"
                f"Numbers:\n{format_numbers(attack['numbers'])}\n\n"
            )
        response += "Continue sending new numbers:"
        
        await update.message.reply_text(
            response,
            parse_mode='Markdown'
        )
        return
    
    # Handle monitoring phase
    session.spins_since_attack += 1
    win_detected = False
    
    # Check against active attacks
    for attack in session.active_attacks[:]:
        if number in attack['numbers']:
            if check_win(attack, session.spins_since_attack):
                win_detected = True
                session.active_attacks.remove(attack)
                await update.message.reply_text(
                    f"🎉 *WIN!* Attack '{attack['name']}' succeeded in "
                    f"{session.spins_since_attack} spins!",
                    parse_mode='Markdown'
                )
            else:
                session.active_attacks.remove(attack)
                await update.message.reply_text(
                    f"💥 *LOSS!* Attack '{attack['name']}' exceeded "
                    f"{session.spins_since_attack} spins",
                    parse_mode='Markdown'
                )
    
    # Handle session completion
    if not session.active_attacks:
        keyboard = [[InlineKeyboardButton("Restart", callback_data="restart")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🏁 All attacks completed!",
            reply_markup=reply_markup
        )
        return
    
    # Continue monitoring
    status = f"Spins since attack: {session.spins_since_attack}\nActive attacks: {len(session.active_attacks)}"
    await update.message.reply_text(status)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the conversation"""
    query = update.callback_query
    await query.answer()
    await start(update, context)

def main():
    """Start the bot"""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logging.error("TELEGRAM_TOKEN environment variable not set!")
        return
        
    application = ApplicationBuilder().token(token).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
        lambda update, context: (
            handle_history(update, context) if get_session(update.effective_chat.id).state == "AWAITING_HISTORY" 
            else handle_new_number(update, context)
        )
    ))
    application.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    
    # Start bot
    application.run_polling()

if __name__ == "__main__":
    main()
