from apscheduler.schedulers.background import BackgroundScheduler
import telebot
import db
import scraper
import ai_translator
from telegraph_api import create_telegraph_page
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import TARGET_CHANNEL_ID, CHANNEL_LINK, ADMIN_ID
from datetime import datetime

scheduler = BackgroundScheduler(timezone='Asia/Tashkent')

def fetch_and_queue_posts(bot=None):
    """
    Saytdan yangi postlarni topadi va navbatga qo'shadi.
    """
    donor = db.get_donor_url()
    last_id = db.get_last_id()
    
    print(f"[{datetime.now()}] Skraping kuting... ({donor})")
    try:
        all_posts = scraper.scrape_telegram_channel(donor, last_id)
    except Exception as e:
        print(f"Skraping xatosi: {e}")
        if bot:
            try:
                bot.send_message(ADMIN_ID, f"⚠️ **Skraping (Xabar o'g'irlash) bo'limida XATOLIK:**\n\n`{str(e)}`", parse_mode="Markdown")
            except: pass
        return
    
    if not all_posts:
        return
        
    new_posts = []
    start_index = 0
    if last_id:
        for idx, post in enumerate(all_posts):
            if post["id"] == last_id:
                start_index = idx + 1
                break
        else:
            # Agar last_id topilmasa (masalan yangi sayt), faqat oxirgi 3 tasini olamiz
            start_index = max(0, len(all_posts) - 3)
            
    for i in range(start_index, len(all_posts)):
        if not db.is_post_seen(all_posts[i]["id"]):
            new_posts.append(all_posts[i])
        
    highest_id = last_id
    for post in new_posts:
        highest_id = post["id"] # xronologik
        if post["text"]:
            db.add_queued_post(post)
            db.set_last_id(highest_id) # Set seen as soon as queued
            print(f"Yangi post navbatga tushdi: {post['id']}")
            
    if new_posts:
        db.set_last_id(highest_id)

def parse_telegraph_response(text):
    xabar = text
    batafsil = ""
    
    if "[XABAR]" in text and "[BATAFSIL]" in text:
        parts = text.split("[BATAFSIL]")
        xabar = parts[0].replace("[XABAR]", "").strip()
        batafsil = parts[1].strip()
    elif "[BATAFSIL]" in text:
        parts = text.split("[BATAFSIL]")
        xabar = parts[0].strip()
        batafsil = parts[1].strip()
        
    return xabar, batafsil

def send_morning_greeting(bot: telebot.TeleBot):
    """Ertalab soat 07:00 da uyg'onib salomlashish layfxaki tashlaydi."""
    print(f"[{datetime.now()}] TONGGI MAXSUS POST YARATILMOQDA...")
    text = ai_translator.generate_morning_lifehack()
    if not text:
        return
        
    main_post, batafsil_post = parse_telegraph_response(text)
    slogan = f"\n\n🚀 Obuna bo'lish esdan chiqmasin: bizda har kuni qaynoq layfxaklar va yangiliklar!\n👉 Kanalimiz: {CHANNEL_LINK}"
    main_post += slogan
    
    markup = None
    if batafsil_post:
        telegraph_url = create_telegraph_page(title="Xayrli tong!", html_content=batafsil_post)
        if telegraph_url:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("👉 Batafsil o'qish", url=telegraph_url))
            
    try:
        bot.send_message(TARGET_CHANNEL_ID, main_post, parse_mode="HTML", reply_markup=markup)
        print("✅ Tonggi salomlashuv post kanalga ketdi!")
    except Exception as e:
        print(f"Tonggi post jo'natish xatosi: {e}")

