<div dir="rtl">

# 🎓 KKU BOT

<div align="center">

```
  ███╗   ███╗ ███╗   ███╗ ██████╗  ██████╗ ██╗  ██╗ █████╗  ██████╗██╗  ██╗
  ████╗ ████║ ████╗ ████║██╔═══██╗██╔═══██╗██║ ██╔╝██╔══██╗██╔════╝██║ ██╔╝
  ██╔████╔██║ ██╔████╔██║██║   ██║██║   ██║█████╔╝ ███████║██║     █████╔╝
  ██║╚██╔╝██║ ██║╚██╔╝██║██║   ██║██║   ██║██╔═██╗ ██╔══██║██║     ██╔═██╗
  ██║ ╚═╝ ██║ ██║ ╚═╝ ██║╚██████╔╝╚██████╔╝██║  ██╗██║  ██║╚██████╗██║  ██╗
  ╚═╝     ╚═╝ ╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
```

**بوت تيليجرام شامل لإدارة وحماية قروبات جامعة الملك خالد**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Docker](https://img.shields.io/badge/Docker-24-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📖 نظرة عامة

**KKU BOT** هو بوت تيليجرام متعدد الميزات مصمم خصيصاً لإدارة وحماية قروبات جامعة الملك خالد. يوفر البوت نظاماً شاملاً لإدارة المحتوى الأكاديمي (الأخبار، الأسئلة الشائعة، الخطط الدراسية) مع نظام حماية ذكي متعدد الطبقات من السبام والحسابات المزعجة، ولوحة تحكم ويب حديثة، ونشر مجدول للمنشورات.

---

## ✨ الميزات الرئيسية

<div align="center">

| # | الميزة | الوصف |
|---|--------|-------|
| 1 | إدارة الأخبار والمنشورات | إضافة، تعديل، نشر، إعادة نشر الأخبار مع الصور والملفات |
| 2 | نظام الأسئلة الشائعة (FAQ) | أسئلة وأجوبة مع تطابق ضبابي (Fuzzy Matching) ومربط بالأخبار |
| 3 | الردود التلقائية الذكية | مطابقة ثلاثية المستويات: تطابق كامل ← جزئي ← ضبابي، مع دعم المرفقات |
| 4 | الخطط الدراسية | منظمة حسب الكلية والمستوى قابلة للبحث مع تطبيع النص العربي |
| 5 | النشر المجدول | جدولة منشورات مع تكرار يومي/أسبوعي/شهري |
| 6 | حماية القروبات | كشف سبام متعدد الطبقات: كلمات مفتاحية، أنماط Regex، تأكيد AI، Rate Limiting، تطبيع عربي |
| 7 | نظام الحظر | حظر وإلغاء حظر المستخدمين عبر جميع القروبات المسجلة |
| 8 | الإذاعة الجماعية | إرسال رسائل لجميع القروبات المسجلة دفعة واحدة |
| 9 | بوابة اشتراك القنوات | يجب على المستخدمين الاشتراك في قناة رسمية قبل استخدام البوت |
| 10 | دعم الذكاء الاصطناعي | بحث DuckDuckGo + OpenCode AI للمعلومات الجامبية وتحليل المحتوى |
| 11 | لوحة تحكم الويب | واجهة React SPA لإدارة جميع مكونات البوت |
| 12 | التخزين السحابي | Cloudflare R2 (متوافق مع S3) لرفع الصور والملفات |
| 13 | سجل النشاطات | تتبع جميع عمليات المشرفين |

</div>

---

## 🛠️ التقنيات المستخدمة

<div align="center">

### الواجهة الخلفية (Backend)

| المكتبة | الاستخدام |
|---------|-----------|
| Python 3.11 | لغة البرمجة |
| python-telegram-bot 20.x | التعامل مع واجهة تيليجرام |
| SQLAlchemy 2.0 | ORM لقاعدة البيانات |
| asyncpg | محرك PostgreSQL غير المتزامن |
| FastAPI | API endpoints للوحة التحكم |
| httpx | HTTP client غير المتزامن |
| boto3 | التعامل مع Cloudflare R2 (S3-compatible) |
| python-jose | إدارة JWT tokens |
| passlib | تشفير كلمات المرور |

### الواجهة الأمامية (Frontend)

| المكتبة | الاستخدام |
|---------|-----------|
| React 18 | بناء واجهة المستخدم |
| Vite | أداة البناء والتطوير |
| Recharts | الرسوم البيانية والإحصائيات |
| React Router DOM | إدارة التوجيه |

### البنية التحتية

| الأداة | الاستخدام |
|--------|-----------|
| PostgreSQL 15 | قاعدة البيانات |
| Cloudflare R2 | التخزين السحابي (S3-compatible) |
| OpenCode AI (mimo-v2.5-free) | الذكاء الاصطناعي |
| DuckDuckGo Search | البحث في الإنترنت |
| Docker + Docker Compose | الحاويات |
| Render.com | الاستضافة السحابية |
| GitHub Actions | CI/CD + Keep-Alive |

</div>

---

## 📋 المتطلبات

- **Python** 3.11 أو أحدث
- **Node.js** 20+ (لبناء لوحة التحكم)
- **PostgreSQL** 15+
- توكن بوت تيليجرام (من [@BotFather](https://t.me/BotFather))

---

## 🔧 التثبيت والتشغيل

### التشغيل المحلي

```bash
# 1. استنساخ المستودع
git clone https://github.com/your-repo/kku-bot.git
cd kku-bot

# 2. تثبيت متطلبات Python
pip install -r requirements.txt

# 3. بناء لوحة التحكم
cd dashboard
npm install
npm run build
cd ..

# 4. إعداد ملف البيئة
cp .env.example .env
# عدّل ملف .env بالمتغيرات المطلوبة (انظر القسم التالي)

# 5. تشغيل البوت
python -m bot.main
```

### باستخدام Docker

```bash
# بناء وتشغيل جميع الخدمات
docker-compose up -d

# عرض السجلات
docker-compose logs -f

# إيقاف الخدمات
docker-compose down
```

### النشر على Render

```bash
# 1. ارفع الكود إلى GitHub
# 2. أنشئ مشروع جديد على Render واستخدم render.yaml كـ Blueprint
# 3. أدخل المتغيرات البيئية في لوحة تحكم Render
# 4. سيقوم Render ببناء وتشغيل المشروع تلقائياً
```

---

## 🔐 المتغيرات البيئية

أنشئ ملف `.env` في جذر المشروع:

```env
# === Telegram Bot ===
BOT_TOKEN=توكن_البوت_من_BotFather

# === Database ===
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kku_bot

# === Admin ===
ADMIN_IDS=123456789,987654321

# === Dashboard ===
SECRET_KEY=مفتاح_سري_للتوثيق
ADMIN_USERNAME=admin
ADMIN_PASSWORD=كلمة_مرور_آمنة

# === Cloudflare R2 (التخزين السحابي) ===
R2_ACCOUNT_ID=account_id
R2_ACCESS_KEY_ID=access_key
R2_SECRET_ACCESS_KEY=secret_key
R2_BUCKET_NAME=bucket_name
R2_PUBLIC_URL=https://pub-xxxxx.r2.dev
```

| المتغير | مطلوب | الوصف |
|---------|:-----:|-------|
| `BOT_TOKEN` | ✅ | توكن البوت من BotFather |
| `DATABASE_URL` | ✅ | رابط الاتصال بقاعدة البيانات PostgreSQL |
| `ADMIN_IDS` | ✅ | معرّفات المشرفين (مفصولة بفاصلة) |
| `SECRET_KEY` | ✅ | مفتاح سري لتشفير جلسات لوحة التحكم |
| `ADMIN_USERNAME` | ✅ | اسم مستخدم لدخول لوحة التحكم |
| `ADMIN_PASSWORD` | ✅ | كلمة مرور لوحة التحكم |
| `R2_ACCOUNT_ID` | ✅ | معرّف حساب Cloudflare |
| `R2_ACCESS_KEY_ID` | ✅ | مفتاح الوصول لـ R2 |
| `R2_SECRET_ACCESS_KEY` | ✅ | المفتاح السري لـ R2 |
| `R2_BUCKET_NAME` | ✅ | اسم المجلد (Bucket) في R2 |
| `R2_PUBLIC_URL` | ✅ | الرابط العام للملفات المرفوعة |

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

يقدم البوت نظام حماية متعدد الطبقات لحماية القروبات من الحسابات المزعجة:

```
┌─────────────────────────────────────────────────────────┐
│                    طبقات الحماية                         │
├─────────────────────────────────────────────────────────┤
│  1. فلترة الكلمات المفتاحية  ←  قائمة ممنوعات مخصصة    │
│  2. أنماط Regex              ←  كشف الأنماط المشبوهة    │
│  3. التأكيد بالذكاء الاصطناعي ←  تحليل المحتوى المريب   │
│  4. Rate Limiting            ←  تحديد سرعة الرسائل      │
│  5. تطبيع النص العربي        ←  معالجة التشكيل والمسافات │
│  6. قائمة المحظورين          ←  حظر دائم عبر القروبات   │
└─────────────────────────────────────────────────────────┘
```

### آلية عمل نظام الحماية:

- **كشف السبام**: كشف الرسائل المتكررة والرسائل المتشابهة
- **الأنماط المشبوهة**: كشف الروابط المشبوهة والحسابات المزيفة عبر تعبيرات Regex
- **Rate Limiting**: تحديد عدد الرسائل لكل مستخدم في فترة زمنية معينة
- **تطبيع النص العربي**: معالجة المشاكل الشائعة في الكتابة بالعربي (التشكيل، المسافات، الهمزات، إلخ)
- **الحسابات المحظورة**: حظر المستخدمين المخالفين نهائياً عبر جميع القروبات

---

## 🖥️ لوحة التحكم

لوحة تحكم ويب مبنية بـ **React 18** و **Vite** توفر واجهة سهلة لإدارة جميع مكونات البوت.

### الصفحات المتاحة

| الصفحة | الوصف |
|--------|-------|
| **Dashboard** | نظرة عامة على إحصائيات البوت مع رسوم بيانية |
| **News** | إدارة الأخبار والمنشورات (إضافة، تعديل، حذف، نشر) |
| **Questions** | إدارة الأسئلة الشائعة |
| **Reply Dictionary** | إدارة قاموس الردود التلقائية |
| **Study Plans** | إدارة الخطط الدراسية |
| **Scheduled Posts** | إدارة المنشورات المجدولة |
| **Groups** | إدارة القروبات المسجلة |
| **Banned Users** | إدارة المستخدمين المحظورين |
| **Activity Log** | سجل النشاطات والتعديلات |
| **Responses** | إدارة فئات الردود |
| **Settings** | إعدادات البوت |

### تشغيل لوحة التحكم محلياً

```bash
cd dashboard
npm install
npm run dev
```

ستكون لوحة التحكم متاحة على `http://localhost:5173`

---

## 🗂️ هيكل المشروع

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
│   ├── services/           # الخدمات (قاعدة البيانات، الحماية، الردود، AI)
│   │   ├── ai.py           # خدمات الذكاء الاصطناعي
│   │   ├── database.py     # إدارة قاعدة البيانات
│   │   ├── protection.py   # نظام الحماية
│   │   └── storage.py      # التخزين السحابي (R2)
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

تتكون قاعدة البيانات من **12 جداول**:

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

## ⚠️ ملاحظات مهمة

- **مفتاح API للذكاء الاصطناعي**: ملف `bot/services/ai.py` يحتوي على مفتاح API مكتوب بشكل ثابت — يُنصح بنقله إلى متغيرات البيئية قبل الإنتاج
- **لا توجد اختبارات تلقائية**: المشروع لا يحتوي على اختبارات وحدات أو تكامل
- **النشر الفعلي**: المشروع منشور حالياً على Render.com مع سير عمل Keep-Alive عبر GitHub Actions

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
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://reactjs.org/)
[![Docker](https://img.shields.io/badge/Docker-24-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deploy-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)

</div>

</div>
