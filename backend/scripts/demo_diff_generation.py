#!/usr/bin/env python3
"""
Demo script to test DiffGenerator functionality with test-project code.
Run this from the backend directory: python scripts/demo_diff_generation.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.diff_generator import DiffGenerator


def demo_basic_diff():
    """Demonstrate basic unified diff generation."""
    print("=" * 70)
    print("DEMO 1: Basic Unified Diff")
    print("=" * 70)
    
    original = """import re
from typing import List

def format_greeting(name: str) -> str:
    \"\"\"Formats a greeting message.\"\"\"
    return f"Hello, {name}!"

def validate_email(email: str) -> bool:
    \"\"\"Validates if an email address has correct format.\"\"\"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
"""
    
    generated = """import re
from typing import List, Tuple, Optional

def format_greeting(name: str) -> str:
    \"\"\"Formats a greeting message with emoji support.\"\"\"
    return f"👋 Hello, {name}!"

def validate_email(email: str) -> bool:
    \"\"\"Validates if an email address has correct format.\"\"\"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_email_with_domain(email: str) -> Tuple[bool, Optional[str]]:
    \"\"\"Enhanced validation that extracts domain.\"\"\"
    pattern = r'^[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})$'
    match = re.match(pattern, email)
    if match:
        return True, match.group(1)
    return False, None
"""
    
    generator = DiffGenerator()
    diff = generator.generate_unified_diff(original, generated, "utils/helpers.py")
    
    print(diff)
    print()


def demo_diff_stats():
    """Demonstrate diff statistics."""
    print("=" * 70)
    print("DEMO 2: Diff Statistics")
    print("=" * 70)
    
    original = "def hello():\n    pass\n"
    generated = "def hello():\n    print('Hello')\n    return True\n"
    
    generator = DiffGenerator()
    stats = generator.get_diff_stats(original, generated)
    
    print("Statistics:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    print()


def demo_significance():
    """Demonstrate significance detection."""
    print("=" * 70)
    print("DEMO 3: Significance Detection")
    print("=" * 70)
    
    original = "def foo():\n    x = 1\n    return x\n"
    
    # Minor change
    minor = "def foo():\n    x = 1  # Changed comment\n    return x\n"
    
    # Major change
    major = "def foo():\n    x = 1 + 2\n    y = x * 2\n    return y\n"
    
    generator = DiffGenerator()
    
    minor_sig = generator.is_significant_diff(original, minor, threshold=0.9)
    major_sig = generator.is_significant_diff(original, major, threshold=0.9)
    
    print(f"Minor change is significant (threshold=0.9): {minor_sig}")
    print(f"Major change is significant (threshold=0.9): {major_sig}")
    print()


def demo_context_diff():
    """Demonstrate context diff with surrounding lines."""
    print("=" * 70)
    print("DEMO 4: Context Diff (with surrounding lines)")
    print("=" * 70)
    
    original = "\n".join([
        "def process_user(user):",
        "    validate(user)",
        "    user.activate()",
        "    save(user)",
    ])
    
    generated = "\n".join([
        "def process_user(user):",
        "    if not validate(user):",
        "        raise ValueError('Invalid user')",
        "    user.activate()",
        "    user.send_welcome_email()",
        "    save(user)",
    ])
    
    generator = DiffGenerator()
    diff = generator.generate_context_diff(original, generated, context_lines=1)
    
    print(diff)
    print()


def demo_side_by_side():
    """Demonstrate side-by-side diff."""
    print("=" * 70)
    print("DEMO 5: Side-by-Side Diff")
    print("=" * 70)
    
    original = "x = 1\ny = 2\nz = x + y\n"
    generated = "x = 1\ny = 3\nz = x + y\nprint(z)\n"
    
    generator = DiffGenerator()
    diff = generator.generate_side_by_side_diff(original, generated, width=40)
    
    print(diff)
    print()


def demo_patch_file_io():
    """Demonstrate saving and loading patches."""
    print("=" * 70)
    print("DEMO 6: Patch File I/O")
    print("=" * 70)
    
    original = "def foo():\n    pass\n"
    generated = "def foo():\n    return 42\n"
    
    generator = DiffGenerator()
    diff = generator.generate_unified_diff(original, generated, "example.py")
    
    # Save
    patch_file = "demo_test.patch"
    generator.save_patch_file(diff, patch_file)
    print(f"✓ Saved patch to: {patch_file}")
    
    # Load
    loaded_patch = generator.load_patch_file(patch_file)
    print(f"✓ Loaded patch ({len(loaded_patch)} bytes)")
    
    # Verify they match
    if loaded_patch == diff:
        print("✓ Patch content matches original")
    
    # Cleanup
    Path(patch_file).unlink()
    print(f"✓ Cleaned up: {patch_file}")
    print()


if __name__ == "__main__":
    try:
        demo_basic_diff()
        demo_diff_stats()
        demo_significance()
        demo_context_diff()
        demo_side_by_side()
        demo_patch_file_io()
        
        print("=" * 70)
        print("All demos completed successfully! ✓")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
