"""Test helpers module."""

from helpers import format_greeting


def test_greeting():
    result = format_greeting("Alice")
    assert result == "Hello, Alice!"

def test_greeting_empty():
    result = format_greeting("")
    assert result == "Hello, !"
    
