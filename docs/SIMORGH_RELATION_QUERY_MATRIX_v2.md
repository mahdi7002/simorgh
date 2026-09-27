# SIMORGH Relation Query Matrix v2

اصل پایه: **نبود fact برابر با false نیست.**

| نوع | نمونه | انتظار |
|---|---|---|
| Generic parent lookup | `رستم فرزند چه کسی است؟` | `parent_of` + روابط خاص‌تر، بدون ارتقای خودکار |
| Specific father lookup | `چه کسی پدر رستم است؟` | فقط `father_of` صریح |
| Specific mother lookup | `چه کسی مادر رستم است؟` | فقط `mother_of` صریح |
| Subject parent lookup | `سام والد چه کسی است؟` | factهای `parent_of` مستقیم |
| Exact father | `سیمرغ پدر رستم است؟` | `TRUE/FALSE/UNKNOWN`, با positional parsing |
| Exact mother | `زال مادر رستم است؟` | `TRUE/FALSE/UNKNOWN` |
| Exact son | `سیمرغ پسر زال است؟` | `son_of`; `parent_of` به‌تنهایی کافی نیست |
| Event | `سیمرغ به چه کسی کمک کرد؟` | candidate/evidence review، نه fact خودکار |
| Audit | همه DBها | scan تمام DB/table/row/text-cell با provenance |

## States

- `TRUE`: شاهد ASSERTED برای همان رابطه وجود دارد.
- `FALSE`: شاهد NEGATED برای همان رابطه وجود دارد.
- `UNKNOWN`: شاهد کافی پیدا نشده است.
- `CONFLICT`: برای همان triple هم ASSERTED و هم NEGATED ثبت شده است.

## معماری

`USER → Persian Parser → Structured Relation Query → Fact Store → Provenance`

و مسیر مستقل:

`USER → Retrieval → Evidence → LLM synthesis (only when necessary)`
