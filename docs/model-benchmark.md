# Model benchmark

The benchmark compares OpenRouter models separately for PDF extraction, investor analysis, and the final investment decision. Each candidate sees the same input and is compared with the baseline for that stage. The runner uses the configured `EXTRACTION_MODEL`, `ANALYSIS_MODEL`, and `DECISION_MODEL` when set, or the original screening baselines for reproducibility. Production uses GPT-6 Luna for analysis and DeepSeek V4.1 Flash 1017 for decisions by default.

## Run it

From the repository root, after installing the app dependencies:

```bash
uv run python -m evals.model_benchmark
uv run python -m evals.model_benchmark --live --repeats 3
```

The first command prepares the cases and prints the run matrix. The second uses `OPENROUTER_API_KEY` from the environment or the root `.env` and makes up to 123 billable requests with the default matrix. Use one repeat for a 41-request smoke run. To test a single candidate against the baseline:

```bash
uv run python -m evals.model_benchmark --live --stage analysis --model openai/gpt-6-luna
```

Use `--case indus-motor-sep2026-quarter` to test just the Indus Motor filing. If a selected PDF cannot be downloaded, the runner records the input error, finishes the other cases, and withholds the affected stage's winner.

The starter PDFs are stored in `evals/pdfs/` and pinned by SHA-256. A fresh checkout can run the default suite without downloading any reports. For custom cases that supply only a public PDF URL, the live runner downloads once to the Git-ignored `data/evals/pdfs/` directory. Use `--pdf-cache /path/to/shared/pdfs` to share those downloaded fixtures between workspaces.

## Candidates and list prices

Prices are OpenRouter's advertised USD per million input and output tokens, checked November 20, 2026. Provider selection, cached inputs, reasoning tokens, and PDF parsing can affect the cost of a request. The benchmark uses the cost OpenRouter reports for each response. [OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting)

| Stage | Model | Input | Output | Role |
| --- | --- | ---: | ---: | --- |
| Extraction | [Gemini 3 Flash Preview](https://openrouter.ai/google/gemini-3-flash-preview) | $0.50 | $3.00 | Repository baseline |
| Extraction | [Gemini 3.5 Flash Lite](https://openrouter.ai/google/gemini-3.5-flash-lite) | $0.30 | $2.50 | Lowest listed price in the PDF comparison |
| Extraction | [Gemini 3.8 Flash](https://openrouter.ai/google/gemini-3.8-flash) | $0.75 | $3.75 | Discounted rate |
| Extraction | [Gemini 4 Hydrogen](https://openrouter.ai/google/gemini-4-hydrogen) | $1.50 | $7.50 | Newer PDF candidate |
| Analysis and decision | [GPT-4o](https://openrouter.ai/openai/gpt-4o) | $2.50 | $10.00 | Original screening baseline |
| Analysis and decision | [DeepSeek V4.1 Flash 1017](https://openrouter.ai/deepseek/deepseek-v4.1-flash-1017) | $0.036 | $0.50 | Lowest listed input price in the text comparison |
| Analysis and decision | [Claude Haiku 5.5](https://openrouter.ai/anthropic/claude-haiku-5.5) | $0.10 | $0.50 | Low-cost candidate |
| Analysis and decision | [GPT-6 Luna](https://openrouter.ai/openai/gpt-6-luna) | $0.10 | $0.50 | Low-cost candidate |
| Analysis and decision | [GPT-6.2 Sol](https://openrouter.ai/openai/gpt-6.2-sol) | $2.00 | $10.00 | Newer candidate priced close to baseline |

## Interpret the report

The terminal shows pass rate, mean check score, JSON success rate, median request latency, and billed cost per passing trial. `data/evals/model-benchmark.json` also records each response, which checks passed, the model and provider reported by OpenRouter, token usage, and each candidate's score and cost difference from the baseline. Use `--output` to retain multiple runs.

A trial passes if it produces a JSON object, scores at least 90% on its checks, and passes every critical check. Cost per pass includes the billed cost of failed trials. Missing billing data makes a model's cost comparison unavailable. The cheapest passing model must pass every case and repeat in its stage. Ties go to the lower median latency.

The suite has four published PDF filings, one analysis case based on Lucky Cement's reported figures, and four synthetic cases. The PDF checks cover units, comparative periods, cash flow, and the distinction between standalone and consolidated statements. Lucky Cement adds a scanned filing with a separately reported foreign-exchange effect and a distinction between dividends paid and dividends recommended. [Colgate-Palmolive FY2025 report](https://colgate.com.pk/wp-content/uploads/2025/09/CPPL-Annual-Report-2025.pdf) · [HUM Network FY2025 report](https://humnetwork.tv/wp-content/uploads/2025/09/Annual%20Report%20HUM.pdf) · [Indus Motor quarterly report](https://toyota-indus.com/wp-content/uploads/2026/10/Financial-Report-for-the-Quarter-ended-September-30-2026.pdf) · [Lucky Cement financial results](https://assets.lucky-cement.com/0000204815_Financial_Results_30_09_2026_2_8c1a80dbf9.pdf)

This is a screening suite. The checks sample structured outputs and selected facts. Review prose and borderline cases manually and confirm the shortlist on a larger mix of held-out reports, including quarterly statements and scans, before changing app defaults.

Before promoting a PDF candidate, verify it through the app's financial analysis flow. The current PDF model allowlist in `financial/config/model_config.py` controls whether a selected model receives the PDF.

The benchmark shares the app's prompt construction and submits one PDF in the user message, with explicit scope and units for each report. It requires JSON-mode routing and scores strict JSON. It uses the provider's default sampling settings unless you pass `--temperature`. Only set a fixed temperature when every model in the run supports it. If the local decision schema is absent, it uses a benchmark schema based on the fields the app displays.

## Add cases

Use `--cases` with a JSON file following [the starter cases](../evals/cases.json). Give each case a unique ID and a stage. Extraction supports a public `pdf_url` or local `pdf_path` relative to the case file. Analysis takes frozen extracted data and calculated metrics. Decision takes a frozen profile, technical analysis, financial report, and index membership. Expected values use dot paths into the returned object, including array positions such as `income_composition.segments.0.revenue_pct`. Optional checks cover absolute numeric tolerances, nonempty fields, and regular expressions. Name mandatory paths in `critical`.

```bash
python3 -m unittest tests.test_model_benchmark
```

The [first live screening results](../evals/results/2026-11-20-screening.json) record the prompt fingerprints and cases used for that run. The current extraction cases also check reporting scope, period, and unit scale. Use the current benchmark for new model comparisons.

The [Lucky Cement run](../evals/results/2026-11-20-lucky-cement.json) records the scan's extraction checks and the three-model analysis comparison.
