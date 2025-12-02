"""HTML layout components for the Markdown Analysis Service test UI."""

# =============================================================================
# Header Component
# =============================================================================
_HEADER = """
    <header>
        <h1>🔍 Markdown Analysis Service</h1>
        <p>Agentic text analysis with LLM tool calling (SSE streaming)</p>
    </header>
"""

# =============================================================================
# Sidebar: Text Input Section
# =============================================================================
_TEXT_INPUT_SECTION = """
            <div class="form-group">
                <label>Text to Analyze</label>
                <textarea id="text" placeholder="Paste your text or markdown content here..."></textarea>
                <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                    <label class="file-input-btn" style="flex: 1;">
                        <input type="file" id="fileInput" accept=".txt,.md,.markdown,.json,.xml,.html,.htm,.csv,.log" style="display: none;">
                        <span style="display: block; background: #f5f5f5; border: 1px dashed #ccc; border-radius: 4px; padding: 0.5rem; text-align: center; cursor: pointer; font-size: 0.875rem;">
                            📁 Load from file
                        </span>
                    </label>
                    <button type="button" id="clearBtn" style="background: #f44336; padding: 0.5rem 1rem; font-size: 0.875rem;">
                        ✕ Clear
                    </button>
                </div>
            </div>
"""

# =============================================================================
# Sidebar: LLM Configuration Section
# =============================================================================
_LLM_CONFIG_SECTION = """
            <div class="collapsible" id="configSection">
                <div class="collapsible-header">LLM Configuration</div>
                <div class="collapsible-content">
                    <div class="form-group">
                        <label>Model</label>
                        <input type="text" id="model" placeholder="gpt-4o-mini (default)">
                    </div>
                    <div class="form-group">
                        <label>API Key</label>
                        <input type="password" id="apiKey" placeholder="Uses server default if empty">
                    </div>
                    <div class="form-group">
                        <label>Base URL</label>
                        <input type="text" id="baseUrl" placeholder="https://api.openai.com/v1">
                    </div>
                    <div class="form-group">
                        <label>Max Keywords</label>
                        <input type="number" id="maxKeywords" value="10" min="1" max="50">
                    </div>
                    <hr style="margin: 1rem 0; border: none; border-top: 1px solid #e0e0e0;">
                    <div class="form-group" style="display: flex; align-items: center; gap: 0.5rem;">
                        <input type="checkbox" id="isStandalone" style="width: auto; margin: 0;">
                        <label for="isStandalone" style="margin: 0; cursor: pointer;">Standalone Mode</label>
                    </div>
                    <p style="font-size: 0.75rem; color: #666; margin-top: 0.25rem;">
                        Chunks text and sends to LLM in one go. Faster but uses more tokens.
                    </p>
                    <div class="form-group" style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.75rem;">
                        <input type="checkbox" id="enablePolishContent" checked style="width: auto; margin: 0;">
                        <label for="enablePolishContent" style="margin: 0; cursor: pointer;">Enable Polish Content</label>
                    </div>
                    <p style="font-size: 0.75rem; color: #666; margin-top: 0.25rem;">
                        Allow LLM to clean and polish messy text.
                    </p>
                    <div class="form-group" style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.75rem;">
                        <input type="checkbox" id="enableGlossaryLookup" checked style="width: auto; margin: 0;">
                        <label for="enableGlossaryLookup" style="margin: 0; cursor: pointer;">Enable Glossary Lookup</label>
                    </div>
                    <p style="font-size: 0.75rem; color: #666; margin-top: 0.25rem;">
                        Allow LLM to look up terms in the glossary (agentic mode only).
                    </p>
                    <hr style="margin: 1rem 0; border: none; border-top: 1px solid #e0e0e0;">
                    <div class="form-group" style="display: flex; align-items: center; gap: 0.5rem;">
                        <input type="checkbox" id="enableTranslation" style="width: auto; margin: 0;">
                        <label for="enableTranslation" style="margin: 0; cursor: pointer;">Translate Content</label>
                    </div>
                    <div class="form-group" id="translateToGroup" style="display: none; margin-top: 0.5rem;">
                        <label>Target Language</label>
                        <input type="text" id="translateTo" placeholder="e.g., English, 简体中文, 日本語">
                    </div>
                    <p style="font-size: 0.75rem; color: #666; margin-top: 0.25rem;">
                        Translate polished content to target language. Uses glossary for accuracy.
                    </p>
                </div>
            </div>
"""

