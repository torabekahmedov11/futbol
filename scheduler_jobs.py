from apscheduler.schedulers.background import BackgroundScheduler
import telebot
import db
import api_football
import scraper
import ai_translator
import json
import time
from telegraph_api import create_telegraph_page
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TARGET_CHANNEL_ID, CHANNEL_LINK, ADMIN_ID, BOT_TOKEN
from datetime import datetime
import requests

scheduler = BackgroundScheduler(timezone='Asia/Tashkent')

def send_admin_error(context, e):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": ADMIN_ID, "text": f"⚠️ JADVAL XATOSI!\nJoy: {context}\nXato: {str(e)[:500]}"}, timeout=5)
    except: pass

def fetch_rss_news(bot: telebot.TeleBot = None):
    """RSS orqali asosiy (fon) yangiliklarni yig'ish (Bema'lo bepul limit)"""
    # 6 soatdan eski postlarni avtomatik o'chirish
    db.purge_stale_queued_posts(max_age_hours=6)
    
    donors = [
        "http://feeds.bbci.co.uk/sport/football/rss.xml",
        "https://www.espn.com/espn/rss/soccer/news",
        "https://www.skysports.com/rss/12040"
    ]
    all_new_posts = []
    for donor in donors:
        try:
            posts = scraper.scrape_telegram_channel(donor, "")
            if len(posts) > 15: posts = posts[-15:]
            for p in posts:
                if not db.is_post_seen(p["id"]):
                    all_new_posts.append(p)
        except Exception as e:
            print(f"Skraping xatosi: {e}")
            send_admin_error("fetch_rss_news (Skraping)", e)

    added_new = False
    for p in all_new_posts:
        if p.get("text"):
            db.add_queued_post(p)
            db.set_last_id(p["id"])
            added_new = True

    # Saytda yangi post chiqsa jadvalni kutmasdan darsxod joylash (kunduzi)
    if added_new and bot:
        current_hour = datetime.now().hour
        if 7 <= current_hour < 23:
            print("Saytda yangi post topildi! Darsxod kanalga joylanmoqda...")
            process_queue_and_post(bot)

def queue_morning_fixtures(bot: telebot.TeleBot, force=False):
    """Ertalabki o'yinlar taqvimi va vaqtlarini xotiraga yuklash va anons berish"""
    fixtures = api_football.get_fixtures_for_date()
    if not fixtures: return

    text_data = "Bugungi o'yinlar jadvali:\n"
    start_times = []
    
    for f in fixtures:
        home = f['teams']['home']['name']
        away = f['teams']['away']['name']
        league = f['league']['name']
        match_time = f['fixture']['date']
        timestamp = f['fixture']['timestamp'] # UTC timestamp
        start_times.append(timestamp)
        text_data += f"- {league}: {home} vs {away} (Vaqti: {match_time})\n"
        
    db.set_today_fixtures_times(start_times)
    post_json = json.dumps({
        "type": "ANONS",
        "title": "🚨 Bugun bomba o'yinlar kutyapti!",
        "content": text_data
    })
    
    if force or not db.is_fixture_notified("anons_" + datetime.now().strftime('%Y%m%d')):
        # Sun'iy intellektga yuboramiz va to'g'ridan to'g'ri kanalga
        translated = ai_translator.translate_and_spice_up(post_json)
        db.add_notified_fixture("anons_" + datetime.now().strftime('%Y%m%d'))
        import random
        bg = random.choice([
            "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?q=80&w=800&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1518605368461-1e1c25143a41?q=80&w=800&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=800&auto=format&fit=crop"
        ])
        send_instant_post(bot, translated, bg)

