"""Test webpage for PyMuPDF PDF-to-markdown conversion.

Adds a simple HTML UI at /test for uploading PDFs and viewing results.
Import this module from main.py to mount the test routes.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

TEST_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyMuPDF Service - Test</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; height: 100vh; display: flex; flex-direction: column; background: #f5f5f5; }
        header { background: #2c3e50; color: white; padding: 1rem 1.5rem; flex-shrink: 0; }
        header h1 { font-size: 1.25rem; font-weight: 500; }
        header p { font-size: 0.875rem; opacity: 0.8; margin-top: 0.25rem; }
        .container { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 320px; background: white; border-right: 1px solid #ddd; display: flex; flex-direction: column; flex-shrink: 0; }
        .sidebar-content { padding: 1rem; overflow-y: auto; flex: 1; }
        .sidebar h2 { font-size: 0.875rem; text-transform: uppercase; color: #666; margin-bottom: 1rem; letter-spacing: 0.05em; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 0.5rem; color: #333; }
        .form-group input[type="file"] { width: 100%; padding: 0.5rem; border: 2px dashed #ccc; border-radius: 6px; background: #fafafa; cursor: pointer; }
        .form-group input[type="file"]:hover { border-color: #3498db; background: #f0f8ff; }
        .form-group select { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 6px; font-size: 0.875rem; }
        button { width: 100%; padding: 0.75rem; background: #3498db; color: white; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; font-weight: 500; }
        button:hover { background: #2980b9; }
        button:disabled { background: #bdc3c7; cursor: not-allowed; }
        .file-list { margin-top: 1rem; }
        .file-item { padding: 0.5rem; background: #f9f9f9; border-radius: 4px; margin-bottom: 0.5rem; font-size: 0.875rem; display: flex; justify-content: space-between; align-items: center; }
        .file-item .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
        .file-item .status { font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 3px; margin-left: 0.5rem; }
        .file-item .status.pending { background: #f39c12; color: white; }
        .file-item .status.done { background: #27ae60; color: white; }
        .file-item .status.error { background: #e74c3c; color: white; }
        .results { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .results-header { padding: 1rem; background: white; border-bottom: 1px solid #ddd; flex-shrink: 0; }
        .results-header h2 { font-size: 1rem; color: #333; }
        .results-content { flex: 1; overflow-y: auto; padding: 1rem; }
        .result-card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1rem; overflow: hidden; }
        .result-card-header { padding: 0.75rem 1rem; background: #ecf0f1; border-bottom: 1px solid #ddd; font-weight: 500; display: flex; justify-content: space-between; align-items: center; }
        .result-card-header .filename { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .result-card-header .meta { font-size: 0.75rem; color: #666; }
        .result-card-body { padding: 1rem; }
        .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 1rem; }
        .tab { padding: 0.5rem 1rem; cursor: pointer; border-bottom: 2px solid transparent; font-size: 0.875rem; color: #666; }
        .tab:hover { color: #333; }
        .tab.active { color: #3498db; border-bottom-color: #3498db; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .markdown-preview { white-space: pre-wrap; font-family: 'SF Mono', Consolas, monospace; font-size: 0.8125rem; background: #f8f9fa; padding: 1rem; border-radius: 4px; max-height: 400px; overflow-y: auto; line-height: 1.5; }
        .json-preview { white-space: pre-wrap; font-family: 'SF Mono', Consolas, monospace; font-size: 0.75rem; background: #f8f9fa; padding: 1rem; border-radius: 4px; max-height: 400px; overflow-y: auto; }
        .empty-state { text-align: center; padding: 3rem; color: #999; }
        .empty-state svg { width: 64px; height: 64px; margin-bottom: 1rem; opacity: 0.5; }
        .loading { display: inline-block; width: 16px; height: 16px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 0.5rem; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <header>
        <h1>PyMuPDF Service</h1>
        <p>Upload PDFs to convert to Markdown or analyze document structure</p>
    </header>
    <div class="container">
        <aside class="sidebar">
            <div class="sidebar-content">
                <h2>Upload Files</h2>
                <form id="uploadForm">
                    <div class="form-group">
                        <label for="files">PDF Files</label>
                        <input type="file" id="files" name="files" accept=".pdf" multiple>
                    </div>
                    <div class="form-group">
                        <label for="mode">Conversion Mode</label>
                        <select id="mode" name="mode">
                            <option value="convert">Convert to Markdown</option>
                            <option value="analyze">Full Analysis (with metadata)</option>
                        </select>
                    </div>
                    <button type="submit" id="submitBtn">Process Files</button>
                </form>
                <div class="file-list" id="fileList"></div>
            </div>
        </aside>
        <main class="results">
            <div class="results-header">
                <h2>Results</h2>
            </div>
            <div class="results-content" id="resultsContent">
                <div class="empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p>Upload PDF files to see conversion results</p>
                </div>
            </div>
        </main>
    </div>
    <script>
        const form = document.getElementById('uploadForm');
        const filesInput = document.getElementById('files');
        const modeSelect = document.getElementById('mode');
        const submitBtn = document.getElementById('submitBtn');
        const fileList = document.getElementById('fileList');
        const resultsContent = document.getElementById('resultsContent');
        let results = [];

        filesInput.addEventListener('change', () => {
            fileList.innerHTML = '';
            Array.from(filesInput.files).forEach((file, idx) => {
                const div = document.createElement('div');
                div.className = 'file-item';
                div.id = `file-${idx}`;
                div.innerHTML = `<span class="name">${file.name}</span><span class="status pending">Pending</span>`;
                fileList.appendChild(div);
            });
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const files = filesInput.files;
            if (!files.length) return;

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading"></span>Processing...';
            results = [];
            resultsContent.innerHTML = '';

            const mode = modeSelect.value;
            const endpoint = mode === 'analyze' ? '/analyze/pdf' : '/convert/pdf-to-markdown';

            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const fileItem = document.getElementById(`file-${i}`);
                const statusSpan = fileItem.querySelector('.status');
                statusSpan.className = 'status pending';
                statusSpan.textContent = 'Processing...';

                try {
                    const formData = new FormData();
                    formData.append('file', file);
                    const resp = await fetch(endpoint, { method: 'POST', body: formData });
                    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                    const data = await resp.json();
                    results.push({ filename: file.name, data, mode });
                    statusSpan.className = 'status done';
                    statusSpan.textContent = 'Done';
                } catch (err) {
                    results.push({ filename: file.name, error: err.message, mode });
                    statusSpan.className = 'status error';
                    statusSpan.textContent = 'Error';
                }
            }

            renderResults();
            submitBtn.disabled = false;
            submitBtn.textContent = 'Process Files';
        });

        function renderResults() {
            if (!results.length) {
                resultsContent.innerHTML = '<div class="empty-state"><p>No results yet</p></div>';
                return;
            }
            resultsContent.innerHTML = results.map((r, idx) => {
                if (r.error) {
                    return `<div class="result-card"><div class="result-card-header"><span class="filename">${r.filename}</span><span class="meta" style="color:#e74c3c;">Error: ${r.error}</span></div></div>`;
                }
                const md = r.data.markdown || '';
                const pageCount = r.data.metadata?.page_count || r.data.pages?.length || '?';
                const tabs = r.mode === 'analyze' ? `
                    <div class="tabs">
                        <div class="tab active" onclick="switchTab(${idx}, 'md')">Markdown</div>
                        <div class="tab" onclick="switchTab(${idx}, 'json')">Full JSON</div>
                    </div>
                    <div class="tab-content active" id="tab-${idx}-md"><div class="markdown-preview">${escapeHtml(md)}</div></div>
                    <div class="tab-content" id="tab-${idx}-json"><div class="json-preview">${escapeHtml(JSON.stringify(r.data, null, 2))}</div></div>
                ` : `<div class="markdown-preview">${escapeHtml(md)}</div>`;
                return `<div class="result-card"><div class="result-card-header"><span class="filename">${r.filename}</span><span class="meta">${pageCount} pages</span></div><div class="result-card-body">${tabs}</div></div>`;
            }).join('');
        }

        function switchTab(idx, tab) {
            document.querySelectorAll(`#tab-${idx}-md, #tab-${idx}-json`).forEach(el => el.classList.remove('active'));
            document.getElementById(`tab-${idx}-${tab}`).classList.add('active');
            const card = document.querySelectorAll('.result-card')[idx];
            card.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            card.querySelector(`.tab:nth-child(${tab === 'md' ? 1 : 2})`).classList.add('active');
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""


@router.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """Serve the test webpage."""
    return HTMLResponse(content=TEST_PAGE_HTML)