# =============================================================================
# Sidebar: Metadata Section
# =============================================================================
_METADATA_SECTION = """
            <div class="collapsible" id="metadataSection">
                <div class="collapsible-header">Metadata (Optional)</div>
                <div class="collapsible-content">
                    <div class="form-group">
                        <label>JSON key-value pairs</label>
                        <textarea id="metadata" class="small-textarea" placeholder='{"source": "arxiv", "date": "2024-01-01"}'></textarea>
                    </div>
                </div>
            </div>
"""

# =============================================================================
# Sidebar: Glossary Section
# =============================================================================
_GLOSSARY_SECTION = """
            <div class="collapsible" id="glossarySection">
                <div class="collapsible-header">Glossary (Optional)</div>
                <div class="collapsible-content">
                    <div class="form-group">
                        <label>JSON array of terms</label>
                        <textarea id="glossary" class="small-textarea" placeholder='[{"term": "RAG", "definition": "Retrieval Augmented Generation"}]'></textarea>
                    </div>
                </div>
            </div>
"""

# =============================================================================
# Sidebar: Categories Section
# =============================================================================
_CATEGORIES_SECTION = """
            <div class="collapsible" id="categoriesSection">
                <div class="collapsible-header">Categories (Optional)</div>
                <div class="collapsible-content">
                    <div class="form-group">
                        <label>JSON category tree</label>
                        <textarea id="categories" class="small-textarea" placeholder='["General", {"name": "Technology", "children": ["AI", "Web"]}]'></textarea>
                    </div>
                </div>
            </div>
"""

# =============================================================================
# Main: Stream Panel
# =============================================================================
_STREAM_PANEL = """
            <div class="stream-panel" id="streamPanel">
                <h3><span class="status"></span> Live Stream</h3>
                <div class="stream-log" id="streamLog"></div>
            </div>
"""

# =============================================================================
# Main: Result Panel
# =============================================================================
_RESULT_PANEL = """
            <div class="result-panel">
                <div class="result-header">
                    <h2>Analysis Results</h2>
                    <div class="tabs">
                        <button class="tab active" data-tab="summary">Summary</button>
                        <button class="tab" data-tab="content">Content</button>
                        <button class="tab" data-tab="sections">Sections</button>
                        <button class="tab" data-tab="json">JSON</button>
                    </div>
                </div>
                <div class="result-content">
                    <div class="loading" id="loading">
                        <div class="spinner"></div>
                        <p>Analyzing text with LLM...</p>
                        <p style="font-size: 0.875rem; color: #666; margin-top: 0.5rem;">
                            The agent is using tools to read and process the document.
                        </p>
                    </div>
                    <div id="results">
                        <p style="color: #666; text-align: center; padding: 2rem;">
                            Enter text and click "Analyze Text" to see results
                        </p>
                    </div>
                </div>
            </div>
"""

# =============================================================================
# Combined Layout Export
# =============================================================================
LAYOUT = f"""{_HEADER}
    <div class="container">
        <aside class="sidebar">
{_TEXT_INPUT_SECTION}
{_LLM_CONFIG_SECTION}
{_METADATA_SECTION}
{_GLOSSARY_SECTION}
{_CATEGORIES_SECTION}
            <div style=\"display: flex; gap: 0.5rem; flex-wrap: wrap;\">
                <button id=\"analyzeBtn\" style=\"flex: 1; min-width: 45%;\">Analyze Text</button>
                <button id=\"checkCleanBtn\" style=\"flex: 1; min-width: 45%; background: #4CAF50;\">Check Cleanliness</button>
                <button id=\"polishBtn\" style=\"flex: 1; min-width: 45%; background: #2196F3;\">Polish Content</button>
                <button id=\"finalizeBtn\" style=\"flex: 1; min-width: 45%; background: #9C27B0;\">Finalize Content</button>
                <button id=\"glossaryBtn\" style=\"flex: 1; min-width: 100%; background: #FF9800;\">Glossary Lookup</button>
            </div>
        </aside>
        <main class="main">
{_STREAM_PANEL}
{_RESULT_PANEL}
        </main>
    </div>
"""
