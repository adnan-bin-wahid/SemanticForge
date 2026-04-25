"""Tests for utils module."""

import pytest
from utils import add, multiply, divide, greet


def test_add():
    """Test add function."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_multiply():
    """Test multiply function."""
    assert multiply(3, 4) == 12
    assert multiply(-2, 3) == -6
    assert multiply(0, 5) == 0


def test_divide():
    """Test divide function."""
    assert divide(10, 2) == 5
    assert divide(9, 3) == 3
    assert divide(5, 0) == 0  # Division by zero returns 0


def test_greet():
    """Test greet function."""
    assert greet("World") == "Hello, World!"
    assert greet("Python") == "Hello, Python!"
