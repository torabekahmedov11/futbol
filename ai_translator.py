import google.generativeai as genai
from config import GEMINI_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

_working_model_name = None
_banned_models = []

def get_working_model():
    global _working_model_name
    if _working_model_name and _working_model_name not in _banned_models:
        return _working_model_name
        
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.replace('models/', '')
                available.append(name)
        
        # print(f"API kalitda mavjud modellar: {available}")
        
        preferred = [
            'gemini-3.5-flash', 'gemini-3.1-flash', 'gemini-3-flash',
            'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash',
            'gemini-3.1-pro', 'gemini-3-pro', 'gemini-2.5-pro',
            'gemini-2.0-pro', 'gemini-1.5-pro', 'gemini-1.0-pro', 
            'gemini-pro', 'gemini-pro-latest'
        ]
        
        for pref in preferred:
            if pref in available and pref not in _banned_models:
                _working_model_name = pref
                print(f"Tanlangan model: {pref}")
                return pref
                
        for m in available:
            if m not in _banned_models and ('flash' in m or 'pro' in m):
                if not any(x in m for x in ['image', 'tts', 'deep-research', 'preview', 'customtools']):
                    _working_model_name = m
                    print(f"Zaxira sifatida tanlangan text model: {m}")
                    return m
                    
        available_clean = [m for m in available if m not in _banned_models]
        if available_clean:
            _working_model_name = available_clean[0]
            return available_clean[0]
            
    except Exception as e:
        print(f"Modellarni yuklashda xato (Fallback qo'llaniladi): {e}")
        
    if 'gemini-1.5-flash' not in _banned_models:
        _working_model_name = 'gemini-1.5-flash'
    return _working_model_name

def safe_generate_content(prompt):
    global _working_model_name, _banned_models
    max_retries = 4
    
    for _ in range(max_retries):
        model_name = get_working_model()
        if not model_name:
            raise Exception("Hamma modellar bloklandi yoki limit tugadi!")
            
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "exhausted" in error_str:
                print(f"[{model_name}] Limit tugadi! Zaxira modelga o'tilmoqda...")
                _banned_models.append(model_name)
                _working_model_name = None
                continue
            else:
                raise e
    
    raise Exception("Maksimal urinishlar tugadi. Model limitlari tamom bo'ldi.")

