# PITFALLS.md — Dead-End Trail Log (append-only · git)

> CODE မရေးခင် ဒီ file ကို မဖြစ်မနေ grep/search လုပ်။
> ပုံစံ: ❌စမ်း→ကျ / ❌စမ်း→ကျ / ✅ဖြစ်→ဘာလို့
> ❌ trail ကို ဘယ်တော့မှ မဖျက် — dead end က feature (နောက်ထပ် မစမ်းမိအောင်)

---

## [2026-07-18] Memory tool hard cap 2200 chars
**SIG:** save/update rejected "over the limit" မျိုး
**❌** စာရှည်တဲ့ entry တိုအောင်ချုံ့ပြီး ထပ်ထည့်ဖို့ ကြိုးစား → ပြည့်နေ
**❌** batch ထဲ တစ်ခု fail → အားလုံး မလုပ် (all-or-nothing)
**✅** lesson/မှား အားလုံးကို MEMORY_LESSONS.md (char limit မရှိ) သို့ ပြောင်း။ memory tool = core rule ၁၃ ခု ပဲ
**why:** flat list + cap မို့ growing log ထည့်လို့ မရ

## [2026-07-18] providers.py import path in study_journal/
**SIG:** AttributeError: module 'providers' has no attribute 'chat'
**❌** sys.path.insert(0, ".") → study_journal/ ကို ညွှန်း, providers.py မေတ္ခင် (scripts/ ထဲမှာ)
**✅** sys.path.insert(0, dirname(__file__) + "/..") → scripts/ ကို ညွှန်
**why:** script ဘယ်ကနေ run လုပ်လုပ် မှန်အောင် relative to __file__

## [2026-07-18] .env location
**SIG:** FileNotFoundError: '.env'
**❌** open(".env") from scripts/ → မရှိ
**✅** .env က hermes/ ROOT မှာ (scripts/ အောက် မဟုတ်) → absolute "C:/Users/user/AppData/Local/hermes"
**why:** config key တွေ hermes root မှာ ရှိ

## [2026-07-18] DB path confusion
**SIG:** sqlite3.OperationalError: unable to open database file
**❌** DB = HERMES + "/study_journal/rag.db" (HERMES=hermes root → path မှား)
**✅** DB = dirname(__file__) + "/rag.db" (script နဲ့ တွဲ)
**why:** local data file = __file__ relative; root config = absolute

## [2026-07-18] providers.chat prefer= invalid ignored
**SIG:** fallback test false-negative (prefer="__nonexistent__" ထားလည်း default သုံး)
**❌** assert r["ok"] is False → openrouter ပြန်လို့ PASS မဖြစ်
**✅** monkeypatch providers.chat = _boom (တကယ် exception) သုံးပြီး စမ်း
**why:** providers.chat က invalid prefer ကို ignore လုပ်

## [2026-07-18] python.exe alias (Windows Store stub)
**SIG:** Permission denied: /c/Program Files/WindowsApps/.../python.exe
**❌** terminal ထဲ `python.exe` သုံး
**✅** C:/Users/user/AppData/Local/Programs/Python/Python310/python.exe သုံး
**why:** alias က Store stub ကို ညွှန်

## [2026-07-18] ROLE §2 primary provider ↔ .env key ကွဲ
**SIG:** §2 "nous=primary" ရေး, NOUS_API_KEY .env မှာ မရှိ
**❌** nous primary အတိုင်းထား → ကျ: runtime က ကျော်, doc လိမ်
**❌** openrouter=primary ချက်ချင်းရေး → ကျ: groq key ရှိတာ မေ့, groq က chain ၂ ဖိုင်မြောက်
**✅** audit run → groq status သိ → တကယ့် primary ရေး → doc = observed reality
**guard:** ROLE မှာ provider ရေးရင် (1) .env key grep (2) audit status စစ်မှ ရေး
**tags:** #providers #role #drift #env

---

<!-- နောက် dead-end တွေ အောက်မှာ append: ❌❌✅ တစ်ခါတည်း -->

## [2026-07-18] groq key dead (403) but listed in chain
**SIG:** providers.py chain မှာ groq ပါ, .env GROQ_API_KEY SET (len 56) ဒါပေမယ့် audit=403 bad key
**❌** "groq(?)" လို့ သံသယနဲ့ ထား → ငတ်, reality=dead
**✅** audit status ကို final ယူ → "dead (key bad): groq" ရေး
**guard:** provider chain ထဲ key SET ဆိုတာ OK မဟုတ် — audit live status ကို source of truth ထား
tags: #providers #groq #audit

## SIG: study bot HTTP 409 Conflict — polling same bot
**component:** telegram_bot.py / .env
**symptom:** [study_bot] 409 Conflict, another process polling same token

**❌** စမ်း: TELEGRAM_TOKEN → TELEGRAM_BOT_TOKEN ဖတ်အောင် code ပြင်
     → ကျ: var မှန်ပေမဲ့ 409 ဆက်ဖြစ် (value က မှား, var မဟုတ်)
**❌** စမ်း: external ကောက် (webhook/cloud/BotFather double-register)
     → ကျ: external မဟုတ်, အချိန်ကုန်
**✅** ဖြစ်: .env ထဲ TELEGRAM_BOT_TOKEN value = token မှားနေတာ
     တွေ့ → @kkk4study_bot token မှန် ထည့် → ၂ bot ကွဲ, 409 ပျောက်
     → ဘာလို့: token VALUE ၂ ခု တူ → တူတဲ့ bot ကို ၂ ခု poll

**guard:** 409 တွေ့ရင် external မ ကောက်ခင် — getMe နဲ့ token ၂ ခုရဲ့ bot id/username တူမတူ အရင် စစ် (var name မှန်ရုံ မ လုံလောက်, value စစ်)
**tags:** #telegram #409 #env #token #misdiagnosis

---
## [2026-07-18] Groq 403 -> fixed (key value error, not dead)
**SIG:** audit=403 bad key, format gsk_ but invalid
**❌** "dead" လို့ ထား → မှား, key value မှား (telegram token pattern)
**✅** Kyaw console မဖွင့်နိုင် -> new key ပေး -> live curl test PASS -> .env update
**✅** primary = groq (llama-3.3-70b, fastest) -> openrouter 429 load relief
**guard:** 403/401 = key VALUE error, fixable. Dont mark dead. Verify with live curl before conclusion.
tags: #providers #groq #key #resolved

## [2026-07-18] Gemini vision LIVE test PASS (model name gotcha)
**SIG:** offline audit cant test vision; key SET but unverified
**✅** live call image -> gemini-flash-latest -> "red" correct
**❌** gemini-1.5-flash -> 404 (not in v1beta)
**❌** gemini-2.0-flash -> 429 quota (use gemini-flash-latest instead)
**guard:** vision key SET != live OK. Always live-test with real image. Model name matters.
tags: #gemini #vision #verified
