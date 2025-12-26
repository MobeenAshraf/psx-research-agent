const API_BASE = '/api';
const USER_PROFILE_KEY = 'psx_user_profile';

let currentEventSource = null;

const DEFAULT_PROFILE = {
    age: 30,
    objectives: {
        primary_goal: "Grow a halal stock portfolio as a core part of FIRE (financial independence, retire early).",
        quarterly_dividend_income_target_pkr: 50000,
        time_horizon_years: 3,
        treat_as_emergency_fund: false
    },
    constraints: {
        halal_only: true,
        leverage_allowed: false,
        derivatives_allowed: false
    },
    current_portfolio: {
        symbols: [],
        past_holdings: [],
        watchlist: []
    },
    risk_profile: {
        risk_tolerance: "moderate",
        focus: "Stable, growing dividend income and/or long-term capital appreciation in halal stocks.",
        preference_for_dividends: "high"
    }
};

function trackEvent(eventName, eventParams = {}) {
    try {
        if (typeof gtag !== 'undefined') {
            gtag('event', eventName, eventParams);
        } else if (window.dataLayer) {
            window.dataLayer.push({
                'event': eventName,
                ...eventParams
            });
        }
    } catch (error) {
        console.error('[GA4] Error tracking event:', error);
    }
}

const MODEL_PRICING = {
    "google/gemini-3-flash-preview": {
        prompt_tokens_per_million: 0.075,
        completion_tokens_per_million: 0.30
    },
    "google/gemini-3-pro-preview": {
        prompt_tokens_per_million: 0.625,
        completion_tokens_per_million: 1.875
    },
    "openai/gpt-4o": {
        prompt_tokens_per_million: 2.50,
        completion_tokens_per_million: 10.00
    },
    "openai/gpt-4o-mini": {
        prompt_tokens_per_million: 0.15,
        completion_tokens_per_million: 0.60
    }
};

function calculateCost(tokenUsage, modelName) {
    if (!tokenUsage || !modelName) {
        return 0.0;
    }
    
    const pricing = MODEL_PRICING[modelName];
    if (!pricing) {
        return 0.0;
    }
    
    const promptTokens = tokenUsage.prompt_tokens || 0;
    const completionTokens = tokenUsage.completion_tokens || 0;
    
    const promptCost = (promptTokens / 1000000) * pricing.prompt_tokens_per_million;
    const completionCost = (completionTokens / 1000000) * pricing.completion_tokens_per_million;
    
    return round(promptCost + completionCost, 6);
}

function round(value, decimals) {
    return Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals);
}

function calculateCosts(tokenUsage, extractionModel, analysisModel) {
    if (!tokenUsage || !tokenUsage.steps) {
        return {
            extraction_cost: 0.0,
            analysis_cost: 0.0,
            total_cost: 0.0
        };
    }
    
    const extractStep = tokenUsage.steps.extract || {};
    const analyzeStep = tokenUsage.steps.analyze || {};
    
    const extractModel = extractStep.model || extractionModel;
    const analyzeModel = analyzeStep.model || analysisModel;
    
    const extractionCost = calculateCost(extractStep, extractModel);
    const analysisCost = calculateCost(analyzeStep, analyzeModel);
    const totalCost = extractionCost + analysisCost;
    
    return {
        extraction_cost: extractionCost,
        analysis_cost: analysisCost,
        total_cost: totalCost,
        extracting_token: extractStep.total_tokens || 0,
        analysis_token: analyzeStep.total_tokens || 0
    };
}

