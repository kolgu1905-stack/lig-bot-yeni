import random
from typing import List, Tuple, Dict, Any

# ── Slot Machine ───────────────────────────────────────────────────────────────

SLOT_SYMBOLS  = ["🍒", "🍋", "🍊", "🍇", "🔔", "⭐", "7️⃣", "💎"]
SLOT_WEIGHTS  = [22,   18,   15,   12,   10,   8,    5,    2]
SLOT_MULTIPLIERS = {
    "🍒": 3, "🍋": 4, "🍊": 5, "🍇": 8,
    "🔔": 10, "⭐": 20, "7️⃣": 50, "💎": 100,
}

def spin_slots(bet: int) -> Tuple[List[str], int, str]:
    reels = random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)
    if reels[0] == reels[1] == reels[2]:
        mult = SLOT_MULTIPLIERS[reels[0]]
        win  = bet * mult
        msg  = f"🎰 *JACKPOT!* {mult}x kazandınız!"
    elif len(set(reels)) == 2:
        win = int(bet * 1.5)
        msg = "✨ İki eşleşme! 1.5x kazandınız!"
    else:
        win = 0
        msg = "😔 Kaybettiniz."
    return reels, win, msg


# ── Penalty ───────────────────────────────────────────────────────────────────

PENALTY_POSITIONS = ["sol", "orta", "sag"]

# Kademelere göre çarpanlar ve kaleci tutma ihtimalleri
PENALTY_LEVELS = {
    1:  {"mult": 1.4,  "save_chance": 0.0},   # Garantili
    2:  {"mult": 2.0,  "save_chance": 0.0},   # Garantili
    3:  {"mult": 2.8,  "save_chance": 0.15},  # %15
    4:  {"mult": 4.0,  "save_chance": 0.25},  # %25
    5:  {"mult": 5.5,  "save_chance": 0.35},  # %35
    6:  {"mult": 8.0,  "save_chance": 0.45},  # %45
    7:  {"mult": 12.0, "save_chance": 0.55},  # %55
    8:  {"mult": 18.0, "save_chance": 0.65},  # %65
    9:  {"mult": 28.0, "save_chance": 0.75},  # %75
    10: {"mult": 50.0, "save_chance": 0.80},  # %80 — büyük ödül!
}

def play_penalty_level(choice: str, level: int) -> Tuple[bool, str, str]:
    """
    Belirli bir kademede penaltı at.
    Returns: (is_goal, visual, keeper_choice)
    """
    cfg          = PENALTY_LEVELS.get(level, PENALTY_LEVELS[10])
    save_chance  = cfg["save_chance"]
    pos_labels   = {"sol": "SOL", "orta": "ORTA", "sag": "SAĞ"}

    # Garantili kademelerde (1-4) her zaman gol
    if save_chance == 0.0:
        keeper = random.choice([p for p in PENALTY_POSITIONS if p != choice])
        visual = (
            f"🥅 Kaleci: *{pos_labels[keeper]}*\n"
            f"⚽ Sen: *{pos_labels[choice]}*\n"
            f"🎯 *GOL!* Kaleci şansı yoktu!"
        )
        return True, visual, keeper

    # 5-10. kademelerde save_chance ihtimaliyle kaleci tutabilir
    saved = random.random() < save_chance
    if saved:
        keeper = choice  # Kaleci doğru yöne atladı
        visual = (
            f"🥅 Kaleci: *{pos_labels[keeper]}*\n"
            f"⚽ Sen: *{pos_labels[choice]}*\n"
            f"🧤 *KURTARıLDI!* Kaleci doğru yönü tahmin etti!"
        )
        return False, visual, keeper
    else:
        keeper = random.choice([p for p in PENALTY_POSITIONS if p != choice])
        visual = (
            f"🥅 Kaleci: *{pos_labels[keeper]}*\n"
            f"⚽ Sen: *{pos_labels[choice]}*\n"
            f"🎯 *GOL!* Kaleci yanıldı!"
        )
        return True, visual, keeper

def play_penalty(choice: str) -> Tuple[bool, str, str]:
    """Geriye dönük uyumluluk için eski fonksiyon."""
    keeper = random.choice(PENALTY_POSITIONS)
    pos_labels = {"sol": "SOL", "orta": "ORTA", "sag": "SAĞ"}
    if keeper == choice:
        return False, f"🥅 Kaleci: *{pos_labels[keeper]}*\n⚽ Sen: *{pos_labels[choice]}*\n🧤 Kaleci kurtardı!", keeper
    return True, f"🥅 Kaleci: *{pos_labels[keeper]}*\n⚽ Sen: *{pos_labels[choice]}*\n🎯 GOL! Kaleci atlayamadı!", keeper