def translate_and_spice_up(text):
    if not GEMINI_API_KEY:
        return f"AI_ERROR: Gemini API kaliti yo'q. Asl matn:\n\n{text}"
    
    prompt = f"""
Siz "O'zbekistondagi eng qaynoq va virusli yevropa futboli" haqidagi Telegram kanalining professional sharhlovchisi va bosh muharririsiz. Ma'lumot:
Ingliz tilidagi maqola (RSS) yoki API-Football xabari (JSON). Ushbu kontentni inson tilida, xuddi qalin do'stingizga o'zbek tilida qiziqarli gapirib berayotgandek jonli, emotsional Postga aylantiring.

Qat'iy Qoidalar (Xavfsizlik va Filtar - O'ta Muhim!):
1. MATIN XAVFSIZLIGI: Hech qachon birovni haqorat qiladigan, 18+ mazmundagi, diniy (yoki islom diniga zid), siyosiy, millatchilikka xos, qimor (betting) reklamasi yoki O'zbekiston qonunlariga zid har qanday axborotni tarjima qilmang va yozmang. Bunday holatda faqat "[FILTERED]" deb javob qaytaring.

Formatlash va Qismlarga Ajratish Qoidalari:
2. QISQA VA UZUN POSTLAR: Avval kelgan matn hajmini o'lchang. Bizda [XABAR] va [BATAFSIL] qismlari bor.
   - AGAR POST QISQA bo'lsa (taxminan yozganingizda 150-180 so'zdan oshmasa), hamma gapni MAJBURIY faqat [XABAR] bloki ichiga yozing! [BATAFSIL] degan blokni UMUMAN yaratmang (bu qoidani buzmang, preview keraksiz!).
   - AGAR POST UZUN va JIDDIY bo'lsa, qiziqtiruvchi ta'rifni [XABAR] qismiga va to'liq uzun davomini [BATAFSIL] qismiga bo'lib yozing.
3. KANAL YUZI [XABAR] qismi:
   - "🚨 Bugungi o'yinlar" (anons bo'lsa) yoxud "⚽️ GOOOOOL!!!" (gol bo'lsa), yoki "🏁 O'YIN TUGADI!" (natija bo'lsa) maxsus emotsional SARLAVHA qo'ying. HTML teglari (<b>...</b>) ishlating.
   - Sarlavha tagiga <i>⏱ O'qish vaqti: 1 daqiqa</i> deb qo'ying.
4. HASHTAGLAR VA SHIOR:
   - [XABAR] ning eng oxiriga yoki matn so'nggiga doim ANIQLIK BILAN mavzuga oid 12 ta xeshteg (M: #futbol #championsleague #realmadrid) joylang. Undan so'ng yana bitta bo'sh joy tashlab, kanal shiorini yozing: "🔥 <b>O'zbekistondagi eng tezkor futbol yangiliklari:</b> @matchtv_livee".
5. TIRIK INSON (P.S.) VA O'ZBEKISTON FUTBOLI:
   - [XABAR] oxirida ba'zida (har doim emas) "<b>P.S.</b>" deb o'z shaxsiy munosabatingizni qoldiring! Ba'zan hazillashib (futbol memlari ruhida), ba'zan rasmiy o'ychan ekspert sifatida fikr bildiring.
   - MUHIMI: Xabar mavzusiga mos keladigan qiziqli o'rinda O'zbekiston milliy terma jamoasi yoki futbolchilarimizning xorijdagi yangiliklariga (Eldor Shomurodov, Abbosbek, Husanov h.k.) mutlaqo HAQIQIY faktga suyangan munosabat va iliqlikni qisqacha qo'shib keting. O'zingizdan o'zbek futboli haqida yolg'on natijalar to'qimang.
6. Hech qachon markdown yulduzcha (*) ishlatmang, faqat HTML (<b> <i>) ishlating.

Sizning javobingiz strukturasi (Agar qisqa bo'lsa [BATAFSIL] bloki bo'lmaydi!!):
[XABAR]
(SARLAVHA)
(O'qish vaqti)
(Asosiy matn...)
(P.S. Munosabat)
(Xeshteglar)
(Shior va havola)

[BATAFSIL]
(Faqatgina ma'lumot uzun va katta bo'lsagina shu yerga davomini yozing, yo'qsa bu blokni bo'sh qoldiring yoki umuman yaratmang!)

Olingan manba:
{text}
"""
    try:
        response = safe_generate_content(prompt)
        try:
            translated = response.text.strip()
            return translated
        except ValueError:
            print("Gemini API: Kontent AI xavfsizlik filtriga tushdi yoki ruxsat etilmadi.")
            return "[FILTERED]"
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def generate_morning_lifehack():
    """Tongi xayrli tong po'sti uchun manbasiz generatsiya (AI o'zi o'ylaydi)."""
    if not GEMINI_API_KEY:
        return None
    
    prompt = """
Siz Telegramdagi "Futbol yulduzlari va faktlari" kanalining samimiy va do'stona adminisiz.
QAT'IY OGOXNATIRISH: 18+, buzg'unchilik, agressiv siyosiy, bet or qimor va O'zbekiston hududida yot (jinoyat) bo'lgan axborot yaratish taqiqlanadi. Faqat sof futbolga doir fakt toping.

Qator Qoidalar:
1. Roppa-rosa ertalab soat 07:00 uchun bitta bomba, mashhur futbol fojiasi yoxud yutug'i, qiziqarli statistika yoki O'zbek futbol maktabi shonli pallalari haqidagi MA'LUM FAKTNI generatsiya qiling (yolg'on yoki asossiz voqea to'qimang).
2. [XABAR] va [BATAFSIL] degan ikki qismga bo'lish (majburiy emas, ammo fakt uzun bo'lsa ajrating). Boshida Salomlashish, masalan "Xayrli tong, futbol shaydoyilari!".
3. [XABAR] tagida 12 ta xeshteg yoxud kichkina P.S. munosabatini ilova qiling.
4. Kanal shiori bilan yakunlang: "🔥 <b>O'zbekistondagi eng tezkor futbol yangiliklari:</b> @matchtv_livee"
5. Yulduzchalar yo'q, faqat <b> va <i> HTML ishlating.

Shablon:
[XABAR]
...
(hashtags)
(slogan)
[BATAFSIL]
... (agar kerak bo'lsa)
"""
    try:
        response = safe_generate_content(prompt)
        text = response.text.strip().replace('**', '').replace('*', '')
        return text
    except Exception as e:
        print(f"Ertalabki layfxak xatosi: {e}")
        return None

def check_ai_status():
    if not GEMINI_API_KEY:
        return "XATO: API kalit kiritilmagan!"
    try:
        response = safe_generate_content("Just say 'OK'")
        if "OK" in response.text.upper():
            return f"NORMAL ({_working_model_name} faol)"
        else:
            return "OGOHLANTIRISH (Noto'g'ri javob)"
    except Exception as e:
        return f"XATO (Limitsiz yoki tarmoq): {str(e)[:50]}"
