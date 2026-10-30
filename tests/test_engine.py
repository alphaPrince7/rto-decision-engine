"""Minimal tests — run with `python -m pytest` (or they run via run.py demo)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from engine.decide import decide
from whatsapp.flow import handle_reply


def test_clean_repeat_customer_ships():
    o = dict(order_id="T1", customer_name="Meera Pillai", phone="9109605378",
             address="784/17, MG Nagar, Opp. Hanuman Mandir", state="Tamil Nadu",
             customer_prior_orders=3, customer_prior_rto=0, utm_source="direct")
    assert decide(o).action == "ship_as_is"


def test_fake_everything_cancels():
    o = dict(order_id="T2", customer_name="asdf", phone="12345", address="x",
             state="Bihar", customer_prior_orders=0, customer_prior_rto=2, utm_source="direct")
    assert decide(o).action == "hold_cancel"


def test_paid_first_order_protected_from_cancel():
    o = dict(order_id="T3", customer_name="Ravi Kumar", phone="9876543210",
             address="chowk se left", state="Uttar Pradesh",
             customer_prior_orders=0, customer_prior_rto=1, utm_source="meta_ads")
    # risky, but protected -> should be nudged, not cancelled
    assert decide(o).action in ("nudge_to_prepaid", "ship_after_confirmation")


def test_whatsapp_replies():
    assert handle_reply("confirm", "haan")["action"] == "ship_as_is"
    assert handle_reply("confirm", "nahi")["action"] == "hold_cancel"
    assert handle_reply("confirm", None)["action"] == "hold_cancel"
    assert handle_reply("prepaid", "PAY")["action"] == "convert_prepaid"


if __name__ == "__main__":
    for fn in [test_clean_repeat_customer_ships, test_fake_everything_cancels,
               test_paid_first_order_protected_from_cancel, test_whatsapp_replies]:
        fn(); print("PASS", fn.__name__)