document.addEventListener('DOMContentLoaded', () => {
    const stockInput = document.getElementById('stockInput');
    const technicalBtn = document.getElementById('technicalBtn');
    const financialBtn = document.getElementById('financialBtn');
    const llmDecisionBtn = document.getElementById('llmDecisionBtn');
    
    stockInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const symbol = stockInput.value.trim().toUpperCase();
            if (symbol) {
                trackEvent('stock_symbol_entered', {
                    stock_symbol: symbol,
                    method: 'enter_key'
                });
            }
            technicalBtn.click();
        }
    });
    
    document.getElementById('extractionModel').addEventListener('change', (e) => {
        trackEvent('model_selected', {
            model_type: 'extraction',
            model_name: e.target.value
        });
    });
    
    document.getElementById('analysisModel').addEventListener('change', (e) => {
        trackEvent('model_selected', {
            model_type: 'analysis',
            model_name: e.target.value
        });
    });
    
    technicalBtn.addEventListener('click', handleTechnicalAnalysis);
    financialBtn.addEventListener('click', handleFinancialAnalysis);
    llmDecisionBtn.addEventListener('click', handleLLMDecision);
    
    initializeProfileModal();
    updateClearButtonVisibility();
});

function hasCustomProfile() {
    return localStorage.getItem(USER_PROFILE_KEY) !== null;
}

function updateClearButtonVisibility() {
    const clearBtn = document.getElementById('clearProfileBtn');
    if (clearBtn) {
        if (hasCustomProfile()) {
            clearBtn.classList.remove('hidden');
        } else {
            clearBtn.classList.add('hidden');
        }
    }
}

function loadUserProfile() {
    const stored = localStorage.getItem(USER_PROFILE_KEY);
    if (stored) {
        try {
            return JSON.parse(stored);
        } catch {
            return { ...DEFAULT_PROFILE };
        }
    }
    return { ...DEFAULT_PROFILE };
}

function saveUserProfile(profile) {
    localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(profile));
    updateClearButtonVisibility();
}

function clearUserProfile() {
    localStorage.removeItem(USER_PROFILE_KEY);
    updateClearButtonVisibility();
    populateFormFromProfile(DEFAULT_PROFILE);
}

function getUserProfile() {
    return loadUserProfile();
}

function parseSymbolList(str) {
    if (!str || !str.trim()) return [];
    return str.split(',').map(s => s.trim().toUpperCase()).filter(s => s.length > 0);
}

function formatSymbolList(arr) {
    if (!arr || !Array.isArray(arr)) return '';
    return arr.join(', ');
}

function getFormProfile() {
    const goalSelect = document.getElementById('profile-goal');
    const emergencyToggle = document.getElementById('toggle-emergency');
    const halalToggle = document.getElementById('toggle-halal');
    const leverageToggle = document.getElementById('toggle-leverage');
    const derivativesToggle = document.getElementById('toggle-derivatives');
    
    return {
        age: parseInt(document.getElementById('profile-age').value) || 30,
        objectives: {
            primary_goal: goalSelect.value,
            quarterly_dividend_income_target_pkr: parseInt(document.getElementById('profile-dividend-target').value) || 50000,
            time_horizon_years: parseInt(document.getElementById('profile-time-horizon').value) || 3,
            treat_as_emergency_fund: emergencyToggle.dataset.value === 'true'
        },
        constraints: {
            halal_only: halalToggle.dataset.value === 'true',
            leverage_allowed: leverageToggle.dataset.value === 'true',
            derivatives_allowed: derivativesToggle.dataset.value === 'true'
        },
        current_portfolio: {
            symbols: parseSymbolList(document.getElementById('profile-symbols').value),
            past_holdings: parseSymbolList(document.getElementById('profile-past-holdings').value),
            watchlist: parseSymbolList(document.getElementById('profile-watchlist').value)
        },
        risk_profile: {
            risk_tolerance: document.getElementById('profile-risk-tolerance').value,
            focus: document.getElementById('profile-focus').value,
            preference_for_dividends: document.getElementById('profile-dividend-pref').value
        }
    };
}

