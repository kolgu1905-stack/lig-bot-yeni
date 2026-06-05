import os
import random
from datetime import datetime

# PostgreSQL için psycopg2, yoksa sqlite3 fallback
try:
    import psycopg2
    import psycopg2.extras
    USE_PG = True
except ImportError:
    USE_PG = False
    print("[DB] psycopg2 bulunamadı, SQLite kullanılıyor")

import sqlite3
import logging

DB_NAME      = "casino.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Başlangıçta hangi DB kullanıldığını logla
if USE_PG and DATABASE_URL:
    print(f"[DB] PostgreSQL bağlantısı kuruluyor... URL uzunluğu: {len(DATABASE_URL)}")
else:
    print(f"[DB] SQLite kullanılıyor. USE_PG={USE_PG}, DATABASE_URL={'var' if DATABASE_URL else 'YOK'}")

# ─────────────────────────────────────────────────────────────
# Bağlantı
# ─────────────────────────────────────────────────────────────

def connect():
    if USE_PG and DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    return sqlite3.connect(DB_NAME, timeout=10)

def ph():
    """Placeholder: PostgreSQL %s, SQLite ?"""
    return "%s" if (USE_PG and DATABASE_URL) else "?"

def fetchone(cur):
    row = cur.fetchone()
    if row and USE_PG:
        return tuple(row)
    return row

def fetchall(cur):
    rows = cur.fetchall()
    if rows and USE_PG:
        return [tuple(r) for r in rows]
    return rows

# ─────────────────────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────────────────────

def init_db():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS users (
            user_id      BIGINT PRIMARY KEY,
            username     TEXT,
            balance      BIGINT  DEFAULT 10000,
            total_won    BIGINT  DEFAULT 0,
            total_lost   BIGINT  DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            xp           INTEGER DEFAULT 0,
            level        INTEGER DEFAULT 1,
            last_daily   TEXT,
            last_spin    TEXT,
            daily_streak INTEGER DEFAULT 0
        )""")

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS gift_codes (
            code        TEXT PRIMARY KEY,
            amount      BIGINT  NOT NULL,
            max_uses    INTEGER DEFAULT 1,
            used_count  INTEGER DEFAULT 0,
            created_at  TEXT
        )""")

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS used_codes (
            user_id BIGINT,
            code    TEXT,
            PRIMARY KEY(user_id, code)
        )""")

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS user_tasks (
            id            SERIAL PRIMARY KEY,
            user_id       BIGINT,
            task_name     TEXT,
            target        INTEGER,
            current       INTEGER DEFAULT 0,
            is_completed  INTEGER DEFAULT 0,
            assigned_date TEXT,
            task_type     TEXT
        )""" if (USE_PG and DATABASE_URL) else f"""
        CREATE TABLE IF NOT EXISTS user_tasks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER,
            task_name     TEXT,
            target        INTEGER,
            current       INTEGER DEFAULT 0,
            is_completed  INTEGER DEFAULT 0,
            assigned_date TEXT,
            task_type     TEXT
        )""")

        # Weekly XP tablosu
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS weekly_xp (
            user_id    BIGINT PRIMARY KEY,
            username   TEXT,
            weekly_xp  INTEGER DEFAULT 0,
            week_start TEXT
        )""")
        # Loto tabloları
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS loto_rounds (
            id          SERIAL PRIMARY KEY,
            start_time  TEXT,
            end_time    TEXT,
            pot         BIGINT DEFAULT 0,
            winner_id   BIGINT,
            winner_name TEXT,
            is_finished INTEGER DEFAULT 0,
            chat_id     BIGINT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS loto_rounds (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time  TEXT,
            end_time    TEXT,
            pot         INTEGER DEFAULT 0,
            winner_id   INTEGER,
            winner_name TEXT,
            is_finished INTEGER DEFAULT 0,
            chat_id     INTEGER
        )""")
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS loto_tickets (
            round_id   INTEGER,
            user_id    BIGINT,
            username   TEXT,
            bet_amount BIGINT,
            joined_at  TEXT,
            PRIMARY KEY(round_id, user_id)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS loto_tickets (
            round_id   INTEGER,
            user_id    INTEGER,
            username   TEXT,
            bet_amount INTEGER,
            joined_at  TEXT,
            PRIMARY KEY(round_id, user_id)
        )""")
        conn.commit()

# ─────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────

def register_user(user_id: int, username: str):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO users (user_id, username)
                VALUES ({p},{p})
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
            """, (user_id, username))
        else:
            cur.execute(f"SELECT user_id FROM users WHERE user_id={p}", (user_id,))
            if cur.fetchone():
                cur.execute(f"UPDATE users SET username={p} WHERE user_id={p}", (username, user_id))
            else:
                cur.execute(f"INSERT INTO users (user_id, username) VALUES ({p},{p})", (user_id, username))
        conn.commit()

def get_balance(user_id: int) -> int:
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT balance FROM users WHERE user_id={p}", (user_id,))
        row = fetchone(cur)
        return row[0] if row else 0

def update_balance(user_id: int, amount: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET balance = balance + {p} WHERE user_id={p}", (amount, user_id))
        conn.commit()

def get_user_stats(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT username, balance, total_won, total_lost, games_played, xp, level, daily_streak
            FROM users WHERE user_id={p}
        """, (user_id,))
        return fetchone(cur)

def get_leaderboard(limit=10):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT username, balance FROM users ORDER BY balance DESC LIMIT {p}", (limit,))
        return fetchall(cur)

# ─────────────────────────────────────────────────────────────
# XP & Level
# ─────────────────────────────────────────────────────────────

def add_xp(user_id: int, amount: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT xp, level, username FROM users WHERE user_id={p}", (user_id,))
        row = fetchone(cur)
        if not row: return
        xp, level, username = row
        xp += amount
        while xp >= 1000:
            xp -= 1000
            level += 1
        cur.execute(f"UPDATE users SET xp={p}, level={p} WHERE user_id={p}", (xp, level, user_id))
        conn.commit()
    # Haftalık XP'yi güncelle
    add_weekly_xp(user_id, username or f"User_{user_id}", amount)

def record_game(user_id: int, won: int, lost: int):
    # Weekly loss tracking
    try:
        track_weekly_loss(user_id, won, lost)
    except Exception as e:
        print(f"[BANK] weekly_loss hata: {e}")
    # Coin Bank — kaybedilen coinler toplansın
    try:
        if lost > won:
            net_loss = lost - won
            add_to_bank(net_loss)
            print(f"[BANK] +{net_loss} eklendi (user: {user_id})")
    except Exception as e:
        print(f"[BANK] add_to_bank hata: {e}")

    # NET KAR GÖREVİ — kazandıysa "earn" görevini güncelle
    try:
        net_profit = won - lost
        if net_profit > 0:
            update_task_progress(user_id, "earn", net_profit)
            update_weekly_task(user_id, "earn", net_profit)
    except Exception as e:
        print(f"[EARN] görev hata: {e}")

    # ANY_PLAY (haftalık) — her oyun 1 sayar
    try:
        update_weekly_task(user_id, "any_play", 1)
    except Exception as e:
        print(f"[ANY_PLAY] görev hata: {e}")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE users
            SET total_won=total_won+{p}, total_lost=total_lost+{p}, games_played=games_played+1
            WHERE user_id={p}
        """, (won, lost, user_id))
        conn.commit()

# ─────────────────────────────────────────────────────────────
# Daily Bonus
# ─────────────────────────────────────────────────────────────

def get_daily_info(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT last_daily, daily_streak FROM users WHERE user_id={p}", (user_id,))
        row = fetchone(cur)
        return (row[0], row[1]) if row else (None, 0)

def claim_daily(user_id: int, amount: int, streak: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE users SET balance=balance+{p}, last_daily={p}, daily_streak={p}
            WHERE user_id={p}
        """, (amount, datetime.now().isoformat(), streak, user_id))
        conn.commit()

# ─────────────────────────────────────────────────────────────
# Çark Çevir
# ─────────────────────────────────────────────────────────────

def get_last_spin(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT last_spin FROM users WHERE user_id={p}", (user_id,))
        row = fetchone(cur)
        return row[0] if row else None

def claim_spin(user_id: int, amount: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET balance=balance+{p}, last_spin={p} WHERE user_id={p}",
                   (amount, datetime.now().isoformat(), user_id))
        conn.commit()

# ─────────────────────────────────────────────────────────────
# Günlük Görevler
# ─────────────────────────────────────────────────────────────

def get_daily_tasks(user_id: int):
    p = ph()
    bugun = datetime.now().strftime("%Y-%m-%d")
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT task_name, target, current, is_completed
            FROM user_tasks
            WHERE user_id={p} AND assigned_date={p}
        """, (user_id, bugun))
        tasks = fetchall(cur)

        if not tasks:
            havuz = [
                # Kolay (1 görev)
                ("3 Kez Yazı Tura At",      3,     "flip"),
                ("2 Kez Çark Çevir",        1,     "cark"),
                ("1 Kez Zar At",            1,     "dice"),
                # Orta (2 görev)
                ("5 Kez Slot Oyna",         5,     "slot"),
                ("5 Kez Roulette Oyna",     5,     "roulette"),
                ("3 Kez Mines Oyna",        3,     "mines"),
                ("3 Kez Tower Oyna",        3,     "tower"),
                ("3 Kez Plinko Oyna",       3,     "plinko"),
                ("3 Kez Penaltı At",        3,     "penalty"),
                # Zor (1 görev)
                ("1 Kez Düello Kazan",      1,     "duel_win"),
                ("2 Kez Blackjack Kazan",   2,     "blackjack_win"),
                ("Zeplin 2x Üstü Çek",      1,     "zeplin_win"),
                ("Slot\'ta Jackpot Vur",     1,     "slot_jackpot"),
                # Kazanç hedefli
                ("50.000 Coin Kazan",       50000, "earn"),
                ("100.000 Coin Kazan",     100000, "earn"),
            ]
            secilenler = random.sample(havuz, 5)
            for isim, hedef, tip in secilenler:
                cur.execute(f"""
                    INSERT INTO user_tasks (user_id, task_name, target, current, is_completed, assigned_date, task_type)
                    VALUES ({p},{p},{p},0,0,{p},{p})
                """, (user_id, isim, hedef, bugun, tip))
            conn.commit()
            cur.execute(f"""
                SELECT task_name, target, current, is_completed
                FROM user_tasks WHERE user_id={p} AND assigned_date={p}
            """, (user_id, bugun))
            tasks = fetchall(cur)
        return tasks

def update_task_progress(user_id: int, task_type: str, amount: int = 1):
    """
    Görev ilerlemesini güncelle.
    Returns: (reward_total, completed_task_names) — tamamlanan görev varsa ödül ve isimler
    """
    p = ph()
    bugun = datetime.now().strftime("%Y-%m-%d")
    with connect() as conn:
        cur = conn.cursor()

        # Önce mevcut değeri al
        cur.execute(f"""
            SELECT id, task_name, target, current FROM user_tasks
            WHERE user_id={p} AND assigned_date={p} AND task_type={p} AND is_completed=0
        """, (user_id, bugun, task_type))
        tasks = fetchall(cur)

        if not tasks:
            return 0, []

        reward_total = 0
        completed_names = []

        for task_id, task_name, target, current in tasks:
            new_current = min(current + amount, target)
            cur.execute(f"UPDATE user_tasks SET current={p} WHERE id={p}", (new_current, task_id))

            # Hedefe ulaştı mı?
            if new_current >= target:
                cur.execute(f"UPDATE user_tasks SET is_completed=1 WHERE id={p}", (task_id,))
                reward = min(target * 500, 10000)
                reward_total += reward
                completed_names.append(task_name)

        if reward_total > 0:
            cur.execute(f"UPDATE users SET balance=balance+{p} WHERE user_id={p}", (reward_total, user_id))

        conn.commit()
        return reward_total, completed_names

def check_all_tasks_done(user_id: int) -> bool:
    """Günün tüm görevleri tamamlandı mı?"""
    p = ph()
    bugun = datetime.now().strftime("%Y-%m-%d")
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT COUNT(*) FROM user_tasks
            WHERE user_id={p} AND assigned_date={p} AND is_completed=0
        """, (user_id, bugun))
        row = fetchone(cur)
        return row[0] == 0 if row else False

# ─────────────────────────────────────────────────────────────
# Hediye Kodu
# ─────────────────────────────────────────────────────────────

def create_code(code: str, amount: int, max_uses: int = 1) -> bool:
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"""
                INSERT INTO gift_codes (code, amount, max_uses, used_count, created_at)
                VALUES ({p},{p},{p},0,{p})
            """, (code.upper(), amount, max_uses, datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception:
            return False

def use_code(user_id: int, code: str):
    p = ph()
    code = code.upper()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT amount, max_uses, used_count FROM gift_codes WHERE code={p}", (code,))
        row = fetchone(cur)
        if not row:
            return False, "❌ Kod bulunamadı."
        amount, max_uses, used_count = row
        if used_count >= max_uses:
            return False, f"❌ Bu kodun kullanım limiti doldu! ({used_count}/{max_uses})"
        cur.execute(f"SELECT 1 FROM used_codes WHERE user_id={p} AND code={p}", (user_id, code))
        if fetchone(cur):
            return False, "❌ Bu kodu zaten kullandınız."
        cur.execute(f"UPDATE users SET balance=balance+{p} WHERE user_id={p}", (amount, user_id))
        cur.execute(f"INSERT INTO used_codes (user_id,code) VALUES ({p},{p})", (user_id, code))
        cur.execute(f"UPDATE gift_codes SET used_count=used_count+1 WHERE code={p}", (code,))
        conn.commit()
        kalan = max_uses - used_count - 1
        return True, (amount, used_count+1, max_uses, kalan)

# ─────────────────────────────────────────────────────────────
# Admin
# ─────────────────────────────────────────────────────────────

def reset_economy():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance=10000, xp=0, level=1, total_won=0, total_lost=0, games_played=0, daily_streak=0")
        cur.execute("DELETE FROM gift_codes")
        cur.execute("DELETE FROM used_codes")
        cur.execute("DELETE FROM user_tasks")
        conn.commit()

def get_admin_stats():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = fetchone(cur)[0]
        cur.execute("SELECT SUM(balance) FROM users")
        total_coins = fetchone(cur)[0] or 0
        cur.execute("SELECT SUM(games_played) FROM users")
        total_games = fetchone(cur)[0] or 0
        cur.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 1")
        richest = fetchone(cur)
        return total_users, total_coins, total_games, richest

# ─────────────────────────────────────────────────────────────
# RANK SİSTEMİ
# ─────────────────────────────────────────────────────────────

RANKS = [
    {"name": "🌱 Çaylak",     "min_level": 1,   "max_bet_bonus": 0,     "daily_bonus": 0,    "min_bet_discount": 0},
    {"name": "⚔️ Savaşçı",   "min_level": 10,  "max_bet_bonus": 10000, "daily_bonus": 500,  "min_bet_discount": 0},
    {"name": "💎 Usta",       "min_level": 25,  "max_bet_bonus": 25000, "daily_bonus": 1500, "min_bet_discount": 50},
    {"name": "👑 Efsane",     "min_level": 50,  "max_bet_bonus": 50000, "daily_bonus": 3000, "min_bet_discount": 75},
    {"name": "🔥 Ekrem Abi",  "min_level": 100, "max_bet_bonus": 99999, "daily_bonus": 5000, "min_bet_discount": 100},
]

def get_rank(level: int) -> dict:
    rank = RANKS[0]
    for r in RANKS:
        if level >= r["min_level"]:
            rank = r
    return rank

def get_rank_name(level: int) -> str:
    return get_rank(level)["name"]

# ─────────────────────────────────────────────────────────────
# HAFTALIK LIDERBOARD
# ─────────────────────────────────────────────────────────────

def init_weekly_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS weekly_xp (
            user_id    BIGINT PRIMARY KEY,
            username   TEXT,
            weekly_xp  INTEGER DEFAULT 0,
            week_start TEXT
        )""")
        conn.commit()

def add_weekly_xp(user_id: int, username: str, amount: int):
    p = ph()
    week_start = _get_week_start()
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO weekly_xp (user_id, username, weekly_xp, week_start)
                VALUES ({p},{p},{p},{p})
                ON CONFLICT (user_id) DO UPDATE
                SET weekly_xp = CASE
                    WHEN weekly_xp.week_start = EXCLUDED.week_start
                    THEN weekly_xp.weekly_xp + EXCLUDED.weekly_xp
                    ELSE EXCLUDED.weekly_xp
                END,
                week_start = EXCLUDED.week_start,
                username = EXCLUDED.username
            """, (user_id, username, amount, week_start))
        else:
            cur.execute(f"SELECT weekly_xp, week_start FROM weekly_xp WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            if row:
                if row[1] == week_start:
                    cur.execute(f"UPDATE weekly_xp SET weekly_xp=weekly_xp+{p}, username={p} WHERE user_id={p}",
                               (amount, username, user_id))
                else:
                    cur.execute(f"UPDATE weekly_xp SET weekly_xp={p}, week_start={p}, username={p} WHERE user_id={p}",
                               (amount, week_start, username, user_id))
            else:
                cur.execute(f"INSERT INTO weekly_xp (user_id,username,weekly_xp,week_start) VALUES ({p},{p},{p},{p})",
                           (user_id, username, amount, week_start))
        conn.commit()

def get_weekly_leaderboard(limit=10):
    p = ph()
    week_start = _get_week_start()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT username, weekly_xp FROM weekly_xp
            WHERE week_start={p}
            ORDER BY weekly_xp DESC LIMIT {p}
        """, (week_start, limit))
        return fetchall(cur)

