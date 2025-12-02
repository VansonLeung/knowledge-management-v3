"""JavaScript for the Markdown Analysis Service test UI."""

# =============================================================================
# Utility Functions
# =============================================================================
_UTILS = """
// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------

/**
 * Escape HTML special characters to prevent XSS.
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * Parse JSON safely, returning null on failure.
 */
function parseJsonSafe(text, fieldName) {
    if (!text.trim()) return null;
    try {
        return JSON.parse(text);
    } catch (e) {
        alert(`Invalid ${fieldName} JSON`);
        return undefined; // Indicates parse error
    }
}
"""

# =============================================================================
# DOM References
# =============================================================================
_DOM_REFS = """
// ---------------------------------------------------------------------------
// DOM Element References
// ---------------------------------------------------------------------------

const elements = {
    analyzeBtn: document.getElementById('analyzeBtn'),
    checkCleanBtn: document.getElementById('checkCleanBtn'),
    polishBtn: document.getElementById('polishBtn'),
    finalizeBtn: document.getElementById('finalizeBtn'),
    glossaryBtn: document.getElementById('glossaryBtn'),
    clearBtn: document.getElementById('clearBtn'),
    fileInput: document.getElementById('fileInput'),
    textArea: document.getElementById('text'),
    loading: document.getElementById('loading'),
    results: document.getElementById('results'),
    streamPanel: document.getElementById('streamPanel'),
    streamLog: document.getElementById('streamLog'),
    tabs: document.querySelectorAll('.tab'),
    collapsibles: document.querySelectorAll('.collapsible-header'),
    
    // Form inputs
    model: document.getElementById('model'),
    apiKey: document.getElementById('apiKey'),
    baseUrl: document.getElementById('baseUrl'),
    maxKeywords: document.getElementById('maxKeywords'),
    isStandalone: document.getElementById('isStandalone'),
    enablePolishContent: document.getElementById('enablePolishContent'),
    enableGlossaryLookup: document.getElementById('enableGlossaryLookup'),
    enableTranslation: document.getElementById('enableTranslation'),
    translateTo: document.getElementById('translateTo'),
    translateToGroup: document.getElementById('translateToGroup'),
    metadata: document.getElementById('metadata'),
    glossary: document.getElementById('glossary'),
    categories: document.getElementById('categories'),
};
"""

# =============================================================================
# State Management
# =============================================================================
_STATE = """
// ---------------------------------------------------------------------------
// Application State
// ---------------------------------------------------------------------------

const state = {
    currentData: null,
    currentTab: 'summary',
    accumulatedChunks: '',
};

function resetState() {
    state.currentData = null;
    state.accumulatedChunks = '';
}
"""

# =============================================================================
# UI Helpers
# =============================================================================
_UI_HELPERS = """
// ---------------------------------------------------------------------------
// UI Helper Functions
// ---------------------------------------------------------------------------

function showLoading() {
    elements.loading.classList.add('show');
    elements.results.innerHTML = '';
    elements.streamLog.innerHTML = '';
    elements.streamPanel.classList.add('show');
    elements.analyzeBtn.disabled = true;
}

function hideLoading() {
    elements.loading.classList.remove('show');
    elements.analyzeBtn.disabled = false;
}

function addStreamEvent(eventType, message) {
    const event = document.createElement('div');
    event.className = 'event';
    event.innerHTML = `<span class="event-type ${eventType}">${eventType}</span>${message}`;
    elements.streamLog.appendChild(event);
    elements.streamLog.scrollTop = elements.streamLog.scrollHeight;
}

function showError(message) {
    addStreamEvent('error', escapeHtml(message));
    elements.results.innerHTML = `<div class="error">Error: ${escapeHtml(message)}</div>`;
}
"""

