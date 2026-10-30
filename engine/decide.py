"""
RTO Decision Engine — core.

Takes one COD order -> returns an action + a plain-English reason + the money math.
Actions: ship_as_is | ship_after_confirmation | nudge_to_prepaid | hold_cancel

Design: a transparent additive risk score (0-100) from tunable weights in
config/rules.yaml, plus an economic (expected-value) sanity check. Everything a
non-technical person would want to change lives in the YAML, not here.
"""
from __future__ import annotations
import os, re, json, yaml
from dataclasses import dataclass, asdict, field

from .llm_check import check_address, check_name_is_fake

_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)


def load_config(path: str | None = None) -> dict:
    path = path or os.path.join(_ROOT, "config", "rules.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def load_risk_tables(path: str | None = None) -> dict:
    path = path or os.path.join(_ROOT, "data", "risk_tables.json")
    with open(path) as f:
        return json.load(f)


_PHONE_PAT = re.compile(r"^[6-9]\d{9}$")


@dataclass
class Decision:
    order_id: str
    action: str
    risk_score: int
    reason: str
    factors: list = field(default_factory=list)   # the human-readable reasons that fired
    est_rto_prob: float = 0.0


def _valid_phone(phone) -> bool:
    return bool(_PHONE_PAT.match(re.sub(r"\D", "", str(phone))))


def score_order(order: dict, cfg: dict, risk: dict) -> Decision:
    w = cfg["risk_weights"]
    score = 0
    factors: list[str] = []

    prior_rto = int(order.get("customer_prior_rto", 0) or 0)
    prior_orders = int(order.get("customer_prior_orders", 0) or 0)
    state = str(order.get("state", "")).strip()

    # --- history (code + maths, no LLM) ---
    if prior_rto >= 2:
        score += w["prior_rto_2plus"]; factors.append(f"Customer has returned {prior_rto} past orders")
    elif prior_rto == 1:
        score += w["prior_rto_1"]; factors.append("Customer returned 1 past order")
    if prior_orders == 0:
        score += w["new_customer"]; factors.append("First-time buyer (no order history)")

    # --- geography (data table, no LLM) ---
    if state in cfg["high_risk_states"]:
        score += w["high_risk_state"]; factors.append(f"{state} is a high-RTO region")
    elif state in cfg["medium_risk_states"]:
        score += w["medium_risk_state"]; factors.append(f"{state} has above-average RTO")

    # --- phone (regex, no LLM) ---
    if not _valid_phone(order.get("phone")):
        score += w["invalid_phone"]; factors.append("Phone number looks invalid")

    # --- name (rules first; LLM in production for edge cases) ---
    if check_name_is_fake(order.get("customer_name", "")):
        score += w["fake_name"]; factors.append("Customer name looks fake/garbage")

    # --- address (LLM judgment — this is where the LLM earns its keep) ---
    av = check_address(order.get("address", ""))
    if not av.is_complete:
        score += w["address_incomplete"]; factors.append(av.reason)
    elif not av.has_house_number:
        score += w["address_no_house_number"]; factors.append(av.reason)

    score = int(min(score, 100))

    # --- estimate RTO probability for the money story (data-anchored) ---
    base = risk["state_risk"].get(state, risk["global_rto"])
    est = base
    if prior_rto >= 2: est = max(est, 0.70)
    elif prior_rto == 1: est = max(est, 0.40)
    if not av.is_complete: est = max(est, 0.45)
    est = round(min(est, 0.95), 3)

    return Decision(str(order.get("order_id", "")), "", score, "", factors, est)


def decide(order: dict, cfg: dict | None = None, risk: dict | None = None) -> Decision:
    cfg = cfg or load_config()
    risk = risk or load_risk_tables()
    d = score_order(order, cfg, risk)
    t = cfg["thresholds"]

    # Marketing guardrail: protect a paid first order from auto-cancel.
    g = cfg["guardrails"]
    protected = (
        g.get("protect_paid_first_order")
        and int(order.get("customer_prior_orders", 0) or 0) == 0
        and str(order.get("utm_source", "")) in g.get("protect_paid_sources", [])
    )

    if d.risk_score < t["ship_as_is_below"]:
        d.action = "ship_as_is"
        d.reason = "Low risk — ship normally."
    elif d.risk_score < t["confirm_below"]:
        d.action = "ship_after_confirmation"
        d.reason = "Some risk — confirm the order on WhatsApp before shipping."
    elif d.risk_score < t["nudge_prepaid_below"]:
        d.action = "nudge_to_prepaid"
        d.reason = f"High risk — offer Rs {cfg['prepaid']['discount_rupees']} off to pay online (prepaid)."
    else:
        if protected and d.risk_score < g["extreme_score_override"]:
            d.action = "nudge_to_prepaid"
            d.reason = ("Very risky, but this is a paid-ads first order (CAC ~Rs 300). "
                        "Try converting to prepaid instead of cancelling.")
        else:
            d.action = "hold_cancel"
            d.reason = "Very high risk — hold/cancel; expected loss outweighs expected profit."

    # Attach the top human-readable factors to the reason.
    if d.factors:
        d.reason += "  (" + "; ".join(d.factors[:3]) + ")"
    return d


if __name__ == "__main__":
    # tiny demo
    cfg, risk = load_config(), load_risk_tables()
    samples = [
        dict(order_id="A1", customer_name="Meera Pillai", phone="9109605378",
             address="784/17, MG Nagar, Opp. Hanuman Mandir", state="Tamil Nadu",
             customer_prior_orders=2, customer_prior_rto=0, utm_source="direct"),
        dict(order_id="A2", customer_name="asdf", phone="12345",
             address="chowk se left", state="Bihar",
             customer_prior_orders=0, customer_prior_rto=0, utm_source="meta_ads"),
        dict(order_id="A3", customer_name="Ravi Kumar", phone="9876543210",
             address="Station chowk se left, Hanuman Mandir ke saamne", state="Uttar Pradesh",
             customer_prior_orders=0, customer_prior_rto=1, utm_source="meta_ads"),
    ]
    for s in samples:
        d = decide(s, cfg, risk)
        print(f"{d.order_id}: {d.action.upper():24} score={d.risk_score:3}  {d.reason}")
