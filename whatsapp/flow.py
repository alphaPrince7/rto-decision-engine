"""
WhatsApp confirmation + prepaid-nudge flow — working mock (no real WhatsApp needed).

Two flows:
  A) SHIP_AFTER_CONFIRMATION  — ask the customer to confirm the COD order.
  B) NUDGE_TO_PREPAID         — offer a discount to pay online instead.

Handles: "yes" / "no" / random text / no reply in 24h.
Messages default to Hinglish (what most Indian COD buyers actually read fastest).

Run `python -m whatsapp.flow` for an interactive simulator.
"""
from __future__ import annotations
import re, yaml, os

_ROOT = os.path.dirname(os.path.dirname(__file__))
_cfg = yaml.safe_load(open(os.path.join(_ROOT, "config", "rules.yaml")))
DISCOUNT = _cfg["prepaid"]["discount_rupees"]
WINDOW = _cfg["whatsapp"]["reply_window_hours"]

YES = re.compile(r"\b(yes|haan|haa|ha|ok|okay|confirm|sahi|theek|yep|y|pakka|done)\b", re.I)
NO = re.compile(r"\b(no|nahi|na|cancel|nope|nhi|mat|don'?t|dont)\b", re.I)


# ---------- message templates ----------
def confirm_message(name: str, order_id: str, amount: int, lang="hinglish") -> str:
    if lang == "english":
        return (f"Hi {name}! This is Kesh Haircare. Please confirm your COD order "
                f"#{order_id} of Rs {amount}. Reply YES to ship it today, or NO to cancel.")
    return (f"Namaste {name}! 🌿 Kesh Haircare se.\n"
            f"Aapka COD order #{order_id} (Rs {amount}) confirm karna hai.\n"
            f"👉 Ship karne ke liye *YES* bhejein, cancel ke liye *NO*.")


def prepaid_message(name: str, order_id: str, amount: int, lang="hinglish") -> str:
    new = amount - DISCOUNT
    if lang == "english":
        return (f"Hi {name}! Pay online now for order #{order_id} and get Rs {DISCOUNT} OFF "
                f"— pay just Rs {new} instead of Rs {amount}. Reply PAY for the link, or COD to keep cash on delivery.")
    return (f"Namaste {name}! 🌿 Kesh Haircare.\n"
            f"Order #{order_id}: abhi online pay karein aur Rs {DISCOUNT} ki chhoot paayein!\n"
            f"💳 Sirf Rs {new} (Rs {amount} ki jagah).\n"
            f"👉 Link ke liye *PAY* bhejein, ya COD rakhne ke liye *COD*.")


# ---------- reply handling ----------
def handle_reply(flow: str, reply: str | None) -> dict:
    """flow: 'confirm' or 'prepaid'. reply: text, or None for 24h timeout."""
    if reply is None:  # no reply within the window
        if flow == "confirm":
            return dict(outcome="timeout", action="hold_cancel",
                        note=f"No reply in {WINDOW}h → do NOT ship (COD unconfirmed). Saves an RTO.")
        return dict(outcome="timeout", action="ship_after_confirmation",
                    note=f"No reply in {WINDOW}h → fall back to a confirmation attempt before shipping COD.")

    text = reply.strip()
    if flow == "confirm":
        if YES.search(text):
            return dict(outcome="yes", action="ship_as_is", note="Customer confirmed → ship today.")
        if NO.search(text):
            return dict(outcome="no", action="hold_cancel", note="Customer declined → cancel, RTO avoided.")
        return dict(outcome="unclear", action="reask",
                    note="Unclear reply → send one clarifying message, then treat next no-reply as timeout.")
    else:  # prepaid
        if re.search(r"\bpay\b", text, re.I) or YES.search(text):
            return dict(outcome="pay", action="convert_prepaid",
                        note=f"Customer will pay online → send link, Rs {DISCOUNT} off. RTO risk drops to ~4%.")
        if re.search(r"\bcod\b", text, re.I) or NO.search(text):
            return dict(outcome="keep_cod", action="ship_after_confirmation",
                        note="Customer wants COD → fall back to a WhatsApp confirmation before shipping.")
        return dict(outcome="unclear", action="reask",
                    note="Unclear reply → resend the offer once with a simpler PAY/COD choice.")


def simulate():
    print("=== WhatsApp flow simulator (type a reply, or press Enter for '24h timeout') ===\n")
    name, oid, amt = "Ravi", "KT101753", 699
    for flow, msg in [("confirm", confirm_message(name, oid, amt)),
                      ("prepaid", prepaid_message(name, oid, amt))]:
        print(f"--- {flow.upper()} FLOW ---")
        print("OUTBOUND:\n" + msg + "\n")
        try:
            r = input("Customer reply> ").strip() or None
        except EOFError:
            r = None
        res = handle_reply(flow, r)
        print(f"→ outcome={res['outcome']} | next={res['action']}\n  {res['note']}\n")


if __name__ == "__main__":
    simulate()
