<div dir="rtl" align="center">

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ██╗  ██╗     ███████╗    ███╗   ██╗    ███╗   ███╗ █████╗    ║
║    ██║ ██╔╝     ██╔════╝    ████╗  ██║    ████╗ ████║██╔══██╗   ║
║    █████╔╝      █████╗      ██╔██╗ ██║    ██╔████╔██║███████║   ║
║    ██╔═██╗      ██╔══╝      ██║╚██╗██║    ██║╚██╔╝██║██╔══██║   ║
║    ██║  ██╗     ███████╗    ██║ ╚████║    ██║ ╚═╝ ██║██║  ██║   ║
║    ╚═╝  ╚═╝     ╚══════╝    ╚═╝  ╚═══╝    ╚═╝     ╚═╝╚═╝  ╚═╝   ║
║                                                                  ║
║              🤖 بووت إدارة مجموعات طلاب جامعة الملك خالد 🤖       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-24.0-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

---

</div>

<div dir="rtl">

## نظرة عامة

**KKU BOT** هو بووت تيليجرام شامل لإدارة وحماية مجموعات الطلاب في **جامعة الملك خالد** (KKU)، المملكة العربية السعودية. يوفر البووت نظاماً متكاملاً لإدارة الأخبار، الأسئلة الشائعة، الخطط الدراسية، الحماية من السبام، والتحكم الكامل في المجموعات والقنوات.

يحتوي المشروع على لوحة تحكم ويب (React SPA) لإدارة جميع الإعدادات والبيانات بشكل مرئي وسهل.

---

## المميزات

| # | الميزة | الوصف |
|---|--------|-------|
| 1 | **إدارة الأخبار** | إنشاء وتعديل ونشر ونشر מחדש للمنشورات مع الصور والملفات في المجموعات والقنوات |
| 2 | **نظام الأسئلة الشائعة** | أسئلة وإجابات بناءً على الكلمات المفتاحية مع تطابق ضبابي، مرتبطة بالأخبار |
| 3 | **الردود التلقائية** | مطابقة بثلاث مستويات: تام → جزئي → ضبابي (عتبة 0.6)، مع دعم المرفقات |
| 4 | **الخطط الدراسية** | منظمة حسب الكلية والمستوى، مع بحث مُنقَّح للنصوص العربية |
| 5 | **المنشورات المجدولة** | تكرار يومي/أسبوعي/شهري، يعمل كل 60 ثانية |
| 6 | **حماية المجموعات** | 46 كلمة سبام، 6 أنماط تعبير نمطي، تأكيد بالذكاء الاصطناعي، حدود المعدل |
| 7 | **حظر المستخدمين** | حظر/إلغاء حظر عبر جميع المجموعات المسجلة |
| 8 | **البث** | إرسال رسائل لجميع المجموعات المسجلة |
| 9 | **بوابة الاشتراك** | يجب الاشتراك في القناة الرسمية لاستخدام البوت |
| 10 | **التكامل مع الذكاء الاصطناعي** | بحث DuckDuckGo + نموذج OpenCode AI (mimo-v2.5-free) |
| 11 | **لوحة تحكم ويب** | واجهة React SPA بـ 9 صفحات لإدارة البوت |
| 12 | **التخزين السحابي** | Cloudflare R2 (متوافق مع S3) لتخزين الملفات |
| 13 | **سجل النشاط** | تتبع جميع إجراءات المسؤول |

---

## التقنيات المستخدمة

### الباك إند (Backend)

| التقنية | الإصدار | الوظيفة |
|---------|---------|---------|
| Python | 3.11 | لغة البرمجة الأساسية |
| python-telegram-bot | 20.7 | واجهة تيليجرام (مع دعم Job Queue) |
| SQLAlchemy | 2.0.23 | ORM لقاعدة البيانات (asyncpg 0.29.0) |
| FastAPI | 0.104.1 | واجهة برمجة التطبيقات (REST API) |
| uvicorn | 0.24.0 | خادم ASGI |
| python-jose | 3.3.0 | توقيع JWT |
| passlib | 1.7.4 | تشفير كلمات المرور |
| httpx | ~0.25.2 | عميل HTTP غير متزامن |
| boto3 | - | عميل AWS S3 (لـ Cloudflare R2) |
| ddgs | >=7.0.0 | بحث DuckDuckGo |
| PyMuPDF | 1.24.3 | معالجة ملفات PDF |
| Pillow | - | معالجة الصور |
| hijri-converter | 2.3.2.post1 | تحويل التواريخ الهجرية |

