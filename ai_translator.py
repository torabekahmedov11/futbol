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
    max_retries = 15
    
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
            if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "404" in error_str or "no longer available" in error_str or "403" in error_str:
                print(f"[{model_name}] Ulanish rad etildi (Limit yoki 404)! Zaxira modelga o'tilmoqda... Xato: {str(e)[:50]}")
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
Siz Telegramdagi "Match TV Live" Yevropa futboli kanalining professional, emotsional va savodli sport sharhlovchisisiz.
Berilgan inglizcha yangilik (RSS) yoki API-Football ma'lumotini o'zbek tiliga tushunarli, qiziqarli va professional jurnalistik uslubda o'giring.

Qat'iy Qoidalar:
1. FAQT VA ANIQ MATN: Faqat va faqat manba matnida berilgan REAL faktlarga tayaning. O'zingizdan uydirma voqea, eskirgan faktlar yoki manbada bo'lmagan natijalarni to'qimang.
2. USLUB (MUHIM): "Og'ayni", "do'stim", "daxshatni qara", "og'ayni qara" kabi bachkana yoki ko'cha jargon so'zlarini UMUMAN ISHLATMANG! Professional, hayajonli va savodli til ishlating. "⏱ O'qish vaqti" degan ortiqcha qatorlarni yozmang.
3. KANAL SHIORI VA LINKLAR: Javobingizga kanal linki (@matchtv_livee) yoki obuna bo'ling degan shiorlarni UMUMAN QO'SHMANG! (Bu avtomatik qo'shiladi).
4. XAVFSIZLIK: 18+, buzg'unchilik, siyosiy, bet/qimor reklamalarini tarjima qilmang. Bunday bo'lsa faqat "[FILTERED]" deb javob bering.

Formatlash Qoidalari:
5. QISQA VA UZUN POSTLAR:
   - AGAR POST QISQA bo'lsa (150-180 so'zdan oshmasa), hamma gapni MAJBURIY faqat [XABAR] bloki ichiga yozing! [BATAFSIL] degan blokni UMUMAN yaratmang!
   - AGAR POST UZUN va JIDDIY bo'lsa, qiziqtiruvchi ta'rifni [XABAR] qismiga va to'liq davomini [BATAFSIL] qismiga bo'lib yozing.
6. SARLAVHA VA HASHTAGLAR:
   - Sarlavhani emotsional qiling: "🚨 REAL MADRIDDA YANGILIK!" yoki "⚽️ GOOOOOL!" yoki "🏁 O'YIN TUGADI!". HTML (<b>...</b>) ishlating.
   - [XABAR] matni oxiriga mavzuga oid 8-10 ta xeshteg joylang (M: #futbol #realmadrid #championsleague).
7. Faqat HTML (<b>, <i>) ishlating. Markdown (*) ishlatmang.

Sizning javobingiz strukturasi (Qisqa bo'lsa [BATAFSIL] bo'lmaydi!):
[XABAR]
<b>(SARLAVHA)</b>

(Asosiy yangilik matni...)

(Hashtaglar)

[BATAFSIL]
(Faqatgina ma'lumot juda uzun bo'lsagina shu yerga davomini yozing, yo'qsa bu blokni umuman yaratmang!)

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
    """Tongi xayrli tong po'sti uchun manbasiz generatsiya."""
    if not GEMINI_API_KEY:
        return None
    
    prompt = """
Siz Telegramdagi "Match TV Live" futbol kanalining savodli va samimiy adminisiz.

Qat'iy Qoidalar:
1. Ertalab soat 07:00 uchun futbol olamidagi mashhur va QIZIQARLI FAKT, burilish nuqtasi yoki statistika haqida samimiy post tayyorlang (yolg'on fakt to'qimang).
2. "Og'ayni", "do'stim" kabi so'zlarni ishlatmang. Professional va samimiy so'rashish: "Xayrli tong, futbol muxlislari!".
3. Javobingizga kanal linki yoki shiorlarni QO'SHMANG!
4. Yulduzchalar yo'q, faqat <b> va <i> HTML ishlating.

Shablon:
[XABAR]
<b>Xayrli tong, futbol muxlislari! ⚽️</b>

(Fakt matni...)

(Hashtaglar)
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
