# Futbol Botini 0 Dan Ishga Tushirish Qo'llanmasi

Ushbu shablon sizning yangi "Futbol" kanalingiz uchun to'liq tayyorlangan mukammal (bulutli xotiraga ega) Avtobot hisoblanadi. Uni mustaqil ravishda ishga tushirish uchun quyidagi qadamlarni e'tibor bilan bajaring:

## 1-bosqich: Dastlabki Sozlamalar (Lokal)
1. VS Code yordamida `d:\futbol_bot` papkasini oching.
2. `config.py` yoki `ai_translator.py` ga kiring va propmtlarni **"futbol sharhlovchisi"** yoki **"sport mutaxassisi"** ga o'zgartirib chiqing. M: *"Siz futbol ekspertisiz..."* (Avtokanal o'rniga).
3. **BotFather** dan yangi futbol boti ochib to'ken oling.
4. Ushbu joriy papkada `.env` nomli fayl yarating (agar bo'lmasa `.env.example` ga qarab yarating) va ichiga quyidagilarni aniq kiriting:
   ```env
   BOT_TOKEN=Yangi_futbol_botning_tokeni
   ADMIN_ID=Sizning_shaxsiy_telegram_ID_raqamingiz
   TARGET_CHANNEL_ID=-100xxxxxxxxxx (Futbol kanalingiz IDsi)
   CHANNEL_LINK=https://t.me/futbol_kanalingiz
   GEMINI_API_KEY=Gemini_Pochtangizdan_olingan_yangi_API_kalit
   ```
5. Botni ushbu futbol kanalingizga **Admin (Administrator)** qilib qo'shishni unutmang!

## 2-bosqich: GitHub'ga Bog'lash va Yuklash
Lokal dastyringiz tugagach, uni Vebga (Github'ga) yuklashimiz shart.

1. **Github.com** ga kiring va o'ng tarafdagi `+` (New Repository) tugmasini bosib o'zingizga yangi platforma yarating. Nomini masaalan: `futbol-avtobot` deb yozing va *Create* qiling.
2. VS Code ning tepadagi **Terminal** (New Terminal) darchasini oching. U yerda manzili aynan `D:\futbol_bot` bo'lib turganiga ishonch hosil qilib juyidagi kodlarni ketma cherting:
   
   ```bash
   # 1. Loyihani Github tizimiga ulashni boshlash
   git init
   
   # 2. Hamma fayllarni tanlash
   git add .
   
   # 3. Yaratilgan o'zgarishlarni nomlash
   git commit -m "Futbol loyihasi 1.0"
   
   # 4. Asosiy Master (Main) bo'limiga biralashtirish
   git branch -M main
   
   # 5. DIQQAT: Github'da yaratgan bo'sh loyihangiz URL linkini shu yerga ulaysiz
   git remote add origin https://github.com/Sizning-Github-Ismingiz/futbol-avtobot.git
   
   # 6. Va nihoyat fayllarni uchirib jo'natish:
   git push -u origin main
   ```
*(Bu qadamlardan so'ng barcha futbol fayllari Githubdagi omboringizga ko'chib o'tadi).*

## 3-bosqich: Render.com orqali Yonga qo'yish (Hosting)
1. **Render.com** saytiga kiring (Github zikrida logindan o'ting).
2. Tepadagi `New +` tugmasini bosib **"Web Service"** bo'limini tanlang.
3. Sahifada sizning boyagi Githubingizdagi repozitoriylar ro'yxati chiqadi, o'shalar ichidan `futbol-avtobot` ni tanlab `Connect` qiling.
4. Sozlamalar:
   - **Name:** futbolbotchi (ixtiyoriy)
   - **Language:** Python
   - **Run Command:** `gunicorn keep_alive:app & python main.py`
   - **Instance Type:** Bepul (Free) ni tanlang.
5. Eng pastda (Environment Variables - Advance) bo'limida barcha sirlaringizni `.env` dagi kabi bitta-bitta klavish va kalitlarini **(BOT_TOKEN, ADMIN_ID va h.k)** kiritib chiqing.
6. **"Create Web Service"** tugmachasiga bosing!
7. 2-3 daqiqa o'tib consolde **Taymer (Scheduler) ishga tushdi!** degan yashil xat chiqadi, demak ishingiz mukammal bajarildi!

U endi avtomat ishida davom etaveradi! Tabriklaymiz sizning shaxsiy Avtobot Kloni yaratildi. Muvaffaqiyatlar!