function populateFormFromProfile(profile) {
    document.getElementById('profile-age').value = profile.age || 30;
    
    const goalSelect = document.getElementById('profile-goal');
    const goalValue = profile.objectives?.primary_goal || DEFAULT_PROFILE.objectives.primary_goal;
    for (let i = 0; i < goalSelect.options.length; i++) {
        if (goalSelect.options[i].value === goalValue) {
            goalSelect.selectedIndex = i;
            break;
        }
    }
    
    document.getElementById('profile-dividend-target').value = profile.objectives?.quarterly_dividend_income_target_pkr || 50000;
    
    const timeHorizon = profile.objectives?.time_horizon_years || 3;
    document.getElementById('profile-time-horizon').value = timeHorizon;
    document.getElementById('time-horizon-value').textContent = timeHorizon;
    
    setToggleState('toggle-emergency', profile.objectives?.treat_as_emergency_fund || false);
    setToggleState('toggle-halal', profile.constraints?.halal_only !== false);
    setToggleState('toggle-leverage', profile.constraints?.leverage_allowed || false);
    setToggleState('toggle-derivatives', profile.constraints?.derivatives_allowed || false);
    
    document.getElementById('profile-symbols').value = formatSymbolList(profile.current_portfolio?.symbols);
    document.getElementById('profile-past-holdings').value = formatSymbolList(profile.current_portfolio?.past_holdings);
    document.getElementById('profile-watchlist').value = formatSymbolList(profile.current_portfolio?.watchlist);
    
    const riskSelect = document.getElementById('profile-risk-tolerance');
    riskSelect.value = profile.risk_profile?.risk_tolerance || 'moderate';
    
    document.getElementById('profile-focus').value = profile.risk_profile?.focus || DEFAULT_PROFILE.risk_profile.focus;
    
    const divPrefSelect = document.getElementById('profile-dividend-pref');
    divPrefSelect.value = profile.risk_profile?.preference_for_dividends || 'high';
}

function setToggleState(toggleId, isActive) {
    const toggle = document.getElementById(toggleId);
    if (toggle) {
        toggle.dataset.value = isActive ? 'true' : 'false';
        if (isActive) {
            toggle.classList.add('active');
        } else {
            toggle.classList.remove('active');
        }
    }
}

function initializeProfileModal() {
    const modal = document.getElementById('profileModal');
    const settingsBtn = document.getElementById('settingsBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const cancelProfileBtn = document.getElementById('cancelProfileBtn');
    const saveProfileBtn = document.getElementById('saveProfileBtn');
    const clearProfileBtn = document.getElementById('clearProfileBtn');
    const modalBackdrop = document.getElementById('modalBackdrop');
    const timeHorizonSlider = document.getElementById('profile-time-horizon');
    const timeHorizonValue = document.getElementById('time-horizon-value');
    
    settingsBtn.addEventListener('click', openProfileModal);
    closeModalBtn.addEventListener('click', closeProfileModal);
    cancelProfileBtn.addEventListener('click', closeProfileModal);
    modalBackdrop.addEventListener('click', closeProfileModal);
    
    saveProfileBtn.addEventListener('click', () => {
        const profile = getFormProfile();
        saveUserProfile(profile);
        
        const checkmark = document.getElementById('saveCheckmark');
        const btnText = saveProfileBtn.querySelector('span');
        checkmark.classList.remove('hidden');
        btnText.textContent = 'Saved!';
        saveProfileBtn.classList.add('save-success');
        
        setTimeout(() => {
            checkmark.classList.add('hidden');
            btnText.textContent = 'Save Profile';
            saveProfileBtn.classList.remove('save-success');
            closeProfileModal();
        }, 1000);
        
        trackEvent('profile_saved', { has_custom_profile: true });
    });
    
    clearProfileBtn.addEventListener('click', () => {
        if (confirm('Reset your investor profile to defaults?')) {
            clearUserProfile();
            trackEvent('profile_cleared');
        }
    });
    
    timeHorizonSlider.addEventListener('input', (e) => {
        timeHorizonValue.textContent = e.target.value;
    });
    
    document.querySelectorAll('.toggle-switch').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const isActive = toggle.dataset.value === 'true';
            setToggleState(toggle.id, !isActive);
        });
    });
    
    document.querySelectorAll('.profile-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            
            document.querySelectorAll('.profile-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            closeProfileModal();
        }
    });
}

