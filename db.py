import json
import os
import threading
import requests
import hashlib
from config import BOT_TOKEN

DB_FILE = "db.json"
_db_lock = threading.Lock()

# Xavfsiz, parolli cloud nomi yasaymiz.
_kvdb_bucket = "avto_" + hashlib.md5(BOT_TOKEN.encode()).hexdigest()[:15]
_kvdb_url = f"https://kvdb.io/bucket/{_kvdb_bucket}/db"

def init_db():
    global _db_lock
    _db_lock = threading.Lock()
    with _db_lock:
        if not os.path.exists(DB_FILE):
            print("Lokal baza yo'q. Cloud KVDB dan sinab ko'rilmoqda...")
            try:
                r = requests.get(_kvdb_url, timeout=5)
                if r.status_code == 200 and r.json():
                    data = r.json()
                    with open(DB_FILE, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    print("✅ Onlayn xotiradan (Cloud) Database muvaffaqiyatli TIKLANDI!")
                    return
            except Exception as e:
                print(f"Cloud dan tiklashda xato yoki xotira yo'q: {e}")
                
            default_data = {
                "donor_url": "http://feeds.bbci.co.uk/sport/football/rss.xml",
                "last_scraped_id": "",
                "seen_ids": [],
                "queued_posts": []
            }
            # fayl yo'q bo'lsa _save_unlocked o'zi yozib cloudga 1-marta commit beradi
            try:
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(e)

def _load_unlocked():
    if not os.path.exists(DB_FILE):
        return {"donor_url": "http://feeds.bbci.co.uk/sport/football/rss.xml", "last_scraped_id": "", "seen_ids": [], "queued_posts": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_unlocked(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        # Async bulutga commit qilish
        def _upload():
            try: requests.post(_kvdb_url, json=data, timeout=5)
            except: pass
        threading.Thread(target=_upload).start()
    except Exception as e:
        print(f"Xato (saqlash): {e}")

def get_donor_url():
    with _db_lock:
        return _load_unlocked().get("donor_url", "http://feeds.bbci.co.uk/sport/football/rss.xml")

def set_donor_url(url):
    with _db_lock:
        data = _load_unlocked()
        data["donor_url"] = url
        data["last_scraped_id"] = ""  # yangi saytdan yangi postlarni eslab qolish uchun
        data["queued_posts"] = []     # eski navbatni tozalaymiz
        _save_unlocked(data)

def get_last_id():
    with _db_lock:
        return _load_unlocked().get("last_scraped_id", "")

def set_last_id(msg_id):
    with _db_lock:
        data = _load_unlocked()
        data["last_scraped_id"] = msg_id
        if "seen_ids" not in data:
            data["seen_ids"] = []
        if msg_id and msg_id not in data["seen_ids"]:
            data["seen_ids"].append(msg_id)
            # 50 tadan oshib ketmasligi uchun
            if len(data["seen_ids"]) > 50:
                data["seen_ids"] = data["seen_ids"][-50:]
        _save_unlocked(data)

def is_post_seen(post_id):
    with _db_lock:
        data = _load_unlocked()
        return post_id in data.get("seen_ids", [])

def add_queued_post(post_data):
    with _db_lock:
        data = _load_unlocked()
        data["queued_posts"].append(post_data)
        _save_unlocked(data)

def requeue_post(post_data):
    """
    Xatoga uchragan yoxud jo'natish xatolikka tushgan po'stni qayta o'qish uchun navbatning boshiga qo'shadi.
    """
    with _db_lock:
        data = _load_unlocked()
        data["queued_posts"].insert(0, post_data)
        _save_unlocked(data)

def get_next_post():
    with _db_lock:
        data = _load_unlocked()
        if data["queued_posts"]:
            post = data["queued_posts"].pop(0)
            _save_unlocked(data)
            return post
        return None

def get_queued_count():
    with _db_lock:
        return len(_load_unlocked().get("queued_posts", []))


