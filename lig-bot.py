"""
TÜRK BUDUN LİGİ BOTU — Bağımsız Sürüm
Sadece lig komutları. Casino ile çakışma yok.
"""
import os
import asyncio
import logging
import random
from datetime import time as dtime, timezone, timedelta, datetime
from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

import database as db
import lig as lig_module
import lig

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)

# ── Token & Admin ──
TOKEN = os.getenv("LIG_BOT_TOKEN") or os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("LIG_BOT_TOKEN veya BOT_TOKEN env variable eksik!")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "6084870602").split(",")))
def is_admin(uid): return uid in ADMIN_IDS

# ── Sabitler ──
BROADCAST_TOPICS = {}
LIG_BROADCAST_CHATS = set()
_prematch_done_date = None
_morning_done_date = None
_noon_done_date = None
_evening_done_date = None

def tr_now():
    return datetime.now(timezone(timedelta(hours=3)))

def _get_week_start():
    from datetime import datetime
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")

# ── Start & Yardım ──
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db.register_user(uid, update.effective_user.first_name)
    await update.message.reply_text(
        "🏟️ *TÜRK BUDUN LİGİ*\n\n"
        "Takımını kur, oyuncuları transfer et, şampiyon ol!\n\n"
        "📋 /yardim — Tüm komutlar\n"
        "🏟️ /lig — Lig ekranı\n"
        "💰 /lc_bakiye — LC bakiye",
        parse_mode="Markdown")

async def cmd_yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg1 = (
        "📋 *TÜRK BUDUN LİGİ — KOMUTLAR*\n\n"
        "🏁 *BAŞLANGIÇ*\n"
        "/lig /takim\\_kur /takimim /form\n\n"
        "🛒 *TRANSFER MARKETİ*\n"
        "/market — Tüm müsait oyuncular\n"
        "/market GK/DEF/MID/FWD — Pozisyon filtresi\n"
        "/market <isim> — Oyuncu ara\n"
        "/transfer /sat /akademi /akademi\\_al\n\n"
        "🤝 *OYUNCULAR ARASI*\n"
        "/teklif /teklif\\_kabul /teklif\\_red\n"
        "/teklif\\_karsi /kirala\n"
        "/sat\\_pazar /pazar /pazardan\\_al\n\n"
        "👔 *ANTRENÖR*\n"
        "/antrenor /hoca\\_tut /hoca\\_birak\n\n"
        "🏋️ *GELİŞİM*\n"
        "/antrenman /fizyo /motivasyon\n"
        "/tatil /kamp /kaptan\n\n"
        "⚽ *İLK 11*\n"
        "/ilk11 — Mevcut ilk 11'i gör\n"
        "/ilk11\\_ekle /ilk11\\_cikar /ilk11\\_sifirla\n\n"
        "⚙️ *TAKTİK*\n"
        "/taktik /dizilis /taktik\\_sec\n\n"
        "🏆 *SIRALAMA*\n"
        "/lig\\_top /puandurumu /ligler /sampiyonlar\n\n"
        "📅 *MAÇ*\n"
        "/fikstur /tahmin /rakip /macbaslat\n"
        "/haberler /sosyal\n\n"
        "💱 *EKONOMİ*\n"
        "/kur /cevir /lc\\_bakiye /lc\\_kod"
    )
    await update.message.reply_text(msg1, parse_mode="Markdown")
    if is_admin(uid):
        await update.message.reply_text(
            "🔐 *ADMİN KOMUTLARI*\n\n"
            "/lc\\_yukle /lc\\_dusur /lc\\_toplu\\_yukle\n"
            "/lc\\_kodolustur /lig\\_sil\n"
            "/lig\\_oyuncular — Tüm oyuncuları listele\n"
            "/lig\\_tam\\_sifirla — Sezonu sıfırla\n"
            "/terfi\\_dusme /fikstur\\_olustur\n"
            "/maclari\\_basla /sezon\\_bitir /sezon\\_sifirla\n"
            "/lig\\_yayin /casino\\_yayin\n"
            "/yayin\\_test /yayin\\_durum",
            parse_mode="Markdown"
        )

# ════════════════════════════════════════════
# LİG KOMUTLARI (bot.py'den taşındı)
# ════════════════════════════════════════════

def _get_halftime_coach_msg(t1, t2, g1, g2):
    if g1 > g2:
        return f"💪 {t1} hocası: Devam edin!"
    elif g2 > g1:
        return f"😤 {t2} hocası: Geri donelim!"
    else:
        return "🤝 İki hoca da değişiklik düşünüyor..."

async def _send_to_broadcast_chats(context, text, parse_mode="Markdown", category="lig"):
    """
    Yayın chat'lerine gönder.
    category: "lig" | "casino"
    """
    sent_to = set()

    if not BROADCAST_TOPICS and not LIG_BROADCAST_CHATS:
        print(f"[YAYIN] ⚠️ Hiç yayın kanalı kayıtlı değil! /lig_yayin komutuyla kayıt et.")
        return sent_to

    for chat_id, topics in list(BROADCAST_TOPICS.items()):
        if chat_id in sent_to:
            continue
        thread_id = topics.get(category)
        try:
            kwargs = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
            if thread_id is not None:
                kwargs["message_thread_id"] = thread_id
            await context.bot.send_message(**kwargs)
            sent_to.add(chat_id)
            print(f"[YAYIN] ✅ {category} → chat {chat_id} thread {thread_id}")
        except Exception as e1:
            print(f"[YAYIN] ⚠️ Markdown hata chat {chat_id}: {e1} — düz metin deneniyor")
            try:
                kwargs2 = {"chat_id": chat_id, "text": text}
                if thread_id is not None:
                    kwargs2["message_thread_id"] = thread_id
                await context.bot.send_message(**kwargs2)
                sent_to.add(chat_id)
            except Exception as e2:
                print(f"[YAYIN] ❌ Gönderilemedi chat {chat_id}: {e2}")

    for chat_id in list(LIG_BROADCAST_CHATS):
        if chat_id in sent_to:
            continue
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            sent_to.add(chat_id)
            print(f"[YAYIN] ✅ fallback → chat {chat_id}")
        except Exception as e:
            print(f"[YAYIN] ❌ fallback hata chat {chat_id}: {e}")

    return sent_to

async def _notify_admin(context, text, parse_mode="Markdown"):
    """SADECE önemli gelişmeleri admin'e özelden bildir (1 kez)."""
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=f"🔔 {text}", parse_mode=parse_mode)
        except:
            pass
        break  # Sadece ilk admin

def _find_player_in_squad(uid, name_query):
    """Squad'da oyuncu bul (case-insensitive)."""
    squad = db.get_squad(uid)
    name_lower = name_query.lower()
    for p_name, rating, pos, starter in squad:
        if name_lower in p_name.lower():
            return p_name, rating, pos
    return None

async def _resolve_target_user(update, context):
    """Hedef kullanıcıyı belirle: reply > @username > arg[0]."""
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id, update.message.reply_to_message.from_user.first_name
    if context.args and context.args[0].startswith("@"):
        username = context.args[0][1:]
        user = db.get_user_by_username(username)
        if user:
            return user[0], user[1]
    return None, None

def random_yorum(minute, team_name):
    import random as _r
    return _r.choice(CANLI_YORUMLAR).format(minute=minute, team=team_name)

async def _live_match_simulation(context, team1_name, team1_squad, team1_form,
                                  team2_name, team2_squad, team2_form,
                                  t1_formation="4-3-3", t1_tactic="dengeli",
                                  t2_formation="4-3-3", t2_tactic="dengeli"):
    """
    15 dakikada canlı maç — zengin mesajlar, tempo yorumları,
    yarı zaman, değişiklik, ek dakika.
    DÖNDÜRÜR: (g1, g2, mvp, scorers)
    """
    import random as _r
    try:
        g1, g2, events, mvp, scorers = lig.simulate_match_with_tactics(
            team1_name, team1_squad, team1_form, t1_formation, t1_tactic,
            team2_name, team2_squad, team2_form, t2_formation, t2_tactic,
        )
    except Exception:
        g1, g2, events, mvp, scorers = lig.simulate_match_detailed(
            team1_name, team1_squad, team1_form,
            team2_name, team2_squad, team2_form
        )

    # Form emojileri
    def form_em(f): return "🔥" if f>=3 else "📈" if f>0 else "📉" if f<0 else "➡️"

    # ── AÇILIŞ ──
    intro_templates = [
        f"🏟️ *SAHAYA ÇIKIYORLAR!*\n\n"
        f"{'🔴' if 'a' in team1_name.lower() else '🔵'} *{team1_name}* {form_em(team1_form)}\n"
        f"⚡ *KARŞISINDA* ⚡\n"
        f"{'🟡' if 'b' in team2_name.lower() else '⚪'} *{team2_name}* {form_em(team2_form)}\n\n"
        f"📐 {t1_formation} *vs* {t2_formation}\n"
        f"🎯 {t1_tactic.upper()} *vs* {t2_tactic.upper()}\n\n"
        f"_Düdük çalmak üzere..._",

        f"📣 *MAÇA DAKIKALAR KALA!*\n\n"
        f"🏠 *{team1_name}* → *{t1_tactic}* taktiğiyle geliyor {form_em(team1_form)}\n"
        f"✈️ *{team2_name}* → *{t2_tactic}* taktiğiyle sahada {form_em(team2_form)}\n\n"
        f"⚡ Kim üstün gelecek?\n"
        f"_Birkaç dakika sonra başlıyoruz!_",
    ]
    await _send_to_broadcast_chats(context, _r.choice(intro_templates), category="lig")
    await asyncio.sleep(8)

    # Olayları 15 dakikaya yay (her olay = yaklaşık 60-90 sn bekleme)
    current_g1, current_g2 = 0, 0
    halftime_done = False
    last_tempo_min = 0

    # Tempo yorumu şablonları
    tempo_templates = {
        "neutral": [
            f"📊 *{{min}}. DAKİKA*\n⚖️ Sahada denge hakim, iki takım da pozisyon arıyor...",
            f"⚙️ *{{min}}. DAKİKA*\n💭 Orta saha mücadelesi kızışıyor, top el değiştiriyor.",
            f"👁️ *{{min}}. DAKİKA*\n🎯 Kritik anlar yaklaşıyor olabilir, her iki takım da dikkatli...",
        ],
        "attack1": [
            f"⚡ *{{min}}. DAKİKA*\n🔥 *{team1_name}* üst üste atakta! Savunma zorlanıyor...",
            f"💨 *{{min}}. DAKİKA*\n⚠️ *{team1_name}* tehlike yaratıyor, *{team2_name}* direnç gösteriyor!",
        ],
        "attack2": [
            f"⚡ *{{min}}. DAKİKA*\n🔥 *{team2_name}* üst üste atakta! Savunma zorlanıyor...",
            f"💨 *{{min}}. DAKİKA*\n⚠️ *{team2_name}* tehlike yaratıyor, *{team1_name}* direnç gösteriyor!",
        ],
    }

    # Olayları sırala
    sorted_events = sorted(events, key=lambda e: e[0])
    total_events = len(sorted_events)
    total_duration = 900  # 15 dk = 900 sn
    sleep_per_event = total_duration / max(total_events + 3, 5)

    for i, evt in enumerate(sorted_events[:10]):
        minute, evt_type, team, player, detail = evt
        await asyncio.sleep(min(sleep_per_event, 90))

        # Yarı zaman mesajı
        if not halftime_done and minute >= 45:
            halftime_done = True
            ht_score = f"{current_g1} - {current_g2}"
            if current_g1 > current_g2:
                ht_durum = f"🔥 {team1_name} üstün ilk yarıda!"
            elif current_g2 > current_g1:
                ht_durum = f"⚡ {team2_name} önde gidiyor!"
            else:
                ht_durum = "⚖️ Berabere gidiyoruz!"

            ht_msg1 = (
                f"⏸️ *İLK YARI BİTTİ!*\n\n"
                f"┌──────────────────────┐\n"
                f"│  {team1_name[:10].center(10)}  {current_g1} ┃ {current_g2}  {team2_name[:10].center(10)}  │\n"
                f"└──────────────────────┘\n\n"
                f"{ht_durum}\n"
                f"_İkinci yarı heyecanla başlıyor..._"
            )
            ht_msg2 = (
                f"📢 *SOYUNMA ODASI ZAMANI!*\n\n"
                f"🕐 45 dakika oynadık\n"
                f"📊 Skor: *{team1_name}* `{ht_score}` *{team2_name}*\n\n"
                f"{_get_halftime_coach_msg(team1_name, team2_name, current_g1, current_g2)}"
            )
            await _send_to_broadcast_chats(context, _r.choice([ht_msg1, ht_msg2]), category="lig")
            await asyncio.sleep(12)

        # Tempo yorumu (her 20 dakikada bir)
        if minute - last_tempo_min >= 20 and minute not in [45, 90]:
            last_tempo_min = minute
            if current_g1 > current_g2:
                t = _r.choice(tempo_templates["attack1"])
            elif current_g2 > current_g1:
                t = _r.choice(tempo_templates["attack2"])
            else:
                t = _r.choice(tempo_templates["neutral"])
            await _send_to_broadcast_chats(context, t.format(min=minute), category="lig")
            await asyncio.sleep(5)

        # GOL
        if evt_type == "goal":
            if team == team1_name:
                current_g1 += 1
            else:
                current_g2 += 1

            gol_templates = [
                f"💥 *GOOOOL!* 💥\n\n"
                f"⭐ *{player}* — {minute}. DAKİKA\n"
                f"🏟️ *{team}*\n"
                f"{'👟 Asist: _' + detail + '_' if detail else '💪 Serbest bırakıldı, kaçırmadı!'}\n\n"
                f"┌──────────────────────┐\n"
                f"│  {team1_name[:10].center(10)}  {current_g1} ┃ {current_g2}  {team2_name[:10].center(10)}  │\n"
                f"└──────────────────────┘",

                f"🚨 *NET! GOOOOL!*\n\n"
                f"🎯 *{minute}. DAKİKADA {player.upper()}!*\n"
                f"Takım: *{team}*\n"
                f"{'🤝 ' + detail + ' harika pasıyla buldu!' if detail else '🔥 Solo aksiyon, müthiş bitiriş!'}\n\n"
                f"📊 *{team1_name}* {current_g1} — {current_g2} *{team2_name}*\n"
                f"{'🏆 ' + team + ' önde!' if current_g1 != current_g2 else '⚖️ Eşitlik bozuldu!'}",

                f"⚽ *{minute}\' — GOOOOOL!* ⚽\n\n"
                f"👤 *{player}*\n"
                f"🏟️ Takım: _{team}_\n"
                f"{'🎁 Harika bir asistle geldi: ' + detail if detail else '💎 Bireysel bir klas!'}\n\n"
                f"🔢 Skor: **{current_g1} - {current_g2}**\n"
                f"_Tribünler çılgına döndü!_ 🎉",
            ]
            await _send_to_broadcast_chats(context, _r.choice(gol_templates), category="lig")

        # SARI KART
        elif evt_type == "yellow":
            kart_templates = [
                f"🟨 *{minute}\' — SARI KART!*\n\n"
                f"⚠️ *{player}* ({team})\n"
                f"😤 Hakem tereddüt etmedi!\n"
                f"_Bir sonraki sarı kart tehlikeli..._",

                f"🟨 *SARI KART — {minute}. DAKİKA*\n\n"
                f"👤 *{player}* kartı gördü\n"
                f"🏟️ Takım: _{team}_\n"
                f"😬 _{player} dikkatli olmak zorunda!_",
            ]
            await _send_to_broadcast_chats(context, _r.choice(kart_templates), category="lig")

    # Ek dakika mesajı
    await asyncio.sleep(15)
    extra = _r.randint(2, 5)
    if g1 != g2:
        losing = team2_name if g1 > g2 else team1_name
        await _send_to_broadcast_chats(context,
            f"⏰ *{extra} EK DAKİKA!*\n\n"
            f"😰 *{losing}* son şansını arıyor...\n"
            f"_Kalpler ağızda!_",
            category="lig")
    else:
        await _send_to_broadcast_chats(context,
            f"⏰ *{extra} EK DAKİKA!*\n\n"
            f"🤝 Beraberlik devam ediyor...\n"
            f"_Son dakika golü gelebilir!_",
            category="lig")
    await asyncio.sleep(20)

    # ── MAÇ SONU ──
    if g1 > g2: winner_txt = f"🏆 *{team1_name}* kazandı!"
    elif g2 > g1: winner_txt = f"🏆 *{team2_name}* kazandı!"
    else: winner_txt = "🤝 *Beraberlik!*"

    # Daha temiz final mesajı
    final_msg = (
        f"🏁 *MAÇ BİTTİ!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ *{team1_name}* `{g1} — {g2}` *{team2_name}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{winner_txt}\n\n"
    )
    all_scorers = scorers.get("team1", []) + scorers.get("team2", [])
    if all_scorers:
        final_msg += "⚽ *Goller:*\n"
        for s in all_scorers:
            final_msg += f"  • {s['minute']}\' *{s['player']}*"
            if s.get("assist"):
                final_msg += f" _(asist: {s['assist']})_"
            final_msg += "\n"
    if mvp:
        final_msg += f"\n⭐ *Maçın Adamı:* _{mvp}_"

    await _send_to_broadcast_chats(context, final_msg, category="lig")
    return g1, g2, mvp, scorers





# ─────────────────────────────────────────────────────────────
# TOPLU MAÇ SONU — Haberler + Sosyal Medya
# ─────────────────────────────────────────────────────────────

async def _send_match_day_summary(context, results: list, season_no: int):
    """
    Tüm maç sonuçlarını tek mesajda özetle.
    results: [(t1_name, g1, t2_name, g2, mvp, derby), ...]
    """
    import random as _r
    if not results: return

    # Tek özet mesaj
    text = (
        "╔══════════════════════╗\n"
        "║  📊  GÜNÜN SONUÇLARI  ║\n"
        "╚══════════════════════╝\n\n"
    )
    for t1, g1, t2, g2, mvp, derby in results:
        if g1 > g2:   em = "🏆"
        elif g2 > g1: em = "🏆"
        else:         em = "🤝"
        derby_em = " 🔥" if derby else ""
        text += f"{em} *{t1}* `{g1}-{g2}` *{t2}*{derby_em}\n"
        if mvp:
            text += f"   ⭐ _{mvp}_\n"
        text += "\n"

    # Gün sonu puan durumu
    try:
        top5 = db.get_all_teams_ranked()[:5]
        if top5:
            text += "━━━━━━━━━━━━━━━━━━━━━━\n"
            text += "🏆 *GÜNCEL SIRALAMA (TOP 5)*\n"
            medals = ["🥇","🥈","🥉","4️⃣","5️⃣"]
            for i, t in enumerate(top5):
                pts = t[3]*3 + t[4]
                text += f"{medals[i]} *{t[1]}* — {pts}p\n"
    except: pass

    await _send_to_broadcast_chats(context, text, category="lig")
    await asyncio.sleep(10)

    # ── HABERLER (5 dk sonra) ──
    haber_templates = []
    for t1, g1, t2, g2, mvp, derby in results:
        if g1 > g2:
            haber_templates += [
                f"📰 *{t1}* galibiyetiyle liderliğini sağlamlaştırdı! {g1}-{g2}\nBu sezonun en etkileyici performanslarından biri sergilendi.",
                f"🗞️ *{t1}* sahadan *{g1}-{g2}* ayrıldı!\n*{mvp}* gecenin yıldızı olurken, *{t2}* taraftarı hayal kırıklığı yaşadı.",
            ]
        elif g2 > g1:
            haber_templates += [
                f"📰 Deplasman galibiyeti! *{t2}* rakip sahada *{g2}-{g1}* kazandı!\nBu sonuç lig sıralamasını alt üst etti.",
                f"🗞️ *{t2}* kritik 3 puanı aldı! *{t1}* evinde yenildi: {g1}-{g2}\n*{mvp}* gecenin en iyi ismi oldu.",
            ]
        else:
            haber_templates += [
                f"📰 *{t1}* ile *{t2}* golsüz berabere kaldı!\nİki takım da fırsatları değerlendiremedi, puan paylaşıldı.",
                f"🗞️ *{t1}* {g1}-{g2} *{t2}* — Drama dolu bir maç!\nBeraberlik iki takımı da memnun etmedi.",
            ]
        if derby:
            haber_templates.append(
                f"🔥 *DERBİ* | *{t1}* {g1}-{g2} *{t2}*\n"
                f"Bu derby şehirde uzun süre konuşulacak!\n"
                f"{'🏆 ' + (t1 if g1>g2 else t2) + ' şampiyonluk yolunda büyük avantaj yakaladı!' if g1!=g2 else '🤝 Derby beraberlikle kapandı, iki taraf da hayal kırıklığında.'}"
            )

    if haber_templates:
        import random as _r
        # Max 3 haber at, tekrar etmesin
        haberler = _r.sample(haber_templates, min(3, len(haber_templates)))
        haber_msg = "📰 *LİG HABERLERİ*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for h in haberler:
            haber_msg += f"• {h}\n\n"
        await _send_to_broadcast_chats(context, haber_msg, category="lig")
        # DB'ye kaydet
        try:
            for h in haberler:
                db.save_news(h[:150])
        except: pass
    await asyncio.sleep(10)

    # ── SOSYAL MEDYA (10 dk sonra) ──
    sosyal_pool = []
    for t1, g1, t2, g2, mvp, derby in results:
        winner = t1 if g1>g2 else t2 if g2>g1 else None
        loser  = t2 if g1>g2 else t1 if g2>g1 else None
        if winner:
            sosyal_pool += [
                f"🐦 *Twitter:* \"#{winner.replace(' ','')} KAZANDI!\" — Trending 1. sırada 🔥",
                f"💬 *Forum:* \"*{winner}* bu sene çok güçlü, durduracak var mı?!\"",
                f"📺 *Yorumcu:* \"*{mvp}* sahadaki en iyi oyuncuydu. Paha biçilemez bir performans!\"",
            ]
            sosyal_pool += [
                f"😤 *{loser} Taraftarı:* \"Bu nasıl futbol, utanç verici!\"\n😍 *{winner} Taraftarı:* \"Şampiyon biz olacağız!\"",
            ]
        else:
            sosyal_pool += [
                f"🐦 *Twitter:* \"*{t1}* - *{t2}* beraberlik! İki taraf da hayal kırıklığında.\"",
                f"💬 *Forum:* \"Kötü bir maçtı, puan bile kazanamadık!\n—Her iki taraf için de geçerli bu!\"",
            ]
        if derby:
            sosyal_pool.append(
                f"🔥 *DERBİ SONRASI SOSYAL MEDYA:*\n"
                f"{'🏆 ' + winner + ' taraftarı çılgına döndü! Stadyum şenlendi!' if winner else '🤝 Derby beraberlikle bitti, herkes tartışıyor!'}"
            )

    if sosyal_pool:
        sosyal_secim = _r.sample(sosyal_pool, min(2, len(sosyal_pool)))
        sosyal_msg = "📱 *SOSYAL MEDYA ÇALKANIYOR!*\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for s in sosyal_secim:
            sosyal_msg += f"{s}\n\n"
        try:
            db.post_social_reaction(t1 if results else "Lig", mvp or "Yıldız", "positive")
        except: pass
        await _send_to_broadcast_chats(context, sosyal_msg, category="lig")

