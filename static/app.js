const API_BASE = '/api';

let currentEventSource = null;

document.addEventListener('DOMContentLoaded', () => {
    const stockInput = document.getElementById('stockInput');
    const technicalBtn = document.getElementById('technicalBtn');
    const financialBtn = document.getElementById('financialBtn');
    
    stockInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            technicalBtn.click();
        }
    });
    
    technicalBtn.addEventListener('click', handleTechnicalAnalysis);
    financialBtn.addEventListener('click', handleFinancialAnalysis);
});

function getSymbol() {
    const input = document.getElementById('stockInput');
    const symbol = input.value.trim().toUpperCase();
    
    if (!symbol) {
        showError('Please enter a stock symbol');
        return null;
    }
    
    return symbol;
}

function showError(message) {
    hideAllSections();
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
    errorSection.classList.add('fade-in');
}

function hideAllSections() {
    document.getElementById('progressSection').classList.add('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('errorSection').classList.add('hidden');
}

function showLoading(buttonId, spinnerId, textId) {
    const button = document.getElementById(buttonId);
    const spinner = document.getElementById(spinnerId);
    const text = document.getElementById(textId);
    
    button.disabled = true;
    spinner.classList.remove('hidden');
    text.textContent = 'Loading...';
}

function hideLoading(buttonId, spinnerId, textId, originalText) {
    const button = document.getElementById(buttonId);
    const spinner = document.getElementById(spinnerId);
    const text = document.getElementById(textId);
    
    button.disabled = false;
    spinner.classList.add('hidden');
    text.textContent = originalText;
}

async function handleTechnicalAnalysis() {
    const symbol = getSymbol();
    if (!symbol) return;
    
    hideAllSections();
    showLoading('technicalBtn', 'technicalSpinner', 'technicalBtnText');
    
    try {
        const response = await fetch(`${API_BASE}/technical-analysis`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symbol }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Analysis failed');
        }
        
        const data = await response.json();
        displayTechnicalResults(data);
    } catch (error) {
        showError(`Technical analysis failed: ${error.message}`);
    } finally {
        hideLoading('technicalBtn', 'technicalSpinner', 'technicalBtnText', 'Technical Analysis');
    }
}

function displayTechnicalResults(data) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsContent = document.getElementById('resultsContent');
    
    if (data.detailed_format) {
        resultsTitle.classList.add('hidden');
        resultsContent.textContent = data.detailed_format;
    } else {
        showError('Detailed format not available. Please try again.');
        return;
    }
    
    resultsSection.classList.remove('hidden');
    resultsSection.classList.add('fade-in');
}

async function handleFinancialAnalysis() {
    const symbol = getSymbol();
    if (!symbol) return;
    
    hideAllSections();
    showLoading('financialBtn', 'financialSpinner', 'financialBtnText');
    
    try {
        const checkResponse = await fetch(`${API_BASE}/financial-analysis/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symbol }),
        });
        
        if (!checkResponse.ok) {
            throw new Error('Failed to check for existing report');
        }
        
        const checkData = await checkResponse.json();
        
        if (checkData.status === 'exists') {
            hideLoading('financialBtn', 'financialSpinner', 'financialBtnText', 'Financial Analysis');
            displayFinancialResults(checkData);
            return;
        }
        
        const runResponse = await fetch(`${API_BASE}/financial-analysis/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symbol }),
        });
        
        if (!runResponse.ok) {
            const error = await runResponse.json();
            throw new Error(error.detail || 'Failed to start analysis');
        }
        
        hideLoading('financialBtn', 'financialSpinner', 'financialBtnText', 'Financial Analysis');
        
        showProgressSection();
        connectToStream(symbol);
    } catch (error) {
        showError(`Financial analysis failed: ${error.message}`);
        hideLoading('financialBtn', 'financialSpinner', 'financialBtnText', 'Financial Analysis');
    }
}

