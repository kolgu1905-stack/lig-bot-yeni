"""
Cumhuriyetçiler Ligi — Futbol Yönetim Sistemi
"""
import random
from typing import List, Tuple, Dict

# ─────────────────────────────────────────────────────────────
# FUTBOLCU VERİTABANI (~150 oyuncu)
# Rating: 60-99 | Mevki: GK, DEF, MID, FWD | Fiyat: rating'e göre
# ─────────────────────────────────────────────────────────────

PLAYERS = [
    # ── SÜPER YILDIZLAR (rating 90+) ──
    {"name": "Mbappé",        "rating": 95, "pos": "FWD"},
    {"name": "Haaland",       "rating": 94, "pos": "FWD"},
    {"name": "Bellingham",    "rating": 92, "pos": "MID"},
    {"name": "Vinicius Jr",   "rating": 93, "pos": "FWD"},
    {"name": "Rodri",         "rating": 92, "pos": "MID"},
    {"name": "De Bruyne",     "rating": 91, "pos": "MID"},
    {"name": "Salah",         "rating": 91, "pos": "FWD"},
    {"name": "Kane",          "rating": 91, "pos": "FWD"},
    {"name": "Lewandowski",   "rating": 90, "pos": "FWD"},
    {"name": "Modric",        "rating": 90, "pos": "MID"},
    {"name": "Van Dijk",      "rating": 90, "pos": "DEF"},
    {"name": "Courtois",      "rating": 91, "pos": "GK"},
    {"name": "Donnarumma",    "rating": 89, "pos": "GK"},
    {"name": "Alisson",       "rating": 90, "pos": "GK"},

    # ── YILDIZLAR (rating 85-89) ──
    {"name": "Foden",         "rating": 88, "pos": "MID"},
    {"name": "Saka",          "rating": 87, "pos": "FWD"},
    {"name": "Pedri",         "rating": 87, "pos": "MID"},
    {"name": "Gavi",          "rating": 85, "pos": "MID"},
    {"name": "Camavinga",     "rating": 85, "pos": "MID"},
    {"name": "Rüdiger",       "rating": 87, "pos": "DEF"},
    {"name": "Militão",       "rating": 86, "pos": "DEF"},
    {"name": "Hakimi",        "rating": 86, "pos": "DEF"},
    {"name": "Theo Hernandez","rating": 85, "pos": "DEF"},
    {"name": "Walker",        "rating": 85, "pos": "DEF"},
    {"name": "Cancelo",       "rating": 85, "pos": "DEF"},
    {"name": "Dias",          "rating": 88, "pos": "DEF"},
    {"name": "Konaté",        "rating": 84, "pos": "DEF"},
    {"name": "Saliba",        "rating": 86, "pos": "DEF"},
    {"name": "Casemiro",      "rating": 86, "pos": "MID"},
    {"name": "Valverde",      "rating": 87, "pos": "MID"},
    {"name": "Tchouameni",    "rating": 84, "pos": "MID"},
    {"name": "Bruno Fernandes","rating": 87, "pos": "MID"},
    {"name": "Ødegaard",      "rating": 86, "pos": "MID"},
    {"name": "Rice",          "rating": 86, "pos": "MID"},
    {"name": "Olmo",          "rating": 84, "pos": "MID"},
    {"name": "Musiala",       "rating": 86, "pos": "MID"},
    {"name": "Wirtz",         "rating": 85, "pos": "MID"},
    {"name": "Griezmann",     "rating": 86, "pos": "FWD"},
    {"name": "Neymar",        "rating": 87, "pos": "FWD"},
    {"name": "Rashford",      "rating": 85, "pos": "FWD"},
    {"name": "Son",           "rating": 87, "pos": "FWD"},
    {"name": "Lautaro",       "rating": 87, "pos": "FWD"},
    {"name": "Osimhen",       "rating": 88, "pos": "FWD"},
    {"name": "Vlahovic",      "rating": 84, "pos": "FWD"},
    {"name": "Isak",          "rating": 85, "pos": "FWD"},
    {"name": "Núñez",         "rating": 83, "pos": "FWD"},
    {"name": "Antony",        "rating": 82, "pos": "FWD"},
    {"name": "Leão",          "rating": 86, "pos": "FWD"},
    {"name": "Ter Stegen",    "rating": 87, "pos": "GK"},
    {"name": "Neuer",         "rating": 87, "pos": "GK"},
    {"name": "Oblak",         "rating": 87, "pos": "GK"},

    # ── TÜRK OYUNCULAR ──
    {"name": "Hakan Çalhanoğlu","rating": 86, "pos": "MID"},
    {"name": "Kenan Yıldız",    "rating": 81, "pos": "FWD"},
    {"name": "Arda Güler",      "rating": 80, "pos": "MID"},
    {"name": "Merih Demiral",   "rating": 81, "pos": "DEF"},
    {"name": "Çağlar Söyüncü",  "rating": 80, "pos": "DEF"},
    {"name": "Zeki Çelik",      "rating": 78, "pos": "DEF"},
    {"name": "Ferdi Kadıoğlu",  "rating": 79, "pos": "DEF"},
    {"name": "Orkun Kökçü",     "rating": 80, "pos": "MID"},
    {"name": "İrfan Can Kahveci","rating": 79, "pos": "MID"},
    {"name": "Salih Özcan",     "rating": 76, "pos": "MID"},
    {"name": "Cengiz Ünder",    "rating": 79, "pos": "FWD"},
    {"name": "Yunus Akgün",     "rating": 76, "pos": "FWD"},
    {"name": "Barış Alper",     "rating": 78, "pos": "FWD"},
    {"name": "Kerem Aktürkoğlu","rating": 78, "pos": "FWD"},
    {"name": "Uğurcan Çakır",   "rating": 80, "pos": "GK"},
    {"name": "Altay Bayındır",  "rating": 76, "pos": "GK"},
    {"name": "Mert Günok",      "rating": 79, "pos": "GK"},

    # ── ORTA SEVİYE (rating 75-84) ──
    {"name": "Hojlund",       "rating": 79, "pos": "FWD"},
    {"name": "Gakpo",         "rating": 82, "pos": "FWD"},
    {"name": "Lookman",       "rating": 81, "pos": "FWD"},
    {"name": "Werner",        "rating": 79, "pos": "FWD"},
    {"name": "Kvaratskhelia", "rating": 86, "pos": "FWD"},
    {"name": "Felix",         "rating": 81, "pos": "FWD"},
    {"name": "Pulisic",       "rating": 82, "pos": "FWD"},
    {"name": "Sterling",      "rating": 81, "pos": "FWD"},
    {"name": "Diaby",         "rating": 82, "pos": "FWD"},
    {"name": "Doku",          "rating": 80, "pos": "FWD"},
    {"name": "Kudus",         "rating": 80, "pos": "FWD"},
    {"name": "Olise",         "rating": 81, "pos": "FWD"},
    {"name": "Bowen",         "rating": 81, "pos": "FWD"},
    {"name": "Mac Allister",  "rating": 83, "pos": "MID"},
    {"name": "Szoboszlai",    "rating": 82, "pos": "MID"},
    {"name": "Mainoo",        "rating": 78, "pos": "MID"},
    {"name": "Eze",           "rating": 81, "pos": "MID"},
    {"name": "Reijnders",     "rating": 81, "pos": "MID"},
    {"name": "Lobotka",       "rating": 84, "pos": "MID"},
    {"name": "Pjanic",        "rating": 78, "pos": "MID"},
    {"name": "Joshua Kimmich","rating": 87, "pos": "MID"},
    {"name": "Goretzka",      "rating": 84, "pos": "MID"},
    {"name": "Frattesi",      "rating": 80, "pos": "MID"},
    {"name": "Barella",       "rating": 86, "pos": "MID"},
    {"name": "Tonali",        "rating": 83, "pos": "MID"},
    {"name": "Locatelli",     "rating": 81, "pos": "MID"},
    {"name": "Bastoni",       "rating": 84, "pos": "DEF"},
    {"name": "Bremer",        "rating": 84, "pos": "DEF"},
    {"name": "Calafiori",     "rating": 80, "pos": "DEF"},
    {"name": "Acerbi",        "rating": 82, "pos": "DEF"},
    {"name": "Pavard",        "rating": 84, "pos": "DEF"},
    {"name": "Theo",          "rating": 84, "pos": "DEF"},
    {"name": "Kounde",        "rating": 85, "pos": "DEF"},
    {"name": "Upamecano",     "rating": 84, "pos": "DEF"},
    {"name": "Tah",           "rating": 82, "pos": "DEF"},
    {"name": "Davies",        "rating": 83, "pos": "DEF"},
    {"name": "Gvardiol",      "rating": 84, "pos": "DEF"},
    {"name": "Stones",        "rating": 84, "pos": "DEF"},
    {"name": "Romero",        "rating": 85, "pos": "DEF"},
    {"name": "Cuadrado",      "rating": 79, "pos": "DEF"},
    {"name": "Maignan",       "rating": 88, "pos": "GK"},
    {"name": "Onana",         "rating": 84, "pos": "GK"},
    {"name": "Sommer",        "rating": 83, "pos": "GK"},
    {"name": "Diogo Costa",   "rating": 84, "pos": "GK"},
    {"name": "Pickford",      "rating": 84, "pos": "GK"},
    {"name": "Lloris",        "rating": 84, "pos": "GK"},

    # ── GENÇ YETENEKLER (rating 70-78) ──
    {"name": "Yamal",         "rating": 84, "pos": "FWD"},
    {"name": "Endrick",       "rating": 78, "pos": "FWD"},
    {"name": "Estêvão",       "rating": 76, "pos": "FWD"},
    {"name": "Mainoo",        "rating": 78, "pos": "MID"},
    {"name": "Tel",           "rating": 76, "pos": "FWD"},
    {"name": "Garnacho",      "rating": 79, "pos": "FWD"},
    {"name": "Wharton",       "rating": 75, "pos": "MID"},
    {"name": "Kobbie",        "rating": 76, "pos": "MID"},
    {"name": "Pavlidis",      "rating": 78, "pos": "FWD"},
    {"name": "Akliouche",     "rating": 76, "pos": "MID"},
    {"name": "Bah",           "rating": 73, "pos": "DEF"},
    {"name": "Hato",          "rating": 75, "pos": "DEF"},
    {"name": "Cubarsi",       "rating": 80, "pos": "DEF"},

    # ── UCUZ OYUNCULAR (rating 65-74) ──
    {"name": "Cevat Çağdaş",  "rating": 72, "pos": "MID"},
    {"name": "Berkay Özcan",  "rating": 71, "pos": "MID"},
    {"name": "Kerem Demirbay","rating": 75, "pos": "MID"},
    {"name": "Caglar Sun",    "rating": 70, "pos": "FWD"},
    {"name": "Halil Akbunar", "rating": 71, "pos": "FWD"},
    {"name": "Ozan Tufan",    "rating": 76, "pos": "MID"},
    {"name": "Berke Özer",    "rating": 73, "pos": "GK"},
    {"name": "Doğan Alemdar", "rating": 72, "pos": "GK"},
    {"name": "Bertuğ Yıldırım","rating": 72, "pos": "FWD"},
    {"name": "Yusuf Sarı",    "rating": 70, "pos": "FWD"},
    {"name": "Emre Mor",      "rating": 73, "pos": "FWD"},
    {"name": "Enes Ünal",     "rating": 76, "pos": "FWD"},
    {"name": "Halil Dervişoğlu","rating": 73, "pos": "FWD"},
    {"name": "Berat Özdemir", "rating": 74, "pos": "MID"},
    {"name": "Taylan Antalyalı","rating": 73, "pos": "MID"},
    {"name": "Dorukhan Toköz","rating": 72, "pos": "MID"},
    {"name": "Atakan Karazor","rating": 73, "pos": "MID"},

    # ── DÜNYA YILDIZLARI EK (rating 85-94) ──
    {"name": "Osimhen",       "rating": 90, "pos": "FWD"},
    {"name": "Lautaro",       "rating": 89, "pos": "FWD"},
    {"name": "Griezmann",     "rating": 88, "pos": "FWD"},
    {"name": "Dembele",       "rating": 87, "pos": "FWD"},
    {"name": "Son",           "rating": 88, "pos": "FWD"},
    {"name": "Diaz L.",       "rating": 86, "pos": "FWD"},
    {"name": "Rashford",      "rating": 85, "pos": "FWD"},
    {"name": "Gnabry",        "rating": 85, "pos": "FWD"},
    {"name": "Kroos",         "rating": 88, "pos": "MID"},
    {"name": "Kimmich",       "rating": 89, "pos": "MID"},
    {"name": "Musiala",       "rating": 87, "pos": "MID"},
    {"name": "Wirtz",         "rating": 88, "pos": "MID"},
    {"name": "Barella",       "rating": 86, "pos": "MID"},
    {"name": "Thiago",        "rating": 86, "pos": "MID"},
    {"name": "Goretzka",      "rating": 85, "pos": "MID"},
    {"name": "Muller",        "rating": 85, "pos": "MID"},
    {"name": "Mac Allister",  "rating": 85, "pos": "MID"},
    {"name": "Zubimendi",     "rating": 85, "pos": "MID"},
    {"name": "Reijnders",     "rating": 84, "pos": "MID"},
    {"name": "Calhanoglu",    "rating": 83, "pos": "MID"},
    {"name": "Nkunku",        "rating": 84, "pos": "MID"},
    {"name": "Thuram M.",     "rating": 85, "pos": "MID"},
    {"name": "Brozovic",      "rating": 84, "pos": "MID"},
    {"name": "Trent Alexander","rating": 87, "pos": "DEF"},
    {"name": "Gvardiol",      "rating": 86, "pos": "DEF"},
    {"name": "Bastoni",       "rating": 86, "pos": "DEF"},
    {"name": "Kounde",        "rating": 86, "pos": "DEF"},
    {"name": "Laporte",       "rating": 85, "pos": "DEF"},
    {"name": "Upamecano",     "rating": 85, "pos": "DEF"},
    {"name": "Gabriel M.",    "rating": 85, "pos": "DEF"},
    {"name": "Akanji",        "rating": 84, "pos": "DEF"},
    {"name": "Stones",        "rating": 84, "pos": "DEF"},
    {"name": "Pavard",        "rating": 84, "pos": "DEF"},
    {"name": "White B.",      "rating": 84, "pos": "DEF"},
    {"name": "Timber",        "rating": 84, "pos": "DEF"},
    {"name": "Dimarco",       "rating": 84, "pos": "DEF"},
    {"name": "Tomori",        "rating": 82, "pos": "DEF"},
    {"name": "Bremer",        "rating": 83, "pos": "DEF"},
    {"name": "Acerbi",        "rating": 83, "pos": "DEF"},
    {"name": "Maignan",       "rating": 88, "pos": "GK"},
    {"name": "Ederson",       "rating": 88, "pos": "GK"},
    {"name": "Ter Stegen",    "rating": 88, "pos": "GK"},
    {"name": "Neuer",         "rating": 87, "pos": "GK"},
    {"name": "Szczęsny",      "rating": 85, "pos": "GK"},
    {"name": "Kobel",         "rating": 84, "pos": "GK"},
    {"name": "Raya",          "rating": 84, "pos": "GK"},
    {"name": "De Gea",        "rating": 84, "pos": "GK"},
    {"name": "Navas",         "rating": 82, "pos": "GK"},
    {"name": "Sommer",        "rating": 84, "pos": "GK"},
    {"name": "Trubin",        "rating": 79, "pos": "GK"},
    {"name": "Lunin",         "rating": 83, "pos": "GK"},

    # ── ORTA SEVİYE EK (rating 76-84) ──
    {"name": "Vlahovic",      "rating": 84, "pos": "FWD"},
    {"name": "Guirassy",      "rating": 83, "pos": "FWD"},
    {"name": "Fullkrug",      "rating": 82, "pos": "FWD"},
    {"name": "Openda",        "rating": 82, "pos": "FWD"},
    {"name": "Depay",         "rating": 82, "pos": "FWD"},
    {"name": "Morata",        "rating": 81, "pos": "FWD"},
    {"name": "Giroud",        "rating": 81, "pos": "FWD"},
    {"name": "Son Heung",     "rating": 82, "pos": "FWD"},
    {"name": "Gomez P.",      "rating": 80, "pos": "FWD"},
    {"name": "Firmino",       "rating": 80, "pos": "FWD"},
    {"name": "Adeyemi",       "rating": 79, "pos": "FWD"},
    {"name": "Zaha",          "rating": 79, "pos": "FWD"},
    {"name": "Rabiot",        "rating": 82, "pos": "MID"},
    {"name": "Zielinski",     "rating": 82, "pos": "MID"},
    {"name": "Diaby",         "rating": 82, "pos": "MID"},
    {"name": "Locatelli",     "rating": 81, "pos": "MID"},
    {"name": "Wijnaldum",     "rating": 81, "pos": "MID"},
    {"name": "Mkhitaryan",    "rating": 80, "pos": "MID"},
    {"name": "Ruiz F.",       "rating": 80, "pos": "MID"},
    {"name": "Saul",          "rating": 79, "pos": "MID"},
    {"name": "Simons",        "rating": 77, "pos": "MID"},
    {"name": "Doue",          "rating": 75, "pos": "MID"},
    {"name": "Cherki",        "rating": 74, "pos": "MID"},
    {"name": "Ndicka",        "rating": 80, "pos": "DEF"},
    {"name": "Maguire",       "rating": 82, "pos": "DEF"},
    {"name": "Lenglet",       "rating": 80, "pos": "DEF"},
    {"name": "Lindelof",      "rating": 79, "pos": "DEF"},
    {"name": "Frimpong",      "rating": 76, "pos": "DEF"},
    {"name": "Llorente",      "rating": 75, "pos": "DEF"},
    {"name": "Odriozola",     "rating": 75, "pos": "DEF"},
    {"name": "Yoro",          "rating": 73, "pos": "DEF"},
    {"name": "Nubel",         "rating": 78, "pos": "GK"},
    {"name": "Bijlow",        "rating": 77, "pos": "GK"},
    {"name": "Ramsdale",      "rating": 82, "pos": "GK"},
    {"name": "Gollini",       "rating": 75, "pos": "GK"},
    {"name": "Caballero",     "rating": 72, "pos": "GK"},

    # ── DÜŞÜK BÜTÇE & YERLI EK (rating 65-74) ──
    {"name": "Madueke",       "rating": 74, "pos": "FWD"},
    {"name": "Bynoe-Gittens", "rating": 72, "pos": "FWD"},
    {"name": "Amdouni",       "rating": 72, "pos": "FWD"},
    {"name": "Demir E.",      "rating": 69, "pos": "FWD"},
    {"name": "Arslan T.",     "rating": 67, "pos": "FWD"},
    {"name": "Ağaoğlu",       "rating": 68, "pos": "FWD"},
    {"name": "Tuncay Er",     "rating": 66, "pos": "MID"},
    {"name": "Demirkol",      "rating": 68, "pos": "MID"},
    {"name": "Şahin C.",      "rating": 67, "pos": "DEF"},
    {"name": "Bozan",         "rating": 66, "pos": "DEF"},
    {"name": "Kaya M.",       "rating": 65, "pos": "GK"},
]