def get_weekly_winner():
    """Geçen haftanın kazananını döndür."""
    p = ph()
    last_week = _get_last_week_start()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT username, weekly_xp FROM weekly_xp
            WHERE week_start={p}
            ORDER BY weekly_xp DESC LIMIT 1
        """, (last_week,))
        return fetchone(cur)

def get_user_weekly_rank(user_id: int):
    """Kullanıcının bu haftaki sırası."""
    p = ph()
    week_start = _get_week_start()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT COUNT(*)+1 FROM weekly_xp
            WHERE week_start={p} AND weekly_xp > (
                SELECT COALESCE(weekly_xp,0) FROM weekly_xp WHERE user_id={p} AND week_start={p}
            )
        """, (week_start, user_id, week_start))
        row = fetchone(cur)
        return row[0] if row else 0

def reset_weekly_xp():
    """Haftalık XP'yi sıfırla ve ödülleri dağıt."""
    p = ph()
    week_start = _get_week_start()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT user_id, username, weekly_xp FROM weekly_xp
            WHERE week_start={p}
            ORDER BY weekly_xp DESC LIMIT 10
        """, (week_start,))
        winners = fetchall(cur)
        rewards = {1: 100000, 2: 50000, 3: 25000}
        for i, (uid, uname, xp) in enumerate(winners, 1):
            reward = rewards.get(i, 5000)
            cur.execute(f"UPDATE users SET balance=balance+{p} WHERE user_id={p}", (reward, uid))
        conn.commit()
        return winners

def _get_week_start() -> str:
    from datetime import datetime, timedelta
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")

def _get_last_week_start() -> str:
    from datetime import datetime, timedelta
    today = datetime.now()
    monday = today - timedelta(days=today.weekday() + 7)
    return monday.strftime("%Y-%m-%d")

# ─────────────────────────────────────────────────────────────
# GENİŞLETİLMİŞ ADMİN FONKSİYONLARI
# ─────────────────────────────────────────────────────────────

def get_user_by_username(username: str):
    p = ph()
    username = username.lstrip("@")
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id, username, balance, xp, level, games_played, total_won, total_lost FROM users WHERE LOWER(username)=LOWER({p})", (username,))
        return fetchone(cur)

def get_user_by_id(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id, username, balance, xp, level, games_played, total_won, total_lost FROM users WHERE user_id={p}", (user_id,))
        return fetchone(cur)

def set_balance(user_id: int, amount: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET balance={p} WHERE user_id={p}", (amount, user_id))
        conn.commit()

def deduct_balance(user_id: int, amount: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET balance=GREATEST(0,balance-{p}) WHERE user_id={p}" if (USE_PG and DATABASE_URL) else f"UPDATE users SET balance=MAX(0,balance-{p}) WHERE user_id={p}", (amount, user_id))
        conn.commit()

def add_balance_all(amount: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET balance=balance+{p}", (amount,))
        affected = cur.rowcount
        conn.commit()
        return affected

def ban_user(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
        except Exception:
            pass
        cur.execute(f"UPDATE users SET is_banned=1 WHERE user_id={p}", (user_id,))
        conn.commit()

def unban_user(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET is_banned=0 WHERE user_id={p}", (user_id,))
        conn.commit()

def is_banned(user_id: int) -> bool:
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT is_banned FROM users WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            return bool(row[0]) if row else False
        except Exception:
            return False

def get_detailed_stats():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = fetchone(cur)[0]
        cur.execute("SELECT SUM(balance) FROM users")
        total_coins = fetchone(cur)[0] or 0
        cur.execute("SELECT SUM(games_played) FROM users")
        total_games = fetchone(cur)[0] or 0
        cur.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 1")
        richest = fetchone(cur)
        cur.execute("SELECT COUNT(*) FROM users WHERE games_played > 0")
        active_users = fetchone(cur)[0]
        cur.execute("SELECT AVG(balance) FROM users")
        avg_balance = int(fetchone(cur)[0] or 0)
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_coins": total_coins,
            "avg_balance": avg_balance,
            "total_games": total_games,
            "richest": richest,
        }

def get_all_users_sorted():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, balance, level, games_played FROM users ORDER BY balance DESC LIMIT 20")
        return fetchall(cur)

# ─────────────────────────────────────────────────────────────
# LOTO SİSTEMİ
# ─────────────────────────────────────────────────────────────

def init_loto_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS loto_rounds (
            id          SERIAL PRIMARY KEY,
            start_time  TEXT,
            end_time    TEXT,
            pot         BIGINT DEFAULT 0,
            winner_id   BIGINT,
            winner_name TEXT,
            is_finished INTEGER DEFAULT 0,
            chat_id     BIGINT
        )""" if (USE_PG and DATABASE_URL) else f"""
        CREATE TABLE IF NOT EXISTS loto_rounds (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time  TEXT,
            end_time    TEXT,
            pot         INTEGER DEFAULT 0,
            winner_id   INTEGER,
            winner_name TEXT,
            is_finished INTEGER DEFAULT 0,
            chat_id     INTEGER
        )""")
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS loto_tickets (
            round_id   INTEGER,
            user_id    BIGINT,
            username   TEXT,
            bet_amount BIGINT,
            joined_at  TEXT,
            PRIMARY KEY(round_id, user_id)
        )""" if (USE_PG and DATABASE_URL) else f"""
        CREATE TABLE IF NOT EXISTS loto_tickets (
            round_id   INTEGER,
            user_id    INTEGER,
            username   TEXT,
            bet_amount INTEGER,
            joined_at  TEXT,
            PRIMARY KEY(round_id, user_id)
        )""")
        conn.commit()

def create_loto_round(chat_id: int, duration_hours: int = 2):
    """Yeni loto turu oluştur, ID döndür."""
    from datetime import datetime, timedelta
    p = ph()
    now = datetime.now()
    end = now + timedelta(hours=duration_hours)
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO loto_rounds (start_time, end_time, pot, is_finished, chat_id)
                VALUES ({p},{p},0,0,{p}) RETURNING id
            """, (now.isoformat(), end.isoformat(), chat_id))
            row = cur.fetchone()
            conn.commit()
            return row[0]
        else:
            cur.execute(f"""
                INSERT INTO loto_rounds (start_time, end_time, pot, is_finished, chat_id)
                VALUES ({p},{p},0,0,{p})
            """, (now.isoformat(), end.isoformat(), chat_id))
            conn.commit()
            return cur.lastrowid

def get_active_loto():
    """Aktif loto turunu getir."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT id, start_time, end_time, pot, chat_id FROM loto_rounds WHERE is_finished=0 ORDER BY id DESC LIMIT 1")
        return fetchone(cur)

MAX_LOTO_TICKETS = 3  # Bir kullanıcı max kaç kez bahis ekleyebilir

def _ensure_ticket_count_column():
    """ticket_count kolonu yoksa ekle — ayrı bağlantıda."""
    try:
        with connect() as conn:
            conn.autocommit = True if (USE_PG and DATABASE_URL) else False
            cur = conn.cursor()
            cur.execute("ALTER TABLE loto_tickets ADD COLUMN ticket_count INTEGER DEFAULT 1")
            if not (USE_PG and DATABASE_URL):
                conn.commit()
    except Exception:
        pass

# Modül yüklendiğinde bir kez çalıştır
_ticket_column_ensured = False

def join_loto(round_id: int, user_id: int, username: str, bet: int):
    """Kullanıcıyı loto turuna kaydet veya bahsini artır."""
    global _ticket_column_ensured
    from datetime import datetime
    p = ph()

    # İlk çağrıda kolon kontrolü yap
    if not _ticket_column_ensured:
        _ensure_ticket_count_column()
        _ticket_column_ensured = True

    with connect() as conn:
        cur = conn.cursor()

        # Zaten kayıtlı mı?
        cur.execute(f"SELECT bet_amount, ticket_count FROM loto_tickets WHERE round_id={p} AND user_id={p}",
                   (round_id, user_id))
        existing = fetchone(cur)

        if existing:
            current_bet, ticket_count = existing
            ticket_count = ticket_count or 1
            if ticket_count >= MAX_LOTO_TICKETS:
                return False, f"❌ Maksimum {MAX_LOTO_TICKETS} kez bahis artırabilirsiniz! (Şu an: {ticket_count}/{MAX_LOTO_TICKETS})"
            # Bahsini artır
            new_total = current_bet + bet
            new_count = ticket_count + 1
            cur.execute(f"UPDATE loto_tickets SET bet_amount={p}, ticket_count={p} WHERE round_id={p} AND user_id={p}",
                       (new_total, new_count, round_id, user_id))
            cur.execute(f"UPDATE loto_rounds SET pot=pot+{p} WHERE id={p}", (bet, round_id))
            conn.commit()
            return True, f"✅ Bahsin artırıldı! ({new_count}/{MAX_LOTO_TICKETS}) Toplam: {new_total:,} coin"

        # İlk katılım
        cur.execute(f"INSERT INTO loto_tickets (round_id, user_id, username, bet_amount, joined_at, ticket_count) VALUES ({p},{p},{p},{p},{p},1)",
                   (round_id, user_id, username, bet, datetime.now().isoformat()))
        cur.execute(f"UPDATE loto_rounds SET pot=pot+{p} WHERE id={p}", (bet, round_id))
        conn.commit()
        return True, "✅ Loto turuna kayıt oldun! (1/3)"

def get_loto_participants(round_id: int):
    global _ticket_column_ensured
    p = ph()
    if not _ticket_column_ensured:
        _ensure_ticket_count_column()
        _ticket_column_ensured = True
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT username, bet_amount, COALESCE(ticket_count,1) FROM loto_tickets WHERE round_id={p} ORDER BY bet_amount DESC", (round_id,))
            return fetchall(cur)
        except Exception:
            # Tamamen başarısız olursa yeni bağlantıyla 2-kolonlu sorgu
            pass
    with connect() as conn2:
        cur2 = conn2.cursor()
        cur2.execute(f"SELECT username, bet_amount FROM loto_tickets WHERE round_id={p} ORDER BY bet_amount DESC", (round_id,))
        rows = fetchall(cur2)
        return [(r[0], r[1], 1) for r in rows]

def finish_loto(round_id: int):
    """Loto turunu bitir, kazananı belirle ve ödülü ver."""
    import random
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id, username, bet_amount FROM loto_tickets WHERE round_id={p}", (round_id,))
        tickets = fetchall(cur)
        if not tickets:
            cur.execute(f"UPDATE loto_rounds SET is_finished=1 WHERE id={p}", (round_id,))
            conn.commit()
            return None, 0, []
        # Bahisle orantılı şans
        users   = [t[0] for t in tickets]
        weights = [t[2] for t in tickets]
        winner  = random.choices(users, weights=weights, k=1)[0]
        winner_data = next(t for t in tickets if t[0] == winner)
        # Pot'u al
        cur.execute(f"SELECT pot FROM loto_rounds WHERE id={p}", (round_id,))
        pot = fetchone(cur)[0]
        # Kazanana ver
        cur.execute(f"UPDATE users SET balance=balance+{p} WHERE user_id={p}", (pot, winner))
        cur.execute(f"UPDATE loto_rounds SET is_finished=1, winner_id={p}, winner_name={p} WHERE id={p}",
                   (winner, winner_data[1], round_id))
        conn.commit()
        return winner_data, pot, tickets

# ─────────────────────────────────────────────────────────────
# CUMHURİYETÇİLER LİGİ — Veritabanı
# ─────────────────────────────────────────────────────────────

def init_lig_tables():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Takımlar
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_teams (
            user_id        BIGINT PRIMARY KEY,
            team_name      TEXT,
            lc_balance     BIGINT DEFAULT 500000,
            formation      TEXT DEFAULT '4-3-3',
            wins           INTEGER DEFAULT 0,
            draws          INTEGER DEFAULT 0,
            losses         INTEGER DEFAULT 0,
            goals_for      INTEGER DEFAULT 0,
            goals_against  INTEGER DEFAULT 0,
            form           INTEGER DEFAULT 0,
            recent_results TEXT DEFAULT '',
            created_at     TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_teams (
            user_id        INTEGER PRIMARY KEY,
            team_name      TEXT,
            lc_balance     INTEGER DEFAULT 500000,
            formation      TEXT DEFAULT '4-3-3',
            wins           INTEGER DEFAULT 0,
            draws          INTEGER DEFAULT 0,
            losses         INTEGER DEFAULT 0,
            goals_for      INTEGER DEFAULT 0,
            goals_against  INTEGER DEFAULT 0,
            form           INTEGER DEFAULT 0,
            recent_results TEXT DEFAULT '',
            created_at     TEXT
        )""")
        conn.commit()  # CREATE TABLE'ı commit et
        # Kadrolar
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_squad (
            id              SERIAL PRIMARY KEY,
            user_id         BIGINT,
            player_name     TEXT,
            rating          INTEGER,
            base_rating     INTEGER,
            pos             TEXT,
            is_starter      INTEGER DEFAULT 0,
            form            INTEGER DEFAULT 0,
            injury_matches  INTEGER DEFAULT 0
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_squad (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            player_name     TEXT,
            rating          INTEGER,
            base_rating     INTEGER,
            pos             TEXT,
            is_starter      INTEGER DEFAULT 0,
            form            INTEGER DEFAULT 0,
            injury_matches  INTEGER DEFAULT 0
        )""")
        # Maçlar
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_matches (
            id          SERIAL PRIMARY KEY,
            match_date  TEXT,
            team1_id    BIGINT,
            team2_id    BIGINT,
            team1_goals INTEGER,
            team2_goals INTEGER,
            chat_id     BIGINT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_matches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            match_date  TEXT,
            team1_id    INTEGER,
            team2_id    INTEGER,
            team1_goals INTEGER,
            team2_goals INTEGER,
            chat_id     INTEGER
        )""")
        conn.commit()

def _init_lc_codes_if_needed():
    """LC kod tabloları yoksa oluştur."""
    try:
        init_lc_codes_table()
    except Exception:
        pass

def _add_form_columns():
    """Eski lig_teams tablolarına form ve recent_results kolonları ekle."""
    for col_sql in [
        "ALTER TABLE lig_teams ADD COLUMN form INTEGER DEFAULT 0",
        "ALTER TABLE lig_teams ADD COLUMN recent_results TEXT DEFAULT ''",
    ]:
        try:
            with connect() as conn:
                if USE_PG and DATABASE_URL:
                    conn.autocommit = True
                cur = conn.cursor()
                cur.execute(col_sql)
                if not (USE_PG and DATABASE_URL):
                    conn.commit()
        except Exception:
            pass

# Lig tabloları oluşturulduktan sonra çağrılır
_form_columns_added = False

def create_team(user_id: int, team_name: str) -> bool:
    global _form_columns_added
    if not _form_columns_added:
        _add_form_columns()
        _form_columns_added = True

    p = ph()
    from datetime import datetime
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM lig_teams WHERE user_id={p}", (user_id,))
        if fetchone(cur):
            return False
        cur.execute(f"""
            INSERT INTO lig_teams (user_id, team_name, lc_balance, created_at)
            VALUES ({p},{p},500000,{p})
        """, (user_id, team_name, datetime.now().isoformat()))
        conn.commit()
        return True