function openProfileModal() {
    const modal = document.getElementById('profileModal');
    const modalContent = modal.querySelector('.modal-content');
    const backdrop = document.getElementById('modalBackdrop');
    
    const profile = loadUserProfile();
    populateFormFromProfile(profile);
    
    document.querySelectorAll('.profile-tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.profile-tab[data-tab="objectives"]').classList.add('active');
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('tab-objectives').classList.add('active');
    
    modal.classList.remove('hidden');
    backdrop.classList.remove('closing');
    modalContent.classList.remove('closing');
    
    document.body.style.overflow = 'hidden';
    
    trackEvent('profile_modal_opened');
}

function closeProfileModal() {
    const modal = document.getElementById('profileModal');
    const modalContent = modal.querySelector('.modal-content');
    const backdrop = document.getElementById('modalBackdrop');
    
    backdrop.classList.add('closing');
    modalContent.classList.add('closing');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }, 150);
}

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
    
    trackEvent('analysis_started', {
        analysis_type: 'technical',
        stock_symbol: symbol
    });
    
    hideAllSections();
    showLoading('technicalBtn', 'technicalSpinner', 'technicalBtnText');
    
    const startTime = Date.now();
    
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
        const duration = Date.now() - startTime;
        
        trackEvent('analysis_completed', {
            analysis_type: 'technical',
            stock_symbol: symbol,
            duration_ms: duration,
            success: true
        });
        
        displayTechnicalResults(data);
    } catch (error) {
        const duration = Date.now() - startTime;
        
        trackEvent('analysis_error', {
            analysis_type: 'technical',
            stock_symbol: symbol,
            duration_ms: duration,
            error_message: error.message
        });
        
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
    
    const extractionModel = document.getElementById('extractionModel').value;
    const analysisModel = document.getElementById('analysisModel').value;
    
    trackEvent('analysis_started', {
        analysis_type: 'financial',
        stock_symbol: symbol,
        extraction_model: extractionModel,
        analysis_model: analysisModel
    });
    
    hideAllSections();
    showLoading('financialBtn', 'financialSpinner', 'financialBtnText');
    
    const startTime = Date.now();
    
    try {
        const checkResponse = await fetch(`${API_BASE}/financial-analysis/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                symbol,
                extraction_model: extractionModel,
                analysis_model: analysisModel
            }),
        });
        
        if (!checkResponse.ok) {
            throw new Error('Failed to check for existing report');
        }
        
        const checkData = await checkResponse.json();
        
        if (checkData.status === 'exists') {
            const duration = Date.now() - startTime;
            
            const costs = calculateCosts(checkData.token_usage, extractionModel, analysisModel);
            
            trackEvent('analysis_completed', {
                analysis_type: 'financial',
                stock_symbol: symbol,
                extraction_model: extractionModel,
                analysis_model: analysisModel,
                duration_ms: duration,
                success: true,
                cached: true,
                extracting_token: costs.extracting_token,
                analysis_token: costs.analysis_token,
                extraction_price: costs.extraction_cost,
                analysis_price: costs.analysis_cost,
                cost: costs.total_cost
            });
            
            hideLoading('financialBtn', 'financialSpinner', 'financialBtnText', 'Financial Analysis');
            displayFinancialResults(checkData);
            return;
        }
        
        const runResponse = await fetch(`${API_BASE}/financial-analysis/run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                symbol,
                extraction_model: extractionModel,
                analysis_model: analysisModel
            }),
        });
        
        if (!runResponse.ok) {
            const error = await runResponse.json();
            throw new Error(error.detail || 'Failed to start analysis');
        }
        
        hideLoading('financialBtn', 'financialSpinner', 'financialBtnText', 'Financial Analysis');
        
        showProgressSection();
        connectToStream(symbol, extractionModel, analysisModel);
    } catch (error) {
        const duration = Date.now() - startTime;
        
        trackEvent('analysis_error', {
            analysis_type: 'financial',
            stock_symbol: symbol,
            extraction_model: extractionModel,
            analysis_model: analysisModel,
            duration_ms: duration,
            error_message: error.message
        });
        
        showError(`Financial analysis failed: ${error.message}`);
        hideLoading('financialBtn', 'financialSpinner', 'financialBtnText', 'Financial Analysis');
    }
}