def queue_yesterday_results(bot: telebot.TeleBot):
    """Kecha bo'lib o'tgan o'yinlar haqida yakuniy hisobot"""
    results = api_football.get_yesterday_results()
    if not results: return
    
    text_data = ""
    for r in results:
        home = r['teams']['home']['name']
        away = r['teams']['away']['name']
        score = f"{r['goals']['home']} - {r['goals']['away']}"
        league = r['league']['name']
        text_data += f"🏆 {league}: {home} {score} {away}\n"
        
    post_json = json.dumps({
        "type": "RESULT",
        "title": "🔥 Kechagi kunning qaynoq natijalari!",
        "content": text_data
    })
    
    if not db.is_fixture_notified("yesterday_" + datetime.now().strftime('%Y%m%d')):
        translated = ai_translator.translate_and_spice_up(post_json)
        db.add_notified_fixture("yesterday_" + datetime.now().strftime('%Y%m%d'))
        import random
        bg = random.choice([
            "https://images.unsplash.com/photo-1511886929837-354d827a426d?q=80&w=800&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=800&auto=format&fit=crop"
        ])
        send_instant_post(bot, translated, bg)

def check_live_matches(bot: telebot.TeleBot):
    """
    Tunda ham, kunduzi ham 24/7 ishlaydi. Jonli o'yin (Live) payti gollarni darhol uzatadi!
    """
    lives = api_football.get_live_scores()
    if not lives: return
    
    print(f"[{datetime.now()}] LIVE: Jonli o'yinlar hisobi tekshirilmoqda ({len(lives)} ta o'yin)...")
    for l in lives:
        fixture_id = str(l['fixture']['id'])
        status = l['fixture']['status']['short']
        curr_home = l['goals']['home'] or 0
        curr_away = l['goals']['away'] or 0
        
        home_team = l['teams']['home']['name']
        away_team = l['teams']['away']['name']
        logo = l['teams']['home']['logo']
        
        state = db.get_live_match_state(fixture_id)
        
        if status in ['FT', 'AET', 'PEN']:
            # O'yin tugagan
            if state is not None:
                db.remove_live_match_state(fixture_id)
                msg_json = json.dumps({"type": "RESULT", "Home": home_team, "Away": away_team, "Score": f"{curr_home} - {curr_away}", "Status": "FINAL"})
                translated = ai_translator.translate_and_spice_up(msg_json)
                send_instant_post(bot, translated, logo)
            continue
            
        # Jonli o'yin davom etyapti
        if state is None:
            db.set_live_match_state(fixture_id, {'home': curr_home, 'away': curr_away})
        else:
            prev_home = state.get('home', 0)
            prev_away = state.get('away', 0)
            
            if curr_home > prev_home or curr_away > prev_away:
                print(f"⚽️ GOL! {home_team} {curr_home} - {curr_away} {away_team}")
                db.set_live_match_state(fixture_id, {'home': curr_home, 'away': curr_away})
                
                # Qaysi jamoa gol urgan bo'lsa xabar tayyorlash
                scorer = home_team if curr_home > prev_home else away_team
                logo = l['teams']['home']['logo'] if curr_home > prev_home else l['teams']['away']['logo']
                elapsed = l['fixture']['status']['elapsed']
                
                msg_json = json.dumps({
                    "type": "GOAL",
                    "Event": f"⚽️ {scorer} GOAL! ({elapsed}')",
                    "Home": home_team, "Away": away_team,
                    "Current_Score": f"{curr_home} - {curr_away}"
                })
                translated = ai_translator.translate_and_spice_up(msg_json)
                send_instant_post(bot, translated, logo)

