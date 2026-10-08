# Roadmap to the national-conference deadline / نقشهٔ راه تا مهلت همایش ملی

Updated 2026-10-07 (15 Mehr 1405) · Deadline: **30 Dey 1405 = 20 Jan 2027** (≈ 15 weeks) · Optional: AbjadNLP, paper deadline **15 Dec 2026**, decide by **26 Oct** (4 Aban)

## 1. Where things stand / وضعیت فعلی
| Item / مورد | Status / وضعیت |
|---|---|
| Evaluation harness, held-out evidence, defect found and fixed / ارزیابی و شواهد مستقل | ✅ done, in `main` |
| Persian abstract + full paper draft / چکیده و پیش‌نویس کامل فارسی | ✅ draft; **citations, venue template, author block open** |
| English technical draft (AbjadNLP) / پیش‌نویس فنی انگلیسی | 🟡 structure only; **no citations** |
| EarthOS unified copy, 28 tests, waste pilot, bilingual `/pilot` dashboard / نسخهٔ یکپارچه، پایلوت، داشبورد دوزبانه | ✅ software; ❌ **no real bin has reported yet** |
| Municipality letter (annex from tests) / نامهٔ شهرداری | ✅ draft; placeholders `[ ]` open |

## 2. Plan / برنامه
| When / زمان | Do / کار | Done when / ملاک پایان |
|---|---|---|
| By 31 Oct (۹ آبان) | **One real bin**: build the ESP32 reporter, calibrate, leave it running 72 h | 72 h of readings visible at `/pilot` (history chart) |
| By 26 Oct (۴ آبان) | **Decide** AbjadNLP yes/no | one-line answer |
| Oct–mid Nov | Persian paper: fill citations, apply the venue template, add author block; read it aloud once | no `[ارجاع]` left, template applied |
| Nov | Municipality: send the letter with a 5-minute demo (live `/pilot` + alerts) | meeting date set |
| 15 Nov – 15 Dec (only if AbjadNLP = yes) | English paper: related work (**real, read** sources), anonymise repo, submit | submitted by 12 Dec |
| 15 Dec – 10 Jan | Persian paper final edit; re-run `python eval/finalize_evidence.py`, update numbers if code changed | numbers match `docs/evidence` |
| **By 14 Jan (۲۴ دی)** | **Submit the national paper** (6 days before the deadline) | submission receipt |

## 3. Freeze until after submission / فریز تا بعد از ارسال
Persona-prompt rewrites, per-persona memory, sqlite-vec, Mother merge, Hodhod rebrand, coding agent, new EarthOS modules beyond waste, typo-robust matching (report it as a limitation). Each of these is real work and none changes what the papers can claim.

## 4. Proposals / پیشنهادها
1. **Backups.** Everything lives on one desktop (7.7 GB RAM, unstable tether). Weekly copy of `~/simorgh`, `~/EarthOS-unified` (**exclude `.env`**) and `~/Desktop/fa-eval` to an external disk; keep the poetry DB hash in `docs/evidence`.
2. **One demo scenario, offline, 5 minutes** (for exhibitions and the municipality): greeting → "who wrote this verse?" → Quran search → honest "I don't know" → `/pilot` with live bin data. Record a backup video.
3. **Real-world test set.** The next strongest improvement to the paper is a small set of verse queries typed by *other people* (30–50), not derived from the database. It tests the thing the current evaluation cannot.
4. **After 20 Jan**, in this order: typo-robust matching with before/after numbers → persona prompts (charter) → Mother observing the repos → Hodhod.
5. **Clean public copy of EarthOS** (fresh `git init`, no history, rotated keys) only when the municipality asks for code.
