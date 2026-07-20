# HERMES SYSTEM ARCHITECTURE — Kyaw (verified 2026-07-20)

【1】CONNECT FLOW (gateway cloud, AGENT local)
─────────────────────────────
မင်း (Telegram app)
   → @kyawkk3_bot (824051, TELEGRAM_BOT_TOKEN)
   → Hermes Cloud Gateway (Nous server — message receive only, always up)
   → LOCAL Hermes agent (backend: local, မင့် computer — computer ON မှ run)
   → session: agent:main:telegram:dm:8192230588
   → ကျာ် (Hermes Agent / Main Role)
✅ getMe: 824051 = @kyawkk3_bot (first_name: kkk3)
⚠️ CORRECTED: computer OFF → gateway up (msg received) BUT local agent dead → NO reply.
   kkk3 talk/control = computer ON required (agent backend local).
   Cloud = message route only, NOT compute.
→ kkk3 = main channel (computer on မှ)
- **getMe live: 824051 = @kyawkk3_bot (first_name: kkk3)** ✅

## 【2】STUDY BOT (separate, poll-only)
```
@kkk4study_bot (809095, STUDY_BOT_TOKEN)
   → study.py run_session (cron) → study_inbox → study.db
   → ကျာ် (same agent, separate chat — kkk3 နဲ့ မ ရော)
```
- ၂ token ကွဲ (824051 ≠ 809095) = conflict မ ရှိ, 409 မ ဖြစ်
- **getMe live: 809095 = @kkk4study_bot (first_name: @study_bot)** ✅
- Live test PASS: "test routing" → study_bot only, kkk3 မ ရော

## 【3】LOCAL SCRIPTS (computer on only)
```
C:/Users/user/AppData/Local/hermes/scripts/
   study.py, code_study.py, providers.py
   day-27.py … day-48.py   (M7–M12 study code, PASS)
   study.db          (123 notes, inbox + notes)
   study_vectors.db  (1020 vectors, scripts/ ONLY — gitignored)
   MAIN_ROLE.md, SOUL.md, MEMORY_MAP.md, PITFALLS.md, MEMORY_LESSONS.md
   agent_study.json

C:/Users/user/AppData/Local/hermes/
   .env        (tokens — DON'T TOUCH kkk3 token)
   config.yaml (telegram: enabled: true)
   sessions/sessions.json  (kkk3 session key ONLY)
```

## 【4】MEMORY TIERS (T0–T3)
- T0: memory tool (13 entries, 2200 char cap)
- T1: study.db (notes 1–123)
- T2: PITFALLS.md + MEMORY_LESSONS.md (git, append-only)
- T3: skills/ + .env + config.yaml
- retrieval = 0 API (SQL + TF-IDF local)

## 【5】PROVIDER CHAIN (providers.py = source of truth)
- primary : groq (llama-3.3-70b, fastest)
- buffer  : openrouter (429 risk) · mistral
- vision  : gemini-3.1-flash-lite (GEMINI_API_KEY)
- embed   : gemini-embed-2 (3072, GEMINI_API_KEY — SAME as vision)
- nvidia  : text-only 2048 (curl)
- inactive: nous · cohere (dead) · kimi (suspended)
- ⚠️ GEMINI vision + embed = SAME key → rolling window SHARED
  (vision calls eat embed quota → 560-cutoff factor)

## 【6】CRON (6 jobs — hermes agent loop, NOT schtasks)
- Learning 18:00 · Audit 20:00 · Coding ~21:00 · Forex overnight · Weekly Sun 08:00
- ⚠️ Cron = computer ON မှ run
- ⚠️ Missed (computer off) = skip, NO auto-catchup
- ✅ Catch-up: study.py last_run meta → "🔄 Catch-up: N day(s) gap" + resume

## 【7】CLOUD ↔ LOCAL BRIDGE
- ❌ NONE (no ngrok/tunnel/webhook)
- kkk3 cloud command = manual (မင်း computer မှာ run)
- embed/cron/study = local process (computer on)

## 【8】GUARD / LIMITS (MAIN_ROLE §5)
- ❌ EA / live-trading code (study example ပဲ)
- ❌ Main system မထိ (fix = approval)
- ❌ Live trading signal (analysis ပဲ)
- ❌ Don't-touch: state.db · sessions/ · auth.json · memories/
- ❌ CONNECT PROTECTION:
  - kkk3 token (824051) မ ထိ
  - Desktop Local gateway မ ဖွင့်
  - BotFather Revoke မ လုပ်
  - sessions.json မ ဖျက်
  - cloud→local bridge မ တည်ဆောက်

## 【9】PENDING (carry)
- ⏳ 524 embed       = (quota reset ~03:45) AND (computer ON)
- ⏳ iATR coverage   = embed ပြီးမှ
- ⏳ 2-way analysis  = embed ပြီးမှ (PASS design)
- ⏳ M12 recap       = embed ပြီးမှ

## 【10】VERIFIED FACTS (this session, getMe live)
- ✅ kkk3 = 824051 (@kyawkk3_bot), cloud, separate, PROTECTED
- ✅ study_bot = 809095 (@kkk4study_bot), separate, live test PASS
- ✅ Desktop = local gateway (closed, separate session)
- ✅ No bridge (cloud can't trigger local)
- ✅ Catch-up code works (3-day gap test PASS)
- ✅ day-48.py valid GEMINI key (last-wins fix)
- ✅ study_vectors.db = 1020, scripts/ only, UNIQUE hash guard
- ⚠️ doc drift fixed: 824051=kkk3 (NOT study — yesterday's note was wrong)
- ⚠️ GEMINI vision+embed = same key → shared rolling quota