# ── Blackjack ──────────────────────────────────────────────────────────────────

SUITS = ["♠️", "♥️", "♦️", "♣️"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def new_deck() -> List[Tuple[str, str]]:
    deck: List[Tuple[str, str]] = [(r, s) for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck

def card_value(rank: str) -> int:
    if rank in ("J", "Q", "K"): return 10
    if rank == "A": return 11
    return int(rank)

def hand_value(hand: List[Tuple[str, str]]) -> int:
    total = sum(card_value(r) for r, _ in hand)
    aces  = sum(1 for r, _ in hand if r == "A")
    while total > 21 and aces:
        total -= 10
        aces  -= 1
    return total

def format_hand(hand: List[Tuple[str, str]]) -> str:
    return " ".join(f"`{r}{s}`" for r, s in hand)

def deal_blackjack() -> Dict[str, Any]:
    deck = new_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    return {"deck": deck, "player": player, "dealer": dealer}


# ── Roulette ───────────────────────────────────────────────────────────────────

RED_NUMBERS   = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

def _num_emoji(n: int) -> str:
    if n == 0: return "🟢"
    return "🔴" if n in RED_NUMBERS else "⚫"

def spin_roulette() -> int:
    return random.randint(0, 36)

def play_roulette(bet: int, choice: str) -> Tuple[int, str, int]:
    number = spin_roulette()
    mult, _ = roulette_result(number, choice)
    win = int(bet * mult)
    if number == 0:                  color = "🟢 Sıfır"
    elif number in RED_NUMBERS:      color = "🔴 Kırmızı"
    else:                            color = "⚫ Siyah"
    return number, color, win

def roulette_result(number: int, bet_type: str) -> Tuple[float, str]:
    em = _num_emoji(number)
    bet_type = str(bet_type).lower().replace("ı", "i").replace("ç", "c")
    if number == 0:
        return 0.0, "🟢 *Sıfır!* Kasa kazandı."
    if bet_type in ["kirmizi", "red"]:
        return (1.9, f"{em} *{number}* Kırmızı! (1.9x)") if number in RED_NUMBERS else (0.0, f"{em} *{number}* Kaybetti.")
    if bet_type in ["siyah", "black"]:
        return (1.9, f"{em} *{number}* Siyah! (1.9x)") if number in BLACK_NUMBERS else (0.0, f"{em} *{number}* Kaybetti.")
    if bet_type in ["tek", "odd"]:
        return (1.9, f"{em} *{number}* Tek! (1.9x)") if number % 2 == 1 else (0.0, f"{em} *{number}* Kaybetti.")
    if bet_type in ["cift", "even"]:
        return (1.9, f"{em} *{number}* Çift! (1.9x)") if number % 2 == 0 else (0.0, f"{em} *{number}* Kaybetti.")
    try:
        target = int(bet_type)
        if 0 <= target <= 36:
            return (35.0, f"🎯 *{number}*! Tam isabetli! (35x)") if number == target else (0.0, f"{em} *{number}* Kaybettiniz.")
    except ValueError:
        pass
    return 0.0, "❌ Geçersiz bahis tipi."


# ── Coin Flip ──────────────────────────────────────────────────────────────────

def flip_coin(choice: str) -> Tuple[str, bool]:
    choice = choice.lower().replace("ı", "i")
    result = random.choice(["yazi", "tura"])
    label  = "🦅 Tura" if result == "tura" else "🪙 Yazı"
    return label, result == choice


# ── Dice ───────────────────────────────────────────────────────────────────────

DICE_FACES = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

def roll_dice(choice: str) -> Tuple[int, int, float, str]:
    choice = choice.lower().replace("ü", "u").replace("ö", "o").replace("ş", "s")
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    total = d1 + d2
    f1, f2 = DICE_FACES[d1 - 1], DICE_FACES[d2 - 1]
    if choice in ["yuksek", "high"]:
        return (d1, d2, 1.9, f"{f1}{f2}=*{total}* Yüksek! (1.9x)") if total > 7 else (d1, d2, 0.0, f"{f1}{f2}=*{total}* Kaybetti.")
    if choice in ["dusuk", "low"]:
        return (d1, d2, 1.9, f"{f1}{f2}=*{total}* Düşük! (1.9x)") if total < 7 else (d1, d2, 0.0, f"{f1}{f2}=*{total}* Kaybetti.")
    if choice in ["yedi", "seven", "7"]:
        return (d1, d2, 4.0, f"{f1}{f2}=*{total}* TAM 7! (4x)") if total == 7 else (d1, d2, 0.0, f"{f1}{f2}=*{total}* 7 değil.")
    return d1, d2, 0.0, "❌ Geçersiz seçim. Kullanım: `dusuk`, `yuksek` veya `7`."


# ── Zeplin (Crash) ────────────────────────────────────────────────────────────

def generate_crash_point() -> float:
    r = random.random()
    crash = round(0.99 / (1.0 - r), 2)
    return max(min(crash, 1000.0), 1.15)


# ── Mines ─────────────────────────────────────────────────────────────────────
# 25 kare, mayın sayısını seç, açtıkça çarpan artar. %10 house edge.

MINES_GRID = 25

def mines_multiplier(mines: int, revealed: int) -> float:
    safe = MINES_GRID - mines
    if revealed <= 0: return 1.0
    mult = 1.0
    for i in range(revealed):
        remaining_safe  = safe - i
        remaining_total = MINES_GRID - i
        if remaining_safe <= 0: return 0.0
        mult *= remaining_total / remaining_safe
    return round(mult * 0.90, 2)

def mines_next_multiplier(mines: int, revealed: int) -> float:
    return mines_multiplier(mines, revealed + 1)

def generate_mines_board(mines: int) -> List[int]:
    return random.sample(range(MINES_GRID), mines)

def mines_reveal(board: List[int], cell: int) -> bool:
    """True = mayın (patlama)."""
    return cell in board


# ── Tower ─────────────────────────────────────────────────────────────────────
# Her katta N kapıdan doğruyu seç. Yanlışta patlarsın. %10 house edge.

TOWER_DIFFICULTIES = {
    "kolay": {"doors": 3, "safe": 2},   # 2/3 şans
    "orta":  {"doors": 3, "safe": 1},   # 1/3 şans
    "zor":   {"doors": 4, "safe": 1},   # 1/4 şans
}

def tower_multiplier(difficulty: str, floor: int) -> float:
    cfg  = TOWER_DIFFICULTIES.get(difficulty, TOWER_DIFFICULTIES["orta"])
    odds = cfg["safe"] / cfg["doors"]
    return round((1.0 / odds) ** floor * 0.90, 2)

def tower_next_multiplier(difficulty: str, floor: int) -> float:
    return tower_multiplier(difficulty, floor + 1)

def tower_pick(difficulty: str) -> bool:
    """True = doğru kapı, False = bomba."""
    cfg = TOWER_DIFFICULTIES.get(difficulty, TOWER_DIFFICULTIES["orta"])
    return random.random() < (cfg["safe"] / cfg["doors"])


# ── Plinko ────────────────────────────────────────────────────────────────────
# Top 8 satır iner, sol/sağ kayar, son slota göre ödül. %10 house edge.

PLINKO_ROWS        = 8
PLINKO_MULTIPLIERS = [10.0, 3.0, 1.4, 0.7, 0.4, 0.7, 1.4, 3.0, 10.0]

def play_plinko(bet: int) -> Tuple[int, float, int, str]:
    pos  = 0
    path = []
    for _ in range(PLINKO_ROWS):
        if random.random() < 0.5:
            pos += 1
            path.append("▶️")
        else:
            path.append("◀️")
    mult     = round(PLINKO_MULTIPLIERS[pos] * 0.90, 2)
    win      = int(bet * mult)
    path_str = "".join(path)
    slots    = " ".join(
        f"[{m}x]" if i == pos else f"{m}x"
        for i, m in enumerate(PLINKO_MULTIPLIERS)
    )
    visual = f"🔵 {path_str}\n🎯 {slots}"
    return pos, mult, win, visual


# ── Çark Çevir (Spin Wheel) ───────────────────────────────────────────────────
# Günde 1 kez ücretsiz. %10 ihtimalle sıfır (house edge).

WHEEL_SEGMENTS = [
    {"label": "💀 Sıfır!",   "value": 0,       "weight": 10},
    {"label": "🎁 500",      "value": 500,      "weight": 20},
    {"label": "💰 1.000",    "value": 1_000,    "weight": 18},
    {"label": "💵 2.500",    "value": 2_500,    "weight": 15},
    {"label": "💎 5.000",    "value": 5_000,    "weight": 12},
    {"label": "🔥 10.000",   "value": 10_000,   "weight": 10},
    {"label": "⭐ 25.000",   "value": 25_000,   "weight": 8},
    {"label": "🚀 50.000",   "value": 50_000,   "weight": 5},
    {"label": "👑 100.000",  "value": 100_000,  "weight": 2},
]

def spin_wheel() -> Dict:
    weights = [s["weight"] for s in WHEEL_SEGMENTS]
    return random.choices(WHEEL_SEGMENTS, weights=weights, k=1)[0]