def _generate_news_after_match(t1_name, t2_name, g1, g2, mvp, scorers, is_derby):
    """Maç sonrası rastgele bir haber üret."""
    import random as _r
    headlines = []
    if is_derby:
        if g1 > g2:
            headlines.append(f"🔥 DERBİDE *{t1_name}* damgası! {t2_name}'ı {g1}-{g2} mağlup etti!")
        elif g2 > g1:
            headlines.append(f"🔥 DERBİDE büyük şok! *{t2_name}* deplasmanda {t1_name}'ı yıktı: {g2}-{g1}")
        else:
            headlines.append(f"🔥 DERBİDE puanlar paylaşıldı: *{t1_name}* {g1}-{g2} *{t2_name}*")
    if scorers.get("team1") and len(scorers["team1"]) >= 2:
        for goal in scorers["team1"]:
            pass
        # Hat-trick var mı?
        from collections import Counter
        all_scorers = [g["player"] for g in scorers["team1"]] + [g["player"] for g in scorers["team2"]]
        scorer_count = Counter(all_scorers)
        for player, cnt in scorer_count.items():
            if cnt >= 3:
                headlines.append(f"⚽ HAT-TRICK! *{player}* tek başına 3 gol attı!")
            elif cnt == 2:
                headlines.append(f"⚽ İkili gol: *{player}* bugün ön plandaydı!")
    if mvp:
        headlines.append(f"⭐ MVP: *{mvp}* parıltısı geceyi aydınlattı!")
    # Büyük skor
    if g1 + g2 >= 6:
        headlines.append(f"🎆 Gol şöleni! *{t1_name}* {g1}-{g2} *{t2_name}* — toplam {g1+g2} gol!")
    elif g1 + g2 == 0:
        headlines.append(f"🔒 İki kale de bos: *{t1_name}* 0-0 *{t2_name}*")
    return _r.choice(headlines) if headlines else None




# ─────────────────────────────────────────────────────────────
# CASHBACK + BOT KONUŞMA + GÜZELLEŞTİRME
# ─────────────────────────────────────────────────────────────

async def countdown_match_job(context):
    """Maça 2 saat kala geri sayım, 1 saat, 30 dk."""
    now = tr_now()
    season = db.get_active_season()
    if not season: return
    today = now.strftime("%Y-%m-%d")
    fixtures = db.get_fixtures_by_date(today, season[0])
    if not fixtures: return

    # 19:00 → 2 saat kaldı
    if now.hour == 19 and now.minute <= 5:
        await _send_to_broadcast_chats(
            context,
            f"⏰ *MAÇA 2 SAAT KALDI!*\n\n"
            f"📅 Bugün *{len(fixtures)}* maç oynanacak.\n"
            f"💪 Kadronu kontrol et: `/takimim`\n"
            f"⚙️ Taktiğini ayarla: `/taktik`\n"
            f"📋 Fikstürü gör: `/fikstur`",
            category="lig")
        return

    # 20:00 → 1 saat kaldı
    if now.hour == 20 and now.minute <= 5:
        await _send_to_broadcast_chats(
            context,
            f"⏰ *MAÇA 1 SAAT KALDI!*\n\n"
            f"🎯 Tahmin penceresi 30 dakika sonra açılacak!\n"
            f"🏟️ Bugün oynanacak: *{len(fixtures)} maç*",
            category="lig")

async def morning_news_job(context):
    """10:00 — Günün maçları duyurusu."""
    global _morning_done_date
    now = tr_now()
    today_str = now.strftime("%Y-%m-%d")
    if _morning_done_date == today_str: return
    if not (now.hour == 10 and now.minute >= 0 and now.minute <= 30):
        return
    _morning_done_date = today_str
    season = db.get_active_season()
    if not season: return
    today = tr_now().strftime("%Y-%m-%d")
    fixtures = db.get_fixtures_by_date(today, season[0])
    if not fixtures:
        return

    msg = (
        "╔══════════════════════╗\n"
        "║  ☀️  GÜNAYDIN LİG!  ║\n"
        "╚══════════════════════╝\n\n"
        f"📅 *Bugün {len(fixtures)} maç var!*\n\n"
    )

    derby_count = 0
    for f in fixtures:
        fid, week, mdate, t1id, t2id, derby, t1name, t2name = f
        f1 = db.get_team_form(t1id)
        f2 = db.get_team_form(t2id)
        form1 = "🔥" if f1 >= 3 else "📈" if f1 > 0 else "📉" if f1 < 0 else "➡️"
        form2 = "🔥" if f2 >= 3 else "📈" if f2 > 0 else "📉" if f2 < 0 else "➡️"
        derby_em = " 🔥" if derby else ""
        if derby: derby_count += 1
        msg += f"⚽ *{t1name}* {form1} 🆚 {form2} *{t2name}*{derby_em}\n"

    if derby_count:
        msg += f"\n🔥 *{derby_count} DERBİ var!*\n"

    msg += (
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "🕘 Maçlar: *21:00* (TR)\n"
        "🎯 Tahmin penceresi: 20:30 - 21:00\n"
        "💡 `/fikstur` ile detay"
    )

    await _send_to_broadcast_chats(context, msg, category="lig")

async def noon_news_job(context):
    """14:00 — Transfer hareketleri + antrenman raporları."""
    global _noon_done_date
    now = tr_now()
    today_str = now.strftime("%Y-%m-%d")
    if _noon_done_date == today_str: return
    if not (now.hour == 14 and now.minute >= 0 and now.minute <= 30):
        return
    _noon_done_date = today_str
    season = db.get_active_season()
    if not season: return

    # En çok antrenman yapan oyuncular (basit özet)
    msg = (
        "╔══════════════════════╗\n"
        "║  📰  ÖĞLE HABERLERİ  ║\n"
        "╚══════════════════════╝\n\n"
    )

    # Son haberlerden rastgele birkaç tane
    recent_news = db.get_recent_news(15)
    if recent_news:
        msg += "📜 *Son Haberler:*\n"
        for nd, content_news in recent_news[:5]:
            msg += f"  • {content_news}\n"
        msg += "\n"

    # En çok satılan oyuncular (akademi)
    msg += (
        "💼 *AKADEMİ AKTİVİTESİ*\n"
        "Genç yetenekler için /akademi yaz!\n\n"
        "🏋️ *ANTRENMAN HATIRLATMASI*\n"
        "/antrenman ile günde 2 oyuncunu çalıştır!"
    )

    await _send_to_broadcast_chats(context, msg, category="lig")

async def evening_news_job(context):
    """17:00 — Maç önizleme, form analizi."""
    global _evening_done_date
    now = tr_now()
    today_str = now.strftime("%Y-%m-%d")
    if _evening_done_date == today_str: return
    if not (now.hour == 17 and now.minute >= 0 and now.minute <= 30):
        return
    _evening_done_date = today_str
    season = db.get_active_season()
    if not season: return
    today = tr_now().strftime("%Y-%m-%d")
    fixtures = db.get_fixtures_by_date(today, season[0])
    if not fixtures: return

    # En formda takımlar
    teams = db.get_all_teams_ranked()
    top_form = []
    for t in teams[:20]:
        uid_t = t[0]
        form = db.get_team_form(uid_t)
        if form >= 2:
            top_form.append((t[1], form))
    top_form.sort(key=lambda x: -x[1])

    msg = (
        "╔══════════════════════╗\n"
        "║  🌆  AKŞAM ANALİZİ  ║\n"
        "╚══════════════════════╝\n\n"
        f"⏰ *4 saat sonra maç saati!*\n\n"
    )

    if top_form:
        msg += "🔥 *EN FORMDA TAKIMLAR:*\n"
        for name, form in top_form[:5]:
            em = "🔥🔥" if form >= 4 else "🔥" if form >= 2 else "📈"
            msg += f"  {em} *{name}* (form +{form})\n"
        msg += "\n"

    # Bugünkü maçlar
    msg += "⚽ *BUGÜN OYNANACAK:*\n"
    for f in fixtures[:5]:
        fid, week, mdate, t1id, t2id, derby, t1name, t2name = f
        derby_em = " 🔥" if derby else ""
        msg += f"  • *{t1name}* vs *{t2name}*{derby_em}\n"

    msg += (
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 Tahmin penceresi: 20:30\n"
        "💡 `/taktik` ile takımını hazırla!"
    )

    await _send_to_broadcast_chats(context, msg, category="lig")



# ─────────────────────────────────────────────────────────────
# CANLI MAÇ YORUMLARI (Yarı zaman, anlar, geri sayım)
# ─────────────────────────────────────────────────────────────

CANLI_YORUMLAR = [
    "📊 *{minute}\' {team}* tempoyu artırıyor!",
    "⚡ *{minute}\' {team}* presle baskı kuruyor!",
    "🎯 *{minute}\' {team}* pozisyon arıyor!",
    "🛡️ *{minute}\' {team}* defansı kapatıyor!",
    "👟 *{minute}\' Tehlikeli kornerden uzaklaştırıldı!*",
    "🚨 *{minute}\' Az kaldı! Direkt vuruş!*",
    "💨 *{minute}\' {team}* hücumda devrede!",
    "⚙️ *{minute}\' Orta saha ortaya çıkmaya başladı.*",
    "🔄 *{minute}\' Top sahanın orta yerinde dolaşıyor.*",
    "👁️ *{minute}\' Maçın seyri değişebilir!*",
]

async def prematch_announcement_job(context):
    """Maçtan 30 dk önce (TR saat 20:30) maç önizleme + hava + tahmin penceresi."""
    global _prematch_done_date
    now = tr_now()
    today_str = now.strftime("%Y-%m-%d")
    # Bugün zaten çalıştıysa dur
    if _prematch_done_date == today_str:
        return
    # 20:30 - 20:55 arasında bir kez çalışsın
    if not (now.hour == 20 and now.minute >= 30 and now.minute <= 55):
        return
    _prematch_done_date = today_str

    season = db.get_active_season()
    if not season: return
    season_no = season[0]

    today = now.strftime("%Y-%m-%d")
    fixtures = db.get_fixtures_by_date(today, season_no)
    if not fixtures: return

    # Hava durumu çek
    weather = await get_istanbul_weather()
    weather_line = weather if weather else "🌡️ _Hava bilgisi alınamadı_"

    # Maç önizleme mesajı
    header = (
        "╔══════════════════════╗\n"
        "║  ⚽  BUGÜNKÜ MAÇLAR  ║\n"
        "║       21:00         ║\n"
        "╚══════════════════════╝\n\n"
        f"🌤️ *İstanbul Hava Durumu* _(Maçlar İstanbul dışında oynanmıyor gibi bilgi)_\n"
        f"{weather_line}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 *MAÇ PROGRAMI*\n\n"
    )

    for f in fixtures:
        fid, week, mdate, t1id, t2id, derby, t1name, t2name = f
        # Form bilgileri
        f1 = db.get_team_form(t1id)
        f2 = db.get_team_form(t2id)
        form1 = "🔥" if f1 >= 3 else "📈" if f1 > 0 else "📉" if f1 < 0 else "➡️"
        form2 = "🔥" if f2 >= 3 else "📈" if f2 > 0 else "📉" if f2 < 0 else "➡️"
        # Taktik
        form_t1, tac1 = db.get_team_tactics(t1id)
        form_t2, tac2 = db.get_team_tactics(t2id)
        derby_em = " 🔥 *DERBİ*" if derby else ""
        header += (
            f"⚽ *{t1name}* {form1} 🆚 {form2} *{t2name}*{derby_em}\n"
            f"   📐 {form_t1} ({tac1}) vs {form_t2} ({tac2})\n"
            f"   🎯 Tahmin: `/tahmin {fid} <skor>`\n\n"
        )

    header += (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 *TAHMİN PENCERESİ AÇIK!*\n"
        "   Maç başlayana kadar tahmin yapabilirsin.\n"
        "   • Tam skor: +10.000 LC\n"
        "   • Sadece sonuç: +2.000 LC"
    )

    await _send_to_broadcast_chats(context, header)

    # Maçı olanlara DM gönder
    for f in fixtures:
        fid, week, mdate, t1id, t2id, derby, t1name, t2name = f
        msg_text = (
            f"⏰ *MAÇ HATIRLATMA!*\n\n"
            f"⚽ 30 dakika sonra (21:00) maçın var!\n\n"
            f"🏠 *{t1name}* 🆚 *{t2name}*{' 🔥 DERBİ!' if derby else ''}\n"
            f"📊 {weather_line}\n\n"
            f"💪 Kadronu kontrol et: `/takimim`"
        )
        for uid_t in (t1id, t2id):
            try:
                await context.bot.send_message(chat_id=uid_t, text=msg_text, parse_mode="Markdown")
            except:
                pass

