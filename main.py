import telebot
import db
import threading
from config import BOT_TOKEN, ADMIN_ID, TARGET_CHANNEL_ID
from scheduler_jobs import setup_scheduler, scheduler, fetch_and_queue_posts, process_queue_and_post

db.init_db()

bot = telebot.TeleBot(BOT_TOKEN)

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_admin(message.from_user.id):
        text = f"🔒 Siz admin emassiz.\n\nSizning Telegram ID raqamingiz: `{message.from_user.id}`\n\nIltimos, ushbu ID ni `.env` faylidagi `ADMIN_ID` qatoriga yozing va botni qayta ishga tushiring."
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return
        
    text = (
        "👋 Assalomu alaykum, Admin!\n\n"
        "Bu bot o'zbek tiliga xorijiy kanallardan postlarni 'o'g'irlab', "
        "Gemini AI yordamida 'virusli' formatda kanalingizga joylab beradi.\n\n"
        "🛠 /settings - Donor kanalni o'zgartirish\n"
        "📊 /status - Hozirgi holatni ko'rish\n"
        "🚀 /force_fetch - Hozirning o'zida postlarni yig'ish\n"
        "📨 /force_post - Hozirning o'zida bitta post chiqarib ko'rish"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not is_admin(message.from_user.id):
        return
    donor = db.get_donor_url()
    q_count = db.get_queued_count()
    last_id = db.get_last_id()
    
    text = (
        "📈 **Bot Holati:**\n\n"
        f"🎯 RSS Manba (Sayt): {donor}\n"
        f"📦 Navbatdagi postlar soni: {q_count} ta\n"
        f"🔍 Oxirgi o'qilgan xabar URL: {last_id}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['force_fetch'])
def cmd_force_fetch(message):
    if not is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id, "Sikraping ishga tushirildi... Kutib turing.")
    fetch_and_queue_posts()
    bot.send_message(message.chat.id, f"Skraping tugadi! Navbatda {db.get_queued_count()} ta post yig'ildi.")

@bot.message_handler(commands=['force_post'])
def cmd_force_post(message):
    if not is_admin(message.from_user.id):
        return
    if db.get_queued_count() == 0:
        bot.send_message(message.chat.id, "Bazada post yo'q. Oldin /force_fetch qilib postlarni yig'ing.")
        return
    
    bot.send_message(message.chat.id, "Tarjima qilinmoqda va kanalga jo'natilmoqda...")
    process_queue_and_post(bot)
    bot.send_message(message.chat.id, "Urinish tugadi. Kanalni tekshiring.")

@bot.message_handler(commands=['settings'])
def cmd_settings(message):
    if not is_admin(message.from_user.id):
        return
    donor = db.get_donor_url()
    text = (
        f"Hozirgi RSS Manba (Sayt): {donor}\n\n"
        "Yangi RSS manbalarini to'liq havolasi (URL) bilan jo'nating:\n"
        "Misollar:\n"
        "- https://lifehacker.com/rss\n"
        "- https://www.reddit.com/r/BeAmazed/.rss\n"
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
    
    print("Bot polling boshlandi...")
    bot.infinity_polling()
