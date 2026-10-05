# چکیده / Abstract — «آینده فضای مجازی ایران در عصر هوش مصنوعی»

**محور پیشنهادی:** زیرساخت، فناوری و استقلال فناورانه  (محور دوم: رسانه، فرهنگ و زیست دیجیتال)
**مهلت ارسال:** ۳۰ دی ۱۴۰۵ · **نتایج داوری:** ۲۰ بهمن · **برگزاری:** ۱۷ اسفند ۱۴۰۵

## عنوان
سیمرغ: مطالعه‌ی موردی یک دستیار هوش مصنوعی فارسی، آفلاین و منبع‌محور روی سخت‌افزار مصرفی

## چکیده (فارسی)
وابستگی به سرویس‌های ابری خارجی، اختلال یا فیلتر اینترنت و ضعف مدل‌های کوچک در دانش فرهنگی فارسی، سه مانع عملی برای استقلال فناورانه در هوش مصنوعی‌اند. این مقاله سیمرغ را به‌عنوان مطالعه‌ی موردی معرفی می‌کند: دستیاری که کاملاً محلی و بدون اتصال به اینترنت اجرا می‌شود و یک مدل زبانی کوچک (Gemma-3-4B با کوانتیزاسیون ۴بیتی) را با یک لایه‌ی بازیابی قطعی از منابع محلی ترکیب می‌کند: حدود ۱٫۴ میلیون بیت از ادبیات کلاسیک فارسی و ۶٬۲۳۶ آیه‌ی قرآن با ترجمه‌ی فارسی. اصل طراحی این است که پاسخ‌های مستند به منبع بدون دخالت مدل و با برچسب روشن «بازیابی‌شده» ارائه شوند و اگر منبعی نباشد، سیستم به‌جای جعل، ناتوانی خود را اعلام کند. سامانه روی رایانه‌ای با پردازنده‌ی i5-4460، ۷٫۷ گیگابایت حافظه و بدون پردازنده‌ی گرافیکی، با سرعت حدود ۱۰ توکن در ثانیه اجرا شد. در آزمون «این بیت از کیست؟» روی ۳۰۰ بیت تصادفی (حالت آسان: پرسش از خود پایگاه ساخته شده)، همه‌ی پرسش‌ها درست پاسخ گرفتند و ۰ از ۱۴۱ بیت ترکیبی ساختگی به‌اشتباه پذیرفته شد. با پرسش چهارکلمه‌ای از میان بیت، ۲۸۷ از ۲۸۸ پاسخ درست بود؛ با حذف یک حرف، سیستم تنها ۳۵٪ پرسش‌ها را پاسخ داد، اما هیچ‌کدام از ۱۰۶ پاسخ غلط نبود. محدودیت‌ها شامل ارزیابی روی یک دستگاه و یک نمونه، وابستگی درستی به نسبت‌دهی خود پایگاه داده، و نبود ارزیابی انسانی است. نتایج و کد با یک دستور تکرارپذیرند. در پایان سه توصیه‌ی سیاستی برای حمایت از زیرساخت‌های بومی و آفلاین ارائه می‌شود.

**کلیدواژه‌ها:** هوش مصنوعی بومی، استقلال فناورانه، مدل زبانی محلی، زبان فارسی، بازیابی منبع‌محور

## Abstract (English)
Dependence on foreign cloud services, internet disruption or filtering, and the weak cultural knowledge of small language models are three practical barriers to technological independence in AI. This paper presents Simorgh, a case study of a fully local, offline Persian assistant that pairs a small language model (Gemma-3-4B, 4-bit quantised) with a deterministic retrieval layer over local sources: about 1.4 million verses of classical Persian poetry and 6,236 Quranic verses with a Persian translation. Its core design rule is that source-backed answers are returned without model involvement and labelled as retrieved, and that the system states uncertainty instead of fabricating when no source exists. The system ran on a 2014-era desktop (Core i5-4460, 7.7 GB RAM, no GPU) at roughly 10 tokens per second. On a "who wrote this verse?" test over 300 random verses (an easy setting: queries derived from the database itself), all queries were answered correctly and 0 of 141 synthetic chimera verses were wrongly accepted. With four-word mid-verse queries, 287 of 288 answers were correct; with one letter dropped, the system answered only 35% of queries but none of its 106 answers was wrong. Limitations include a single machine and sample, correctness bounded by the database's own attributions, and no human evaluation. Results and code are reproducible with one command. We conclude with three policy recommendations for supporting local, offline AI infrastructure.

**Keywords:** sovereign AI, technological independence, local language models, Persian, retrieval-grounded generation

## یادداشت‌های داخلی (حذف شود پیش از ارسال)
- «سه توصیه‌ی سیاستی» هنوز نوشته نشده؛ باید در متن کامل بیاید و چکیده فقط به آن اشاره کند.
- اعداد QA مدل (۶ از ۹) عمداً در چکیده نیست: مجموعه‌ی ده‌سؤالی برای ادعا کافی نیست. با مجموعه‌ی `fa-eval` بزرگ‌تر جایگزین شود.
- ۲۸۷/۲۸۸: یک پاسخ غلط هنوز بررسی نشده؛ قبل از ارسال علتش مشخص شود.
- در متن انگلیسی عبارت «2014-era» برای i5-4460 آمده (سال عرضه‌ی این پردازنده)؛ پیش از ارسال تأیید شود.