def process_queue_and_post(bot: telebot.TeleBot):
    """
    Navbatda turgan eng birinchi postni olib, filtrdan o'tkazadi va chiqaradi.
    """
    if not TARGET_CHANNEL_ID:
        return

    post = db.get_next_post()
    if not post:
        return
        
    print(f"Postga ishlov berilmoqda ({post['id']})...")
    translated_text = ai_translator.translate_and_spice_up(post['text'])
    
    if not translated_text:
        print("API yoki tarjimon xatoligi yuz berdi. Post qayta navbatga qo'shilmoqda...")
        post['retries'] = post.get('retries', 0) + 1
        if post['retries'] <= 3:
            db.requeue_post(post)
        else:
            print(f"Post 3 marta urinishdan so'ng ham o'tmadi. Bekor qilindi: {post['id']}")
        return

    # Senzura testi
    if "[FILTERED]" in translated_text:
        print(f"Post SENZURAdan o'tmadi! Bloklandi.")
        return

    # Agar AI baribir yulduzchalardan foydalangan bo'lsa, xato bermasligi uchun qolgan * ni olib tashlash ham mumkin:
    translated_text = translated_text.replace('**', '').replace('*', '')

    main_post, batafsil_post = parse_telegraph_response(translated_text)

    # Post oxiriga kanal shiori va ssilkasini biriktirish
    slogan = f"\n\n🚀 Obuna bo'lish esdan chiqmasin: bizda har kuni qaynoq layfxaklar va yangiliklar!\n👉 Kanalimiz: {CHANNEL_LINK}"
    main_post += slogan

    try:
        video_url = post.get('video')
        image_url = post.get('image')
        
        # Telegraph linkni tayyorlash
        markup = None
        if batafsil_post:
            telegraph_url = create_telegraph_page(title=post.get('title', 'Batafsil Qo\'llanma'), html_content=batafsil_post)
            if telegraph_url:
                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("👉 Batafsil o'qish", url=telegraph_url))
        
        sent_msg = None
        if video_url:
            bot.send_video(TARGET_CHANNEL_ID, video_url, caption=main_post, parse_mode="HTML", reply_markup=markup)
        elif image_url:
            bot.send_photo(TARGET_CHANNEL_ID, image_url, caption=main_post, parse_mode="HTML", reply_markup=markup)
        else:
            bot.send_message(TARGET_CHANNEL_ID, main_post, parse_mode="HTML", reply_markup=markup)
            
        print(f"✅ Kanalga POST yuborildi! (Qoldi: {db.get_queued_count()})")
    except Exception as e:
        print(f"Jo'natishda xato: {e}")
        try:
            bot.send_message(ADMIN_ID, f"⚠️ **DIQQAT! Post kanalga jo'natishda xatolik yuz berdi:**\n\n`{str(e)}`", parse_mode="Markdown")
        except:
            pass
            
        post['retries'] = post.get('retries', 0) + 1
        if post['retries'] <= 3:
            db.requeue_post(post)
        else:
            print(f"Kanalga yuborish 3 marta feyl bo'ldi. Tashlab yuborildi: {post['id']}")

def setup_scheduler(bot: telebot.TeleBot):
    # Saytdan 10 minutda yangilikni bazaga yig'ib turadi (24/7 ishlaydi)
    scheduler.add_job(
        fetch_and_queue_posts,
        trigger="interval",
        minutes=10,
        kwargs={"bot": bot}
    )
    
    # 07:00 dagi xayrli tong AI posti
    scheduler.add_job(send_morning_greeting, trigger="cron", hour=7, minute=0, kwargs={"bot": bot})
    
    # Odamlar passiv vaqtida, eng ko'p o'qiladigan Prime-Time vaqtlardagi rejali nashr (15 ta)
    post_times = [
        (8, 15), (9, 30), (11, 0), (12, 30), 
        (13, 15), (14, 0), (15, 30), (17, 0), 
        (18, 0), (19, 0), (20, 0), (20, 45), 
        (21, 30), (22, 15), (23, 15)
    ]
    for h, m in post_times:
        scheduler.add_job(process_queue_and_post, trigger="cron", hour=h, minute=m, kwargs={"bot": bot})
        
    fetch_and_queue_posts(bot)