def get_player_price(rating: int) -> int:
    """Rating'e göre LC cinsinden fiyat."""
    if rating >= 95: return 200_000
    if rating >= 92: return 120_000
    if rating >= 89: return 70_000
    if rating >= 85: return 35_000
    if rating >= 80: return 18_000
    if rating >= 75: return 8_000
    if rating >= 70: return 3_500
    return 1_500

def get_player_by_name(name: str):
    """İsme göre futbolcu bul."""
    name_lower = name.lower()
    for p in PLAYERS:
        if p["name"].lower() == name_lower:
            return p
    # Kısmi eşleşme
    for p in PLAYERS:
        if name_lower in p["name"].lower():
            return p
    return None

def get_players_by_position(pos: str, limit: int = 20):
    """Pozisyona göre futbolcu listele."""
    pos = pos.upper()
    return [p for p in PLAYERS if p["pos"] == pos][:limit]

# ─────────────────────────────────────────────────────────────
# LEGEND COIN — Borsa Sistemi
# ─────────────────────────────────────────────────────────────

LC_MIN_RATE = 5     # 1 LC = min 5 casino coin
LC_MAX_RATE = 20    # 1 LC = max 20 casino coin
LC_BASE_RATE = 10   # Ortalama kur

def calculate_current_rate(hour: int) -> int:
    """Saate göre kur hesapla — 5 saat yüksek, 5 saat düşük dalgalı."""
    # 10 saatlik döngü: 5 yüksek + 5 düşük
    cycle_pos = hour % 10
    if cycle_pos < 5:
        # Yükseliş fazı
        progress = cycle_pos / 4  # 0-1 arası
        rate = LC_BASE_RATE + int((LC_MAX_RATE - LC_BASE_RATE) * progress)
    else:
        # Düşüş fazı
        progress = (cycle_pos - 5) / 4
        rate = LC_MAX_RATE - int((LC_MAX_RATE - LC_MIN_RATE) * progress)

    # Küçük dalgalanma ekle
    rate += random.randint(-1, 1)
    return max(LC_MIN_RATE, min(LC_MAX_RATE, rate))

