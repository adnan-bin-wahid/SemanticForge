"""Test helpers module."""

from helpers import format_greeting


def test_greeting():
    result = format_greeting("Alice")
    assert result == "Hello, Alice!"
