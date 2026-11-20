"""Verify Python financial calculations against checked filing inputs."""

import argparse
import json
import math
from pathlib import Path

from evals.model_benchmark import MISSING, field, is_number
from financial.statement_calculations import calculate_metrics
from financial.statement_values import normalize_statement
from financial.validators.financial_validator import FinancialMetricsValidator


CASES = Path(__file__).with_name("calculation_cases.json")


def audit_case(case):
    statement = normalize_statement(case["inputs"])
    validation = FinancialMetricsValidator().validate_all(statement)
    values = {"normalized": statement, "calculated": calculate_metrics(statement, case["quote_pkr"])}
    checks = []
    for path, expected in case["expected"].items():
        actual = field(values, path)
        if expected is None:
            passed = actual is MISSING or actual is None
        elif type(expected) is int:
            passed = is_number(actual) and actual == expected
        else:
            passed = is_number(actual) and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10)
        checks.append({
            "field": path, "expected": expected,
            "actual": actual if actual is not MISSING else None, "passed": passed,
        })
    return {
        "case": case["case"],
        "validation": validation,
        "checks": checks,
        "passed": validation["is_valid"] and all(check["passed"] for check in checks),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/evals/calculation-audit.json"))
    args = parser.parse_args()
    results = [audit_case(case) for case in json.loads(CASES.read_text(encoding="utf-8"))]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for result in results:
        checks = result["checks"]
        print(f"{result['case']}: {sum(check['passed'] for check in checks)}/{len(checks)} arithmetic checks")
        for issue in result["validation"]["errors"]:
            print(f"  {issue['message']}")
        for check in checks:
            if not check["passed"]:
                print(f"  {check['field']}: expected {check['expected']}, got {check['actual']}")
    return int(not all(result["passed"] for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
