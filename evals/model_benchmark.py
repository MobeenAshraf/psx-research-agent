"""Compare OpenRouter models on fixed PSX research tasks."""

import argparse
import base64
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from statistics import mean, median
import sys
from tempfile import NamedTemporaryFile
import time
from urllib.parse import urlparse

import requests

from financial.prompt_builders import (
    DEFAULT_SYSTEM_PROMPT,
    DECISION_RESPONSE_SCHEMA,
    build_analysis_prompt,
    build_decision_prompts,
    build_pdf_extraction_prompt,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "financial" / "prompts"
DEFAULT_CASES = ROOT / "evals" / "cases.json"
DEFAULT_PDF_CACHE = ROOT / "data" / "evals" / "pdfs"
URL = "https://openrouter.ai/api/v1/chat/completions"
BASELINES = {
    "extraction": ("EXTRACTION_MODEL", "google/gemini-3-flash-preview"),
    "analysis": ("ANALYSIS_MODEL", "openai/gpt-4o"),
    "decision": ("DECISION_MODEL", "openai/gpt-4o"),
}
TEXT_CANDIDATES = (
    "deepseek/deepseek-v4.1-flash-1017",
    "anthropic/claude-haiku-5.5",
    "openai/gpt-6-luna",
    "openai/gpt-6.2-sol",
)
CANDIDATES = {
    "extraction": (
        "google/gemini-3.5-flash-lite",
        "google/gemini-3.8-flash",
        "google/gemini-4-hydrogen",
    ),
    "analysis": TEXT_CANDIDATES,
    "decision": TEXT_CANDIDATES,
}
MISSING = object()


def load_dotenv_if_available():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT / ".env")


def pdf_cache_path(cache_dir, url):
    return cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.pdf"


def validate_pdf(case, contents):
    if not contents.startswith(b"%PDF-"):
        raise ValueError(f"{case['id']}: fixture is not a PDF")
    expected = case.get("pdf_sha256")
    if expected and hashlib.sha256(contents).hexdigest() != expected:
        raise ValueError(f"{case['id']}: PDF does not match its pinned SHA-256")


def load_pdf(case, cache_dir):
    url = case["pdf_url"]
    path = pdf_cache_path(cache_dir, url)
    try:
        return path.read_bytes()
    except FileNotFoundError:
        pass

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    contents = response.content
    validate_pdf(case, contents)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temp_path = Path(temporary.name)
        try:
            temporary.write(contents)
            temporary.close()
            try:
                os.link(temp_path, path)
            except FileExistsError:
                # Another run saved the first snapshot while this one downloaded.
                return path.read_bytes()
        finally:
            temp_path.unlink(missing_ok=True)
    return contents


def prepare_payload(case, cases_dir, *, fetch_pdf=False, pdf_cache=DEFAULT_PDF_CACHE):
    stage = case["stage"]
    system_file = PROMPTS / "1_system_prompt_expert_analyst.md"
    system = system_file.read_text(encoding="utf-8") if system_file.exists() else DEFAULT_SYSTEM_PROMPT
    if stage == "decision":
        schema_path = PROMPTS / "decision_response_schema.json"
        schema = (
            schema_path.read_text(encoding="utf-8")
            if schema_path.exists()
            else json.dumps(DECISION_RESPONSE_SCHEMA, indent=2)
        )
        system, user = build_decision_prompts(
            (PROMPTS / "decision_prompt.md").read_text(encoding="utf-8"),
            schema,
            **case["input"],
        )
    elif stage == "analysis":
        template = (PROMPTS / "investor_analysis_prompt.md").read_text(encoding="utf-8")
        user = build_analysis_prompt(template, case["input"]).format()
        system = system.format()
    else:
        template = (PROMPTS / "investor_extraction_prompt.md").read_text(encoding="utf-8")
        text = build_pdf_extraction_prompt(template, "").format()
        if case.get("scope"):
            text = f"{case['scope']}\n\n{text}"
        if "pdf_path" in case:
            pdf = cases_dir / case["pdf_path"]
            filename, pdf_bytes = pdf.name, pdf.read_bytes()
        else:
            url = case["pdf_url"]
            filename, pdf_bytes = Path(urlparse(url).path).name or "statement.pdf", None
            if fetch_pdf:
                pdf_bytes = load_pdf(case, pdf_cache)
        if pdf_bytes is not None:
            validate_pdf(case, pdf_bytes)
            data = base64.b64encode(pdf_bytes).decode("ascii")
            location = f"data:application/pdf;base64,{data}"
        else:
            location = url
        attachment = {"filename": filename, "file_data": location}
        user = [{"type": "text", "text": text}, {"type": "file", "file": attachment}]
        system = system.format()
    return {
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": 16000 if stage == "extraction" else 8000,
        "response_format": {"type": "json_object"},
        "provider": {"require_parameters": True},
    }


