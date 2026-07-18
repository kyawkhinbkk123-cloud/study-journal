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

## [2026-07-18] study bot 409 Conflict (external, NOT code)
**SIG:** telegram_bot.py fix (TELEGRAM_BOT_TOKEN) ပြီးသော်လည်း 409 Conflict ပြန်၊ bot stop
**❌** code fix မှန် (TELEGRAM_BOT_TOKEN != gateway TELEGRAM_TOKEN) ဒါပေမယ့် 409 မပျောက်
**❌** cron jobs grep → study.py/forex/daily (bot ကို cron မစတဘူး)
**✅** root = EXTERNAL: @kkk4study_bot (824051) ကို တခြား instance poll လုပ်နေ (cloud/hermes profile/botfather double-reg/webhook)
**why:** code မှန်ပေမယ့် token ကို နှစ်ခု ပြိုင် poll → 409 (Telegram 1 bot=1 poll only)
**guard:** 409 = external conflict, code fix နဲ့ မပျောက်။ Kyaw က cloud/account စစ်ရမယ်။
tags: #telegram #409 #external #studybot
