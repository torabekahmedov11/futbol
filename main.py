import telebot
import db
import threading
import json
from config import BOT_TOKEN, ADMIN_ID, TARGET_CHANNEL_ID
from scheduler_jobs import setup_scheduler, scheduler, fetch_rss_news, process_queue_and_post
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import api_football
import ai_translator

db.init_db()

bot = telebot.TeleBot(BOT_TOKEN)

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def get_admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("📊 Holat"), KeyboardButton("🛠 Sozlamalar"))
    markup.row(KeyboardButton("🚀 Majburiy yig'ish"), KeyboardButton("📨 Majburiy post"))
    return markup

def notify_admin(context, error):
    try:
        if ADMIN_ID:
            bot.send_message(ADMIN_ID, f"⚠️ XATOLIK:\n📍 Joy: {context}\n📄 Xato: `{error}`", parse_mode="Markdown")
    except: pass

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_admin(message.from_user.id):
        text = f"🔒 Siz admin emassiz.\n\nSizning Telegram ID raqamingiz: `{message.from_user.id}`\n\nIltimos, ushbu ID ni `.env` faylidagi `ADMIN_ID` qatoriga yozing va botni qayta ishga tushiring."
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return
        
    text = (
        "👋 Assalomu alaykum, Admin!\n\n"
        "Bu bot o'zbek tiliga xorijiy kanallardan postlarni 'o'g'irlab', "
        "Gemini AI yordamida 'virusli' formatda kanalingizga joylab beradi."
    )
    bot.send_message(message.chat.id, text, reply_markup=get_admin_menu())

@bot.message_handler(func=lambda message: message.text == "📊 Holat" or message.text.startswith('/status'))
def cmd_status(message):
    if not is_admin(message.from_user.id):
        return
    donor = db.get_donor_url()
    q_count = db.get_queued_count()
    last_id = db.get_last_id()
    
    bot.send_message(message.chat.id, "Holat hisoblanmoqda, kutib turing...")
    
    api_stat = api_football.get_api_status()
    ai_stat = ai_translator.check_ai_status()
    
    limit_info = ""
    if api_stat["status"] == "OK":
        lim = api_stat["limit_day"]
        curr = api_stat["current"]
        qoldiq = lim - curr
        xulosa = "Yetmaydi (API kalit almashtiring)" if qoldiq < 15 else "Bugunga yetadi"
        limit_info = f"⚽️ API-Football: {curr}/{lim} band (Qoldiq: {qoldiq}), {xulosa}"
    else:
        limit_info = "⚽️ API-Football: Ulanishda xato!"

    text = (
        "📈 **Bot Holati:**\n\n"
        f"🎯 RSS Manba: {donor}\n"
        f"📦 Navbatdagi postlar soni: {q_count} ta\n"
        f"🔍 Oxirgi o'qilgan maxsus xabar: {last_id if last_id else 'Hali yoq'}\n\n"
        f"🤖 AI Holati: {ai_stat}\n"
        f"{limit_info}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(func=lambda message: message.text == "🚀 Majburiy yig'ish" or message.text.startswith('/force_fetch'))
def cmd_force_fetch(message):
    if not is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id, "Sikraping ishga tushirildi... Kutib turing.")
    try:
        fetch_rss_news()
        bot.send_message(message.chat.id, f"Skraping tugadi! Navbatda {db.get_queued_count()} ta post yig'ildi.")
    except Exception as e:
        notify_admin("Force fetch", e)

@bot.message_handler(func=lambda message: message.text == "📨 Majburiy post" or message.text.startswith('/force_post'))
def cmd_force_post(message):
    if not is_admin(message.from_user.id):
        return
    if db.get_queued_count() == 0:
        bot.send_message(message.chat.id, "Bazada post yo'q. Oldin '🚀 Majburiy yig'ish' qilib postlarni yig'ing.")
        return
    
    bot.send_message(message.chat.id, "Tarjima qilinmoqda va kanalga jo'natilmoqda...")
    try:
        process_queue_and_post(bot)
        bot.send_message(message.chat.id, "Urinish tugadi. Kanalni tekshiring (Agar tushmagan bo'lsa limit to'lgan bo'lishi mumkin).")
    except Exception as e:
        notify_admin("Force post", e)

@bot.message_handler(func=lambda message: message.text == "🛠 Sozlamalar" or message.text.startswith('/settings'))
def cmd_settings(message):
    if not is_admin(message.from_user.id):
        return
    donor = db.get_donor_url()
    text = (
        f"Hozirgi RSS Manba (Sayt): {donor}\n\n"
        "Yangi RSS manbalarini to'liq havolasi (URL) bilan jo'nating:\n"
        "Misollar:\n"
        "- http://feeds.bbci.co.uk/sport/football/rss.xml\n"
        "- https://www.espn.com/espn/rss/soccer/news\n"
        "(Bekor qilish uchun /cancel)"
    )
    msg = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(msg, process_new_donor)

@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    if not is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id, "Bekor qilindi.")
    bot.clear_step_handler_by_chat_id(message.chat.id)

def process_new_donor(message):
    if not is_admin(message.from_user.id):
        return
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "Sozlamalarni o'zgartirish bekor qilindi.")
        return
        
    new_url = message.text.strip()
    db.set_donor_url(new_url)
    bot.send_message(message.chat.id, f"✅ Muvaffaqiyatli! Yangi RSS Manba ulandi: {new_url} \n"
                         f"Endi yangi ma'lumotlarni yig'ib olish uchun /force_fetch ni bosing.")

if __name__ == "__main__":
    from keep_alive import keep_alive
    keep_alive()
    
    setup_scheduler(bot)
    scheduler.start()
    print("Taymer (Scheduler) ishga tushdi!")
    
    try:
        if ADMIN_ID:
            bot.send_message(ADMIN_ID, "🚀 Bot serverda qayta ishga tushdi va bulutli xotirani faollashtirdi!", reply_markup=get_admin_menu())
    except Exception as e:
        print(f"Boshlang'ich xabar xatosi: {e}")
    
    print("Bot polling boshlandi...")
    bot.infinity_polling()