def field(output, path):
    for part in path.split("."):
        if isinstance(output, dict):
            output = output.get(part, MISSING)
        elif isinstance(output, list) and part.isdecimal() and int(part) < len(output):
            output = output[int(part)]
        else:
            return MISSING
    return output


def is_number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def equal_value(actual, expected, tolerance):
    if is_number(expected):
        return is_number(actual) and (
            actual == expected if tolerance == 0 else abs(actual - expected) <= tolerance
        )
    return type(actual) is type(expected) and actual == expected


def grade(case, output):
    """Grade a JSON object against deterministic checks and mandatory fields."""
    checks = {}
    for path, expected in case.get("expected", {}).items():
        tolerance = case.get("absolute_tolerance", {}).get(path, 0)
        checks[f"value:{path}"] = equal_value(field(output, path), expected, tolerance)
    for path, kind in case.get("nonempty", {}).items():
        actual = field(output, path)
        if kind == "string":
            valid = isinstance(actual, str) and bool(actual.strip())
        else:
            valid = isinstance(actual, list) and bool(actual) and all(
                isinstance(item, str) and item.strip() for item in actual
            )
        checks[f"shape:{path}"] = valid
    for path, pattern in case.get("patterns", {}).items():
        actual = field(output, path)
        if isinstance(actual, list):
            actual = " ".join(item for item in actual if isinstance(item, str))
        checks[f"pattern:{path}"] = isinstance(actual, str) and bool(re.search(pattern, actual, re.I))
    if case["stage"] == "decision":
        confidence = field(output, "confidence")
        checks["range:confidence"] = is_number(confidence) and 0 <= confidence <= 1
    score = sum(checks.values()) / len(checks)
    critical = set(case.get("critical", []))
    critical_ok = all(passed for name, passed in checks.items() if name.split(":", 1)[1] in critical)
    return {
        "checks": checks,
        "score": score,
        "critical_ok": critical_ok,
        "passed": critical_ok and score >= 0.90,
    }


def reject_json_constant(value):
    raise ValueError(f"Invalid JSON constant {value}")


