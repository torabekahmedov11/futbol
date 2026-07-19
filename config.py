import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TARGET_CHANNEL_ID = os.getenv("TARGET_CHANNEL_ID", "")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", TARGET_CHANNEL_ID)  

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("WARNING: Kalitlar sozlanmagan! .env faylni tekshiring.")
