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
    enablePolishContent: document.getElementById('enablePolishContent'),
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
    
    // Add enable polish content flag
    request.enable_polish_content = elements.enablePolishContent.checked;
    
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
            addStreamEvent('start', `Started analysis (${data.total_lines} lines, ${data.total_characters} characters, model: ${escapeHtml(data.model)})`);
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
"""

# =============================================================================
# Initialization
# =============================================================================
_INIT = """
// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

function init() {
    // Bind event listeners
    elements.analyzeBtn.addEventListener('click', handleAnalyzeClick);
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
    + _INIT
)
