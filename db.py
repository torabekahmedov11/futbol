import json
import os
import threading
import requests
import hashlib
from config import BOT_TOKEN

DB_FILE = "db.json"
_db_lock = threading.Lock()

_db_id = "fbdb_" + hashlib.md5(BOT_TOKEN.encode()).hexdigest()[:12]
_db_secret = hashlib.md5((BOT_TOKEN + "secret").encode()).hexdigest()[:15]
_db_read_url = f"https://rentry.co/{_db_id}"

def init_db():
    global _db_lock
    _db_lock = threading.Lock()
    with _db_lock:
        if not os.path.exists(DB_FILE):
            print("Lokal baza yo'q. Cloud Rentry dan sinab ko'rilmoqda...")
            try:
                r = requests.get(_db_read_url, timeout=10)
                if r.status_code == 200:
                    try:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(r.text, 'html.parser')
                        article = soup.find('article')
                        if article:
                            raw_text = article.get_text(strip=True)
                            if raw_text.startswith('{'):
                                data = json.loads(raw_text)
                                with open(DB_FILE, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, ensure_ascii=False, indent=4)
                                print("✅ Onlayn xotiradan (Cloud) Database muvaffaqiyatli TIKLANDI!")
                                return
                    except Exception as parse_e:
                        print(f"Parse error: {parse_e}")
            except Exception as e:
                print(f"Cloud dan tiklashda xato yoki xotira yo'q: {e}")
                
            default_data = {
                "donor_url": "http://feeds.bbci.co.uk/sport/football/rss.xml",
                "last_scraped_id": "",
                "seen_ids": [],
                "notified_fixture_ids": [],
                "queued_posts": [],
                "live_match_states": {}
            }
            # fayl yo'q bo'lsa _save_unlocked o'zi yozib cloudga 1-marta commit beradi
            try:
                with open(DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_data, f, ensure_ascii=False, indent=4)
                
                requests.post("https://rentry.co/api/new", data={
                    "url": _db_id,
                    "edit_code": _db_secret,
                    "text": json.dumps(default_data)
                }, timeout=10)
            except Exception as e:
                print(e)

def _load_unlocked():
    if not os.path.exists(DB_FILE):
        return {
            "donor_url": "http://feeds.bbci.co.uk/sport/football/rss.xml",
            "last_scraped_id": "",
            "seen_ids": [],
            "notified_fixture_ids": [], 
            "queued_posts": [],
            "live_match_states": {}
        }
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_unlocked(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        def _upload():
            try: 
                text_data = json.dumps(data, ensure_ascii=False)
                res = requests.post(f"https://rentry.co/api/edit/{_db_id}", data={
                    "edit_code": _db_secret,
                    "text": text_data
                }, timeout=10)
                # Agar mavjud bo'lmasa, yaratish
                if res.status_code != 200 or ("not found" in res.text.lower()):
                    requests.post("https://rentry.co/api/new", data={"url": _db_id, "edit_code": _db_secret, "text": text_data}, timeout=10)
            except: pass
        threading.Thread(target=_upload).start()
    except Exception as e:
        print(f"Xato (saqlash): {e}")

# ---- RSS ----
def get_donor_url():
    with _db_lock:
        return _load_unlocked().get("donor_url", "http://feeds.bbci.co.uk/sport/football/rss.xml")

def set_donor_url(url):
    with _db_lock:
        data = _load_unlocked()
        data["donor_url"] = url
        data["last_scraped_id"] = ""
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
            if len(data["seen_ids"]) > 200:
                data["seen_ids"] = data["seen_ids"][-200:]
        _save_unlocked(data)

def is_post_seen(post_id):
    with _db_lock:
        data = _load_unlocked()
        return post_id in data.get("seen_ids", [])

# ---- API FOOTBALL ----
def add_notified_fixture(fixture_id):
    with _db_lock:
        data = _load_unlocked()
        if "notified_fixture_ids" not in data:
            data["notified_fixture_ids"] = []
        if fixture_id not in data["notified_fixture_ids"]:
            data["notified_fixture_ids"].append(fixture_id)
            if len(data["notified_fixture_ids"]) > 1000:
                data["notified_fixture_ids"] = data["notified_fixture_ids"][-1000:]
        _save_unlocked(data)

def is_fixture_notified(fixture_id):
    with _db_lock:
        data = _load_unlocked()
        return fixture_id in data.get("notified_fixture_ids", [])

def get_live_match_state(fixture_id):
    with _db_lock:
        data = _load_unlocked()
        return data.get("live_match_states", {}).get(str(fixture_id))

def set_live_match_state(fixture_id, state_dict):
    with _db_lock:
        data = _load_unlocked()
        if "live_match_states" not in data:
            data["live_match_states"] = {}
        data["live_match_states"][str(fixture_id)] = state_dict
        _save_unlocked(data)

def remove_live_match_state(fixture_id):
    with _db_lock:
        data = _load_unlocked()
        if "live_match_states" in data and str(fixture_id) in data["live_match_states"]:
            del data["live_match_states"][str(fixture_id)]
            _save_unlocked(data)

# ---- QUEUE ----
def add_queued_post(post_data):
    with _db_lock:
        data = _load_unlocked()
        if "queued_posts" not in data:
            data["queued_posts"] = []
        data["queued_posts"].append(post_data)
        _save_unlocked(data)

def requeue_post(post_data):
    with _db_lock:
        data = _load_unlocked()
        if "queued_posts" not in data:
            data["queued_posts"] = []
        data["queued_posts"].insert(0, post_data)
        _save_unlocked(data)

def get_next_post():
    with _db_lock:
        data = _load_unlocked()
        if data.get("queued_posts"):
            post = data["queued_posts"].pop(0)
            _save_unlocked(data)
            return post
        return None

# ---- TRACKING ACTIVE HOURS ----
def set_today_fixtures_times(times_list):
    """Bugungi o'yinlarning boshlanish va tugash taxminiy UTC vaktlarini (timestamp) saqlaydi."""
    with _db_lock:
        data = _load_unlocked()
        data["today_fixtures_times"] = times_list
        _save_unlocked(data)

def get_today_fixtures_times():
    with _db_lock:
        data = _load_unlocked()
        return data.get("today_fixtures_times", [])

def get_queued_count():
    with _db_lock:
        return len(_load_unlocked().get("queued_posts", []))

def purge_stale_queued_posts(max_age_hours=6):
    """6 soatdan eski yoki kechagi postlarni bazadan yo'qotib tashlaydi."""
    import time
    with _db_lock:
        data = _load_unlocked()
        queued = data.get("queued_posts", [])
        if not queued:
            return 0
        now = time.time()
        fresh_queued = []
        purged_count = 0
        for p in queued:
            created_at = p.get('created_at', now)
            if (now - created_at) <= (max_age_hours * 3600):
                fresh_queued.append(p)
            else:
                purged_count += 1
        if purged_count > 0:
            data["queued_posts"] = fresh_queued
            _save_unlocked(data)
            print(f"🧹 Bazadan {purged_count} ta eski post tozalandi!")
        return purged_count