def get_team(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT team_name, lc_balance, formation, wins, draws, losses, goals_for, goals_against
            FROM lig_teams WHERE user_id={p}
        """, (user_id,))
        return fetchone(cur)

def get_lc_balance(user_id: int) -> int:
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT lc_balance FROM lig_teams WHERE user_id={p}", (user_id,))
        row = fetchone(cur)
        return row[0] if row else 0

def update_lc_balance(user_id: int, amount: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_teams SET lc_balance=lc_balance+{p} WHERE user_id={p}",
                   (amount, user_id))
        conn.commit()

def get_squad(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT player_name, rating, pos, is_starter FROM lig_squad
            WHERE user_id={p} ORDER BY rating DESC
        """, (user_id,))
        return fetchall(cur)

def add_player_to_squad(user_id: int, player_name: str, rating: int, pos: str):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Aynı oyuncu var mı?
        cur.execute(f"SELECT 1 FROM lig_squad WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        if fetchone(cur):
            return False
        cur.execute(f"""
            INSERT INTO lig_squad (user_id, player_name, rating, pos, is_starter)
            VALUES ({p},{p},{p},{p},0)
        """, (user_id, player_name, rating, pos))
        conn.commit()
        return True

def remove_player_from_squad(user_id: int, player_name: str):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM lig_squad WHERE user_id={p} AND LOWER(player_name)=LOWER({p})",
                   (user_id, player_name))
        affected = cur.rowcount
        conn.commit()
        return affected > 0

def get_all_teams_ranked():
    """Lig sıralaması: puan, averaj, atılan gol."""
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, team_name, wins, draws, losses, goals_for, goals_against,
                   (wins*3 + draws) AS points
            FROM lig_teams
            ORDER BY points DESC, (goals_for - goals_against) DESC, goals_for DESC
        """)
        return fetchall(cur)

def update_team_stats(user_id: int, result: str, gf: int, ga: int):
    """result: 'win', 'draw', 'loss'"""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if result == "win":
            cur.execute(f"UPDATE lig_teams SET wins=wins+1, goals_for=goals_for+{p}, goals_against=goals_against+{p} WHERE user_id={p}",
                       (gf, ga, user_id))
        elif result == "draw":
            cur.execute(f"UPDATE lig_teams SET draws=draws+1, goals_for=goals_for+{p}, goals_against=goals_against+{p} WHERE user_id={p}",
                       (gf, ga, user_id))
        else:
            cur.execute(f"UPDATE lig_teams SET losses=losses+1, goals_for=goals_for+{p}, goals_against=goals_against+{p} WHERE user_id={p}",
                       (gf, ga, user_id))
        conn.commit()

def save_match(team1_id: int, team2_id: int, g1: int, g2: int, chat_id: int):
    p = ph()
    from datetime import datetime
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO lig_matches (match_date, team1_id, team2_id, team1_goals, team2_goals, chat_id)
            VALUES ({p},{p},{p},{p},{p},{p})
        """, (datetime.now().isoformat(), team1_id, team2_id, g1, g2, chat_id))
        conn.commit()

# ─────────────────────────────────────────────────────────────
# LC ADMİN — LC kod sistemi ve toplu işlemler
# ─────────────────────────────────────────────────────────────

def init_lc_codes_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lc_gift_codes (
            code        TEXT PRIMARY KEY,
            amount      BIGINT NOT NULL,
            max_uses    INTEGER DEFAULT 1,
            used_count  INTEGER DEFAULT 0,
            created_at  TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lc_gift_codes (
            code        TEXT PRIMARY KEY,
            amount      INTEGER NOT NULL,
            max_uses    INTEGER DEFAULT 1,
            used_count  INTEGER DEFAULT 0,
            created_at  TEXT
        )""")
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lc_used_codes (
            user_id BIGINT,
            code    TEXT,
            PRIMARY KEY(user_id, code)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lc_used_codes (
            user_id INTEGER,
            code    TEXT,
            PRIMARY KEY(user_id, code)
        )""")
        conn.commit()

def create_lc_code(code: str, amount: int, max_uses: int = 1) -> bool:
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"""
                INSERT INTO lc_gift_codes (code, amount, max_uses, used_count, created_at)
                VALUES ({p},{p},{p},0,{p})
            """, (code.upper(), amount, max_uses, datetime.now().isoformat()))
            conn.commit()
            return True
        except Exception:
            return False

def use_lc_code(user_id: int, code: str):
    """LC hediye kodu kullan."""
    p = ph()
    code = code.upper()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT amount, max_uses, used_count FROM lc_gift_codes WHERE code={p}", (code,))
        row = fetchone(cur)
        if not row:
            return False, "❌ LC kodu bulunamadı."
        amount, max_uses, used_count = row
        if used_count >= max_uses:
            return False, f"❌ Bu kodun kullanım limiti doldu! ({used_count}/{max_uses})"
        cur.execute(f"SELECT 1 FROM lc_used_codes WHERE user_id={p} AND code={p}", (user_id, code))
        if fetchone(cur):
            return False, "❌ Bu LC kodunu zaten kullandınız."
        # Lig hesabı kontrol
        cur.execute(f"SELECT 1 FROM lig_teams WHERE user_id={p}", (user_id,))
        if not fetchone(cur):
            return False, "❌ Önce `/takim_kur` ile lig hesabı oluşturun!"
        cur.execute(f"UPDATE lig_teams SET lc_balance=lc_balance+{p} WHERE user_id={p}", (amount, user_id))
        cur.execute(f"INSERT INTO lc_used_codes (user_id,code) VALUES ({p},{p})", (user_id, code))
        cur.execute(f"UPDATE lc_gift_codes SET used_count=used_count+1 WHERE code={p}", (code,))
        conn.commit()
        kalan = max_uses - used_count - 1
        return True, (amount, used_count+1, max_uses, kalan)

def deduct_lc_balance(user_id: int, amount: int):
    """LC bakiyesinden düşür (negatife düşmez)."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"UPDATE lig_teams SET lc_balance=GREATEST(0,lc_balance-{p}) WHERE user_id={p}", (amount, user_id))
        else:
            cur.execute(f"UPDATE lig_teams SET lc_balance=MAX(0,lc_balance-{p}) WHERE user_id={p}", (amount, user_id))
        conn.commit()

def add_lc_all(amount: int) -> int:
    """Tüm lig kullanıcılarına LC yükle."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_teams SET lc_balance=lc_balance+{p}", (amount,))
        affected = cur.rowcount
        conn.commit()
        return affected


def get_team_form(user_id: int) -> int:
    """Takımın güncel formunu döndür (-5 ile +5 arası)."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT form FROM lig_teams WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            return row[0] if row else 0
        except:
            return 0

def update_team_form(user_id: int, result: str):
    """
    Form sistemi: son 5 maç hatırlanır.
    Galibiyet → form +1 (max +5)
    Beraberlik → form değişmez
    Mağlubiyet → form -1 (min -5)
    Üst üste 3 galibiyet/mağlubiyet ekstra etki
    """
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT form, recent_results FROM lig_teams WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            if not row: return
            form, recent = row
            recent = recent or ""

            # Yeni sonucu ekle (max 5 maç sakla)
            new_recent = (recent + ("W" if result == "win" else "D" if result == "draw" else "L"))[-5:]

            # Formu yeniden hesapla
            new_form = 0
            for r in new_recent:
                if r == "W": new_form += 1
                elif r == "L": new_form -= 1

            # Üst üste 3 galibiyet bonusu
            if new_recent.endswith("WWW"):
                new_form += 2
            elif new_recent.endswith("LLL"):
                new_form -= 2

            new_form = max(-5, min(5, new_form))

            cur.execute(f"UPDATE lig_teams SET form={p}, recent_results={p} WHERE user_id={p}",
                       (new_form, new_recent, user_id))
            conn.commit()
        except Exception as e:
            pass

def init_mvp_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_mvp_history (
            id         SERIAL PRIMARY KEY,
            match_date TEXT,
            user_id    BIGINT,
            player     TEXT,
            week_start TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_mvp_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            match_date TEXT,
            user_id    INTEGER,
            player     TEXT,
            week_start TEXT
        )""")
        conn.commit()

def record_mvp(user_id: int, player: str):
    """MVP ödülünü kaydet."""
    from datetime import datetime, timedelta
    p = ph()
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    week_start = monday.strftime("%Y-%m-%d")
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO lig_mvp_history (match_date, user_id, player, week_start)
            VALUES ({p},{p},{p},{p})
        """, (now.isoformat(), user_id, player, week_start))
        conn.commit()

def get_weekly_mvp():
    """Bu haftanın en çok MVP olan oyuncusunu döndür."""
    from datetime import datetime, timedelta
    p = ph()
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    week_start = monday.strftime("%Y-%m-%d")
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"""
                SELECT player, COUNT(*) as cnt FROM lig_mvp_history
                WHERE week_start={p}
                GROUP BY player ORDER BY cnt DESC LIMIT 1
            """, (week_start,))
            return fetchone(cur)
        except:
            return None


# ─────────────────────────────────────────────────────────────
# SEZON SİSTEMİ (30 günlük)
# ─────────────────────────────────────────────────────────────

def init_season_tables():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_seasons (
            id          SERIAL PRIMARY KEY,
            season_no   INTEGER,
            start_date  TEXT,
            end_date    TEXT,
            is_active   INTEGER DEFAULT 1
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_seasons (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            season_no   INTEGER,
            start_date  TEXT,
            end_date    TEXT,
            is_active   INTEGER DEFAULT 1
        )""")
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_champions (
            id          SERIAL PRIMARY KEY,
            season_no   INTEGER,
            position    INTEGER,
            user_id     BIGINT,
            team_name   TEXT,
            points      INTEGER,
            wins        INTEGER,
            goals_for   INTEGER,
            reward      BIGINT,
            end_date    TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_champions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            season_no   INTEGER,
            position    INTEGER,
            user_id     INTEGER,
            team_name   TEXT,
            points      INTEGER,
            wins        INTEGER,
            goals_for   INTEGER,
            reward      INTEGER,
            end_date    TEXT
        )""")
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_season_stats (
            id          SERIAL PRIMARY KEY,
            season_no   INTEGER,
            user_id     BIGINT,
            player_name TEXT,
            goals       INTEGER DEFAULT 0,
            assists     INTEGER DEFAULT 0,
            mvp_count   INTEGER DEFAULT 0
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_season_stats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            season_no   INTEGER,
            user_id     INTEGER,
            player_name TEXT,
            goals       INTEGER DEFAULT 0,
            assists     INTEGER DEFAULT 0,
            mvp_count   INTEGER DEFAULT 0
        )""")
        conn.commit()

def get_active_season():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT season_no, start_date, end_date FROM lig_seasons WHERE is_active=1 ORDER BY id DESC LIMIT 1")
        return fetchone(cur)

def create_new_season():
    """
    Yeni sezon başlat — tüm istatistikleri sıfırlar.
    - Takım puanları, formu, sakatlıkları sıfırlanır
    - Sezon oyuncu istatistikleri (gol, asist) sıfırlanır
    - Conversion limiti sıfırlanır
    - Antrenörler serbest kalır
    """
    from datetime import datetime, timedelta
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # 1. Önceki sezonu kapat
        cur.execute("UPDATE lig_seasons SET is_active=0")

        # 2. Tüm takım istatistiklerini sıfırla
        cur.execute("UPDATE lig_teams SET wins=0, draws=0, losses=0, goals_for=0, goals_against=0, form=0, recent_results=''")

        # 3. Oyuncuların form ve sakatlıklarını sıfırla
        try:
            cur.execute("UPDATE lig_squad SET form=0, injury_matches=0")
        except: pass

        # 4. Conversion limitini sıfırla
        try:
            cur.execute("DELETE FROM lig_conversion")
        except: pass

        # 5. Antrenörleri serbest bırak
        try:
            cur.execute("UPDATE lig_coaches SET active=0")
        except: pass

        # 6. Tatildeki oyuncuları sıfırla
        try:
            cur.execute("DELETE FROM player_vacation")
        except: pass

        # 7. Kiralıkları kapat
        try:
            cur.execute("UPDATE player_loans SET active=0")
        except: pass

        # 8. Pazar ilanlarını kapat
        try:
            cur.execute("UPDATE market_listings SET sold=1 WHERE sold=0")
        except: pass

        # 9. Bekleyen teklifleri iptal et
        try:
            cur.execute("UPDATE player_offers SET status='expired' WHERE status='pending'")
        except: pass

        # 10. Maç durumlarını sıfırla (recent_results boş)
        try:
            cur.execute("UPDATE lig_teams SET recent_results='', form=0")
        except: pass

        # 11. Antrenman sayaçlarını sıfırla
        try:
            cur.execute("DELETE FROM lig_training")
        except: pass

        # 12. Sözleşme uyarılarını sıfırla
        try:
            cur.execute("DELETE FROM lig_contracts")
        except: pass

        # 13. Kamp sayaçları (yeni sezon olduğu için zaten yok ama temizle)
        # season_camps tablosu zaten sezon bazlı, sıfırlama gerek yok

        # 14. Form aksiyonları temizle
        try:
            cur.execute("DELETE FROM form_actions")
        except: pass

        # 15. Kaptan rozetleri kalsın (kullanıcı seçimi)
        # team_captain tablosu korunur

        # 16. Sosyal medya tepkilerini temizle (eski sezona ait)
        try:
            cur.execute("DELETE FROM social_reactions")
        except: pass

        # 17. Lig haberlerini temizle (eski sezona ait)
        try:
            cur.execute("DELETE FROM lig_news")
        except: pass

        # 18. Tahminleri sıfırla
        try:
            cur.execute("DELETE FROM lig_predictions")
        except: pass

        # 19. Yeni sezon ekle
        cur.execute("SELECT MAX(season_no) FROM lig_seasons")
        row = fetchone(cur)
        last_no = row[0] if row and row[0] else 0
        new_no = last_no + 1
        start = datetime.now()
        end = start + timedelta(days=30)
        cur.execute(f"INSERT INTO lig_seasons (season_no, start_date, end_date, is_active) VALUES ({p},{p},{p},1)",
                   (new_no, start.isoformat(), end.isoformat()))
        conn.commit()
        print(f"[SEZON] ✅ Sezon {new_no} başladı! Tüm istatistikler sıfırlandı.")
        return new_no, start, end

def reset_all_team_stats():
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE lig_teams SET wins=0, draws=0, losses=0, goals_for=0, goals_against=0, form=0, recent_results=''")
        conn.commit()

