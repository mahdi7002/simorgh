# مخزن ملی متن‌باز (سازمان فناوری اطلاعات) — مرجع سیمرغ
منبع: خبرها و راهنمای پورتال، ۱۴۰۵/۰۷ (۲۰۲۶-۱۰-۱۲). مستقیماً توسط Claude باز نشده؛ فقط آدرس‌هایی که در متن راهنما دیده شد ثبت است.

## آدرس‌ها
- پورتال: repo.ito.gov.ir  (آدرس‌های archive.ito.gov.ir قدیمی‌اند)
- مسیر شاخص pip: UNKNOWN؛ نشانی قبلی HTTP 404 داده است
- npm/yarn: https://repo.ito.gov.ir/npm/
- maven: https://repo.ito.gov.ir/gradle/maven_central/ و .../gradle/maven_plugin/
- لینوکس (دیده‌شده): Ubuntu, Debian, Mint, CentOS, Fedora, Rocky, openSUSE
- دیگر: Docker CE, Composer (آدرسشان تأیید نشده)
- ادعای خبر: ۲۱ میلیون بسته، ۲۰ توزیع، ۱۶ زبان؛ بقیه فهرست هنوز احراز نشده
- بسته‌ای که نبود: درخواست در پورتال یا پروکسی Mirror2

## قوانین استفاده (از تصمیم‌های خود ماهدی)
1. فقط نرم‌افزار؛ داده/مدل آموزشی (دیتاست، GGUF، HF) در این مخزن تأیید نشده است
2. قبل از هر داده یا مدل: منبع و مجوز در docs/ASSET_PROVENANCE.md ثبت شود
3. هر بسته فقط وقتی VERIFIED است که بررسی واقعی انجام شده باشد، نه ادعا
4. بدون زیرسیستم جدید: یک ابزار ساده کافی است
5. آفلاین‌اول: wheel ها یک‌بار دانلود و محلی نگه داشته شوند
6. هر کار هر AI در Mother ثبت شود؛ هر ماژول با EVIDENCE.md بسته شود

## چه چیزی برای چه (آموزش و اجرای سیمرغ)
- peft, transformers, datasets, accelerate: خط لوله LoRA روی CPU (persian_pipeline_v7)
- hazm, parsivar: نرمال‌سازی و توکن‌سازی فارسی برای پاک‌سازی داده شعر/قرآن قبل از آموزش
- sentence-transformers, sqlite-vec: جست‌وجوی برداری روی quran.db (آزمایش برنامه‌ریزی‌شده)
- faster-whisper, jiwer: STT و سنجش WER
- llama-cpp-python: اجرای GGUF بدون llama-server جدا
- fastapi, uvicorn: سرویس simorgh-core


## اصلاحیه و بررسی مسیرهای مخزن

تاریخ ثبت: 2026-10-12

### وضعیت منابع

- درگاه پیشنهادی در فهرست عمومی میرورها:
  https://repo-portal.ito.gov.ir/repo
- نشانی قبلی pip:
  https://repo.ito.gov.ir/python/
  نتیجه آزمون قبلی روی این میزبان: HTTP 404
- شاخص سازگار با pip برای مخزن ملی: UNKNOWN
- Python، npm، Yarn و YUM/DNF:
  انواع مخزن گزارش‌شده در فهرست عمومی؛ دسترسی عملی هرکدام
  هنوز باید جداگانه بررسی شود.
- ادعاهای ۲۱ میلیون بسته، ۲۰ توزیع لینوکس و ۱۶ زبان:
  ادعاهای منتشرشده هستند، نه موجودی کامل و مستقلاً تأییدشده.
- وجود دیتاست آموزشی، وزن مدل، فایل GGUF یا محتوای مجاز برای
  آموزش از این اطلاعات نتیجه نمی‌شود.

### قوانین تصمیم‌گیری

- HTTP 200 به‌تنهایی اثبات نمی‌کند که یک شاخص بسته معتبر است.
- HTTP 404 روی یک مسیر، اثبات نبودن بسته در کل مخزن نیست.
- وضعیت بسته تا زمان بررسی درست: UNKNOWN یا NOT_VERIFIED.
- هیچ کتابخانه یا داده‌ای صرفاً به دلیل حضور در یک مخزن وارد
  خط آموزش سیمرغ نمی‌شود.
