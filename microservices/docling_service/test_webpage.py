"""Test webpage for Docling Service.

Provides an HTML UI at /test for uploading and testing document conversion.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docling Service Test</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        header h1 { font-size: 1.5rem; font-weight: 600; }
        header p { font-size: 0.875rem; opacity: 0.9; margin-top: 0.25rem; }
        .container {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .sidebar {
            width: 320px;
            background: white;
            padding: 1.5rem;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .main {
            flex: 1;
            padding: 1.5rem;
            overflow: auto;
        }
        .form-group { display: flex; flex-direction: column; gap: 0.5rem; }
        label { font-weight: 500; font-size: 0.875rem; color: #333; }
        select, input[type="file"] {
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.875rem;
        }
        .drop-zone {
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            background: #fafafa;
        }
        .drop-zone:hover, .drop-zone.dragover {
            border-color: #2e7d32;
            background: #e8f5e9;
        }
        .drop-zone p { color: #666; font-size: 0.875rem; }
        .drop-zone .icon { font-size: 2rem; margin-bottom: 0.5rem; }
        .file-info {
            background: #e8f5e9;
            padding: 0.75rem;
            border-radius: 4px;
            font-size: 0.875rem;
            display: none;
        }
        .file-info.show { display: block; }
        button {
            background: #2e7d32;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover { background: #1b5e20; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .formats {
            font-size: 0.75rem;
            color: #666;
            padding: 0.5rem;
            background: #f5f5f5;
            border-radius: 4px;
        }
        .formats strong { display: block; margin-bottom: 0.25rem; }
        .result-panel {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .result-header {
            padding: 1rem;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .result-header h2 { font-size: 1rem; font-weight: 600; }
        .tabs {
            display: flex;
            gap: 0.5rem;
        }
        .tab {
            padding: 0.5rem 1rem;
            background: #f5f5f5;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
        }
        .tab.active { background: #2e7d32; color: white; }
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
        .result-content .markdown-preview {
            line-height: 1.6;
        }
        .result-content .markdown-preview h1 { font-size: 1.5rem; margin: 1rem 0 0.5rem; }
        .result-content .markdown-preview h2 { font-size: 1.25rem; margin: 1rem 0 0.5rem; }
        .result-content .markdown-preview h3 { font-size: 1.1rem; margin: 1rem 0 0.5rem; }
        .result-content .markdown-preview p { margin: 0.5rem 0; }
        .result-content .markdown-preview ul, .result-content .markdown-preview ol { margin: 0.5rem 0 0.5rem 1.5rem; }
        .result-content .markdown-preview table { border-collapse: collapse; margin: 1rem 0; }
        .result-content .markdown-preview th, .result-content .markdown-preview td {
            border: 1px solid #ddd; padding: 0.5rem; text-align: left;
        }
        .result-content .markdown-preview th { background: #f5f5f5; }
        .loading {
            display: none;
            text-align: center;
            padding: 2rem;
        }
        .loading.show { display: block; }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #2e7d32;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .error { color: #c62828; background: #ffebee; padding: 1rem; border-radius: 4px; }
        .stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        .stat {
            background: #e8f5e9;
            padding: 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
        }
        .stat strong { display: block; font-size: 1rem; color: #2e7d32; }
    </style>
</head>
<body>
    <header>
        <h1>📄 Docling Service</h1>
        <p>Multi-format document to markdown converter</p>
    </header>
    <div class="container">
        <aside class="sidebar">
            <div class="form-group">
                <label>Endpoint</label>
                <select id="endpoint">
                    <option value="/convert/to-markdown">Convert to Markdown</option>
                    <option value="/analyze">Analyze (Full Details)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Upload File</label>
                <div class="drop-zone" id="dropZone">
                    <div class="icon">📁</div>
                    <p>Drop file here or click to browse</p>
                </div>
                <input type="file" id="fileInput" hidden
                    accept=".pdf,.docx,.pptx,.xlsx,.html,.htm,.png,.jpg,.jpeg,.tiff,.tif,.wav,.mp3,.vtt,.txt,.md">
            </div>
            <div class="file-info" id="fileInfo"></div>
            <button id="submitBtn" disabled>Convert Document</button>
            <div class="formats">
                <strong>Supported Formats:</strong>
                PDF, DOCX, PPTX, XLSX, HTML, PNG, TIFF, JPEG, WAV, MP3, VTT
            </div>
        </aside>
        <main class="main">
            <div class="result-panel">
                <div class="result-header">
                    <h2>Results</h2>
                    <div class="tabs">
                        <button class="tab active" data-tab="markdown">Markdown</button>
                        <button class="tab" data-tab="preview">Preview</button>
                        <button class="tab" data-tab="json">JSON</button>
                        <button class="tab" data-tab="tables">Tables</button>
                    </div>
                </div>
                <div class="result-content">
                    <div class="loading" id="loading">
                        <div class="spinner"></div>
                        <p>Processing document...</p>
                    </div>
                    <div id="results">
                        <p style="color: #666; text-align: center; padding: 2rem;">
                            Upload a document to see results
                        </p>
                    </div>
                </div>
            </div>
        </main>
    </div>
    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const submitBtn = document.getElementById('submitBtn');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const endpoint = document.getElementById('endpoint');
        const tabs = document.querySelectorAll('.tab');
        
        let selectedFile = null;
        let currentData = null;
        let currentTab = 'markdown';
        
        // Drop zone events
        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) handleFile(fileInput.files[0]);
        });
        
        function handleFile(file) {
            selectedFile = file;
            fileInfo.textContent = `📄 ${file.name} (${formatSize(file.size)})`;
            fileInfo.classList.add('show');
            submitBtn.disabled = false;
        }
        
        function formatSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }
        
        // Tab switching
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentTab = tab.dataset.tab;
                renderResults();
            });
        });
        
        // Submit
        submitBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            loading.classList.add('show');
            results.innerHTML = '';
            submitBtn.disabled = true;
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            try {
                const response = await fetch(endpoint.value, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Conversion failed');
                }
                
                currentData = await response.json();
                renderResults();
            } catch (error) {
                results.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            } finally {
                loading.classList.remove('show');
                submitBtn.disabled = false;
            }
        });
        
        function renderResults() {
            if (!currentData) return;
            
            let html = '';
            
            // Stats
            if (currentData.format || currentData.metadata) {
                html += '<div class="stats">';
                if (currentData.format) {
                    html += `<div class="stat"><strong>${currentData.format.toUpperCase()}</strong>Format</div>`;
                }
                if (currentData.pages?.length) {
                    html += `<div class="stat"><strong>${currentData.pages.length}</strong>Pages</div>`;
                }
                if (currentData.tables?.length) {
                    html += `<div class="stat"><strong>${currentData.tables.length}</strong>Tables</div>`;
                }
                if (currentData.markdown) {
                    html += `<div class="stat"><strong>${currentData.markdown.length.toLocaleString()}</strong>Characters</div>`;
                }
                html += '</div>';
            }
            
            // Content based on tab
            if (currentTab === 'markdown') {
                html += `<pre>${escapeHtml(currentData.markdown || '')}</pre>`;
            } else if (currentTab === 'preview') {
                html += `<div class="markdown-preview">${simpleMarkdownToHtml(currentData.markdown || '')}</div>`;
            } else if (currentTab === 'json') {
                html += `<pre>${escapeHtml(JSON.stringify(currentData, null, 2))}</pre>`;
            } else if (currentTab === 'tables') {
                if (currentData.tables?.length) {
                    currentData.tables.forEach((table, i) => {
                        html += `<h3>Table ${i + 1} (${table.rows}×${table.columns})</h3>`;
                        if (table.html) {
                            html += table.html;
                        } else if (table.markdown) {
                            html += `<pre>${escapeHtml(table.markdown)}</pre>`;
                        }
                    });
                } else {
                    html += '<p style="color: #666;">No tables detected</p>';
                }
            }
            
            results.innerHTML = html;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function simpleMarkdownToHtml(md) {
            return md
                .replace(/^### (.+)$/gm, '<h3>$1</h3>')
                .replace(/^## (.+)$/gm, '<h2>$1</h2>')
                .replace(/^# (.+)$/gm, '<h1>$1</h1>')
                .replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>')
                .replace(/\\*(.+?)\\*/g, '<em>$1</em>')
                .replace(/^- (.+)$/gm, '<li>$1</li>')
                .replace(/(<li>.*<\\/li>)/s, '<ul>$1</ul>')
                .replace(/\\n\\n/g, '</p><p>')
                .replace(/^(.+)$/gm, '<p>$1</p>')
                .replace(/<p><h/g, '<h')
                .replace(/<\\/h(\\d)><\\/p>/g, '</h$1>')
                .replace(/<p><ul>/g, '<ul>')
                .replace(/<\\/ul><\\/p>/g, '</ul>')
                .replace(/<p><\\/p>/g, '');
        }
    </script>
</body>
</html>
"""


@router.get("/test", response_class=HTMLResponse)
async def test_page():
    """Serve the test webpage."""
    return HTML_PAGE