def record_champion(season_no, position, user_id, team_name, points, wins, gf, reward):
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO lig_champions (season_no, position, user_id, team_name, points, wins, goals_for, reward, end_date)
            VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p})
        """, (season_no, position, user_id, team_name, points, wins, gf, reward, datetime.now().isoformat()))
        conn.commit()

def get_champions_history(limit=10):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT season_no, team_name, points, end_date FROM lig_champions WHERE position=1 ORDER BY season_no DESC LIMIT {p}", (limit,))
        return fetchall(cur)

def add_season_player_stat(user_id, player_name, goals=0, assists=0, mvp=0):
    """Sezonluk oyuncu istatistiği güncelle."""
    p = ph()
    season = get_active_season()
    if not season: return
    season_no = season[0]
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT id FROM lig_season_stats WHERE season_no={p} AND user_id={p} AND player_name={p}",
                   (season_no, user_id, player_name))
        row = fetchone(cur)
        if row:
            cur.execute(f"UPDATE lig_season_stats SET goals=goals+{p}, assists=assists+{p}, mvp_count=mvp_count+{p} WHERE id={p}",
                       (goals, assists, mvp, row[0]))
        else:
            cur.execute(f"INSERT INTO lig_season_stats (season_no, user_id, player_name, goals, assists, mvp_count) VALUES ({p},{p},{p},{p},{p},{p})",
                       (season_no, user_id, player_name, goals, assists, mvp))
        conn.commit()

def get_top_scorer():
    """Aktif sezonun gol kralı."""
    p = ph()
    season = get_active_season()
    if not season: return None
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id, player_name, goals FROM lig_season_stats WHERE season_no={p} AND goals>0 ORDER BY goals DESC LIMIT 1", (season[0],))
        return fetchone(cur)

def get_season_mvp():
    """Aktif sezonun en çok MVP olan oyuncusu."""
    p = ph()
    season = get_active_season()
    if not season: return None
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id, player_name, mvp_count FROM lig_season_stats WHERE season_no={p} AND mvp_count>0 ORDER BY mvp_count DESC LIMIT 1", (season[0],))
        return fetchone(cur)


# ─────────────────────────────────────────────────────────────
# OYUNCU GELİŞİMİ + SAKATLIK + FORM + DÖNÜŞÜM LİMİTİ
# ─────────────────────────────────────────────────────────────

def _add_player_columns():
    """Eski lig_squad tablolarına yeni kolonları ekle."""
    for col_sql in [
        "ALTER TABLE lig_squad ADD COLUMN base_rating INTEGER DEFAULT 0",
        "ALTER TABLE lig_squad ADD COLUMN form INTEGER DEFAULT 0",
        "ALTER TABLE lig_squad ADD COLUMN injury_matches INTEGER DEFAULT 0",
    ]:
        try:
            with connect() as conn:
                if USE_PG and DATABASE_URL:
                    conn.autocommit = True
                cur = conn.cursor()
                cur.execute(col_sql)
                if not (USE_PG and DATABASE_URL):
                    conn.commit()
        except Exception:
            pass
    # base_rating'i mevcut rating ile doldur (NULL olanlar için)
    try:
        with connect() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE lig_squad SET base_rating = rating WHERE base_rating IS NULL OR base_rating = 0")
            conn.commit()
    except Exception:
        pass

_player_cols_added = False

def get_squad_detailed(user_id: int):
    """Kadronun detaylı bilgisi (rating, form, sakatlık)."""
    global _player_cols_added
    if not _player_cols_added:
        _add_player_columns()
        _player_cols_added = True
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT player_name, rating, base_rating, pos, form, injury_matches
            FROM lig_squad WHERE user_id={p} ORDER BY rating DESC
        """, (user_id,))
        return fetchall(cur)

def update_player_after_match(user_id: int, player_name: str, scored: int = 0, assisted: int = 0, played: bool = True, is_mvp: bool = False):
    """Maç sonrası oyuncuyu güncelle."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT rating, base_rating, form, injury_matches FROM lig_squad
            WHERE user_id={p} AND player_name={p}
        """, (user_id, player_name))
        row = fetchone(cur)
        if not row: return

        rating, base_rating, form, injury = row
        if not base_rating or base_rating == 0:
            base_rating = rating

        # Form değişimi
        if played:
            if scored or assisted or is_mvp:
                form = min(10, form + 1)
            else:
                form = max(-5, form - 1)
        else:
            # Oynamadıysa form yavaş düşer
            form = max(-3, form - 1)

        # Rating gelişimi (gol/asist ile)
        if scored:
            rating = min(99, rating + 1)
        if is_mvp:
            rating = min(99, rating + 1)

        # Form rating'e etki etsin: base_rating ±5
        effective_rating = base_rating + (form // 2)
        effective_rating = max(50, min(99, effective_rating))
        # Rating'i base + form etkisi olarak güncelle
        rating = effective_rating

        # Sakatlık iyileşme
        if injury > 0:
            injury -= 1

        cur.execute(f"""
            UPDATE lig_squad SET rating={p}, base_rating={p}, form={p}, injury_matches={p}
            WHERE user_id={p} AND player_name={p}
        """, (rating, base_rating, form, injury, user_id, player_name))
        conn.commit()

def injure_player(user_id: int, player_name: str, matches: int = 2):
    """Oyuncuyu sakatla."""
    p = ph()
    import random as _r
    matches = _r.randint(2, 3)
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_squad SET injury_matches={p} WHERE user_id={p} AND player_name={p}",
                   (matches, user_id, player_name))
        conn.commit()
        return matches

def get_healthy_squad(user_id: int):
    """Sakatlı olmayan oyuncular (maç oynayabilenler)."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT player_name, rating, pos FROM lig_squad
            WHERE user_id={p} AND injury_matches=0
            ORDER BY rating DESC
        """, (user_id,))
        return fetchall(cur)

# ── Dönüşüm Limiti ──

def init_conversion_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_conversion (
            user_id      BIGINT,
            season_no    INTEGER,
            total_amount BIGINT DEFAULT 0,
            PRIMARY KEY (user_id, season_no)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_conversion (
            user_id      INTEGER,
            season_no    INTEGER,
            total_amount INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, season_no)
        )""")
        conn.commit()

CONVERSION_LIMIT = 2_500_000  # Sezon başına 2.5M casino coin

def get_conversion_used(user_id: int) -> int:
    """Bu sezonda kullanılan dönüşüm miktarı."""
    p = ph()
    season = get_active_season()
    if not season: return 0
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT total_amount FROM lig_conversion WHERE user_id={p} AND season_no={p}",
                   (user_id, season[0]))
        row = fetchone(cur)
        return row[0] if row else 0

def add_conversion(user_id: int, amount: int):
    """Dönüşüm miktarını kaydet."""
    p = ph()
    season = get_active_season()
    if not season: return
    season_no = season[0]
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO lig_conversion (user_id, season_no, total_amount)
                VALUES ({p},{p},{p})
                ON CONFLICT (user_id, season_no) DO UPDATE
                SET total_amount = lig_conversion.total_amount + EXCLUDED.total_amount
            """, (user_id, season_no, amount))
        else:
            cur.execute(f"SELECT total_amount FROM lig_conversion WHERE user_id={p} AND season_no={p}",
                       (user_id, season_no))
            row = fetchone(cur)
            if row:
                cur.execute(f"UPDATE lig_conversion SET total_amount=total_amount+{p} WHERE user_id={p} AND season_no={p}",
                           (amount, user_id, season_no))
            else:
                cur.execute(f"INSERT INTO lig_conversion (user_id, season_no, total_amount) VALUES ({p},{p},{p})",
                           (user_id, season_no, amount))
        conn.commit()


# ─────────────────────────────────────────────────────────────
# FİKSTÜR + TAHMİN + DERBİ
# ─────────────────────────────────────────────────────────────

def init_fixture_tables():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_fixtures (
            id          SERIAL PRIMARY KEY,
            season_no   INTEGER,
            week_no     INTEGER,
            match_date  TEXT,
            team1_id    BIGINT,
            team2_id    BIGINT,
            is_derby    INTEGER DEFAULT 0,
            is_played   INTEGER DEFAULT 0,
            team1_goals INTEGER,
            team2_goals INTEGER
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_fixtures (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            season_no   INTEGER,
            week_no     INTEGER,
            match_date  TEXT,
            team1_id    INTEGER,
            team2_id    INTEGER,
            is_derby    INTEGER DEFAULT 0,
            is_played   INTEGER DEFAULT 0,
            team1_goals INTEGER,
            team2_goals INTEGER
        )""")
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_predictions (
            fixture_id  INTEGER,
            user_id     BIGINT,
            pred_g1     INTEGER,
            pred_g2     INTEGER,
            reward      BIGINT DEFAULT 0,
            PRIMARY KEY(fixture_id, user_id)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_predictions (
            fixture_id  INTEGER,
            user_id     INTEGER,
            pred_g1     INTEGER,
            pred_g2     INTEGER,
            reward      INTEGER DEFAULT 0,
            PRIMARY KEY(fixture_id, user_id)
        )""")
        conn.commit()

def generate_fixtures(season_no: int, team_ids: list, start_date):
    """
    Double round-robin fikstür oluştur.
    Her takım diğer herkesle 2 kez (ev+deplasman) karşılaşır.
    8 takım → 14 hafta (her takım 14 maç)
    """
    from datetime import timedelta
    if len(team_ids) < 2: return 0

    teams = list(team_ids)
    # Tek sayı varsa BYE eklenir (None)
    if len(teams) % 2 == 1:
        teams.append(None)

    n = len(teams)
    # İLK TUR: Round-robin (circle method)
    first_half = []
    work_teams = list(teams)
    for week in range(n - 1):
        week_matches = []
        for i in range(n // 2):
            t1 = work_teams[i]
            t2 = work_teams[n - 1 - i]
            if t1 is not None and t2 is not None:
                week_matches.append((t1, t2))
        first_half.append(week_matches)
        # Rotasyon (ilki sabit kalır, diğerleri kayar)
        work_teams = [work_teams[0]] + [work_teams[-1]] + work_teams[1:-1]

    # İKİNCİ TUR: İlk tur maçlarını ters çevir (ev/deplasman değişimi)
    second_half = []
    for week_matches in first_half:
        reversed_week = [(t2, t1) for (t1, t2) in week_matches]
        second_half.append(reversed_week)

    # Tüm haftalar (ilk yarı + ikinci yarı)
    all_rounds = first_half + second_half

    p = ph()
    count = 0
    with connect() as conn:
        cur = conn.cursor()
        for week_no, week_matches in enumerate(all_rounds, 1):
            match_date = start_date + timedelta(days=week_no - 1)
            for t1, t2 in week_matches:
                cur.execute(f"""
                    INSERT INTO lig_fixtures
                    (season_no, week_no, match_date, team1_id, team2_id, is_derby)
                    VALUES ({p},{p},{p},{p},{p},0)
                """, (season_no, week_no, match_date.isoformat(), t1, t2))
                count += 1
        conn.commit()
    print(f"[FIKSTUR] Sezon {season_no}: {len(team_ids)} takım, {len(all_rounds)} hafta, {count} maç")
    return count

def mark_derby_matches(season_no: int):
    """Top 5 takım arasındaki maçları derbi olarak işaretle. Her gün yenilenir."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Önce mevcut derbi işaretlerini sıfırla (oynanmamış maçlar için)
        cur.execute(f"UPDATE lig_fixtures SET is_derby=0 WHERE season_no={p} AND is_played=0", (season_no,))
        # Top 5 takımı al
        cur.execute("""
            SELECT user_id FROM lig_teams
            ORDER BY (wins*3+draws) DESC, (goals_for-goals_against) DESC LIMIT 5
        """)
        top5 = [r[0] for r in fetchall(cur)]
        if len(top5) < 2:
            conn.commit()
            return

        placeholders = ",".join([p] * len(top5))
        cur.execute(f"""
            UPDATE lig_fixtures SET is_derby=1
            WHERE season_no={p} AND is_played=0
            AND team1_id IN ({placeholders}) AND team2_id IN ({placeholders})
        """, [season_no] + top5 + top5)
        conn.commit()

def get_fixtures_by_date(target_date_str: str, season_no: int = None):
    """Belirli tarihteki maçları getir."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if season_no:
            cur.execute(f"""
                SELECT f.id, f.week_no, f.match_date, f.team1_id, f.team2_id, f.is_derby,
                       t1.team_name, t2.team_name
                FROM lig_fixtures f
                LEFT JOIN lig_teams t1 ON f.team1_id = t1.user_id
                LEFT JOIN lig_teams t2 ON f.team2_id = t2.user_id
                WHERE f.season_no={p} AND f.match_date LIKE {p} AND f.is_played=0
                ORDER BY f.is_derby DESC
            """, (season_no, target_date_str + "%"))
        else:
            cur.execute(f"""
                SELECT f.id, f.week_no, f.match_date, f.team1_id, f.team2_id, f.is_derby,
                       t1.team_name, t2.team_name
                FROM lig_fixtures f
                LEFT JOIN lig_teams t1 ON f.team1_id = t1.user_id
                LEFT JOIN lig_teams t2 ON f.team2_id = t2.user_id
                WHERE f.match_date LIKE {p} AND f.is_played=0
                ORDER BY f.is_derby DESC
            """, (target_date_str + "%",))
        return fetchall(cur)

def get_today_fixtures(season_no: int):
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    return get_fixtures_by_date(today, season_no)

def get_user_next_match(user_id: int, season_no: int):
    """Kullanıcının sıradaki maçını getir."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT f.id, f.week_no, f.match_date, f.team1_id, f.team2_id, f.is_derby,
                   t1.team_name, t2.team_name
            FROM lig_fixtures f
            LEFT JOIN lig_teams t1 ON f.team1_id = t1.user_id
            LEFT JOIN lig_teams t2 ON f.team2_id = t2.user_id
            WHERE f.season_no={p} AND f.is_played=0
            AND (f.team1_id={p} OR f.team2_id={p})
            ORDER BY f.match_date ASC LIMIT 1
        """, (season_no, user_id, user_id))
        return fetchone(cur)

def get_all_fixtures(season_no: int, week_no: int = None):
    """Sezonun tüm fikstürü veya belirli hafta."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if week_no:
            cur.execute(f"""
                SELECT f.id, f.week_no, f.match_date, f.team1_id, f.team2_id, f.is_derby,
                       t1.team_name, t2.team_name, f.is_played, f.team1_goals, f.team2_goals
                FROM lig_fixtures f
                LEFT JOIN lig_teams t1 ON f.team1_id = t1.user_id
                LEFT JOIN lig_teams t2 ON f.team2_id = t2.user_id
                WHERE f.season_no={p} AND f.week_no={p}
                ORDER BY f.match_date
            """, (season_no, week_no))
        else:
            cur.execute(f"""
                SELECT f.id, f.week_no, f.match_date, f.team1_id, f.team2_id, f.is_derby,
                       t1.team_name, t2.team_name, f.is_played, f.team1_goals, f.team2_goals
                FROM lig_fixtures f
                LEFT JOIN lig_teams t1 ON f.team1_id = t1.user_id
                LEFT JOIN lig_teams t2 ON f.team2_id = t2.user_id
                WHERE f.season_no={p}
                ORDER BY f.match_date
            """, (season_no,))
        return fetchall(cur)

def mark_fixture_played(fixture_id: int, g1: int, g2: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_fixtures SET is_played=1, team1_goals={p}, team2_goals={p} WHERE id={p}",
                   (g1, g2, fixture_id))
        conn.commit()

# ── TAHMİN SİSTEMİ ──

def submit_prediction(fixture_id: int, user_id: int, g1: int, g2: int):
    """Skor tahmini gönder."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO lig_predictions (fixture_id, user_id, pred_g1, pred_g2)
                VALUES ({p},{p},{p},{p})
                ON CONFLICT (fixture_id, user_id) DO UPDATE
                SET pred_g1 = EXCLUDED.pred_g1, pred_g2 = EXCLUDED.pred_g2
            """, (fixture_id, user_id, g1, g2))
        else:
            cur.execute(f"SELECT 1 FROM lig_predictions WHERE fixture_id={p} AND user_id={p}",
                       (fixture_id, user_id))
            if fetchone(cur):
                cur.execute(f"UPDATE lig_predictions SET pred_g1={p}, pred_g2={p} WHERE fixture_id={p} AND user_id={p}",
                           (g1, g2, fixture_id, user_id))
            else:
                cur.execute(f"INSERT INTO lig_predictions (fixture_id, user_id, pred_g1, pred_g2) VALUES ({p},{p},{p},{p})",
                           (fixture_id, user_id, g1, g2))
        conn.commit()

def process_predictions(fixture_id: int, actual_g1: int, actual_g2: int):
    """Tahminleri değerlendir, doğru bilenleri ödüllendir."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id, pred_g1, pred_g2 FROM lig_predictions WHERE fixture_id={p}",
                   (fixture_id,))
        preds = fetchall(cur)
        winners = []
        for uid, pg1, pg2 in preds:
            reward = 0
            if pg1 == actual_g1 and pg2 == actual_g2:
                # Tam skor: 10.000 LC
                reward = 10000
            elif (pg1 > pg2 and actual_g1 > actual_g2) or (pg1 < pg2 and actual_g1 < actual_g2) or (pg1 == pg2 and actual_g1 == actual_g2):
                # Sadece sonucu doğru bildi: 2.000 LC
                reward = 2000
            if reward > 0:
                # Lig hesabı varsa LC ver, yoksa casino coin
                cur.execute(f"SELECT 1 FROM lig_teams WHERE user_id={p}", (uid,))
                if fetchone(cur):
                    cur.execute(f"UPDATE lig_teams SET lc_balance=lc_balance+{p} WHERE user_id={p}", (reward, uid))
                cur.execute(f"UPDATE lig_predictions SET reward={p} WHERE fixture_id={p} AND user_id={p}",
                           (reward, fixture_id, uid))
                winners.append((uid, pg1, pg2, reward))
        conn.commit()
        return winners

