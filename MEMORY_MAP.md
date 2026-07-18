# HERMES MEMORY MAP — ၆ ထပ် (ဝါးစည်း · control လွယ်)

C:/Users/user/AppData/Local/hermes/
│
├─ [T0] IDENTITY + RULES ......... memory tool (~13 entry ceiling)
│      • Kyaw = XAUUSD algo-trader, Thailand GMT+7, Burmese
│      • "ရေး" မှ code / capital preservation first / လိုတိုရှင်း
│      • LLM = analysis only, live signal မဟုတ် / no martingale
│      • ⭐ coding fix မတင်ပြခင် PITFALLS.md grep — dead end ပြန်မစမ်း
│      • active project နာမည် ၁-၂ ခု (detail မထည့်)
│      ✎ test: "၆ လကြာ တူတူပဲလား?" ဟုတ်မှ ဒီထဲ
│      ✎ ဘယ်တော့မှ auto မချုံ့ရ (safety)
│
├─ scripts/
│   │
│   ├─ [T1] FACTS .............. study.db  (42 rows, SQLite)
│   │      • study note (topic/note/recap/verify/provider)
│   │      • queryable · durable
│   │      ✎ retrieval = SQL LIKE + TF-IDF (0 API, embed မခေါ်)
│   │
│   ├─ [T2] LESSONS ........... MEMORY_LESSONS.md (append-only · git)
│   │      • ဇာတ်ကြောင်း: မှား + root cause + fix + guard
│   │      • ဘယ်အချိန်: session ပြီးမှ "ဘာ သင်ခဲ့လဲ" ဖတ်
│   │      • ကြည့်ပုံ: chronological read
│   │
│   ├─ [T2b] PITFALLS ......... PITFALLS.md  ★ (append-only · git)
│   │      • dead-end trail: ❌စမ်း→ကျ / ❌စမ်း→ကျ / ✅ဖြစ်→ဘာလို့
│   │      • ဘယ်အချိန်: code မရေးခင် "ဒါ ကြုံဖူးလား?"
│   │      • ကြည့်ပုံ: SIG (symptom) နဲ့ grep/search
│   │      ✎ ❌ ဘယ်တော့မှ မဖျက် — dead end က feature
│   │      ✎ ဖြေရှင်းပြီးမှ trail အပြည့် (❌❌✅) တစ်ခါတည်း append
│   │
│   ├─ [ROLE] MAIN_ROLE.md .... master copy (v2, section ၈) + SOUL.md auto-load
│   │      • session start: framework loads SOUL.md (= MAIN_ROLE.md content)
│   │      • study.py recap_line = self-contained (recap 0 API)
│   │      • sync: MAIN_ROLE.md edit → copy to SOUL.md (drift guard)
│   │
│   └─ providers.py ........... .env ← source of truth
│          nous→groq→openrouter→mistral→cohere→nvidia(+gemini)
│          ✎ config.yaml နဲ့ မချိတ် (drift #1 ကာကွယ်)
│
├─ [T3] SKILLS ................. skills/ (ရှိပြီး — အသစ် မဆောက်)
│      • ပြန်သုံး workflow ရှိမှ ထည့် · over-engineer မဖြစ်စေနဲ့
│
├─ .env ....................... provider key + TELEGRAM (study ဟာ)
├─ config.yaml ............... main agent settings ← မထိ
│
└─ ⛔ DON'T-TOUCH ZONE (agent ကိုယ်ပိုင် · ငါ မမြင်ရ · မထိ)
       memories/  ← per-session memory
       sessions/  ← conversation history
       state.db   ← 66MB main state (ဘယ်တော့မှ မထိ)
       auth.json  ← gateway auth
       cron/      ← ၆ job (schtasks)

# CONTROL RULES ၇ ချက်
1. fact တစ်ခု = နေရာတစ်ခုတည်း (၂ နေရာ ထပ်ရင် drift)
2. grep-before-code = မဖြစ်မနေ (T0 rule) — dead end ပြန်မစမ်း
3. ❌ trail ဘယ်တော့မှ မဖျက် — "ဘာ မလုပ်ရ" က တန်ဖိုး
4. retrieval အားလုံး = 0 API (SQL + TF-IDF, embed မခေါ်)
5. rules ဘယ်တော့မှ auto မချုံ့ရ (guard ပျောက်ရင် ငွေဆုံး)
6. store တစ်ခု ပြည့်လည်း တခြားဟာ မပျက် (bamboo fence)
7. append-only + git (LESSONS / PITFALLS ၂ ခုစလုံး)

⚠️ RAG/embed box = မထည့် — quota စား + failure အသစ်
⚠️ providers: .env only ← config.yaml နဲ့ မရော