- پیش از استفاده، نیاز فنی، نسخه، مجوز، منبع و نتیجه آزمون
  باید مشخص شود.

فهرست عمومی برای بررسی دسته‌بندی‌ها:
https://github.com/MiravaOrg/Mirava/blob/main/README.fa.md

### HTTP probe: 2026-10-12T16:37:49+03:30
این آزمون فقط دسترسی مسیرها را می‌سنجد.

URL=https://repo-portal.ito.gov.ir/
HTTP=200 TYPE=text/html; charset=utf-8 FINAL=https://repo-portal.ito.gov.ir/
CURL_RC=0
TITLE=<title>مخزن ملی منابع متن باز

URL=https://repo-portal.ito.gov.ir/repo
HTTP=200 TYPE=text/html; charset=utf-8 FINAL=https://repo-portal.ito.gov.ir:443/repo/
CURL_RC=0
TITLE=<title>مخزن ملی منابع متن باز

URL=https://repo-portal.ito.gov.ir/repo/library/Python/Others/
HTTP=200 TYPE=text/html; charset=utf-8 FINAL=https://repo-portal.ito.gov.ir/repo/library/Python/Others/
CURL_RC=0
TITLE=<title>مخزن ملی منابع متن باز

URL=https://repo.ito.gov.ir/
HTTP=200 TYPE=text/html; charset=utf-8 FINAL=https://repo.ito.gov.ir/
CURL_RC=0
TITLE=<title>مخزن ملی منابع متن باز



## اسکن ساختار HTML مخزن ملی
زمان ثبت: 2026-10-12T16:44:26+03:30


================ PORTAL ================
HTTP=200
FINAL_URL=https://repo-portal.ito.gov.ir/
CONTENT_TYPE=text/html; charset=utf-8
CURL_RC=0

TITLE: مخزن ملی منابع متن باز
HTML_BYTES: 31828
ANCHOR_COUNT: 43
FORM_COUNT: 1
FORM_1: action='/repo/v1/search' method=GET
  FIELD: {'tag': 'input', 'name': 'q', 'type': 'text', 'placeholder': 'نام بسته، سیستم عامل، نرم افزار ...', 'value': ''}
  FIELD: {'tag': 'button', 'name': '', 'type': 'submit', 'placeholder': '', 'value': ''}
ALL_SEARCH_RELATED_INPUTS:
  {'tag': 'input', 'name': 'q', 'type': 'text', 'placeholder': 'نام بسته، سیستم عامل، نرم افزار ...', 'value': ''}
RELEVANT_LINKS:
  مخزن ملی منابع متن باز | https://repo-portal.ito.gov.ir/
  درخواست بسته جدید | https://repo-portal.ito.gov.ir/new-package
  راهنما | https://repo-portal.ito.gov.ir/docs/guide/
  Ubuntu | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/ubuntu
  Python | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/python
  Fedora | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/fedora
  Flutter | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/flutter
  CentOS | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/centos
  Maven | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/maven
  Npm | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/npm
  Yarn | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/yarn
  Java | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/java
  Docker | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/docker
  شروع جستجو | https://repo-portal.ito.gov.ir/repo/
  ثبت درخواست | https://repo-portal.ito.gov.ir/new-package/
  دسترسی به مخزن | https://archive.ito.gov.ir/
  مشاهده راهنما | https://repo-portal.ito.gov.ir/#guide
  مشاهده راهنمای میرور اصلی | https://repo-portal.ito.gov.ir/docs/guide/main-mirror
  مشاهده راهنمای میرور ۲ | https://repo-portal.ito.gov.ir/docs/guide/mirror2
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/centos
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/fedora
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/rocky
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/opensuse
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/ubuntu
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/debian
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/python
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/npm
   | https://repo-portal.ito.gov.ir/docs/guide/main-mirror/yarn
  سامانه جستجوی بسته های متن باز | https://repo-portal.ito.gov.ir/
  مخزن ملی - سامانه جستجو | https://repo.ito.gov.ir/
  مخزن ملی - منابع | https://archive.ito.gov.ir/
  راهنمای استفاده از مخزن سامانه و ... | https://repo-portal.ito.gov.ir/#guide