def safe_send_post(bot, channel_id, main_post, image_url=None, markup=None):
    """
    Telegram-ga xabar yuborishda barcha xatoliklarni xavfsiz ushlab qoluvchi va hal etuvchi helper:
    1. Telegram send_photo liti (1024 belgi) oshganda rasm captionini qisqartirish yoki text-only ga fallback qilish
    2. HTML parse xatolarida taglarni tozalab (clean HTML) qayta yuborish
    3. Rasm yuklashda tarmoq/URL xatolarida oddiy text message yuborish
    """
    import re
    clean_post = re.sub(r'<[^>]+>', '', main_post)
    
    # 1-Bosqich: Rasm bilan yuborishga urinib ko'ramiz
    if image_url:
        if len(main_post) <= 1024:
            photo_caption = main_post
            use_html = True
        else:
            photo_caption = clean_post[:1015] + "..."
            use_html = False
            
        try:
            bot.send_photo(channel_id, image_url, caption=photo_caption, parse_mode="HTML" if use_html else None, reply_markup=markup)
            return True
        except telebot.apihelper.ApiTelegramException as e:
            err_str = str(e).lower()
            if "parse entities" in err_str:
                try:
                    clean_cap = clean_post[:1015] + "..." if len(clean_post) > 1020 else clean_post
                    bot.send_photo(channel_id, image_url, caption=clean_cap, reply_markup=markup)
                    return True
                except Exception as e2:
                    print(f"Rasm bilan oddiy matn yuborishda ham xato: {e2}")
            else:
                print(f"Rasm yuborish API xatosi ({e}). Text message rejimiga o'tilmoqda...")
        except Exception as e:
            print(f"Rasm yuborish umumiy xatosi: {e}")

    # 2-Bosqich: Text message sifatida yuborish (sendMessage max 4096 char limit)
    try:
        bot.send_message(channel_id, main_post, parse_mode="HTML", reply_markup=markup)
        return True
    except telebot.apihelper.ApiTelegramException as e:
        if "parse entities" in str(e).lower():
            bot.send_message(channel_id, clean_post, reply_markup=markup)
            return True
        else:
            raise e

FOOTER_TEXT = "\n\n🔥 <b>O'zbekistondagi eng tezkor futbol yangiliklari:</b> @matchtv_livee"

def send_instant_post(bot, text, image_url):
    """GOL va Natijalarni Queue ga kiritmasdan o'sha soniyada (Push method) to'g'ri yuboradi!"""
    if not text or "[FILTERED]" in text: return
    text = text.replace('**', '').replace('*', '')
    main_post, batafsil_post = parse_telegraph_response(text)
    main_post += FOOTER_TEXT
    
    try:
        safe_send_post(bot, TARGET_CHANNEL_ID, main_post, image_url)
    except Exception as e:
        print(f"Tezkor xabar xatosi: {e}")
        send_admin_error("send_instant_post", e)

def parse_telegraph_response(text):
    xabar = text
    batafsil = ""
    if "[BATAFSIL]" in text:
        parts = text.split("[BATAFSIL]")
        xabar = parts[0].strip()
        batafsil = parts[1].strip()
    
    # Qolgan [XABAR] larni tozalab tashlash (ayniqsa qisqa postlarda yopishib qoladi)
    xabar = xabar.replace("[XABAR]", "").strip()
    return xabar, batafsil

def send_morning_greeting(bot: telebot.TeleBot):
    text = ai_translator.generate_morning_lifehack()
    if not text: return
    main_post, batafsil_post = parse_telegraph_response(text)
    main_post += FOOTER_TEXT
    
    markup = InlineKeyboardMarkup()
    if batafsil_post:
        url = create_telegraph_page(title="Xayrli tong!", html_content=batafsil_post)
        if url: markup.add(InlineKeyboardButton("👉 Batafsil o'qish", url=url))
            
    try:
        safe_send_post(bot, TARGET_CHANNEL_ID, main_post, reply_markup=markup if batafsil_post else None)
    except Exception as e:
        print(f"Morning greeting xatosi: {e}")

