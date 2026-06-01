"""
CUMHURİYETÇİLER LİG BOTU
Sadece lig komutları — Casino botundan ayrılmış sürüm
"""
import os
import asyncio
import logging
from datetime import time as dtime, timezone
from dotenv import load_dotenv

load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

import database as db
import lig as lig_module

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN    = os.getenv("LIG_BOT_TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "6084870602").split(",")))

def is_admin(uid): return uid in ADMIN_IDS

def tr_now():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=3)))

# Yayın sistemi
BROADCAST_TOPICS = {}
LIG_BROADCAST_CHATS = set()

async def _send_to_broadcast_chats(context, text, parse_mode="Markdown", category="lig"):
    sent_to = set()
    for chat_id, topics in list(BROADCAST_TOPICS.items()):
        if chat_id in sent_to: continue
        thread_id = topics.get(category)
        try:
            kwargs = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
            if thread_id is not None:
                kwargs["message_thread_id"] = thread_id
            await context.bot.send_message(**kwargs)
            sent_to.add(chat_id)
        except:
            try:
                kwargs = {"chat_id": chat_id, "text": text}
                if thread_id is not None:
                    kwargs["message_thread_id"] = thread_id
                await context.bot.send_message(**kwargs)
                sent_to.add(chat_id)
            except: pass
    for chat_id in list(LIG_BROADCAST_CHATS):
        if chat_id in sent_to: continue
        try:
            await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            sent_to.add(chat_id)
        except: pass

async def _notify_admin(context, text, parse_mode="Markdown"):
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=f"🔔 {text}", parse_mode=parse_mode)
        except: pass
        break

# ─────────────────────────────────────────────────────────────
# TEMEL KOMUTLAR
# ─────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db.register_user(uid, update.effective_user.first_name)
    await update.message.reply_text(
        "🏟️ *CUMHURİYETÇİLER LİGİ*\n\n"
        "Takımını kur, oyuncuları transfer et, şampiyon ol!\n\n"
        "📋 Komutlar için /yardim\n"
        "🏟️ Lig ekranı için /lig",
        parse_mode="Markdown")

async def cmd_yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg1 = (
        "📋 LİG KOMUTLARI — 1/2\n\n"
        "BAŞLANGIÇ\n"
        "/lig — Lig ana ekranı\n"
        "/takim_kur — Takım kur (500K LC)\n"
        "/takimim — Kadronu gör\n"
        "/form — Kadronun form durumu\n\n"
        "TRANSFER\n"
        "/market — Bot marketi\n"
        "/transfer — Oyuncu al\n"
        "/sat — Oyuncu sat\n"
        "/akademi — Genç oyuncular\n"
        "/akademi_al — Genç oyuncu al\n\n"
        "PAZAR\n"
        "/teklif — Transfer teklifi\n"
        "/teklif_kabul /teklif_red /teklif_karsi\n"
        "/kirala — 4 maç kirala\n"
        "/sat_pazar — Pazara koy\n"
        "/pazar — Açık pazar\n"
        "/pazardan_al — Pazardan al\n\n"
        "GELİŞİM\n"
        "/antrenman — Oyuncu antrenmanı (3/gün)\n"
        "/antrenor — Antrenör marketi\n"
        "/hoca_tut /hoca_birak\n"
        "/fizyo — Form +2 (10K LC)\n"
        "/motivasyon — Rastgele form\n"
        "/tatil — Form sıfırla\n"
        "/kamp — Tüm kadro +1 form\n"
        "/kaptan — Kaptan ata"
    )
    msg2 = (
        "📋 LİG KOMUTLARI — 2/2\n\n"
        "TAKTİK\n"
        "/taktik — Taktik merkezi\n"
        "/dizilis — Diziliş değiştir\n"
        "/taktik_sec — Taktik seç\n\n"
        "SIRALAMA\n"
        "/lig_top — Anlık sıralama\n"
        "/puandurumu — Puan durumu\n"
        "/ligler — Tüm ligler\n"
        "/sampiyonlar — Şampiyon geçmişi\n\n"
        "MAÇ\n"
        "/fikstur — Fikstür\n"
        "/tahmin — Skor tahmini\n"
        "/rakip — Rakip profili\n"
        "/haberler — Lig haberleri\n"
        "/sosyal — Sosyal medya\n\n"
        "EKONOMİ\n"
        "/kur — LC borsa kuru\n"
        "/cevir — Casino coin → LC\n"
        "/lc_bakiye — LC bakiye\n"
        "/lc_kod — LC hediye kodu"
    )
    await update.message.reply_text(msg1)
    await update.message.reply_text(msg2)
    if is_admin(uid):
        await update.message.reply_text(
            "🔐 ADMIN\n\n"
            "/lc_yukle /lc_dusur /lc_toplu_yukle\n"
            "/lc_kodolustur /terfi_dusme\n"
            "/fikstur_olustur /maclari_basla\n"
            "/sezon_bitir /sezon_sifirla\n"
            "/lig_sil /kullanici_sil\n"
            "/lig_yayin /casino_yayin /yayin_durum"
        )