def get_predictions_for_fixture(fixture_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT p.user_id, p.pred_g1, p.pred_g2, u.username
            FROM lig_predictions p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.fixture_id={p}
        """, (fixture_id,))
        return fetchall(cur)


def is_team_in_active_fixtures(user_id: int) -> bool:
    """Kullanıcı aktif sezon fikstüründe var mı?"""
    p = ph()
    season = get_active_season()
    if not season: return False
    season_no = season[0]
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT 1 FROM lig_fixtures
            WHERE season_no={p} AND (team1_id={p} OR team2_id={p})
            LIMIT 1
        """, (season_no, user_id, user_id))
        return fetchone(cur) is not None


# ─────────────────────────────────────────────────────────────
# ANTRENMAN + SÖZLEŞME + LİG HABERLERİ
# ─────────────────────────────────────────────────────────────

def init_extra_tables():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Antrenman tablosu
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_training (
            user_id     BIGINT,
            train_date  TEXT,
            count       INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, train_date)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_training (
            user_id     INTEGER,
            train_date  TEXT,
            count       INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, train_date)
        )""")
        # Akademi (genç oyuncu) tablosu — günlük yenilenir
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_academy (
            id          SERIAL PRIMARY KEY,
            generated   TEXT,
            player_name TEXT,
            rating      INTEGER,
            pos         TEXT,
            price       BIGINT,
            sold        INTEGER DEFAULT 0
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_academy (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            generated   TEXT,
            player_name TEXT,
            rating      INTEGER,
            pos         TEXT,
            price       INTEGER,
            sold        INTEGER DEFAULT 0
        )""")
        # Sözleşme — oyuncu bir takımda kaç maç oynadı
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_contracts (
            user_id        BIGINT,
            player_name    TEXT,
            matches_played INTEGER DEFAULT 0,
            wants_leave    INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, player_name)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_contracts (
            user_id        INTEGER,
            player_name    TEXT,
            matches_played INTEGER DEFAULT 0,
            wants_leave    INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, player_name)
        )""")
        # Lig haberleri arşivi
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_news (
            id         SERIAL PRIMARY KEY,
            news_date  TEXT,
            content    TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_news (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            news_date  TEXT,
            content    TEXT
        )""")
        conn.commit()

DAILY_TRAINING_LIMIT = 3

def get_training_count_today(user_id: int) -> int:
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT count FROM lig_training WHERE user_id={p} AND train_date={p}", (user_id, today))
        row = fetchone(cur)
        return row[0] if row else 0

def increment_training_count(user_id: int):
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT count FROM lig_training WHERE user_id={p} AND train_date={p}", (user_id, today))
        row = fetchone(cur)
        if row:
            cur.execute(f"UPDATE lig_training SET count=count+1 WHERE user_id={p} AND train_date={p}",
                       (user_id, today))
        else:
            cur.execute(f"INSERT INTO lig_training (user_id, train_date, count) VALUES ({p},{p},1)",
                       (user_id, today))
        conn.commit()

def train_player(user_id: int, player_name: str):
    """
    Oyuncuyu antrene et.
    - Genç (rating < 75): %75 gelişim, %3 sakatlık
    - Orta (75-84): %50 gelişim, %5 sakatlık
    - Yıldız (85-92): %30 gelişim, %7 sakatlık
    - Süper yıldız (93+): %15 gelişim, %10 sakatlık (zaten tepe)
    - Rating 99'da: MAX (gelişim olmaz)
    """
    import random as _r
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT rating, base_rating FROM lig_squad WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        row = fetchone(cur)
        if not row: return None, None
        rating, base_rating = row
        if not base_rating or base_rating == 0:
            base_rating = rating

        # Rating'e göre gelişim ve sakatlık şansı belirle
        if rating < 75:
            improve_chance = 0.75   # %75 gelişim
            injury_chance = 0.03    # %3 sakatlık
        elif rating < 85:
            improve_chance = 0.50   # %50
            injury_chance = 0.05    # %5
        elif rating < 93:
            improve_chance = 0.30   # %30
            injury_chance = 0.07    # %7
        else:
            improve_chance = 0.15   # %15
            injury_chance = 0.10    # %10

        # MAX kontrolü — 99'da artık gelişmez
        if rating >= 99:
            conn.commit()
            return "max", 99

        # Sakatlık riski
        if _r.random() < injury_chance:
            matches = _r.randint(2, 3)
            cur.execute(f"UPDATE lig_squad SET injury_matches={p} WHERE user_id={p} AND player_name={p}",
                       (matches, user_id, player_name))
            conn.commit()
            return "injury", matches

        # Gelişim
        if _r.random() < improve_chance:
            new_rating = min(99, rating + 1)
            new_base = min(99, base_rating + 1)
            cur.execute(f"UPDATE lig_squad SET rating={p}, base_rating={p} WHERE user_id={p} AND player_name={p}",
                       (new_rating, new_base, user_id, player_name))
            conn.commit()
            # 99'a ulaştıysa özel dön
            if new_rating >= 99:
                return "max_reached", new_rating
            return "improved", new_rating

        conn.commit()
        return "no_change", rating

# ── Akademi ──
def refresh_academy_if_needed():
    """Akademiyi günlük yenile."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM lig_academy WHERE generated={p} AND sold=0", (today,))
        row = fetchone(cur)
        if row and row[0] > 0:
            return  # Bugün var
        # Yeni 8 genç oyuncu üret
        import lig as _lig
        for _ in range(8):
            yp = _lig.generate_youth_player()
            price = _lig.get_youth_price(yp["rating"])
            cur.execute(f"""
                INSERT INTO lig_academy (generated, player_name, rating, pos, price, sold)
                VALUES ({p},{p},{p},{p},{p},0)
            """, (today, yp["name"], yp["rating"], yp["pos"], price))
        conn.commit()

def get_academy_players():
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    refresh_academy_if_needed()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT id, player_name, rating, pos, price FROM lig_academy WHERE generated={p} AND sold=0 ORDER BY rating DESC", (today,))
        return fetchall(cur)

def buy_youth_player(academy_id: int, user_id: int):
    """Akademi oyuncusunu satın al."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT player_name, rating, pos, price, sold FROM lig_academy WHERE id={p}", (academy_id,))
        row = fetchone(cur)
        if not row or row[4]: return None
        name, rating, pos, price, _ = row
        # Sold işaretle
        cur.execute(f"UPDATE lig_academy SET sold=1 WHERE id={p}", (academy_id,))
        conn.commit()
        return name, rating, pos, price

# ── Sözleşme ──
def increment_match_played(user_id: int, player_name: str):
    """Oyuncunun oynadığı maç sayısını artır."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT matches_played FROM lig_contracts WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        row = fetchone(cur)
        if row:
            cur.execute(f"UPDATE lig_contracts SET matches_played=matches_played+1 WHERE user_id={p} AND player_name={p}",
                       (user_id, player_name))
        else:
            cur.execute(f"INSERT INTO lig_contracts (user_id, player_name, matches_played) VALUES ({p},{p},1)",
                       (user_id, player_name))
        conn.commit()

def check_contract_demands():
    """20+ maç oynayan ve düşük formdaki oyuncular ayrılmak ister."""
    import random as _r
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.user_id, c.player_name, c.matches_played, s.form
            FROM lig_contracts c
            LEFT JOIN lig_squad s ON c.user_id=s.user_id AND c.player_name=s.player_name
            WHERE c.matches_played >= 20 AND c.wants_leave=0
        """)
        candidates = fetchall(cur)
        wants_leave = []
        for uid, pname, matches, form in candidates:
            # Form düşükse veya çok uzun süredir oynuyorsa %20 ihtimal
            chance = 0.1
            if form is not None and form < -2: chance = 0.3
            if matches > 40: chance = 0.4
            if _r.random() < chance:
                cur.execute(f"UPDATE lig_contracts SET wants_leave=1 WHERE user_id={p} AND player_name={p}",
                           (uid, pname))
                wants_leave.append((uid, pname))
        conn.commit()
        return wants_leave

def get_unhappy_players(user_id: int):
    """Ayrılmak isteyen oyuncuları getir."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT player_name FROM lig_contracts WHERE user_id={p} AND wants_leave=1", (user_id,))
        return [r[0] for r in fetchall(cur)]

# ── Lig Haberleri ──
def save_news(content: str):
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"INSERT INTO lig_news (news_date, content) VALUES ({p},{p})",
                   (datetime.now().isoformat(), content))
        conn.commit()

def get_recent_news(limit: int = 10):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT news_date, content FROM lig_news ORDER BY id DESC LIMIT {p}", (limit,))
        return fetchall(cur)


# ─────────────────────────────────────────────────────────────
# CASHBACK SİSTEMİ (Haftalık kayıp iadesi)
# ─────────────────────────────────────────────────────────────

def init_cashback_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS weekly_losses (
            user_id    BIGINT PRIMARY KEY,
            net_loss   BIGINT DEFAULT 0,
            week_start TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS weekly_losses (
            user_id    INTEGER PRIMARY KEY,
            net_loss   INTEGER DEFAULT 0,
            week_start TEXT
        )""")
        conn.commit()

def track_weekly_loss(user_id: int, won: int, lost: int):
    """Haftalık kazanç/kayıp takibi."""
    from datetime import datetime, timedelta
    p = ph()
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.strftime("%Y-%m-%d")
    net_change = lost - won  # pozitifse kayıp

    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO weekly_losses (user_id, net_loss, week_start)
                VALUES ({p},{p},{p})
                ON CONFLICT (user_id) DO UPDATE
                SET net_loss = CASE
                    WHEN weekly_losses.week_start = EXCLUDED.week_start
                    THEN weekly_losses.net_loss + EXCLUDED.net_loss
                    ELSE EXCLUDED.net_loss
                END,
                week_start = EXCLUDED.week_start
            """, (user_id, net_change, week_start))
        else:
            cur.execute(f"SELECT net_loss, week_start FROM weekly_losses WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            if row:
                if row[1] == week_start:
                    cur.execute(f"UPDATE weekly_losses SET net_loss=net_loss+{p} WHERE user_id={p}",
                               (net_change, user_id))
                else:
                    cur.execute(f"UPDATE weekly_losses SET net_loss={p}, week_start={p} WHERE user_id={p}",
                               (net_change, week_start, user_id))
            else:
                cur.execute(f"INSERT INTO weekly_losses (user_id, net_loss, week_start) VALUES ({p},{p},{p})",
                           (user_id, net_change, week_start))
        conn.commit()

def process_weekly_cashback():
    """Pazartesi geçen haftanın kayıplarına %5 cashback ver."""
    from datetime import datetime, timedelta
    p = ph()
    today = datetime.now()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_week = last_monday.strftime("%Y-%m-%d")

    cashbacks = []
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id, net_loss FROM weekly_losses WHERE week_start={p} AND net_loss>0", (last_week,))
        rows = fetchall(cur)
        for uid, loss in rows:
            cashback = int(loss * 0.05)
            if cashback >= 100:  # Min 100 coin
                cur.execute(f"UPDATE users SET balance=balance+{p} WHERE user_id={p}", (cashback, uid))
                cashbacks.append((uid, loss, cashback))
        conn.commit()
    return cashbacks

def get_weekly_loss(user_id: int) -> int:
    """Bu haftaki net kayıp."""
    from datetime import datetime, timedelta
    p = ph()
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    week_start = monday.strftime("%Y-%m-%d")
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT net_loss FROM weekly_losses WHERE user_id={p} AND week_start={p}", (user_id, week_start))
        row = fetchone(cur)
        return row[0] if row else 0


# ─────────────────────────────────────────────────────────────
# TAKTİK SİSTEMİ — Diziliş + Taktik (günlük değişir)
# ─────────────────────────────────────────────────────────────

def _add_tactic_columns():
    """lig_teams'e taktik kolonları ekle."""
    for col_sql in [
        "ALTER TABLE lig_teams ADD COLUMN current_tactic TEXT DEFAULT 'dengeli'",
        "ALTER TABLE lig_teams ADD COLUMN tactic_set_date TEXT",
    ]:
        try:
            with connect() as conn:
                if USE_PG and DATABASE_URL:
                    conn.autocommit = True
                cur = conn.cursor()
                cur.execute(col_sql)
                if not (USE_PG and DATABASE_URL):
                    conn.commit()
        except Exception:
            pass

_tactic_cols_added = False

def get_team_tactics(user_id: int):
    """(formation, tactic) çiftini döndür."""
    global _tactic_cols_added
    if not _tactic_cols_added:
        _add_tactic_columns()
        _tactic_cols_added = True
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT formation, current_tactic FROM lig_teams WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            if row:
                return row[0] or "4-3-3", row[1] or "dengeli"
        except Exception:
            pass
        return "4-3-3", "dengeli"

def set_team_tactics(user_id: int, formation: str = None, tactic: str = None) -> bool:
    """Diziliş ve/veya taktik ayarla. Günde 1 kez."""
    global _tactic_cols_added
    if not _tactic_cols_added:
        _add_tactic_columns()
        _tactic_cols_added = True
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Bugün değiştirdi mi?
        try:
            cur.execute(f"SELECT tactic_set_date FROM lig_teams WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            if row and row[0] and row[0][:10] == today:
                return False  # Bugün zaten değişti
        except: pass

        updates = []
        params = []
        if formation:
            updates.append(f"formation={p}")
            params.append(formation)
        if tactic:
            updates.append(f"current_tactic={p}")
            params.append(tactic)
        updates.append(f"tactic_set_date={p}")
        params.append(datetime.now().isoformat())
        params.append(user_id)
        cur.execute(f"UPDATE lig_teams SET {', '.join(updates)} WHERE user_id={p}", params)
        conn.commit()
        return True

def can_change_tactics_today(user_id: int) -> bool:
    """Bugün taktik değiştirildi mi?"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT tactic_set_date FROM lig_teams WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            if row and row[0] and row[0][:10] == today:
                return False
        except: pass
        return True


# ─────────────────────────────────────────────────────────────
# COIN BANK + LİG KADEMELERİ (1, 2, 3, Süper Lig)
# ─────────────────────────────────────────────────────────────

LEAGUE_TIERS = {
    1: {"name": "🥉 1. Lig",            "promote": 3, "relegate": 0},
    2: {"name": "🥈 2. Lig",            "promote": 3, "relegate": 3},
    3: {"name": "🥇 3. Lig",            "promote": 3, "relegate": 3},
    4: {"name": "🏆 Türk Budun Süper Ligi", "promote": 0, "relegate": 3},
}

def init_bank_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS coin_bank (
            id      INTEGER PRIMARY KEY,
            total   BIGINT DEFAULT 0,
            last_op TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS coin_bank (
            id      INTEGER PRIMARY KEY,
            total   INTEGER DEFAULT 0,
            last_op TEXT
        )""")
        # İlk kayıt
        cur.execute("SELECT 1 FROM coin_bank WHERE id=1")
        if not fetchone(cur):
            cur.execute("INSERT INTO coin_bank (id, total, last_op) VALUES (1, 0, '')")
        # Takımlara tier kolonu ekle
        try:
            cur.execute("ALTER TABLE lig_teams ADD COLUMN league_tier INTEGER DEFAULT 1")
        except Exception:
            pass
        conn.commit()

def add_to_bank(amount: int):
    """Coin Bank'a coin ekle. Tablo yoksa oluştur."""
    from datetime import datetime
    p = ph()
    if amount <= 0: return
    # Tablo garantisi
    try:
        with connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM coin_bank WHERE id=1 LIMIT 1")
            if not fetchone(cur):
                cur.execute("INSERT INTO coin_bank (id, total, last_op) VALUES (1, 0, '')")
                conn.commit()
    except Exception:
        # Tablo yoksa oluştur
        init_bank_table()
    # Asıl ekleme
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE coin_bank SET total=total+{p}, last_op={p} WHERE id=1",
                   (amount, datetime.now().isoformat()))
        affected = cur.rowcount
        if affected == 0:
            # İlk kayıt yoksa
            cur.execute(f"INSERT INTO coin_bank (id, total, last_op) VALUES (1,{p},{p})",
                       (amount, datetime.now().isoformat()))
        conn.commit()

def get_bank_total() -> int:
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT total FROM coin_bank WHERE id=1")
        row = fetchone(cur)
        return row[0] if row else 0