def get_rate_trend(current_hour: int) -> str:
    """Trend göstergesi."""
    current = calculate_current_rate(current_hour)
    prev    = calculate_current_rate(current_hour - 1)
    if current > prev:    return "📈"
    elif current < prev:  return "📉"
    return "➡️"

def get_24h_history(current_hour: int) -> List[Tuple[int, int]]:
    """Son 24 saatin kurunu döndür."""
    history = []
    for i in range(24, 0, -1):
        h = current_hour - i
        history.append((h, calculate_current_rate(h)))
    return history

# ─────────────────────────────────────────────────────────────
# MAÇ SİMÜLASYONU
# ─────────────────────────────────────────────────────────────

def simulate_match_detailed(team1_name: str, team1_squad: List[Dict], team1_form: int,
                            team2_name: str, team2_squad: List[Dict], team2_form: int):
    """
    Detaylı maç simülasyonu.
    Returns: (team1_goals, team2_goals, events, mvp, scorers)
    events: [(minute, type, team, player, detail), ...]
    """
    # İlk 11 oluştur — manuel seçim varsa onu kullan, yoksa rating'e göre
    def pick_starters(squad):
        manual = [p for p in squad if p.get("is_starter") == 1]
        if len(manual) >= 11:
            return manual[:11]
        return sorted(squad, key=lambda x: -x["rating"])[:11]

    team1_starters = pick_starters(team1_squad)
    team2_starters = pick_starters(team2_squad)

    str1 = sum(p["rating"] for p in team1_starters) // max(len(team1_starters), 1)
    str2 = sum(p["rating"] for p in team2_starters) // max(len(team2_starters), 1)

    # Form bonusu (-5 ile +5 arası)
    str1 += team1_form
    str2 += team2_form

    diff = str1 - str2
    team1_xg = max(0.3, (str1 - 60) / 18 + diff * 0.015)
    team2_xg = max(0.3, (str2 - 60) / 18 - diff * 0.015)

    team1_goals = max(0, min(6, int(random.gauss(team1_xg, 0.9))))
    team2_goals = max(0, min(6, int(random.gauss(team2_xg, 0.9))))

    # Forvet ve orta saha gol atma olasılığı yüksek
    def pick_scorer(squad):
        weights = []
        for p in squad:
            if p["pos"] == "FWD":   w = p["rating"] * 4
            elif p["pos"] == "MID": w = p["rating"] * 2
            elif p["pos"] == "DEF": w = p["rating"] * 0.5
            else:                   w = 0.1  # GK
            weights.append(w)
        if not weights: return None
        return random.choices(squad, weights=weights, k=1)[0]

    def pick_assister(squad, scorer):
        candidates = [p for p in squad if p != scorer and p["pos"] != "GK"]
        if not candidates: return None
        weights = [p["rating"] * (2 if p["pos"] == "MID" else 1) for p in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    # Olayları oluştur
    events = []
    scorers = {"team1": [], "team2": []}
    all_goal_minutes = sorted(random.sample(range(2, 90), team1_goals + team2_goals)) if (team1_goals + team2_goals) > 0 else []

    g1_count, g2_count = 0, 0
    for minute in all_goal_minutes:
        # Hangi takım atacak — kalan gole göre rastgele
        team1_remain = team1_goals - g1_count
        team2_remain = team2_goals - g2_count
        if team1_remain > 0 and team2_remain > 0:
            who = "team1" if random.random() < (team1_remain / (team1_remain + team2_remain)) else "team2"
        elif team1_remain > 0:
            who = "team1"
        else:
            who = "team2"

        if who == "team1":
            scorer = pick_scorer(team1_starters)
            assister = pick_assister(team1_starters, scorer)
            scorers["team1"].append({"player": scorer["name"], "minute": minute, "assist": assister["name"] if assister else None})
            events.append((minute, "goal", team1_name, scorer["name"], assister["name"] if assister else None))
            g1_count += 1
        else:
            scorer = pick_scorer(team2_starters)
            assister = pick_assister(team2_starters, scorer)
            scorers["team2"].append({"player": scorer["name"], "minute": minute, "assist": assister["name"] if assister else None})
            events.append((minute, "goal", team2_name, scorer["name"], assister["name"] if assister else None))
            g2_count += 1

    # MVP belirle: en çok gol+asist yapan
    player_stats = {}
    for goal in scorers["team1"] + scorers["team2"]:
        player_stats[goal["player"]] = player_stats.get(goal["player"], 0) + 2  # Gol 2 puan
        if goal["assist"]:
            player_stats[goal["assist"]] = player_stats.get(goal["assist"], 0) + 1  # Asist 1 puan

    mvp = None
    if player_stats:
        mvp = max(player_stats.items(), key=lambda x: x[1])[0]
    else:
        # Skor yoksa kazanan takımın en yüksek rating'li oyuncusu
        if team1_goals > team2_goals:
            mvp = team1_starters[0]["name"] if team1_starters else None
        elif team2_goals > team1_goals:
            mvp = team2_starters[0]["name"] if team2_starters else None

    # Sarı kart olayları ekle (estetik için)
    yellow_count = random.randint(0, 4)
    for _ in range(yellow_count):
        minute = random.randint(10, 88)
        team = random.choice([team1_name, team2_name])
        squad = team1_starters if team == team1_name else team2_starters
        player = random.choice(squad)
        events.append((minute, "yellow", team, player["name"], None))

    events.sort(key=lambda x: x[0])

    return team1_goals, team2_goals, events, mvp, scorers


def simulate_match(team1_strength: int, team2_strength: int) -> Tuple[int, int, List[str]]:
    """Eski uyumluluk için basit versiyon."""
    diff = team1_strength - team2_strength
    team1_xg = max(0.5, (team1_strength - 60) / 15 + diff * 0.01)
    team2_xg = max(0.5, (team2_strength - 60) / 15 - diff * 0.01)
    team1_goals = max(0, min(6, int(random.gauss(team1_xg, 0.8))))
    team2_goals = max(0, min(6, int(random.gauss(team2_xg, 0.8))))
    return team1_goals, team2_goals, []

def calculate_team_strength(players: List[Dict]) -> int:
    """Takımın toplam gücünü hesapla."""
    if not players: return 0
    return sum(p["rating"] for p in players) // len(players)

# ─────────────────────────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────────────────────────

def format_player(p: Dict) -> str:
    """Futbolcuyu güzel formatla."""
    pos_emoji = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}
    return f"{pos_emoji.get(p['pos'], '⚽')} *{p['name']}* — `{p['rating']}` ({p['pos']})"