async def daily_match_job(context):
    """Bugünkü fikstüre göre maçları oyna."""
    season = db.get_active_season()
    if not season:
        print("[MAÇ] ❌ Aktif sezon yok!")
        return
    season_no = season[0]
    print(f"[MAÇ] Sezon {season_no} kontrol ediliyor...")

    # Top 4 takım için derbi işaretle
    db.mark_derby_matches(season_no)

    fixtures = db.get_today_fixtures(season_no)
    if not fixtures:
        print(f"[MAÇ] ⚠️ Bugün maç yok (sezon {season_no})")
        # Fikstür var mı genel?
        try:
            all_today = db.get_fixtures_by_date(tr_now().strftime("%Y-%m-%d"), season_no)
            print(f"[MAÇ] Genel bugün fikstür: {len(all_today) if all_today else 0}")
        except: pass
        return
    print(f"[MAÇ] ✅ {len(fixtures)} maç bulundu, başlıyor...")

    # Her fikstürün takım verilerini hazırla
    pairs = []
    bye_team = None
    removed_blocked = []
    for f in fixtures:
        fid, week, mdate, t1id, t2id, is_derby, t1name, t2name = f
        # Maç öncesi kaptan bonusu
        try:
            db.apply_captain_bonus(t1id)
            db.apply_captain_bonus(t2id)
        except: pass
        # Her takım için sağlıklı kadro
        h1 = db.get_healthy_squad(t1id)
        h2 = db.get_healthy_squad(t2id)
        # Tatildeki oyuncuları çıkar
        h1 = [p for p in h1 if not db.is_on_vacation(t1id, p[0])]
        h2 = [p for p in h2 if not db.is_on_vacation(t2id, p[0])]
        if len(h1) < 7 or len(h2) < 7:
            print(f"[MAÇ] ⚠️ {t1name} ({len(h1)}) vs {t2name} ({len(h2)}) — kadro yetersiz")
            continue
        s1 = [{"name": s[0], "rating": s[1], "pos": s[2], "is_starter": s[3] if len(s)>3 else 0} for s in h1]
        s2 = [{"name": s[0], "rating": s[1], "pos": s[2], "is_starter": s[3] if len(s)>3 else 0} for s in h2]
        f1, tc1 = db.get_team_tactics(t1id)
        f2, tc2 = db.get_team_tactics(t2id)
        # Antrenör bonusu — oyuncu rating'lerine ekle
        c1 = db.get_user_coach(t1id)
        c2 = db.get_user_coach(t2id)
        if c1:
            cname1, crating1, batk1, bdef1, _ = c1
            for p in s1:
                if p["pos"] in ["FWD","MID"]:
                    p["rating"] = min(99, p["rating"] + batk1 // 2)
                if p["pos"] in ["DEF","GK"]:
                    p["rating"] = min(99, p["rating"] + bdef1 // 2)
        if c2:
            cname2, crating2, batk2, bdef2, _ = c2
            for p in s2:
                if p["pos"] in ["FWD","MID"]:
                    p["rating"] = min(99, p["rating"] + batk2 // 2)
                if p["pos"] in ["DEF","GK"]:
                    p["rating"] = min(99, p["rating"] + bdef2 // 2)
        team1 = {
            "uid": t1id, "name": t1name, "squad": s1,
            "form": db.get_team_form(t1id), "fixture_id": fid, "is_derby": is_derby,
            "formation": f1, "tactic": tc1,
        }
        team2 = {
            "uid": t2id, "name": t2name, "squad": s2,
            "form": db.get_team_form(t2id), "fixture_id": fid, "is_derby": is_derby,
            "formation": f2, "tactic": tc2,
        }
        pairs.append((team1, team2))

    if not pairs:
        print("[MAÇ] ❌ Hiç oynanabilir maç yok!")
        await _notify_admin(context,
            "⚠️ *Bugün hiç maç oynanamadı!*\n_Kadrolar yetersiz veya fikstür sorunu var. /fikstur kontrol et._")
        return
    print(f"[MAÇ] {len(pairs)} maç oynanmaya başlanıyor...")
    match_results = []  # Tüm maç sonuçları

    # Açılış mesajı
    intro_text = (
        "╔══════════════════════╗\n"
        "║  ⚽  GÜNÜN MAÇLARI  ║\n"
        "╚══════════════════════╝\n\n"
        f"📅 {len(pairs)} maç oynanacak\n"
    )
    if bye_team:
        intro_text += f"🛌 *{bye_team['name']}* bu hafta dinleniyor (BYE)\n"
    intro_text += "\nMaçlar birazdan başlıyor..."

    await _send_to_broadcast_chats(context, intro_text)
    await asyncio.sleep(3)

    # Her maçı sırayla oyna
    summary = "╔══════════════════════╗\n║  📊  GÜNÜN SONUÇLARI  ║\n╚══════════════════════╝\n\n"

    for t1, t2 in pairs:
        await asyncio.sleep(2)
        # Taktik parametrelerini set et
        _live_match_simulation._t1_form   = t1.get("formation", "4-3-3")
        _live_match_simulation._t1_tactic = t1.get("tactic", "dengeli")
        _live_match_simulation._t2_form   = t2.get("formation", "4-3-3")
        _live_match_simulation._t2_tactic = t2.get("tactic", "dengeli")

        g1, g2, mvp, scorers = await _live_match_simulation(
            context,
            t1["name"], t1["squad"], t1["form"],
            t2["name"], t2["squad"], t2["form"],
        )

        # Sonuçları kaydet
        if g1 > g2:
            db.update_team_stats(t1["uid"], "win", g1, g2)
            db.update_team_stats(t2["uid"], "loss", g2, g1)
            db.update_team_form(t1["uid"], "win")
            db.update_team_form(t2["uid"], "loss")
            db.update_lc_balance(t1["uid"], 5000)
        elif g2 > g1:
            db.update_team_stats(t1["uid"], "loss", g1, g2)
            db.update_team_stats(t2["uid"], "win", g2, g1)
            db.update_team_form(t1["uid"], "loss")
            db.update_team_form(t2["uid"], "win")
            db.update_lc_balance(t2["uid"], 5000)
        else:
            db.update_team_stats(t1["uid"], "draw", g1, g2)
            db.update_team_stats(t2["uid"], "draw", g2, g1)
            db.update_team_form(t1["uid"], "draw")
            db.update_team_form(t2["uid"], "draw")
            db.update_lc_balance(t1["uid"], 2000)
            db.update_lc_balance(t2["uid"], 2000)

        # MVP ve sezon istatistikleri kaydet
        if mvp:
            mvp_uid = None
            for p in t1["squad"]:
                if p["name"] == mvp:
                    mvp_uid = t1["uid"]
                    break
            if not mvp_uid:
                for p in t2["squad"]:
                    if p["name"] == mvp:
                        mvp_uid = t2["uid"]
                        break
            if mvp_uid:
                db.record_mvp(mvp_uid, mvp)
                db.add_season_player_stat(mvp_uid, mvp, mvp=1)

        # Gol/asist istatistikleri sezon tablosuna ekle
        scorer_names = set()
        assist_names = set()
        for goal in scorers.get("team1", []):
            db.add_season_player_stat(t1["uid"], goal["player"], goals=1)
            db.update_player_after_match(t1["uid"], goal["player"], scored=1, is_mvp=(goal["player"]==mvp))
            scorer_names.add((t1["uid"], goal["player"]))
            if goal.get("assist"):
                db.add_season_player_stat(t1["uid"], goal["assist"], assists=1)
                db.update_player_after_match(t1["uid"], goal["assist"], assisted=1)
                assist_names.add((t1["uid"], goal["assist"]))
        for goal in scorers.get("team2", []):
            db.add_season_player_stat(t2["uid"], goal["player"], goals=1)
            db.update_player_after_match(t2["uid"], goal["player"], scored=1, is_mvp=(goal["player"]==mvp))
            scorer_names.add((t2["uid"], goal["player"]))
            if goal.get("assist"):
                db.add_season_player_stat(t2["uid"], goal["assist"], assists=1)
                db.update_player_after_match(t2["uid"], goal["assist"], assisted=1)
                assist_names.add((t2["uid"], goal["assist"]))

        # İlk 11'de oynayıp gol/asist atmayan oyunculara form -1 + sakatlık şansı
        injured_msgs = []
        for team_info in [t1, t2]:
            # Manuel seçilmiş starter varsa onları kullan, yoksa top 11 rating
            manual_starters = [p for p in team_info["squad"] if p.get("is_starter") == 1]
            if len(manual_starters) >= 11:
                starters = manual_starters[:11]
            else:
                starters = sorted(team_info["squad"], key=lambda x: -x["rating"])[:11]
            for p in starters:
                key = (team_info["uid"], p["name"])
                if key not in scorer_names and key not in assist_names:
                    db.update_player_after_match(team_info["uid"], p["name"], played=True)
                # Sakatlık şansı %3
                if random.random() < 0.03:
                    matches = db.injure_player(team_info["uid"], p["name"])
                    injured_msgs.append(f"🚑 *{p['name']}* sakatlandı ({matches} maç)")

        # Sakatlık duyurusu
        if injured_msgs:
            await _send_to_broadcast_chats(context, "\n".join(injured_msgs))

        # Fikstürü işaretle
        if "fixture_id" in t1:
            db.mark_fixture_played(t1["fixture_id"], g1, g2)

            # Tahminleri değerlendir
            winners = db.process_predictions(t1["fixture_id"], g1, g2)
            if winners:
                pred_text = "🎯 *TAHMİN KAZANANLARI:*\n"
                for uid_w, pg1, pg2, reward in winners[:5]:
                    pred_text += f"  • ID:`{uid_w}` ({pg1}-{pg2}) → *+{reward:,} LC*\n"
                await _send_to_broadcast_chats(context, pred_text)

        # Derbi bonusu — 2x ödül
        if t1.get("is_derby"):
            if g1 > g2:
                db.update_lc_balance(t1["uid"], 5000)  # +5K daha (toplam 10K)
            elif g2 > g1:
                db.update_lc_balance(t2["uid"], 5000)

        db.save_match(t1["uid"], t2["uid"], g1, g2, 0)

        # Hat-trick bonusu — aynı maçta 3 gol atan oyuncu
        try:
            from collections import Counter
            all_t1 = Counter(g["player"] for g in scorers.get("team1", []))
            all_t2 = Counter(g["player"] for g in scorers.get("team2", []))
            for pname, cnt in all_t1.items():
                if cnt >= 3:
                    # Form +3 ekstra (rating bonus zaten var)
                    db.update_player_after_match(t1["uid"], pname, scored=2)  # Ekstra boost
            for pname, cnt in all_t2.items():
                if cnt >= 3:
                    db.update_player_after_match(t2["uid"], pname, scored=2)
        except: pass

        # Sözleşme: ilk 11'in maç sayısını artır
        for p in t1["squad"][:11]:
            db.increment_match_played(t1["uid"], p["name"])
        for p in t2["squad"][:11]:
            db.increment_match_played(t2["uid"], p["name"])

        # Haber üret
        news = _generate_news_after_match(t1["name"], t2["name"], g1, g2, mvp, scorers, t1.get("is_derby"))
        if news:
            db.save_news(news)

        # Sonucu listeye ekle (toplu özet için)
        is_derby_match = 1 if t1.get("is_derby") else 0
        match_results.append((t1["name"], g1, t2["name"], g2, mvp, is_derby_match))

        derby_em = " 🔥" if t1.get("is_derby") else ""
        summary += f"⚽ *{t1['name'][:12]}* `{g1}-{g2}` *{t2['name'][:12]}*{derby_em}\n"

    # BYE takıma küçük teselli ödülü
    if bye_team:
        db.update_lc_balance(bye_team["uid"], 1500)
        summary += f"\n🛌 *{bye_team['name']}* BYE — +1.500 LC dinlenme primi\n"

    # Bot engelleyenleri duyur
    if removed_blocked:
        summary += f"\n🚫 *Bot Engelleyenler:*\n"
        for name in removed_blocked:
            summary += f"  • {name} (maç iptal)\n"
        summary += "💡 Yeni sezonda yeniden kayıt olmaları gerekir."

    # ── TÜM MAÇLAR BİTTİ — Toplu özet + haberler + sosyal medya ──
    if match_results:
        await asyncio.sleep(5)
        await _send_match_day_summary(context, match_results, season_no)

    # Tatil sayaçlarını azalt
    try: db.decrement_vacations()
    except: pass

    # Kiralık süreleri azalt, biten kiralıkları sahibine geri ver
    expired_loans = db.decrement_loans()
    if expired_loans:
        for owner_id, renter_id, pname in expired_loans:
            # Renter\'dan oyuncuyu geri al
            squad_r = db.get_squad(renter_id)
            target = next((s for s in squad_r if s[0] == pname), None)
            if target:
                db.add_player_to_squad(owner_id, pname, target[1], target[2])
                db.remove_player_from_squad(renter_id, pname)
            try:
                await context.bot.send_message(
                    chat_id=owner_id,
                    text=f"🔄 *Kiralık bitti!* {pname} takımına geri döndü.",
                    parse_mode="Markdown")
                await context.bot.send_message(
                    chat_id=renter_id,
                    text=f"🔄 *Kiralık sona erdi!* {pname} sahibinin takımına döndü.",
                    parse_mode="Markdown")
            except: pass

    # Sözleşme talepleri kontrol et
    wants_leave = db.check_contract_demands()
    if wants_leave:
        # Sahiplerine DM gönder
        from collections import defaultdict
        by_user = defaultdict(list)
        for uid_t, pname in wants_leave:
            by_user[uid_t].append(pname)
        for uid_t, names in by_user.items():
            msg = "📨 *KADRONDAN AYRILMA TALEPLERİ*\n\n"
            for n in names:
                msg += f"  • *{n}* takımdan ayrılmak istiyor\n"
            msg += "\n💡 `/sat <oyuncu>` ile satabilir veya beklemeye devam edebilirsin."
            try:
                await context.bot.send_message(chat_id=uid_t, text=msg, parse_mode="Markdown")
            except: pass

    # MVP haftalık duyurusu
    weekly_mvp = db.get_weekly_mvp()
    if weekly_mvp:
        summary += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        summary += f"⭐ *Bu Hafta MVP:* _{weekly_mvp[0]}_ ({weekly_mvp[1]} maç)"

    summary += "\n\n💡 `/lig_top` ile sıralamayı gör!"
    await _send_to_broadcast_chats(context, summary)

    # 5 dakika sonra lig haberleri otomatik gönder
    await asyncio.sleep(300)  # 5 dakika
    recent_news = db.get_recent_news(8)
    if recent_news:
        news_text = (
            "╔══════════════════════╗\n"
            "║  📰  GÜNÜN LİG HABERLERİ  ║\n"
            "╚══════════════════════╝\n\n"
        )
        for news_date, content_news in recent_news:
            news_text += f"• {content_news}\n\n"
        news_text += "📋 `/haberler` ile geçmiş haberleri gör"
        await _send_to_broadcast_chats(context, news_text)

async def season_check_job(context):
    """Sezonun bitip bitmediğini kontrol et, bittiyse ödülleri dağıt.
    Sezon biter:
      1. Belirlenen sezon tarihi geçince
      2. Tüm fikstür oynanınca (her takım tüm maçlarını tamamlayınca)
    """
    from datetime import datetime
    season = db.get_active_season()
    if not season:
        new_season_info = db.create_new_season()
    # Yeni sezon zengin duyuruları
    try:
        await _post_new_season_announcements(context, new_season_info, season_no)
    except Exception as e:
        print(f"[YENİ SEZON] duyuru hatası: {e}")
        return

    season_no, start_date, end_date = season
    end_dt = datetime.fromisoformat(end_date)

    # Tarih kontrolü
    time_ended = datetime.now() >= end_dt

    # Fikstür kontrolü — tüm maçlar oynandı mı?
    fixtures_done = False
    try:
        unplayed = db.count_unplayed_fixtures(season_no)
        played = db.count_played_fixtures(season_no)
        total = unplayed + played
        if total > 0 and unplayed == 0:
            fixtures_done = True
            print(f"[SEZON] ⚽ Tüm fikstür oynandı! ({played}/{total})")
        else:
            print(f"[SEZON] Fikstür: {played}/{total} oynandı, {unplayed} kaldı")
    except Exception as e:
        print(f"[SEZON] fikstür kontrol hatası: {e}")

    # Sezon bitiş şartı
    if not time_ended and not fixtures_done:
        return  # Henüz bitmedi

    # Sezon bitti — ödülleri dağıt
    rankings = db.get_all_teams_ranked()
    if not rankings:
        db.create_new_season()
        return

    # Ödül havuzu: 3.5M LC
    rewards = {
        1: 1_750_000,  # 50%
        2: 950_000,    # 27%
        3: 450_000,    # 13%
    }
    # 4-10 için 50K her biri
    for i in range(4, 11):
        rewards[i] = 50_000

    reason = "📅 Süre doldu" if time_ended else "⚽ Tüm fikstür oynandı"
    text = (
        "╔══════════════════════╗\n"
        "║  🏆  SEZON BİTTİ!  ║\n"
        "╚══════════════════════╝\n\n"
        f"📅 *Sezon {season_no}* sona erdi!\n"
        f"_{reason}_\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏆 *FİNAL SIRALAMA*\n\n"
    )

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, t in enumerate(rankings[:10], 1):
        uid_t, name, w, d, l, gf, ga, pts = t
        reward = rewards.get(i, 0)
        if reward > 0:
            db.update_lc_balance(uid_t, reward)
        db.record_champion(season_no, i, uid_t, name, pts, w, gf, reward)

        em = medals.get(i, f"{i}.")
        reward_str = f" — *+{reward:,} LC*" if reward > 0 else ""
        text += f"{em} *{name}* `{pts}` puan{reward_str}\n"

    # Gol Kralı ödülü
    top_scorer = db.get_top_scorer()
    if top_scorer:
        scorer_uid, scorer_name, goals = top_scorer
        db.update_lc_balance(scorer_uid, 200_000)
        text += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"⚽ *GOL KRALI:* _{scorer_name}_ ({goals} gol)\n"
        text += f"   💎 +*200.000 LC* ödülü kazandı!\n"

    # Sezon MVP ödülü
    season_mvp = db.get_season_mvp()
    if season_mvp:
        mvp_uid, mvp_name, mvp_count = season_mvp
        db.update_lc_balance(mvp_uid, 150_000)
        text += f"\n⭐ *SEZON MVP:* _{mvp_name}_ ({mvp_count} kez)\n"
        text += f"   💎 +*150.000 LC* ödülü kazandı!\n"

    text += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💰 *Toplam dağıtılan:* 3.5M LC\n"
    text += f"🆕 Yeni sezon başlıyor! Takım istatistikleri sıfırlandı.\n"

    # İstatistikleri sıfırla, yeni sezon başlat
    # Antrenörleri sezon sonunda serbest bırak
    try:
        db.release_all_coaches()
    except: pass

    # Terfi/düşme uygula
    actions = db.promote_relegate_teams()
    if actions:
        text += "\n\n🏆 *TERFİ/DÜŞME*\n"
        for uid, name, from_t, to_t, reason in actions[:10]:
            em = "⬆️" if reason == "promote" else "⬇️"
            text += f"{em} *{name}*: {db.LEAGUE_TIERS[from_t]['name']} → {db.LEAGUE_TIERS[to_t]['name']}\n"

    db.reset_all_team_stats()
    new_no, start_dt, _ = db.create_new_season()

    # Yeni sezonun fikstürünü oluştur
    new_teams = db.get_all_teams_ranked()
    if len(new_teams) >= 2:
        team_ids = [t[0] for t in new_teams]
        fixture_count = db.generate_fixtures(new_no, team_ids, start_dt)
        text += f"\n📅 *{fixture_count}* maçlık fikstür oluşturuldu!"

    text += f"\n🏁 *Sezon {new_no}* başladı! Yarış yeniden başlıyor!"

    await _send_to_broadcast_chats(context, text)

async def cmd_lig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lig ana ekranı."""
    uid = update.effective_user.id
    db.register_user(uid, update.effective_user.first_name)
    team = db.get_team(uid)

    if not team:
        return await update.message.reply_text(
            "╔══════════════════════╗\n"
            "║  🏟️  TÜRK BUDUN LİGİ  ║\n"
            "╚══════════════════════╝\n\n"
            "👋 Hoş geldin! Henüz bir takımın yok.\n\n"
            "🚀 Başlamak için:\n"
            "`/takim_kur <takim_ismi>`\n"
            "Örnek: `/takim_kur Galatasaray`\n\n"
            "💎 Başlangıçta *500.000 Legend Coin* sana verilir!\n"
            "🛒 `/market` ile oyuncu satın al\n"
            "📅 Her gün 21:00'da maçlar yapılır",
            parse_mode="Markdown")

    from datetime import datetime
    name, lc, formation, w, d, l, gf, ga = team
    points = w*3 + d
    games_played = w + d + l
    squad = db.get_squad(uid)

    # Sezon bilgisi
    season = db.get_active_season()
    season_info = ""
    if season:
        season_no, start_date, end_date = season
        end_dt = datetime.fromisoformat(end_date)
        remaining = end_dt - datetime.now()
        days = remaining.days
        hours = remaining.seconds // 3600
        if days >= 0:
            season_info = f"\n🏆 *Sezon {season_no}* — Kalan: *{days}g {hours}s*\n"
        else:
            season_info = f"\n🏆 *Sezon {season_no}* — Yakında bitiyor!\n"

        # Fikstürde mi kontrol et
        if not db.is_team_in_active_fixtures(uid):
            season_info += "🕓 *Sonraki sezona kayıtlısın!* Mevcut sezona dahil değilsin.\n"
            season_info += "💡 Bu sezonda market\'ten oyuncu al, kadronu hazırla. Yeni sezon başlayınca otomatik dahil olacaksın!\n"

    await update.message.reply_text(
        f"╔══════════════════════╗\n"
        f"║  🏟️  {name[:18]}  ║\n"
        f"╚══════════════════════╝\n"
        f"{season_info}\n"
        f"💎 Legend Coin: *{lc:,}*\n"
        f"📐 Formasyon: *{formation}*\n"
        f"👥 Kadro: *{len(squad)}/15* oyuncu\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *SEZON İSTATİSTİKLERİ*\n"
        f"🏆 Puan: *{points}* | Maç: *{games_played}*\n"
        f"✅ G: *{w}* | ➖ B: *{d}* | ❌ M: *{l}*\n"
        f"⚽ Atılan: *{gf}* | Yenilen: *{ga}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *KOMUTLAR*\n"
        f"`/takimim` — Kadronu gör\n"
        f"`/market` — Transfer marketi\n"
        f"`/lig_top` — Lig sıralaması\n"
        f"`/sampiyonlar` — Şampiyon geçmişi\n"
        f"`/kur` — Legend Coin kuru",
        parse_mode="Markdown")

async def cmd_takim_kur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db.register_user(uid, update.effective_user.first_name)

    if not context.args:
        return await update.message.reply_text(
            "💡 Kullanım: `/takim_kur <takim_ismi>`\n"
            "Örnek: `/takim_kur Budun FC`",
            parse_mode="Markdown")

    team_name = " ".join(context.args)[:30]
    if db.get_team(uid):
        return await update.message.reply_text("❌ Zaten bir takımın var! `/takimim` ile gör.", parse_mode="Markdown")

    # ÖNCE: Bot kullanıcıya DM atabiliyor mu kontrol et
    dm_ok = False
    try:
        test_msg = await context.bot.send_message(
            chat_id=uid,
            text="🤝 *Bot bağlantısı kuruldu!*\n\nArtık maç hatırlatmaları ve özel bilgiler alabilirsin.",
            parse_mode="Markdown")
        dm_ok = True
    except Exception:
        dm_ok = False

    if not dm_ok:
        return await update.message.reply_text(
            "⚠️ *Bot sana DM atamıyor!*\n\n"
            "Takımını kurabilmen için önce bota özel mesaj atman gerek:\n\n"
            "1️⃣ @cmhryteglencebot yaz\n"
            "2️⃣ */start* komutuyla bot'u aç\n"
            "3️⃣ Sonra buraya gel, tekrar `/takim_kur` yaz\n\n"
            "_Bu zorunlu çünkü maç hatırlatmaları, sakatlık bildirimleri vs. DM olarak gelir._",
            parse_mode="Markdown")

    db.create_team(uid, team_name)

    # Sezon ortasında mı katıldı kontrol et
    season = db.get_active_season()
    extra = ""
    if season:
        from datetime import datetime
        season_no, start_date, end_date = season
        start_dt = datetime.fromisoformat(start_date)
        days_since_start = (datetime.now() - start_dt).days
        if days_since_start >= 1:  # 1+ gün geçmiş
            extra = (
                f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🕓 *Sonraki sezona kayıtlısın!*\n"
                f"📅 Aktif sezon {days_since_start} gündür devam ediyor.\n"
                f"💡 Bu sezonda hazırlık yap:\n"
                f"  • `/market` ile oyuncu al\n"
                f"  • Kadronu güçlendir\n"
                f"  • Yeni sezon başlayınca otomatik fikstüre dahil olacaksın!\n"
            )

    await update.message.reply_text(
        f"╔══════════════════════╗\n"
        f"║  🎉  TAKIM KURULDU  ║\n"
        f"╚══════════════════════╝\n\n"
        f"⚽ Takım: *{team_name}*\n"
        f"💎 Başlangıç bütçesi: *500.000 LC*\n\n"
        f"🛒 Şimdi `/market` yazıp oyuncu satın al!\n"
        f"📐 11 ilk 11 + 4 yedek oyuncuya ihtiyacın var."
        f"{extra}",
        parse_mode="Markdown")

async def cmd_takimim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce `/takim_kur <isim>` ile takım kur!", parse_mode="Markdown")

    name, lc, formation, w, d, l, gf, ga = team
    owner_name = db.get_owner_username(uid)
    squad = db.get_squad(uid)

    if not squad:
        return await update.message.reply_text(
            f"📋 *{name}* — Kadron boş!\n💡 `/market` ile oyuncu satın al.",
            parse_mode="Markdown")

    # Mevkilere göre grupla
    by_pos = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p_name, rating, pos, starter in squad:
        if pos in by_pos:
            by_pos[pos].append((p_name, rating))

    pos_emoji = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}
    pos_name  = {"GK": "Kaleciler", "DEF": "Defans", "MID": "Orta Saha", "FWD": "Forvet"}

    # Detaylı kadro (form + sakatlık)
    detailed = db.get_squad_detailed(uid)
    detail_map = {d[0]: d for d in detailed}  # name -> (name, rating, base_rating, pos, form, injury)

    text = f"📋 *{name}* — Kadro ({len(squad)}/15)\n"
    text += f"👤 Sahip: *{owner_name}*\n"
    text += f"📐 Formasyon: *{formation}* | 💎 *{lc:,} LC*\n\n"

    for pos in ["GK", "DEF", "MID", "FWD"]:
        players = by_pos[pos]
        if not players: continue
        text += f"{pos_emoji[pos]} *{pos_name[pos]}* ({len(players)})\n"
        for p_name, rating in players:
            # Form ve sakatlık bilgisi
            d = detail_map.get(p_name)
            extras = ""
            if d:
                _, _, base_r, _, form, injury = d
                if injury > 0:
                    extras = f" 🚑 *{injury} maç*"
                elif form >= 3:
                    extras = " 🔥"
                elif form <= -3:
                    extras = " 😴"
            text += f"  • {p_name} — `{rating}`{extras}\n"
        text += "\n"

    avg_rating = sum(p[1] for p in squad) // len(squad) if squad else 0
    form = db.get_team_form(uid)
    form_emoji = "🔥" if form >= 3 else "📈" if form > 0 else "📉" if form < 0 else "➡️"
    form_text = f"+{form}" if form > 0 else str(form)

    text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"⭐ Ortalama: *{avg_rating}*\n"
    text += f"{form_emoji} Form: *{form_text}* (son 5 maç)\n"
    text += f"\n💡 İlk 11: En yüksek rating'li 11 oyuncu otomatik seçilir"

    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm oyuncuların form durumu."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    detailed = db.get_squad_detailed(uid)
    if not detailed:
        return await update.message.reply_text("❌ Kadron boş!")

    text = (
        "╔══════════════════════╗\n"
        "║  📈  KADRO FORMU  ║\n"
        "╚══════════════════════╝\n\n"
    )

    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}

    # Pozisyona göre grupla
    by_pos = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for d in detailed:
        pname, rating, base_rating, pos, form, injury = d
        if pos in by_pos:
            by_pos[pos].append(d)

    for pos in ["GK", "DEF", "MID", "FWD"]:
        players = by_pos[pos]
        if not players: continue
        text += f"{pos_em[pos]} *{pos}*\n"
        for d in players:
            pname, rating, base_rating, pos, form, injury = d
            # Form emoji
            if injury > 0:
                form_em = f"🚑 {injury} maç"
            elif form >= 4:
                form_em = "🔥🔥 Süper form"
            elif form >= 2:
                form_em = "🔥 Formda"
            elif form >= 0:
                form_em = "➡️ Normal"
            elif form >= -2:
                form_em = "📉 Düşük"
            else:
                form_em = "😴 Formsuz"

            text += f"  • {pname} `{rating}` — {form_em}\n"
        text += "\n"

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *İPUÇLARI*\n"
        "• Gol/asist atan: form artar\n"
        "• Oynamayan: form düşer\n"
        "• `/antrenman` ile gelişimi hızlandır"
    )

    await update.message.reply_text(text, parse_mode="Markdown")

# ─────────────────────────────────────────────────────────────
# SOSYAL MEDYA
# ─────────────────────────────────────────────────────────────

async def cmd_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce `/takim_kur <isim>` ile takım kur!", parse_mode="Markdown")

    # Filtre: pozisyon veya arama
    search_query = None
    if context.args and context.args[0].upper() in ["GK", "DEF", "MID", "FWD"]:
        pos = context.args[0].upper()
        all_players = lig.get_players_by_position(pos, 999)
        pos_name = {"GK": "Kaleciler", "DEF": "Defans", "MID": "Orta Saha", "FWD": "Forvet"}[pos]
        title = f"🛒 *{pos_name} Marketi*"
    elif context.args:
        # Oyuncu ismi arama
        search_query = " ".join(context.args).lower()
        all_players = [p for p in lig.PLAYERS if search_query in p["name"].lower()]
        title = f"🔍 *Arama: {' '.join(context.args)}*"
    else:
        all_players = sorted(lig.PLAYERS, key=lambda x: -x["rating"])
        title = "🛒 *TRANSFER MARKETİ*"

    lc = team[1]

    # Sahipsiz oyuncuları filtrele ve listele
    available = []
    owned_count = 0
    for p in all_players:
        owner_id = db.is_player_owned(p["name"])
        if owner_id is None:
            available.append(p)
        elif owner_id == uid:
            pass  # Zaten kadroda, gösterme
        else:
            owned_count += 1

    if not available:
        return await update.message.reply_text(
            f"😔 *Müsait oyuncu yok!*\n\n"
            f"Bu pozisyondaki tüm oyuncular başka takımlarda.\n"
            f"💡 `/pazar` ile diğer takımların ilanlarına bak.",
            parse_mode="Markdown")

    # İlk 25'i göster
    show = available[:25]
    text = f"{title}\n💎 Bütçen: *{lc:,} LC*"
    if owned_count > 0:
        text += f" | 🔒 {owned_count} oyuncu başka takımda\n\n"
    else:
        text += "\n\n"

    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}
    for p in show:
        price = lig.get_player_price(p["rating"])
        afford = "✅" if lc >= price else "❌"
        text += f"{afford} {pos_em[p['pos']]} *{p['name']}* `{p['rating']}` — `{price:,}`\n"

    if len(available) > 25:
        text += f"\n_...ve {len(available)-25} oyuncu daha_\n"

    text += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    text += "💡 `/transfer <oyuncu adı>` ile satın al\n"
    text += "🔍 `/market GK/DEF/MID/FWD` pozisyon filtresi\n"
    text += "🔍 `/market messi` isim araması"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce `/takim_kur <isim>` ile takım kur!", parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text("💡 Kullanım: `/transfer <oyuncu_adi>`", parse_mode="Markdown")

    player_name = " ".join(context.args)
    player = lig.get_player_by_name(player_name)
    if not player:
        return await update.message.reply_text(
            f"❌ *{player_name}* bulunamadı.\n💡 `/market` ile listeyi gör veya ismi kontrol et.",
            parse_mode="Markdown")

    # ── BENZERSİZ SAHİPLİK KONTROLÜ ──
    owner_id = db.is_player_owned(player["name"])
    if owner_id and owner_id != uid:
        owner_team = db.get_team(owner_id)
        owner_name = db.get_owner_username(owner_id)
        owner_team_name = owner_team[0] if owner_team else "Bilinmeyen Takım"
        return await update.message.reply_text(
            f"🔒 *{player['name']}* başka bir takımda!\n\n"
            f"👤 Sahibi: *{owner_name}* ({owner_team_name})\n\n"
            f"💡 Bu oyuncuyu almak için:\n"
            f"  • Sahibine `/teklif` yap\n"
            f"  • Veya `/market` ile başka oyuncu bak",
            parse_mode="Markdown")

    if owner_id == uid:
        return await update.message.reply_text(f"❌ *{player['name']}* zaten kadronda!", parse_mode="Markdown")

    price = lig.get_player_price(player["rating"])
    lc = team[1]

    if lc < price:
        return await update.message.reply_text(
            f"❌ Yetersiz LC!\n💎 Fiyat: *{price:,}* | Mevcut: *{lc:,}*",
            parse_mode="Markdown")

    squad = db.get_squad(uid)
    if len(squad) >= 15:
        return await update.message.reply_text("❌ Kadron dolu! (15/15) Önce birini sat.", parse_mode="Markdown")

    success = db.add_player_to_squad(uid, player["name"], player["rating"], player["pos"])
    if not success:
        return await update.message.reply_text(f"❌ *{player['name']}* zaten kadronda!", parse_mode="Markdown")

    db.update_lc_balance(uid, -price)
    new_balance = db.get_lc_balance(uid)

    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}[player["pos"]]
    await update.message.reply_text(
        f"✅ *TRANSFER BAŞARILI!*\n\n"
        f"{pos_em} *{player['name']}* (`{player['rating']}`)\n"
        f"💸 Ödenen: *{price:,} LC*\n"
        f"💎 Yeni bütçe: *{new_balance:,} LC*\n"
        f"👥 Kadro: *{len(squad)+1}/15*\n\n"
        f"🔒 Bu oyuncu artık sadece senin takımında!",
        parse_mode="Markdown")

    # Transfer haberi (rating 85+)
    if player["rating"] >= 85:
        team_data = db.get_team(uid)
        team_name = team_data[0] if team_data else "Bilinmeyen"
        news = (
            f"💼 *TRANSFER BOMBASI!*\n\n"
            f"{pos_em} *{player['name']}* ({player['rating']}) → *{team_name}*\n"
            f"💰 Bonservis: *{price:,} LC*\n\n"
            f"_Ligin yeni yıldızı kim olacak?_"
        )
        try:
            db.save_news(f"💼 {player['name']} ({player['rating']}) → {team_name} ({price:,} LC)")
            await _send_to_broadcast_chats(context, news, category="lig")
        except: pass

async def cmd_sat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text("💡 Kullanım: `/sat <oyuncu_adi>`", parse_mode="Markdown")

    player_name = " ".join(context.args)
    # Kadrodaki oyuncuyu bul
    squad = db.get_squad(uid)
    target = None
    for p_name, rating, pos, starter in squad:
        if player_name.lower() in p_name.lower():
            target = (p_name, rating, pos)
            break

    if not target:
        return await update.message.reply_text(f"❌ *{player_name}* kadronda yok!", parse_mode="Markdown")

    p_name, rating, pos = target
    sale_price = int(lig.get_player_price(rating) * 0.7)  # %70 değerinde satılır

    db.remove_player_from_squad(uid, p_name)
    db.update_lc_balance(uid, sale_price)

    await update.message.reply_text(
        f"💸 *{p_name}* satıldı!\n"
        f"💎 Kazanılan: *{sale_price:,} LC* (%70)\n"
        f"💼 Yeni bütçe: *{db.get_lc_balance(uid):,}*",
        parse_mode="Markdown")

    # Önemli oyuncu sat haberi (rating 85+)
    if rating >= 85:
        team_data = db.get_team(uid)
        team_name = team_data[0] if team_data else "Bilinmeyen"
        try:
            db.save_news(f"📤 *{team_name}* yıldız oyuncusu {p_name} ({rating})'i sattı")
            news = (
                f"📤 *YILDIZ AYRILDI!*\n\n"
                f"*{p_name}* ({rating}) — *{team_name}* takımından ayrıldı.\n"
                f"💰 Bonservis: *{sale_price:,} LC*"
            )
            await _send_to_broadcast_chats(context, news, category="lig")
        except: pass

async def cmd_akademi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Akademi — ucuz genç oyuncular."""
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    players = db.get_academy_players()
    if not players:
        return await update.message.reply_text("❌ Akademide oyuncu yok, yarın tekrar dene.")

    lc = team[1]
    text = (
        "╔══════════════════════╗\n"
        "║  🎓  AKADEMİ  ║\n"
        "╚══════════════════════╝\n\n"
        f"💎 Bütçen: *{lc:,} LC*\n"
        f"✨ Genç oyuncular — %70 indirimli!\n"
        f"📅 Her gün yenilenir\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}
    for aid, name, rating, pos, price in players:
        afford = "✅" if lc >= price else "❌"
        text += f"{afford} {pos_em[pos]} *{name}* `{rating}` — `{price:,}` LC\n"
        text += f"   `/akademi_al {aid}`\n"

    text += "\n💡 Genç oyuncular antrenmanla daha hızlı gelişir!"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_akademi_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Akademi oyuncusu satın al."""
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text("💡 Kullanım: `/akademi_al <id>`", parse_mode="Markdown")

    try:
        aid = int(context.args[0])
    except:
        return await update.message.reply_text("❌ Geçerli ID girin.")

    result = db.buy_youth_player(aid, uid)
    if not result:
        return await update.message.reply_text("❌ Oyuncu bulunamadı veya satılmış.")

    name, rating, pos, price = result
    lc = db.get_lc_balance(uid)
    if lc < price:
        return await update.message.reply_text(f"❌ Yetersiz LC! Mevcut: *{lc:,}*", parse_mode="Markdown")

    squad = db.get_squad(uid)
    if len(squad) >= 15:
        return await update.message.reply_text("❌ Kadron dolu!", parse_mode="Markdown")

    db.add_player_to_squad(uid, name, rating, pos)
    db.update_lc_balance(uid, -price)

    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}[pos]
    await update.message.reply_text(
        f"✅ *AKADEMİ TRANSFERİ!*\n\n"
        f"{pos_em} *{name}* (`{rating}`)\n"
        f"💸 Ödenen: *{price:,} LC*\n"
        f"💎 Yeni bütçe: *{lc-price:,}*\n\n"
        f"💡 Genç yetenek! Antrenmanla geliştir.",
        parse_mode="Markdown")

async def cmd_antren(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyuncuyu antrene et — günde max 2, %5 sakatlık riski."""
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    if not context.args:
        used = db.get_training_count_today(uid)
        remaining = db.DAILY_TRAINING_LIMIT - used
        return await update.message.reply_text(
            f"💡 Kullanım: `/antrenman <oyuncu_adı>`\n\n"
            f"📊 Bugünkü antrenman: *{used}/{db.DAILY_TRAINING_LIMIT}*\n"
            f"⚡ Kalan: *{remaining}*\n\n"
            f"🎯 *RATING'E GÖRE ETKİ:*\n"
            f"  • Akademi (<75): %75 gelişim, %3 sakatlık\n"
            f"  • Orta (75-84): %50 gelişim, %5 sakatlık\n"
            f"  • Yıldız (85-92): %30 gelişim, %7 sakatlık\n"
            f"  • Süper (93+): %15 gelişim, %10 sakatlık\n\n"
            f"🌟 *MAX 99* — Bu seviyeye ulaşan oyuncu artık gelişmez!\n"
            f"_Max'taki oyuncuyu antrene etmek hakkını tüketmez._",
            parse_mode="Markdown")

    used = db.get_training_count_today(uid)
    if used >= db.DAILY_TRAINING_LIMIT:
        return await update.message.reply_text(
            f"❌ Bugün için antrenman hakkın bitti! ({used}/{db.DAILY_TRAINING_LIMIT})\n"
            f"⏰ Yarın yeniden 2 antrenman yapabilirsin.",
            parse_mode="Markdown")

    player_name = " ".join(context.args)
    # Kadrosunda var mı?
    squad = db.get_squad(uid)
    target = None
    for p_name, rating, pos, starter in squad:
        if player_name.lower() in p_name.lower():
            target = p_name
            break

    if not target:
        return await update.message.reply_text(f"❌ *{player_name}* kadronda yok!", parse_mode="Markdown")

    result, value = db.train_player(uid, target)
    if result == "max":
        # Antrenman hakkı tüketilmedi
        return await update.message.reply_text(
            f"🌟 *MAX SEVİYE!*\n\n"
            f"⭐ *{target}* zaten zirvede! (rating: *99*)\n"
            f"_Antrenman hakkın korundu._\n\n"
            f"💡 Bu oyuncu daha fazla gelişemez, yedeklerini geliştir!",
            parse_mode="Markdown")

    db.increment_training_count(uid)

    if result == "injury":
        await update.message.reply_text(
            f"🚑 *Felaket!*\n\n"
            f"❌ *{target}* antrenmanda sakatlandı!\n"
            f"⏰ {value} maç oynayamayacak.\n"
            f"📊 Antrenman: *{used+1}/{db.DAILY_TRAINING_LIMIT}*",
            parse_mode="Markdown")
    elif result == "max_reached":
        await update.message.reply_text(
            f"🎆 *MAX SEVİYEYE ULAŞTI!*\n\n"
            f"🌟 *{target}* → *99* (+1)\n"
            f"_Daha fazla gelişim mümkün değil — efsane oyuncu!_\n\n"
            f"📊 Antrenman: *{used+1}/{db.DAILY_TRAINING_LIMIT}*",
            parse_mode="Markdown")
    elif result == "improved":
        await update.message.reply_text(
            f"💪 *Gelişme var!*\n\n"
            f"⭐ *{target}* → rating: *{value}* (+1)\n"
            f"📊 Antrenman: *{used+1}/{db.DAILY_TRAINING_LIMIT}*",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"⚙️ *{target}* antrenman yaptı ama gelişim olmadı.\n"
            f"📊 Antrenman: *{used+1}/{db.DAILY_TRAINING_LIMIT}*\n\n"
            f"💡 Yüksek rating'li oyuncular daha zor gelişir!",
            parse_mode="Markdown")

async def cmd_antrenor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Antrenör marketi."""
    uid = update.effective_user.id
    try:
        if not db.get_team(uid):
            return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

        my_coach = db.get_user_coach(uid)
        coaches = db.get_coach_market()
    except Exception as e:
        import traceback
        print(f"[ANTRENOR HATA] {e}\n{traceback.format_exc()}")
        return await update.message.reply_text(f"❌ Antrenör marketi hatası: `{type(e).__name__}: {e}`", parse_mode="Markdown")

    text = (
        "╔══════════════════════╗\n"
        "║  👔  ANTRENÖR MARKETİ  ║\n"
        "╚══════════════════════╝\n\n"
    )

    if my_coach:
        cname, crating, batk, bdef, hired = my_coach
        text += f"✅ *Mevcut hocan:* *{cname}* (`{crating}`)\n"
        text += f"   ⚔️ +{batk} hücum | 🛡️ +{bdef} defans\n"
        text += f"   📅 Sezon sonu sözleşme biter\n\n"
        text += "_💡 `/hoca_birak` ile şimdi salabilirsin_\n\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n"

    if coaches:
        text += "📋 *SATILIK HOCALAR* (ilk gelen alır)\n\n"
        for cid, name, rating, batk, bdef, cost in coaches:
            text += f"👔 *{name}* (`{rating}`) — *{cost:,} LC*\n"
            text += f"   ⚔️ +{batk} | 🛡️ +{bdef}\n"
            text += f"   `/hoca_tut {cid}`\n\n"
        text += "_📅 Her gün yenilenir_\n"
        text += "_💡 1 takıma 1 hoca, ilk gelen alır_"
    else:
        text += "_Bugün hoca yok, yarın kontrol et._"

    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_hoca_tut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Antrenör tut."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")
    if not context.args:
        return await update.message.reply_text("💡 `/hoca_tut <id>`", parse_mode="Markdown")
    try:
        mid = int(context.args[0])
    except:
        return await update.message.reply_text("❌ Geçerli ID.")

    # Mevcut hoca kontrolü
    if db.get_user_coach(uid):
        return await update.message.reply_text(
            "❌ Zaten hocan var! Önce `/hoca_birak` ile sal.",
            parse_mode="Markdown")

    # Fiyat kontrolü
    coaches = db.get_coach_market()
    target = next((c for c in coaches if c[0] == mid), None)
    if not target:
        return await update.message.reply_text("❌ Hoca yok veya tutuldu.")
    _, name, rating, batk, bdef, cost = target

    if db.get_lc_balance(uid) < cost:
        return await update.message.reply_text(
            f"❌ Yetersiz LC! Gerekli: *{cost:,}*", parse_mode="Markdown")

    result = db.hire_coach(mid, uid)
    if result == "has_coach":
        return await update.message.reply_text("❌ Zaten hocan var.")
    if not result:
        return await update.message.reply_text("❌ Hoca yok.")

    db.update_lc_balance(uid, -cost)
    name, rating, batk, bdef, cost = result

    # Sosyal medya tepkisi
    team = db.get_team(uid)
    if team:
        try:
            db.post_social_reaction(team[0], name, "positive")
            news = f"👔 *YENİ HOCA!* *{name}* (`{rating}`) artık *{team[0]}* takımında!"
            db.save_news(news)
            await _send_to_broadcast_chats(context, news, category="lig")
        except: pass

    await update.message.reply_text(
        f"✅ *Hoca tutuldu!*\n\n"
        f"👔 *{name}* (`{rating}`)\n"
        f"⚔️ +{batk} hücum | 🛡️ +{bdef} defans\n"
        f"💸 Ödenen: *{cost:,} LC*\n\n"
        f"_Sezon sonu sözleşme biter, yenilenir._",
        parse_mode="Markdown")

async def cmd_hoca_birak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mevcut hocayı sal."""
    uid = update.effective_user.id
    if not db.get_user_coach(uid):
        return await update.message.reply_text("❌ Hocan yok zaten.")
    db.release_coach(uid)
    await update.message.reply_text("✅ Hoca salındı. Yeni hoca tutabilirsin.", parse_mode="Markdown")

# ─────────────────────────────────────────────────────────────
# FORM EKRANI
# ─────────────────────────────────────────────────────────────

async def cmd_fizyo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fizyo seansı: form +2 garantili, 10K LC."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    status = db.get_form_action_status(uid)
    if not context.args:
        return await update.message.reply_text(
            f"💆 *FİZYO SEANSI*\n\n"
            f"💡 Kullanım: `/fizyo <oyuncu>`\n\n"
            f"📊 *DURUM*\n"
            f"  • Bugün: {status['fizyo_used']}/{status['fizyo_limit']}\n"
            f"  • Maliyet: *{db.FIZYO_COST:,} LC*\n"
            f"  • Etki: Form *+2* (garantili)",
            parse_mode="Markdown")

    name_query = " ".join(context.args)
    player = _find_player_in_squad(uid, name_query)
    if not player:
        return await update.message.reply_text(f"❌ *{name_query}* kadronda yok!", parse_mode="Markdown")

    pname, rating, pos = player
    if db.get_lc_balance(uid) < db.FIZYO_COST:
        return await update.message.reply_text(f"❌ Yetersiz LC! Gerekli: *{db.FIZYO_COST:,}*", parse_mode="Markdown")

    result = db.do_fizyo(uid, pname)
    if result == "limit":
        return await update.message.reply_text(
            f"❌ Bugün limit doldu! ({db.DAILY_FIZYO_LIMIT}/{db.DAILY_FIZYO_LIMIT})", parse_mode="Markdown")
    if result is None:
        return await update.message.reply_text("❌ Bir hata oluştu.")

    db.update_lc_balance(uid, -db.FIZYO_COST)
    await update.message.reply_text(
        f"💆 *FİZYO TAMAM!*\n\n"
        f"⭐ *{pname}*\n"
        f"📈 Yeni form: *{result:+d}*\n"
        f"💸 Ödenen: *{db.FIZYO_COST:,} LC*",
        parse_mode="Markdown")

async def cmd_motivasyon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Motivasyon konuşması: ücretsiz, rastgele etki."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    status = db.get_form_action_status(uid)
    if not context.args:
        return await update.message.reply_text(
            f"🗣️ *MOTİVASYON KONUŞMASI*\n\n"
            f"💡 Kullanım: `/motivasyon <oyuncu>`\n\n"
            f"📊 *DURUM*\n"
            f"  • Bugün: {status['motivasyon_used']}/{status['motivasyon_limit']}\n"
            f"  • Maliyet: *ÜCRETSİZ*\n\n"
            f"🎲 *ETKİ (Rastgele)*\n"
            f"  ✅ %50: Form +1\n"
            f"  ➡️ %30: Değişmez\n"
            f"  ❌ %20: Form -1 (ters tepki)",
            parse_mode="Markdown")

    name_query = " ".join(context.args)
    player = _find_player_in_squad(uid, name_query)
    if not player:
        return await update.message.reply_text(f"❌ *{name_query}* kadronda yok!", parse_mode="Markdown")

    pname, rating, pos = player
    result, new_form = db.do_motivation(uid, pname)
    if result == "limit":
        return await update.message.reply_text(
            f"❌ Bugün motivasyon limiti doldu! ({db.DAILY_MOTIVATION_LIMIT}/{db.DAILY_MOTIVATION_LIMIT})",
            parse_mode="Markdown")

    if result == "iyi":
        msg = (f"🔥 *İLHAM GELDİ!*\n\n"
               f"⭐ *{pname}* motivasyondan etkilendi!\n"
               f"📈 Form: *{new_form:+d}* (+1)")
    elif result == "notr":
        msg = (f"😐 *DİKKATLE DİNLEDİ*\n\n"
               f"⭐ *{pname}* etkilenmiş gibi durdu ama form değişmedi.\n"
               f"📊 Form: *{new_form:+d}*")
    else:
        msg = (f"😤 *TERS TEPKİ!*\n\n"
               f"❌ *{pname}* sözlerini hor karşıladı!\n"
               f"📉 Form: *{new_form:+d}* (-1)")

    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_tatil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tatil: form sıfırlanır, 1 maç dışarda kalır."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text(
            f"🏖️ *TATİL*\n\n"
            f"💡 Kullanım: `/tatil <oyuncu>`\n\n"
            f"📊 *ETKİ*\n"
            f"  • Form: SIFIRLANIR\n"
            f"  • 1 maç dışarda kalır\n"
            f"  • Maliyet: *{db.TATIL_COST:,} LC*\n\n"
            f"💡 Kötü formdaki oyuncuyu kurtarmak için.",
            parse_mode="Markdown")

    name_query = " ".join(context.args)
    player = _find_player_in_squad(uid, name_query)
    if not player:
        return await update.message.reply_text(f"❌ *{name_query}* kadronda yok!", parse_mode="Markdown")

    pname, rating, pos = player
    if db.get_lc_balance(uid) < db.TATIL_COST:
        return await update.message.reply_text(f"❌ Yetersiz LC! Gerekli: *{db.TATIL_COST:,}*", parse_mode="Markdown")

    db.do_tatil(uid, pname)
    db.update_lc_balance(uid, -db.TATIL_COST)
    await update.message.reply_text(
        f"🏖️ *TATİLE GÖNDERİLDİ!*\n\n"
        f"⭐ *{pname}*\n"
        f"🔄 Form sıfırlandı\n"
        f"⏰ Sonraki 1 maç oynamayacak\n"
        f"💸 Ödenen: *{db.TATIL_COST:,} LC*",
        parse_mode="Markdown")

async def cmd_kamp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kamp: tüm kadro form +1, sezonda 2 kez."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    used = db.get_camps_used(uid)
    if not context.args or context.args[0].lower() not in ["onayla", "yes", "evet"]:
        return await update.message.reply_text(
            f"🏕️ *TAKIM KAMPI*\n\n"
            f"📊 *DURUM*\n"
            f"  • Bu sezon: {used}/{db.SEASON_CAMP_LIMIT}\n"
            f"  • Maliyet: *{db.KAMP_COST:,} LC*\n"
            f"  • Etki: Tüm kadro form *+1*\n\n"
            f"💡 Onaylamak için: `/kamp onayla`",
            parse_mode="Markdown")

    if used >= db.SEASON_CAMP_LIMIT:
        return await update.message.reply_text(
            f"❌ Bu sezon kamp limiti doldu! ({used}/{db.SEASON_CAMP_LIMIT})",
            parse_mode="Markdown")

    if db.get_lc_balance(uid) < db.KAMP_COST:
        return await update.message.reply_text(f"❌ Yetersiz LC! Gerekli: *{db.KAMP_COST:,}*", parse_mode="Markdown")

    result = db.do_camp(uid)
    if result == "limit":
        return await update.message.reply_text("❌ Limit doldu!")
    db.update_lc_balance(uid, -db.KAMP_COST)

    await update.message.reply_text(
        f"🏕️ *KAMP TAMAMLANDI!*\n\n"
        f"🔥 Tüm kadronun formu *+1* artırıldı\n"
        f"📊 Kullanım: *{result}/{db.SEASON_CAMP_LIMIT}*\n"
        f"💸 Ödenen: *{db.KAMP_COST:,} LC*\n\n"
        f"💪 Takım moralı tavan!",
        parse_mode="Markdown")

async def cmd_kaptan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kaptan seç."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    if not context.args:
        current = db.get_captain(uid)
        if current:
            return await update.message.reply_text(
                f"👑 *KAPTAN*\n\n"
                f"⭐ Mevcut kaptan: *{current}*\n\n"
                f"💡 Değiştirmek için: `/kaptan <yeni_oyuncu>`\n"
                f"📊 Etki: Maç öncesi kaptan + 2 oyuncuya form *+1*",
                parse_mode="Markdown")
        return await update.message.reply_text(
            f"👑 *KAPTAN SEÇİMİ*\n\n"
            f"💡 Kullanım: `/kaptan <oyuncu_adı>`\n\n"
            f"📊 Etki:\n"
            f"  • Kaptan + en yüksek 2 oyuncuya pasif form +1\n"
            f"  • Maç öncesi otomatik uygulanır",
            parse_mode="Markdown")

    name_query = " ".join(context.args)
    player = _find_player_in_squad(uid, name_query)
    if not player:
        return await update.message.reply_text(f"❌ *{name_query}* kadronda yok!", parse_mode="Markdown")

    pname, rating, pos = player
    if db.set_captain(uid, pname):
        await update.message.reply_text(
            f"👑 *YENİ KAPTAN!*\n\n"
            f"⭐ *{pname}* (`{rating}`)\n\n"
            f"💪 Maç öncesi yan oyunculara form bonusu verecek.",
            parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Kaptan atama başarısız.")


# ─────────────────────────────────────────────────────────────
# ANTRENÖR SİSTEMİ
# ─────────────────────────────────────────────────────────────

async def cmd_taktik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Taktik ve diziliş ana ekranı."""
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    formation, tactic = db.get_team_tactics(uid)
    can_change = db.can_change_tactics_today(uid)

    # Diziliş bilgisi
    f_info = lig.FORMATIONS.get(formation, lig.FORMATIONS["4-3-3"])
    t_info = lig.TACTICS.get(tactic, lig.TACTICS["dengeli"])

    # Etkiler
    mod = lig.calculate_team_modifier(formation, tactic)
    atk_pct = int((mod["attack"] - 1) * 100)
    def_pct = int((mod["defense"] - 1) * 100)

    atk_str = f"+%{atk_pct}" if atk_pct >= 0 else f"%{atk_pct}"
    def_str = f"+%{def_pct}" if def_pct >= 0 else f"%{def_pct}"

    text = (
        "╔══════════════════════╗\n"
        "║  ⚙️  TAKTİK MERKEZİ  ║\n"
        "╚══════════════════════╝\n\n"
        f"📐 *Diziliş:* `{formation}` — _{f_info['label']}_\n"
        f"🎯 *Taktik:* {t_info['label']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 *KOMBİNE ETKİ*\n"
        f"⚔️ Hücum: *{atk_str}*\n"
        f"🛡️ Savunma: *{def_str}*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if can_change:
        text += "✅ *Bugün değiştirebilirsin!*\n\n"
    else:
        text += "🔒 *Bugün taktik değiştirdin.* Yarın tekrar dene.\n\n"

    text += (
        "📋 *KOMUTLAR*\n"
        "`/dizilis <kod>` — Diziliş değiştir\n"
        "`/taktik_sec <ad>` — Taktik seç\n\n"
        "📐 *DİZİLİŞLER:*\n"
        "• 4-3-3 — Hücum (+%10 gol, -%5 def)\n"
        "• 4-4-2 — Dengeli (nötr)\n"
        "• 5-3-2 — Defans (+%15 def, -%10 gol)\n"
        "• 4-2-3-1 — Kontrollü (+%5 her ikisi)\n"
        "• 3-5-2 — Orta saha (form +%15)\n\n"
        "🎯 *TAKTİKLER:*\n"
        "• `hucum` — ⚔️ +%20 gol, -%15 def\n"
        "• `defans` — 🛡️ -%20 yenilen, -%10 atılan\n"
        "• `dengeli` — ⚖️ Nötr\n"
        "• `pres` — 🔥 +%10 her ikisi, %66 fazla sakatlık"
    )

    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_dizilis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Diziliş değiştir."""
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text(
            "💡 Kullanım: `/dizilis <kod>`\n\n"
            "📐 Seçenekler:\n"
            "• `4-3-3` — Hücum\n"
            "• `4-4-2` — Dengeli\n"
            "• `5-3-2` — Defans\n"
            "• `4-2-3-1` — Kontrollü\n"
            "• `3-5-2` — Orta saha",
            parse_mode="Markdown")

    new_formation = context.args[0]
    if new_formation not in lig.FORMATIONS:
        return await update.message.reply_text(
            f"❌ Geçersiz diziliş: `{new_formation}`\nGeçerli: 4-3-3, 4-4-2, 5-3-2, 4-2-3-1, 3-5-2",
            parse_mode="Markdown")

    if not db.can_change_tactics_today(uid):
        return await update.message.reply_text(
            "🔒 *Bugün taktik değiştirildi!*\n"
            "⏰ Yarın tekrar değiştirebilirsin.",
            parse_mode="Markdown")

    success = db.set_team_tactics(uid, formation=new_formation)
    if not success:
        return await update.message.reply_text("❌ Bugün zaten değişti, yarın dene.")

    f_info = lig.FORMATIONS[new_formation]
    await update.message.reply_text(
        f"✅ *Diziliş Değiştirildi!*\n\n"
        f"📐 Yeni: `{new_formation}` — *{f_info['label']}*\n"
        f"💡 `/taktik` ile detay göster",
        parse_mode="Markdown")

async def cmd_taktik_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Taktik seç."""
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    if not context.args:
        return await update.message.reply_text(
            "💡 Kullanım: `/taktik_sec <ad>`\n\n"
            "🎯 Seçenekler:\n"
            "• `hucum` — ⚔️\n"
            "• `defans` — 🛡️\n"
            "• `dengeli` — ⚖️\n"
            "• `pres` — 🔥",
            parse_mode="Markdown")

    new_tactic = context.args[0].lower()
    if new_tactic not in lig.TACTICS:
        return await update.message.reply_text(
            f"❌ Geçersiz: `{new_tactic}`\nGeçerli: hucum, defans, dengeli, pres",
            parse_mode="Markdown")

    if not db.can_change_tactics_today(uid):
        return await update.message.reply_text(
            "🔒 *Bugün taktik değiştirildi!*\n⏰ Yarın tekrar dene.",
            parse_mode="Markdown")

    success = db.set_team_tactics(uid, tactic=new_tactic)
    if not success:
        return await update.message.reply_text("❌ Bugün zaten değişti.")

    t_info = lig.TACTICS[new_tactic]
    await update.message.reply_text(
        f"✅ *Taktik Değiştirildi!*\n\n"
        f"🎯 Yeni: {t_info['label']}\n"
        f"💡 `/taktik` ile detay göster",
        parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────
# ANTRENMAN + AKADEMİ + SÖZLEŞME + HABERLER
# ─────────────────────────────────────────────────────────────

async def cmd_teklif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Belirli oyuncu için karşı takıma teklif yap.
    Kullanım:
      /teklif <oyuncu_adı> <miktar>  (yanıtla)
      /teklif @username <oyuncu_adı> <miktar>
    """
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    args = list(context.args)
    target_id, target_name = await _resolve_target_user(update, context)
    if target_id and args and args[0].startswith("@"):
        args = args[1:]  # @user tüketildi

    if not target_id:
        return await update.message.reply_text(
            "💡 Kullanım:\n"
            "• Yanıtla: `/teklif <oyuncu> <miktar>`\n"
            "• `/teklif @kullanici <oyuncu> <miktar>`",
            parse_mode="Markdown")

    if not db.get_team(target_id):
        return await update.message.reply_text("❌ Hedef takım yok.")

    if len(args) < 2:
        return await update.message.reply_text("💡 `/teklif <oyuncu> <miktar>`", parse_mode="Markdown")

    try:
        amount = int(args[-1].replace(".", "").replace(",", ""))
        player_name = " ".join(args[:-1])
    except:
        return await update.message.reply_text("❌ Geçerli miktar girin.")

    if amount < 1000:
        return await update.message.reply_text("❌ Min 1.000 LC")

    # Oyuncuyu kontrol et
    squad = db.get_squad(target_id)
    target_player = None
    for p_name, rating, pos, starter in squad:
        if player_name.lower() in p_name.lower():
            target_player = (p_name, rating, pos)
            break
    if not target_player:
        return await update.message.reply_text(f"❌ *{player_name}* hedef takımda yok.", parse_mode="Markdown")

    pname, rating, pos = target_player

    # Kiralık mı kontrol et
    if db.is_player_loaned(pname, target_id):
        return await update.message.reply_text(f"❌ *{pname}* şu an kiralık, satılamaz.", parse_mode="Markdown")

    # Bütçe kontrolü
    if db.get_lc_balance(uid) < amount:
        return await update.message.reply_text(f"❌ Yetersiz LC! Mevcut: *{db.get_lc_balance(uid):,}*", parse_mode="Markdown")

    offer_id = db.create_offer(uid, target_id, pname, amount, is_loan=False)

    # Hedef takıma DM gönder
    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}[pos]
    my_team = db.get_team(uid)
    teklif_msg = (
        f"📩 *YENİ TRANSFER TEKLİFİ!*\n\n"
        f"{pos_em} *{pname}* (`{rating}`)\n"
        f"💰 Teklif: *{amount:,} LC*\n"
        f"🏟️ Teklif eden: *{my_team[0]}*\n\n"
        f"📋 *YANITLA:*\n"
        f"• `/teklif_kabul {offer_id}`\n"
        f"• `/teklif_red {offer_id}`\n"
        f"• `/teklif_karsi {offer_id} <yeni_fiyat>`\n\n"
        f"_⏰ Cevap vermezsen iptal olur._"
    )
    try:
        await context.bot.send_message(chat_id=target_id, text=teklif_msg, parse_mode="Markdown")
    except:
        pass

    await update.message.reply_text(
        f"✅ *Teklif gönderildi!*\n\n"
        f"📨 Hedef: {target_name}\n"
        f"⚽ Oyuncu: *{pname}*\n"
        f"💰 Fiyat: *{amount:,} LC*\n"
        f"🆔 Teklif ID: `{offer_id}`",
        parse_mode="Markdown")

async def cmd_teklif_kabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Teklifi kabul et."""
    uid = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("💡 `/teklif_kabul <id>`", parse_mode="Markdown")
    try:
        offer_id = int(context.args[0])
    except:
        return await update.message.reply_text("❌ Geçerli ID.")

    offer = db.get_offer(offer_id)
    if not offer:
        return await update.message.reply_text("❌ Teklif bulunamadı.")
    oid, from_uid, to_uid, pname, amount, status, round_no, is_loan, loan_matches = offer
    if to_uid != uid:
        return await update.message.reply_text("❌ Bu teklif sana değil.")
    if status != "pending":
        return await update.message.reply_text(f"❌ Bu teklif zaten: {status}")

    # Alıcı bütçesi kontrol
    if db.get_lc_balance(from_uid) < amount:
        db.update_offer_status(offer_id, "failed")
        return await update.message.reply_text("❌ Teklif sahibinin LC'si yetmiyor, iptal edildi.")

    # Para transferi
    db.update_lc_balance(from_uid, -amount)
    db.update_lc_balance(to_uid, amount)

    if is_loan:
        # Kiralama: 4 maç
        db.create_loan(to_uid, from_uid, pname, matches=loan_matches)
        db.update_offer_status(offer_id, "accepted")
        # Oyuncu geçici olarak alıcının kadrosuna eklenir
        # (Squad'ı kopyalayalım, kiralık biterse otomatik geri döner)
        squad = db.get_squad(to_uid)
        target = next((s for s in squad if s[0] == pname), None)
        if target:
            db.add_player_to_squad(from_uid, pname, target[1], target[2])
            db.remove_player_from_squad(to_uid, pname)

        await update.message.reply_text(
            f"✅ Kiralama kabul edildi!\n💰 *{amount:,} LC* hesabına geçti.\n⏰ *{pname}* 4 maç sonra geri dönecek.",
            parse_mode="Markdown")
        try:
            await context.bot.send_message(
                chat_id=from_uid,
                text=f"🎉 *Kiralama kabul edildi!*\n*{pname}* 4 maç senin takımında.",
                parse_mode="Markdown")
        except: pass
    else:
        # Direkt transfer
        db.transfer_player(to_uid, from_uid, pname)
        db.update_offer_status(offer_id, "accepted")
        await update.message.reply_text(
            f"✅ Transfer kabul edildi!\n💰 *{amount:,} LC* hesabına geçti.\n📤 *{pname}* gitti.",
            parse_mode="Markdown")
        try:
            await context.bot.send_message(
                chat_id=from_uid,
                text=f"🎉 *Transfer kabul edildi!*\n*{pname}* senin takımında.",
                parse_mode="Markdown")
        except: pass

async def cmd_teklif_red(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Teklifi reddet."""
    uid = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("💡 `/teklif_red <id>`", parse_mode="Markdown")
    try:
        offer_id = int(context.args[0])
    except: return await update.message.reply_text("❌ Geçerli ID.")
    offer = db.get_offer(offer_id)
    if not offer: return await update.message.reply_text("❌ Yok.")
    oid, from_uid, to_uid, pname, amount, status, round_no, is_loan, loan_matches = offer
    if to_uid != uid: return await update.message.reply_text("❌ Sana değil.")
    db.update_offer_status(offer_id, "rejected")
    await update.message.reply_text(f"❌ Teklif reddedildi: *{pname}*", parse_mode="Markdown")
    try:
        await context.bot.send_message(chat_id=from_uid, text=f"❌ Teklifin reddedildi: *{pname}*", parse_mode="Markdown")
    except: pass

async def cmd_teklif_karsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Karşı teklif yap (max 3 tur)."""
    uid = update.effective_user.id
    if len(context.args) < 2:
        return await update.message.reply_text("💡 `/teklif_karsi <id> <yeni_fiyat>`", parse_mode="Markdown")
    try:
        offer_id = int(context.args[0])
        new_amount = int(context.args[1].replace(".", "").replace(",", ""))
    except: return await update.message.reply_text("❌ Geçerli.")

    offer = db.get_offer(offer_id)
    if not offer: return await update.message.reply_text("❌ Yok.")
    oid, from_uid, to_uid, pname, amount, status, round_no, is_loan, loan_matches = offer
    if to_uid != uid: return await update.message.reply_text("❌ Sana değil.")
    if status != "pending": return await update.message.reply_text("❌ Aktif değil.")
    if round_no >= 3: return await update.message.reply_text("❌ Pazarlık limiti doldu (3 tur).")

    ok = db.counter_offer(offer_id, new_amount)
    if not ok: return await update.message.reply_text("❌ Hata.")

    await update.message.reply_text(
        f"✅ *Karşı teklif gönderildi!*\n💰 Yeni fiyat: *{new_amount:,} LC*\n🔄 Tur: {round_no+1}/3",
        parse_mode="Markdown")
    try:
        await context.bot.send_message(
            chat_id=from_uid,
            text=(f"💬 *KARŞI TEKLİF!*\n\n*{pname}* için yeni fiyat: *{new_amount:,} LC*\n"
                  f"🔄 Tur: {round_no+1}/3\n\n"
                  f"• `/teklif_kabul {offer_id}`\n"
                  f"• `/teklif_red {offer_id}`\n"
                  f"• `/teklif_karsi {offer_id} <fiyat>`"),
            parse_mode="Markdown")
    except: pass

# ── Açık Pazar ──

async def cmd_kirala(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kiralama teklifi (4 maç)."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    args = list(context.args)
    target_id, target_name = await _resolve_target_user(update, context)
    if target_id and args and args[0].startswith("@"):
        args = args[1:]

    if not target_id:
        return await update.message.reply_text(
            "💡 Kullanım:\n"
            "• Yanıtla: `/kirala <oyuncu> <miktar>`\n"
            "• `/kirala @kullanici <oyuncu> <miktar>`\n\n"
            "⏰ Süre: *4 maç*",
            parse_mode="Markdown")

    if len(args) < 2:
        return await update.message.reply_text("💡 `/kirala <oyuncu> <miktar>`", parse_mode="Markdown")

    try:
        amount = int(args[-1].replace(".", "").replace(",", ""))
        player_name = " ".join(args[:-1])
    except:
        return await update.message.reply_text("❌ Geçerli miktar.")

    if amount < 500:
        return await update.message.reply_text("❌ Min 500 LC")

    squad = db.get_squad(target_id)
    target_player = None
    for p_name, rating, pos, starter in squad:
        if player_name.lower() in p_name.lower():
            target_player = (p_name, rating, pos)
            break
    if not target_player:
        return await update.message.reply_text(f"❌ *{player_name}* yok.", parse_mode="Markdown")

    pname, rating, pos = target_player

    if db.is_player_loaned(pname, target_id):
        return await update.message.reply_text(f"❌ *{pname}* zaten kiralık.", parse_mode="Markdown")

    if db.get_lc_balance(uid) < amount:
        return await update.message.reply_text(f"❌ Yetersiz LC.")

    offer_id = db.create_offer(uid, target_id, pname, amount, is_loan=True, loan_matches=4)

    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}[pos]
    my_team = db.get_team(uid)
    teklif_msg = (
        f"📩 *KİRALAMA TEKLİFİ!*\n\n"
        f"{pos_em} *{pname}* (`{rating}`)\n"
        f"💰 Kira: *{amount:,} LC*\n"
        f"⏰ Süre: *4 maç*\n"
        f"🏟️ Teklif eden: *{my_team[0]}*\n\n"
        f"• `/teklif_kabul {offer_id}` veya `/teklif_red {offer_id}`"
    )
    try:
        await context.bot.send_message(chat_id=target_id, text=teklif_msg, parse_mode="Markdown")
    except: pass

    await update.message.reply_text(
        f"✅ Kiralama teklifi gönderildi!\n🆔 `{offer_id}`",
        parse_mode="Markdown")

async def cmd_sat_pazar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyuncuyu açık pazara koy."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")
    if len(context.args) < 2:
        return await update.message.reply_text(
            "💡 `/sat_pazar <oyuncu> <fiyat>`\n📅 İlan 7 gün geçerli.",
            parse_mode="Markdown")
    try:
        price = int(context.args[-1].replace(".", "").replace(",", ""))
        player_name = " ".join(context.args[:-1])
    except: return await update.message.reply_text("❌ Geçerli fiyat.")
    if price < 1000:
        return await update.message.reply_text("❌ Min 1.000 LC.")

    squad = db.get_squad(uid)
    target = None
    for p_name, rating, pos, starter in squad:
        if player_name.lower() in p_name.lower():
            target = (p_name, rating, pos)
            break
    if not target:
        return await update.message.reply_text(f"❌ *{player_name}* yok.", parse_mode="Markdown")

    pname, rating, pos = target
    if db.is_player_loaned(pname, uid):
        return await update.message.reply_text("❌ Kiralık oyuncu satılamaz.")

    db.add_to_market(uid, pname, rating, pos, price)
    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}[pos]
    await update.message.reply_text(
        f"✅ *Pazara eklendi!*\n\n{pos_em} *{pname}* (`{rating}`) — *{price:,} LC*\n📋 `/pazar` ile görünür.",
        parse_mode="Markdown")

    # Canlı pazar bildirimi (gruba)
    team = db.get_team(uid)
    team_name = team[0] if team else "Bilinmeyen"
    try:
        await _send_to_broadcast_chats(
            context,
            f"🛒 *YENİ İLAN!*\n\n{pos_em} *{pname}* (`{rating}`) — *{price:,} LC*\n📍 _{team_name}_ takımı satıyor\n💡 `/pazar` ile bak!",
            category="lig")
    except: pass

async def cmd_pazar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm satılık oyuncular."""
    db.cleanup_old_market(days=7)
    listings = db.get_market_listings(30)
    if not listings:
        return await update.message.reply_text("🛒 Pazar boş! Oyuncu satışa kondu mu? `/sat_pazar`", parse_mode="Markdown")

    text = (
        "╔══════════════════════╗\n"
        "║  🛒  OYUNCU PAZARI  ║\n"
        "╚══════════════════════╝\n\n"
    )
    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}
    for lid, seller_uid, pname, rating, pos, price, listed_at, seller_team in listings[:15]:
        seller_team = seller_team or f"User_{seller_uid}"
        text += f"{pos_em[pos]} *{pname}* (`{rating}`) — *{price:,} LC*\n"
        text += f"   📍 _{seller_team}_ | `/pazardan_al {lid}`\n\n"

    if len(listings) > 15:
        text += f"_...ve {len(listings)-15} ilan daha._"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_pazardan_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pazardan oyuncu satın al."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")
    if not context.args:
        return await update.message.reply_text("💡 `/pazardan_al <id>`", parse_mode="Markdown")
    try:
        lid = int(context.args[0])
    except: return await update.message.reply_text("❌ Geçerli ID.")

    result = db.buy_from_market(lid, uid)
    if result is None:
        return await update.message.reply_text("❌ İlan yok veya satıldı.")
    if result == "own":
        return await update.message.reply_text("❌ Kendi ilanını alamazsın.")

    seller_uid, pname, rating, pos, price = result
    if db.get_lc_balance(uid) < price:
        # Geri açılır mı? Pratikte iptal et
        return await update.message.reply_text(f"❌ Yetersiz LC! İhtiyacın: *{price:,}*", parse_mode="Markdown")

    squad = db.get_squad(uid)
    if len(squad) >= 15:
        return await update.message.reply_text("❌ Kadro dolu (15/15)")

    db.update_lc_balance(uid, -price)
    db.update_lc_balance(seller_uid, price)
    db.transfer_player(seller_uid, uid, pname)

    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}[pos]
    await update.message.reply_text(
        f"✅ *PAZARDAN ALINDI!*\n\n{pos_em} *{pname}* (`{rating}`)\n💸 *{price:,} LC* ödendi.",
        parse_mode="Markdown")
    try:
        await context.bot.send_message(
            chat_id=seller_uid,
            text=f"💰 *{pname}* satıldı! *+{price:,} LC* hesabına geçti.",
            parse_mode="Markdown")
    except: pass

    # Canlı satış bildirimi (gruba)
    buyer_team = db.get_team(uid)
    seller_team = db.get_team(seller_uid)
    buyer_name = buyer_team[0] if buyer_team else "Bilinmeyen"
    seller_name = seller_team[0] if seller_team else "Bilinmeyen"
    try:
        await _send_to_broadcast_chats(
            context,
            f"💰 *PAZAR SATIŞI!*\n\n{pos_em} *{pname}* (`{rating}`)\n📤 _{seller_name}_ → 📥 _{buyer_name}_\n💸 *{price:,} LC*",
            category="lig")
    except: pass


# ─────────────────────────────────────────────────────────────
# YAYIN KANALI YÖNETİMİ (Konu bazlı)
# ─────────────────────────────────────────────────────────────

async def cmd_rakip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yarınki rakibinin profilini veya yanıtladığın/@user takımının profilini gör."""
    uid = update.effective_user.id
    target_id = None

    # 1. Yanıtla / @user / arg
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        if context.args[0].startswith("@"):
            user = db.get_user_by_username(context.args[0][1:])
            if user: target_id = user[0]
        else:
            try: target_id = int(context.args[0])
            except: pass

    # 2. Otomatik: sıradaki rakip
    if not target_id:
        if not db.get_team(uid):
            return await update.message.reply_text("❌ Önce takım kur veya rakibi belirt!", parse_mode="Markdown")
        season = db.get_active_season()
        if not season:
            return await update.message.reply_text("❌ Aktif sezon yok.")
        next_match = db.get_user_next_match(uid, season[0])
        if not next_match:
            return await update.message.reply_text("❌ Sıradaki maçın yok.")
        fid, week, mdate, t1id, t2id, derby, t1name, t2name = next_match
        target_id = t2id if t1id == uid else t1id

    # Rakip takımı analiz et
    team = db.get_team(target_id)
    if not team:
        return await update.message.reply_text("❌ Bu kullanıcının takımı yok.")

    name, lc, formation, w, d, l, gf, ga = team
    points = w*3 + d
    form = db.get_team_form(target_id)
    f_form, tactic = db.get_team_tactics(target_id)

    # Form göstergesi
    if form >= 4: form_em = "🔥🔥 Süper form"
    elif form >= 2: form_em = "🔥 Formda"
    elif form >= 0: form_em = "➡️ Normal"
    elif form >= -2: form_em = "📉 Düşük"
    else: form_em = "😴 Formsuz"

    # En iyi 3 oyuncu
    squad = db.get_squad(target_id)
    top3 = sorted(squad, key=lambda x: -x[1])[:3]

    text = (
        f"╔══════════════════════╗\n"
        f"║  🔍  RAKİP PROFİLİ  ║\n"
        f"╚══════════════════════╝\n\n"
        f"🏟️ *{name}*\n"
        f"📐 Diziliş: `{f_form}` | Taktik: `{tactic}`\n"
        f"📊 Form: *{form_em}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 *SEZON İSTATİSTİKLERİ*\n"
        f"🏆 Puan: *{points}* | Maç: {w+d+l}\n"
        f"✅ G:{w} ➖B:{d} ❌M:{l}\n"
        f"⚽ Atılan: *{gf}* | Yenilen: *{ga}*\n"
        f"📊 Averaj: *{gf-ga:+d}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ *EN İYİ 3 OYUNCU*\n"
    )
    pos_em = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚔️"}
    for p_name, rating, pos, starter in top3:
        text += f"  {pos_em.get(pos, '⚽')} *{p_name}* (`{rating}`)\n"

    # Tehlike analizi
    text += "\n━━━━━━━━━━━━━━━━━━━━━━\n💡 *ANALİZ*\n"
    if form >= 3:
        text += "⚠️ *DİKKAT:* Rakip süper formda!\n"
    if gf > w * 3:
        text += "⚽ Ofansif takım, çok gol atıyor.\n"
    if ga < l * 1.5 and l > 0:
        text += "🛡️ Sağlam defansı var.\n"
    if not text.endswith("💡 *ANALİZ*\n"):
        pass
    else:
        text += "📊 Standart takım, dengeli oynuyor."

    await update.message.reply_text(text, parse_mode="Markdown")




# ─────────────────────────────────────────────────────────────
# FORM EKOSİSTEMİ KOMUTLARI
# ─────────────────────────────────────────────────────────────

async def cmd_lig_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teams = db.get_all_teams_ranked()
    if not teams:
        return await update.message.reply_text("❌ Henüz lige katılan yok!")

    text = (
        "╔══════════════════════╗\n"
        "║  📊  PUAN DURUMU  ║\n"
        "╚══════════════════════╝\n\n"
    )

    medals = ["🥇", "🥈", "🥉"]
    for i, t in enumerate(teams[:15], 1):
        uid_t, name, w, d, l, gf, ga, pts = t
        em = medals[i-1] if i <= 3 else f"{i}."
        avg = gf - ga
        avg_s = f"+{avg}" if avg >= 0 else str(avg)
        text += f"{em} *{name[:14]}* — `{pts}` puan\n"
        text += f"     G:{w} B:{d} M:{l} | Av:{avg_s}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_ligler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm liglerin sıralamalarını göster."""
    summary = db.get_all_tiers_summary()

    text = (
        "╔══════════════════════╗\n"
        "║  🏆  LİG SİSTEMİ  ║\n"
        "╚══════════════════════╝\n\n"
    )

    for tier in [4, 3, 2, 1]:
        tier_info = db.LEAGUE_TIERS[tier]
        teams = summary.get(tier, [])
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"*{tier_info['name']}*\n"

        if not teams:
            text += "_Henüz takım yok_\n\n"
            continue

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, t in enumerate(teams, 1):
            uid_t, name, w, d, l, gf, ga, pts = t
            em = medals[i-1] if i <= 5 else f"{i}."
            text += f"{em} *{name[:14]}* — `{pts}` puan\n"
        text += "\n"

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📖 *SİSTEM*\n"
        "• Top 3 → Üst lige çıkar\n"
        "• Son 3 → Alt lige düşer\n"
        "• Sezon sonunda otomatik"
    )

    await update.message.reply_text(text, parse_mode="Markdown")