def withdraw_from_bank(amount: int) -> bool:
    """Admin: Bank'tan çek."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT total FROM coin_bank WHERE id=1")
        row = fetchone(cur)
        if not row or row[0] < amount:
            return False
        cur.execute(f"UPDATE coin_bank SET total=total-{p} WHERE id=1", (amount,))
        conn.commit()
        return True

# ── Lig Kademeleri ──

def _add_tier_column():
    """lig_teams'e league_tier ekle."""
    try:
        with connect() as conn:
            if USE_PG and DATABASE_URL:
                conn.autocommit = True
            cur = conn.cursor()
            cur.execute("ALTER TABLE lig_teams ADD COLUMN league_tier INTEGER DEFAULT 1")
            if not (USE_PG and DATABASE_URL):
                conn.commit()
    except Exception:
        pass

_tier_col_added = False

def get_team_tier(user_id: int) -> int:
    global _tier_col_added
    if not _tier_col_added:
        _add_tier_column()
        _tier_col_added = True
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT league_tier FROM lig_teams WHERE user_id={p}", (user_id,))
            row = fetchone(cur)
            return row[0] if row and row[0] else 1
        except:
            return 1

def set_team_tier(user_id: int, tier: int):
    global _tier_col_added
    if not _tier_col_added:
        _add_tier_column()
        _tier_col_added = True
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_teams SET league_tier={p} WHERE user_id={p}", (tier, user_id))
        conn.commit()

def get_teams_by_tier(tier: int):
    """Belirli ligin sıralaması."""
    global _tier_col_added
    if not _tier_col_added:
        _add_tier_column()
        _tier_col_added = True
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"""
                SELECT user_id, team_name, wins, draws, losses, goals_for, goals_against,
                       (wins*3 + draws) AS points
                FROM lig_teams
                WHERE league_tier={p}
                ORDER BY points DESC, (goals_for - goals_against) DESC, goals_for DESC
            """, (tier,))
            return fetchall(cur)
        except:
            # Tier kolonu yoksa hepsini 1. lig sayar
            cur.execute("""
                SELECT user_id, team_name, wins, draws, losses, goals_for, goals_against,
                       (wins*3 + draws) AS points
                FROM lig_teams
                ORDER BY points DESC, (goals_for - goals_against) DESC, goals_for DESC
            """)
            return fetchall(cur)

def get_all_tiers_summary():
    """Tüm liglerin top 5'ini döndür."""
    summary = {}
    for tier in [4, 3, 2, 1]:  # En üstten en alta
        teams = get_teams_by_tier(tier)
        summary[tier] = teams[:5]
    return summary

def promote_relegate_teams():
    """Sezon sonu terfi/düşme işlemleri."""
    actions = []  # [(uid, name, from_tier, to_tier, reason), ...]
    for tier in [1, 2, 3]:  # Süper lig haricindeki ligler
        teams = get_teams_by_tier(tier)
        if len(teams) < 4: continue

        # Top 3 → bir üst lig
        for t in teams[:3]:
            uid, name = t[0], t[1]
            set_team_tier(uid, tier + 1)
            actions.append((uid, name, tier, tier + 1, "promote"))

    for tier in [2, 3, 4]:  # Alt ligler hariç
        teams = get_teams_by_tier(tier)
        if len(teams) < 4: continue

        # Son 3 → bir alt lige (eğer promote olmadıysa)
        promoted_uids = {a[0] for a in actions if a[3] == tier and a[1] != ""}
        bottom3 = [t for t in teams[-3:] if t[0] not in promoted_uids]
        for t in bottom3:
            uid, name = t[0], t[1]
            set_team_tier(uid, tier - 1)
            actions.append((uid, name, tier, tier - 1, "relegate"))

    return actions

# ── Bank'tan LC ödülü dönüşümü ──

def bank_to_season_pool(amount_coins: int, rate: int = 10) -> int:
    """Bank'tan coin çek, LC olarak döndür. rate: 1 LC = X coin"""
    if not withdraw_from_bank(amount_coins):
        return 0
    return amount_coins // rate


# ─────────────────────────────────────────────────────────────
# YAYIN AYARLARI (kalıcı)
# ─────────────────────────────────────────────────────────────

def init_broadcast_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS broadcast_settings (
            chat_id     BIGINT,
            category    TEXT,
            thread_id   INTEGER,
            PRIMARY KEY(chat_id, category)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS broadcast_settings (
            chat_id     INTEGER,
            category    TEXT,
            thread_id   INTEGER,
            PRIMARY KEY(chat_id, category)
        )""")
        conn.commit()

def save_broadcast_setting(chat_id: int, category: str, thread_id: int = None):
    """Yayın ayarını kalıcı kaydet."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO broadcast_settings (chat_id, category, thread_id)
                VALUES ({p},{p},{p})
                ON CONFLICT (chat_id, category) DO UPDATE SET thread_id=EXCLUDED.thread_id
            """, (chat_id, category, thread_id))
        else:
            cur.execute(f"SELECT 1 FROM broadcast_settings WHERE chat_id={p} AND category={p}",
                       (chat_id, category))
            if fetchone(cur):
                cur.execute(f"UPDATE broadcast_settings SET thread_id={p} WHERE chat_id={p} AND category={p}",
                           (thread_id, chat_id, category))
            else:
                cur.execute(f"INSERT INTO broadcast_settings (chat_id, category, thread_id) VALUES ({p},{p},{p})",
                           (chat_id, category, thread_id))
        conn.commit()

def get_all_broadcast_settings():
    """Tüm yayın ayarlarını döndür: {chat_id: {category: thread_id}}"""
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT chat_id, category, thread_id FROM broadcast_settings")
        rows = fetchall(cur)
        result = {}
        for chat_id, cat, tid in rows:
            if chat_id not in result:
                result[chat_id] = {"lig": None, "casino": None}
            result[chat_id][cat] = tid
        return result

def delete_broadcast_setting(chat_id: int, category: str = None):
    """Yayın ayarını sil."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if category:
            cur.execute(f"DELETE FROM broadcast_settings WHERE chat_id={p} AND category={p}",
                       (chat_id, category))
        else:
            cur.execute(f"DELETE FROM broadcast_settings WHERE chat_id={p}", (chat_id,))
        conn.commit()


# ─────────────────────────────────────────────────────────────
# OYUNCU PAZARI — Teklif, Pazarlık, Kiralama, Açık Pazar
# ─────────────────────────────────────────────────────────────

def init_market_tables():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Direkt teklifler (pazarlık dahil)
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS player_offers (
            id              SERIAL PRIMARY KEY,
            from_user_id    BIGINT,
            to_user_id      BIGINT,
            player_name     TEXT,
            offer_amount    BIGINT,
            status          TEXT DEFAULT 'pending',
            round_no        INTEGER DEFAULT 1,
            created_at      TEXT,
            is_loan         INTEGER DEFAULT 0,
            loan_matches    INTEGER DEFAULT 0
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS player_offers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id    INTEGER,
            to_user_id      INTEGER,
            player_name     TEXT,
            offer_amount    INTEGER,
            status          TEXT DEFAULT 'pending',
            round_no        INTEGER DEFAULT 1,
            created_at      TEXT,
            is_loan         INTEGER DEFAULT 0,
            loan_matches    INTEGER DEFAULT 0
        )""")
        # Açık pazar ilanları
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS market_listings (
            id              SERIAL PRIMARY KEY,
            seller_user_id  BIGINT,
            player_name     TEXT,
            rating          INTEGER,
            pos             TEXT,
            price           BIGINT,
            listed_at       TEXT,
            sold            INTEGER DEFAULT 0
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS market_listings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_user_id  INTEGER,
            player_name     TEXT,
            rating          INTEGER,
            pos             TEXT,
            price           INTEGER,
            listed_at       TEXT,
            sold            INTEGER DEFAULT 0
        )""")
        # Kiralık takip
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS player_loans (
            id              SERIAL PRIMARY KEY,
            owner_id        BIGINT,
            renter_id       BIGINT,
            player_name     TEXT,
            matches_left    INTEGER,
            started_at      TEXT,
            active          INTEGER DEFAULT 1
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS player_loans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id        INTEGER,
            renter_id       INTEGER,
            player_name     TEXT,
            matches_left    INTEGER,
            started_at      TEXT,
            active          INTEGER DEFAULT 1
        )""")
        conn.commit()

# ── Direkt Teklif ──

def create_offer(from_uid, to_uid, player, amount, is_loan=False, loan_matches=0):
    """Yeni teklif oluştur."""
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO player_offers (from_user_id, to_user_id, player_name, offer_amount, status, round_no, created_at, is_loan, loan_matches)
                VALUES ({p},{p},{p},{p},'pending',1,{p},{p},{p}) RETURNING id
            """, (from_uid, to_uid, player, amount, datetime.now().isoformat(),
                  1 if is_loan else 0, loan_matches))
            row = cur.fetchone()
            conn.commit()
            return row[0]
        else:
            cur.execute(f"""
                INSERT INTO player_offers (from_user_id, to_user_id, player_name, offer_amount, status, round_no, created_at, is_loan, loan_matches)
                VALUES ({p},{p},{p},{p},'pending',1,{p},{p},{p})
            """, (from_uid, to_uid, player, amount, datetime.now().isoformat(),
                  1 if is_loan else 0, loan_matches))
            conn.commit()
            return cur.lastrowid

def get_offer(offer_id):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT id, from_user_id, to_user_id, player_name, offer_amount, status, round_no, is_loan, loan_matches
                        FROM player_offers WHERE id={p}""", (offer_id,))
        return fetchone(cur)

def update_offer_status(offer_id, status):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE player_offers SET status={p} WHERE id={p}", (status, offer_id))
        conn.commit()

def counter_offer(offer_id, new_amount):
    """Karşı teklif: amount güncellenir, round artırılır, taraflar tersine döner."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT from_user_id, to_user_id, round_no FROM player_offers WHERE id={p}
        """, (offer_id,))
        row = fetchone(cur)
        if not row: return False
        from_uid, to_uid, round_no = row
        if round_no >= 3:
            return False  # 3 turdan fazla pazarlık yok
        # Tarafları ters çevir (artık karşı taraf teklif yapıyor)
        cur.execute(f"""
            UPDATE player_offers
            SET offer_amount={p}, round_no={p}, from_user_id={p}, to_user_id={p}
            WHERE id={p}
        """, (new_amount, round_no+1, to_uid, from_uid, offer_id))
        conn.commit()
        return True

# ── Açık Pazar ──

def add_to_market(seller_uid, player_name, rating, pos, price):
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO market_listings (seller_user_id, player_name, rating, pos, price, listed_at)
            VALUES ({p},{p},{p},{p},{p},{p})
        """, (seller_uid, player_name, rating, pos, price, datetime.now().isoformat()))
        conn.commit()

def get_market_listings(limit=30):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT m.id, m.seller_user_id, m.player_name, m.rating, m.pos, m.price, m.listed_at, t.team_name
            FROM market_listings m
            LEFT JOIN lig_teams t ON m.seller_user_id = t.user_id
            WHERE m.sold=0
            ORDER BY m.listed_at DESC LIMIT {p}
        """, (limit,))
        return fetchall(cur)

def buy_from_market(listing_id, buyer_uid):
    """Pazardan al."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT seller_user_id, player_name, rating, pos, price, sold FROM market_listings WHERE id={p}", (listing_id,))
        row = fetchone(cur)
        if not row or row[5]: return None  # Satıldı veya yok
        seller_uid, pname, rating, pos, price, _ = row
        if seller_uid == buyer_uid: return "own"
        cur.execute(f"UPDATE market_listings SET sold=1 WHERE id={p}", (listing_id,))
        conn.commit()
        return seller_uid, pname, rating, pos, price

def cleanup_old_market(days=7):
    """7 gün dolanları iptal et."""
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE market_listings SET sold=1 WHERE sold=0 AND listed_at<{p}", (cutoff,))
        conn.commit()

# ── Kiralama ──

def create_loan(owner_id, renter_id, player_name, matches=4):
    """Kiralık başlat."""
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO player_loans (owner_id, renter_id, player_name, matches_left, started_at, active)
            VALUES ({p},{p},{p},{p},{p},1)
        """, (owner_id, renter_id, player_name, matches, datetime.now().isoformat()))
        conn.commit()

def get_active_loan(player_name, owner_id):
    """Bu oyuncunun aktif kiralık durumu var mı?"""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT id, renter_id, matches_left FROM player_loans
            WHERE player_name={p} AND owner_id={p} AND active=1
        """, (player_name, owner_id))
        return fetchone(cur)

def decrement_loans():
    """Maç sonu kiralık sayıyı 1 azalt, biten kiralıkları döndür."""
    p = ph()
    expired = []
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, owner_id, renter_id, player_name, matches_left FROM player_loans WHERE active=1")
        loans = fetchall(cur)
        for lid, owner_id, renter_id, pname, left in loans:
            new_left = left - 1
            if new_left <= 0:
                cur.execute(f"UPDATE player_loans SET active=0, matches_left=0 WHERE id={p}", (lid,))
                expired.append((owner_id, renter_id, pname))
            else:
                cur.execute(f"UPDATE player_loans SET matches_left={p} WHERE id={p}", (new_left, lid))
        conn.commit()
    return expired

def is_player_loaned(player_name, owner_id):
    """Oyuncu şu an kiralık mı?"""
    return get_active_loan(player_name, owner_id) is not None

def get_user_loans_in(user_id):
    """Kullanıcının kiralık aldığı oyuncuları döndür."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT player_name, matches_left FROM player_loans
            WHERE renter_id={p} AND active=1
        """, (user_id,))
        return fetchall(cur)

