<div dir="rtl">

```
  ████████╗ ██████╗  █████╗  ██████╗██╗  ██╗███╗   ███╗ ██████╗  ██████╗ ██████╗
  ╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝██║ ██╔╝████╗ ████║██╔═══██╗██╔═══██╗██╔══██╗
     ██║   ██║   ██║███████║██║     █████╔╝ ██╔████╔██║██║   ██║██║   ██║██████╔╝
     ██║   ██║   ██║██╔══██║██║     ██╔═██╗ ██║╚██╔╝██║██║   ██║██║   ██║██╔══██╗
     ██║   ╚██████╔╝██║  ██║╚██████╗██║  ██╗██║ ╚═╝ ██║╚██████╔╝╚██████╔╝██║  ██║
     ╚═╝    ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
```

# 🎓 KKU BOT — بوت إدارة وحماية قروبات جامعة الملك خالد

بوت تيليجرام احترافي متكامل يجمع بين إدارة المحتوى الأكاديمي والحماية الذكية من الحسابات المزعجة، مع لوحة تحكم ويب حديثة ونظام نشر مجدول.

---

## ✨ الميزات الرئيسية

| الميزة | الوصف |
|--------|-------|
| 📰 إدارة الأخبار والمنشورات | إضافة وتعديل وحذف ونشر الأخبار مع الصور والملفات |
| ❓ الأسئلة الشائعة (FAQ) | نظام أسئلة وأجوبة مع تطابق ذكي بالكلمات المفتاحية |
| 📋 الخطط الدراسية | إدارة الخطط الدراسية لكل كلية ومستوى دراسي |
| 🤖 ردود تلقائية ذكية | ردود فورية بتقنية التطابق الضبابي (Fuzzy Matching) |
| 🛡️ حماية القروبات | كشف السبام، الأنماط المشبوهة، Rate Limiting، تطبيع النص العربي |
| 🚫 نظام الحظر | حظر المستخدمين المخالفين مع سبب الحظر |
| 📅 نشر مجدول | جدولة المنشورات للنشر التلقائي في أوقات محددة |
| 📢 الإذاعة | إرسال رسائل جماعية لجميع القروبات المسجلة |
| 🌐 لوحة تحكم ويب | واجهة React حديثة لإدارة جميع مكونات البوت |
| 🤖 ذكاء اصطناعي | تحليل المحتوى باستخدام OpenCode AI |
| 📁 رفع الملفات | دعم رفع الصور والملفات عبر Cloudinary |
| 📊 سجل النشاطات | تتبع جميع العمليات والتعديلات |

---

## 🏗️ هيكل المشروع

```
KKU BOT/
├── bot/
│   ├── api/                 # FastAPI endpoints للوحة التحكم
│   ├── handlers/            # معالجات أوامر البوت
│   │   ├── start.py         # أمر /start
│   │   ├── help.py          # أمر /help
│   │   ├── news.py          # إدارة الأخبار
│   │   ├── questions.py     # إدارة الأسئلة الشائعة
│   │   ├── study_plans.py   # إدارة الخطط الدراسية
│   │   ├── broadcast.py     # نظام الإذاعة
│   │   ├── responses.py     # إدارة الردود التلقائية
│   │   ├── admin_commands.py # أوامر المشرفين
│   │   ├── admin.py         # معالجات المشرف
│   │   └── group_handler.py # إدارة القروبات
│   ├── middleware/          # Middleware (الاشتراك في القناة)
│   ├── models/             # نماذج SQLAlchemy
│   ├── services/           # الخدمات (قاعدة البيانات، الحماية، الردود)
│   ├── config.py           # إعدادات البوت
│   └── main.py             # نقطة الدخول الرئيسية
├── dashboard/              # لوحة تحكم React
│   ├── src/
│   │   ├── components/     # مكونات الواجهة
│   │   ├── pages/          # صفحات لوحة التحكم
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js
├── database/
│   └── schema.sql          # مخطط قاعدة البيانات
├── uploads/                # الملفات المرفوعة
├── Dockerfile              # ملف Docker
├── docker-compose.yml      # إعدادات Docker Compose
├── render.yaml             # إعدادات النشر على Render
├── requirements.txt        # المتطلبات البرمجية
└── start.sh                # سكريبت التشغيل
```

---

## 🗃️ قاعدة البيانات

تتكون قاعدة البيانات من **10 جداول**:

| الجدول | الوصف |
|--------|-------|
| `users` | المستخدمون المسجلون |
| `groups` | القروبات المسجلة |
| `auto_responses` | الردود التلقائية |
| `questions` | الأسئلة الشائعة |
| `news` | الأخبار والمنشورات |
| `scheduled_posts` | المنشورات المجدولة |
| `study_plans` | الخطط الدراسية |
| `study_plan_groups` | ربط الخطط بالقروبات |
| `banned_users` | المستخدمون المحظورون |
| `activity_log` | سجل النشاطات |
| `response_categories` | تصنيفات الردود |
| `settings` | إعدادات البوت |

