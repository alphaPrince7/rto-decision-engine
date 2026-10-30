# Decision Log

A running list of the important choices, the alternatives I considered, and why I picked what I did.

### 1. Score-based rules vs. a trained ML model
- **Chose:** a transparent additive risk score (0–100) from tunable weights.
- **Alternatives:** logistic regression / gradient boosting on the labelled data.
- **Why:** the brief demands that (a) a non-technical person can change thresholds without code, and (b) every decision has a plain-English reason. A hand-weighted score gives both for free. A trained model is my *next* step (see memo §5), but it would start as a black box and needs guardrails before it touches real orders.

### 2. Where the LLM is used — and where it is NOT
- **LLM used for:** judging address completeness/realness (incl. Hinglish, landmark-only addresses) and flagging fake names.
- **LLM NOT used for:** RTO probability (lookup + arithmetic), phone validity (regex), geography risk (data table), and the final money decision (expected-value maths).
- **Why:** LLMs are slow, cost money per call, and are non-deterministic. I only pay for one where language understanding genuinely beats code. This line is enforced in `engine/llm_check.py`.

### 3. Don't auto-cancel risky orders — the economics say so
- **Chose:** cancel only near-certain returns (score ≥ 85, ~0.2% of orders).
- **Alternative:** Head of Ops wanted to auto-cancel anything risky / stop COD in bad pincodes.
- **Why:** a delivered order earns ₹402; a return costs ₹169. Break-even RTO probability is **~70%**. Cancelling a 40–50% RTO order destroys more value (lost profit on the ones that would deliver) than it saves. The data confirmed it: holding below score 85 produced a *negative* net.

### 4. Thresholds calibrated against the real data, not guessed
- **Chose:** ship<20, confirm<45, nudge<85, else hold.
- **Why:** my first guess (35/55/75) put the hold bucket at 60% RTO, which *lost* ₹887 because it cancelled genuine orders. I swept thresholds against actual bucket RTO and breakeven economics and moved them so the hold bucket is ~100% RTO. This iteration is the whole point — the first guess was wrong and the data fixed it.

### 5. State-level geography, not pincode
- **Chose:** state risk table.
- **Alternative:** pincode-level risk.
- **Why:** only 1 pincode in the sample had ≥8 orders — pincode data is far too sparse to trust. State-level is statistically solid (Bihar 53% on 146 orders vs TN 20% on 158). The config still *allows* pincode overrides when real volume justifies it.

### 6. Marketing guardrail for paid-ads first orders
- **Chose:** never auto-cancel a first order from paid sources (meta/google/influencer) unless score ≥ 85.
- **Why:** directly answers Marketing's ₹300 CAC concern. A risky paid-ads newbie gets nudged to prepaid instead of cancelled.

### 7. Hinglish as the default WhatsApp language
- **Chose:** Hinglish messages by default (config-switchable to English/Hindi).
- **Why:** most Indian COD buyers read Hinglish fastest; higher reply rate = more RTOs caught.

### 8. Clean the dirty labels, don't drop silently
- The file had `Rto`, `delivered`, one `IN_TRANSIT`. I normalise case and keep only DELIVERED/RTO for scoring, and flagged this in the memo as a data-quality risk.

### 9. Conservative money assumptions, stated openly
- Confirmation prevents 50% of would-be RTOs; 50% of nudged customers accept prepaid.
- **Why:** better to under-promise savings. Both live as constants and are easy to update once real outcomes arrive.
