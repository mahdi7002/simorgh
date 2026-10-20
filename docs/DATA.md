# داده‌ها: کد در گیت، پایگاه‌های بزرگ در Release

| فایل | کجا | چگونه به‌روز می‌شود |
|------|-----|---------------------|
| `data/grid/quran.db` | در همین مخزن | با pull request |
| `data/simorgh_full.db` (حدود ۳۹۲MB) | Release با برچسب `data` | فایل در Release جای‌گزین می‌شود و `MANIFEST.json` آخر منتشر می‌شود |

## دریافت

```bash
bash scripts/fetch_data.sh
```

این دستور فایل فشرده را با ادامه‌ی دانلود می‌گیرد و پیش و پس از بازکردن، SHA-256 را با `MANIFEST.json` می‌سنجد. اگر فایل کامل و درست باشد، دوباره دانلود نمی‌شود.

اگر `files.pythonhosted.org` بسته است، نصب وابستگی‌ها را با آینه‌ی PyPI انجام دهید (QUICKSTART.md).

## نسخه‌ی LFS

فایل `data/simorgh_full.db` هنوز به‌صورت اشاره‌گر LFS در مخزن هست و به‌روز نمی‌شود، چون CI و ساخت AppImage به آن وابسته‌اند. برای آخرین نسخه از `fetch_data.sh` استفاده کنید.

## مجوز

نرم‌افزار سیمرغ با مجوز MIT است؛ داده‌ها مجوز جدا دارند. ترجمه‌ی فارسی قرآن (Ansarian، از Tanzil) فقط برای استفاده‌ی غیرتجاری است. جزئیات: `docs/ASSET_PROVENANCE.md` و `docs/TANZIL_FA_ANSARIAN.md`.
