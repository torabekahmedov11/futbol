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
                "notified_fixture_ids": [],
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
            try: requests.post(_kvdb_url, json=data, timeout=5)
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


