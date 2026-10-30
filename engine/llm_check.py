"""
LLM-based checks — used ONLY where judgment beats simple code.

WHERE WE USE AN LLM (judgment / fuzzy language):
  - Is this address complete and real, or vague? (Hinglish, landmarks, missing house no.)
  - Is this a fake/garbage name ("asdf", "test", "jkjk")?

WHERE WE DO NOT USE AN LLM (code/maths is better, cheaper, deterministic):
  - RTO probability from history         -> lookup tables + arithmetic
  - Phone number validity                -> regex
  - Geography risk                       -> data table
  - The final money/EV decision          -> arithmetic
Reason: an LLM is slow, costs money, and is non-deterministic. We only pay for it
on the two tasks that genuinely need language understanding.

This module runs OFFLINE by default (a deterministic mock that mimics the LLM),
so the whole project runs in <10 minutes with no API key. Set OPENAI_API_KEY to
use a real model via the same interface.
"""
from __future__ import annotations
import os, re, json
from dataclasses import dataclass


@dataclass
class AddressVerdict:
    has_house_number: bool
    is_complete: bool          # complete & plausibly real
    reason: str


_FAKE_NAME_PAT = re.compile(r"(asdf|qwer|test|dummy|xxx|abcd|jkjk|aaa|zzz|na na|no name)", re.I)
_VAGUE_PAT = re.compile(r"(saamne|se left|se right|peeche|ke paas|ke pass|chowk|mandir ke|bank ke)", re.I)
_HOUSE_NO_PAT = re.compile(r"(\d+\s*[/-]?\s*\d*|flat|plot|house|h\.?no|door)", re.I)


def check_name_is_fake(name: str) -> bool:
    """Rule-first; an LLM would only be called on ambiguous cases in production."""
    if not name or len(str(name).strip()) < 3:
        return True
    if _FAKE_NAME_PAT.search(str(name)):
        return True
    # single repeated char / no vowels at all -> likely garbage
    s = re.sub(r"[^a-z]", "", str(name).lower())
    if s and (len(set(s)) == 1 or not re.search(r"[aeiou]", s)):
        return True
    return False


def _mock_llm_address(address: str) -> AddressVerdict:
    """Deterministic stand-in for an LLM address judgment (offline default)."""
    a = str(address or "").strip()
    has_num = bool(_HOUSE_NO_PAT.search(a))
    vague = bool(_VAGUE_PAT.search(a)) and not has_num
    too_short = len(a) < 15
    if not a or too_short:
        return AddressVerdict(has_num, False, "Address too short / missing — likely undeliverable")
    if vague:
        return AddressVerdict(has_num, False, "Landmark-only address with no house/flat number")
    if not has_num:
        return AddressVerdict(False, True, "No clear house/flat number, but otherwise plausible")
    return AddressVerdict(True, True, "Address looks complete (has house number)")


def check_address(address: str) -> AddressVerdict:
    """
    Public entry point. Uses a real LLM if OPENAI_API_KEY is set, else the mock.
    The mock encodes the same heuristics an LLM would learn, so results are stable.
    """
    if os.getenv("OPENAI_API_KEY"):
        try:
            return _real_llm_address(address)
        except Exception:
            # Fail safe: if the LLM errors, fall back to the deterministic mock.
            return _mock_llm_address(address)
    return _mock_llm_address(address)


def _real_llm_address(address: str) -> AddressVerdict:  # pragma: no cover
    """Optional real-LLM path. Kept tiny and defensive."""
    from openai import OpenAI
    client = OpenAI()
    prompt = (
        "You judge Indian delivery addresses (often Hinglish). "
        "Return JSON {\"has_house_number\":bool,\"is_complete\":bool,\"reason\":str}. "
        "is_complete = could a courier actually find this? "
        f"Address: {address!r}"
    )
    r = client.chat.completions.create(
        model="gpt-4o-mini", temperature=0,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    d = json.loads(r.choices[0].message.content)
    return AddressVerdict(bool(d["has_house_number"]), bool(d["is_complete"]), str(d["reason"]))
