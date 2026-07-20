# PITFALLS.md — Dead-End Trail Log (append-only · git)

> CODE မရေးခင် ဒီ file ကို မဖြစ်မနေ grep/search လုပ်။
> ပုံစံ: ❌စမ်း→ကျ / ❌စမ်း→ကျ / ✅ဖြစ်→ဘာလို့
> ❌ trail ကို ဘယ်တော့မှ မဖျက် — dead end က feature (နောက်ထပ် မစမ်းမိအောင်)

---

## [2026-07-19] study scripts exit code ≠ success (verify *_notes.json, not exit code)
**SIG:** background job exit 0 (or -1=4294967295) but no useful work done
**❌** (a) trust the cron `exit 0 = done` assumption → silent no-op days; (b) check `study_notes` table to verify forex/code done — WRONG store (that's the ML/agent curriculum)
**✅** study scripts write to JSON, NOT study.db: `forex_study.py`→**forex_notes.json**, `code_study.py`→**code_notes.json**. Verify: (a) grep log for `all providers unavailable`/`flagged garbage` = fail; (b) load the JSON, check each entry: `note` length >0 AND `quality != "garbage"`. A `ts` from tonight is NOT proof of success — garbage entries also get stamped. Only run when a text provider is free.
**why:** all-providers-down is reachable (groq/openrouter cooldown + mistral daily cap 120 + gemini vision-only + nous/cerebras/deepseek no key). Scripts exit 0 or -1 regardless and still write `quality:garbage` placeholders with empty `note`.
**also seen:** exit `-1` (killed mid-backoff) ALSO yields 0 real notes — same trap, don't trust ANY exit code. `openrouter` key flipped to "no key" between runs (was key=True) → check .env if persists; groq went cooldown→RuntimeError (rate-limited).
**verified success example:** 2026-07-19 forex run → 8 entries in forex_notes.json, note lengths 333–883, quality ok, timestamps 22:47–23:25.
**verified FAIL example:** 2026-07-19 code_study run (after sleep 100 cooldown) → 6 entries all `quality:garbage`, empty `note`, exit 0. Same provider-down.

## [2026-07-20] cooldown-gate race: shared provider_state.json + overlapping study procs
**SIG:** wrapper waited for `provider_state.json` `cooldown_until`≤now, then launched code_study → but code_study STILL saw `groq cooldown 194s` and wrote all-garbage
**❌** assume a pre-launch `cooldown_until` check is enough — a concurrent study process re-extends `cooldown_until` on the SHARED json at the exact moment the new run starts, poisoning its gate
**✅** BEFORE launching any study run: (1) kill ALL other study procs (`tasklist`/`wmic` for `forex_study.py`/`code_study.py` — they linger as orphans even after "exit 0" reported); (2) then wait for cooldown; (3) re-check state IMMEDIATELY before subprocess.run, not 20-1500s earlier. Only one study process may touch provider_state.json at a time.
**why:** `providers.py` persists cooldown to one shared `provider_state.json` (`_STATE_FILE = _DIR/"provider_state.json"`). forex_study.py (PID 5288) was still alive at 00:09 after its "exit 0", thrashing the state while code_study started → race. Wrapper's pre-check is defeated by a concurrent writer.
**also:** midnight resets daily cap (`day` flips 2026-07-19→2026-07-20, `calls`→0) — mistral gets fresh 120 quota then, but is cooldown-locked ~3min from the thrash. After kill + cooldown, mistral is the clean free path.

## [2026-07-20] study script orphan processes survive "exit 0"
**SIG:** `forex_study.py` reported "completed normally (exit code 0)" yet a python.exe running `forex_study.py` (PID 5288) was STILL ALIVE 30+ min later, thrashing provider_state.json
**❌** trust the background-process "completed" event = process really gone — the launcher/shell may detach while the child keeps running (MT5/long-poll style)
**✅** after any study run, `tasklist | wmic` for the script name; if still present, `taskkill /F /PID` it before the next run. Overlapping study procs corrupt shared cooldown state (see above).
**why:** multiple "exit 0" study runs stacked without cleanup → 12+ python procs, shared state thrash, every later run starved.

---
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

## [2026-07-19] verify 2-tier RESOLVED (host-literal+query-dynamic)
**fixed:** subprocess/socket unblock, network allowlist (7 domains), dynamic HOST block (var/f-string host -> block), host-literal+query-dynamic ALLOW, os.remove unblock (tempfile cleanup safe).
**resolved:** day-44 (gemini embed) = CLEAN (auto-pipeline run OK). agent (wikipedia search, query-dynamic) = CLEAN.
**rule:** host MUST be literal+allowlist. query/path (?q={x}) = OK. full-host var (f"https://{h}") = BLOCK.
**partial:** static scan က runtime redirect / DNS-rebind မ ဖမ်း. real fix = OS network restrict (proxy/firewall) - solo laptop မှာ overkill. study code=self-authored (low threat) -> (A) လုံလောက်.
**tags:** #verify #sandbox #network #resolved #pitfall

## [2026-07-19] gap #1 RESOLVED: chat_json key-normalize
**root (verified via raw LLM output):** LLM returns JSON with capital keys {'Topic':...} -> chat_json json.loads SUCCESS but keys NOT lowercased -> study._ask returns {Topic:...} -> topic='' empty.
**NOT** (ii) LLM empty / (iii) truncate — LLM output was correct, parse layer dropped it.
**fix:** chat_json normalizes out = {k.lower(): v} after parse (covers both json + ast.literal_eval paths).
**verify:** inbox 14 (day-46) -> run_session -> note id80 (topic+352char note, processed=1). M11 fully wired.
**lesson:** Day 33 class — dont assume, print raw LLM before diagnosing. (i) parse-layer bug, not LLM bug.
**tags:** #study #autopipeline #gap #resolved #pitfall

## [2026-07-19] stale gaps #3/#4 RESOLVED (fact-checked)
**#3 Forex/Coding cron provider error:** ran both (fee997c7e38a, dccb013e7670) -> execution_success=True. prior error was groq403/openrouter404 (fixed 07-18). NOT stale anymore.
**#4 fastapi venv broken:** hermes-agent/venv python import fastapi OK (0.139.2). __audit.py references venv path (not import). Day27 pydantic_core issue -> substituted stdlib, fastapi not used in main. FALSE ALARM.
**lesson:** stale gaps from old context (07-17) auto-resolved by later fixes. Don't carry forward without re-verify.
**tags:** #gap #resolved #cron #fastapi #pitfall

## [2026-07-19] META-LESSON: gap စွပ်ခင် re-verify (false-alarm ၄ ခု pattern)
**pattern:** session ဒီတစ်ခုလုံး false-alarm ၄ ခု:
  1. gap#1 checkpoint (study.py processed flag ရှိပြီး -> false alarm)
  2. gap#2 pyflakes (verify_code ထဲ ရှိပြီး -> false alarm)
  3. stale#3 cron provider error (07-18 fix နောက် auto-resolved -> false alarm)
  4. stale#4 fastapi venv (import OK -> false alarm)
**real gap:** ၂ ခု ပဲ (argv secret, network tension)။
**root:** old context carry-forward -> "gap" ထင်, code/state re-verify မ လုပ်။
**rule:** gap claim မလုပ်ခင် (1) grep code (2) run/ps/sqlite check -> confirm မှ claim။ Day33 lesson ပဲ (print raw before diagnose)။
**tags:** #meta #false-alarm #verify #pitfall

## [2026-07-19] META-LESSON: quantified != correct (criteria validate)
**pattern:** Day 50 trivial-skip = MEASURED 1756->1159 (<1500 OK) -> confident. But criteria WRONG: <4 stmt dropped OnTick/OnTrade (core, short fn).
Day 51: sample skipped chunks -> OVER-SKIP found -> smart-skip (name/keyword) -> 1756->1484, core kept.
**root:** metric right, criteria wrong. "trivial" defined by statement-count (proxy) not by function-role.
**rule:** measurement != correctness. After measuring, VALIDATE criteria: sample the excluded set (skip/drop) -> confirm truly trivial. Quantify then verify exclusion.
**tags:** #meta #false-alarm #verify #pitfall #quantify

## [2026-07-19] Kimi/Moonshot = paid-only (free tier discontinued)
**fact:** platform.moonshot.cn/pricing shows 充值 (recharge) only. 免费 = file API temp-free, NOT model API.
  Key suspended (insufficient balance). kimi-moonlight model deprecated/free promo ended.
**decision:** SKIP. Not wired to provider chain. .env key kept for future reactivate.

## [2026-07-19] ALL TEXT PROVIDERS DEAD (forex/coding study blocked 23:05-23:10)
**SIG:** forex_study.py cron run -> exit -1 (crash). 2 runs failed same way.
**root causes (verified via curl):**
  1. groq = HTTP 403 / error 1010 (Cloudflare region/IP ban — Thailand IP blocked).
  2. openrouter = HTTP 404 "model unavailable for free" (free slug dead).
  3. mistral = daily cap 120 reached (resets next UTC day).
  4. gemini = vision-only (text not used by chat()).
  5. nous/cerebras/deepseek = no key in .env.
**secondary bug:** forex_study.py line 40 hardcodes `os.environ["OPENROUTER_API_KEY"]=""` (disables openrouter).
  Correct call (openrouter WAS dead anyway 404), but means "no key" error is self-inflicted on forex runs.
**result:** NO text provider usable -> forex study cannot run until mistral cap resets (next day) OR groq IP ban lifted.
**action:** study_journal push NOT done for forex_notes.json (file not even in study_journal git — separate gap, see other entry).
**RESOLVED 2026-07-20 00:06-04:02:** mistral daily cap reset (UTC) -> forex study ran OK (4 repos, provider gemini/mistral), coding study ran OK (2x mistral). forex_notes.json + code_notes.json NOW pushed to study_journal (gap closed). groq 403 IP ban + openrouter 404 STILL dead (only mistral/gemini text usable).
**tags:** #all-dead #groq-403 #openrouter-404 #mistral-cap #forex-blocked #escalation #resolved-next-day

## [2026-07-19] Kimi/Moonshot = paid-only (free tier discontinued)
**fact:** platform.moonshot.cn/pricing shows 充值 (recharge) only. 免费 = file API temp-free, NOT model API.
  Key suspended (insufficient balance). kimi-moonlight model deprecated/free promo ended.
**decision:** SKIP. Not wired to provider chain. .env key kept for future reactivate.
**tags:** #provider #kimi #paid #skip

## [2026-07-19] META: agent repo = full code (false-alarm on template)
**false:** checked ai_reasoning_agent README only -> claimed "template, no code".
**real:** repo HAS .py (reasoning_agent.py etc) - wrong curl path (subfolder) caused miss.
**rule:** verify code presence via GitHub API (contents/) not README-only. Don't claim template from 1 file.
**tags:** #meta #false-alarm #verify #agent-repo

## [2026-07-19] Coding/forex overnight study = save-only, NOT pushed (DONE bar gap)
**SIG:** overnight cron (code_study.py) exit 0, repo notes present — but study_journal remote `main` had no commit for them.
**❌** code_study.py writes `scripts/code_notes.json` only. No copy to `study_journal/`, no `git add/commit/push`.
**❌** study_journal/code_notes.json was stale (Jul 18) vs scripts/ (Jul 19 22:53) — missed ~24h of study from remote.
**✅** manual fix this run: `cp code_notes.json study_journal/ && git add && git commit && git push -u origin main` (first push needed upstream set; branch=main NOT master).
**why:** MAIN_ROLE DONE bar = "note saved + pushed". Save-alone ≠ done. Pipeline lacks push step.
**TODO/ASK:** make code_study.py push to study_journal itself (or wrap cron in sync+push) — SYSTEM fix, pending Kyaw approval.
**tags:** #push-gap #code_study #study_journal #done-bar #ask

## [2026-07-20] cron Windows path: `C:\` backslash → bash strips → EXIT 127
**SIG:** overnight cron given literal `C:\Users\user\...\python.exe code_study.py ...` → `EXIT_CODE=127`, bash: `C:UsersuserAppData...: command not found`
**❌** pass Windows BACKSLASH paths to the git-bash shell (terminal() runs bash/MSYS, NOT cmd). `\U`/`\u`/`\A` are escape chars → stripped → `C:Usersuser...` → command not found.
**✅** use `C:/Users/user/...` (forward slash — valid Windows path, keeps `C:` drive prefix) OR single-quote `'C:\Users\user\...'` (literal backslash). Both EXECUTE. `C:/` is cleanest (also works for `>` redirect targets).
**why:** user said "NO MSYS /c/ style" + "no cd". `C:/` satisfies both: Windows-native `C:` prefix, no `/c/` conversion, no backslash-escape bug. `/c/Users/...` also works but is the banned MSYS form.
**verify:** `C:/Users/user/AppData/Local/Programs/Python/Python310/python.exe --version` → `Python 3.10.0`, rc=0.
**tags:** #cron #windows #bash #path #127 #escape #gotcha

## [2026-07-20] re-run overwrite risk: two code_study runs same night
**SIG:** ran code_study.py manually at 02:52 → scripts/code_notes.json (ts 02:52–02:54, provider mistral, English notes). But study_journal already had commit `583f18b` (02:48) with SAME 6 repos, kavaan note in MYANMAR + provider groq (more role-aligned: §2 groq primary, §8 Myanmar).
**❌** blindly `cp scripts/code_notes.json study_journal/ && push` on every run → overwrites the better-aligned committed notes with a near-duplicate (buffer provider, English), redundant commit noise.
**✅** before push: diff scripts/ vs study_journal/ code_notes.json. If study_journal ALREADY has tonight's valid notes (quality:ok) — SKIP push, report. Only push when study_journal is genuinely behind (missing repos / stale / garbage).
**why:** ROLE precedence = correctness > automation, survivability > progress. Don't regress good notes for a redundant copy.
**tags:** #push #code_study #dedup #overwrite #cron

## [2026-07-20] META: gemini-embed = ROLLING SHARED window (not daily cap)
**false:** single task 1084 < 1500 daily cap -> 1 batch ရမယ် ထင်။
**real:** rolling 24h window = ALL embed tasks share (Day47-51 + M12). 560 မှာ ကုန် (shared).
**rule:** plan embed = task-total vs SHARED window, not single-task vs cap. Reset = prev+24h.
**tags:** #gemini #embed #quota #meta #rolling

## [2026-07-20] META: study_vectors.db path + git bloat
**issue:** 2 copies (scripts/ 44.8MB main + study_journal/ stale). day-48.py uses scripts/ (correct).
**risk:** journal/ copy = stale/partial; git binary bloat (44.8MB, no diff).
**fix:** .gitignore study_vectors.db + rag_day30.db (keep study.db notes). git rm --cached.
**rule:** vector/large db = OFF git. notes db = keep. Path = scripts/study_vectors.db (source of truth).
**tags:** #git #bloat #vector #path #meta

## [2026-07-20] META: STUDY_BOT_TOKEN = separate bot (misdiagnosis fixed)
**wrong:** git 8b72fab said STUDY_BOT_TOKEN မထည့် (conflict) -> reversed git 6a6fbdd.
**verify:** getMe 2 tokens -> kkk3=824051 (@kyawkk3_bot), study=809095 (@kkk4study_bot). DIFFERENT.
**truth:** 2 distinct tokens = NO conflict, 409 impossible. study_bot needs 809095 to have own identity.
**rule:** token conflict = SAME token polled by 2 procs. Different tokens = separate bots (safe).
**fix:** MAIN_ROLE §5 corrected: STUDY_BOT_TOKEN stays (separate), kkk3 protected separately.
**tags:** #telegram #token #409 #misdiagnosis #verify

## [2026-07-20] META: GEMINI_API_KEY rotation (stale first key)
- .env has 2 GEMINI_API_KEY (first=expired 401, second=valid).
- day-48.py os.environ.setdefault kept FIRST (stale) -> 401.
- fix: load .env last-wins (valid key).
- rule: when .env has dup keys, last occurrence = current. setdefault = bug.
- tags: #gemini #key #rotation #embed
