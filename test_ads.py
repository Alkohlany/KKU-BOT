import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SPAM_KEYWORDS = [
    "taplink", "linktr", "bit.ly", "tinyurl", "cutt.ly", "shorturl.at", "rb.gy", "is.gd", "ow.ly",
    "xxx", "porn", "porno", "محتوى اباحي", "إباحي", "إباحية",
    "مخدر", "مخدرات", "حشيش", "بانجو", "drugs", "cannabis", "marijuana",
    "احتيال", "خديعة", "scam", "fraud",
    "سكليف", "اجازة مرضية", "تقرير طبي", "شهادة صحيه", "حذف ملاحظة",
    "للبيع", "رابط واتساب", "رقم واتساب", "رابط تيليجرام", "يتوفر مكان", "للإيجار",
    "يتوفر", "متوفر", "جديد", "مستعمل", "عرض خاص", "عرض",
    "توصيل", "شحن", "توصيل مجاني",
    "التواصل على", "التواصل عبر", "راسلني", "راسلنا",
    "محل", "متجر", "موقعنا",
    "خصم", "تخفيض",
    "وظيفة", "توظيف", "مطلوب عامل",
    "أعلان", "إعلان",
    "رابط مباشر", "رابط الحين",
    "واتساب مباشر", "اتواصل واتساب", "قروب واتساب", "جروب واتساب", "واتساب"
]

URL_RE = re.compile(r'https?://\S+')
LONG_AT_RE = re.compile(r'@\w{15,}')
WHATSAPP_TELEGRAM_RE = re.compile(r'(wa\.me|chat\.whatsapp|t\.me|joinchat)', re.IGNORECASE)
SAUDI_PHONE_RE = re.compile(r'(\+?967|05\d{8})')
INTL_PHONE_RE = re.compile(r'\+\d{10,}')

# Simple AI spam signals
AI_PATTERNS = [
    'حل اختبار', 'حل واجب', 'حل كويز', 'حل الواجب', 'حل الاختبار',
    'ضمان الفل', 'ضمان الدرجة', 'ضمان الدرجه', 'فل مارك',
    'اجازه مرضيه', 'اجازة مرضيه', 'عذر طبي', 'اعذار طبية',
    'سكل يف', 'sklif', 'سِڪلَيَف',
    'اسوي بحث', 'يسوي بحث', 'يحل واجب', 'يحل اختبار',
    'تحل واجب', 'تحل اختبار', 'تحل كويز',
    'ضمن الدرجه', 'ضمن الدرجة', 'ضمن فل',
    'اسعارنا منافسه', 'الترم كامل', 'اشتراك شهري',
    'منصة جامعتي', 'جامعتي الذكية',
    'فرص بحثيه', 'فرص بحثية', 'نشر علمي',
    'فرص شغل', 'ادخلو على', 'شغال فوري', 'شغال لان',
    'ازالة ملاحظ', 'شهاده صحيه', 'شهادة صحيه',
    'مدرس خصوصي', 'معلم خصوصي',
    'البورد', 'الهيئة السعودية', 'التخصصات الصحية',
    'ابحاث تخرج', 'مشاريع تخرج', 'رسائل ماجستير',
    'دكتوراه مهنية', 'الدكتوراه المهنية',
    'اوراق علميه', 'أوراق علمية',
    'Q1', 'Q2', 'Q3', 'Scopus', 'PubMed', 'Web of Science',
    'Systematic Review', 'Meta-Analysis',
    'بوربوينت', 'اسايمنت', 'Case Study',
    'تلاخيص', 'تلخيص محاضرات',
    'التواصل واتساب', 'تواصل واتساب', 'للتواصل واتساب',
    'التواصل عبر الوتس', 'التواصل عبر الواتس',
    'الحجز', 'للحجز',
]

with open(r"C:\Users\qqq\Desktop\KKU BOT\ads.txt", encoding="utf-8") as f:
    lines = f.readlines()

timestamp_re = re.compile(r'^\[\d+/\d+/\d+\s+\d+:\d+\s*[AP]M\]')