def transfer_player(from_uid, to_uid, player_name):
    """Oyuncuyu bir takımdan diğerine taşı."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_squad SET user_id={p} WHERE user_id={p} AND player_name={p}",
                   (to_uid, from_uid, player_name))
        conn.commit()


# ─────────────────────────────────────────────────────────────
# KULLANICI SİLME (admin)
# ─────────────────────────────────────────────────────────────

def delete_lig_data(user_id: int) -> dict:
    """Kullanıcının SADECE lig verilerini sil."""
    p = ph()
    deleted = {"squad": 0, "team": 0, "fixtures": 0, "predictions": 0,
               "offers": 0, "listings": 0, "loans": 0, "season_stats": 0,
               "conversion": 0, "training": 0, "contracts": 0, "lc_codes": 0,
               "tactic_log": 0}
    with connect() as conn:
        cur = conn.cursor()
        # Kadro
        cur.execute(f"DELETE FROM lig_squad WHERE user_id={p}", (user_id,))
        deleted["squad"] = cur.rowcount
        # Takım
        cur.execute(f"DELETE FROM lig_teams WHERE user_id={p}", (user_id,))
        deleted["team"] = cur.rowcount
        # Fikstür (hem team1 hem team2)
        try:
            cur.execute(f"DELETE FROM lig_fixtures WHERE team1_id={p} OR team2_id={p}", (user_id, user_id))
            deleted["fixtures"] = cur.rowcount
        except: pass
        # Tahminler
        try:
            cur.execute(f"DELETE FROM lig_predictions WHERE user_id={p}", (user_id,))
            deleted["predictions"] = cur.rowcount
        except: pass
        # Teklifler
        try:
            cur.execute(f"DELETE FROM player_offers WHERE from_user_id={p} OR to_user_id={p}",
                       (user_id, user_id))
            deleted["offers"] = cur.rowcount
        except: pass
        # Pazar ilanları
        try:
            cur.execute(f"DELETE FROM market_listings WHERE seller_user_id={p}", (user_id,))
            deleted["listings"] = cur.rowcount
        except: pass
        # Kiralık
        try:
            cur.execute(f"DELETE FROM player_loans WHERE owner_id={p} OR renter_id={p}",
                       (user_id, user_id))
            deleted["loans"] = cur.rowcount
        except: pass
        # Sezon istatistikleri
        try:
            cur.execute(f"DELETE FROM lig_season_stats WHERE user_id={p}", (user_id,))
            deleted["season_stats"] = cur.rowcount
        except: pass
        # Dönüşüm geçmişi
        try:
            cur.execute(f"DELETE FROM lig_conversion WHERE user_id={p}", (user_id,))
            deleted["conversion"] = cur.rowcount
        except: pass
        # Antrenman
        try:
            cur.execute(f"DELETE FROM lig_training WHERE user_id={p}", (user_id,))
            deleted["training"] = cur.rowcount
        except: pass
        # Sözleşmeler
        try:
            cur.execute(f"DELETE FROM lig_contracts WHERE user_id={p}", (user_id,))
            deleted["contracts"] = cur.rowcount
        except: pass
        # LC kodu geçmişi
        try:
            cur.execute(f"DELETE FROM lc_used_codes WHERE user_id={p}", (user_id,))
            deleted["lc_codes"] = cur.rowcount
        except: pass
        # MVP geçmişi
        try:
            cur.execute(f"DELETE FROM lig_mvp_history WHERE user_id={p}", (user_id,))
        except: pass
        # Maçlar (team1 veya team2)
        try:
            cur.execute(f"DELETE FROM lig_matches WHERE team1_id={p} OR team2_id={p}",
                       (user_id, user_id))
        except: pass
        # Şampiyon geçmişi
        try:
            cur.execute(f"DELETE FROM lig_champions WHERE user_id={p}", (user_id,))
        except: pass
        conn.commit()
    return deleted

def delete_full_user(user_id: int) -> dict:
    """Kullanıcının TÜM verilerini sil — casino + lig."""
    p = ph()
    deleted = {}
    # Önce lig
    lig_del = delete_lig_data(user_id)
    deleted.update(lig_del)

    with connect() as conn:
        cur = conn.cursor()
        # Casino
        cur.execute(f"DELETE FROM users WHERE user_id={p}", (user_id,))
        deleted["user"] = cur.rowcount
        try:
            cur.execute(f"DELETE FROM user_tasks WHERE user_id={p}", (user_id,))
            deleted["tasks"] = cur.rowcount
        except: pass
        try:
            cur.execute(f"DELETE FROM used_codes WHERE user_id={p}", (user_id,))
            deleted["used_codes"] = cur.rowcount
        except: pass
        try:
            cur.execute(f"DELETE FROM weekly_xp WHERE user_id={p}", (user_id,))
            deleted["weekly_xp"] = cur.rowcount
        except: pass
        try:
            cur.execute(f"DELETE FROM weekly_losses WHERE user_id={p}", (user_id,))
            deleted["weekly_losses"] = cur.rowcount
        except: pass
        try:
            cur.execute(f"DELETE FROM loto_tickets WHERE user_id={p}", (user_id,))
            deleted["loto_tickets"] = cur.rowcount
        except: pass
        conn.commit()
    return deleted


# ─────────────────────────────────────────────────────────────
# ANTRENÖR + SOSYAL MEDYA + GLOBAL OYUNCU TAKİP
# ─────────────────────────────────────────────────────────────

def init_extras2_tables():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Antrenörler
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS lig_coaches (
            id          SERIAL PRIMARY KEY,
            owner_id    BIGINT,
            coach_name  TEXT,
            rating      INTEGER,
            bonus_atk   INTEGER,
            bonus_def   INTEGER,
            cost        BIGINT,
            hired_at    TEXT,
            active      INTEGER DEFAULT 1
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS lig_coaches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id    INTEGER,
            coach_name  TEXT,
            rating      INTEGER,
            bonus_atk   INTEGER,
            bonus_def   INTEGER,
            cost        BIGINT,
            hired_at    TEXT,
            active      INTEGER DEFAULT 1
        )""")
        # Pazar bot antrenörler (günlük yenilenir)
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS coach_market (
            id          SERIAL PRIMARY KEY,
            generated   TEXT,
            name        TEXT,
            rating      INTEGER,
            bonus_atk   INTEGER,
            bonus_def   INTEGER,
            cost        BIGINT,
            sold        INTEGER DEFAULT 0
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS coach_market (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            generated   TEXT,
            name        TEXT,
            rating      INTEGER,
            bonus_atk   INTEGER,
            bonus_def   INTEGER,
            cost        INTEGER,
            sold        INTEGER DEFAULT 0
        )""")
        # Sosyal medya tepkileri (gruba haber olarak yansır)
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS social_reactions (
            id          SERIAL PRIMARY KEY,
            posted_at   TEXT,
            content     TEXT,
            tone        TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS social_reactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            posted_at   TEXT,
            content     TEXT,
            tone        TEXT
        )""")
        conn.commit()

# ── Antrenör Market ──

import random as _r_extras

COACH_NAMES = [
    "Pep Guardiola", "Jürgen Klopp", "Carlo Ancelotti", "José Mourinho",
    "Diego Simeone", "Antonio Conte", "Thomas Tuchel", "Hansi Flick",
    "Mauricio Pochettino", "Erik ten Hag", "Xavi Hernández", "Mikel Arteta",
    "Massimiliano Allegri", "Stefano Pioli", "Luciano Spalletti", "Roberto Mancini",
    "Fatih Terim", "Şenol Güneş", "Abdullah Avcı", "Aykut Kocaman",
    "İsmail Kartal", "Vincenzo Montella", "Okan Buruk", "Sergen Yalçın",
]

def generate_coach():
    """Rastgele antrenör üret (rating ve fiyat orantılı)."""
    name = _r_extras.choice(COACH_NAMES)
    rating = _r_extras.randint(75, 95)
    # Rating'e göre bonus
    bonus_atk = (rating - 70) // 3
    bonus_def = (rating - 70) // 3
    # Fiyat (oyuncu fiyatlarına benzer)
    if rating >= 92:   cost = 250_000
    elif rating >= 88: cost = 150_000
    elif rating >= 85: cost = 80_000
    elif rating >= 80: cost = 40_000
    else:              cost = 15_000
    return {"name": name, "rating": rating, "bonus_atk": bonus_atk,
            "bonus_def": bonus_def, "cost": cost}

def refresh_coach_market_if_needed():
    """Antrenör marketi günlük yenile."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM coach_market WHERE generated={p} AND sold=0", (today,))
        row = fetchone(cur)
        if row and row[0] > 0: return
        # 5 yeni antrenör
        used_names = set()
        for _ in range(5):
            tries = 0
            coach = generate_coach()
            while coach["name"] in used_names and tries < 10:
                coach = generate_coach()
                tries += 1
            used_names.add(coach["name"])
            cur.execute(f"""
                INSERT INTO coach_market (generated, name, rating, bonus_atk, bonus_def, cost, sold)
                VALUES ({p},{p},{p},{p},{p},{p},0)
            """, (today, coach["name"], coach["rating"], coach["bonus_atk"],
                  coach["bonus_def"], coach["cost"]))
        conn.commit()

def get_coach_market():
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    refresh_coach_market_if_needed()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT id, name, rating, bonus_atk, bonus_def, cost
                        FROM coach_market WHERE generated={p} AND sold=0
                        ORDER BY rating DESC""", (today,))
        return fetchall(cur)

def hire_coach(market_id: int, user_id: int):
    """Antrenör tut. Kullanıcının zaten varsa hata."""
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Mevcut antrenör?
        cur.execute(f"SELECT 1 FROM lig_coaches WHERE owner_id={p} AND active=1", (user_id,))
        if fetchone(cur):
            return "has_coach"
        cur.execute(f"SELECT name, rating, bonus_atk, bonus_def, cost, sold FROM coach_market WHERE id={p}",
                   (market_id,))
        row = fetchone(cur)
        if not row or row[5]:
            return None
        name, rating, batk, bdef, cost, _ = row
        cur.execute(f"UPDATE coach_market SET sold=1 WHERE id={p}", (market_id,))
        cur.execute(f"""
            INSERT INTO lig_coaches (owner_id, coach_name, rating, bonus_atk, bonus_def, cost, hired_at, active)
            VALUES ({p},{p},{p},{p},{p},{p},{p},1)
        """, (user_id, name, rating, batk, bdef, cost, datetime.now().isoformat()))
        conn.commit()
        return name, rating, batk, bdef, cost

def get_user_coach(user_id: int):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT coach_name, rating, bonus_atk, bonus_def, hired_at
                        FROM lig_coaches WHERE owner_id={p} AND active=1""", (user_id,))
        return fetchone(cur)

def release_coach(user_id: int):
    """Antrenörü bırak (sezon sonu otomatik)."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_coaches SET active=0 WHERE owner_id={p}", (user_id,))
        conn.commit()

def release_all_coaches():
    """Sezon sonu tüm antrenörleri serbest bırak."""
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE lig_coaches SET active=0")
        conn.commit()

# ── Sosyal Medya ──

SOCIAL_TEMPLATES = {
    "positive": [
        "🐦 _Twitter:_ \"#{player} bu maçta sınıfta kaldı!\" diyenlere cevap geldi sahada! 🔥",
        "💬 _Forum:_ \"{team} taraftarları yıldızlarına aşık oldu, {player} muhteşem!\"",
        "📺 _Yorumcu:_ \"{player}'in performansı paha biçilemez, {team} için altın!\"",
        "📰 _Manşet:_ \"{team}'in tabelası mı yoksa kalbi mi büyük? {player} kazandırdı.\"",
    ],
    "negative": [
        "🐦 _Twitter:_ \"#{player} bugün top oynamamış sanki, {team} taraftarları kızgın 😤\"",
        "💬 _Forum:_ \"{team} alacaklı kalır gibi oynadı, hocayı sorgulayan çok!\"",
        "📺 _Yorumcu:_ \"{player}'in formu düştü, {team} acil teknik değişiklik istiyor.\"",
        "📰 _Manşet:_ \"{team} taraftarı isyan ediyor: '{player} satılsın!'\"",
    ],
    "neutral": [
        "🐦 _Twitter:_ \"{team} bu maça beraberlik geldi, gönlü dolu yarısı kızgın 😶\"",
        "📺 _Yorumcu:_ \"{team} oyununu kuramadı ama yıldızlardan {player} kurtardı.\"",
        "💬 _Forum:_ \"{team} için kayıp puan ama yenilmedik diyoruz, devam!\"",
    ],
}

def post_social_reaction(team_name: str, player_name: str, tone: str = "positive"):
    """Sosyal medya tepkisi üret ve kaydet."""
    from datetime import datetime
    import random as _r
    p = ph()
    templates = SOCIAL_TEMPLATES.get(tone, SOCIAL_TEMPLATES["neutral"])
    content = _r.choice(templates).replace("{team}", team_name).replace("{player}", player_name)
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"INSERT INTO social_reactions (posted_at, content, tone) VALUES ({p},{p},{p})",
                   (datetime.now().isoformat(), content, tone))
        conn.commit()
    return content

def get_recent_social(limit=10):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT posted_at, content FROM social_reactions ORDER BY id DESC LIMIT {p}", (limit,))
        return fetchall(cur)

# ── Global Oyuncu Sahipliği (Top 30) ──
# Top 30 oyuncu adlarını tek sahipli yapıyoruz.

def is_unique_owner_player(player_name: str) -> bool:
    """Bu oyuncu tek sahipli mi? Top 30 listesinden kontrol et."""
    try:
        import lig as _lig
        # Top 30: ratingi en yüksek 30 oyuncu
        sorted_players = sorted(_lig.PLAYERS, key=lambda x: -x["rating"])
        top30 = {p["name"] for p in sorted_players[:30]}
        return player_name in top30
    except:
        return False

def is_player_already_owned(player_name: str) -> int:
    """Bu yıldız oyuncu zaten bir takımda mı? Sahibi varsa user_id döner, yoksa None."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id FROM lig_squad WHERE player_name={p} LIMIT 1", (player_name,))
        row = fetchone(cur)
        return row[0] if row else None


# ─────────────────────────────────────────────────────────────
# TEK SAHİPLİ YILDIZ OYUNCULAR (sonraki sezondan itibaren)
# ─────────────────────────────────────────────────────────────

UNIQUE_OWNERSHIP_START_SEASON = 2  # 2. sezondan itibaren aktif

def is_unique_ownership_active() -> bool:
    """Aktif sezonda tek sahiplik açık mı?"""
    season = get_active_season()
    if not season: return False
    season_no = season[0]
    return season_no >= UNIQUE_OWNERSHIP_START_SEASON

def is_star_player(player_name: str) -> bool:
    """Bu oyuncu yıldız (Top 30 rating 90+) mı?"""
    try:
        import lig as _lig
        # Rating 90+ tüm oyuncular yıldız
        for p in _lig.PLAYERS:
            if p["name"] == player_name and p["rating"] >= 90:
                return True
        return False
    except:
        return False

def is_star_owned(player_name: str) -> int:
    """Bu yıldız oyuncu zaten sahipli mi? Sahip user_id döner, yoksa None."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT user_id FROM lig_squad WHERE player_name={p} LIMIT 1", (player_name,))
        row = fetchone(cur)
        return row[0] if row else None


# ─────────────────────────────────────────────────────────────
# DETAYLI İSTATİSTİKLER (Oyun bazlı)
# ─────────────────────────────────────────────────────────────

def init_game_stats_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS game_stats (
            user_id     BIGINT,
            game_type   TEXT,
            plays       INTEGER DEFAULT 0,
            wins        INTEGER DEFAULT 0,
            total_bet   BIGINT DEFAULT 0,
            total_won   BIGINT DEFAULT 0,
            biggest_win BIGINT DEFAULT 0,
            PRIMARY KEY(user_id, game_type)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS game_stats (
            user_id     INTEGER,
            game_type   TEXT,
            plays       INTEGER DEFAULT 0,
            wins        INTEGER DEFAULT 0,
            total_bet   INTEGER DEFAULT 0,
            total_won   INTEGER DEFAULT 0,
            biggest_win INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, game_type)
        )""")
        conn.commit()

def update_game_stat(user_id: int, game_type: str, bet: int, won: int):
    """Oyun bazlı istatistik güncelle."""
    p = ph()
    is_win = 1 if won > bet else 0
    with connect() as conn:
        cur = conn.cursor()
        if USE_PG and DATABASE_URL:
            cur.execute(f"""
                INSERT INTO game_stats (user_id, game_type, plays, wins, total_bet, total_won, biggest_win)
                VALUES ({p},{p},1,{p},{p},{p},{p})
                ON CONFLICT (user_id, game_type) DO UPDATE SET
                    plays = game_stats.plays + 1,
                    wins = game_stats.wins + EXCLUDED.wins,
                    total_bet = game_stats.total_bet + EXCLUDED.total_bet,
                    total_won = game_stats.total_won + EXCLUDED.total_won,
                    biggest_win = GREATEST(game_stats.biggest_win, EXCLUDED.biggest_win)
            """, (user_id, game_type, is_win, bet, won, won))
        else:
            cur.execute(f"SELECT plays FROM game_stats WHERE user_id={p} AND game_type={p}",
                       (user_id, game_type))
            if fetchone(cur):
                cur.execute(f"""
                    UPDATE game_stats SET plays=plays+1, wins=wins+{p},
                    total_bet=total_bet+{p}, total_won=total_won+{p},
                    biggest_win=MAX(biggest_win,{p})
                    WHERE user_id={p} AND game_type={p}
                """, (is_win, bet, won, won, user_id, game_type))
            else:
                cur.execute(f"""
                    INSERT INTO game_stats (user_id, game_type, plays, wins, total_bet, total_won, biggest_win)
                    VALUES ({p},{p},1,{p},{p},{p},{p})
                """, (user_id, game_type, is_win, bet, won, won))
        conn.commit()

def get_user_game_stats(user_id: int):
    """Kullanıcının tüm oyun istatistikleri."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT game_type, plays, wins, total_bet, total_won, biggest_win
            FROM game_stats WHERE user_id={p} ORDER BY plays DESC
        """, (user_id,))
        return fetchall(cur)

def get_favorite_game(user_id: int):
    """En çok oynanan oyun."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT game_type, plays FROM game_stats
            WHERE user_id={p} ORDER BY plays DESC LIMIT 1
        """, (user_id,))
        return fetchone(cur)


# ─────────────────────────────────────────────────────────────
# HAFTALIK GÖREVLER (Pazartesi - Pazar, zor)
# ─────────────────────────────────────────────────────────────

def init_weekly_tasks_table():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS weekly_tasks (
            user_id      BIGINT,
            task_name    TEXT,
            target       BIGINT,
            current      BIGINT DEFAULT 0,
            is_completed INTEGER DEFAULT 0,
            week_start   TEXT,
            task_type    TEXT,
            reward       BIGINT,
            PRIMARY KEY(user_id, task_name, week_start)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS weekly_tasks (
            user_id      INTEGER,
            task_name    TEXT,
            target       INTEGER,
            current      INTEGER DEFAULT 0,
            is_completed INTEGER DEFAULT 0,
            week_start   TEXT,
            task_type    TEXT,
            reward       INTEGER,
            PRIMARY KEY(user_id, task_name, week_start)
        )""")
        conn.commit()