### الواجهة الأمامية (Frontend)

| التقنية | الإصدار | الوظيفة |
|---------|---------|---------|
| React | 18.2.0 | مكتبة الواجهات |
| react-router-dom | 6.20.0 | التوجيه |
| Recharts | 2.10.3 | الرسوم البيانية |
| Vite | 5.0.8 | أداة البناء |

### البنية التحتية (Infrastructure)

| التقنية | الوظيفة |
|---------|---------|
| PostgreSQL 15 | قاعدة البيانات |
| Docker + Docker Compose | الحاويات |
| Render.com | الاستضافة (الخطة المجانية) |
| GitHub Actions | الحفاظ على التشغيل (keep-alive) |
| Cloudflare R2 | التخزين السحابي |

---

## المتطلبات

- Python 3.11+
- Node.js 20+ (لبناء لوحة التحكم)
- PostgreSQL 15+
- حساب تيليجرام للبوت (من [@BotFather](https://t.me/BotFather))
- حساب Cloudflare (اختياري، للتخزين السحابي)

---

## التثبيت

### التثبيت المحلي

```bash
# 1. استنساخ المستودع
git clone https://github.com/your-username/KKU-BOT.git
cd KKU-BOT

# 2. إنشاء البيئة الافتراضية
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. تثبيت المتطلبات
pip install -r requirements.txt

# 4. إعداد ملف البيئة
copy .env.example .env
# عدّل قيم .env حسب إعداداتك

# 5. بناء لوحة التحكم
cd dashboard
npm install
npm run build
cd ..

# 6. تشغيل البوت
python bot/main.py
```

### التثبيت باستخدام Docker

```bash
# 1. إعداد ملف البيئة
copy .env.example .env
# عدّل قيم .env

# 2. التشغيل
docker-compose up -d

# 3. عرض السجلات
docker-compose logs -f

# 4. الإيقاف
docker-compose down
```

### النشر على Render.com

1. ارفع الكود إلى GitHub
2. أنشئ حساب على [Render.com](https://render.com)
3. أنشئ **Background Worker** للبوت
4. أنشئ **Web Service** لـ API
5. أضف متغيرات البيئة (Environment Variables) في لوحة التحكم
6. Render سيقوم تلقائياً بنشر المشروع

**ملاحظة:** يحتوي الملف `render.yaml` على إعدادات النشر التلقائية.

---

## متغيرات البيئة

### مطلوبة (Required)

| المتغير | الوصف | مثال |
|---------|-------|------|
| `BOT_TOKEN` | توكن البوت من BotFather | `123456:ABC-DEF...` |
| `DATABASE_URL` | رابط اتصال PostgreSQL | `postgresql://user:pass@localhost:5432/kku_bot` |
| `ADMIN_IDS` | معرفات المسؤولين (مفصولة بفاصلة) | `123456789,987654321` |
| `SECRET_KEY` | مفتاح توقيع JWT | `your-super-secret-key-change-this` |
| `ADMIN_USERNAME` | اسم مستخدم لوحة التحكم | `admin` |
| `ADMIN_PASSWORD` | كلمة مرور لوحة التحكم | `secure-password` |

### اختيارية (Optional)

| المتغير | الوصف | القيمة الافتراضية |
|---------|-------|-------------------|
| `R2_ACCOUNT_ID` | معرّف حساب Cloudflare | `""` |
| `R2_ACCESS_KEY_ID` | مفتاح الوصول لـ R2 | `""` |
| `R2_SECRET_ACCESS_KEY` | المفتاح السري لـ R2 | `""` |
| `R2_BUCKET_NAME` | اسم الحاوية | `kku-bot` |
| `R2_PUBLIC_URL` | الرابط العام للملفات | `""` |
| `OPENCODE_API_KEY` | مفتاح API للذكاء الاصطناعي | `""` |
| `OPENCODE_API_URL` | رابط API للذكاء الاصطناعي | `""` |
| `OPENCODE_AI_MODEL` | نموذج الذكاء الاصطناعي | `""` |
| `PORT` | منفذ الخادم | `8000` |

---

## أوامر البوت

### أوامر المستخدمين

| الأمر | الوصف |
|-------|-------|
| `/start` | بدء التشغيل ومعرفة المميزات |
| `/help` | عرض المساعدة |
| `/news` | عرض آخر الأخبار |
| `/questions` | البحث عن أسئلة شائعة |
| `/plans` | عرض الخطط الدراسية |
| `/responses` | عرض الردود المتاحة |

### أوامر المسؤولين (Slash Commands)

| الأمر | الوصف |
|-------|-------|
| `/admin` | لوحة تحكم المسؤول |
| `/r` | إدارة الردود |
| `/q` | إدارة الأسئلة |
| `/n` | إدارة الأخبار |
| `/stats` | الإحصائيات |
| `/groups` | إدارة المجموعات |
| `/broadcast` | بث رسالة لجميع المجموعات |
| `/ban` | حظر مستخدم |
| `/unban` | إلغاء حظر مستخدم |
| `/banned` | قائمة المحظورين |

### أوامر المسؤولين (نص عربي)

| الأمر | الوصف |
|-------|-------|
| `اضافه رد` | إضافة رد جديد |
| `حذف رد` | حذف رد موجود |
| `قائمة الردود` | عرض جميع الردود |
| `اضافه سؤال` | إضافة سؤال جديد |
| `حذف سؤال` | حذف سؤال موجود |
| `قائمة الاسئلة` | عرض جميع الأسئلة |
| `اضافه منشور` | إضافة منشور جديد |
| `حذف منشور` | حذف منشور موجود |
| `قائمة المنشورات` | عرض جميع المنشورات |
| `حظر` | حظر مستخدم |
| `الغاء حظر` | إلغاء حظر مستخدم |
| `قائمة المحظورين` | عرض المحظورين |
| `الاحصائيات` | عرض الإحصائيات |
| `القروبات` | إدارة المجموعات |
| `اذاعة` | بث رسالة |
| `مساعدة` | عرض المساعدة |

---

## نظام الحماية

يحتوي البووت على نظام حماية متقدم ضد السبام والرسائل غير المرغوبها:

### كلمات السبام (46 كلمة)

<div dir="ltr">

```
- روابط مختصرة (bit.ly, tinyurl, t.co, etc.)
- محتوى للبالغين
- أدوية غير مشروعة
- احتيال ونصب
- سبام تجاري
```

</div>

### أنماط التحقق (Regex)

| النمط | الوصف |
|-------|-------|
| `3+ روابط URL` | كشف الرسائل التي تحتوي على 3 روابط أو أكثر |
| `@mentions 15+ حرف` | كشف الإشارات الطويلة (السبام التجاري) |
| `WhatsApp/Telegram links` | روابط واتساب وتيليجرام المشبوهة |
| `أرقام هواتف` | كشف أرقام الهاتف في الرسائل |

### آلية العمل

1. **تحليل الرسالة** - فحص النص بناءً على الكلمات والأنماط
2. **تطابق ثلاثي المستوى**:
   - **تطابق تام** - كلمة السبام موجودة بالضبط
   - **تطابق جزئي** - كلمة السبام موجودة داخل نص أطول
   - **تطابق ضبابي** - تطابق بمعامل 0.6
3. **تأكيد بالذكاء الاصطناعي** - استخدام AI للتحقق قبل الحظر
4. **حدود المعدل** - حظر تلقائي عند تجاوز الحد (5 رسائل في 60 ثانية)
5. **تطبيع النص العربي** - تجاهل علامات التشكيل والنقاط

---

## لوحة التحكم (Dashboard)

لوحة تحكم ويب مبنية بـ **React SPA** مع 9 صفحات:

| الصفحة | الوصف |
|--------|-------|
| **الرئيسية** | نظرة عامة + إحصائيات أسبوعية |
| **المجموعات** | إدارة القنوات والمجموعات |
| **الأخبار** | CRUD + نشر + تحسين المحتوى |
| **قاموس الردود** | الردود التلقائية + الأسئلة الشائعة |
| **الخطط الدراسية** | مجموعات الخطط + الخطط + النشر |
| **المنشورات المجدولة** | CRUD + رفع الملفات |
| **المحظورين** | إدارة المستخدمين المحظورين |
| **سجل النشاط** | تتبع جميع الإجراءات |
| **الإعدادات** | إعدادات البوت والنظام |

### بناء لوحة التحكم

```bash
cd dashboard
npm install
npm run build
```

الملفات المبنية توضع في `dashboard/dist/` وتُخدم تلقائياً عبر FastAPI.

---

## هيكل المشروع

```
KKU BOT/
├── bot/
│   ├── main.py              # نقطة دخول البوت
│   ├── config.py            # تحميل متغيرات البيئة
│   ├── models/
│   │   └── models.py        # نماذج SQLAlchemy (12 جدول)
│   ├── services/
│   │   ├── ai.py            # ذكاء اصطناعي + بحث DuckDuckGo
│   │   ├── cloud_storage.py # Cloudflare R2 (boto3)
│   │   ├── database.py      # جميع عمليات قاعدة البيانات (~814 سطر)
│   │   ├── news_publisher.py# نشر/تعديل/حذف تيليجرام
│   │   ├── protection.py    # نظام الحماية ضد السبام
│   │   ├── responses.py     # معالج الردود التلقائية
│   │   ├── responses_system.py # الردود الافتراضية المضمّنة
│   │   └── scheduler.py     # فاحص المنشورات المجدولة (كل 60 ثانية)
│   ├── handlers/
│   │   ├── start.py         # /start + أزرار المميزات
│   │   ├── help.py          # /help
│   │   ├── admin.py         # أوامر المسؤول النصية بالعربية (907 أسطر)
│   │   ├── admin_commands.py# أوامر الشرطة (/r, /q, /n, etc.)
│   │   ├── news.py          # /news
│   │   ├── questions.py     # /questions
│   │   ├── study_plans.py   # /plans + محفزات النص
│   │   ├── broadcast.py     # /broadcast
│   │   ├── responses.py     # /responses
│   │   ├── group_handler.py # تتبع المجموعات + /registergroup
│   │   └── channel_handler.py # تتبع القنوات + /registerchannel
│   ├── middleware/
│   │   └── subscription.py  # بوابة الاشتراك
│   └── api/
│       ├── main.py          # تطبيق FastAPI
│       ├── auth.py          # مصادقة JWT
│       ├── config.py        # إعدادات API
│       └── routes/          # نقاط النهاية (REST)
├── dashboard/               # واجهة React SPA (Vite)
├── database/
│   └── schema.sql           # المخطط القديم (غير محدث)
├── docker-compose.yml       # bot + PostgreSQL
├── Dockerfile               # Python 3.11 + Node 20
├── render.yaml              # إعداد نشر Render
├── start.sh                 # نقطة دخول Docker
├── requirements.txt         # متطلبات Python
└── .env.example             # مثال على ملف البيئة
```

---

## قاعدة البيانات

### الجداول (12 جدول)

| # | الجدول | الوصف |
|---|--------|-------|
| 1 | `users` | المستخدمون (telegram_id, username, first_name, is_subscribed) |
| 2 | `channel_groups` | القنوات والمجموعات (chat_id, title, type, member_count, is_active, is_official) |
| 3 | `auto_responses` | الردود التلقائية (keyword, response, file_url, file_tg_id, news_id FK) |
| 4 | `banned_users` | المحظورون (telegram_id, reason, banned_by) |
| 5 | `activity_log` | سجل النشاط (action, details, performed_by) |
| 6 | `news` | الأخبار (content, image_url, file_url, files_json, target_channels JSON) |
| 7 | `questions` | الأسئلة الشائعة (question, answer, category, keywords, news_id FK) |
| 8 | `scheduled_posts` | المنشورات المجدولة (content, schedule_time, is_recurring, recurring_interval) |
| 9 | `study_plan_groups` | مجموعات الخطط الدراسية (title, specialization, link, channel_message_id) |
| 10 | `study_plans` | الخطط الدراسية (group_id FK, faculty, level, plan_url, usage_count) |
| 11 | `settings` | الإعدادات (key unique, value) |

---

## التشغيل

### تشغيل محلي

```bash
python bot/main.py
```

### تشغيل Docker

```bash
docker-compose up -d
```

### هيكل start.sh

```bash
#!/bin/bash
# تشغيل البوت + FastAPI بشكل متوازي
# يمر على إشارات SIGTERM للإيقاف النظيف
```

---

## الترخيص

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

هذا المشروع مرخص بموجب **MIT License**.

```
MIT License

Copyright (c) 2026 KKU BOT

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**تم بناؤه بـ ❤️ لطلاب جامعة الملك خالد**

</div>
