from __future__ import annotations

from src.utils.health import readiness


class _HealthyCollection:
    def count(self) -> int:
        return 0


class _BrokenCollection:
    def count(self) -> int:
        raise RuntimeError("collection unavailable")


def test_readiness_ok_with_sqlite_and_chroma(sqlite_db):
    status = readiness(sqlite_db, _HealthyCollection())
    assert status["ok"] is True
    assert status["dependencies"]["sqlite"] == "ready"
    assert status["dependencies"]["chroma"] == "ready"


def test_readiness_fails_without_chroma(sqlite_db):
    status = readiness(sqlite_db, None)
    assert status["ok"] is False
    assert "error" in status["dependencies"]["chroma"]


def test_readiness_fails_when_chroma_raises(sqlite_db):
    status = readiness(sqlite_db, _BrokenCollection())
    assert status["ok"] is False
    assert "error" in status["dependencies"]["chroma"]