def get_weekly_tasks(user_id: int):
    """
    Haftalık görevleri al, yoksa oluştur.
    - Her hafta farklı görevler (hafta no × kullanıcı ID seed'i)
    - Önceki haftayla çakışmasın
    - 3 farklı zorluk seviyesinden 1'er görev
    """
    import random as _r
    from datetime import datetime
    p = ph()
    week_start = _get_week_start()

    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT task_name, target, current, is_completed, reward FROM weekly_tasks
                       WHERE user_id={p} AND week_start={p}""", (user_id, week_start))
        tasks = fetchall(cur)
        if tasks:
            return tasks

        # Hafta bazlı seed — her hafta, her kullanıcı farklı kombinasyon alır
        week_num = datetime.now().isocalendar()[1]  # 1-52 hafta numarası
        year_num = datetime.now().year
        seed = (year_num * 100 + week_num) * 1000 + (user_id % 1000)
        _r.seed(seed)

        # Önceki haftanın görevlerini al (tekrar etmesin)
        from datetime import timedelta
        prev_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        cur.execute(f"""SELECT task_name FROM weekly_tasks
                       WHERE user_id={p} AND week_start={p}""", (user_id, prev_week))
        prev_tasks = {row[0] for row in fetchall(cur)}

        # BÜYÜK HAVUZ — 3 kategori
        havuz_kolay = [
            ("50 Slot Oyna",              50,         "slot",          150_000),
            ("50 Roulette Oyna",          50,         "roulette",      150_000),
            ("30 Plinko Oyna",            30,         "plinko",        150_000),
            ("50 Yazı Tura At",           50,         "flip",          120_000),
            ("50 Zar At",                 50,         "dice",          120_000),
            ("30 Tower Oyna",             30,         "tower",         150_000),
            ("30 Mines Oyna",             30,         "mines",         150_000),
            ("7 Günlük Görev Tamamla",    7,          "daily_done",    200_000),
            ("10 Düello Oyna",            10,         "duel",          130_000),
            ("20 Penaltı At",             20,         "penalty",       130_000),
            ("20 Blackjack Oyna",         20,         "blackjack",     140_000),
            ("15 Zeplin Oyna",            15,         "zeplin",        160_000),
            ("5 Kez Çark Çevir",          5,          "cark",          100_000),
            ("3 Kez Lotoya Katıl",        3,          "loto_bet",      120_000),
        ]

        havuz_orta = [
            ("100 Oyun Oyna",             100,        "any_play",      250_000),
            ("10 Düello Kazan",           10,         "duel_win",      300_000),
            ("20 Blackjack Kazan",        20,         "blackjack_win", 280_000),
            ("5 Milyon Coin Kazan",       5_000_000,  "earn",          350_000),
            ("Zeplinde 5 Kez 2x+ Çek",    5,          "zeplin_big",    300_000),
            ("Slot'ta 3 Jackpot Yap",     3,          "slot_jackpot",  400_000),
            ("Tower'da 5 Kat Geç",        5,          "tower_floor",   320_000),
            ("Mines'da 5 Kez 3+ Kart Aç", 5,          "mines_safe",    280_000),
            ("50 Blackjack Oyna",         50,         "blackjack",     250_000),
            ("200 Oyun Oyna",             200,        "any_play",      350_000),
            ("Zeplinde 10 Kez Oyna",      10,         "zeplin",        280_000),
        ]

        havuz_zor = [
            ("15 Milyon Coin Kazan",      15_000_000, "earn",          1_000_000),
            ("20 Düello Kazan",           20,         "duel_win",      700_000),
            ("10 Jackpot Yap",            10,         "slot_jackpot",  800_000),
            ("500 Oyun Oyna",             500,        "any_play",      600_000),
            ("50 Milyon Coin Bahse Yatır", 50_000_000, "total_bet",    900_000),
            ("30 Blackjack Kazan",        30,         "blackjack_win", 650_000),
            ("Zeplinde 3 Kez 5x+ Çek",    3,          "zeplin_big5",   750_000),
            ("7 Gün Üst Üste Giriş",      7,          "streak",        500_000),
            ("5 Milyon Coin Tek Oyunda Kazan", 5_000_000, "single_win", 850_000),
            ("30 Milyon Coin Kazan",      30_000_000, "earn",          1_200_000),
        ]

        # Her kategoriden 1 görev seç (önceki haftayla çakışmayan)
        def pick_one(pool):
            available = [t for t in pool if t[0] not in prev_tasks]
            if not available:
                available = pool  # Tüm havuz öncekiyle aynıysa normal seç
            return _r.choice(available)

        chosen = [
            pick_one(havuz_kolay),
            pick_one(havuz_orta),
            pick_one(havuz_zor),
        ]

        # Seed'i sıfırla (başka random işlemleri etkilemesin)
        _r.seed()

        for tname, target, ttype, reward in chosen:
            cur.execute(f"""
                INSERT INTO weekly_tasks (user_id, task_name, target, current, is_completed, week_start, task_type, reward)
                VALUES ({p},{p},{p},0,0,{p},{p},{p})
            """, (user_id, tname, target, week_start, ttype, reward))
        conn.commit()

        cur.execute(f"""SELECT task_name, target, current, is_completed, reward FROM weekly_tasks
                       WHERE user_id={p} AND week_start={p}""", (user_id, week_start))
        return fetchall(cur)

def update_weekly_task(user_id: int, task_type: str, amount: int = 1):
    """Haftalık görev ilerlemesini güncelle."""
    p = ph()
    week_start = _get_week_start()
    rewards_won = []
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"""SELECT task_name, target, current, reward FROM weekly_tasks
                       WHERE user_id={p} AND week_start={p} AND task_type={p} AND is_completed=0""",
                   (user_id, week_start, task_type))
        # any_play tüm oyunları sayar
        if not fetchone(cur):
            cur.execute(f"""SELECT task_name, target, current, reward FROM weekly_tasks
                           WHERE user_id={p} AND week_start={p} AND task_type='any_play' AND is_completed=0""",
                       (user_id, week_start))
        tasks = fetchall(cur)
        for tname, target, current, reward in tasks:
            new_current = min(current + amount, target)
            cur.execute(f"""UPDATE weekly_tasks SET current={p} WHERE user_id={p} AND task_name={p} AND week_start={p}""",
                       (new_current, user_id, tname, week_start))
            if new_current >= target:
                cur.execute(f"""UPDATE weekly_tasks SET is_completed=1 WHERE user_id={p} AND task_name={p} AND week_start={p}""",
                           (user_id, tname, week_start))
                cur.execute(f"UPDATE users SET balance=balance+{p} WHERE user_id={p}", (reward, user_id))
                rewards_won.append((tname, reward))
        conn.commit()
        return rewards_won


# ─────────────────────────────────────────────────────────────
# FORM EKOSİSTEMİ (Fizyo, Motivasyon, Tatil, Kamp, Kaptan)
# ─────────────────────────────────────────────────────────────

DAILY_FIZYO_LIMIT = 3
DAILY_MOTIVATION_LIMIT = 5
SEASON_CAMP_LIMIT = 2

FIZYO_COST = 10_000
TATIL_COST = 5_000
KAMP_COST = 50_000

def init_form_eco_tables():
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # Günlük form aksiyonları
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS form_actions (
            user_id     BIGINT,
            action_type TEXT,
            action_date TEXT,
            count       INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, action_type, action_date)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS form_actions (
            user_id     INTEGER,
            action_type TEXT,
            action_date TEXT,
            count       INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, action_type, action_date)
        )""")
        # Sezonluk kamp sayacı
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS season_camps (
            user_id     BIGINT,
            season_no   INTEGER,
            used        INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, season_no)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS season_camps (
            user_id     INTEGER,
            season_no   INTEGER,
            used        INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, season_no)
        )""")
        # Kaptan seçimi
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS team_captain (
            user_id     BIGINT PRIMARY KEY,
            player_name TEXT,
            assigned_at TEXT
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS team_captain (
            user_id     INTEGER PRIMARY KEY,
            player_name TEXT,
            assigned_at TEXT
        )""")
        # Tatil durumu (kaç maç dışarda)
        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS player_vacation (
            user_id     BIGINT,
            player_name TEXT,
            matches_left INTEGER,
            PRIMARY KEY(user_id, player_name)
        )""" if (USE_PG and DATABASE_URL) else """
        CREATE TABLE IF NOT EXISTS player_vacation (
            user_id     INTEGER,
            player_name TEXT,
            matches_left INTEGER,
            PRIMARY KEY(user_id, player_name)
        )""")
        conn.commit()

def _get_action_count(user_id, action_type):
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT count FROM form_actions WHERE user_id={p} AND action_type={p} AND action_date={p}",
                   (user_id, action_type, today))
        row = fetchone(cur)
        return row[0] if row else 0

def _inc_action_count(user_id, action_type):
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT count FROM form_actions WHERE user_id={p} AND action_type={p} AND action_date={p}",
                   (user_id, action_type, today))
        if fetchone(cur):
            cur.execute(f"UPDATE form_actions SET count=count+1 WHERE user_id={p} AND action_type={p} AND action_date={p}",
                       (user_id, action_type, today))
        else:
            cur.execute(f"INSERT INTO form_actions (user_id, action_type, action_date, count) VALUES ({p},{p},{p},1)",
                       (user_id, action_type, today))
        conn.commit()

def do_fizyo(user_id, player_name):
    """Fizyo seansı: form +2 garantili."""
    used = _get_action_count(user_id, "fizyo")
    if used >= DAILY_FIZYO_LIMIT:
        return "limit"
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT form FROM lig_squad WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        row = fetchone(cur)
        if not row: return None
        form = row[0]
        new_form = min(10, form + 2)
        cur.execute(f"UPDATE lig_squad SET form={p} WHERE user_id={p} AND player_name={p}",
                   (new_form, user_id, player_name))
        conn.commit()
    _inc_action_count(user_id, "fizyo")
    return new_form

def do_motivation(user_id, player_name):
    """Motivasyon konuşması: %50 +1, %30 nötr, %20 -1."""
    import random as _r
    used = _get_action_count(user_id, "motivasyon")
    if used >= DAILY_MOTIVATION_LIMIT:
        return "limit", None
    p = ph()
    rnd = _r.random()
    if rnd < 0.5:
        delta = 1
        result = "iyi"
    elif rnd < 0.8:
        delta = 0
        result = "notr"
    else:
        delta = -1
        result = "ters"
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT form FROM lig_squad WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        row = fetchone(cur)
        if not row: return None, None
        form = row[0]
        new_form = max(-10, min(10, form + delta))
        cur.execute(f"UPDATE lig_squad SET form={p} WHERE user_id={p} AND player_name={p}",
                   (new_form, user_id, player_name))
        conn.commit()
    _inc_action_count(user_id, "motivasyon")
    return result, new_form

def do_tatil(user_id, player_name):
    """Tatil: form sıfırlanır, 1 maç oynamaz."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_squad SET form=0 WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        # Vacation kaydı
        cur.execute(f"SELECT 1 FROM player_vacation WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        if fetchone(cur):
            cur.execute(f"UPDATE player_vacation SET matches_left=1 WHERE user_id={p} AND player_name={p}",
                       (user_id, player_name))
        else:
            cur.execute(f"INSERT INTO player_vacation (user_id, player_name, matches_left) VALUES ({p},{p},1)",
                       (user_id, player_name))
        conn.commit()
    return True

def is_on_vacation(user_id, player_name):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT matches_left FROM player_vacation WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        row = fetchone(cur)
        return row[0] if row and row[0] > 0 else 0

def decrement_vacations():
    """Maç sonrası tatil sayaçlarını azalt."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE player_vacation SET matches_left = matches_left - 1 WHERE matches_left > 0")
        cur.execute("DELETE FROM player_vacation WHERE matches_left <= 0")
        conn.commit()

def do_camp(user_id):
    """Kamp: Tüm kadro form +1, sezonda 2 kez."""
    season = get_active_season()
    if not season: return "no_season"
    season_no = season[0]
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT used FROM season_camps WHERE user_id={p} AND season_no={p}",
                   (user_id, season_no))
        row = fetchone(cur)
        used = row[0] if row else 0
        if used >= SEASON_CAMP_LIMIT:
            return "limit"
        # Tüm oyunculara form +1
        cur.execute(f"UPDATE lig_squad SET form=LEAST(10, form+1) WHERE user_id={p}" if (USE_PG and DATABASE_URL) else f"UPDATE lig_squad SET form=MIN(10, form+1) WHERE user_id={p}",
                   (user_id,))
        # Sayaç
        if row:
            cur.execute(f"UPDATE season_camps SET used=used+1 WHERE user_id={p} AND season_no={p}",
                       (user_id, season_no))
        else:
            cur.execute(f"INSERT INTO season_camps (user_id, season_no, used) VALUES ({p},{p},1)",
                       (user_id, season_no))
        conn.commit()
        return used + 1

def set_captain(user_id, player_name):
    """Kaptan seç."""
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM lig_squad WHERE user_id={p} AND player_name={p}",
                   (user_id, player_name))
        if not fetchone(cur):
            return False
        cur.execute(f"SELECT 1 FROM team_captain WHERE user_id={p}", (user_id,))
        if fetchone(cur):
            cur.execute(f"UPDATE team_captain SET player_name={p}, assigned_at={p} WHERE user_id={p}",
                       (player_name, datetime.now().isoformat(), user_id))
        else:
            cur.execute(f"INSERT INTO team_captain (user_id, player_name, assigned_at) VALUES ({p},{p},{p})",
                       (user_id, player_name, datetime.now().isoformat()))
        conn.commit()
        return True

def get_captain(user_id):
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT player_name FROM team_captain WHERE user_id={p}", (user_id,))
        row = fetchone(cur)
        return row[0] if row else None

def apply_captain_bonus(user_id):
    """Kaptan ve yanındaki 2 oyuncuya form +1 (maç öncesi)."""
    captain = get_captain(user_id)
    if not captain: return 0
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        # En yüksek rating'li 3 oyuncu (kaptan dahil) +1 form
        cur.execute(f"""
            SELECT player_name FROM lig_squad
            WHERE user_id={p} AND injury_matches=0
            ORDER BY rating DESC LIMIT 3
        """, (user_id,))
        targets = [r[0] for r in fetchall(cur)]
        affected = 0
        for pname in targets:
            cur.execute(f"UPDATE lig_squad SET form=LEAST(10, form+1) WHERE user_id={p} AND player_name={p}" if (USE_PG and DATABASE_URL) else f"UPDATE lig_squad SET form=MIN(10, form+1) WHERE user_id={p} AND player_name={p}",
                       (user_id, pname))
            affected += 1
        conn.commit()
        return affected

def get_form_action_status(user_id):
    """Bugünkü tüm aksiyon durumları."""
    return {
        "fizyo_used": _get_action_count(user_id, "fizyo"),
        "fizyo_limit": DAILY_FIZYO_LIMIT,
        "motivasyon_used": _get_action_count(user_id, "motivasyon"),
        "motivasyon_limit": DAILY_MOTIVATION_LIMIT,
    }

def get_camps_used(user_id):
    season = get_active_season()
    if not season: return 0
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT used FROM season_camps WHERE user_id={p} AND season_no={p}",
                   (user_id, season[0]))
        row = fetchone(cur)
        return row[0] if row else 0


def count_unplayed_fixtures(season_no: int) -> int:
    """Sezonda oynanmamış maç sayısı."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM lig_fixtures WHERE season_no={p} AND is_played=0", (season_no,))
        row = fetchone(cur)
        return row[0] if row else 0

def count_played_fixtures(season_no: int) -> int:
    """Sezonda oynanmış maç sayısı."""
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM lig_fixtures WHERE season_no={p} AND is_played=1", (season_no,))
        row = fetchone(cur)
        return row[0] if row else 0

def force_end_season(season_no: int):
    """Manuel sezon bitiş (admin)."""
    from datetime import datetime
    p = ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_seasons SET end_date={p}, is_active=0 WHERE season_no={p}",
                   (datetime.now().isoformat(), season_no))
        conn.commit()