# Admin komutları

async def cmd_sampiyonlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Şampiyonlar tarihi."""
    history = db.get_champions_history(15)
    if not history:
        return await update.message.reply_text(
            "📜 Henüz şampiyon yok!\n\nİlk sezonun şampiyonu sen ol! 🏆",
            parse_mode="Markdown")

    text = (
        "╔══════════════════════╗\n"
        "║  🏆  ŞAMPİYONLAR  ║\n"
        "╚══════════════════════╝\n\n"
    )
    for season_no, team_name, points, end_date in history:
        text += f"👑 *Sezon {season_no}* — *{team_name}* ({points} puan)\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# Sezon bitirme job — her saat kontrol eder

async def cmd_fikstur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime, timedelta
    uid = update.effective_user.id
    season = db.get_active_season()
    if not season:
        return await update.message.reply_text("❌ Aktif sezon yok.")
    season_no = season[0]

    # Parametre kontrolü
    arg = context.args[0].lower() if context.args else "bugun"

    if arg in ["tum", "hepsi", "tümü", "all"]:
        # Tüm sezonun fikstürü — haftalara göre
        all_fix = db.get_all_fixtures(season_no)
        if not all_fix:
            return await update.message.reply_text("📅 Henüz fikstür oluşturulmamış.")

        # Haftalara göre grupla
        by_week = {}
        for f in all_fix:
            week = f[1]
            by_week.setdefault(week, []).append(f)

        text = f"╔══════════════════════╗\n║  📅  SEZON {season_no} FİKSTÜRÜ  ║\n╚══════════════════════╝\n\n"

        for week in sorted(by_week.keys())[:8]:  # İlk 8 hafta
            matches = by_week[week]
            date_str = matches[0][2][:10] if matches else ""
            text += f"━━━ *Hafta {week}* ({date_str}) ━━━\n"
            for f in matches:
                fid, w, mdate, t1id, t2id, derby, t1name, t2name, played, g1, g2 = f
                derby_em = " 🔥" if derby else ""
                if played:
                    text += f"  ✅ {t1name or '?'} `{g1}-{g2}` {t2name or '?'}{derby_em}\n"
                else:
                    text += f"  ⏳ {t1name or '?'} 🆚 {t2name or '?'}{derby_em}\n"
            text += "\n"

        if len(by_week) > 8:
            text += f"_...ve {len(by_week)-8} hafta daha. `/fikstur <hafta>` ile bak._"

        return await update.message.reply_text(text, parse_mode="Markdown")

    elif arg.isdigit():
        # Belirli hafta
        week_no = int(arg)
        week_fix = db.get_all_fixtures(season_no, week_no)
        if not week_fix:
            return await update.message.reply_text(f"❌ Hafta {week_no} maçı yok.")

        text = f"📅 *HAFTA {week_no} FİKSTÜRÜ*\n\n"
        for f in week_fix:
            fid, w, mdate, t1id, t2id, derby, t1name, t2name, played, g1, g2 = f
            derby_em = " 🔥 DERBİ" if derby else ""
            date_str = mdate[:10]
            if played:
                text += f"✅ *{t1name}* `{g1}-{g2}` *{t2name}*{derby_em}\n"
            else:
                text += f"⏳ *{t1name}* 🆚 *{t2name}*{derby_em}\n   📅 {date_str}\n"
        return await update.message.reply_text(text, parse_mode="Markdown")

    elif arg in ["yarin", "yarın"]:
        target = datetime.now() + timedelta(days=1)
        target_str = target.strftime("%Y-%m-%d")
        title = "📅 YARINKİ MAÇLAR"
    else:
        # Bugün (default)
        target_str = datetime.now().strftime("%Y-%m-%d")
        title = "⚽ BUGÜNKÜ MAÇLAR"

    fixtures = db.get_fixtures_by_date(target_str, season_no)

    text = f"╔══════════════════════╗\n║  {title}  ║\n╚══════════════════════╝\n\n"

    if not fixtures:
        text += "🛌 Bugün maç yok!\n"
    else:
        for f in fixtures:
            fid, week, mdate, t1id, t2id, derby, t1name, t2name = f
            derby_em = " 🔥 *DERBİ*" if derby else ""
            mine = " 👈" if (uid in (t1id, t2id)) else ""
            text += f"⚽ *{t1name}* 🆚 *{t2name}*{derby_em}{mine}\n"
            text += f"   💡 `/tahmin {fid} <skor>` örn: `/tahmin {fid} 2-1`\n\n"

    # Kullanıcının sıradaki maçı
    next_match = db.get_user_next_match(uid, season_no)
    if next_match:
        fid, week, mdate, t1id, t2id, derby, t1name, t2name = next_match
        rakip = t2name if t1id == uid else t1name
        date_str = mdate[:10]
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"🎯 *Senin Sıradaki Maçın*\n"
        text += f"⚽ vs *{rakip}*{' 🔥' if derby else ''}\n"
        text += f"📅 {date_str} — Hafta {week}"

    text += "\n\n💡 `/fikstur tum` — Tüm sezon\n💡 `/fikstur yarin` — Yarın\n💡 `/fikstur <hafta>` — Belirli hafta"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_tahmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Skor tahmini gönder. Sadece maçtan 30 dk önce - maç başlayana kadar açık."""
    from datetime import datetime
    uid = update.effective_user.id
    db.register_user(uid, update.effective_user.first_name)

    if len(context.args) < 2:
        return await update.message.reply_text(
            "💡 Kullanım: `/tahmin <maç_id> <skor>`\n"
            "Örnek: `/tahmin 42 2-1`\n\n"
            "🏆 *Ödüller:*\n"
            "  • Tam skor doğru: *+10.000 LC*\n"
            "  • Sadece sonucu doğru (G/B/M): *+2.000 LC*\n\n"
            "⏰ Tahmin penceresi: *20:30 - 21:00* arası açık.",
            parse_mode="Markdown")

    # Tahmin penceresi kontrolü: TR 20:30 - 21:00 arası açık
    now = tr_now()
    minutes_of_day = now.hour * 60 + now.minute
    if not (1230 <= minutes_of_day < 1260):  # 20:30 - 21:00 TR
        return await update.message.reply_text(
            "🔒 *Tahmin penceresi kapalı!*\n\n"
            "⏰ Tahminler sadece *20:30 - 21:00* arasında alınır.\n"
            "📋 `/fikstur` ile bugünkü maçları gör.",
            parse_mode="Markdown")

    try:
        fid = int(context.args[0])
        score = context.args[1]
        if "-" not in score:
            return await update.message.reply_text("❌ Skor formatı: `2-1`", parse_mode="Markdown")
        g1, g2 = score.split("-", 1)
        g1, g2 = int(g1.strip()), int(g2.strip())
        if g1 < 0 or g2 < 0 or g1 > 10 or g2 > 10:
            return await update.message.reply_text("❌ Skor 0-10 arası olmalı.")
    except:
        return await update.message.reply_text("❌ Geçersiz format. Örnek: `/tahmin 42 2-1`", parse_mode="Markdown")

    db.submit_prediction(fid, uid, g1, g2)
    await update.message.reply_text(
        f"✅ *Tahminin kaydedildi!*\n\n"
        f"⚽ Skor tahmini: *{g1} - {g2}*\n"
        f"🆔 Maç ID: `{fid}`\n\n"
        f"🏆 Tam skor: +10K LC | Sonuç: +2K LC",
        parse_mode="Markdown")

