"""
Tests for io_manager.py

Focuses strictly on pure utility functions (pagination math, text formatting)
to avoid the complexities of mocking terminal standard input/output.
"""

import sys
import os
import traceback
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import io_manager as io


# ------------------ #
# _fit Tests
# ------------------ #

def test_fit_pads_short_text():
    """Test that text shorter than the width is padded with spaces."""
    result = io._fit("Hello", 10)
    assert len(result) == 10
    assert result == "Hello     "

def test_fit_truncates_long_text():
    """Test that text longer than the width is cut off and appended with an ellipsis."""
    result = io._fit("This is a very long location name", 15)
    assert len(result) == 15
    assert result.endswith("… ")
    assert result == "This is a ver… "

def test_fit_handles_non_strings():
    """Test that numeric or boolean inputs are safely converted to strings before fitting."""
    result = io._fit(42.5, 6)
    assert result == "42.5  "


# ------------------ #
# Pagination Tests
# ------------------ #

def test_page_count_exact_multiple():
    """Test page calculation when the row count perfectly divides by PAGE_SIZE."""
    # Assuming PAGE_SIZE is 5, a 10-row table should be exactly 2 pages
    dummy_table = pd.DataFrame([{"id": i} for i in range(10)])
    assert io._page_count(dummy_table) == 2

def test_page_count_with_remainder():
    """Test page calculation when the row count spills over into a new page."""
    # A 12-row table should be 3 pages
    dummy_table = pd.DataFrame([{"id": i} for i in range(12)])
    assert io._page_count(dummy_table) == 3

def test_page_count_empty_table():
    """Test that an empty table still registers as at least 1 page to prevent UI crashes."""
    dummy_table = pd.DataFrame()
    assert io._page_count(dummy_table) == 1

def test_go_next_success():
    """Test that page increments correctly when not on the last page."""
    new_page, changed = io._go_next(page=1, pages=3)
    assert new_page == 2
    assert changed is True

def test_go_next_blocked_at_end():
    """Test that scrolling past the last page is blocked."""
    new_page, changed = io._go_next(page=3, pages=3)
    assert new_page == 3
    assert changed is False

def test_go_previous_success():
    """Test that page decrements correctly."""
    new_page, changed = io._go_previous(page=2)
    assert new_page == 1
    assert changed is True

def test_go_previous_blocked_at_start():
    """Test that scrolling into negative pages is blocked."""
    new_page, changed = io._go_previous(page=1)
    assert new_page == 1
    assert changed is False


# ------------------ #
# Mini runner
# ------------------ #
def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            sys.stdout.write(f"PASS  {name}\n")
        except AssertionError as e:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n      {e}\n")
        except Exception:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n{traceback.format_exc()}\n")
            
    sys.stdout.write(f"\n{len(tests) - failures}/{len(tests)} tests passed\n")
    return failures

if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)