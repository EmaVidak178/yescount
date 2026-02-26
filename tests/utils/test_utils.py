from __future__ import annotations

from src.utils.health import liveness
from src.utils.invite_text import generate_invite


def test_liveness_ok():
    assert liveness()["ok"] is True


def test_generate_invite_contains_url():
    text = generate_invite("Plan", "Ema", "https://example.com?session=1", {"title": "Top Event"})
    assert "https://example.com?session=1" in text
