#!/usr/bin/env python3
"""
One command to run everything.

    python run.py                 # score the sample, print bucket summary, rebuild dashboard
    python run.py --order '{...}' # score a single JSON order
    python run.py --demo          # run the 3-order demo
"""
import argparse, json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from engine.decide import decide, load_config, load_risk_tables


def score_sample():
    import pandas as pd
    cfg, risk = load_config(), load_risk_tables()
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "data", "orders_clean.csv"))
    from collections import Counter
    c = Counter()
    for _, o in df.iterrows():
        c[decide(o.to_dict(), cfg, risk).action] += 1
    print("Scored", len(df), "historical COD orders:\n")
    for a in ["ship_as_is", "ship_after_confirmation", "nudge_to_prepaid", "hold_cancel"]:
        print(f"  {a:26} {c[a]:5}")
    # rebuild dashboard
    os.system(f"{sys.executable} " + os.path.join(os.path.dirname(__file__), "dashboard", "build_dashboard.py"))
    print("\nOpen dashboard/index.html in a browser. Read docs/Business_Memo.pdf for the recommendation.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", help="JSON string for a single order")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    if a.order:
        import ast
        d = decide(ast.literal_eval(a.order) if "'" in a.order and '"' not in a.order else json.loads(a.order))
        print(json.dumps({"action": d.action, "risk_score": d.risk_score,
                          "reason": d.reason, "est_rto_prob": d.est_rto_prob}, indent=2))
    elif a.demo:
        from engine.decide import __name__ as _
        os.system(f"{sys.executable} -m engine.decide")
    else:
        score_sample()


if __name__ == "__main__":
    main()