# =============================================================================
# Request Builder
# =============================================================================
_REQUEST_BUILDER = """
// ---------------------------------------------------------------------------
// Request Builder
// ---------------------------------------------------------------------------

function buildRequest() {
    const text = elements.textArea.value.trim();
    if (!text) {
        alert('Please enter text to analyze');
        return null;
    }
    
    const request = { text };
    
    // Add optional string fields
    const model = elements.model.value.trim();
    if (model) request.model = model;
    
    const apiKey = elements.apiKey.value.trim();
    if (apiKey) request.api_key = apiKey;
    
    const baseUrl = elements.baseUrl.value.trim();
    if (baseUrl) request.base_url = baseUrl;
    
    // Add max keywords
    const maxKeywords = parseInt(elements.maxKeywords.value);
    if (maxKeywords) request.max_keywords = maxKeywords;
    
    // Add toggle flags
    request.is_standalone = elements.isStandalone.checked;
    request.enable_polish_content = elements.enablePolishContent.checked;
    request.enable_glossary_lookup = elements.enableGlossaryLookup.checked;
    
    // Add translation options
    request.enable_translation = elements.enableTranslation.checked;
    const translateTo = elements.translateTo.value.trim();
    if (translateTo) request.translate_to = translateTo;
    
    // Parse JSON fields
    const metadata = parseJsonSafe(elements.metadata.value, 'metadata');
    if (metadata === undefined) return null;
    if (metadata) request.metadata = metadata;
    
    const glossary = parseJsonSafe(elements.glossary.value, 'glossary');
    if (glossary === undefined) return null;
    if (glossary) request.glossary = glossary;
    
    const categories = parseJsonSafe(elements.categories.value, 'categories');
    if (categories === undefined) return null;
    if (categories) request.categories = categories;
    
    return request;
}
"""

# =============================================================================
# SSE Handler
# =============================================================================
_SSE_HANDLER = """
// ---------------------------------------------------------------------------
// SSE Event Handler
// ---------------------------------------------------------------------------

function handleSSEEvent(eventType, dataStr) {
    let data;
    try {
        data = JSON.parse(dataStr);
    } catch (e) {
        console.error('Failed to parse SSE data:', dataStr);
        return;
    }
    
    switch (eventType) {
        case 'start':
            const modeInfo = data.mode === 'standalone' 
                ? `(standalone: ${data.total_chunks} chunks, ${data.total_words} words)` 
                : `(${data.total_lines} lines, ${data.total_characters} characters)`;
            addStreamEvent('start', `Started analysis ${modeInfo}, model: ${escapeHtml(data.model)}`);
            break;
            
        case 'iteration':
            addStreamEvent('iteration', `Iteration ${data.iteration}/${data.max_iterations}`);
            break;
            
        case 'chunk':
            handleChunkEvent(data);
            break;
            
        case 'tool_call':
            handleToolCallEvent(data);
            break;
            
        case 'tool_result':
            handleToolResultEvent(data);
            break;
            
        case 'complete':
            addStreamEvent('complete', 'Analysis complete!');
            state.currentData = data;
            renderResults();
            break;
            
        case 'error':
            showError(data.message);
            break;
    }
}

function handleChunkEvent(data) {
    state.accumulatedChunks += data.content;
    
    let chunkEl = elements.streamLog.querySelector('.chunk-accumulator');
    if (!chunkEl) {
        chunkEl = document.createElement('div');
        chunkEl.className = 'event chunk-accumulator';
        chunkEl.innerHTML = '<span class="event-type chunk">stream</span><span class="chunk-text"></span>';
        elements.streamLog.appendChild(chunkEl);
    }
    
    chunkEl.querySelector('.chunk-text').textContent = state.accumulatedChunks.slice(-200);
    elements.streamLog.scrollTop = elements.streamLog.scrollHeight;
}

function handleToolCallEvent(data) {
    state.accumulatedChunks = '';
    const argsStr = JSON.stringify(data.arguments || {}) || '{}';
    const truncatedArgs = argsStr;
    addStreamEvent('tool_call', `<strong>${escapeHtml(data.name || 'unknown')}</strong>(${escapeHtml(truncatedArgs)})`);
}

function handleToolResultEvent(data) {
    const result = data.result || '';
    const truncatedResult = result;
    addStreamEvent('tool_result', `${escapeHtml(data.name || 'unknown')} → ${escapeHtml(truncatedResult)}`);
}
"""

