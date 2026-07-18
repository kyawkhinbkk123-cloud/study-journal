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

## [2026-07-18] Gemini 3.1 model name
**SIG:** "3.1 lite" -> gemini-3.1-lite 404
**✅** gemini-3.1-flash-lite vision PASS (red correct)
**note:** gemini-flash-latest ALSO works; gemini-2.0-flash 429 quota
**guard:** dont guess gemini model name; live-test. 3.1-lite != 3.1-flash-lite

## [2026-07-18] study bot push sets processed=1 (BUG)
**SIG:** image ပို့ -> study_inbox id8 processed=1 -> study.py WHERE processed=0 က မယူ
**❌** telegram_bot.py push() မှာ processed=1 ထား -> study.py မဖတ်နိုင်
**✅** test: processed=0 reset -> study.py run -> note PASS (gemini vision ok)
**guard:** inbox push = processed=0 သာ။ processed=1 ကို study.py run မှ ထား
**tags:** #studybot #inbox #bug #vision

## [2026-07-18] study inbox flow = CORRECT (false alarm resolved)
**SIG:** image id8 processed=1 -> study.py WHERE processed=0 မယူ
**❌** ထင်တာ: telegram_bot push က processed=1 ထား (BUG)
**✅** တကယ်: schema DEFAULT 0, push 0 ထား။ id8=1 က အရင် run_session က process လုပ်ပြီး
**✅** test: processed=0 reset -> study.py -> note PASS (real flow works)
**guard:** bug မစွပ်စွဲခင် -> INSERT default + ဘယ် run က process လုပ်လဲ trace လုပ်
**tags:** #studybot #inbox #false-alarm #verified

## [2026-07-18] Windows Python urllib -> groq 401/403 (use curl)
**SIG:** providers._post urllib -> groq 403/401, but curl subprocess PASS (same key)
**❌** urllib.request on Windows fails groq TLS/header (401 even with UA+Accept)
**✅** _post -> curl subprocess -> groq OK (primary works)
**guard:** Windows provider HTTP = use curl subprocess, not urllib. urllib unreliable for groq.
**tags:** #providers #groq #windows #urllib #curl

## [2026-07-18] Sandbox breach: study code imports providers (curl tunnel)
**SIG:** verify.py blocked subprocess/os.system but NOT local infra import
**❌** study code `import providers` -> providers._post -> curl subprocess (key leak)
**✅** BLOCKED_MODULES added: providers/telegram_bot/study/verify/sync_role/__audit/config
**guard:** study sandbox must block infra module imports, not just subprocess keyword
**tags:** #sandbox #verify #security #tunnel

## [2026-07-18] code_study shallow-note blind spot (source-count)
**SIG:** overnight 6/6 pass, but #1/#5 README-only repo -> shallow note, garbage-check pass
**❌** _is_garbage binary (len/repetitive/chunk) -> "shallow but well-formed" မ ဖမ်း
**✅** fix later: code_study list_sources len<2 -> "shallow" flag; audit note-quality tier (rich/ok/shallow)
**guard:** format-ok != content-rich. README-only repo = shallow by definition. Count sources.
tags: #code_study #quality #blindspot #shallow

## [2026-07-18] sandbox scan != runtime check (Day 33 bug)
**SIG:** day-33.py cosine nb=sum(x*y for x in b) NameError -> run fail, scan pass
**❌** verify.py scan = syntax/import/keyword only, runtime NameError မ ဖမ်း
**✅** fix: study code run မစခင် py_compile လုပ် (Day 34 ကစလုပ်)
**guard:** sandbox pass != run pass. Always py_compile before execute.
tags: #sandbox #verify #runtime #pitfall

## [2026-07-18] py_compile != NameError catch (REVISED)
**SIG:** Day34 "py_compile before run" = incomplete. py_compile=syntax only, NameError=runtime.
**❌** py_compile alone က undefined name (y not defined) မ ဖမ်း -> Day33 bug ပြန်ဖြစ်နိုင်
**✅** verify.py _pyflakes_check added: catches "undefined name: y" (Day33 pattern confirmed)
**guard:** sandbox = BLOCKED_MODULES + py_compile + pyflakes lint. py_compile single != safe.
tags: #sandbox #verify #pyflakes #runtime #pitfall

## [2026-07-19] tool ထဲ eval() = sandbox risk
**SIG:** day-36 tool_calc eval(expr) -> verify.py block (providers/eval)
**❌** eval() = arbitrary code exec, agent tool ထဲ မသုံးရ
**✅** safe parser (re.fullmatch numeric only) သုံး, ဒါမှမဟုတ် ast.literal_eval
**guard:** agent tool ရေးတိုင်း eval/exec မ ပါအောင် scan
**tags:** #agent #sandbox #eval #pitfall

## [2026-07-19] curl -K secret hygiene; Windows chmod no-op
**SIG:** providers._post argv ထဲ Bearer key -> tasklist/Process Explorer မြင် -> -K config file
**✅** fix: temp .curl config (header=), 0600, finally unlink, curl -K
**⚠️ Windows os.chmod(0o600) = no-op (POSIX perm မ honor) -> real guard = user 
## [2026-07-19] sandbox network-block vs embed/agent study (core tension)
**SIG:** verify.py danger-scan blocks subprocess/tempfile -> day-44 (curl embed) BLOCKED in auto-pipeline (study.py inbox), only manual-run works.
**root:** network embed/agent study needs curl, but sandbox blocks network -> blind spot: real embed code never auto-runs.
**options (pre-Day46):**
  (a) network whitelist (provider domain only) -> sandbox 2-tier
  (b) embed/agent code = manual review, sandbox skip
  (c) accept embed study = manual-run only, not in auto-pipeline
**guard:** Day 46 (research agent) needs web = tension returns. Decide (a/b/c) before Day 46. verify.py edit = main system = approval.
**tags:** #verify #sandbox #network #tension #pitfall
