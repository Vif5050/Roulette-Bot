import logging
import random
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters import Command

API_TOKEN = '7894143384:AAGgSoRwwCqxIWJNc4o202MgAffwqznPOXk'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Attack definitions
SECTORS = {
    "Left 6":     [22, 18, 29, 7, 28, 12],
    "Right 6":    [15, 19, 4, 21, 2, 25],
    "Vertical":   [0, 5, 8, 10, 23, 24, 26, 32],
    "Orfelins":   [1, 6, 9, 14, 17, 20, 31, 34],
    "Two Towers": [27, 30, 36, 28, 7, 12, 11, 13]
}

EURO_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30,
              8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7,
              28, 12, 35, 3, 26]

SIXTEEN_NUMBERS = [0, 1, 2, 3, 10, 11, 12, 13,
                   20, 21, 22, 23, 30, 31, 32, 33]

# Emoji coloring
RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_NUMBERS = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}

def color_number(n):
    if n == 0:
        return "🟩 0"
    if n in RED_NUMBERS:
        return f"🟥 {n}"
    return f"⬛️ {n}"

def format_attack(title, numbers):
    return f"\u2728 {title}\nPut on: " + ", ".join([color_number(n) for n in numbers])

def pick_sectoral_attack(user_numbers):
    eligible = {}
    for name, nums in SECTORS.items():
        count = len(set(user_numbers) & set(nums))
        if 4 <= count <= 15:
            eligible[name] = count
    if not eligible:
        return None
    sector_names = list(eligible.keys())
    weights = list(eligible.values())
    chosen = random.choices(sector_names, weights=weights, k=1)[0]
    return (f"Sectoral: {chosen}", SECTORS[chosen])

def pick_3_side_by_side(user_numbers):
    user_set = set(user_numbers)
    candidates = []
    for i in range(len(EURO_ORDER) - 2):
        triplet = EURO_ORDER[i:i+3]
        if all(n in user_set for n in triplet):
            before = EURO_ORDER[i-1] if i > 0 else None
            after = EURO_ORDER[i+3] if i + 3 < len(EURO_ORDER) else None
            full = ([before] if before is not None else []) + triplet + ([after] if after is not None else [])
            candidates.append(full)
    if not candidates:
        return None
    return ("3 Side by Side", random.choice(candidates))

def should_trigger_16_numbers(user_numbers):
    recent = user_numbers[-10:]
    trigger_set = set(SIXTEEN_NUMBERS)
    for i in range(len(user_numbers) - 10, len(user_numbers)):
        if user_numbers[i] in trigger_set:
            for j in range(i + 4, len(user_numbers)):
                if user_numbers[j] in trigger_set:
                    return True
    return False

# Session memory
user_sessions = {}

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_sessions[message.from_user.id] = {}
    await message.answer("Send a list of numbers (between 20 and 50, comma-separated):")

@dp.message_handler()
async def handle_numbers(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_sessions:
        user_sessions[user_id] = {}

    session = user_sessions[user_id]

    # If we are waiting for attack result
    if session.get("awaiting_attack"):
        try:
            new_number = int(message.text.strip())
            session["inputs"].append(new_number)
            if new_number in session["attack_numbers"]:
                limit = session["limit"]
                if len(session["inputs"]) <= limit:
                    await message.answer(f"✅ You won! It took you {len(session['inputs'])} numbers.")
                else:
                    await message.answer(f"❌ Number appeared after {limit} draws. You lost.")
                session.clear()
            else:
                await message.answer("...waiting for a win...")
        except ValueError:
            await message.reply("Send a valid number.")
        return

    # Otherwise, treat as list
    try:
        user_numbers = [int(n.strip()) for n in message.text.split(',') if n.strip().isdigit()]
        if not (20 <= len(user_numbers) <= 50):
            await message.reply("Please send between 20 and 50 numbers.")
            return

        attacks = []

        sec = pick_sectoral_attack(user_numbers)
        if sec:
            attacks.append(sec)

        sbs = pick_3_side_by_side(user_numbers)
        if sbs:
            attacks.append(sbs)

        if should_trigger_16_numbers(user_numbers):
            attacks.append(("16 Numbers", SIXTEEN_NUMBERS))

        if len(attacks) < 2:
            await message.reply("Not enough attack patterns found. Try different numbers.")
            return

        chosen = random.sample(attacks, 2)

        for title, nums in chosen:
            await message.answer(format_attack(title, nums))
            # Now track one of the attacks
            session.clear()
            session["awaiting_attack"] = True
            session["attack_title"] = title
            session["attack_numbers"] = nums
            session["inputs"] = []
            if "Sectoral" in title:
                session["limit"] = 11 if len(nums) == 6 else 8
            elif "3 Side" in title:
                session["limit"] = 13
            elif "16 Numbers" in title:
                session["limit"] = 3
            await message.answer("Now enter numbers one by one until you win or lose.")
            break  # Track only one attack

    except Exception as e:
        await message.reply(f"Error: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