def get_formation_requirements(formation: str) -> Dict[str, int]:
    """Formasyona göre mevki sayıları."""
    formations = {
        "4-3-3": {"GK": 1, "DEF": 4, "MID": 3, "FWD": 3},
        "4-4-2": {"GK": 1, "DEF": 4, "MID": 4, "FWD": 2},
        "3-5-2": {"GK": 1, "DEF": 3, "MID": 5, "FWD": 2},
        "4-2-3-1":{"GK": 1, "DEF": 4, "MID": 5, "FWD": 1},
    }
    return formations.get(formation, formations["4-3-3"])


# ─────────────────────────────────────────────────────────────
# AKADEMİ — Genç Oyuncular (ucuz, hızlı gelişen)
# ─────────────────────────────────────────────────────────────

YOUTH_FIRST_NAMES = [
    "Emre", "Ahmet", "Mehmet", "Mustafa", "Ali", "Hasan", "Hüseyin",
    "İbrahim", "Murat", "Burak", "Eren", "Berkay", "Onur", "Selim",
    "Furkan", "Cem", "Kerem", "Doruk", "Yiğit", "Kuzey", "Demir",
    "Atakan", "Berke", "Mert", "Yusuf", "Arda", "Kaan", "Barış",
    "Efe", "Ege", "Alper", "Tolga", "Cenk", "Volkan", "Gökhan",
]
YOUTH_LAST_NAMES = [
    "Yılmaz", "Demir", "Şahin", "Çelik", "Yıldız", "Kara", "Koç",
    "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan",
    "Çetin", "Kaya", "Yıldırım", "Erdoğan", "Bulut", "Polat",
    "Avcı", "Korkmaz", "Şen", "Aksoy", "Güneş", "Akar", "Tekin",
]