def run_trial(session, case, payload, model, repeat, timeout):
    row = {
        "stage": case["stage"],
        "case": case["id"],
        "model": model,
        "repeat": repeat,
        "score": 0.0,
        "passed": False,
        "valid_json": False,
        "cost_usd": None,
    }
    started = time.monotonic()
    try:
        response = session.post(URL, json={**payload, "model": model}, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        row["latency_s"] = round(time.monotonic() - started, 3)
        usage = result.get("usage") or {}
        row.update(
            generation_id=result.get("id"),
            resolved_model=result.get("model"),
            provider=result.get("provider"),
            usage=usage,
            cost_usd=usage.get("cost") if is_number(usage.get("cost")) else None,
        )
        choice = result["choices"][0]
        row["finish_reason"] = choice.get("finish_reason")
        row["raw_output"] = choice["message"].get("content")
        if row["finish_reason"] in {"length", "error", "content_filter"} or choice.get("error"):
            raise ValueError(f"Incomplete response ({row['finish_reason']})")
        output = json.loads(row["raw_output"], parse_constant=reject_json_constant)
        if not isinstance(output, dict):
            raise ValueError("Expected a JSON object")
        row["valid_json"] = True
        row.update(grade(case, output))
    except requests.HTTPError as exc:
        row["error"] = str(exc)
        if exc.response is not None:
            row["http_status"] = exc.response.status_code
            try:
                message = exc.response.json()["error"]["message"]
                if isinstance(message, str):
                    row["error"] = f"HTTP {row['http_status']}: {message[:250]}"
            except (ValueError, KeyError, TypeError):
                pass
        row.setdefault("latency_s", round(time.monotonic() - started, 3))
    except (requests.RequestException, ValueError, AttributeError, KeyError, IndexError, TypeError) as exc:
        row["error"] = str(exc)
        row.setdefault("latency_s", round(time.monotonic() - started, 3))
    return row


def summarize(rows, baselines, incomplete_stages=()):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["stage"], row["model"]].append(row)
    summaries = []
    for (stage, model), trials in grouped.items():
        passed = sum(row["passed"] for row in trials)
        known = [row["cost_usd"] for row in trials if row["cost_usd"] is not None]
        total = sum(known) if len(known) == len(trials) else None
        summaries.append({
            "stage": stage,
            "model": model,
            "baseline": baselines[stage] == model,
            "trials": len(trials),
            "passed": passed,
            "mean_score": mean(row["score"] for row in trials),
            "json_rate": mean(row["valid_json"] for row in trials),
            "median_latency_s": median(row["latency_s"] for row in trials),
            "total_cost_usd": total,
            "cost_per_pass_usd": total / passed if passed and total is not None else None,
        })
    cheapest_passing = {}
    for stage in baselines:
        stage_rows = [row for row in summaries if row["stage"] == stage]
        if not stage_rows:
            continue
        baseline = next(row for row in stage_rows if row["baseline"])
        baseline_cost = baseline["cost_per_pass_usd"]
        for row in stage_rows:
            cost = row["cost_per_pass_usd"]
            row["cost_savings_vs_baseline_pct"] = (
                100 * (1 - cost / baseline_cost) if cost is not None and baseline_cost else None
            )
            row["score_delta_vs_baseline"] = row["mean_score"] - baseline["mean_score"]
        eligible = [
            row for row in stage_rows
            if row["passed"] == row["trials"] and row["cost_per_pass_usd"] is not None
        ]
        if eligible and stage not in incomplete_stages:
            winner = min(eligible, key=lambda row: (row["cost_per_pass_usd"], row["median_latency_s"]))
            cheapest_passing[stage] = winner["model"]
    return summaries, cheapest_passing


