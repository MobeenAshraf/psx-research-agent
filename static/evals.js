"use strict";

const data = JSON.parse(document.getElementById("evaluation-data").textContent);
const results = document.getElementById("results");
const tabs = Array.from(document.querySelectorAll("[role='tab']"));
const integer = new Intl.NumberFormat("en-US", {maximumFractionDigits: 0});
const decimal = new Intl.NumberFormat("en-US", {maximumFractionDigits: 6});
const labels = {
    "google/gemini-3-flash-preview": "Gemini 3 Flash Preview",
    "google/gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "google/gemini-3.5-flash-lite": "Gemini 3.5 Flash Lite",
    "google/gemini-3.8-flash": "Gemini 3.8 Flash",
    "google/gemini-4-hydrogen": "Gemini 4 Hydrogen",
    "openai/gpt-4o": "GPT-4o",
    "openai/gpt-6-luna": "GPT-6 Luna",
    "openai/gpt-6.2-sol": "GPT-6.2 Sol",
    "deepseek/deepseek-v4.1-flash-1017": "DeepSeek V4.1 Flash 1017",
    "anthropic/claude-haiku-5.5": "Claude Haiku 5.5",
};
const cases = {
    "lucky-cement-sep2026-results-scan": ["LUCK", "Lucky Cement", "Scanned PDF · September 2026 quarter · consolidated statements"],
    "indus-motor-sep2026-quarter": ["INDU", "Indus Motor", "Text PDF · September 2026 quarter · standalone statements"],
    "hum-fy2025-unconsolidated": ["HUM", "HUM Network", "FY2025 annual report · standalone statements"],
    "colgate-fy2025": ["COLG", "Colgate-Palmolive Pakistan", "FY2025 annual report · scope, currency and cash flow"],
    "analysis-payout-and-segments": ["SIM", "Payout and income mix", "Known capex, dividend coverage, valuation and segment inputs"],
    "analysis-undisclosed-breakdowns": ["SIM", "Undisclosed detail", "Missing note breakdowns and facts the model should leave unknown"],
    "analysis-lucky-cement-sep2026": ["LUCK", "Lucky Cement filing inputs", "Frozen consolidated figures, computed cash flow and payout, and no inferred segment split"],
    "decision-conflicting-halal-signal": ["SIM", "Conflicting portfolio signals", "Technical strength, investor constraints and conflicting classification signals"],
    "decision-aligned-dividend-profile": ["SIM", "Aligned dividend profile", "Financial and technical evidence with an income-focused investor profile"],
};
const fields = {
    operating_income: "Operating profit",
    operating_income_previous: "Prior-year operating profit",
    total_debt: "Total borrowings",
    shares_outstanding: "Period-end shares",
    total_liabilities: "Total liabilities",
    "other_income_breakdown.#count": "Itemized other-income rows",
    "calculated.free_cash_flow": "Free cash flow",
};
const introductions = {
    extraction: ["PDF extraction", "The same pinned files went to each model. Checks compare the returned fields to the filing, including amounts, units, reporting scope and fields the model should leave empty."],
    analysis: ["Financial analysis", "Models received frozen financial data and Python-calculated ratios. Checks covered factual consistency, missing disclosures and whether the analysis preserved the supplied numbers."],
    decision: ["Investment decisions", "Models received the same financial facts, technical signals and investor profile. Checks covered the expected recommendation, confidence and the required structured explanations."],
    calculations: ["Python calculations", "Independently checked filing inputs go through the same Python formulas used by the app. These tests use no language model and make no API calls."],
};

