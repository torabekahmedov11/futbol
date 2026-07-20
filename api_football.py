import requests
import datetime
from config import API_FOOTBALL_KEY

API_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY,
    "x-apisports-host": "v3.football.api-sports.io"
}

# Asosiy dunyoga mashhur ligalar ID lari (O'zgarmaslar)
TOP_LEAGUES = [
    39,   # Premier League
    140,  # La Liga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    2,    # UEFA Champions League
    3,    # UEFA Europa League
    848,  # Conference League
    1,    # World Cup
    4,    # Euro Championship
    15,   # FIFA Club World Cup
]

def get_fixtures_for_date(date_str=None):
    """
    Berilgan sanadagi (YYYY-MM-DD) barcha o'yinlarni olib, faqat top ligalarni filtrlab qaytaradi.
    date_str: 'YYYY-MM-DD'. Agar berilmasa, bugungi sana (Tashkent vaqti) olinadi.
    """
    if not date_str:
        # Tashkent vaqti bo'yicha aniq hisoblaymiz (+5 UTC)
        # UTC vaqtini olamiz
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        tz_tashkent = datetime.timezone(datetime.timedelta(hours=5))
        local_now = utc_now.astimezone(tz_tashkent)
        date_str = local_now.strftime('%Y-%m-%d')
        print(f"Tanlangan sana (Anons uchun): {date_str}")
        
    url = f"{API_URL}/fixtures"
    params = {"date": date_str, "timezone": "Asia/Tashkent"}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = response.json()
        
        if not data or 'response' not in data:
            print(f"API Error yoki bo'sh response: {data}")
            return []
            
        all_fixtures = data['response']
        
        # Faqat top ligalarni filtrlaymiz
        top_fixtures = [fix for fix in all_fixtures if fix['league']['id'] in TOP_LEAGUES]
        
        # O'yin vaqtiga ko'ra saralaymiz
        top_fixtures.sort(key=lambda x: x['fixture']['timestamp'])
        return top_fixtures

    except Exception as e:
        print(f"API-Football bilan bog'lanishda xato: {e}")
        return []

def get_yesterday_results():
    """
    Kechagi kundagi barcha (faqa TO'LIG'I YAKUNLANGAN) top ligalar o'yinlarini natijalari qaytaradi.
    """
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    tz_tashkent = datetime.timezone(datetime.timedelta(hours=5))
    yesterday = (utc_now.astimezone(tz_tashkent) - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Tekshirilayotgan kechagi sana: {yesterday}")
    
    url = f"{API_URL}/fixtures"
    params = {"date": yesterday, "timezone": "Asia/Tashkent"}
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = response.json()
        if not data or 'response' not in data:
            return []
            
        all_fixtures = data['response']
        # Faqat top ligalarni va yakunlangan (FT, AET, PEN) larni filtrlaymiz
        finished_statuses = ['FT', 'AET', 'PEN']
        top_fixtures = [
            fix for fix in all_fixtures 
            if fix['league']['id'] in TOP_LEAGUES and fix['fixture']['status']['short'] in finished_statuses
        ]
        
        top_fixtures.sort(key=lambda x: x['league']['id'])
        return top_fixtures
    except Exception as e:
        print(f"Kechagi natijalarni olishda xato: {e}")
        return []

def get_fixture_details(fixture_id):
    """
    O'ziga xos match ID si bo'yicha to'liq ma'lumot (gollar, statistika).
    Bu 1 ta request oladi, shuning uchun juda muhim bo'lgandagina chaqiramiz.
    """
    url = f"{API_URL}/fixtures"
    params = {"id": fixture_id, "timezone": "Asia/Tashkent"}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = response.json()
        if 'response' in data and len(data['response']) > 0:
            return data['response'][0]
    except Exception as e:
        print(f"Fixture details xato ({fixture_id}): {e}")
def get_live_scores():
    """
    Faqatgina TOP ligalardagi Ayni damdagi (Live) o'yinlarni oladi.
    1 ta API request olinadi. O'yinlar yo'q bo'lsa ro'yxat bo'sh qaytadi.
    """
    if not TOP_LEAGUES:
        return []
    
    # 39-140-135-78 shaklida ligalarni birlashtiramiz... 
    # v3 football api da `live=all` deb ligani param qilib bergan ma'qul.
    url = f"{API_URL}/fixtures"
    params = {"live": "all", "timezone": "Asia/Tashkent"}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = response.json()
        if not data or 'response' not in data:
            return []
            
        all_lives = data['response']
        # Endi olingan yuzlab live o'yindan keraklilarini ajratib olamiz
        top_lives = [fix for fix in all_lives if fix['league']['id'] in TOP_LEAGUES]
        return top_lives
    except Exception as e:
        print(f"Live polling xatosi: {e}")
        return []

def get_standings(league_id=39, season=2024):
    """
    Muayyan liganing turnir jadvalini oladi.
    """
    url = f"{API_URL}/standings"
    params = {"league": league_id, "season": season}
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = response.json()
        if 'response' in data and len(data['response']) > 0:
            return data['response'][0]
    except Exception as e:
        print(f"Standings formati xato: {e}")
    return None

def get_api_status():
    """API-Football akkaunt holati va limitlarini xabar beradi"""
    url = f"{API_URL}/status"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        data = response.json()
        if 'response' in data and 'account' in data['response'] and 'requests' in data['response']['subscription']:
            # Wait, API structure might differ. Better robust dict getting
            pass 
        # v3 da response -> subscription -> active, requests -> current, limit_day
        if 'response' in data and data.get('response'):
            subs = data['response'].get('subscription', {})
            req = int(data['response'].get('requests', {}).get('current', 0))
            limit_day = int(data['response'].get('requests', {}).get('limit_day', 100))
            return {"limit_day": limit_day, "current": req, "status": "OK"}
    except Exception as e:
        print(f"Status xato: {e}")
    return {"status": "ERROR"}