# =============================================================================
# SSE Stream Reader
# =============================================================================
_SSE_READER = """
// ---------------------------------------------------------------------------
// SSE Stream Reader
// ---------------------------------------------------------------------------

async function readSSEStream(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split('\\n');
        buffer = lines.pop() || '';
        
        let currentEvent = null;
        let currentData = '';
        
        for (const line of lines) {
            if (line.startsWith('event: ')) {
                currentEvent = line.slice(7);
            } else if (line.startsWith('data: ')) {
                currentData = line.slice(6);
                if (currentEvent && currentData) {
                    handleSSEEvent(currentEvent, currentData);
                    currentEvent = null;
                    currentData = '';
                }
            } else if (line === '' && currentEvent && currentData) {
                handleSSEEvent(currentEvent, currentData);
                currentEvent = null;
                currentData = '';
            }
        }
    }
}
"""

# =============================================================================
# Results Renderer
# =============================================================================
_RESULTS_RENDERER = """
// ---------------------------------------------------------------------------
// Results Renderer
// ---------------------------------------------------------------------------

function renderResults() {
    const data = state.currentData;
    if (!data) return;
    
    const renderers = {
        summary: renderSummary,
        content: renderContent,
        sections: renderSections,
        json: renderJson,
    };
    
    const renderer = renderers[state.currentTab] || renderSummary;
    elements.results.innerHTML = renderer(data);
}

function renderSummary(data) {
    let html = '<div class="summary-grid">';
    html += `<div class="summary-card"><h3>Language</h3><div class="value">${escapeHtml(data.language)}</div></div>`;
    html += `<div class="summary-card"><h3>Iterations</h3><div class="value">${data.iterations_used}</div></div>`;
    html += '</div>';
    
    html += `<div class="summary-card" style="margin-bottom: 1rem;"><h3>Title</h3><div class="value">${escapeHtml(data.title)}</div></div>`;
    
    if (data.category?.length) {
        html += '<div class="summary-card" style="margin-bottom: 1rem;"><h3>Category</h3><div class="category-path">';
        data.category.forEach(cat => html += `<span>${escapeHtml(cat)}</span>`);
        html += '</div></div>';
    }
    
    if (data.keywords?.length) {
        html += '<div class="summary-card" style="margin-bottom: 1rem;"><h3>Keywords</h3><div>';
        data.keywords.forEach(kw => html += `<span class="tag">${escapeHtml(kw)}</span>`);
        html += '</div></div>';
    }
    
    if (data.glossary_matches?.length) {
        html += '<h3 style="margin: 1rem 0 0.5rem;">Glossary Matches</h3>';
        data.glossary_matches.forEach(match => {
            html += `<div class="glossary-card"><strong>${escapeHtml(match.term)}</strong>: ${escapeHtml(match.definition)}</div>`;
        });
    }
    
    return html;
}

function renderContent(data) {
    return `<pre>${escapeHtml(data.content)}</pre>`;
}

function renderSections(data) {
    let html = '';
    
    if (data.polished_sections?.length) {
        html += `<h3>Polished Sections (${data.polished_sections.length})</h3>`;
        html += '<div style="margin-bottom: 1rem; padding: 0.5rem; background: #e8f5e9; border-radius: 4px;">';
        html += `<strong>Total polished content:</strong> ${data.content?.length || 0} characters`;
        html += '</div>';
        
        data.polished_sections.forEach((sec, idx) => {
            const label = sec.section_label ? ` - ${escapeHtml(sec.section_label)}` : '';
            html += `<div class="section-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>Section #${sec.section_number || idx + 1}${label}</strong>
                    <span style="font-size: 0.75rem; color: #666;">Lines ${sec.start_line}-${sec.end_line} (${sec.polished_char_count} chars)</span>
                </div>
            </div>`;
        });
    } else {
        html += '<p style="color: #666;">No polished sections yet</p>';
    }
    
    return html;
}

function renderJson(data) {
    return `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
}
"""

