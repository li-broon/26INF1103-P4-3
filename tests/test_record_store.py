# Imports

import inspect
import os
import sys
import traceback
from abc import ABC

# Import the Module Under Test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))  # Let 'src' be Imported
from src.data_manager.storage.record_store import RecordStore

# The Methods the Contract Must Declare
EXPECTED_METHODS = {"save_record", "load_records", "get_column_names"}

# ----- #
# Tests
# ----- #

# RecordStore is an abstract class (ABC)
def test_record_store_is_an_abc():
    assert issubclass(RecordStore, ABC)


# An abstract class cannot be created directly, only through a class that implements it
def test_record_store_cannot_be_created():
    try:
        RecordStore()
    except TypeError:
        return
    raise AssertionError("RecordStore() should raise TypeError")


# The contract is exactly the three methods the DataManager needs (no more, no fewer)
def test_record_store_declares_exactly_the_three_methods():
    assert set(RecordStore.__abstractmethods__) == EXPECTED_METHODS


# Every method in the contract has typed parameters and a return type
def test_every_method_has_type_hints():
    for name in EXPECTED_METHODS:
        signature = inspect.signature(getattr(RecordStore, name))
        for parameter in signature.parameters.values():
            if parameter.name != "self":
                assert parameter.annotation is not inspect.Parameter.empty, f"{name}({parameter.name})"
        assert signature.return_annotation is not inspect.Signature.empty, f"{name} has no return type"


# The default for ascending is False, so the most urgent report comes first
def test_load_records_defaults_to_most_urgent_first():
    default = inspect.signature(RecordStore.load_records).parameters["ascending"].default
    assert default is False


# ------------ #
# Test Runner
# ------------ #

def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            sys.stdout.write(f"PASS  {name}\n")
        except Exception:
            failures += 1
            sys.stdout.write(f"FAIL  {name}\n{traceback.format_exc()}\n")
    sys.stdout.write(f"\n{len(tests) - failures}/{len(tests)} tests passed\n")
    return failures


if __name__ == "__main__":
    sys.exit(1 if run_all() else 0)