# ── Hatırlatıcı job — saatte bir kontrol ──



# ─────────────────────────────────────────────────────────────
# GÜN İÇİ HABER JOB'LARI
# ─────────────────────────────────────────────────────────────

async def cmd_haberler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Son lig haberleri."""
    news = db.get_recent_news(10)
    if not news:
        return await update.message.reply_text("📰 Henüz haber yok!")

    text = (
        "╔══════════════════════╗\n"
        "║  📰  LİG HABERLERİ  ║\n"
        "╚══════════════════════╝\n\n"
    )
    for news_date, content in news:
        date_str = news_date[:10]
        text += f"📅 _{date_str}_\n{content}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# Lig haberi üreten yardımcı

async def cmd_sosyal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Son sosyal medya tepkileri."""
    posts = db.get_recent_social(10)
    if not posts:
        return await update.message.reply_text(
            "📱 Henüz tepki yok!\nMaçlar oynanınca sosyal medya hareketlenir 🐦",
            parse_mode="Markdown")

    text = (
        "╔══════════════════════╗\n"
        "║  📱  SOSYAL MEDYA  ║\n"
        "╚══════════════════════╝\n\n"
    )
    for posted_at, content in posts:
        date_str = posted_at[:10]
        text += f"📅 _{date_str}_\n{content}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")