# =============================================================================
# Event Handlers
# =============================================================================
_EVENT_HANDLERS = """
// ---------------------------------------------------------------------------
// Event Handlers
// ---------------------------------------------------------------------------

async function handleAnalyzeClick() {
    const request = buildRequest();
    if (!request) return;
    
    resetState();
    showLoading();
    
    try {
        const response = await fetch('/study_text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        await readSSEStream(response);
        
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

function handleTabClick(tab) {
    elements.tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    state.currentTab = tab.dataset.tab;
    renderResults();
}

async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
        elements.textArea.value = await file.text();
    } catch (error) {
        alert('Error reading file: ' + error.message);
    }
    
    event.target.value = '';
}

function handleClearClick() {
    elements.textArea.value = '';
    elements.textArea.focus();
}

function handleCollapsibleClick(header) {
    header.parentElement.classList.toggle('open');
}

// ---------------------------------------------------------------------------
// Cleanliness Check Handler
// ---------------------------------------------------------------------------

function showLoadingCleanliness() {
    elements.loading.classList.add('show');
    elements.loading.querySelector('p').textContent = 'Evaluating article cleanliness...';
    elements.results.innerHTML = '';
    elements.streamLog.innerHTML = '';
    elements.streamPanel.classList.remove('show');
    elements.analyzeBtn.disabled = true;
    elements.checkCleanBtn.disabled = true;
}

function hideLoadingCleanliness() {
    elements.loading.classList.remove('show');
    elements.loading.querySelector('p').textContent = 'Analyzing text with LLM...';
    elements.analyzeBtn.disabled = false;
    elements.checkCleanBtn.disabled = false;
}

function renderCleanlinessResult(data) {
    const scoreColor = data.cleanliness_score >= 70 ? '#4CAF50' : 
                       data.cleanliness_score >= 40 ? '#ff9800' : '#f44336';
    const statusIcon = data.is_messy ? '⚠️' : '✅';
    const statusText = data.is_messy ? 'MESSY - Needs Cleaning' : 'CLEAN - Ready to Use';
    
    let html = `
        <div class="summary-card" style="margin-bottom: 1rem; border-left: 4px solid ${scoreColor};">
            <h3>${statusIcon} ${statusText}</h3>
            <div style="display: flex; gap: 2rem; margin-top: 1rem;">
                <div>
                    <strong>Cleanliness Score</strong>
                    <div style="font-size: 2rem; color: ${scoreColor};">${data.cleanliness_score || 'N/A'}/100</div>
                </div>
                <div style="flex: 1;">
                    <strong>Model</strong>
                    <div>${escapeHtml(data.model || 'unknown')}</div>
                    <strong style="margin-top: 0.5rem; display: block;">Stats</strong>
                    <div>${data.total_words || 0} words, ${data.total_chunks || 0} chunks</div>
                </div>
            </div>
        </div>
    `;
    
    if (data.reasoning) {
        html += `
            <div class="summary-card" style="margin-bottom: 1rem;">
                <h3>Reasoning</h3>
                <p>${escapeHtml(data.reasoning)}</p>
            </div>
        `;
    }
    
    if (data.issues_found && data.issues_found.length > 0) {
        html += `
            <div class="summary-card" style="margin-bottom: 1rem;">
                <h3>Issues Found (${data.issues_found.length})</h3>
                <ul style="margin: 0.5rem 0 0 1.5rem; padding: 0;">
                    ${data.issues_found.map(issue => `<li>${escapeHtml(issue)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    if (data.error) {
        html += `<div class="error">Error: ${escapeHtml(data.error)}</div>`;
    }
    
    elements.results.innerHTML = html;
}

async function handleCheckCleanlinessClick() {
    const text = elements.textArea.value.trim();
    if (!text) {
        alert('Please enter text to evaluate');
        return;
    }
    
    const request = { text };
    
    // Add optional config overrides
    const model = elements.model.value.trim();
    if (model) request.model = model;
    
    const apiKey = elements.apiKey.value.trim();
    if (apiKey) request.api_key = apiKey;
    
    const baseUrl = elements.baseUrl.value.trim();
    if (baseUrl) request.base_url = baseUrl;
    
    showLoadingCleanliness();
    
    try {
        const response = await fetch('/evaluate_article_cleanliness', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        renderCleanlinessResult(data);
        
    } catch (error) {
        elements.results.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
    } finally {
        hideLoadingCleanliness();
    }
}

// ---------------------------------------------------------------------------
// Polish Content Handler
// ---------------------------------------------------------------------------

function showLoadingGeneric(message) {
    elements.loading.classList.add('show');
    elements.loading.querySelector('p').textContent = message;
    elements.results.innerHTML = '';
    elements.streamLog.innerHTML = '';
    elements.streamPanel.classList.remove('show');
    setAllButtonsDisabled(true);
}

function hideLoadingGeneric() {
    elements.loading.classList.remove('show');
    elements.loading.querySelector('p').textContent = 'Analyzing text with LLM...';
    setAllButtonsDisabled(false);
}

function setAllButtonsDisabled(disabled) {
    elements.analyzeBtn.disabled = disabled;
    elements.checkCleanBtn.disabled = disabled;
    elements.polishBtn.disabled = disabled;
    elements.finalizeBtn.disabled = disabled;
    elements.glossaryBtn.disabled = disabled;
}

function buildBaseRequest() {
    const text = elements.textArea.value.trim();
    if (!text) return null;
    
    const request = { text };
    
    const model = elements.model.value.trim();
    if (model) request.model = model;
    
    const apiKey = elements.apiKey.value.trim();
    if (apiKey) request.api_key = apiKey;
    
    const baseUrl = elements.baseUrl.value.trim();
    if (baseUrl) request.base_url = baseUrl;
    
    return request;
}

function renderPolishResult(data) {
    let translatedInfo = data.translated_to ? ` | <strong>Translated to:</strong> ${escapeHtml(data.translated_to)}` : '';
    let html = `
        <div class="summary-card" style="margin-bottom: 1rem; border-left: 4px solid #2196F3;">
            <h3>✨ Content Polished</h3>
            <div style="margin-top: 0.5rem;">
                <strong>Model:</strong> ${escapeHtml(data.model || 'unknown')} |
                <strong>Stats:</strong> ${data.total_words || 0} words, ${data.total_chunks || 0} chunks${translatedInfo}
            </div>
        </div>
    `;
    
    if (data.changes_made && data.changes_made.length > 0) {
        html += `
            <div class="summary-card" style="margin-bottom: 1rem;">
                <h3>Changes Made</h3>
                <ul style="margin: 0.5rem 0 0 1.5rem; padding: 0;">
                    ${data.changes_made.map(c => `<li>${escapeHtml(c)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    if (data.sections_removed && data.sections_removed.length > 0) {
        html += `
            <div class="summary-card" style="margin-bottom: 1rem;">
                <h3>Sections Removed</h3>
                <ul style="margin: 0.5rem 0 0 1.5rem; padding: 0;">
                    ${data.sections_removed.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    if (data.translation_notes && data.translation_notes.length > 0) {
        html += `
            <div class="summary-card" style="margin-bottom: 1rem;">
                <h3>Translation Notes</h3>
                <ul style="margin: 0.5rem 0 0 1.5rem; padding: 0;">
                    ${data.translation_notes.map(n => `<li>${escapeHtml(n)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    if (data.polished_content) {
        html += `
            <div class="summary-card" style="margin-bottom: 1rem;">
                <h3>Polished Content</h3>
                <pre style="white-space: pre-wrap; max-height: 400px; overflow-y: auto;">${escapeHtml(data.polished_content)}</pre>
            </div>
        `;
    }
    
    if (data.error) {
        html += `<div class="error">Error: ${escapeHtml(data.error)}</div>`;
    }
    
    elements.results.innerHTML = html;
}

async function handlePolishClick() {
    const request = buildBaseRequest();
    if (!request) {
        alert('Please enter text to polish');
        return;
    }
    
    // Add translation options for Polish Content
    request.enable_translation = elements.enableTranslation.checked;
    const translateTo = elements.translateTo.value.trim();
    if (translateTo) request.translate_to = translateTo;
    
    // Add glossary for translation accuracy
    const glossary = parseJsonSafe(elements.glossary.value, 'glossary');
    if (glossary === undefined) return;
    if (glossary) request.glossary = glossary;
    
    showLoadingGeneric('Polishing content...');
    
    try {
        const response = await fetch('/polish_content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        renderPolishResult(data);
        
    } catch (error) {
        elements.results.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
    } finally {
        hideLoadingGeneric();
    }
}

// ---------------------------------------------------------------------------
// Finalize Content Handler
// ---------------------------------------------------------------------------

function renderFinalizeResult(data) {
    let html = `
        <div class="summary-card" style="margin-bottom: 1rem; border-left: 4px solid #9C27B0;">
            <h3>📋 Content Finalized</h3>
            <div style="margin-top: 0.5rem;">
                <strong>Model:</strong> ${escapeHtml(data.model || 'unknown')} |
                <strong>Stats:</strong> ${data.total_words || 0} words, ${data.total_chunks || 0} chunks
            </div>
        </div>
    `;
    
    if (data.language || data.title) {
        html += '<div class="summary-grid">';
        if (data.language) {
            html += `<div class="summary-card"><h3>Language</h3><div class="value">${escapeHtml(data.language)}</div></div>`;
        }
        if (data.title) {
            html += `<div class="summary-card"><h3>Title</h3><div class="value">${escapeHtml(data.title)}</div></div>`;
        }
        html += '</div>';
    }
    
    if (data.summary) {
        html += `
            <div class="summary-card" style="margin-bottom: 1rem;">
                <h3>Summary</h3>
                <p>${escapeHtml(data.summary)}</p>
            </div>
        `;
    }
    
    if (data.category && data.category.length > 0) {
        html += '<div class="summary-card" style="margin-bottom: 1rem;"><h3>Category</h3><div class="category-path">';
        data.category.forEach(cat => html += `<span>${escapeHtml(cat)}</span>`);
        html += '</div></div>';
    }
    
    if (data.keywords && data.keywords.length > 0) {
        html += '<div class="summary-card" style="margin-bottom: 1rem;"><h3>Keywords</h3><div>';
        data.keywords.forEach(kw => html += `<span class="tag">${escapeHtml(kw)}</span>`);
        html += '</div></div>';
    }
    
    // Author/Publishing info
    const pubInfo = [];
    if (data.author) pubInfo.push(`<strong>Author:</strong> ${escapeHtml(data.author)}`);
    if (data.published_by) pubInfo.push(`<strong>Publisher:</strong> ${escapeHtml(data.published_by)}`);
    if (data.published_at) pubInfo.push(`<strong>Date:</strong> ${escapeHtml(data.published_at)}`);
    
    if (pubInfo.length > 0) {
        html += `<div class="summary-card" style="margin-bottom: 1rem;"><h3>Publication Info</h3><p>${pubInfo.join(' | ')}</p></div>`;
    }
    
    // Event info
    const eventInfo = [];
    if (data.location) eventInfo.push(`<strong>Location:</strong> ${escapeHtml(data.location)}`);
    if (data.venue) eventInfo.push(`<strong>Venue:</strong> ${escapeHtml(data.venue)}`);
    if (data.date_start) eventInfo.push(`<strong>Start:</strong> ${escapeHtml(data.date_start)}`);
    if (data.date_end) eventInfo.push(`<strong>End:</strong> ${escapeHtml(data.date_end)}`);
    
    if (eventInfo.length > 0) {
        html += `<div class="summary-card" style="margin-bottom: 1rem;"><h3>Event Info</h3><p>${eventInfo.join(' | ')}</p></div>`;
    }
    
    // Related entities
    if (data.related_people && data.related_people.length > 0) {
        html += '<div class="summary-card" style="margin-bottom: 1rem;"><h3>Related People</h3><div>';
        data.related_people.forEach(p => html += `<span class="tag">${escapeHtml(p)}</span>`);
        html += '</div></div>';
    }
    
    if (data.related_organizations && data.related_organizations.length > 0) {
        html += '<div class="summary-card" style="margin-bottom: 1rem;"><h3>Related Organizations</h3><div>';
        data.related_organizations.forEach(o => html += `<span class="tag">${escapeHtml(o)}</span>`);
        html += '</div></div>';
    }
    
    if (data.error) {
        html += `<div class="error">Error: ${escapeHtml(data.error)}</div>`;
    }
    
    elements.results.innerHTML = html;
}

async function handleFinalizeClick() {
    const request = buildBaseRequest();
    if (!request) {
        alert('Please enter text to finalize');
        return;
    }
    
    // Add categories if provided
    const categories = parseJsonSafe(elements.categories.value, 'categories');
    if (categories === undefined) return;
    if (categories) request.categories = categories;
    
    // Add max keywords
    const maxKeywords = parseInt(elements.maxKeywords.value);
    if (maxKeywords) request.max_keywords = maxKeywords;
    
    showLoadingGeneric('Finalizing content...');
    
    try {
        const response = await fetch('/finalize_content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        renderFinalizeResult(data);
        
    } catch (error) {
        elements.results.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
    } finally {
        hideLoadingGeneric();
    }
}

// ---------------------------------------------------------------------------
// Glossary Lookup Handler
// ---------------------------------------------------------------------------

function renderGlossaryResult(data) {
    let html = `
        <div class="summary-card" style="margin-bottom: 1rem; border-left: 4px solid #FF9800;">
            <h3>📚 Glossary Lookup</h3>
            <div style="margin-top: 0.5rem;">
                <strong>Model:</strong> ${escapeHtml(data.model || 'unknown')} |
                <strong>Stats:</strong> ${data.total_words || 0} words |
                <strong>Terms Searched:</strong> ${data.glossary_terms_searched || 0} |
                <strong>Total Matches:</strong> ${data.total_matches || 0}
            </div>
        </div>
    `;
    
    if (data.matches && data.matches.length > 0) {
        html += '<div class="summary-card" style="margin-bottom: 1rem;"><h3>Matches Found</h3>';
        data.matches.forEach(match => {
            html += `
                <div class="glossary-card" style="margin-bottom: 0.5rem; padding: 0.75rem; background: #fff8e1; border-radius: 4px;">
                    <strong>${escapeHtml(match.term)}</strong>
                    <span style="color: #666; margin-left: 0.5rem;">(${match.occurrences || 1} occurrence${(match.occurrences || 1) > 1 ? 's' : ''})</span>
                    ${match.definition ? `<p style="margin: 0.25rem 0 0 0; font-size: 0.875rem;">${escapeHtml(match.definition)}</p>` : ''}
                    ${match.context_snippets && match.context_snippets.length > 0 ? 
                        `<p style="margin: 0.25rem 0 0 0; font-size: 0.75rem; color: #666; font-style: italic;">"${escapeHtml(match.context_snippets[0])}"</p>` : ''}
                </div>
            `;
        });
        html += '</div>';
    } else {
        html += `
            <div class="summary-card" style="margin-bottom: 1rem;">
                <p style="color: #666;">No glossary terms found in the text.</p>
            </div>
        `;
    }
    
    if (data.error) {
        html += `<div class="error">Error: ${escapeHtml(data.error)}</div>`;
    }
    
    elements.results.innerHTML = html;
}

async function handleGlossaryClick() {
    const request = buildBaseRequest();
    if (!request) {
        alert('Please enter text to search');
        return;
    }
    
    // Glossary is required for this API
    const glossary = parseJsonSafe(elements.glossary.value, 'glossary');
    if (glossary === undefined) return;
    if (!glossary || glossary.length === 0) {
        alert('Please provide a glossary in the Glossary section');
        return;
    }
    request.glossary = glossary;
    
    showLoadingGeneric('Looking up glossary terms...');
    
    try {
        const response = await fetch('/glossary_lookup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        renderGlossaryResult(data);
        
    } catch (error) {
        elements.results.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
    } finally {
        hideLoadingGeneric();
    }
}
"""