SCRIPT_SOURCES:
  https://repo-portal.ito.gov.ir/assets/vendor/purecounter/purecounter.js
  https://repo-portal.ito.gov.ir/assets/vendor/aos/aos.js
  https://repo-portal.ito.gov.ir/assets/js/jquery-3.6.0.js
  https://repo-portal.ito.gov.ir/assets/vendor/bootstrap 5/js/bootstrap.bundle.min.js
  https://repo-portal.ito.gov.ir/assets/js/frontpage.3cc751d327.js
TARGET_PACKAGE_TEXT_HITS:
  peft: NOT_FOUND_IN_THIS_HTML
  transformers: NOT_FOUND_IN_THIS_HTML
  datasets: NOT_FOUND_IN_THIS_HTML
  accelerate: NOT_FOUND_IN_THIS_HTML
  hazm: NOT_FOUND_IN_THIS_HTML
  parsivar: NOT_FOUND_IN_THIS_HTML
  sentence-transformers: NOT_FOUND_IN_THIS_HTML
  sqlite-vec: NOT_FOUND_IN_THIS_HTML
  faster-whisper: NOT_FOUND_IN_THIS_HTML
  jiwer: NOT_FOUND_IN_THIS_HTML
  llama-cpp-python: NOT_FOUND_IN_THIS_HTML
  fastapi: NOT_FOUND_IN_THIS_HTML
  uvicorn: NOT_FOUND_IN_THIS_HTML
NOTE: NOT_FOUND_IN_THIS_HTML DOES NOT MEAN PACKAGE ABSENT.

================ REPO ================
HTTP=200
FINAL_URL=https://repo-portal.ito.gov.ir:443/repo/
CONTENT_TYPE=text/html; charset=utf-8
CURL_RC=0

TITLE: مخزن ملی منابع متن باز
HTML_BYTES: 1765234
ANCHOR_COUNT: 1181
FORM_COUNT: 1
FORM_1: action='/v1/search' method=GET
  FIELD: {'tag': 'input', 'name': '', 'type': '', 'placeholder': 'جستجو...', 'value': ''}
  FIELD: {'tag': 'button', 'name': '', 'type': 'submit', 'placeholder': '', 'value': ''}
ALL_SEARCH_RELATED_INPUTS:
  {'tag': 'input', 'name': '', 'type': '', 'placeholder': 'جستجو...', 'value': ''}