def generate_youth_player():
    """Rastgele genç oyuncu üret."""
    name = f"{random.choice(YOUTH_FIRST_NAMES)} {random.choice(YOUTH_LAST_NAMES)}"
    rating = random.randint(60, 72)  # Düşük rating ama gelişim potansiyeli yüksek
    pos = random.choice(["GK", "DEF", "DEF", "MID", "MID", "MID", "FWD", "FWD"])
    return {"name": name, "rating": rating, "pos": pos, "is_youth": True}

def get_academy_offerings(count: int = 8):
    """Akademiden satılık genç oyuncuları döndür."""
    return [generate_youth_player() for _ in range(count)]

def get_youth_price(rating: int) -> int:
    """Genç oyuncu fiyatı — normalden %70 daha ucuz."""
    base = get_player_price(rating)
    return max(500, int(base * 0.3))


# ─────────────────────────────────────────────────────────────
# TAKTİK SİSTEMİ
# ─────────────────────────────────────────────────────────────

FORMATIONS = {
    "4-3-3":   {"attack": 1.10, "defense": 0.95, "form_mult": 1.0,  "label": "Hücum Ağırlıklı"},
    "4-4-2":   {"attack": 1.00, "defense": 1.00, "form_mult": 1.0,  "label": "Dengeli"},
    "5-3-2":   {"attack": 0.90, "defense": 1.15, "form_mult": 1.0,  "label": "Defans"},
    "4-2-3-1": {"attack": 1.05, "defense": 1.05, "form_mult": 1.0,  "label": "Kontrollü"},
    "3-5-2":   {"attack": 1.05, "defense": 0.95, "form_mult": 1.15, "label": "Orta Saha Bombası"},
}