# =============================================================================
# LocalStorage Settings
# =============================================================================
_LOCAL_STORAGE = """
// ---------------------------------------------------------------------------
// LocalStorage Settings Management
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'markdown_analysis_settings';

// Form fields to persist (key: element id, type: 'text' | 'checkbox')
const PERSISTED_FIELDS = [
    { id: 'model', type: 'text' },
    { id: 'apiKey', type: 'text' },
    { id: 'baseUrl', type: 'text' },
    { id: 'maxKeywords', type: 'text' },
    { id: 'isStandalone', type: 'checkbox' },
    { id: 'enablePolishContent', type: 'checkbox' },
    { id: 'enableGlossaryLookup', type: 'checkbox' },
    { id: 'enableTranslation', type: 'checkbox' },
    { id: 'translateTo', type: 'text' },
    { id: 'metadata', type: 'text' },
    { id: 'glossary', type: 'text' },
    { id: 'categories', type: 'text' },
];

/**
 * Save all form settings to localStorage.
 */
function saveSettingsToStorage() {
    const settings = {};
    
    PERSISTED_FIELDS.forEach(field => {
        const el = document.getElementById(field.id);
        if (!el) return;
        
        if (field.type === 'checkbox') {
            settings[field.id] = el.checked;
        } else {
            settings[field.id] = el.value;
        }
    });
    
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {
        console.warn('Failed to save settings to localStorage:', e);
    }
}

/**
 * Load form settings from localStorage.
 */
function loadSettingsFromStorage() {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (!stored) return;
        
        const settings = JSON.parse(stored);
        
        PERSISTED_FIELDS.forEach(field => {
            const el = document.getElementById(field.id);
            if (!el || settings[field.id] === undefined) return;
            
            if (field.type === 'checkbox') {
                el.checked = settings[field.id];
            } else {
                el.value = settings[field.id];
            }
        });
    } catch (e) {
        console.warn('Failed to load settings from localStorage:', e);
    }
}

/**
 * Bind change/input listeners to all persisted fields.
 */
function bindSettingsListeners() {
    PERSISTED_FIELDS.forEach(field => {
        const el = document.getElementById(field.id);
        if (!el) return;
        
        if (field.type === 'checkbox') {
            el.addEventListener('change', saveSettingsToStorage);
        } else {
            // Use 'input' for immediate save on typing
            el.addEventListener('input', saveSettingsToStorage);
            // Also save on blur for good measure
            el.addEventListener('change', saveSettingsToStorage);
        }
    });
}
"""