function showProgressSection() {
    const progressSection = document.getElementById('progressSection');
    progressSection.classList.remove('hidden');
    
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressStep = document.getElementById('progressStep');
    const stateUpdates = document.getElementById('stateUpdates');
    
    progressBar.style.width = '0%';
    progressPercent.textContent = '0%';
    progressStep.textContent = 'Initializing...';
    stateUpdates.innerHTML = '';
}

function connectToStream(symbol) {
    if (currentEventSource) {
        currentEventSource.close();
    }
    
    const eventSource = new EventSource(`${API_BASE}/financial-analysis/stream/${symbol}`);
    currentEventSource = eventSource;
    
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressStep = document.getElementById('progressStep');
    const stateUpdates = document.getElementById('stateUpdates');
    
    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'state') {
                progressBar.style.width = `${data.progress}%`;
                progressPercent.textContent = `${data.progress}%`;
                
                const stepName = formatStepName(data.step);
                progressStep.textContent = stepName;
                
                const stateDiv = document.createElement('div');
                stateDiv.className = 'fade-in p-3 bg-gray-50 rounded border border-gray-200';
                stateDiv.innerHTML = `
                    <div class="font-semibold text-gray-800 mb-1">${stepName}</div>
                    <div class="text-xs text-gray-600">${data.timestamp || ''}</div>
                    <details class="mt-2">
                        <summary class="cursor-pointer text-sm text-blue-600 hover:text-blue-800">View state data</summary>
                        <pre class="mt-2 text-xs bg-white p-2 rounded border overflow-auto max-h-40">${JSON.stringify(data.data, null, 2)}</pre>
                    </details>
                `;
                stateUpdates.appendChild(stateDiv);
                stateUpdates.scrollTop = stateUpdates.scrollHeight;
            } else if (data.type === 'complete') {
                progressBar.style.width = '100%';
                progressPercent.textContent = '100%';
                progressStep.textContent = 'Complete!';
                
                if (data.final_state && data.final_state.final_report) {
                    displayFinancialResults({
                        status: 'complete',
                        result: data.final_state.final_report,
                        symbol: symbol,
                        token_usage: data.token_usage || data.final_state.token_usage
                    });
                } else {
                    fetchFinalResult(symbol);
                }
                
                eventSource.close();
                currentEventSource = null;
            } else if (data.type === 'error') {
                showError(`Analysis error: ${data.error || 'Unknown error'}`);
                eventSource.close();
                currentEventSource = null;
            } else if (data.type === 'timeout') {
                showError('Analysis timeout - please try again');
                eventSource.close();
                currentEventSource = null;
            }
        } catch (error) {
            console.error('Error parsing SSE data:', error);
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        if (eventSource.readyState === EventSource.CLOSED) {
            eventSource.close();
            currentEventSource = null;
        }
    };
}

function formatStepName(step) {
    const stepNames = {
        '00_initial': 'Initializing',
        '01_extract': 'Extracting Data',
        '02_calculate': 'Calculating Metrics',
        '03_validate': 'Validating Data',
        '04_analyze': 'Analyzing',
        '05_format': 'Formatting Report',
        '99_final': 'Complete'
    };
    return stepNames[step] || step;
}

async function fetchFinalResult(symbol) {
    try {
        const response = await fetch(`${API_BASE}/financial-analysis/result/${symbol}`);
        if (!response.ok) {
            throw new Error('Failed to fetch final result');
        }
        const data = await response.json();
        displayFinancialResults(data);
    } catch (error) {
        showError(`Failed to fetch final result: ${error.message}`);
    }
}

function displayFinancialResults(data) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsContent = document.getElementById('resultsContent');
    
    let content = '';
    
    if (data.result) {
        content = data.result;
    } else if (data.final_report) {
        content = data.final_report;
    } else {
        content = 'No report available';
    }
    
    resultsTitle.textContent = `Financial Analysis: ${data.symbol || 'Unknown'}`;
    resultsTitle.classList.remove('hidden');
    resultsContent.textContent = content;
    resultsSection.classList.remove('hidden');
    resultsSection.classList.add('fade-in');
    
    if (data.states) {
        const stateInfo = Object.keys(data.states).length > 0 
            ? `\n\n(Generated from ${Object.keys(data.states).length} analysis steps)`
            : '';
        resultsContent.textContent += stateInfo;
    }
    
    const tokenUsage = data.token_usage || (data.final_state && data.final_state.token_usage) || (data.state && data.state.token_usage);
    if (tokenUsage) {
        displayTokenUsage(tokenUsage);
    }
}

