"""
Backtest the decision engine on the historical COD orders and compute the
money impact with a CORRECT, explicit time basis.

Time-basis rule (this is the fix):
  - The dataset is ~6 months of orders. We never relabel the whole sample as
    "one month". We report three figures that all reconcile:
      1. net over the sample   (the raw total across the full ~6-month dataset)
      2. net per month         = net_over_sample / months_in_sample
      3. net per 1,000 orders  = net_over_sample / sample_orders * 1000
         (so the result scales honestly to any future monthly volume)
  - months_in_sample is DERIVED from the data's own min/max dates, not assumed.

Run:  python analysis/backtest.py
Writes: data/backtest_results.csv, data/impact_summary.json
"""
from __future__ import annotations
import os, sys, json
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine.decide import decide, load_config, load_risk_tables

# Assumptions for the behavioural levers (stated openly in the memo).
CONFIRM_PREVENT = 0.50   # WhatsApp confirmation prevents ~50% of would-be RTOs
NUDGE_ACCEPT = 0.50      # ~50% of nudged customers accept prepaid (RTO -> 4%)


def main() -> None:
    cfg, risk = load_config(), load_risk_tables()
    RTO_COST = cfg["economics"]["cost_per_rto"]
    PD = cfg["economics"]["profit_per_delivered"]
    PREPAID_RTO = cfg["economics"]["prepaid_rto_rate"]
    DISC = cfg["prepaid"]["discount_rupees"]

    df = pd.read_csv(os.path.join(ROOT, "data", "orders_clean.csv"))

    # --- derive the real time span from the data (THE FIX) ---
    dates = pd.to_datetime(df["order_datetime"], errors="coerce")
    span_days = (dates.max() - dates.min()).days
    months_in_sample = span_days / 30.44  # avg days per month
    n = len(df)

    # --- run the engine over every order ---
    rows = []
    for _, o in df.iterrows():
        d = decide(o.to_dict(), cfg, risk)
        rows.append((o.order_id, d.action, d.risk_score, int(o.rto)))
    res = pd.DataFrame(rows, columns=["order_id", "action", "score", "actual_rto"])

    buckets = {a: int((res.action == a).sum())
               for a in ["ship_as_is", "ship_after_confirmation",
                         "nudge_to_prepaid", "hold_cancel"]}
    bucket_rto = {a: round(float(res[res.action == a].actual_rto.mean()), 3)
                  for a in buckets if buckets[a] > 0}

    confirm = res[res.action == "ship_after_confirmation"]
    nudge = res[res.action == "nudge_to_prepaid"]
    hold = res[res.action == "hold_cancel"]

    # --- money model (over the whole sample) ---
    saved_hold = hold.actual_rto.sum() * RTO_COST                 # avoided RTOs
    lost_hold = (1 - hold.actual_rto).sum() * PD                  # genuine orders cancelled
    saved_confirm = confirm.actual_rto.sum() * CONFIRM_PREVENT * RTO_COST
    accepters = len(nudge) * NUDGE_ACCEPT
    # accepters' RTO drops from their actual rate to the prepaid rate; discount paid on delivered prepaid
    saved_nudge = (nudge.actual_rto.sum() * NUDGE_ACCEPT * RTO_COST
                   - accepters * (1 - PREPAID_RTO) * DISC)

    net_sample = saved_hold - lost_hold + saved_confirm + saved_nudge

    # --- the three reconciling, correctly-based figures ---
    net_per_month = net_sample / months_in_sample
    net_per_1000_orders = net_sample / n * 1000

    summary = {
        "time_basis": {
            "sample_start": str(dates.min().date()),
            "sample_end": str(dates.max().date()),
            "span_days": int(span_days),
            "months_in_sample": round(months_in_sample, 2),
            "sample_orders": n,
        },
        "buckets": buckets,
        "bucket_rto": bucket_rto,
        "baseline_rto": round(float(res.actual_rto.mean()), 3),
        "components_over_sample": {
            "saved_hold": round(saved_hold),
            "lost_hold": round(lost_hold),
            "saved_confirm": round(saved_confirm),
            "saved_nudge": round(saved_nudge),
        },
        "net_over_sample": round(net_sample),
        "net_per_month": round(net_per_month),
        "net_per_1000_orders": round(net_per_1000_orders),
        "assumptions": {
            "confirmation_prevents_rto": CONFIRM_PREVENT,
            "nudge_accept_rate": NUDGE_ACCEPT,
        },
    }

    res.to_csv(os.path.join(ROOT, "data", "backtest_results.csv"), index=False)
    json.dump(summary, open(os.path.join(ROOT, "data", "impact_summary.json"), "w"), indent=2)

    print(f"Sample: {n} orders over {summary['time_basis']['months_in_sample']} months "
          f"({summary['time_basis']['sample_start']} to {summary['time_basis']['sample_end']})")
    print(f"Net over sample : Rs {summary['net_over_sample']:,}")
    print(f"Net per month   : Rs {summary['net_per_month']:,}   (= net_over_sample / months)")
    print(f"Net per 1,000 orders: Rs {summary['net_per_1000_orders']:,}")
    for a, c in buckets.items():
        r = bucket_rto.get(a)
        print(f"  {a:26} {c:5}  actual RTO {r*100:.0f}%" if r is not None else f"  {a:26} {c:5}")


if __name__ == "__main__":
    main()