def main(argv=None):
    load_dotenv_if_available()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Send billable OpenRouter requests")
    parser.add_argument("--stage", choices=BASELINES, action="append", help="Repeat to select multiple stages")
    parser.add_argument("--model", action="append", help="Override challengers, keeping each stage's baseline")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--pdf-cache", type=Path, default=DEFAULT_PDF_CACHE, help="Directory of reusable PDF fixtures")
    parser.add_argument("--case", action="append", help="Repeat to select case IDs within the chosen stages")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=300, help="Request timeout in seconds")
    parser.add_argument("--temperature", type=float, help="Use a fixed temperature if supported by all models")
    parser.add_argument("--output", type=Path, default=Path("data/evals/model-benchmark.json"))
    args = parser.parse_args(argv)
    if args.repeats < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--repeats and --timeout must be positive")
    if args.temperature is not None and not 0 <= args.temperature <= 2:
        parser.error("--temperature must be between 0 and 2")
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if args.case:
        selected = set(args.case)
        cases = [case for case in cases if case["id"] in selected]
        if selected != {case["id"] for case in cases}:
            parser.error("--case must match a case ID")
    stages = list(dict.fromkeys(args.stage or [case["stage"] for case in cases]))
    if any(stage not in BASELINES for stage in stages):
        parser.error("unknown benchmark stage")
    cases = [case for case in cases if case["stage"] in stages]
    if set(stages) != {case["stage"] for case in cases}:
        parser.error("each selected stage needs at least one case")
    if len({case["id"] for case in cases}) != len(cases):
        parser.error("case IDs must be unique")
    if not all(case.get("expected") for case in cases):
        parser.error("each case needs at least one expected field")
    baselines = {stage: os.getenv(BASELINES[stage][0]) or BASELINES[stage][1] for stage in stages}
    models = {
        stage: list(dict.fromkeys([baselines[stage], *(args.model or CANDIDATES[stage])]))
        for stage in stages
    }
    api_key = os.getenv("OPENROUTER_API_KEY")
    if args.live and not api_key:
        parser.error("--live requires OPENROUTER_API_KEY to be set in the environment or .env")
    payloads = {}
    input_errors = {}
    for case in cases:
        try:
            payload = prepare_payload(case, args.cases.parent, fetch_pdf=args.live, pdf_cache=args.pdf_cache)
            if args.temperature is not None:
                payload["temperature"] = args.temperature
            payloads[case["id"]] = payload
        except (OSError, ValueError, requests.RequestException) as exc:
            input_errors[case["id"]] = str(exc)
            print(f"Could not prepare {case['id']}: {exc}", file=sys.stderr, flush=True)
    runnable_cases = [case for case in cases if case["id"] in payloads]
    incomplete_stages = {case["stage"] for case in cases if case["id"] in input_errors}
    for stage in stages:
        count = sum(case["stage"] == stage for case in runnable_cases)
        print(f"{stage}: {count} cases × {args.repeats} repeats × {len(models[stage])} models")
        for model in models[stage]:
            print(f"  {model}" + (" (baseline)" if model == baselines[stage] else ""))
    if not args.live:
        print("Dry run. Add --live to send requests.")
        return int(bool(input_errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with requests.Session() as session:
        session.headers["Authorization"] = f"Bearer {api_key}"
        for repeat in range(1, args.repeats + 1):
            for case in runnable_cases:
                for model in models[case["stage"]]:
                    row = run_trial(session, case, payloads[case["id"]], model, repeat, args.timeout)
                    rows.append(row)
                    outcome = row.get("error", f"{row['score']:.0%}")
                    print(f"{case['id']} [{repeat}] {model}: {outcome}", flush=True)

    summaries, cheapest = summarize(rows, baselines, incomplete_stages)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "temperature": args.temperature,
        "repeats": args.repeats,
        "cases": cases,
        "input_errors": input_errors,
        "baselines": baselines,
        "prompt_hashes": {
            name: hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            for name, payload in payloads.items()
        },
        "summary": summaries,
        "cheapest_passing": cheapest,
        "trials": rows,
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print()
    for row in summaries:
        cost = row["cost_per_pass_usd"]
        cost_text = f"${cost:.6f}" if cost is not None else "n/a"
        print(
            f"{row['stage']} {row['model']} | {row['passed']}/{row['trials']} passed | "
            f"{row['mean_score']:.0%} checks | {row['json_rate']:.0%} JSON | "
            f"{row['median_latency_s']:.2f}s median | {cost_text} per pass"
        )
    for stage in stages:
        outcome = "incomplete inputs" if stage in incomplete_stages else cheapest.get(stage, "none")
        print(f"Cheapest passing {stage}: {outcome}")
    print(f"Report written to {args.output}")
    return int(bool(input_errors) or not any(row["valid_json"] for row in rows))


if __name__ == "__main__":
    sys.exit(main())
