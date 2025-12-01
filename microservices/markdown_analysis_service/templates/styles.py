"""CSS styles for the Markdown Analysis Service test UI."""

# =============================================================================
# Base Styles
# =============================================================================
_BASE_STYLES = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f5f5f5;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}
"""

# =============================================================================
# Header Styles
# =============================================================================
_HEADER_STYLES = """
header {
    background: linear-gradient(135deg, #6a1b9a 0%, #4a148c 100%);
    color: white;
    padding: 1rem 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

header h1 { font-size: 1.5rem; font-weight: 600; }
header p { font-size: 0.875rem; opacity: 0.9; margin-top: 0.25rem; }
"""

# =============================================================================
# Layout Styles
# =============================================================================
_LAYOUT_STYLES = """
.container {
    display: flex;
    flex: 1;
    overflow: hidden;
}

.sidebar {
    width: 400px;
    background: white;
    padding: 1.5rem;
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    overflow-y: auto;
}

.main {
    flex: 1;
    padding: 1.5rem;
    overflow: auto;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
"""

# =============================================================================
# Form Styles
# =============================================================================
_FORM_STYLES = """
.form-group { display: flex; flex-direction: column; gap: 0.5rem; }

label { font-weight: 500; font-size: 0.875rem; color: #333; }

input, textarea, select {
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.875rem;
    font-family: inherit;
}

textarea { min-height: 150px; resize: vertical; }
.small-textarea { min-height: 80px; }

button {
    background: #6a1b9a;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.2s;
}

button:hover { background: #4a148c; }
button:disabled { background: #ccc; cursor: not-allowed; }
"""

# =============================================================================
# Collapsible Section Styles
# =============================================================================
_COLLAPSIBLE_STYLES = """
.collapsible {
    background: #f5f5f5;
    border: 1px solid #ddd;
    border-radius: 4px;
    overflow: hidden;
}

.collapsible-header {
    padding: 0.75rem;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
    font-size: 0.875rem;
}

.collapsible-header:hover { background: #eee; }

.collapsible-content {
    display: none;
    padding: 0.75rem;
    border-top: 1px solid #ddd;
}

.collapsible.open .collapsible-content { display: block; }
.collapsible-header::after { content: '▼'; font-size: 0.75rem; }
.collapsible.open .collapsible-header::after { content: '▲'; }
"""

# =============================================================================
# Stream Panel Styles
# =============================================================================
_STREAM_PANEL_STYLES = """
.stream-panel {
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    padding: 1rem;
    max-height: 200px;
    overflow-y: auto;
    display: none;
}

.stream-panel.show { display: block; }

.stream-panel h3 {
    font-size: 0.875rem;
    color: #666;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.stream-panel h3 .status {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #4caf50;
    animation: pulse 1s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.stream-log {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.75rem;
    line-height: 1.6;
}

.stream-log .event {
    padding: 0.25rem 0;
    border-bottom: 1px solid #f0f0f0;
}

.stream-log .event:last-child { border-bottom: none; }

.stream-log .event-type {
    display: inline-block;
    padding: 0.125rem 0.375rem;
    border-radius: 3px;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    margin-right: 0.5rem;
}

.stream-log .event-type.start { background: #e3f2fd; color: #1976d2; }
.stream-log .event-type.iteration { background: #fff3e0; color: #f57c00; }
.stream-log .event-type.chunk { background: #f3e5f5; color: #7b1fa2; }
.stream-log .event-type.tool_call { background: #e8f5e9; color: #388e3c; }
.stream-log .event-type.tool_result { background: #fce4ec; color: #c2185b; }
.stream-log .event-type.complete { background: #e8f5e9; color: #2e7d32; }
.stream-log .event-type.error { background: #ffebee; color: #c62828; }
.stream-log .chunk-text { color: #6a1b9a; }
"""

# =============================================================================
# Result Panel Styles
# =============================================================================
_RESULT_PANEL_STYLES = """
.result-panel {
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.result-header {
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.result-header h2 { font-size: 1rem; font-weight: 600; }

.tabs { display: flex; gap: 0.5rem; }

.tab {
    padding: 0.5rem 1rem;
    background: #f5f5f5;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
}

.tab.active { background: #6a1b9a; color: white; }

.result-content {
    flex: 1;
    overflow: auto;
    padding: 1rem;
}

.result-content pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.8rem;
    line-height: 1.5;
    background: #f8f8f8;
    padding: 1rem;
    border-radius: 4px;
}
"""

# =============================================================================
# Loading & Error Styles
# =============================================================================
_LOADING_STYLES = """
.loading {
    display: none;
    text-align: center;
    padding: 2rem;
}

.loading.show { display: block; }

.spinner {
    border: 3px solid #f3f3f3;
    border-top: 3px solid #6a1b9a;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
}

@keyframes spin { to { transform: rotate(360deg); } }

.error {
    color: #c62828;
    background: #ffebee;
    padding: 1rem;
    border-radius: 4px;
}
"""

# =============================================================================
# Summary Card Styles
# =============================================================================
_SUMMARY_CARD_STYLES = """
.summary-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    margin-bottom: 1rem;
}

.summary-card {
    background: #f5f5f5;
    padding: 1rem;
    border-radius: 8px;
}

.summary-card h3 {
    font-size: 0.75rem;
    color: #666;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

.summary-card .value {
    font-size: 1rem;
    font-weight: 500;
}

.tag {
    display: inline-block;
    background: #e1bee7;
    color: #6a1b9a;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    margin: 0.125rem;
}

.category-path {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.category-path span:not(:last-child)::after {
    content: '→';
    margin-left: 0.5rem;
    color: #999;
}
"""

# =============================================================================
# Section Card Styles
# =============================================================================
_SECTION_CARD_STYLES = """
.section-card {
    background: #fff3e0;
    border-left: 3px solid #ff9800;
    padding: 0.75rem;
    margin: 0.5rem 0;
    border-radius: 0 4px 4px 0;
}

.removed-card {
    background: #ffebee;
    border-left: 3px solid #f44336;
    padding: 0.75rem;
    margin: 0.5rem 0;
    border-radius: 0 4px 4px 0;
}

.glossary-card {
    background: #e3f2fd;
    border-left: 3px solid #2196f3;
    padding: 0.75rem;
    margin: 0.5rem 0;
    border-radius: 0 4px 4px 0;
}
"""

# =============================================================================
# Combined Styles Export
# =============================================================================
STYLES = (
    _BASE_STYLES
    + _HEADER_STYLES
    + _LAYOUT_STYLES
    + _FORM_STYLES
    + _COLLAPSIBLE_STYLES
    + _STREAM_PANEL_STYLES
    + _RESULT_PANEL_STYLES
    + _LOADING_STYLES
    + _SUMMARY_CARD_STYLES
    + _SECTION_CARD_STYLES
)