groups = []
current_group = []
for line in lines:
    stripped = line.rstrip('\n')
    if timestamp_re.match(stripped):
        if current_group:
            groups.append(current_group)
        current_group = [stripped]
    else:
        current_group.append(stripped)
if current_group:
    groups.append(current_group)

messages = []
for group in groups:
    raw_text = '\n'.join(group)
    raw_text = re.sub(r'^\[.*?\]\s*\w+:\s*', '', raw_text, count=1)
    blocks = re.split(r'\n\s*\n', raw_text)
    merged = []
    carry = ''
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if len(b) < 40:
            carry = (carry + '\n' + b).strip() if carry else b
        else:
            if carry:
                merged.append((carry + '\n' + b).strip())
                carry = ''
            else:
                merged.append(b)
    if carry:
        merged.append(carry)
    messages.extend(merged)

print(f"Total distinct ad messages: {len(messages)}\n")

caught = 0
missed = 0
kw_count = 0
rx_count = 0
ai_count = 0
miss_list = []

for i, msg in enumerate(messages, 1):
    msg_lower = msg.lower()
    kw_hits = []
    rx_hits = []

    for kw in SPAM_KEYWORDS:
        if kw.lower() in msg_lower:
            kw_hits.append(kw)

    urls = URL_RE.findall(msg)
    if len(urls) >= 3:
        rx_hits.append(f"3+ URLs ({len(urls)})")
    if LONG_AT_RE.search(msg):
        rx_hits.append("@long-username")
    if WHATSAPP_TELEGRAM_RE.search(msg):
        rx_hits.append("wa.me/t.me link")
    if SAUDI_PHONE_RE.search(msg):
        rx_hits.append("SA phone")
    if INTL_PHONE_RE.search(msg):
        rx_hits.append("intl phone")

    # AI: check simple patterns
    ai_hit = False
    for pat in AI_PATTERNS:
        if pat.lower() in msg_lower:
            ai_hit = True
            break
    # Phone number + ad context = spam
    if not ai_hit and len(msg) > 60:
        has_phone = bool(INTL_PHONE_RE.search(msg) or SAUDI_PHONE_RE.search(msg))
        has_ad_word = any(w in msg_lower for w in ['واجب', 'اختبار', 'كويز', 'بحث', 'تقرير', 'project', 'assignment', 'بوربوينت', 'секл يف', 'اجاز', 'ممرض', 'dr', 'دكتور', 'مركز', 'خدمة', 'itchtirak', 'اشتراك', 'الترم', 'ضمان', 'فل مارك', 'الدرجه', 'الدرجة'])
        if has_phone and has_ad_word:
            ai_hit = True

    if kw_hits:
        verdict = "CAUGHT"
        reason = "KW: " + ", ".join(kw_hits[:4])
        kw_count += 1
    elif rx_hits:
        verdict = "CAUGHT"
        reason = "RX: " + ", ".join(rx_hits[:3])
        rx_count += 1
    elif ai_hit:
        verdict = "CAUGHT"
        reason = "AI"
        ai_count += 1
    else:
        verdict = "MISSED"
        reason = "No detection"

    if verdict == "CAUGHT":
        caught += 1
    else:
        missed += 1
        miss_list.append((i, msg[:120].replace('\n', ' ')))

    mark = "[OK]" if verdict == "CAUGHT" else "[XX]"
    preview = msg[:95].replace('\n', ' ')
    print(f"  {mark} #{i:3d} | {reason}")
    print(f"        {preview}")
    print()

print("=" * 70)
print(f"  TOTAL ADS:    {len(messages)}")
print(f"  CAUGHT:       {caught}")
print(f"  MISSED:       {missed}")
if messages:
    print(f"  RATE:         {caught/len(messages)*100:.1f}%")
print(f"  Breakdown:")
print(f"    Keyword:    {kw_count}")
print(f"    Regex:      {rx_count}")
print(f"    AI:         {ai_count}")
print("=" * 70)

if miss_list:
    print(f"\n  MISSED MESSAGES ({len(miss_list)}):")
    for idx, preview in miss_list:
        print(f"    #{idx}: {preview}")
