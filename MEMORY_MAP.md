# HERMES MEMORY MAP — v2.1 (verified against live disk 2026-07-18)

C:/Users/user/AppData/Local/hermes/
│
├─ [T0] IDENTITY + RULES ......... memory tool (14 entries, ~93% of 2200 cap)
│      • Kyaw = XAUUSD algo-trader, Thailand GMT+7, Burmese
│      • "ရေး" မှ code / capital preservation first / လိုတိုရှင်း
│      • LLM = analysis only, live signal မဟုတ် / no martingale
│      • ⭐ coding fix မတင်ပြခင် PITFALLS.md grep — dead end ပြန်မစမ်း
│      • active project နာမည် ၁-၂ ခု (detail မထည့်)
│      ✎ test: "၆ လကြာ တူတူပဲလား?" ဟုတ်မှ ဒီထဲ
│      ✎ ဘယ်တော့မှ auto မချုံ့ရ (safety)
│      ✎ MAIN_ROLE pointer: "scripts/MAIN_ROLE.md — session start READ it"
│
├─ scripts/
│   │
│   ├─ [T1] FACTS .............. study.db  (42 rows, SQLite, VERIFIED)
│   │      • study note (topic/note/recap/verify/provider)
│   │      • queryable · durable · 5 rows recap_line EMPTY (gap §4)
│   │      ✎ retrieval = SQL LIKE + TF-IDF (0 API, embed မခေါ်)
│   │
│   ├─ [T2] LESSONS ........... MEMORY_LESSONS.md (6459 b, append-only · git)
│   │      • ဇာတ်ကြောင်း: မှား + root cause + fix + guard
│   │      • ကြည့်ပုံ: chronological read (session ပြီးမှ)
│   │
│   ├─ [T2b] PITFALLS ......... PITFALLS.md (3088 b, append-only · git)
│   │      • dead-end trail: ❌စမ်း→ကျ / ❌စမ်း→ကျ / ✅ဖြစ်→ဘာလို့
│   │      • code မရေးခင် "ဒါ ကြုံဖူးလား?" → grep SIG
│   │      ✎ ❌ ဘယ်တော့မှ မဖျက် — dead end က feature
│   │
│   ├─ [ROLE] MAIN_ROLE.md .... master copy (7646 b, v2, section ၈)
│   │      • scripts/MAIN_ROLE.md == study_journal/MAIN_ROLE.md (SYNC)
│   │      • SOUL.md = MAIN_ROLE.md content (7646 b, framework auto-load)
│   │      • SOUL.md.bak.20260718_203327 = original default identity
│   │      ✎ sync: MAIN_ROLE.md edit → copy to SOUL.md (drift guard)
│   │      ✎ study.py recap_line = self-contained (recap 0 API)
│   │
│   └─ providers.py ........... .env ← source of truth (VERIFIED)
│          list = nous→groq→openrouter→mistral→cohere→nvidia(+gemini)
│          ✎ config.yaml နဲ့ မချိတ် (drift #1 ကာကွယ်)
│          ⚠️ NOUS_API_KEY = UNSET → openrouter ပဲ အလုပ်လုပ် (§2 vs reality gap)
│
├─ [T3] SKILLS ................. skills/ (exists — အသစ် မဆောက်)
│      • ပြန်သုံး workflow ရှိမှ ထည့် · over-engineer မဖြစ်စေနဲ့
│
├─ .env ....................... provider key + TELEGRAM (hermes root, NOT scripts/)
├─ config.yaml ............... main agent settings ← မထိ
│
└─ ⛔ DON'T-TOUCH ZONE (agent ကိုယ်ပိုင် · မထိ)
       memories/  ← per-session memory
       sessions/  ← conversation history
       state.db   ← 66MB main state
       auth.json  ← gateway auth
       cron/      ← ၆ job (schtasks)

# ROUTING (fact တစ်ခု = နေရာတစ်ခု)
  study note ရလဒ် ........... study.db
  ❌ dead end / အလုပ်မဖြစ် ... PITFALLS.md   ← code မရေးခင် grep
  session သင်ခန်းစာ ဇာတ် ..... MEMORY_LESSONS.md
  ပြန်သုံး workflow ......... skills/
  provider / version / param  .env + git commit
  ၆ လ stable rule .......... memory tool (T0) + MAIN_ROLE.md (SOUL.md)

# CONTROL RULES ၇ ချက်
1. fact တစ်ခု = နေရာတစ်ခု (၂ နေရာ ထပ်ရင် drift)
2. grep-before-code = မဖြစ်မနေ — dead end ပြန်မစမ်း
3. ❌ trail ဘယ်တော့မှ မဖျက် — "ဘာ မလုပ်ရ" က တန်ဖိုး
4. retrieval အားလုံး = 0 API (SQL + TF-IDF, embed မခေါ်)
5. rules ဘယ်တော့မှ auto မချုံ့ရ (guard ပျောက်ရင် ငွေဆုံး)
6. store တစ်ခု ပြည့်လည်း တခြားဟာ မပျက် (bamboo fence)
7. append-only + git (LESSONS / PITFALLS / MAP / MAIN_ROLE)

⚠️ RAG/embed box = မထည့် — quota စား + failure အသစ်
⚠️ providers: .env only ← config.yaml နဲ့ မရော

# KNOWN GAPS (fix လိုအပ် — Kyaw approval လို)
  G1: NOUS_API_KEY UNSET → "nous=primary" (§2) နဲ့ ဆန့်ကျင် → key ထည့် ဒါမဟုတ် ROLE ပြင်
  G2: study.db 5 rows recap_line EMPTY → §4 DONE bar မပြည့် → backfill
