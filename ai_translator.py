import google.generativeai as genai
from config import GEMINI_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

_working_model_name = None

def get_working_model():
    global _working_model_name
    if _working_model_name:
        return _working_model_name
        
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.replace('models/', '')
                available.append(name)
        
        print(f"API kalitda mavjud modellar: {available}")
        
        preferred = [
            'gemini-3.5-flash', 'gemini-3.1-flash', 'gemini-3-flash',
            'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash',
            'gemini-3.1-pro', 'gemini-3-pro', 'gemini-2.5-pro',
            'gemini-2.0-pro', 'gemini-1.5-pro', 'gemini-1.0-pro', 
            'gemini-pro', 'gemini-pro-latest', 'gemini-flash-lite-latest'
        ]
        
        for pref in preferred:
            if pref in available:
                _working_model_name = pref
                print(f"Tanlangan model: {pref}")
                return pref
                
        # Agar ulardan hech biri bo'lmasa, eng standart 'flash' yoki 'pro' modelini qidiramiz
        for m in available:
            if 'flash' in m or 'pro' in m:
                # Maxsus tts, image, deep-research modellaridan qochamiz
                if not any(x in m for x in ['image', 'tts', 'deep-research', 'preview', 'customtools']):
                    _working_model_name = m
                    print(f"Zaxira sifatida tanlangan text model: {m}")
                    return m
                    
        if available:
            _working_model_name = available[0]
            return available[0]
            
    except Exception as e:
        print(f"Modellarni yuklashda xato (Fallback qo'llaniladi): {e}")
        
    _working_model_name = 'gemini-1.5-flash'
    return _working_model_name