# ─────────────────────────────────────────────────────────────
# COIN BANK + LİG KADEMELERİ KOMUTLARI
# ─────────────────────────────────────────────────────────────

async def cmd_kur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime
    now = datetime.now()
    current_hour = now.hour + now.day * 24  # Stabil hash

    rate = lig.calculate_current_rate(current_hour)
    trend = lig.get_rate_trend(current_hour)

    # Son 24 saatin mini grafiği
    history = lig.get_24h_history(current_hour)
    rates = [r for _, r in history]
    min_r, max_r = min(rates), max(rates)

    # ASCII grafik (5 seviye)
    levels = 5
    graph_lines = []
    for level in range(levels, 0, -1):
        line = ""
        threshold = min_r + (max_r - min_r) * (level / levels)
        for r in rates[-12:]:  # Son 12 saat
            line += "█" if r >= threshold else " "
        graph_lines.append(line)

    graph = "\n".join(f"`{l}`" for l in graph_lines)

    await update.message.reply_text(
        f"╔══════════════════════╗\n"
        f"║  💱  LC BORSA KURU  ║\n"
        f"╚══════════════════════╝\n\n"
        f"💎 *1 LC = {rate} casino coin* {trend}\n\n"
        f"📊 Son 12 saat:\n{graph}\n\n"
        f"📈 24h yüksek: `{max_r}` coin\n"
        f"📉 24h düşük: `{min_r}` coin\n\n"
        f"💡 `/cevir <miktar>` ile LC'ye dönüştür",
        parse_mode="Markdown")

async def cmd_cevir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import datetime
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce `/takim_kur` ile takım kur!", parse_mode="Markdown")

    # Sezonluk limit kontrolü
    used = db.get_conversion_used(uid)
    remaining = db.CONVERSION_LIMIT - used

    if not context.args:
        return await update.message.reply_text(
            f"💡 Kullanım: `/cevir <casino_coin>`\n\n"
            f"📊 *Sezonluk Limit:* {db.CONVERSION_LIMIT:,} coin\n"
            f"✅ Kullanılan: *{used:,}* coin\n"
            f"💎 Kalan: *{remaining:,}* coin",
            parse_mode="Markdown")

    try:
        amount = int(context.args[0].replace(".", "").replace(",", ""))
    except:
        return await update.message.reply_text("❌ Geçerli sayı girin.")

    if amount < 1000:
        return await update.message.reply_text("❌ Minimum 1.000 casino coin.")

    if amount > remaining:
        return await update.message.reply_text(
            f"❌ *Sezonluk limit aşıldı!*\n\n"
            f"💱 İstenen: *{amount:,}* coin\n"
            f"💎 Kalan limit: *{remaining:,}* coin\n"
            f"📊 Sezon başına: *{db.CONVERSION_LIMIT:,}* coin\n\n"
            f"_Yeni sezonda sıfırlanır._",
            parse_mode="Markdown")

    balance = db.get_balance(uid)
    if balance < amount:
        return await update.message.reply_text(f"❌ Yetersiz bakiye! Mevcut: *{balance:,}*", parse_mode="Markdown")

    now = datetime.now()
    current_hour = now.hour + now.day * 24
    rate = lig.calculate_current_rate(current_hour)
    lc_received = amount // rate

    if lc_received < 1:
        return await update.message.reply_text("❌ En az 1 LC alacak kadar coin gerekli.")

    db.update_balance(uid, -amount)
    db.update_lc_balance(uid, lc_received)
    db.add_conversion(uid, amount)

    new_remaining = remaining - amount
    await update.message.reply_text(
        f"💱 *DÖNÜŞÜM BAŞARILI!*\n\n"
        f"💵 Verilen: *{amount:,}* casino coin\n"
        f"💎 Alınan: *{lc_received:,}* LC\n"
        f"📊 Kur: *1 LC = {rate} coin*\n\n"
        f"💼 Yeni LC bakiye: *{db.get_lc_balance(uid):,}*\n"
        f"📉 Sezon limiti kalan: *{new_remaining:,}* coin",
        parse_mode="Markdown")

async def cmd_lc_bakiye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    team = db.get_team(uid)
    if not team:
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")
    await update.message.reply_text(
        f"💎 LC Bakiyeniz: *{team[1]:,}* Legend Coin",
        parse_mode="Markdown")

# ── Günlük maç simülasyonu — canlı, detaylı, formlu ──
# Yayın kanalları: {chat_id: {"lig": thread_id, "casino": thread_id}}
BROADCAST_TOPICS = {}
LIG_BROADCAST_CHATS = set()
# Job duplikasyon önleme
_prematch_done_date = None
_morning_done_date = None
_noon_done_date = None
_evening_done_date = None