TACTICS = {
    "hucum":   {"attack": 1.20, "defense": 0.85, "injury_mult": 1.0,  "label": "⚔️ Hücum"},
    "defans":  {"attack": 0.80, "defense": 1.20, "injury_mult": 1.0,  "label": "🛡️ Defans"},
    "dengeli": {"attack": 1.00, "defense": 1.00, "injury_mult": 1.0,  "label": "⚖️ Dengeli"},
    "pres":    {"attack": 1.10, "defense": 1.10, "injury_mult": 1.66, "label": "🔥 Pres"},
}

def calculate_team_modifier(formation: str, tactic: str):
    """Diziliş + taktik kombinasyonu için son çarpanları döndür."""
    f = FORMATIONS.get(formation, FORMATIONS["4-3-3"])
    t = TACTICS.get(tactic, TACTICS["dengeli"])
    return {
        "attack":      f["attack"] * t["attack"],
        "defense":     f["defense"] * t["defense"],
        "form_mult":   f["form_mult"],
        "injury_mult": t["injury_mult"],
    }


def simulate_match_with_tactics(team1_name, team1_squad, team1_form, team1_formation, team1_tactic,
                                 team2_name, team2_squad, team2_form, team2_formation, team2_tactic):
    """
    Taktik + diziliş etkili gelişmiş simülasyon.
    """
    # Manuel İlk 11 varsa kullan, yoksa rating sırası
    def pick_starters(squad):
        manual = [p for p in squad if p.get("is_starter") == 1]
        if len(manual) >= 11:
            return manual[:11]
        return sorted(squad, key=lambda x: -x["rating"])[:11]

    team1_starters = pick_starters(team1_squad)
    team2_starters = pick_starters(team2_squad)

    str1 = sum(p["rating"] for p in team1_starters) // max(len(team1_starters), 1)
    str2 = sum(p["rating"] for p in team2_starters) // max(len(team2_starters), 1)

    # Modifiyeleri al
    m1 = calculate_team_modifier(team1_formation, team1_tactic)
    m2 = calculate_team_modifier(team2_formation, team2_tactic)

    # Form bonusu (form_mult ile çarpılır)
    str1 += int(team1_form * m1["form_mult"])
    str2 += int(team2_form * m2["form_mult"])

    diff = str1 - str2

    # Hücum/savunma karşılaştırması
    team1_attack_factor  = m1["attack"]  / m2["defense"]
    team2_attack_factor  = m2["attack"]  / m1["defense"]

    base_xg1 = max(0.3, (str1 - 60) / 18 + diff * 0.015)
    base_xg2 = max(0.3, (str2 - 60) / 18 - diff * 0.015)

    team1_xg = base_xg1 * team1_attack_factor
    team2_xg = base_xg2 * team2_attack_factor

    team1_goals = max(0, min(6, int(random.gauss(team1_xg, 0.9))))
    team2_goals = max(0, min(6, int(random.gauss(team2_xg, 0.9))))

    # Skor seçenleri/asistlerin seçimi (eski fonksiyondan)
    def pick_scorer(squad):
        weights = []
        for p in squad:
            if p["pos"] == "FWD":   w = p["rating"] * 4
            elif p["pos"] == "MID": w = p["rating"] * 2
            elif p["pos"] == "DEF": w = p["rating"] * 0.5
            else:                   w = 0.1
            weights.append(w)
        if not weights: return None
        return random.choices(squad, weights=weights, k=1)[0]

    def pick_assister(squad, scorer):
        candidates = [p for p in squad if p != scorer and p["pos"] != "GK"]
        if not candidates: return None
        weights = [p["rating"] * (2 if p["pos"] == "MID" else 1) for p in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    events = []
    scorers = {"team1": [], "team2": []}
    all_goal_minutes = sorted(random.sample(range(2, 90), team1_goals + team2_goals)) if (team1_goals + team2_goals) > 0 else []

    g1_count, g2_count = 0, 0
    for minute in all_goal_minutes:
        team1_remain = team1_goals - g1_count
        team2_remain = team2_goals - g2_count
        if team1_remain > 0 and team2_remain > 0:
            who = "team1" if random.random() < (team1_remain / (team1_remain + team2_remain)) else "team2"
        elif team1_remain > 0:
            who = "team1"
        else:
            who = "team2"

        if who == "team1":
            scorer = pick_scorer(team1_starters)
            assister = pick_assister(team1_starters, scorer)
            scorers["team1"].append({"player": scorer["name"], "minute": minute, "assist": assister["name"] if assister else None})
            events.append((minute, "goal", team1_name, scorer["name"], assister["name"] if assister else None))
            g1_count += 1
        else:
            scorer = pick_scorer(team2_starters)
            assister = pick_assister(team2_starters, scorer)
            scorers["team2"].append({"player": scorer["name"], "minute": minute, "assist": assister["name"] if assister else None})
            events.append((minute, "goal", team2_name, scorer["name"], assister["name"] if assister else None))
            g2_count += 1

    # MVP
    player_stats = {}
    for goal in scorers["team1"] + scorers["team2"]:
        player_stats[goal["player"]] = player_stats.get(goal["player"], 0) + 2
        if goal["assist"]:
            player_stats[goal["assist"]] = player_stats.get(goal["assist"], 0) + 1
    mvp = None
    if player_stats:
        mvp = max(player_stats.items(), key=lambda x: x[1])[0]
    elif team1_goals > team2_goals:
        mvp = team1_starters[0]["name"] if team1_starters else None
    elif team2_goals > team1_goals:
        mvp = team2_starters[0]["name"] if team2_starters else None

    # Sarı kart olayları
    yellow_count = random.randint(0, 4)
    for _ in range(yellow_count):
        minute = random.randint(10, 88)
        team = random.choice([team1_name, team2_name])
        squad = team1_starters if team == team1_name else team2_starters
        player = random.choice(squad)
        events.append((minute, "yellow", team, player["name"], None))

    events.sort(key=lambda x: x[0])
    return team1_goals, team2_goals, events, mvp, scorers