RELEVANT_LINKS:
  مخزن ملی منابع متن باز | https://repo-portal.ito.gov.ir/
  ubuntu | https://repo-portal.ito.gov.ir/repo
  centos | https://repo-portal.ito.gov.ir/repo
  debian | https://repo-portal.ito.gov.ir/repo
  debian-security | https://repo-portal.ito.gov.ir/repo
  fedora | https://repo-portal.ito.gov.ir/repo
  rocky | https://repo-portal.ito.gov.ir/repo
  بسته های مطرح | https://repo-portal.ito.gov.ir/repo
  docker | https://repo-portal.ito.gov.ir/repo
  docker-ce | https://repo-portal.ito.gov.ir/repo
  composer | https://repo-portal.ito.gov.ir/repo
  npm | https://repo-portal.ito.gov.ir/repo
  python | https://repo-portal.ito.gov.ir/repo
  gradle | https://repo-portal.ito.gov.ir/repo
  maven | https://repo-portal.ito.gov.ir/repo
  yarn | https://repo-portal.ito.gov.ir/repo
  راهنما | https://repo-portal.ito.gov.ir/#guide
  ubuntu | https://repo-portal.ito.gov.ir/repo#ubuntu
  نسخه Bionic-18.04 | https://repo-portal.ito.gov.ir/repo#ubuntu_Bionic-18-04_collapse
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Bionic-18.04/universe/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Bionic-18.04/restricted/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Bionic-18.04/multiverse/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Bionic-18.04/main/i386/
  نسخه Focal-20.04 | https://repo-portal.ito.gov.ir/repo#ubuntu_Focal-20-04_collapse
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Focal-20.04/restricted/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Focal-20.04/main/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Focal-20.04/universe/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Focal-20.04/multiverse/i386/
  نسخه Jammy-22.04 | https://repo-portal.ito.gov.ir/repo#ubuntu_Jammy-22-04_collapse
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Jammy-22.04/universe/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Jammy-22.04/main/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Jammy-22.04/multiverse/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Jammy-22.04/restricted/i386/
  نسخه Kinetic-22.10 | https://repo-portal.ito.gov.ir/repo#ubuntu_Kinetic-22-10_collapse
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/main/i386/
  all | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/main/all/
  amd64 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/main/amd64/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/multiverse/i386/
  all | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/multiverse/all/
  amd64 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/multiverse/amd64/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/restricted/i386/
  all | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/restricted/all/
  amd64 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/restricted/amd64/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/universe/i386/
  all | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/universe/all/
  amd64 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Kinetic-22.10/universe/amd64/
  نسخه Lunar-23.04 | https://repo-portal.ito.gov.ir/repo#ubuntu_Lunar-23-04_collapse
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Lunar-23.04/universe/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Lunar-23.04/multiverse/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Lunar-23.04/main/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Lunar-23.04/restricted/i386/
  نسخه Mantic-23.10 | https://repo-portal.ito.gov.ir/repo#ubuntu_Mantic-23-10_collapse
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Mantic-23.10/main/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Mantic-23.10/multiverse/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Mantic-23.10/universe/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Mantic-23.10/restricted/i386/
  نسخه Noble-24.04 | https://repo-portal.ito.gov.ir/repo#ubuntu_Noble-24-04_collapse
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/restricted/i386/
  all | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/restricted/all/
  amd64 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/restricted/amd64/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/multiverse/i386/
  all | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/multiverse/all/
  amd64 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/multiverse/amd64/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/main/i386/
  all | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/main/all/
  amd64 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/main/amd64/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/universe/i386/
  all | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/universe/all/
  amd64 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Noble-24.04/universe/amd64/
  نسخه Plucky-25.04 | https://repo-portal.ito.gov.ir/repo#ubuntu_Plucky-25-04_collapse
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Plucky-25.04/multiverse/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Plucky-25.04/main/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Plucky-25.04/restricted/i386/
  i386 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Plucky-25.04/universe/i386/
  نسخه Questing-25.10 | https://repo-portal.ito.gov.ir/repo#ubuntu_Questing-25-10_collapse
  amd64v3 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Questing-25.10/universe/amd64v3/
  amd64v3 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Questing-25.10/multiverse/amd64v3/
  amd64v3 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Questing-25.10/restricted/amd64v3/
  amd64v3 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Questing-25.10/main/amd64v3/
  نسخه Resolute-26.04 | https://repo-portal.ito.gov.ir/repo#ubuntu_Resolute-26-04_collapse
  amd64v3 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Resolute-26.04/multiverse/amd64v3/
  amd64v3 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Resolute-26.04/universe/amd64v3/
  amd64v3 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Resolute-26.04/restricted/amd64v3/
  amd64v3 | https://repo-portal.ito.gov.ir/repo/package/Ubuntu/Resolute-26.04/main/amd64v3/
  centos | https://repo-portal.ito.gov.ir/repo#centos
  نسخه 10-stream | https://repo-portal.ito.gov.ir/repo#centos_10-stream_collapse
  aarch64 | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/BaseOS/aarch64/
  noarch | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/BaseOS/noarch/
  aarch64 | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/AppStream/aarch64/
  noarch | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/AppStream/noarch/
  aarch64 | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/RT/aarch64/
  noarch | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/RT/noarch/
  aarch64 | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/CRB/aarch64/
  noarch | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/CRB/noarch/
  aarch64 | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/HighAvailability/aarch64/
  noarch | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/HighAvailability/noarch/
  noarch | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/NFV/noarch/
  x86_64 | https://repo-portal.ito.gov.ir/repo/package/Centos/10-stream/NFV/x86_64/
  نسخه 7 | https://repo-portal.ito.gov.ir/repo#centos_7_collapse
  noarch | https://repo-portal.ito.gov.ir/repo/package/Centos/7/dotnet/noarch/
  LINK_OUTPUT_LIMIT=100
SCRIPT_SOURCES:
  https://repo-portal.ito.gov.ir/assets/js/jquery-3.6.0.js
  https://repo-portal.ito.gov.ir/assets/vendor/bootstrap%204/js/bootstrap.bundle.js
  https://repo-portal.ito.gov.ir/assets/vendor/aos/aos.js
  https://repo-portal.ito.gov.ir/assets/vendor/swiper/swiper-bundle.min.js
  https://repo-portal.ito.gov.ir/assets/js/index.45dd0472c4.js
  https://repo-portal.ito.gov.ir/assets/js/search.8bd070c4a5.js