async function handleLLMDecision() {
    const symbol = getSymbol();
    if (!symbol) return;
    
    const extractionModel = document.getElementById('extractionModel').value;
    const analysisModel = document.getElementById('analysisModel').value;
    const userProfile = getUserProfile();
    
    trackEvent('analysis_started', {
        analysis_type: 'llm_decision',
        stock_symbol: symbol,
        extraction_model: extractionModel,
        analysis_model: analysisModel,
        has_custom_profile: hasCustomProfile()
    });
    
    hideAllSections();
    showLoading('llmDecisionBtn', 'llmDecisionSpinner', 'llmDecisionBtnText');
    
    const startTime = Date.now();
    
    try {
        const response = await fetch(`${API_BASE}/llm-decision`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol,
                extraction_model: extractionModel,
                analysis_model: analysisModel,
                decision_model: 'auto',
                user_profile: userProfile
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Decision generation failed');
        }
        
        const data = await response.json();
        const duration = Date.now() - startTime;
        
        let decisionCost = 0.0;
        if (data.token_usage && data.cost !== undefined) {
            decisionCost = data.cost;
        } else if (data.token_usage) {
            const decisionModel = 'openai/gpt-4o';
            decisionCost = calculateCost(data.token_usage, decisionModel);
        }
        
        trackEvent('analysis_completed', {
            analysis_type: 'llm_decision',
            stock_symbol: symbol,
            extraction_model: extractionModel,
            analysis_model: analysisModel,
            duration_ms: duration,
            success: true,
            decision: data.decision || 'UNKNOWN',
            confidence: data.confidence || 0,
            cost: decisionCost
        });
        
        displayLLMDecisionResults(data);
    } catch (error) {
        const duration = Date.now() - startTime;
        
        trackEvent('analysis_error', {
            analysis_type: 'llm_decision',
            stock_symbol: symbol,
            extraction_model: extractionModel,
            analysis_model: analysisModel,
            duration_ms: duration,
            error_message: error.message
        });
        
        showError(`LLM Decision failed: ${error.message}`);
    } finally {
        hideLoading('llmDecisionBtn', 'llmDecisionSpinner', 'llmDecisionBtnText', 'LLM Decision');
    }
}

