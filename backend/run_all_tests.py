"""
ClimateShield - Backend Test Suite Execution Script
Executes the complete test suite and outputs structured diagnostic metrics.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.tests.test_complete_workflow import run_tests_programmatically

if __name__ == "__main__":
    print("==================================================")
    print("🧪 RUNNING CLIMATESHIELD COMPLETE BACKEND TEST SUITE")
    print("==================================================")
    results = run_tests_programmatically()
    print("--------------------------------------------------")
    print(f"Total Tests Run : {results['total_tests']}")
    print(f"Tests Passed    : {results['passed']}")
    print(f"Tests Failed    : {results['failed']}")
    print(f"Test Errors     : {results['errors']}")
    print(f"Overall Result  : {'SUCCESS' if results['was_successful'] else 'FAILED'}")
    print("==================================================")
    sys.exit(0 if results['was_successful'] else 1)
