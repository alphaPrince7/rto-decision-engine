# Kesh Haircare — COD RTO Decision Engine

An AI-assisted system that looks at every **Cash-on-Delivery order before it ships** and decides
what to do with it, to cut the 28% RTO (Return-to-Origin) rate that is bleeding money.

For each order it outputs one of four actions, each with a **plain-English reason**:
`ship_as_is` · `ship_after_confirmation` · `nudge_to_prepaid` · `hold_cancel`.

> **TL;DR of the findings:** cancelling "risky" orders *loses* money — a delivered order (+₹402)
> far outweighs a return (−₹169), so the break-even is ~70% RTO. The real wins are **WhatsApp
> confirmation** and **nudging to prepaid**. On the 2,017-order sample this nets **+₹29k (~₹43k/month)**.
> See `docs/Business_Memo.pdf`.

---

## Run it in under 10 minutes

```bash
# 1. Install (only 3 light deps)
pip install -r requirements.txt

# 2. Score all 2,000 sample orders + rebuild the founder dashboard
python run.py

# 3. Open the dashboard
#    dashboard/index.html   (one screen: 4 buckets, ₹ saved, ₹ lost, net ₹)

# 4. Score a single new order
python run.py --order '{"order_id":"NEW1","customer_name":"Ravi Kumar","phone":"9876543210","address":"chowk se left","state":"Bihar","customer_prior_orders":0,"customer_prior_rto":1,"utm_source":"meta_ads"}'

# 5. Try the WhatsApp confirmation / prepaid simulator
python -m whatsapp.flow

# 6. Run tests
python tests/test_engine.py
```

No API key needed — the address/name AI check runs on a built-in deterministic mock.
To use a real LLM instead, `export OPENAI_API_KEY=...` (same interface, see `engine/llm_check.py`).

---

## What's inside

| Path | What it is |
|------|-----------|
| `engine/decide.py` | Core decision engine — risk score → action + reason |
| `engine/llm_check.py` | The LLM-judged checks (address, fake names) + where we draw the AI line |
| `config/rules.yaml` | **All thresholds & weights — edit here, no code needed** |
| `whatsapp/flow.py` | WhatsApp confirmation + prepaid-nudge mock (yes/no/random/timeout) |
| `dashboard/index.html` | The founder's one-screen morning dashboard |
| `data/` | The orders, cleaned data, risk tables, and backtest results |
| `docs/Business_Memo.pdf` | **The memo to the founder (read this first)** |
| `docs/DECISION_LOG.md` | Key choices, alternatives, and why |
| `docs/AI_USAGE_LOG.md` | AI tools used + 3 times AI was wrong and how I caught it |

---

## Where the LLM is used (and where it is NOT)

**LLM** → judging address completeness/realness (incl. Hinglish, landmark-only) and fake names.
**Not LLM** → RTO probability (maths), phone validity (regex), geography risk (data table),
and the final money decision (expected-value maths).
*Reason:* an LLM is slow, costs money, and is non-deterministic — only pay for it where language
understanding actually beats code.

---

## Changing the rules (for a non-technical person)

Open `config/rules.yaml`. Want to be stricter? Lower the threshold numbers. Want a bigger prepaid
discount? Change `discount_rupees`. Want to stop treating a state as high-risk? Remove it from the list.
No code change, no redeploy.