def process_queue_and_post(bot: telebot.TeleBot):
    """Navbatdagi RSS postlarni uzatish (Har 40-70 minutda)"""
    if not TARGET_CHANNEL_ID: return
    
    # Tunda (23:00 - 07:00) oddiy RSS xabarlari navbatda turadi, obunachilarni bezovta qilmaslik uchun
    current_hour = datetime.now().hour
    if 23 <= current_hour or current_hour < 7:
        print("🌙 Tungi vaqt: oddiy RSS xabarlari navbatda yig'ilmoqda (Ertalab 07:00 dan boshlab uzatiladi).")
        return

    # Eskirgan postlarni tozalash
    db.purge_stale_queued_posts(max_age_hours=6)
    
    post = db.get_next_post()
    if not post: return
        
    created_at = post.get('created_at')
    if created_at and (time.time() - created_at) > (6 * 3600):
        print(f"⚠️ Post ({post.get('id', '')}) 6 soatdan eskirgani uchun tashlab yuborildi.")
        return

    print(f"Jadvaldagi RSS postga ishlov berilmoqda ({post['id']})...")
    translated_text = ai_translator.translate_and_spice_up(post['text'])
    
    if not translated_text:
        post['retries'] = post.get('retries', 0) + 1
        if post['retries'] <= 3: db.requeue_post(post)
        return

    if "[FILTERED]" in translated_text: return
    translated_text = translated_text.replace('**', '').replace('*', '')
    main_post, batafsil_post = parse_telegraph_response(translated_text)
    main_post += FOOTER_TEXT

    try:
        markup = None
        if batafsil_post:
            title = "Batafsil" if post.get('type') == 'news' else "Bugungi O'yinlar Jadvali"
            url = create_telegraph_page(title=title, html_content=batafsil_post)
            if url:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("👉 Batafsil to'liq xabar", url=url))
        
        image_url = post.get('image')
        
        # Jonli tarzda bazadagi eski xiralarni to'g'irlash (oldin saqlanib qolgan bo'lsa)
        if image_url and 'ichef.bbci.co.uk' in image_url:
            if '/240/' in image_url: image_url = image_url.replace('/240/', '/800/')
            if '/480/' in image_url: image_url = image_url.replace('/480/', '/800/')
        
        # Bazadagi rasm yo'qlarni tekshirib to'ldirish
        if not image_url:
            image_url = scraper.get_unique_fallback_image()
            
        safe_send_post(bot, TARGET_CHANNEL_ID, main_post, image_url=image_url, markup=markup)
            
        print(f"✅ RSS POST ketti (Qoldi: {db.get_queued_count()})")
    except Exception as e:
        post['retries'] = post.get('retries', 0) + 1
        if post['retries'] <= 3:
            db.requeue_post(post)
        else:
            print(f"⚠️ Post {post.get('id')} 3 martadan ko'p muvaffaqiyatsiz bo'ldi, o'chirildi.")
        send_admin_error("process_queue_and_post", e)

def setup_scheduler(bot: telebot.TeleBot):
    # Har 10 minutda sekkin fon xabarlarini bepul yig'ish (RSS)
    scheduler.add_job(fetch_rss_news, trigger="interval", minutes=10, kwargs={"bot": bot})
    
    # 24/7 har 4 minutda jonli o'yinlarni kuzatish va gol postlarini tezkor uzatish
    scheduler.add_job(check_live_matches, trigger="interval", minutes=4, kwargs={"bot": bot})
    
    # Anons qismi
    scheduler.add_job(queue_morning_fixtures, trigger="cron", hour=8, minute=0, kwargs={"bot": bot})
    
    # Kechagi natijalar
    scheduler.add_job(queue_yesterday_results, trigger="cron", hour=7, minute=30, kwargs={"bot": bot})
    
    # Ertalabki greeting
    scheduler.add_job(send_morning_greeting, trigger="cron", hour=7, minute=0, kwargs={"bot": bot})
    
    # Navbatdagi postlarni har 40 - 70 minut oralig'ida yuborish (55 minut ± 15 minut jitter)
    scheduler.add_job(process_queue_and_post, trigger="interval", minutes=55, jitter=900, kwargs={"bot": bot})
    
    print("Gibrid (RSS + 24/7 API) tizimi o'rnatildi!")
    fetch_rss_news(bot)
