# Predefined sector attacks and other constants
SECTORAL_ATTACKS = {
    "Left 6": [22, 18, 29, 7, 28, 12],
    "Right 6": [15, 19, 4, 21, 2, 25],
    "Vertical": [0, 5, 8, 10, 23, 24, 26, 32],
    "Orfelins": [1, 6, 9, 14, 17, 20, 31, 34],
    "Two Towers": [27, 30, 36, 28, 7, 12, 11, 13]
}

SIXTEEN_LIST = [0, 1, 2, 3, 10, 11, 12, 13, 20, 21, 22, 23, 30, 31, 32, 33]
WHEEL_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]

def get_sectoral_score(recent, sector):
    """Calculate how many numbers in last 20 spins belong to a sector"""
    return sum(1 for num in recent[:20] if num in SECTORAL_ATTACKS[sector])

def get_side_score(recent):
    """Find consecutive triples in wheel order with recency weighting"""
    best_score = 0
    best_triple = None
    
    # Check all possible consecutive triples
    for i in range(1, len(WHEEL_ORDER) - 3):
        a, b, c = WHEEL_ORDER[i], WHEEL_ORDER[i+1], WHEEL_ORDER[i+2]
        triple = [a, b, c]
        score = 0
        
        # Weight recent appearances
        for idx, num in enumerate(recent[:20]):
            if num in triple:
                score += (20 - idx)  # More recent = higher weight
        
        if score > best_score:
            best_score = score
            best_triple = triple
    
    if best_triple:
        i = WHEEL_ORDER.index(best_triple[0])
        return best_score, [
            WHEEL_ORDER[i-1],
            *best_triple,
            WHEEL_ORDER[i+3]
        ]
    return 0, []

def get_sixteen_score(recent):
    """Check if two 16-list numbers appear with >=3 numbers between them"""
    last_10 = recent[:10]
    for i in range(len(last_10)):
        if last_10[i] in SIXTEEN_LIST:
            for j in range(i+4, min(i+7, len(last_10))):
                if last_10[j] in SIXTEEN_LIST:
                    return 10 - i  # Higher score for more recent hits
    return 0

def select_attacks(recent):
    """Select top 2 attacks based on recent spins"""
    candidates = []
    
    # 1. Sectoral attacks
    for sector in SECTORAL_ATTACKS:
        count = get_sectoral_score(recent, sector)
        if 4 <= count <= 15:
            candidates.append({
                "type": "sectoral",
                "name": sector,
                "numbers": SECTORAL_ATTACKS[sector],
                "score": count
            })
    
    # 2. 3 Side-by-Side attack
    side_score, side_numbers = get_side_score(recent)
    if side_score > 0:
        candidates.append({
            "type": "3 side by side",
            "name": "3 Side by Side",
            "numbers": side_numbers,
            "score": side_score
        })
    
    # 3. 16 Numbers attack
    sixteen_score = get_sixteen_score(recent)
    if sixteen_score > 0:
        candidates.append({
            "type": "16 numbers",
            "name": "16 Numbers",
            "numbers": SIXTEEN_LIST,
            "score": sixteen_score
        })
    
    # Select top 2 by score
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:2]

def check_win(attack, spins_count):
    """Check if win condition is met for an attack"""
    if attack["type"] == "sectoral":
        if len(attack["numbers"]) == 6:
            return spins_count <= 11
        else:  # 8 numbers
            return spins_count <= 8
    elif attack["type"] == "3 side by side":
        return spins_count <= 13
    else:  # 16 numbers
        return spins_count <= 3

def main():
    print("Roulette Strategy Bot")
    print("Enter last 20-50 numbers (comma separated, most recent LAST):")
    
    # Get and validate input
    while True:
        nums_input = input("> ").strip()
        nums_list = [int(num.strip()) for num in nums_input.split(",")]
        
        if 20 <= len(nums_list) <= 50:
            # Reverse so most recent is first
            recent = list(reversed(nums_list))
            break
        print("Please enter 20-50 numbers")
    
    # Select attacks
    attacks = select_attacks(recent)
    print("\nRecommended Attacks:")
    for i, attack in enumerate(attacks, 1):
        print(f"{i}. {attack['name']}:")
        print(f"   Numbers: {', '.join(map(str, attack['numbers']))}")
    
    # Track new spins
    spin_count = 0
    print("\nEnter new spins one by line (most recent first):")
    while True:
        spin_count += 1
        new_num = int(input(f"Spin #{spin_count}: ").strip())
        
        # Check if number appears in attacks
        for attack in attacks:
            if new_num in attack["numbers"]:
                if check_win(attack, spin_count):
                    print(f"\n🎉 You WON with {attack['name']} after {spin_count} spins!")
                    return
                else:
                    print(f"\n💥 You LOST! {attack['name']} didn't win within limit.")
                    return

if __name__ == "__main__":
    main()