function displayLLMDecisionResults(data) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsContent = document.getElementById('resultsContent');
    
    if (data.status !== 'success') {
        showError(data.error || 'Decision generation failed');
        return;
    }
    
    const decision = data.decision || 'UNKNOWN';
    const confidence = data.confidence || 0;
    const summary = data.summary || '';
    const reasons = data.reasons || [];
    const riskNotes = data.risk_notes || [];
    const dividendAnalysis = data.dividend_analysis || '';
    const halalCompliance = data.halal_compliance || '';
    
    const decisionColor = decision === 'BUY' ? 'text-green-400' : 'text-red-400';
    const decisionBg = decision === 'BUY' ? 'bg-green-900' : 'bg-red-900';
    
    let html = `<div class="mb-6 ${decisionBg} p-4 rounded-lg border-2 ${decision === 'BUY' ? 'border-green-500' : 'border-red-500'}">`;
    html += `<h2 class="text-2xl font-bold ${decisionColor} mb-2">Decision: ${decision}</h2>`;
    html += `<p class="text-gray-300 text-sm">Confidence: ${(confidence * 100).toFixed(1)}%</p>`;
    html += `</div>`;
    
    if (summary) {
        html += `<div class="mb-4">`;
        html += `<h3 class="text-lg font-semibold text-gray-200 mb-2">Summary</h3>`;
        html += `<p class="text-gray-300">${summary}</p>`;
        html += `</div>`;
    }
    
    if (reasons.length > 0) {
        html += `<div class="mb-4">`;
        html += `<h3 class="text-lg font-semibold text-gray-200 mb-2">Reasons</h3>`;
        html += `<ul class="list-disc list-inside text-gray-300 space-y-1">`;
        reasons.forEach(reason => {
            html += `<li>${reason}</li>`;
        });
        html += `</ul>`;
        html += `</div>`;
    }
    
    if (riskNotes.length > 0) {
        html += `<div class="mb-4">`;
        html += `<h3 class="text-lg font-semibold text-yellow-400 mb-2">Risk Notes</h3>`;
        html += `<ul class="list-disc list-inside text-gray-300 space-y-1">`;
        riskNotes.forEach(note => {
            html += `<li>${note}</li>`;
        });
        html += `</ul>`;
        html += `</div>`;
    }
    
    if (dividendAnalysis) {
        html += `<div class="mb-4">`;
        html += `<h3 class="text-lg font-semibold text-gray-200 mb-2">Dividend Analysis</h3>`;
        html += `<p class="text-gray-300">${dividendAnalysis}</p>`;
        html += `</div>`;
    }
    
    if (halalCompliance) {
        html += `<div class="mb-4">`;
        html += `<h3 class="text-lg font-semibold text-gray-200 mb-2">Halal Compliance</h3>`;
        html += `<p class="text-gray-300">${halalCompliance}</p>`;
        html += `</div>`;
    }
    
    if (data.token_usage) {
        html += `<div class="mt-4 pt-4 border-t border-gray-700">`;
        html += `<h3 class="text-sm font-semibold text-gray-400 mb-2">Token Usage</h3>`;
        html += `<p class="text-xs text-gray-500">Prompt: ${data.token_usage.prompt_tokens || 0} | Completion: ${data.token_usage.completion_tokens || 0} | Total: ${data.token_usage.total_tokens || 0}</p>`;
        html += `</div>`;
    }
    
    resultsTitle.textContent = `LLM Decision for ${data.symbol}`;
    resultsContent.innerHTML = html;
    resultsSection.classList.remove('hidden');
    resultsSection.classList.add('fade-in');
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

function connectToStream(symbol, extractionModel, analysisModel) {
    if (currentEventSource) {
        currentEventSource.close();
    }
    
    const params = new URLSearchParams({
        extraction_model: extractionModel || 'auto',
        analysis_model: analysisModel || 'auto'
    });
    const eventSource = new EventSource(`${API_BASE}/financial-analysis/stream/${symbol}?${params.toString()}`);
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
                
                const tokenUsage = data.token_usage || (data.final_state && data.final_state.token_usage);
                const costs = calculateCosts(tokenUsage, extractionModel, analysisModel);
                
                trackEvent('analysis_completed', {
                    analysis_type: 'financial',
                    stock_symbol: symbol,
                    extraction_model: extractionModel,
                    analysis_model: analysisModel,
                    success: true,
                    extracting_token: costs.extracting_token,
                    analysis_token: costs.analysis_token,
                    extraction_price: costs.extraction_cost,
                    analysis_price: costs.analysis_cost,
                    cost: costs.total_cost
                });
                
                if (data.final_state && data.final_state.final_report) {
                    displayFinancialResults({
                        status: 'complete',
                        result: data.final_state.final_report,
                        symbol: symbol,
                        token_usage: tokenUsage
                    });
                } else {
                    fetchFinalResult(symbol);
                }
                
                eventSource.close();
                currentEventSource = null;
            } else if (data.type === 'error') {
                trackEvent('analysis_error', {
                    analysis_type: 'financial',
                    stock_symbol: symbol,
                    extraction_model: extractionModel,
                    analysis_model: analysisModel,
                    error_message: data.error || 'Unknown error'
                });
                
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
    tokenUsageCard.className = 'hidden bg-gray-800 rounded-lg shadow-lg p-6 mb-4 fade-in border border-gray-700';
    
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

