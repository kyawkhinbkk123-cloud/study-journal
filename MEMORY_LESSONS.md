# MEMORY_LESSONS.md

> Hermes agent ရဲ့ **သင်ခန်းစာ log** — မှားတာ / ပြင်ချက် / guard တွေကို append-only စနစ်နဲ့ သိမ်းတယ်။
> နေရာ (Windows): `C:/Users/user/AppData/Local/hermes/scripts/MEMORY_LESSONS.md`

---

## ဒီ file ရဲ့ စည်းမျဉ်း

1. **Append-only** — အဟောင်း entry ကို ဖျက်/ပြင် မလုပ်ဘူး၊ အောက်ဆုံးမှာ အသစ်ထပ်ရုံ။ (မှားခဲ့တာ ကိုယ်တိုင်က record — ဖျက်ရင် သင်ခန်းစာ ပျောက်တယ်)
2. **Main system မထိဘူး** — venv / agents core / study.db ကို မထိလို့ **approval မလို**၊ တိုက်ရိုက် append လုပ်နိုင်တယ်။
3. **Char limit မရှိ** — memory tool (2,200 cap) မဟုတ်။ ရှည်သလောက် ရေးလို့ရ။
4. **Git-tracked** — `git add MEMORY_LESSONS.md` → version history ရ။
5. **Greppable** — `grep -i "memory"` / `grep "#tooling"` နဲ့ ရှာ။

## ဘာက ဘယ်မှာ သွားလဲ (memory routing)

| အမျိုးအစား | နေရာ | ဘာလို့ |
|---|---|---|
| Core rules (၆ လကြာ တူတူ) | **memory tool** (~၁၃ entry) | stable, context တိုင်း လိုတယ် |
| မှားတာ / lesson / guard | **ဒီ file** | ကြီးထွားတယ်, char limit မရှိ |
| Study note | **study.db** | ရှိပြီးသား |
| EA param / version / config | **repo / commit** | မြန်မြန်ပြောင်း, memory ကုန်စေတယ် |

**စည်းမျဉ်း:** memory tool ထဲ မထည့်ခင် မေး — *"ဒါ ၆ လကြာရင် တူတူပဲလား?"* ဟုတ် → memory။ မဟုတ် → ဒီ file။

---

## Append format (နောက်ထပ် မှားတိုင်း ဒီ template ကူး)

```
## [YYYY-MM-DD] ခေါင်းစဉ် တို
**ကြုံတာ:**   ဘာ error / ဘာ ပြဿနာ
**Root cause:** တကယ့် အကြောင်းရင်း (surface မဟုတ်)
**ပြင်ချက်:**   ဘယ်လို ဖြေရှင်းလိုက်လဲ
**Guard:**     နောက် မဖြစ်အောင် ဘာ ထည့်/ပြောင်းလဲ
**Tags:**      #tooling #memory ...
```

---

# LESSONS

## [2026-07-18] Memory tool ရဲ့ အားနည်းချက် ၅ ချက်

**ကြုံတာ:**
memory အသုံးပြုရင်း error အများကြီး တက်တယ် —
1. Hard cap **2,200 chars** — စာရှည်ရင် save မရ
2. **Flat list** — category မခွဲရ၊ နေရာ မြန်မြန်ကုန်
3. **All-or-nothing batch** — batch ထဲ တစ်ခု fail ရင် အားလုံး မလုပ်
4. **Replace = exact old_text match** — ၁ စာလုံးမှားရင် fail
5. **Field ရှုပ်** — `replace=content`, `add=new_text` ရောနှော

**Root cause:**
memory tool က *"အရာအားလုံး တစ်နေရာတည်း"* design ဖြစ်တယ်။ stable rule နဲ့ growing lesson ကို မခွဲထားလို့ cap မြန်မြန်ပြည့်ပြီး edit လုပ်ရ ခက်တယ်။

**ပြင်ချက် (ဒီနေ့ ဆုံးဖြတ်):**
memory tool ကို **ပြန်မဆောက်ဘူး** — ဘေးမှာ append-only file (ဒီ file) ထားတယ်။
- memory tool ← core rule **~၁၃ ခု** ပဲ (stable)
- ဒီ file ← lesson / မှား / guard အားလုံး (char limit မရှိ)
- ဒါက "learning off main system" rule နဲ့ ကိုက် → approval မလို

**Guard:**
- memory ထဲ ထည့်ခင် *"၆ လကြာ တူတူပဲလား?"* test လုပ်
- lesson ဆို ချက်ချင်း ဒီ file ထဲ append (memory tool ထဲ မထည့်)
- version / param / config ← memory မထား၊ commit ထဲ ထား

**Tags:** #tooling #memory #architecture

---

### နောက်ဆက်တွဲ — Ideal memory design (တစ်နေ့ ပြန်ဆောက်ရင်)

ဒီ ၇ ချက်က ဒီနေ့ error တွေက ဆွဲထုတ်ထားတာ။ **1+2+4+7 က core** (ဒီနေ့ error အားလုံး ဖြေ) —

1. **Namespace store** — `user.json` / `rules.json` / `lessons.json` / `skills.json` သီးခြား။ တစ်ခု ပြည့်လည်း တခြားဟာ မပျက်
2. **Entry ID** — `update(id, text)` ရိုးရှင်း, exact-match မလို
3. ~~LLM auto-compact~~ **← မလုပ်ရ။** LLM နဲ့ တိတ်တဆိတ် ချုံ့ရင် guard/rule ပျောက်နိုင်တယ် → capital-preservation rule ပျောက်ရင် ငွေဆုံး။ survivability philosophy နဲ့ တိုက်ရိုက် တိုက်တယ်။
   **အစား:** limit ကို 10,000+ တိုး။ ချုံ့ဖို့ လိုရင် explicit + diff ပြ + approval မှ။ **rules ကို ဘယ်တော့မှ auto မချုံ့ရ။**
4. **Partial apply** — validate-all-then-apply: load → memory ထဲ apply → schema check → `os.replace()` atomic write။ တစ်ခု fail ရင် disk မထိရသေးဘူး (1+2 ရှိရင် အလကားရ)
5. **Char budget ပြ** — `remaining: X/limit` တိုင်း ပြ
6. **Field တစ်မျိုးတည်း** — အားလုံး `text` (`content`/`new_text` မရော)
7. **Search** — `memory.search("provider")` → JSON structured field scan (flat grep အစား)

**မှတ်ချက်:** #3 က တခြား ၆ ခုနဲ့ မတူ — ဒါ safety decision။ ကျန် ၆ ခုက convenience။

**Tags:** #tooling #memory #design #safety

---

<!-- နောက်ထပ် lesson တွေ အောက်မှာ append -->