function displayTokenUsage(tokenUsage) {
    const resultsSection = document.getElementById('resultsSection');
    
    let existingTokenUsage = document.getElementById('tokenUsageCard');
    if (existingTokenUsage) {
        existingTokenUsage.remove();
    }
    
    const tokenUsageCard = document.createElement('div');
    tokenUsageCard.id = 'tokenUsageCard';
    tokenUsageCard.className = 'bg-gray-800 rounded-lg shadow-lg p-6 mb-4 fade-in border border-gray-700';
    
    const steps = tokenUsage.steps || {};
    const cumulative = tokenUsage.cumulative || {};
    
    let html = '<h3 class="text-lg font-semibold text-gray-100 mb-4 flex items-center gap-2">';
    html += '<svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>';
    html += 'Token Usage</h3>';
    
    if (Object.keys(steps).length > 0) {
        html += '<div class="mb-6">';
        html += '<h4 class="text-sm font-semibold text-gray-300 mb-3">Per-Step Breakdown</h4>';
        html += '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">';
        
        const stepNames = {
            'extract': 'Extract Step',
            'analyze': 'Analyze Step'
        };
        
        for (const [stepKey, stepData] of Object.entries(steps)) {
            const stepName = stepNames[stepKey] || stepKey.charAt(0).toUpperCase() + stepKey.slice(1);
            html += '<div class="bg-gray-700 rounded-lg p-4 border border-gray-600">';
            html += `<div class="text-sm font-medium text-gray-200 mb-3">${stepName}</div>`;
            html += '<div class="space-y-2">';
            html += `<div class="flex justify-between items-center"><span class="text-xs text-gray-400">Prompt Tokens:</span><span class="text-sm font-semibold text-blue-400">${formatNumber(stepData.prompt_tokens || 0)}</span></div>`;
            html += `<div class="flex justify-between items-center"><span class="text-xs text-gray-400">Completion Tokens:</span><span class="text-sm font-semibold text-green-400">${formatNumber(stepData.completion_tokens || 0)}</span></div>`;
            html += `<div class="flex justify-between items-center pt-2 border-t border-gray-600"><span class="text-xs text-gray-300 font-medium">Total:</span><span class="text-sm font-bold text-gray-100">${formatNumber(stepData.total_tokens || 0)}</span></div>`;
            html += '</div></div>';
        }
        
        html += '</div></div>';
    }
    
    if (cumulative.total_tokens > 0) {
        html += '<div class="bg-gradient-to-r from-gray-700 to-gray-600 rounded-lg p-5 border-2 border-blue-500">';
        html += '<h4 class="text-sm font-semibold text-gray-200 mb-4">Cumulative Totals</h4>';
        html += '<div class="grid grid-cols-3 gap-4">';
        html += '<div class="text-center"><div class="text-xs text-gray-400 mb-1">Prompt Tokens</div><div class="text-2xl font-bold text-blue-400">' + formatNumber(cumulative.prompt_tokens || 0) + '</div></div>';
        html += '<div class="text-center"><div class="text-xs text-gray-400 mb-1">Completion Tokens</div><div class="text-2xl font-bold text-green-400">' + formatNumber(cumulative.completion_tokens || 0) + '</div></div>';
        html += '<div class="text-center"><div class="text-xs text-gray-300 mb-1 font-medium">Total Tokens</div><div class="text-3xl font-bold text-gray-100">' + formatNumber(cumulative.total_tokens || 0) + '</div></div>';
        html += '</div></div>';
    }
    
    tokenUsageCard.innerHTML = html;
    resultsSection.appendChild(tokenUsageCard);
}

function formatNumber(num) {
    return num.toLocaleString('en-US');
}