TARGET_PACKAGE_TEXT_HITS:
  peft: NOT_FOUND_IN_THIS_HTML
  transformers: NOT_FOUND_IN_THIS_HTML
  datasets: NOT_FOUND_IN_THIS_HTML
  accelerate: NOT_FOUND_IN_THIS_HTML
  hazm: NOT_FOUND_IN_THIS_HTML
  parsivar: NOT_FOUND_IN_THIS_HTML
  sentence-transformers: NOT_FOUND_IN_THIS_HTML
  sqlite-vec: NOT_FOUND_IN_THIS_HTML
  faster-whisper: NOT_FOUND_IN_THIS_HTML
  jiwer: NOT_FOUND_IN_THIS_HTML
  llama-cpp-python: NOT_FOUND_IN_THIS_HTML
  fastapi: PRESENT_IN_HTML
  uvicorn: NOT_FOUND_IN_THIS_HTML
NOTE: NOT_FOUND_IN_THIS_HTML DOES NOT MEAN PACKAGE ABSENT.

================ PYTHON ================
HTTP=200
FINAL_URL=https://repo-portal.ito.gov.ir/repo/library/Python/Others/
CONTENT_TYPE=text/html; charset=utf-8
CURL_RC=0

TITLE: مخزن ملی منابع متن باز
HTML_BYTES: 487325
ANCHOR_COUNT: 1598
FORM_COUNT: 1
FORM_1: action='/v1/search' method=GET
  FIELD: {'tag': 'input', 'name': '', 'type': '', 'placeholder': 'جستجو...', 'value': ''}
  FIELD: {'tag': 'button', 'name': '', 'type': 'submit', 'placeholder': '', 'value': ''}
ALL_SEARCH_RELATED_INPUTS:
  {'tag': 'input', 'name': '', 'type': '', 'placeholder': 'جستجو...', 'value': ''}
