"""Test webpage for chunking service.

Adds a simple HTML UI at /test for uploading markdown/text files and viewing chunking results.
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
    <title>Chunking Service - Test</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; height: 100vh; display: flex; flex-direction: column; background: #f5f5f5; }
        header { background: #27ae60; color: white; padding: 1rem 1.5rem; flex-shrink: 0; }
        header h1 { font-size: 1.25rem; font-weight: 500; }
        header p { font-size: 0.875rem; opacity: 0.8; margin-top: 0.25rem; }
        .container { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 360px; background: white; border-right: 1px solid #ddd; display: flex; flex-direction: column; flex-shrink: 0; }
        .sidebar-content { padding: 1rem; overflow-y: auto; flex: 1; }
        .sidebar h2 { font-size: 0.875rem; text-transform: uppercase; color: #666; margin-bottom: 1rem; letter-spacing: 0.05em; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; font-size: 0.875rem; font-weight: 500; margin-bottom: 0.5rem; color: #333; }
        .form-group input[type="file"] { width: 100%; padding: 0.5rem; border: 2px dashed #ccc; border-radius: 6px; background: #fafafa; cursor: pointer; }
        .form-group input[type="file"]:hover { border-color: #27ae60; background: #f0fff4; }
        .form-group input[type="number"], .form-group select, .form-group textarea { width: 100%; padding: 0.5rem; border: 1px solid #ccc; border-radius: 6px; font-size: 0.875rem; font-family: inherit; }
        .form-group textarea { min-height: 120px; resize: vertical; }
        .form-group .hint { font-size: 0.75rem; color: #888; margin-top: 0.25rem; }
        .form-row { display: flex; gap: 1rem; }
        .form-row .form-group { flex: 1; }
        button { width: 100%; padding: 0.75rem; background: #27ae60; color: white; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; font-weight: 500; }
        button:hover { background: #219a52; }
        button:disabled { background: #bdc3c7; cursor: not-allowed; }
        .file-info { margin-top: 1rem; padding: 0.5rem; background: #e8f5e9; border-radius: 4px; font-size: 0.875rem; }
        .results { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .results-header { padding: 1rem; background: white; border-bottom: 1px solid #ddd; flex-shrink: 0; display: flex; justify-content: space-between; align-items: center; }
        .results-header h2 { font-size: 1rem; color: #333; }
        .results-header .stats { font-size: 0.875rem; color: #666; }
        .results-content { flex: 1; overflow-y: auto; padding: 1rem; }
        .chunk-card { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 0.75rem; overflow: hidden; }
        .chunk-card-header { padding: 0.5rem 1rem; background: #e8f5e9; border-bottom: 1px solid #c8e6c9; font-weight: 500; display: flex; justify-content: space-between; align-items: center; font-size: 0.875rem; }
        .chunk-card-header .index { color: #27ae60; }
        .chunk-card-header .meta { font-size: 0.75rem; color: #666; font-weight: normal; }
        .chunk-card-body { padding: 0.75rem 1rem; }
        .chunk-text { white-space: pre-wrap; font-family: 'SF Mono', Consolas, monospace; font-size: 0.8125rem; background: #f8f9fa; padding: 0.75rem; border-radius: 4px; max-height: 200px; overflow-y: auto; line-height: 1.5; }
        .chunk-metadata { margin-top: 0.5rem; font-size: 0.75rem; color: #888; }
        .empty-state { text-align: center; padding: 3rem; color: #999; }
        .empty-state svg { width: 64px; height: 64px; margin-bottom: 1rem; opacity: 0.5; }
        .loading { display: inline-block; width: 16px; height: 16px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 0.5rem; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .or-divider { text-align: center; color: #999; font-size: 0.875rem; margin: 1rem 0; position: relative; }
        .or-divider::before, .or-divider::after { content: ''; position: absolute; top: 50%; width: 40%; height: 1px; background: #ddd; }
        .or-divider::before { left: 0; }
        .or-divider::after { right: 0; }
    </style>
</head>
<body>
    <header>
        <h1>Chunking Service</h1>
        <p>Upload markdown/text files or paste text to test chunking with configurable parameters</p>
    </header>
    <div class="container">
        <aside class="sidebar">
            <div class="sidebar-content">
                <h2>Input</h2>
                <form id="chunkForm">
                    <div class="form-group">
                        <label for="file">Upload File (.md, .txt)</label>
                        <input type="file" id="file" name="file" accept=".md,.txt,.text">
                    </div>
                    <div class="or-divider">or paste text</div>
                    <div class="form-group">
                        <label for="textInput">Text Content</label>
                        <textarea id="textInput" name="textInput" placeholder="Paste your text here..."></textarea>
                    </div>
                    <h2 style="margin-top: 1.5rem;">Parameters</h2>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="chunkSize">Chunk Size</label>
                            <input type="number" id="chunkSize" name="chunkSize" value="1000" min="1">
                        </div>
                        <div class="form-group">
                            <label for="chunkOverlap">Overlap</label>
                            <input type="number" id="chunkOverlap" name="chunkOverlap" value="200" min="0">
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="language">Language Hint</label>
                        <select id="language" name="language">
                            <option value="">Auto-detect</option>
                            <option value="english">English</option>
                            <option value="chinese">Chinese</option>
                        </select>
                        <div class="hint">Auto-detects CJK characters if not specified</div>
                    </div>
                    <div class="form-group">
                        <label for="keepSeparator">Keep Separator</label>
                        <select id="keepSeparator" name="keepSeparator">
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                        </select>
                    </div>
                    <button type="submit" id="submitBtn">Chunk Text</button>
                </form>
                <div class="file-info" id="fileInfo" style="display: none;"></div>
            </div>
        </aside>
        <main class="results">
            <div class="results-header">
                <h2>Chunks</h2>
                <div class="stats" id="stats"></div>
            </div>
            <div class="results-content" id="resultsContent">
                <div class="empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 6h16M4 12h16m-7 6h7" />
                    </svg>
                    <p>Upload a file or paste text to see chunking results</p>
                </div>
            </div>
        </main>
    </div>
    <script>
        const form = document.getElementById('chunkForm');
        const fileInput = document.getElementById('file');
        const textInput = document.getElementById('textInput');
        const submitBtn = document.getElementById('submitBtn');
        const fileInfo = document.getElementById('fileInfo');
        const resultsContent = document.getElementById('resultsContent');
        const stats = document.getElementById('stats');

        fileInput.addEventListener('change', async () => {
            const file = fileInput.files[0];
            if (file) {
                const text = await file.text();
                textInput.value = text;
                fileInfo.style.display = 'block';
                fileInfo.textContent = `Loaded: ${file.name} (${text.length} chars)`;
            }
        });

        textInput.addEventListener('input', () => {
            fileInfo.style.display = 'none';
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = textInput.value.trim();
            if (!text) {
                alert('Please provide text to chunk');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading"></span>Chunking...';

            const payload = {
                text: text,
                chunk_size: parseInt(document.getElementById('chunkSize').value) || 1000,
                chunk_overlap: parseInt(document.getElementById('chunkOverlap').value) || 200,
                language_hint: document.getElementById('language').value || null,
                keep_separator: document.getElementById('keepSeparator').value === 'true',
                metadata: { source: fileInput.files[0]?.name || 'pasted_text' }
            };

            try {
                const resp = await fetch('/chunk', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const data = await resp.json();
                renderResults(data.chunks, text.length);
            } catch (err) {
                resultsContent.innerHTML = `<div class="empty-state" style="color: #e74c3c;">Error: ${err.message}</div>`;
                stats.textContent = '';
            }

            submitBtn.disabled = false;
            submitBtn.textContent = 'Chunk Text';
        });

        function renderResults(chunks, totalChars) {
            if (!chunks || !chunks.length) {
                resultsContent.innerHTML = '<div class="empty-state"><p>No chunks generated</p></div>';
                stats.textContent = '';
                return;
            }

            const avgLen = Math.round(chunks.reduce((sum, c) => sum + c.text.length, 0) / chunks.length);
            stats.textContent = `${chunks.length} chunks | avg ${avgLen} chars | input ${totalChars} chars`;

            resultsContent.innerHTML = chunks.map((chunk, idx) => {
                const meta = chunk.metadata || {};
                const metaStr = Object.entries(meta).map(([k, v]) => `${k}: ${v}`).join(' | ');
                return `
                    <div class="chunk-card">
                        <div class="chunk-card-header">
                            <span class="index">Chunk ${idx + 1}</span>
                            <span class="meta">${chunk.text.length} chars</span>
                        </div>
                        <div class="chunk-card-body">
                            <div class="chunk-text">${escapeHtml(chunk.text)}</div>
                            ${metaStr ? `<div class="chunk-metadata">${escapeHtml(metaStr)}</div>` : ''}
                        </div>
                    </div>
                `;
            }).join('');
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
