"""Serve evaluated results from the repository's published benchmark snapshots."""

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from evals.calculation_audit import CASES as CALCULATION_CASES, audit_case


router = APIRouter()
ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals" / "results"
TEMPLATE = ROOT / "templates" / "evals.html"


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _case_result(trial):
    checks = trial.get("checks", {})
    checked = trial.get("fields_checked", len(checks))
    if "fields_passed" in trial:
        passed = trial["fields_passed"]
    elif "findings" in trial:
        passed = checked - len(trial["findings"])
    else:
        passed = sum(checks.values())
    return {
        "id": trial["case"], "passed": trial["passed"], "checks_passed": passed,
        "checks_total": checked, "valid_json": trial["valid_json"],
    }


def _published_run(snapshot, stage):
    cases = [{"id": case["id"], "pdf_url": case.get("pdf_url")}
             for case in snapshot["cases"] if case.get("stage", stage) == stage]
    summaries = []
    for result in snapshot["summary"]:
        if result["stage"] != stage:
            continue
        trials = [trial for trial in snapshot["trials"]
                  if trial["stage"] == stage and trial["model"] == result["model"]]
        summaries.append({
            **{key: result[key] for key in (
                "model", "passed", "trials", "mean_score", "total_cost_usd", "median_latency_s"
            )},
            "cases": [_case_result(trial) for trial in trials],
        })
    return {"cases": cases, "models": summaries}


def evaluation_results():
    screening = _read(RESULTS / "2026-11-20-screening.json")
    lucky = _read(RESULTS / "2026-11-20-lucky-cement.json")
    extracts = _read(RESULTS / "2026-11-20-luck-indu-audit.json")
    latest = extracts["three_model"]
    fixtures = {case["id"]: case for case in _read(ROOT / "evals" / "cases.json")}
    extraction = _published_run(latest, "extraction")
    extraction["cases"].sort(key=lambda case: fixtures[case["id"]]["pdf_input_kind"] != "scanned images")
    for case in extraction["cases"]:
        case["pdf_url"] = fixtures[case["id"]]["pdf_url"]
    comparisons = {group["case"]: group for group in latest["field_comparisons"]}

    return {
        "run_at": latest["timestamp_utc"],
        "extraction": extraction,
        "extraction_screening": _published_run(screening, "extraction"),
        "comparisons": [comparisons[case["id"]] for case in extraction["cases"]],
        "scan_repeats": [
            {"name": name, **_published_run(extracts[name], "extraction")}
            for name in ("initial", "refined")
        ],
        "analysis": _published_run(screening, "analysis"),
        "lucky_analysis": _published_run(lucky["analysis"], "analysis"),
        "decision": _published_run(screening, "decision"),
        "calculations": [audit_case(case) for case in _read(CALCULATION_CASES)],
    }


@router.get("/evals", response_class=HTMLResponse, include_in_schema=False)
def read_evaluations():
    data = json.dumps(evaluation_results(), ensure_ascii=True).replace("<", "\\u003c")
    return HTMLResponse(TEMPLATE.read_text(encoding="utf-8").replace("<!-- EVALUATION_DATA -->", data))