---

## 📋 المتطلبات

- **Python** 3.10 أو أحدث
- **Node.js** 20+ (لبناء لوحة التحكم)
- **PostgreSQL** 15+
- توكن بوت تيليجرام (من [@BotFather](https://t.me/BotFather))

---

## 🔧 التثبيت والتشغيل

### التشغيل المحلي

1. استنساخ المستودع:
```bash
git clone https://github.com/your-repo/kku-bot.git
cd kku-bot
```

2. تثبيت المتطلبات:
```bash
pip install -r requirements.txt
```

3. تثبيت متطلبات لوحة التحكم:
```bash
cd dashboard
npm install
npm run build
cd ..
```

4. إنشاء ملف `.env` وتعبئة المتغيرات (انظر القسم التالي)

5. تشغيل البوت:
```bash
python -m bot.main
```

### باستخدام Docker

```bash
docker-compose up -d
```

هذا سيشغّل البوت وقاعدة البيانات PostgreSQL في حاويات منفصلة.

### النشر على Render

1. ارفع الكود إلى GitHub
2. أنشئ خدمة **Web Service** على Render
3. اربط المستودع واختر ملف `render.yaml` كإطار عمل
4. أدخل المتغيرات البيئية في لوحة تحكم Render
5. سيقوم Render ببناء وتشغيل المشروع تلقائياً

---

## 🔐 المتغيرات البيئية

أنشئ ملف `.env` في جذر المشروع:

```env
# === Telegram Bot ===
BOT_TOKEN=توكن_البوت_من_BotFather
CHANNEL_ID=@username_القناة
CHANNEL_LINK=https://t.me/username_القناة

# === Database ===
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kku_bot

# === Admin ===
ADMIN_IDS=123456789,987654321

# === Dashboard ===
SECRET_KEY=مفتاح_سري_للتوثيق
ADMIN_USERNAME=admin
ADMIN_PASSWORD=كلمة_مرور_آمنة

# === Cloudinary (اختياري - لرفع الملفات) ===
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name

# === AI (اختياري) ===
GEMINI_API_KEY=مفتاح_Gemini_API
OPENROUTER_API_KEY=مفتاح_OpenRouter_API
```

| المتغير | مطلوب | الوصف |
|---------|-------|-------|
| `BOT_TOKEN` | ✅ | توكن البوت من BotFather |
| `CHANNEL_ID` | ✅ | معرّف أو اسم مستخدم للقناة |
| `CHANNEL_LINK` | ✅ | رابط الدعوة للقناة |
| `DATABASE_URL` | ✅ | رابط الاتصال بقاعدة البيانات PostgreSQL |
| `ADMIN_IDS` | ✅ | معرّفات المشرفين (مفصولة بفاصلة) |
| `SECRET_KEY` | ✅ | مفتاح سري لتشفير جلسات لوحة التحكم |
| `ADMIN_USERNAME` | ✅ | اسم مستخدم لدخول لوحة التحكم |
| `ADMIN_PASSWORD` | ✅ | كلمة مرور لوحة التحكم |
| `CLOUDINARY_URL` | ❌ | إعدادات Cloudinary لرفع الصور والملفات |
| `GEMINI_API_KEY` | ❌ | مفتاح Google Gemini AI |
| `OPENROUTER_API_KEY` | ❌ | مفتاح OpenRouter API |

---

## 🤖 أوامر البوت

### أوامر المستخدمين

| الأمر | الوصف |
|-------|-------|
| `/start` | بدء التفاعل مع البوت |
| `/help` | عرض قائمة المساعدة |
| `/news` | عرض آخر الأخبار والمنشورات |
| `/questions` | البحث في الأسئلة الشائعة |
| `/plans` | عرض الخطط الدراسية |
| `/responses` | استعراض الردود التلقائية المتاحة |
| `/registergroup` | تسجيل القروب في قائمة الإذاعة (للمشرفين) |

### أوامر المشرفين

| الأمر | الوصف |
|-------|-------|
| `/admin` | لوحة التحكم السريعة |
| `/r add` | إضافة رد تلقائي جديد |
| `/r del` | حذف رد تلقائي |
| `/r list` | عرض جميع الردود |
| `/r search` | البحث في الردود |
| `/q add` | إضافة سؤال شائع جديد |
| `/q del` | حذف سؤال شائع |
| `/q list` | عرض جميع الأسئلة |
| `/q search` | البحث في الأسئلة |
| `/n add` | إضافة خبر جديد |
| `/n del` | حذف خبر |
| `/n list` | عرض جميع الأخبار |
| `/n edit` | تعديل خبر موجود |
| `/n republish` | إعادة نشر خبر |
| `/ban` | حظر مستخدم |
| `/unban` | إلغاء حظر مستخدم |
| `/banned` | عرض قائمة المحظورين |
| `/stats` | عرض الإحصائيات |
| `/groups` | عرض القروبات المسجلة |
| `/broadcast` | إذاعة رسالة لجميع القروبات |

### الأوامر باللغة العربية (في القروبات)

| الأمر | الوصف |
|-------|-------|
| `اضافه رد` | إضافة رد تلقائي |
| `احذف رد` | حذف رد تلقائي |
| `قائمة الردود` | عرض جميع الردود |
| `اضافه سؤال` | إضافة سؤال شائع |
| `حظر` | حظر مستخدم |
| `الغاء حظر` | إلغاء حظر مستخدم |
| `اذاعة` | إرسال رسالة جماعية |
| `الاحصائيات` | عرض إحصائيات البوت |
| `قائمة القروبات` | عرض القروبات المسجلة |
| `مساعدة` | عرض قائمة المساعدة |

---

## 🛡️ نظام الحماية

يوفر البوت نظام حماية متعدد الطبقات للقروبات:

- **كشف السبام**: كشف الرسائل المتكررة والرسائل المتشابهة
- **الأنماط المشبوهة**: كشف الروابط المشبوهة والحسابات المزيفة
- **Rate Limiting**: تحديد عدد الرسائل لكل مستخدم في فترة زمنية معينة
- **الحسابات المحظورة**: حظر المستخدمين المخالفين نهائياً
- **تطبيع النص العربي**: معالجة المشاكل الشائعة في الكتابة بالعربي (التشكيل، المسافات، إلخ)

---

## 🖥️ لوحة التحكم

لوحة تحكم ويب مبنية بـ **React** و **Vite** توفر واجهة سهلة لإدارة البوت.

### الصفحات المتاحة

| الصفحة | الوصف |
|--------|-------|
| Dashboard | نظرة عامة على إحصائيات البوت |
| News | إدارة الأخبار والمنشورات |
| Questions | إدارة الأسئلة الشائعة |
| ReplyDictionary | إدارة قاموس الردود التلقائية |
| StudyPlans | إدارة الخطط الدراسية |
| ScheduledPosts | إدارة المنشورات المجدولة |
| Groups | إدارة القروبات المسجلة |
| BannedUsers | إدارة المستخدمين المحظورين |
| ActivityLog | سجل النشاطات والتعديلات |
| Responses | إدارة فئات الردود |
| Settings | إعدادات البوت |

### تشغيل لوحة التحكم محلياً

```bash
cd dashboard
npm install
npm run dev
```

ستكون لوحة التحكم متاحة على `http://localhost:5173`

---

## 📦 المكتبات والتقنيات الرئيسية

### Backend

| المكتبة | الإصدار | الاستخدام |
|---------|---------|-----------|
| python-telegram-bot | 20.7 | التعامل مع واجهة تيليجرام |
| SQLAlchemy | 2.0.23 | ORM لقاعدة البيانات |
| asyncpg | 0.29.0 | PostgreSQL asynchronous driver |
| FastAPI | 0.104.1 | API endpoints للوحة التحكم |
| httpx | 0.25.2 | HTTP client للطلبات غير المتزامنة |
| PyMuPDF | 1.24.3 | معالجة ملفات PDF |
| Cloudinary | 1.41.0 | رفع وإدارة الصور والملفات |
| python-jose | 3.3.0 | إدارة JWT tokens |
| passlib | 1.7.4 | تشفير كلمات المرور |

### Frontend

| المكتبة | الإصدار | الاستخدام |
|---------|---------|-----------|
| React | 18.2.0 | بناء واجهة المستخدم |
| Vite | 5.0.8 | أداة البناء والتطوير |

---

## 🐳 Docker

### بناء وتشغيل

```bash
# بناء وتشغيل جميع الخدمات
docker-compose up -d

# عرض السجلات
docker-compose logs -f

# إيقاف الخدمات
docker-compose down
```

### هيكل الخدمات

- **bot**: خدمة البوت الرئيسي (Python 3.11)
- **db**: خدمة قاعدة البيانات (PostgreSQL 15 Alpine)

### التخزين

- `postgres_data`: بيانات قاعدة البيانات (Volume)
- `uploads`: الملفات المرفوعة (Volume)

---

## 📜 الرخصة

هذا المشروع محمي بموجب رخصة **MIT License**.

```
MIT License

Copyright (c) 2024 KKU BOT

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

**صُنع بـ ❤️ لجامعة الملك خالد**

[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/your_bot_username)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
[![Docker](https://img.shields.io/badge/Docker-24-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

</div>