async def cmd_lc_kod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """LC hediye kodu kullan (herkese açık)."""
    uid = update.effective_user.id
    db.register_user(uid, update.effective_user.first_name)
    if not context.args:
        return await update.message.reply_text("💡 Kullanım: `/lc_kod KOD`", parse_mode="Markdown")

    success, result = db.use_lc_code(uid, context.args[0])
    if success:
        amount, used, max_uses, kalan = result
        await update.message.reply_text(
            f"🎟 *LC Kodu Kullanıldı!*\n\n"
            f"💎 +*{amount:,} LC* hesabına eklendi!\n"
            f"📊 Kullanım: *{used}/{max_uses}* | Kalan: *{kalan}*",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(result, parse_mode="Markdown")

# ─────────────────────────────────────────────────────────────
# GENİŞLETİLMİŞ ADMİN PANELİ
# ─────────────────────────────────────────────────────────────

async def cmd_lc_yukle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tek bir kullanıcıya LC yükle."""
    if not is_admin(update.effective_user.id): return
    try:
        if update.message.reply_to_message:
            tid = update.message.reply_to_message.from_user.id
            tname = update.message.reply_to_message.from_user.first_name
            amt = int(context.args[0])
        else:
            tid, amt = int(context.args[0]), int(context.args[1])
            tname = f"ID:{tid}"

        # Lig hesabı var mı kontrol
        if not db.get_team(tid):
            return await update.message.reply_text(
                f"❌ *{tname}* henüz lig hesabı oluşturmamış!\n"
                f"Önce `/takim_kur` ile takım kurmalı.",
                parse_mode="Markdown")

        db.update_lc_balance(tid, amt)
        await update.message.reply_text(
            f"✅ *{tname}* kullanıcısına *{amt:,} LC* yüklendi.",
            parse_mode="Markdown")
    except:
        await update.message.reply_text(
            "❌ Kullanım: `/lc_yukle <miktar>` (yanıtlayarak)\n"
            "Veya: `/lc_yukle <user_id> <miktar>`",
            parse_mode="Markdown")

async def cmd_lc_dusur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tek bir kullanıcıdan LC düşür."""
    if not is_admin(update.effective_user.id): return
    try:
        if update.message.reply_to_message:
            tid = update.message.reply_to_message.from_user.id
            tname = update.message.reply_to_message.from_user.first_name
            amt = int(context.args[0])
        else:
            tid, amt = int(context.args[0]), int(context.args[1])
            tname = f"ID:{tid}"

        if not db.get_team(tid):
            return await update.message.reply_text(f"❌ *{tname}* lig hesabı yok!", parse_mode="Markdown")

        db.deduct_lc_balance(tid, amt)
        new_bal = db.get_lc_balance(tid)
        await update.message.reply_text(
            f"✅ *{tname}* kullanıcısından *{amt:,} LC* düşürüldü.\n"
            f"💎 Yeni bakiye: *{new_bal:,} LC*",
            parse_mode="Markdown")
    except:
        await update.message.reply_text(
            "❌ Kullanım: `/lc_dusur <miktar>` (yanıtlayarak)\n"
            "Veya: `/lc_dusur <user_id> <miktar>`",
            parse_mode="Markdown")

async def cmd_lc_toplu_yukle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm lig kullanıcılarına LC yükle."""
    if not is_admin(update.effective_user.id): return
    try:
        amt = int(context.args[0])
        if amt <= 0: raise ValueError
        affected = db.add_lc_all(amt)
        await update.message.reply_text(
            f"✅ *{affected}* lig oyuncusuna *{amt:,} LC* yüklendi!\n"
            f"💎 Toplam dağıtılan: *{amt * affected:,} LC*",
            parse_mode="Markdown")
    except:
        await update.message.reply_text("❌ Kullanım: `/lc_toplu_yukle <miktar>`", parse_mode="Markdown")

async def cmd_lc_kodolustur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """LC hediye kodu oluştur."""
    if not is_admin(update.effective_user.id): return
    try:
        code = context.args[0].upper()
        amount = int(context.args[1])
        max_uses = int(context.args[2]) if len(context.args) > 2 else 1
        if max_uses < 1:
            return await update.message.reply_text("❌ Kullanım sayısı en az 1 olmalı.")

        if db.create_lc_code(code, amount, max_uses):
            await update.message.reply_text(
                f"✅ *LC Kodu Oluşturuldu!*\n\n"
                f"🎟 Kod: `{code}`\n"
                f"💎 Değer: *{amount:,} LC*\n"
                f"👥 Max kullanım: *{max_uses}* kişi",
                parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Bu kod zaten mevcut.")
    except:
        await update.message.reply_text(
            "❌ Kullanım: `/lc_kodolustur <KOD> <miktar> <kişi>`\n"
            "Örnek: `/lc_kodolustur SAMPIYON 10000 50`",
            parse_mode="Markdown")

async def cmd_terfi_dusme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Manuel terfi/düşme."""
    if not is_admin(update.effective_user.id): return
    actions = db.promote_relegate_teams()
    if not actions:
        return await update.message.reply_text("ℹ️ Yapılacak işlem yok (her ligde min 4 takım gerekli).")

    text = "🏆 *TERFİ / DÜŞME*\n\n"
    for uid, name, from_t, to_t, reason in actions:
        if reason == "promote":
            text += f"⬆️ *{name}*: {db.LEAGUE_TIERS[from_t]['name']} → {db.LEAGUE_TIERS[to_t]['name']}\n"
        else:
            text += f"⬇️ *{name}*: {db.LEAGUE_TIERS[from_t]['name']} → {db.LEAGUE_TIERS[to_t]['name']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")




# ─────────────────────────────────────────────────────────────
# ADMİN — KULLANICI SİLME
# ─────────────────────────────────────────────────────────────

async def cmd_fikstur_olustur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Aktif sezona fikstür oluştur (mevcut yoksa)."""
    if not is_admin(update.effective_user.id): return
    from datetime import datetime
    active = db.get_active_season()
    if not active:
        return await update.message.reply_text("❌ Aktif sezon yok.")
    no, start_date_str, end_date_str = active

    existing = db.get_all_fixtures(no)
    if existing and not (context.args and context.args[0] == "force"):
        return await update.message.reply_text(
            f"⚠️ Sezon {no} için {len(existing)} maçlık fikstür mevcut.\n"
            f"Yine de yeniden oluşturmak için: `/fikstur_olustur force`",
            parse_mode="Markdown")

    teams = db.get_all_teams_ranked()
    if len(teams) < 2:
        return await update.message.reply_text("❌ En az 2 takım gerekli.")

    # Eski fikstürleri sil
    if existing:
        from database import connect, ph
        p = ph()
        with connect() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM lig_fixtures WHERE season_no={p}", (no,))
            conn.commit()

    team_ids = [t[0] for t in teams]
    start_dt = datetime.fromisoformat(start_date_str)
    count = db.generate_fixtures(no, team_ids, start_dt)

    await update.message.reply_text(
        f"✅ *Sezon {no}* için *{count}* maçlık fikstür oluşturuldu!\n"
        f"👥 *{len(teams)}* takım katıldı.\n"
        f"📋 `/fikstur` ile bak.",
        parse_mode="Markdown")

async def cmd_maclari_basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Bugünkü maçları manuel başlat."""
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("⚽ *Bugünkü maçlar başlatılıyor...*", parse_mode="Markdown")
    try:
        await daily_match_job(context)
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: `{e}`", parse_mode="Markdown")