function esc(value) {
    return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function modelName(id) { return labels[id] ?? id; }
function caseInfo(id) { return cases[id] ?? ["CASE", id, ""]; }
function fieldName(path) {
    if (fields[path]) return fields[path];
    const words = path.replace(/^(normalized|calculated)\./, "").replaceAll("_", " ").replaceAll(".", " › ");
    return words[0].toUpperCase() + words.slice(1);
}

function number(value) {
    if (value === null || value === undefined) return "—";
    return typeof value === "number" ? decimal.format(value) : String(value);
}

function heading(title, description = "") {
    return `<div class="section-heading"><h2>${esc(title)}</h2>${description ? `<p>${esc(description)}</p>` : ""}</div>`;
}

function metrics(entries) {
    return `<dl class="metrics">${entries.map(([label, value]) =>
        `<div class="metric"><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>`;
}

function table(label, headers, rows, style, note = "") {
    return `<div class="panel"><div class="table-scroll" role="region" aria-label="${esc(label)}" tabindex="0">
        <table class="${style}"><thead><tr>${headers.map(item => `<th scope="col">${esc(item)}</th>`).join("")}</tr></thead>
        <tbody>${rows.join("")}</tbody></table></div>${note ? `<p class="table-note">${esc(note)}</p>` : ""}</div>`;
}

function caseCards(runCases) {
    return `<div class="case-grid">${runCases.map(({id, pdf_url: url}) => {
        const [symbol, title, description] = caseInfo(id);
        const link = typeof url === "string" && url.startsWith("https://")
            ? `<a href="${esc(url)}" target="_blank" rel="noopener">Open filing ↗</a>` : "";
        return `<article class="panel case-card"><span class="case-mark">${esc(symbol)}</span>
            <div><h3>${esc(title)}</h3><p>${esc(description)}</p>${link}</div></article>`;
    }).join("")}</div>`;
}

function modelTable(run, {caseColumns = true, note = ""} = {}) {
    const headers = ["Model", "Cases passed", "Check score"];
    if (caseColumns) headers.push(...run.cases.map(({id}) => caseInfo(id)[0] === "SIM" ? caseInfo(id)[1] : caseInfo(id)[0]));
    headers.push("Billed total", "Median time");
    const rows = run.models.map(model => {
        const percent = Math.round(model.mean_score * 100);
        const caseCells = caseColumns ? run.cases.map(({id}) => {
            const trial = model.cases.find(item => item.id === id);
            if (!trial?.valid_json) return '<td class="muted">No JSON</td>';
            const count = `${trial.checks_passed}/${trial.checks_total}`;
            return `<td class="numbers ${trial.passed ? "cell-match" : "cell-miss"}">${count}</td>`;
        }).join("") : "";
        const price = model.total_cost_usd === null ? "—" : `$${model.total_cost_usd.toFixed(5)}`;
        return `<tr><th scope="row">${esc(modelName(model.model))}</th>
            <td class="numbers ${model.passed === model.trials ? "cell-match" : "cell-miss"}">${model.passed}/${model.trials}</td>
            <td class="numbers"><span class="score"><progress aria-label="Check score" value="${percent}" max="100"></progress>${percent}%</span></td>
            ${caseCells}<td class="numbers">${price}</td><td class="numbers">${model.median_latency_s.toFixed(2)} s</td></tr>`;
    });
    return table("Model results", headers, rows, "model-table", note);
}

function comparisons() {
    return data.comparisons.map(group => {
        const [symbol, name] = caseInfo(group.case);
        const rows = group.findings.map(finding => {
            const values = group.models.map(model => {
                const value = finding.values.find(item => item.model === model);
                if (!value) return '<td class="muted">Unavailable</td>';
                const displayed = value.status === "omitted" ? "Omitted" : value.actual === null ? "null" : number(value.actual);
                const match = value.status === "correct";
                return `<td class="numbers ${match ? "cell-match" : "cell-miss"}">${match ? "" : '<span class="sr-only">Incorrect. </span>'}${esc(displayed)}</td>`;
            }).join("");
            const reasons = [...new Set(finding.values.map(value => value.reason).filter(Boolean))];
            const detail = reasons.length ? `<tr class="finding-detail"><td colspan="${2 + group.models.length}">${esc(reasons.join(" "))}</td></tr>` : "";
            const expected = finding.expected === null ? "null" : number(finding.expected);
            return `<tr><th scope="row">${esc(fieldName(finding.field))}<span class="field-reference">${esc(finding.source)}</span></th>
                <td class="numbers">${esc(expected)}</td>${values}</tr>${detail}`;
        });
        return `<div class="finding-group"><h3 class="subheading">${esc(symbol)} · ${esc(name)}</h3>
            ${table(`${symbol} model field mismatches`, ["Field", "Expected", ...group.models.map(modelName)], rows, "finding-table")}</div>`;
    }).join("");
}

function extraction() {
    const compared = data.comparisons.reduce((sum, group) => sum + group.fields_compared, 0);
    const mismatches = data.comparisons.reduce((sum, group) => sum + group.findings.filter(finding => finding.mismatched_pairs.length).length, 0);
    return `${metrics([["Reports tested", data.extraction.cases.length], ["Checks per model", compared], ["Fields that differed", mismatches]])}
        ${heading("Model results", "Latest three-model run")}
        ${modelTable(data.extraction, {note: "Both Flash models used cached input in this run. Hydrogen did not. A case passes at 90% with all required checks satisfied."})}
        <div class="evaluation-section">${heading("Test filings")}${caseCards(data.extraction.cases)}</div>
        <div class="evaluation-section">${heading("Field mismatches", "Monetary values are in PKR thousands. A null means the filing did not directly report the field.")}${comparisons()}</div>
        <div class="evaluation-section">${heading("Earlier runs")}
            <details class="panel"><summary>LUCK and INDU prompt comparison</summary><div class="detail-body">
                <p class="muted">Flash Preview returned the wrong LUCK operating-profit rows in the previous refined run and correctly extracted them in the latest repeat.</p>
                ${data.scan_repeats.map(run => `<div class="evaluation-section">${heading(run.name === "initial" ? "Initial prompt" : "Refined prompt")}${modelTable(run)}</div>`).join("")}
            </div></details>
            <details class="panel"><summary>Initial three-filing screening</summary><div class="detail-body">
                ${caseCards(data.extraction_screening.cases)}${modelTable(data.extraction_screening)}
            </div></details>
        </div>`;
}

function textStage(stage) {
    const run = data[stage];
    const highest = Math.round(100 * Math.max(...run.models.map(model => model.mean_score)));
    const lucky = stage === "analysis" ? `<div class="evaluation-section">${heading("LUCK filing follow-up", "A separate run using the issuer’s reported September 2026 figures.")}
        ${caseCards(data.lucky_analysis.cases)}<div class="evaluation-section">${modelTable(data.lucky_analysis, {caseColumns: false})}</div></div>` : "";
    return `${metrics([["Models compared", run.models.length], ["Cases per model", run.cases.length], ["Best check score", `${highest}%`]])}
        ${heading("Model results", "Initial screening on synthetic cases")}
        ${modelTable(run, {note: "Check score shows average check accuracy. A case passes at 90% with all required checks satisfied."})}
        <div class="evaluation-section">${heading("Test cases")}${caseCards(run.cases)}</div>${lucky}`;
}

function calculations() {
    const runs = data.calculations;
    const checks = runs.flatMap(run => run.checks);
    const passed = checks.filter(check => check.passed).length;
    const reconciled = runs.filter(run => run.validation.is_valid).length;
    const rows = runs.map(run => {
        const [symbol, title] = caseInfo(run.case);
        const correct = run.checks.filter(check => check.passed).length;
        const fcf = run.checks.find(check => check.field === "calculated.free_cash_flow");
        return `<tr><th scope="row">${esc(symbol)} · ${esc(title)}</th><td class="numbers ${run.passed ? "cell-match" : "cell-miss"}">${correct}/${run.checks.length}</td>
            <td>${run.validation.is_valid ? "Reconciled" : "Review required"}</td><td class="numbers">PKR ${integer.format(fcf.actual)}</td></tr>`;
    });
    return `${metrics([["Checks passed", `${passed}/${checks.length}`], ["Reports reconciled", `${reconciled}/${runs.length}`], ["Model calls", 0]])}
        ${heading("Calculation results", "Quarterly figures from the September 2026 filings")}
        ${table("Calculation results", ["Fixture", "Checks passed", "Balance and cash flow", "Free cash flow"], rows, "compact",
        "Tests use independently verified statement figures, separately supplied share counts and illustrative quotes where needed.")}
        <div class="evaluation-section">${heading("Expected and calculated values")}
            ${runs.map(run => {
                const detail = run.checks.map(check => `<tr><th scope="row">${esc(fieldName(check.field))}</th>
                    <td class="numbers">${esc(number(check.expected))}</td><td class="numbers">${esc(number(check.actual))}</td>
                    <td class="${check.passed ? "cell-match" : "cell-miss"}">${check.passed ? "Pass" : "Fail"}</td></tr>`);
                const symbol = caseInfo(run.case)[0];
                return `<details class="panel"><summary>${esc(symbol)} · ${run.checks.length} checks</summary>
                    <div class="detail-body">${table(`${symbol} calculation details`, ["Metric", "Expected", "Calculated", "Result"], detail, "compact")}</div></details>`;
            }).join("")}</div>`;
}

function selectStage(stage) {
    const selected = tabs.find(tab => tab.dataset.stage === stage) ?? tabs[0];
    const active = selected.dataset.stage;
    for (const tab of tabs) {
        tab.setAttribute("aria-selected", String(tab === selected));
        tab.tabIndex = tab === selected ? 0 : -1;
    }
    results.setAttribute("aria-labelledby", selected.id);
    const [title, description] = introductions[active];
    const content = active === "extraction" ? extraction() : active === "calculations" ? calculations() : textStage(active);
    results.innerHTML = `<div class="stage-intro"><h2>${esc(title)}</h2><p>${esc(description)}</p></div>${content}`;
}

function activate(tab) {
    const stage = tab.dataset.stage;
    history.replaceState(null, "", `#${stage}`);
    selectStage(stage);
}

for (const [index, tab] of tabs.entries()) {
    tab.addEventListener("click", () => activate(tab));
    tab.addEventListener("keydown", event => {
        const targets = {ArrowLeft: (index + tabs.length - 1) % tabs.length, ArrowRight: (index + 1) % tabs.length, Home: 0, End: tabs.length - 1};
        if (!(event.key in targets)) return;
        event.preventDefault();
        const target = tabs[targets[event.key]];
        activate(target);
        target.focus();
    });
}
const date = document.getElementById("run-date");
date.dateTime = data.run_at;
date.textContent = new Intl.DateTimeFormat("en-GB", {dateStyle: "medium", timeZone: "UTC"}).format(new Date(data.run_at));
window.addEventListener("hashchange", () => selectStage(location.hash.slice(1)));
selectStage(location.hash.slice(1));