# ─────────────────────────────────────────────────────────────
# LİG KOMUTLARINI BOT.PY'DEN İMPORT ET
# ─────────────────────────────────────────────────────────────
# bot.py'deki tüm lig fonksiyonlarını burada tekrar yazmak yerine
# bot.py modülünden import ediyoruz

import sys
sys.path.insert(0, os.path.dirname(__file__))

# bot.py'deki fonksiyonları al
try:
    import bot as _bot_module
    # Lig komutları
    cmd_lig         = _bot_module.cmd_lig
    cmd_takim_kur   = _bot_module.cmd_takim_kur
    cmd_takimim     = _bot_module.cmd_takimim
    cmd_form        = _bot_module.cmd_form
    cmd_market      = _bot_module.cmd_market
    cmd_transfer    = _bot_module.cmd_transfer
    cmd_sat         = _bot_module.cmd_sat
    cmd_akademi     = _bot_module.cmd_akademi
    cmd_akademi_al  = _bot_module.cmd_akademi_al
    cmd_antrenman   = _bot_module.cmd_antrenman
    cmd_antrenor    = _bot_module.cmd_antrenor
    cmd_hoca_tut    = _bot_module.cmd_hoca_tut
    cmd_hoca_birak  = _bot_module.cmd_hoca_birak
    cmd_fizyo       = _bot_module.cmd_fizyo
    cmd_motivasyon  = _bot_module.cmd_motivasyon
    cmd_tatil       = _bot_module.cmd_tatil
    cmd_kamp        = _bot_module.cmd_kamp
    cmd_kaptan      = _bot_module.cmd_kaptan
    cmd_taktik      = _bot_module.cmd_taktik
    cmd_dizilis     = _bot_module.cmd_dizilis
    cmd_taktik_sec  = _bot_module.cmd_taktik_sec
    cmd_teklif      = _bot_module.cmd_teklif
    cmd_teklif_kabul= _bot_module.cmd_teklif_kabul
    cmd_teklif_red  = _bot_module.cmd_teklif_red
    cmd_teklif_karsi= _bot_module.cmd_teklif_karsi
    cmd_kirala      = _bot_module.cmd_kirala
    cmd_sat_pazar   = _bot_module.cmd_sat_pazar
    cmd_pazar       = _bot_module.cmd_pazar
    cmd_pazardan_al = _bot_module.cmd_pazardan_al
    cmd_rakip       = _bot_module.cmd_rakip
    cmd_lig_top     = _bot_module.cmd_lig_top
    cmd_puandurumu  = _bot_module.cmd_lig_top  # alias
    cmd_ligler      = _bot_module.cmd_ligler
    cmd_sampiyonlar = _bot_module.cmd_sampiyonlar
    cmd_fikstur     = _bot_module.cmd_fikstur
    cmd_tahmin      = _bot_module.cmd_tahmin
    cmd_haberler    = _bot_module.cmd_haberler
    cmd_sosyal      = _bot_module.cmd_sosyal
    cmd_kur         = _bot_module.cmd_kur
    cmd_cevir       = _bot_module.cmd_cevir
    cmd_lc_bakiye   = _bot_module.cmd_lc_bakiye
    cmd_lc_kod      = _bot_module.cmd_lc_kod
    # Admin
    cmd_lc_yukle        = _bot_module.cmd_lc_yukle
    cmd_lc_dusur        = _bot_module.cmd_lc_dusur
    cmd_lc_toplu_yukle  = _bot_module.cmd_lc_toplu_yukle
    cmd_lc_kodolustur   = _bot_module.cmd_lc_kodolustur
    cmd_terfi_dusme     = _bot_module.cmd_terfi_dusme
    cmd_fikstur_olustur = _bot_module.cmd_fikstur_olustur
    cmd_maclari_basla   = _bot_module.cmd_maclari_basla
    cmd_sezon_bitir     = _bot_module.cmd_sezon_bitir
    cmd_sezon_sifirla   = _bot_module.cmd_sezon_sifirla
    cmd_lig_sil         = _bot_module.cmd_lig_sil
    cmd_kullanici_sil   = _bot_module.cmd_kullanici_sil
    cmd_lig_yayin       = _bot_module.cmd_lig_yayin
    cmd_casino_yayin    = _bot_module.cmd_casino_yayin
    cmd_yayin_durum     = _bot_module.cmd_yayin_durum
    # Jobs
    daily_match_job         = _bot_module.daily_match_job
    season_check_job        = _bot_module.season_check_job
    morning_news_job        = _bot_module.morning_news_job
    noon_news_job           = _bot_module.noon_news_job
    evening_news_job        = _bot_module.evening_news_job
    prematch_announcement_job = _bot_module.prematch_announcement_job
    print("✅ bot.py'den komutlar yüklendi")