async def cmd_sezon_bitir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Sezonu manuel bitir ve ödülleri dağıt."""
    if not is_admin(update.effective_user.id):
        return

    season = db.get_active_season()
    if not season:
        return await update.message.reply_text("❌ Aktif sezon yok.")
    season_no, start_date, end_date = season

    # Onay kontrolü
    if not (context.args and context.args[0] == "onayla"):
        unplayed = db.count_unplayed_fixtures(season_no)
        played = db.count_played_fixtures(season_no)
        return await update.message.reply_text(
            f"⚠️ *SEZON {season_no} MANUEL BİTİRME*\n\n"
            f"📊 Oynanan: *{played}*\n"
            f"📊 Oynanmayan: *{unplayed}*\n\n"
            f"💡 Onaylamak için: `/sezon_bitir onayla`\n\n"
            f"_Bu komut ödülleri dağıtır ve yeni sezon başlatır._",
            parse_mode="Markdown")

    # Sezonu kapat ve season_check_job'ı tetikle
    db.force_end_season(season_no)
    await update.message.reply_text(f"⏳ *Sezon {season_no} kapatılıyor, ödüller dağıtılıyor...*", parse_mode="Markdown")
    await season_check_job(context)
    await update.message.reply_text("✅ *Sezon başarıyla kapatıldı!*", parse_mode="Markdown")

async def cmd_sezon_sifirla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Mevcut sezonu sıfırla — sezon numarası aynı kalır, her şey resetlenir."""
    if not is_admin(update.effective_user.id):
        return

    season = db.get_active_season()
    if not season:
        return await update.message.reply_text("❌ Aktif sezon yok.")
    season_no, start_date, end_date = season

    if not (context.args and context.args[0] == "onayla"):
        return await update.message.reply_text(
            f"⚠️ *SEZON {season_no} SIFIRLAMA*\n\n"
            f"📋 *SIFIRLANACAKLAR:*\n"
            f"  • Tüm takım puanları (W/D/L)\n"
            f"  • Form ve sakatlıklar\n"
            f"  • Mevcut fikstür\n"
            f"  • Kiralık oyuncular\n"
            f"  • Pazar ilanları\n"
            f"  • Bekleyen teklifler\n"
            f"  • Antrenörler serbest\n"
            f"  • Tahmin geçmişi\n"
            f"  • Sosyal medya tepkileri\n"
            f"  • Konversiyon limiti\n\n"
            f"💎 *KORUNACAKLAR:*\n"
            f"  • Sezon numarası ({season_no})\n"
            f"  • LC bakiyeler\n"
            f"  • Kadrolardaki oyuncular\n"
            f"  • Oyuncu rating'leri\n"
            f"  • Şampiyon geçmişi\n\n"
            f"💡 Onaylamak için: `/sezon_sifirla onayla`",
            parse_mode="Markdown")

    from datetime import datetime, timedelta
    msg = await update.message.reply_text("⏳ *Sezon sıfırlanıyor...*", parse_mode="Markdown")

    # Manuel sıfırlama — her SQL ayrı transaction, hata olursa diğerlerini etkilemez
    from database import connect, ph
    p = ph()
    new_start = datetime.now()
    new_end = new_start + timedelta(days=30)

    def _safe_sql(query, params=()):
        """Her SQL'i ayrı bağlantıda çalıştır, hata olursa atla."""
        try:
            with connect() as conn:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
            return True
        except Exception as e:
            print(f"[SEZON_SIFIRLA] '{query[:40]}...' hata: {e}")
            return False

    try:
        # 1. Takım puanları
        _safe_sql("UPDATE lig_teams SET wins=0, draws=0, losses=0, goals_for=0, goals_against=0, form=0, recent_results=''")
        # 2. Form ve sakatlık
        _safe_sql("UPDATE lig_squad SET form=0, injury_matches=0")
        # 3. Konversiyon
        _safe_sql("DELETE FROM lig_conversion")
        # 4. Antrenörler
        _safe_sql("UPDATE lig_coaches SET active=0")
        # 5. Tatil
        _safe_sql("DELETE FROM player_vacation")
        # 6. Kiralık
        _safe_sql("UPDATE player_loans SET active=0")
        # 7. Pazar
        _safe_sql("UPDATE market_listings SET sold=1 WHERE sold=0")
        # 8. Teklifler
        _safe_sql("UPDATE player_offers SET status='expired' WHERE status='pending'")
        # 9. Antrenman
        _safe_sql("DELETE FROM lig_training")
        # 10. Sözleşmeler
        _safe_sql("DELETE FROM lig_contracts")
        # 11. Form aksiyonları
        _safe_sql("DELETE FROM form_actions")
        # 12. Sosyal medya
        _safe_sql("DELETE FROM social_reactions")
        # 13. Haberler
        _safe_sql("DELETE FROM lig_news")
        # 14. Tahminler
        _safe_sql("DELETE FROM lig_predictions")
        # 15. Eski fikstür
        _safe_sql(f"DELETE FROM lig_fixtures WHERE season_no={p}", (season_no,))
        # 16. Eski maç sonuçları
        _safe_sql(f"DELETE FROM lig_matches WHERE season_no={p}", (season_no,))
        # 17. Sezon tarihini güncelle
        _safe_sql(f"UPDATE lig_seasons SET start_date={p}, end_date={p} WHERE season_no={p}",
                  (new_start.isoformat(), new_end.isoformat(), season_no))

        # 18. Yeni fikstür oluştur
        teams = db.get_all_teams_ranked()
        if teams and len(teams) >= 2:
            team_ids = [t[0] for t in teams]
            count = db.generate_fixtures(season_no, team_ids, new_start)
            await msg.edit_text(
                f"✅ *SEZON {season_no} SIFIRLANDI!*\n\n"
                f"📊 *Sıfırlananlar:*\n"
                f"  • Puanlar, form, sakatlıklar\n"
                f"  • Konversiyon limiti (2.5M)\n"
                f"  • Antrenörler serbest\n"
                f"  • Market, teklifler, kiralık\n\n"
                f"📅 *Yeni Fikstür:* {count} maç oluşturuldu\n"
                f"💪 *{len(teams)}* takım katılıyor\n\n"
                f"💡 `/fikstur` ile gör!",
                parse_mode="Markdown")

            # Gruba duyuru
            duyuru = (
                f"╔══════════════════════╗\n"
                f"║ 🔄 SEZON {season_no} YENİDEN BAŞLADI! ║\n"
                f"╚══════════════════════╝\n\n"
                f"📊 Tüm puanlar sıfırlandı!\n"
                f"🏆 Şampiyonluk yarışı tekrar başladı!\n"
                f"⚽ Yeni fikstür: *{count} maç*\n\n"
                f"💪 İyi şanslar Budunlular!"
            )
            await _send_to_broadcast_chats(context, duyuru, category="lig")
        else:
            await msg.edit_text("✅ Sezon sıfırlandı ama fikstür için 2+ takım gerekli.", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Hata: `{e}`", parse_mode="Markdown")

async def cmd_lig_sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Kullanıcının sadece LİG verilerini sil."""
    if not is_admin(update.effective_user.id):
        return
    target_id = None
    target_name = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        if context.args[0].startswith("@"):
            user = db.get_user_by_username(context.args[0][1:])
            if user:
                target_id = user[0]
                target_name = user[1]
        else:
            try: target_id = int(context.args[0])
            except: pass

    if not target_id:
        return await update.message.reply_text(
            "💡 Kullanım:\n"
            "• Yanıtla: `/lig_sil`\n"
            "• `/lig_sil @kullanici`\n"
            "• `/lig_sil <user_id>`\n\n"
            "⚠️ Kullanıcının tüm lig verilerini siler (takım, kadro, fikstür, teklifler, kiralık, vs.)",
            parse_mode="Markdown")

    team = db.get_team(target_id)
    if not team:
        return await update.message.reply_text("❌ Hedef kullanıcının lig hesabı yok.")

    deleted = db.delete_lig_data(target_id)
    total = sum(deleted.values())

    await update.message.reply_text(
        f"✅ *Lig verileri silindi!*\n\n"
        f"👤 Hedef: `{target_name or target_id}` (ID: `{target_id}`)\n"
        f"🏟️ Takım: *{team[0]}*\n\n"
        f"📊 *SİLİNEN:*\n"
        f"  • Takım: {deleted.get('team', 0)}\n"
        f"  • Kadro: {deleted.get('squad', 0)} oyuncu\n"
        f"  • Fikstür: {deleted.get('fixtures', 0)}\n"
        f"  • Teklifler: {deleted.get('offers', 0)}\n"
        f"  • Pazar ilanları: {deleted.get('listings', 0)}\n"
        f"  • Kiralık: {deleted.get('loans', 0)}\n"
        f"  • Tahminler: {deleted.get('predictions', 0)}\n"
        f"  • Diğer: {total - sum([deleted.get(k, 0) for k in ['team','squad','fixtures','offers','listings','loans','predictions']])}\n\n"
        f"💡 Casino hesabı korundu.",
        parse_mode="Markdown")

async def cmd_lig_oyuncular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Ligde kayıtlı tüm oyuncuları listele — username, ID, takım, LC."""
    if not is_admin(update.effective_user.id):
        return

    teams = db.get_all_teams_ranked()
    if not teams:
        return await update.message.reply_text("❌ Ligde kayıtlı takım yok.")

    page = 0
    if context.args:
        try: page = max(0, int(context.args[0]) - 1)
        except: pass

    per_page = 10
    total    = len(teams)
    start    = page * per_page
    slice_   = teams[start:start + per_page]
    total_pages = max(1, (total - 1) // per_page + 1)

    medals = ["🥇", "🥈", "🥉"]
    text = (
        f"╔══════════════════════╗\n"
        f"║  📋  LİG OYUNCULARI  ║\n"
        f"╚══════════════════════╝\n\n"
        f"👥 Toplam: *{total}* takım  |  Sayfa: *{page+1}/{total_pages}*\n\n"
    )

    for i, t in enumerate(slice_, start + 1):
        uid_t, tname, w, d, l, gf, ga, pts = t
        em = medals[i-1] if i <= 3 else f"{i}."
        try:    lc = db.get_lc_balance(uid_t)
        except: lc = 0
        username     = db.get_owner_username(uid_t)
        squad_count  = len(db.get_squad(uid_t))
        text += (
            f"{em} *{tname[:18]}*\n"
            f"   👤 *{username}*\n"
            f"   🆔 `{uid_t}` | 💎 {lc:,} LC\n"
            f"   🏆 {pts}p ({w}G {d}B {l}M) | 👥 {squad_count} oyuncu\n\n"
        )

    nav = []
    if page > 0:          nav.append(f"`/lig_oyuncular {page}` ←")
    if start+per_page < total: nav.append(f"→ `/lig_oyuncular {page+2}`")
    if nav: text += " | ".join(nav) + "\n"
    text += f"\n🗑️ Çıkarmak için: `/lig_sil <user_id>`"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_ilk11(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mevcut ilk 11'i göster."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce `/takim_kur <isim>` ile takım kur!", parse_mode="Markdown")

    squad = db.get_squad(uid)
    if not squad:
        return await update.message.reply_text("❌ Kadron boş! `/market` ile oyuncu al.", parse_mode="Markdown")

    starters = [p for p in squad if p[3] == 1]
    bench    = [p for p in squad if p[3] == 0]
    auto_msg = ""

    if not starters:
        sorted_sq = sorted(squad, key=lambda x: -x[1])
        starters  = sorted_sq[:11]
        bench     = sorted_sq[11:]
        auto_msg  = "⚙️ _Otomatik seçim (rating'e göre)_\n\n"

    pos_em   = {"GK":"🧤","DEF":"🛡️","MID":"⚙️","FWD":"⚔️"}
    pos_name = {"GK":"Kale","DEF":"Defans","MID":"Orta Saha","FWD":"Forvet"}

    by_pos = {"GK":[],"DEF":[],"MID":[],"FWD":[]}
    for p in starters:
        if p[2] in by_pos: by_pos[p[2]].append(p)

    text = (
        f"╔══════════════════════╗\n"
        f"║  ⚽  İLK 11  ║\n"
        f"╚══════════════════════╝\n\n"
        f"{auto_msg}"
    )
    for pos in ["GK","DEF","MID","FWD"]:
        if by_pos[pos]:
            text += f"{pos_em[pos]} *{pos_name[pos]}:*\n"
            for p in by_pos[pos]:
                text += f"  • {p[0]}  `{p[1]}`\n"
            text += "\n"

    if bench:
        text += "🪑 *Yedekler:*\n"
        for p in bench[:4]:
            text += f"  • {p[0]} `{p[1]}` ({p[2]})\n"

    text += (
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 `/ilk11_ekle <oyuncu>` — ekle\n"
        "💡 `/ilk11_cikar <oyuncu>` — çıkar\n"
        "💡 `/ilk11_sifirla` — otomatik moda dön"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_ilk11_ekle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyuncuyu ilk 11'e ekle (is_starter=1)."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")
    if not context.args:
        return await update.message.reply_text("💡 `/ilk11_ekle <oyuncu adı>`", parse_mode="Markdown")

    player_name = " ".join(context.args)
    squad = db.get_squad(uid)
    target = next((p for p in squad if player_name.lower() in p[0].lower()), None)
    if not target:
        return await update.message.reply_text(f"❌ *{player_name}* kadronda yok!", parse_mode="Markdown")

    starters = [p for p in squad if p[3] == 1]
    if len(starters) >= 11:
        return await update.message.reply_text(
            f"❌ İlk 11 dolu! ({len(starters)}/11)\n`/ilk11_cikar <oyuncu>` ile yer aç.",
            parse_mode="Markdown")
    if target[2] == "GK" and any(p[2]=="GK" for p in starters):
        return await update.message.reply_text(
            "❌ Zaten bir kaleci var! Önce onu çıkar.", parse_mode="Markdown")
    if target[3] == 1:
        return await update.message.reply_text(
            f"❌ *{target[0]}* zaten ilk 11'de!", parse_mode="Markdown")

    from database import connect, ph as _ph
    _p = _ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE lig_squad SET is_starter=1 WHERE user_id={_p} AND LOWER(player_name)=LOWER({_p})",
            (uid, target[0]))
        conn.commit()

    pos_em = {"GK":"🧤","DEF":"🛡️","MID":"⚙️","FWD":"⚔️"}.get(target[2],"⚽")
    await update.message.reply_text(
        f"✅ *{target[0]}* ilk 11'e eklendi!\n"
        f"{pos_em} {target[2]} | `{target[1]}` rating\n"
        f"👥 İlk 11: *{len(starters)+1}/11*",
        parse_mode="Markdown")


async def cmd_ilk11_cikar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oyuncuyu ilk 11'den çıkar (is_starter=0)."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")
    if not context.args:
        return await update.message.reply_text("💡 `/ilk11_cikar <oyuncu adı>`", parse_mode="Markdown")

    player_name = " ".join(context.args)
    squad  = db.get_squad(uid)
    target = next((p for p in squad if player_name.lower() in p[0].lower()), None)
    if not target:
        return await update.message.reply_text(f"❌ *{player_name}* kadronda yok!", parse_mode="Markdown")

    from database import connect, ph as _ph
    _p = _ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE lig_squad SET is_starter=0 WHERE user_id={_p} AND LOWER(player_name)=LOWER({_p})",
            (uid, target[0]))
        conn.commit()

    await update.message.reply_text(
        f"✅ *{target[0]}* ilk 11'den çıkarıldı → yedek.", parse_mode="Markdown")


async def cmd_ilk11_sifirla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İlk 11 seçimini sıfırla — otomatik moda dön."""
    uid = update.effective_user.id
    if not db.get_team(uid):
        return await update.message.reply_text("❌ Önce takım kur!", parse_mode="Markdown")

    from database import connect, ph as _ph
    _p = _ph()
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE lig_squad SET is_starter=0 WHERE user_id={_p}", (uid,))
        conn.commit()

    await update.message.reply_text(
        "✅ *İlk 11 sıfırlandı!*\n"
        "Artık en yüksek ratingli 11 oyuncu otomatik seçilir.",
        parse_mode="Markdown")


async def cmd_macbaslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Maçları hemen başlat. Herkes: Ne zaman başlıyor?"""
    uid = update.effective_user.id
    if not is_admin(uid):
        return await update.message.reply_text(
            "⚽ *MAÇLAR NE ZAMAN BAŞLIYOR?*\n\n"
            "Her gün saat *21:00* otomatik başlar.\n"
            "📅 `/fikstur` ile bugünkü maçları gör.\n"
            "🎯 `/tahmin` ile 20:30-21:00 arası tahmin yap!",
            parse_mode="Markdown")

    msg = await update.message.reply_text("⚽ *Maçlar başlatılıyor...*", parse_mode="Markdown")
    try:
        await daily_match_job(context)
        await msg.edit_text("✅ *Bugünkü maçlar oynandı!*", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Hata: `{e}`", parse_mode="Markdown")


async def cmd_lig_tam_sifirla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: TÜM ligi sıfırla — sezon 1'den başlat, tüm takımlar/veriler silinir."""
    if not is_admin(update.effective_user.id):
        return

    if not (context.args and context.args[0] == "EVET"):
        teams = db.get_all_teams_ranked()
        team_count = len(teams) if teams else 0
        return await update.message.reply_text(
            f"⚠️ *TAM LİG SIFIRLAMA*\n\n"
            f"🚨 Bu işlem geri alınamaz!\n\n"
            f"📊 *SİLİNECEK HER ŞEY:*\n"
            f"  • {team_count} takım ve tüm kadroları\n"
            f"  • Tüm sezon geçmişi\n"
            f"  • Şampiyon geçmişi\n"
            f"  • Tüm fikstürler\n"
            f"  • LC bakiyeler (sıfırlanır)\n"
            f"  • Tüm teklifler, kiralıklar\n"
            f"  • Tüm haberler, sosyal medya\n"
            f"  • Tüm tahminler\n\n"
            f"🆕 *Sonuç:* Sezon 1'den temiz başlangıç\n\n"
            f"✅ Onaylamak için:\n"
            f"`/lig_tam_sifirla EVET`",
            parse_mode="Markdown")

    msg = await update.message.reply_text("⏳ *Lig tamamen sıfırlanıyor...*\n\n`[          ]` %0", parse_mode="Markdown")

    from database import connect, ph
    p = ph()

    # Her tablo AYRI connection ile siliniyor
    # PostgreSQL'de bir tablo hata verince diğerleri etkilenmiyor
    def _safe_delete(table: str) -> tuple[bool, str]:
        try:
            with connect() as conn:
                cur = conn.cursor()
                cur.execute(f"DELETE FROM {table}")
                conn.commit()
            return True, ""
        except Exception as e:
            return False, str(e)

    tables_to_clear = [
        "lig_squad",           # önce kadro (foreign key)
        "lig_fixtures",
        "lig_matches",
        "lig_season_stats",
        "lig_conversion",
        "lig_coaches",
        "lig_training",
        "lig_contracts",
        "player_vacation",
        "player_loans",
        "market_listings",
        "player_offers",
        "form_actions",
        "social_reactions",
        "lig_news",
        "lig_predictions",
        "lig_mvp_log",
        "lig_teams",           # takımlar en son
        "lig_seasons",         # sezonlar en son
        "lig_champions",
    ]

    ok_count  = 0
    err_list  = []
    total_tbl = len(tables_to_clear)

    for i, tbl in enumerate(tables_to_clear):
        success, err = _safe_delete(tbl)
        if success:
            ok_count += 1
        else:
            err_list.append(f"{tbl}: {err[:40]}")

        # Her 5 tabloda bir ilerleme göster
        if i % 5 == 0:
            pct = int((i / total_tbl) * 100)
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            try:
                await msg.edit_text(
                    f"⏳ *Sıfırlanıyor...*\n\n`[{bar}]` %{pct}\n_{tbl} temizlendi..._",
                    parse_mode="Markdown")
            except: pass

    # Sezon 1 oluştur — ayrı connection
    from datetime import datetime, timedelta
    new_start = datetime.now()
    new_end   = new_start + timedelta(days=30)
    sezon_ok  = False
    try:
        with connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO lig_seasons (season_no, start_date, end_date, is_active) "
                f"VALUES ({p},{p},{p},1)",
                (1, new_start.isoformat(), new_end.isoformat()))
            conn.commit()
        sezon_ok = True
    except Exception as e:
        err_list.append(f"Sezon1: {e}")

    # Sonuç mesajı
    result = (
        f"✅ *LİG TAMAMEN SIFIRLANDI!*\n\n"
        f"🗑️ *{ok_count}/{total_tbl}* tablo temizlendi\n"
        f"{'✅' if sezon_ok else '❌'} Sezon 1 oluşturuldu\n"
        f"📅 Bitiş: *{new_end.strftime('%d.%m.%Y')}*\n\n"
        f"📋 *Sıradaki adımlar:*\n"
        f"  1️⃣ Oyuncular `/takim_kur <isim>` ile kayıt olsun\n"
        f"  2️⃣ `/fikstur_olustur` ile fikstür oluştur\n"
        f"  3️⃣ Maçlar her gün 21:00'da otomatik başlar\n"
    )
    if err_list:
        result += f"\n⚠️ *{len(err_list)} hata (tablo yoksa normaldir):*\n"
        for e in err_list[:4]:
            result += f"  _{e}_\n"

    await msg.edit_text(result, parse_mode="Markdown")

    # Gruba duyuru
    try:
        await _send_to_broadcast_chats(
            context,
            "🔄 *TÜRK BUDUN LİGİ YENİDEN BAŞLIYOR!*\n\n"
            "🆕 *Sezon 1* — Herkes sıfırdan başlıyor!\n"
            "⚽ Takımını kur: `/takim_kur <takım adı>`\n"
            "💎 Başlangıç bütçesi: *500.000 LC*\n\n"
            "🏆 Kim şampiyon olacak?",
            category="lig")
    except: pass


async def cmd_lig_yayin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bu konuyu/grubu lig mesajları için ayarla."""
    if not is_admin(update.effective_user.id):
        return
    chat_id   = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message.is_topic_message else None

    # Bellekte kaydet
    if chat_id not in BROADCAST_TOPICS:
        BROADCAST_TOPICS[chat_id] = {"lig": None, "casino": None}
    BROADCAST_TOPICS[chat_id]["lig"] = thread_id
    LIG_BROADCAST_CHATS.add(chat_id)

    # DB'ye kalıcı kaydet
    try:
        db.save_broadcast_setting(chat_id, "lig", thread_id)
        db_ok = "✅ DB kaydı başarılı"
    except Exception as e:
        db_ok = f"⚠️ DB kayıt hatası: {e}"

    where = f"konu thread `{thread_id}`" if thread_id else "ana sohbet"
    await update.message.reply_text(
        f"✅ *Lig yayın kanalı ayarlandı!*\n\n"
        f"📺 *Nereye gidecek:* {where}\n"
        f"💾 {db_ok}\n"
        f"🆔 Chat ID: `{chat_id}`\n\n"
        f"📋 *Buraya gelecek mesajlar:*\n"
        f"  • Günlük maç önizleme (10:00)\n"
        f"  • Maç öncesi analiz (20:30)\n"
        f"  • Canlı maç yayını (21:00)\n"
        f"  • Maç sonuçları & haberler\n"
        f"  • Sezon ödülleri\n\n"
        f"💡 Test için: `/yayin_test`",
        parse_mode="Markdown")

    print(f"[YAYIN] ✅ Lig kanalı ayarlandı: chat={chat_id} thread={thread_id}")


async def cmd_yayin_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Yayın kanalına test mesajı gönder."""
    if not is_admin(update.effective_user.id):
        return

    if not BROADCAST_TOPICS and not LIG_BROADCAST_CHATS:
        return await update.message.reply_text(
            "❌ *Yayın kanalı ayarlanmamış!*\n\n"
            "📋 Önce bu kanalda `/lig_yayin` komutunu çalıştır.",
            parse_mode="Markdown")

    await update.message.reply_text("📤 Test mesajı gönderiliyor...", parse_mode="Markdown")

    test_msg = (
        "📡 *YAYIN TESTİ*\n\n"
        "✅ Lig botu bu kanala bağlı!\n"
        "🏟️ Maç yayınları buraya gelecek.\n\n"
        "⚽ *Türk Budun Ligi*"
    )

    sent = await _send_to_broadcast_chats(context, test_msg, category="lig")

    if sent:
        await update.message.reply_text(
            f"✅ *Test başarılı!*\n"
            f"📤 {len(sent)} kanala gönderildi: `{list(sent)}`",
            parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "❌ *Hiçbir yere gönderilemedi!*\n\n"
            "Railway loglarına bak, hata detayı orada.",
            parse_mode="Markdown")




# ─────────────────────────────────────────────────────────────
# FİKSTÜR + TAHMİN KOMUTLARI
# ─────────────────────────────────────────────────────────────

async def cmd_casino_yayin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bu konuyu casino mesajları için ayarla."""
    if not is_admin(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id if update.message.is_topic_message else None

    if chat_id not in BROADCAST_TOPICS:
        BROADCAST_TOPICS[chat_id] = {"lig": None, "casino": None}
    BROADCAST_TOPICS[chat_id]["casino"] = thread_id
    db.save_broadcast_setting(chat_id, "casino", thread_id)

    where = f"konu (thread {thread_id})" if thread_id else "ana sohbet"
    await update.message.reply_text(
        f"✅ *Casino yayın kanalı ayarlandı!*\n"
        f"📺 Mesajlar buraya ({where}) gelecek:\n"
        f"  • Bot konuşmaları\n"
        f"  • Haftalık cashback duyurusu\n"
        f"💾 Kalıcı kaydedildi.",
        parse_mode="Markdown")

async def cmd_yayin_durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mevcut yayın ayarlarını göster."""
    if not is_admin(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    config = BROADCAST_TOPICS.get(chat_id, {})

    cas_t = config.get("casino")

    text = (
        "╔══════════════════════╗\n"
        "║  📺  YAYIN DURUMU  ║\n"
        "╚══════════════════════╝\n\n"
        f"🏟️ *Lig:* "
    )
    if lig_t is not None:
        text += f"konu thread `{lig_t}`\n"
    elif chat_id in LIG_BROADCAST_CHATS:
        text += f"ana sohbet ✅\n"
    else:
        text += f"❌ ayarlanmadı\n"

    text += f"🎰 *Casino:* "
    if cas_t is not None:
        text += f"konu thread `{cas_t}`\n"
    elif config.get("casino") is None and chat_id in BROADCAST_TOPICS:
        text += f"ana sohbet ✅\n"
    else:
        text += f"❌ ayarlanmadı\n"

    text += (
        "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Komutlar:*\n"
        "• `/lig_yayin` — Bu konuyu lig için ayarla\n"
        "• `/casino_yayin` — Bu konuyu casino için ayarla\n\n"
        "_Forum grubu kullanıyorsan istediğin konuda komutu yaz, mesajlar o konuya gelir._"
    )

    await update.message.reply_text(text, parse_mode="Markdown")

# ════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════

def main():
    # DB tablolarını başlat
    db.init_db()
    db.init_lig_tables()
    db.init_lc_codes_table()
    db.init_mvp_table()
    db.init_season_tables()
    db.init_conversion_table()
    db.init_fixture_tables()
    db.init_extra_tables()
    db.init_cashback_table()
    db.init_bank_table()
    db.init_broadcast_table()
    db.init_market_tables()
    db.init_extras2_tables()
    db.init_form_eco_tables()
    db.init_weekly_tasks_table()
    db.init_game_stats_table()

    # Yayın ayarlarını yükle
    global BROADCAST_TOPICS
    BROADCAST_TOPICS = db.get_all_broadcast_settings()
    for cid in BROADCAST_TOPICS:
        LIG_BROADCAST_CHATS.add(cid)
    print(f"[YAYIN] {len(BROADCAST_TOPICS)} chat yüklendi")

    app = Application.builder().token(TOKEN).build()

    # Komutlar
    commands = [
        ("start",           cmd_start),
        ("yardim",          cmd_yardim),
        ("lig",             cmd_lig),
        ("takim_kur",       cmd_takim_kur),
        ("takimim",         cmd_takimim),
        ("form",            cmd_form),
        ("market",          cmd_market),
        ("transfer",        cmd_transfer),
        ("sat",             cmd_sat),
        ("akademi",         cmd_akademi),
        ("akademi_al",      cmd_akademi_al),
        ("antrenman",       cmd_antren),
        ("antrenor",        cmd_antrenor),
        ("hoca_tut",        cmd_hoca_tut),
        ("hoca_birak",      cmd_hoca_birak),
        ("fizyo",           cmd_fizyo),
        ("motivasyon",      cmd_motivasyon),
        ("tatil",           cmd_tatil),
        ("kamp",            cmd_kamp),
        ("kaptan",          cmd_kaptan),
        ("taktik",          cmd_taktik),
        ("dizilis",         cmd_dizilis),
        ("taktik_sec",      cmd_taktik_sec),
        ("teklif",          cmd_teklif),
        ("teklif_kabul",    cmd_teklif_kabul),
        ("teklif_red",      cmd_teklif_red),
        ("teklif_karsi",    cmd_teklif_karsi),
        ("kirala",          cmd_kirala),
        ("sat_pazar",       cmd_sat_pazar),
        ("pazar",           cmd_pazar),
        ("pazardan_al",     cmd_pazardan_al),
        ("rakip",           cmd_rakip),
        ("lig_top",         cmd_lig_top),
        ("puandurumu",      cmd_lig_top),
        ("ligler",          cmd_ligler),
        ("sampiyonlar",     cmd_sampiyonlar),
        ("fikstur",         cmd_fikstur),
        ("tahmin",          cmd_tahmin),
        ("haberler",        cmd_haberler),
        ("sosyal",          cmd_sosyal),
        ("kur",             cmd_kur),
        ("cevir",           cmd_cevir),
        ("lc_bakiye",       cmd_lc_bakiye),
        ("lc_kod",          cmd_lc_kod),
        # Admin
        ("lc_yukle",        cmd_lc_yukle),
        ("lc_dusur",        cmd_lc_dusur),
        ("lc_toplu_yukle",  cmd_lc_toplu_yukle),
        ("lc_kodolustur",   cmd_lc_kodolustur),
        ("terfi_dusme",     cmd_terfi_dusme),
        ("fikstur_olustur", cmd_fikstur_olustur),
        ("maclari_basla",   cmd_maclari_basla),
        ("macbaslat",       cmd_macbaslat),
        ("sezon_bitir",     cmd_sezon_bitir),
        ("ilk11",           cmd_ilk11),
        ("ilk11_ekle",      cmd_ilk11_ekle),
        ("ilk11_cikar",     cmd_ilk11_cikar),
        ("ilk11_sifirla",   cmd_ilk11_sifirla),
        ("sezon_sifirla",   cmd_sezon_sifirla),
        ("lig_sil",          cmd_lig_sil),
        ("lig_oyuncular",   cmd_lig_oyuncular),
        ("lig_tam_sifirla", cmd_lig_tam_sifirla),
        ("lig_yayin",       cmd_lig_yayin),
        ("yayin_test",      cmd_yayin_test),
        ("casino_yayin",    cmd_casino_yayin),
        ("yayin_durum",     cmd_yayin_durum),
    ]

    for cmd, handler in commands:
        try:
            app.add_handler(CommandHandler(cmd, handler))
        except Exception as e:
            print(f"[WARN] /{cmd} eklenemedi: {e}")

    # Callback handlers
    try:
        app.add_handler(CallbackQueryHandler(tahmin_callback, pattern=r"^tahmin_"))
    except: pass

    # Job queue
    if app.job_queue:
        app.job_queue.run_daily(
            daily_match_job,
            time=dtime(hour=18, minute=0, tzinfo=timezone.utc),
            name="daily_matches")
        app.job_queue.run_repeating(season_check_job,            interval=3600, first=60,  name="season_check")
        app.job_queue.run_repeating(morning_news_job,            interval=60,   first=30,  name="morning_news")
        app.job_queue.run_repeating(noon_news_job,               interval=60,   first=60,  name="noon_news")
        app.job_queue.run_repeating(evening_news_job,            interval=60,   first=90,  name="evening_news")
        app.job_queue.run_repeating(prematch_announcement_job,   interval=60,   first=120, name="prematch")
        app.job_queue.run_repeating(countdown_match_job,         interval=60,   first=200, name="countdown")

    print("🏟️ Lig Botu aktif — v3.1 Elite")

    # ── Telegram "/" menüsü için komut listesi ──
    from telegram import BotCommand
    lig_commands = [
        BotCommand("start",          "🏟️ Botu başlat"),
        BotCommand("lig",            "📋 Takım ana ekranı"),
        BotCommand("takim_kur",      "⚽ Takım kur — /takim_kur AdınFC"),
        BotCommand("takimim",        "👥 Kadroyu gör"),
        BotCommand("lc_bakiye",      "💎 LC bakiyeni gör"),
        BotCommand("market",         "🛒 Transfer marketi"),
        BotCommand("transfer",       "✅ Oyuncu satın al — /transfer Haaland"),
        BotCommand("sat",            "💸 Oyuncu sat"),
        BotCommand("akademi",        "🎓 Ucuz genç oyuncular"),
        BotCommand("akademi_al",     "🎓 Akademiden oyuncu al"),
        BotCommand("pazar",          "🏪 Diğer takımların oyuncu ilanları"),
        BotCommand("sat_pazar",      "🏪 Oyuncunu pazara koy"),
        BotCommand("pazardan_al",    "🏪 Pazardan oyuncu satın al"),
        BotCommand("teklif",         "🤝 Oyuncu için teklif yap"),
        BotCommand("teklif_kabul",   "✅ Teklifi kabul et"),
        BotCommand("teklif_red",     "❌ Teklifi reddet"),
        BotCommand("teklif_karsi",   "🔄 Karşı teklif yap"),
        BotCommand("kirala",         "📋 4 maçlık kiralama teklifi"),
        BotCommand("antrenor",       "👔 Antrenör marketi"),
        BotCommand("hoca_tut",       "👔 Antrenör tut"),
        BotCommand("hoca_birak",     "👔 Antrenörü sal"),
        BotCommand("antrenman",      "🏋️ Oyuncu antrene et — günde 2x"),
        BotCommand("form",           "📊 Tüm kadronun form durumu"),
        BotCommand("fizyo",          "💊 Form +2 garantili — 10.000 LC"),
        BotCommand("motivasyon",     "🗣️ Ücretsiz rastgele form denemesi"),
        BotCommand("tatil",          "🏖️ Form sıfırla — 1 maç gıyabi"),
        BotCommand("kamp",           "🏕️ Tüm kadro form +1 — 50.000 LC"),
        BotCommand("kaptan",         "🅰️ Kaptan seç"),
        BotCommand("ilk11",          "⚽ İlk 11i gör"),
        BotCommand("ilk11_ekle",     "➕ İlk 11e oyuncu ekle"),
        BotCommand("ilk11_cikar",    "➖ İlk 11den oyuncu çıkar"),
        BotCommand("ilk11_sifirla",  "🔄 İlk 11i otomatik moda al"),
        BotCommand("taktik",         "⚙️ Taktik merkezi"),
        BotCommand("dizilis",        "📐 Diziliş değiştir — 4-3-3 / 4-4-2 / 5-3-2"),
        BotCommand("taktik_sec",     "🎯 Taktik seç — hucum/defans/dengeli/pres"),
        BotCommand("lig_top",        "🏆 Anlık puan durumu"),
        BotCommand("ligler",         "🏆 Tüm lig kademeleri"),
        BotCommand("sampiyonlar",    "🥇 Geçmiş sezon şampiyonları"),
        BotCommand("fikstur",        "📅 Fikstür — /fikstur bugun/yarin/tum"),
        BotCommand("tahmin",         "🎯 Skor tahmini — 20:30 ile 21:00 arası"),
        BotCommand("rakip",          "🔍 Rakip profili ve analizi"),
        BotCommand("macbaslat",      "⚽ Maçlar ne zaman başlıyor"),
        BotCommand("haberler",       "📰 Son lig haberleri"),
        BotCommand("sosyal",         "📱 Sosyal medya tepkileri"),
        BotCommand("kur",            "💱 Anlık LC döviz kuru"),
        BotCommand("cevir",          "💱 Casino coin LC ye çevir"),
        BotCommand("lc_kod",         "🎁 LC hediye kodu kullan"),
        BotCommand("yardim",         "❓ Tüm komutlar"),
    ]

    async def _set_commands(application):
        try:
            await application.bot.set_my_commands(lig_commands)
            print("[BOT] ✅ Komut listesi Telegram'a yüklendi")
        except Exception as e:
            print(f"[BOT] ⚠️ Komut listesi yüklenemedi: {e}")

    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(
            app.bot.set_my_commands(lig_commands)
        )
        print("[BOT] ✅ Komut listesi Telegram'a yüklendi")
    except Exception as e:
        print(f"[BOT] ⚠️ Komut listesi yüklenemedi: {e}")

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