# =============================================================================
# Initialization
# =============================================================================
_INIT = """
// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

function updateTranslateToVisibility() {
    const show = elements.enableTranslation.checked;
    elements.translateToGroup.style.display = show ? 'block' : 'none';
}

function init() {
    // Load saved settings from localStorage
    loadSettingsFromStorage();
    
    // Bind settings persistence listeners
    bindSettingsListeners();
    
    // Set initial visibility of translate_to field
    updateTranslateToVisibility();
    
    // Toggle translate_to visibility when checkbox changes
    elements.enableTranslation.addEventListener('change', updateTranslateToVisibility);
    
    // Bind event listeners
    elements.analyzeBtn.addEventListener('click', handleAnalyzeClick);
    elements.checkCleanBtn.addEventListener('click', handleCheckCleanlinessClick);
    elements.polishBtn.addEventListener('click', handlePolishClick);
    elements.finalizeBtn.addEventListener('click', handleFinalizeClick);
    elements.glossaryBtn.addEventListener('click', handleGlossaryClick);
    elements.clearBtn.addEventListener('click', handleClearClick);
    elements.fileInput.addEventListener('change', handleFileSelect);
    
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => handleTabClick(tab));
    });
    
    elements.collapsibles.forEach(header => {
        header.addEventListener('click', () => handleCollapsibleClick(header));
    });
}

// Run initialization
init();
"""

# =============================================================================
# Combined Scripts Export
# =============================================================================
SCRIPTS = (
    _UTILS
    + _DOM_REFS
    + _STATE
    + _UI_HELPERS
    + _REQUEST_BUILDER
    + _SSE_HANDLER
    + _SSE_READER
    + _RESULTS_RENDERER
    + _EVENT_HANDLERS
    + _LOCAL_STORAGE
    + _INIT
)
