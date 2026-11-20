import json

from bs4 import BeautifulSoup

from routes.evaluations import read_evaluations


def test_evaluation_page_loads_all_stages_from_stored_results():
    response = read_evaluations()
    assert response.status_code == 200
    page = BeautifulSoup(response.body, "html.parser")
    data = json.loads(page.select_one("#evaluation-data").string)

    latest = data["extraction"]
    hydrogen = next(model for model in latest["models"] if model["model"] == "google/gemini-4-hydrogen")
    assert hydrogen["passed"] == 2
    assert sum(case["checks_passed"] for case in hydrogen["cases"]) == 104
    assert sum(len(group["findings"]) for group in data["comparisons"]) == 6
    assert data["scan_repeats"][0]["models"][0]["cases"][0]["checks_passed"] == 53
    assert len(data["analysis"]["models"]) == len(data["decision"]["models"]) == 5
    assert sum(len(run["checks"]) for run in data["calculations"]) == 61
    assert all(run["passed"] for run in data["calculations"])
    assert b"raw_output" not in response.body