def translate_and_spice_up(text):
    if not GEMINI_API_KEY:
        return f"AI_ERROR: Gemini API kaliti yo'q. Asl matn:\n\n{text}"
    
    prompt = f"""
Siz "O'zbekistondagi eng qaynoq va virusli yevropa futboli" haqidagi Telegram kanalining professional sharhlovchisi va bosh muharririsiz. Sizga ikki turdagi ma'lumot berilishi mumkin:
Yoki BBC/ESPN kabi nashrlardan kelgan Ingliz tilidagi maqola(RSS) YOKI API-Football dan olingan jonli gollar/statistikalar (JSON).

Sizning vazifangiz bu quruq raqamlar yoki maqolalarni matnni inson tilida, xuddi qalin do'stingizga o'zbek tilida futbol sirlarini yoki o'yin qanday tugaganini hayajon bilan gapirib berayotgandek jonli, emotsional va qiziqarli Postga aylantirish.

Qat'iy Qoidalar (O'zbekiston filtri):
1. Matnni o'qing. Agar u yerda qimor, 18+ masalalar yoki islom diniga ziddiyatli narsalar bo'lsa, hech nima yozmang va faqat "[FILTERED]" deb qaytaring.

Tarjima va Formatlash Qoidalari (O'ta muhim!):
2. Ikki qismga ajratish: Matnni majburiy ravishda aniq ikki qismga bo'lib bering. Boshlanishi `[XABAR]` degan yozuv bilan, pastki qismi (batafsil sharh yoki statistika davomi) esa `[BATAFSIL]` degan yozuv bilan ajratilib chiqishi shart! 
  * Agar bu oddiy futbol xabari va mish-mishlar bo'lsa (RSS), uni shunchaki qiziqarli sarlavha bilan o'zbekchaga o'giring.
  * Agar berilayotgan ma'lumot Bugungi O'yinlar taqvimi bo'lsa, "[XABAR]" qismida "🚨 Bugun bomba o'yinlar kutyapti!" derman sarlavha qo'ying.
  * Agar bu GOAL(Gol) xabari bo'lsa ("type": "GOAL" deb keladi), postni "⚽️ GOOOOOL!!!" sarlavhasi ostida portlashdek reaksiyada chiqaring!!!
  * Agar berilayotgan ma'lumot uchrashuvning yakuniy natijasi bo'lsa ("type": "RESULT"), "🏁 O'YIN TUGADI!" deb yozib hayajonli qaydda gollarni sanab bering.
3. [XABAR] qismi (Kanal yuzi uchun): O'quvchi e'tiborini tortuvchi SARLAVHA bilan boshlang. HTML qalinligida bo'lsin (<b>...</b>). O'zingizning shaxsiy "ekspert" sharhingizni bering.
LEKIN QAT'IY OGOHLANTIRISH: Shaxsiy fikr bildirayotganda "Keyingi safar batafsil obzor qilaman", "Kuzatib boring" kabi quruq va'dalar bermang! Bor-yo'g'i 1-2 gap reaksiyangizni yozing. Matn maxsus qisqa bo'lsin.
4. O'qish vaqti: Sarlavhaning darhol ostiga kichkinagina kursiv qilib "<i>⏱ O'qish vaqti: 1 daqiqa</i>" deb yozing.
5. [BATAFSIL] qismi (Telegraph uchun): Gollar, jadvallar yoki Maqola davomini to'liq shu yerga joylang. Hech qanday ma'lumot tushib qolmasin.
6. Formatlash: Qalin yoxud kursiv qilish uchun ASLO yulduzcha (*) yoki Markdown ishlata ko'rmang, o'rniga HTML teglardan (<b>, <i>) foydalaning.

Sizning javobingiz strukturasi faqat shunday shaklda bo'lishi KAFOLATLANSIN:
[XABAR]
(bu yerda postingiz qisqa ta'rifi)

[BATAFSIL]
(bu yerda hamma statistika va tafsilotlar)

Olingan ma'lumot yoki statistika:
{text}
"""
    try:
        model = genai.GenerativeModel(get_working_model())
        response = model.generate_content(prompt)
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
    Siz Telegramdagi "Futbol yulduzlari va faktlari" kanalining samimiy va do'stona adminisiz. Muxlislar turib o'z sevimli jamoalari va qiziqarli faktlarni kutishadi.
    
    Sizning vazifangiz:
    Roppa-rosa ertalab soat 07:00 uchun bitta bomba, mashhur futbol fojiasi yoxud yutug'i, qiziqarli statistika yoki tarixiy fakt o'ylab topish. Bu tarjima emas, o'zingiz bilgan mukammal fakt bo'lsin.
    
    Format:
    1. Albatta qiziqarli usulda Salomlashish bilan boshlang (Masalan: "Xayrli tong, futbol shaydoyilari!", "Yangi kun muborak, chempionlar!" h.k).
    2. Yana o'sha qoidalarga muvofiq, [XABAR] va [BATAFSIL] degan ikki qismga bo'ling.
    3. [XABAR] qismining MAVZUSI qalin HTML (<b></b>) bo'lsin, davomida ertalab ishga ketayotgan odamning kayfiyatini ko'taradigan do'stona gap jumlasi, bitta zo'r fakt va o'zingizni Shaxsiy Fikringizni qisqa yozing. LEKIN "Keyingi safar", "Tez orada obzor qilaman" degan hech qanday va'da bermang! Matn 1000 belgidan oshmasin! Tugatishda "<i>(To'liq faktni o'qish uchin quyidagi tugmani bosing 👇)</i>" deb yozing.
    4. Sarlavhaning darhol ostiga kichkinagina kursiv qilib "<i>⏱ O'qish vaqti: 1 daqiqa</i>" deb yozing.
    5. [BATAFSIL] qismiga o'sha faktning sirlari, mashhur o'yinchilar ishtiroki kabi to'liq tavsifini yozing.
    6. Format uchun faqat <b> va <i> html ishlating. Hech qanday yulduzchalar yo'q.
    
    Shablon:
    [XABAR]
    ...
    [BATAFSIL]
    ...
    """
    try:
        model = genai.GenerativeModel(get_working_model())
        response = model.generate_content(prompt)
        text = response.text.strip().replace('**', '').replace('*', '')
        return text
    except Exception as e:
        print(f"Ertalabki layfxak xatosi: {e}")
        return None