RELEVANT_LINKS:
  مخزن ملی منابع متن باز | https://repo-portal.ito.gov.ir/
  ubuntu | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  centos | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  debian | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  debian-security | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  fedora | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  rocky | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  بسته های مطرح | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  docker | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  docker-ce | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  composer | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  npm | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  python | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  gradle | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  maven | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  yarn | https://repo-portal.ito.gov.ir/repo/library/Python/Others/
  راهنما | https://repo-portal.ito.gov.ir/#guide
  Python | https://repo-portal.ito.gov.ir/repo
  bces-1.5.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/bces-1.5.1.html
  alibabacloud-ims20190815-2.0.7 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/alibabacloud-ims20190815-2.0.7.html
  alnvu-0.3.3 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/alnvu-0.3.3.html
  tf-estimator-nightly-2.9.0.dev2022033108 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/tf-estimator-nightly-2.9.0.dev2022033108.html
  e-socket-0.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/e-socket-0.2.html
  ECRScan-0.2.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/ECRScan-0.2.2.html
  cliglue-1.1.3 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/cliglue-1.1.3.html
  ai-artist-0.0.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/ai-artist-0.0.2.html
  ansibull-0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/ansibull-0.1.html
  django-serverless-emailer-0.3.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/django-serverless-emailer-0.3.0.html
  fedvision-deploy-toolkit-0.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/fedvision-deploy-toolkit-0.2.html
  fimport-0.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/fimport-0.2.html
  check-pypi-name-cli-0.3.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/check-pypi-name-cli-0.3.0.html
  adafruit-circuitpython-dash-display-1.1.9 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/adafruit-circuitpython-dash-display-1.1.9.html
  csvw-3.7.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/csvw-3.7.0.html
  bayse-summary-1.0.3 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/bayse-summary-1.0.3.html
  SALib-1.5.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/SALib-1.5.2.html
  openresponses-types-2.3.0.post1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/openresponses-types-2.3.0.post1.html
  cmstoolbox-0.9.9 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/cmstoolbox-0.9.9.html
  ancientfiles-0.2.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/ancientfiles-0.2.0.html
  dataclass-array-1.4.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/dataclass-array-1.4.1.html
  detective_nester-1.3.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/detective_nester-1.3.0.html
  types-aiobotocore-fsx-3.6.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/types-aiobotocore-fsx-3.6.0.html
  docopt-0.6.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/docopt-0.6.2.html
  desdeo-tools-1.8.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/desdeo-tools-1.8.0.html
  drf-chaos-0.1.3 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/drf-chaos-0.1.3.html
  codon-0.0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/codon-0.0.1.html
  django-impostor-0.1.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/django-impostor-0.1.0.html
  fbbot-1.0.10 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/fbbot-1.0.10.html
  ensauction-0.1.0b0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/ensauction-0.1.0b0.html
  bioplotz-0.1.0.dev3 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/bioplotz-0.1.0.dev3.html
  calfreeslots-1.0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/calfreeslots-1.0.1.html
  buildhat-0.5.9 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/buildhat-0.5.9.html
  django-compass-0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/django-compass-0.1.html
  crawlutils-1.5.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/crawlutils-1.5.0.html
  cspyclient-1.0.9 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/cspyclient-1.0.9.html
  faster-coco-eval-1.7.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/faster-coco-eval-1.7.2.html
  extract-tool-0.0.3 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/extract-tool-0.0.3.html
  docker-compose-swarm-mode-2.1.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/docker-compose-swarm-mode-2.1.0.html
  cleannaming-0.0.4 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/cleannaming-0.0.4.html
  antchain-donpa-1.0.4 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/antchain-donpa-1.0.4.html
  anoikis-0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/anoikis-0.1.html
  bullattack-0.8 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/bullattack-0.8.html
  beautifulsoupselect-0.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/beautifulsoupselect-0.2.html
  CheckRequest-0.0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/CheckRequest-0.0.1.html
  FadeMaxSize-1.0.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/FadeMaxSize-1.0.0.html
  copasi-basico-0.9 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/copasi-basico-0.9.html
  erc20-demurrage-token-0.5.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/erc20-demurrage-token-0.5.2.html
  django-roadmap-0.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/django-roadmap-0.2.html
  cognitiveatlas-0.1.9 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/cognitiveatlas-0.1.9.html
  nvidia-cutlass-dsl-libs-base-4.5.0.dev0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/nvidia-cutlass-dsl-libs-base-4.5.0.dev0.html
  openml-0.9.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/openml-0.9.0.html
  facef-0.1.5 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/facef-0.1.5.html
  allmychanges-0.9.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/allmychanges-0.9.0.html
  advanced-markdown-tools-0.1.8 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/advanced-markdown-tools-0.1.8.html
  backpack-0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/backpack-0.1.html
  dbxref-0.1.7 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/dbxref-0.1.7.html
  fisher-test-python-0.2.7 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/fisher-test-python-0.2.7.html
  BalancedDiscStorage-1.1.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/BalancedDiscStorage-1.1.0.html
  bowline-0.2.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/bowline-0.2.2.html
  colors-format-1.1.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/colors-format-1.1.2.html
  descriptastorus-2.6.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/descriptastorus-2.6.0.html
  django-database-functions-0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/django-database-functions-0.1.html
  brws-0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/brws-0.1.html
  conductor.core-0.1.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/conductor.core-0.1.2.html
  bottlenose-1.1.8 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/bottlenose-1.1.8.html
  distributions-cf-0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/distributions-cf-0.1.html
  algomodule-1.0.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/algomodule-1.0.2.html
  agile_item_master-2.post6 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/agile_item_master-2.post6.html
  albert-1.3.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/albert-1.3.1.html
  arvan-0.1.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/arvan-0.1.1.html
  ccdgen-0.0.5 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/ccdgen-0.0.5.html
  code-generation-2.3.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/code-generation-2.3.0.html
  clixdev-0.3.9.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/clixdev-0.3.9.1.html
  codebottle-0.0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/codebottle-0.0.1.html
  control-ldm-0.1.0 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/control-ldm-0.1.0.html
  django-data-exporter-0.2 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/django-data-exporter-0.2.html
  alibabacloud-green20180509-1.0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/alibabacloud-green20180509-1.0.1.html
  azureml-contrib-itp-0.0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/azureml-contrib-itp-0.0.1.html
  DAXFi-1.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/DAXFi-1.1.html
  focus-time-1.2.9 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/focus-time-1.2.9.html
  dfagent-0.1 | https://repo-portal.ito.gov.ir/repo/library/Python/Others/dfagent-0.1.html
  LINK_OUTPUT_LIMIT=100
