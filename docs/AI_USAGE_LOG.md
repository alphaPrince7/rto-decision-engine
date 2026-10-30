# AI Usage Log

### Tools used
- **Claude (Anthropic)** — data exploration planning, drafting the engine/flow code, writing the memo, and sanity-checking the economics.
- **An LLM inside the product itself** — the address/name judgment step (`engine/llm_check.py`), designed to run on an offline deterministic mock by default and a real model (e.g. GPT-4o-mini) when an API key is set.

### What I used AI for
- Scaffolding the config-driven engine and the WhatsApp flow quickly.
- Turning raw EDA numbers into a plain-English founder memo.
- Pressure-testing the "should we cancel?" economics argument.

### 3 times the AI was wrong or weak, and how I caught it

**1. AI first suggested cancelling all high-risk COD orders.**
When I described the problem, the initial AI framing leaned toward "cancel risky orders to save RTO cost" — echoing the Head of Ops. I caught it by actually computing the expected value: a delivered order (+₹402) massively outweighs a return (−₹169), so break-even is ~70% RTO, not something low. **Fix:** I made "don't cancel; confirm/nudge instead" the core recommendation, backed by the maths.

**2. AI proposed pincode-level risk scoring.**
It sounded precise and I nearly used it. **Caught it** by checking row counts: only one pincode had ≥8 orders, so pincode rates would be noise. **Fix:** dropped to state-level risk, which has enough volume to be reliable, and left pincode as an optional override.

**3. AI's first threshold values looked reasonable but lost money.**
The initially suggested bands (35/55/75) seemed sensible, but when I backtested, the hold bucket was only ~60% RTO and the policy *lost* ₹887 by cancelling genuine orders. **Caught it** by measuring actual RTO rate inside each bucket rather than trusting the numbers. **Fix:** swept thresholds against real data and breakeven economics, landing on 20/45/85 so the hold bucket is ~100% RTO.

### Where I deliberately did NOT trust AI
- The final money figures were computed in code from the real CSV, not estimated by an LLM.
- Phone/name/geo checks are deterministic code, not AI, so results are reproducible and free.
