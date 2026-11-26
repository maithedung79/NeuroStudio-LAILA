"""Temporary probe to verify CI rejects failing tests."""


def test_intentional_failure() -> None:
    assert False, "Intentional failure to verify CI gate"