SCRIPT_SOURCES:
  https://repo-portal.ito.gov.ir/assets/js/jquery-3.6.0.js
  https://repo-portal.ito.gov.ir/assets/vendor/bootstrap%204/js/bootstrap.bundle.js
  https://repo-portal.ito.gov.ir/assets/vendor/aos/aos.js
  https://repo-portal.ito.gov.ir/assets/vendor/swiper/swiper-bundle.min.js
  https://repo-portal.ito.gov.ir/assets/js/index.45dd0472c4.js
  https://repo-portal.ito.gov.ir/assets/js/search.8bd070c4a5.js
TARGET_PACKAGE_TEXT_HITS:
  peft: NOT_FOUND_IN_THIS_HTML
  transformers: NOT_FOUND_IN_THIS_HTML
  datasets: NOT_FOUND_IN_THIS_HTML
  accelerate: NOT_FOUND_IN_THIS_HTML
  hazm: NOT_FOUND_IN_THIS_HTML
  parsivar: NOT_FOUND_IN_THIS_HTML
  sentence-transformers: NOT_FOUND_IN_THIS_HTML
  sqlite-vec: NOT_FOUND_IN_THIS_HTML
  faster-whisper: NOT_FOUND_IN_THIS_HTML
  jiwer: NOT_FOUND_IN_THIS_HTML
  llama-cpp-python: NOT_FOUND_IN_THIS_HTML
  fastapi: NOT_FOUND_IN_THIS_HTML
  uvicorn: NOT_FOUND_IN_THIS_HTML
NOTE: NOT_FOUND_IN_THIS_HTML DOES NOT MEAN PACKAGE ABSENT.

END_OF_READ_ONLY_PAGE_INSPECTION


## بررسی جست‌وجوی زنده بسته‌های موردنیاز سیمرغ
زمان اجرا: 2026-10-12T17:31:17+03:30
مسیر جست‌وجوی انتخاب‌شده: /repo/v1/search

تفسیر وضعیت‌ها:
- CATALOG_MATCH: نام/نسخه در پیوند نتایج دیده شد؛ نصب با pip تأیید نشده.
- NO_MATCH_IN_RESULT_LINKS: در پیوندهای نتایج پیدا نشد؛ نبودن در کل مخزن اثبات نشده.
- UNKNOWN_REQUEST_FAILED: درخواست یا پاسخ HTTP قابل تأیید نبود.
- UNKNOWN_SEARCH_ROUTE: مسیر جست‌وجو از آزمایش پاسخ‌پذیری مشخص نشد.

- peft: CATALOG_MATCH; peft-0.9.0
- transformers: CATALOG_MATCH; transformers-0.0.2, transformers-3.1.0, @huggingface/transformers-4.1.0, @shikijs/transformers-4.0.2, @xenova/transformers-2.17.2
- datasets: CATALOG_MATCH; @stdlib/datasets-0.3.0, datasets-4.8.4
- accelerate: CATALOG_MATCH; accelerate-1.9.0
- hazm: NO_MATCH_IN_RESULT_LINKS
- parsivar: NO_MATCH_IN_RESULT_LINKS
- sentence-transformers: CATALOG_MATCH; sentence-transformers, sentence-transformers-5.4.1
- sqlite-vec: CATALOG_MATCH; sqlite-vec-0.1.9a1
- faster-whisper: CATALOG_MATCH; faster-whisper-0.5.1
- jiwer: CATALOG_MATCH; jiwer-4.0.0
- llama-cpp-python: CATALOG_MATCH; llama-cpp-python, llama-cpp-python-0.3.9
- fastapi: CATALOG_MATCH; FastAPI, fastapi, fastapi-0.99.1
- uvicorn: CATALOG_MATCH; uvicorn_0.17.6-1_all.deb, uvicorn_0.17.6-1_all.deb, uvicorn_0.17.6-1_all.deb, uvicorn_0.17.6-1_all.deb, uvicorn_0.17.6-1_all.deb


## بستهٔ ارزیابی WER سیمرغ: jiwer

- Purpose: measurement of speech-to-text word error rate (WER)
- Download source: https://pypi.org/simple
- National catalog entry: jiwer-4.0.0 was found; direct installation
  from the national portal has not yet been verified.
- Installation: NOT PERFORMED
- Artifact directory: /home/mahdi/simorgh/data/package_cache/jiwer-4.0.0
- Manifest: /home/mahdi/simorgh/data/package_cache/jiwer-4.0.0/MANIFEST.json
- Status: PYPI_HASHES_MATCHED
- Only wheel files were downloaded; no source distributions requested.
