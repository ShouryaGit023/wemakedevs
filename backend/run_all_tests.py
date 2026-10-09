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

import unittest
from backend.tests.test_complete_workflow import TestCompleteBackendWorkflow
from backend.tests.test_data_sources import TestDataSourcesAndFusion
from backend.tests.test_data_sources_integration import TestDataSourcesIntegration

def run_all():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestCompleteBackendWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestDataSourcesAndFusion))
    suite.addTests(loader.loadTestsFromTestCase(TestDataSourcesIntegration))

    runner = unittest.TextTestRunner(verbosity=2)

    result = runner.run(suite)
    return {
        "total_tests": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "was_successful": result.wasSuccessful()
    }

if __name__ == "__main__":
    print("==================================================")
    print("🧪 RUNNING CLIMATESHIELD COMPLETE BACKEND TEST SUITE")
    print("==================================================")
    results = run_all()
    print("--------------------------------------------------")
    print(f"Total Tests Run : {results['total_tests']}")
    print(f"Tests Passed    : {results['passed']}")
    print(f"Tests Failed    : {results['failed']}")
    print(f"Test Errors     : {results['errors']}")
    print(f"Overall Result  : {'SUCCESS' if results['was_successful'] else 'FAILED'}")
    print("==================================================")
    sys.exit(0 if results['was_successful'] else 1)