except Exception as e:
    print(f"❌ bot.py import hatası: {e}")

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
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

    # Yayın ayarlarını yükle
    global BROADCAST_TOPICS
    BROADCAST_TOPICS = db.get_all_broadcast_settings()
    for cid in BROADCAST_TOPICS:
        LIG_BROADCAST_CHATS.add(cid)
    print(f"[YAYIN] {len(BROADCAST_TOPICS)} chat ayarı yüklendi")

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
        ("antrenman",       cmd_antrenman),
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
        ("puandurumu",      cmd_puandurumu),
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
        ("sezon_bitir",     cmd_sezon_bitir),
        ("sezon_sifirla",   cmd_sezon_sifirla),
        ("lig_sil",         cmd_lig_sil),
        ("kullanici_sil",   cmd_kullanici_sil),
        ("lig_yayin",       cmd_lig_yayin),
        ("casino_yayin",    cmd_casino_yayin),
        ("yayin_durum",     cmd_yayin_durum),
    ]

    for cmd, handler in commands:
        try:
            app.add_handler(CommandHandler(cmd, handler))
        except Exception as e:
            print(f"[WARN] /{cmd} eklenemedi: {e}")

    # Job queue
    if app.job_queue:
        app.job_queue.run_daily(
            daily_match_job,
            time=dtime(hour=18, minute=0, tzinfo=timezone.utc),
            name="daily_matches")
        app.job_queue.run_repeating(season_check_job,  interval=3600,  first=60,  name="season_check")
        app.job_queue.run_repeating(morning_news_job,  interval=60,    first=30,  name="morning_news")
        app.job_queue.run_repeating(noon_news_job,     interval=60,    first=60,  name="noon_news")
        app.job_queue.run_repeating(evening_news_job,  interval=60,    first=90,  name="evening_news")
        app.job_queue.run_repeating(prematch_announcement_job, interval=60, first=120, name="prematch")

    print("🏟️ Lig Botu aktif — v3.1 Elite")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
