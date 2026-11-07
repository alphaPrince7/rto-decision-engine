"""Generate the founder dashboard (one self-contained HTML screen) from the backtest."""
import json, os, datetime

ROOT = os.path.dirname(os.path.dirname(__file__))
s = json.load(open(os.path.join(ROOT, "data", "impact_summary.json")))
b, rto = s["buckets"], s["bucket_rto"]
comp = s["components_over_sample"]
tb = s["time_basis"]
saved = comp["saved_hold"] + comp["saved_confirm"] + comp["saved_nudge"]
lost = comp["lost_hold"]
net = s["net_over_sample"]
months = tb["months_in_sample"]
total_orders = tb["sample_orders"]

cards = [
    ("Ship as-is", b["ship_as_is"], rto["ship_as_is"], "#1B998B", "Low risk — goes out normally"),
    ("Confirm on WhatsApp", b["ship_after_confirmation"], rto["ship_after_confirmation"], "#2E6FD6", "Some risk — confirm first"),
    ("Nudge to prepaid", b["nudge_to_prepaid"], rto["nudge_to_prepaid"], "#D98E04", "High risk — offer online payment"),
    ("Hold / cancel", b["hold_cancel"], rto["hold_cancel"], "#C0392B", "Extreme risk — don't ship"),
]
card_html = ""
for name, n, r, color, desc in cards:
    card_html += f"""
    <div class="card" style="border-top:4px solid {color}">
      <div class="card-n">{n}</div>
      <div class="card-name">{name}</div>
      <div class="card-desc">{desc}</div>
      <div class="card-rto">Actual RTO in this bucket: <b>{r*100:.0f}%</b></div>
    </div>"""

html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Kesh Haircare — RTO Control</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body{{font-family:'Segoe UI',system-ui,Arial,sans-serif;margin:0;background:#f4f6fa;color:#1a2230;}}
 .wrap{{max-width:960px;margin:0 auto;padding:28px 20px 48px;}}
 h1{{font-size:24px;margin:0 0 2px;color:#15325B;}}
 .sub{{color:#6b7684;font-size:14px;margin-bottom:22px;}}
 .cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:26px;}}
 .card{{background:#fff;border-radius:10px;padding:16px 16px 14px;box-shadow:0 1px 3px rgba(0,0,0,.06);}}
 .card-n{{font-size:34px;font-weight:700;color:#15325B;line-height:1;}}
 .card-name{{font-weight:600;margin:6px 0 2px;font-size:14px;}}
 .card-desc{{color:#6b7684;font-size:12px;min-height:30px;}}
 .card-rto{{font-size:11.5px;color:#55606e;border-top:1px solid #eef1f5;margin-top:8px;padding-top:7px;}}
 .money{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:12px;}}
 .m{{background:#fff;border-radius:10px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.06);}}
 .m-label{{color:#6b7684;font-size:12.5px;margin-bottom:6px;}}
 .m-val{{font-size:26px;font-weight:700;}}
 .green{{color:#1B998B;}} .red{{color:#C0392B;}} .navy{{color:#15325B;}}
 .net{{background:#15325B;color:#fff;border-radius:10px;padding:20px 24px;display:flex;
       justify-content:space-between;align-items:center;margin-top:4px;}}
 .net .big{{font-size:30px;font-weight:700;}}
 .foot{{color:#8a94a3;font-size:11.5px;margin-top:22px;line-height:1.6;}}
 @media(max-width:720px){{.cards,.money{{grid-template-columns:1fr 1fr;}}}}
</style></head><body><div class="wrap">
 <h1>Kesh Haircare — COD Risk Control</h1>
 <div class="sub">Yesterday's COD orders, after the decision engine ran · {datetime.date.today().strftime('%d %b %Y')}</div>

 <div class="cards">{card_html}</div>

 <div class="money">
   <div class="m"><div class="m-label">Est. ₹ saved from avoided RTOs</div>
     <div class="m-val green">₹{saved:,}</div></div>
   <div class="m"><div class="m-label">Est. ₹ lost from cancelling genuine orders</div>
     <div class="m-val red">₹{lost:,}</div></div>
   <div class="m"><div class="m-label">Orders processed (≈{months}-month sample)</div>
     <div class="m-val navy">{total_orders:,}</div></div>
 </div>

 <div class="net">
   <div><div style="font-size:13px;opacity:.85;">Net ₹ impact vs shipping everything blindly<br>(over the {months}-month sample)</div>
     <div class="big">+ ₹{net:,}</div></div>
   <div style="text-align:right;font-size:13px;opacity:.9;">
     ≈ ₹{s['net_per_month']:,} / month &nbsp;·&nbsp; ≈ ₹{s['net_per_1000_orders']:,} per 1,000 orders<br>
     Baseline RTO was {s['baseline_rto']*100:.0f}% — now triaged before shipping</div>
 </div>

 <div class="foot">
   Numbers are a backtest on {total_orders:,} real past COD orders (≈{months} months) using the current
   rules in <code>config/rules.yaml</code>. "Saved" counts RTOs prevented by holding, WhatsApp
   confirmation, and prepaid conversion; "lost" counts genuine orders that holding cancels.
   Assumptions (confirmation prevents 50% of would-be RTOs; 50% accept prepaid) are stated in the memo.
 </div>
</div></body></html>"""

out = os.path.join(ROOT, "dashboard", "index.html")
open(out, "w").write(html)
print("wrote", out)
