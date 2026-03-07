/* ── Gemini Agent – Frontend Logic ───────────────────────── */

const chatArea = document.getElementById('chat-area');
const messagesDiv = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const input = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const statusDot = document.getElementById('status-dot');

let isProcessing = false;

/* ── Markdown setup ─────────────────────────────────────── */
marked.setOptions({
    highlight: (code, lang) => {
        if (lang && hljs.getLanguage(lang))
            return hljs.highlight(code, { language: lang }).value;
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true,
});

/* ── Sidebar toggles ────────────────────────────────────── */
document.getElementById('toggle-sidebar').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('collapsed');
});

function switchSidebarTab(active) {
    ['btn-chat', 'btn-tools', 'btn-settings'].forEach(id => {
        document.getElementById(id).classList.remove('active');
    });
    document.getElementById(active).classList.add('active');
    document.getElementById('tools-panel').style.display = active === 'btn-tools' ? 'flex' : 'none';
    document.getElementById('settings-panel').style.display = active === 'btn-settings' ? 'flex' : 'none';
}

document.getElementById('btn-chat').addEventListener('click', () => switchSidebarTab('btn-chat'));
document.getElementById('btn-tools').addEventListener('click', () => switchSidebarTab('btn-tools'));
document.getElementById('btn-settings').addEventListener('click', () => {
    switchSidebarTab('btn-settings');
    loadSettings();
});

/* New chat */
document.getElementById('btn-new-chat').addEventListener('click', async () => {
    await fetch('/api/reset', { method: 'POST' });
    messagesDiv.innerHTML = '';
    welcome.classList.remove('hidden');
    input.focus();
});

/* Quick action buttons */
document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const prompt = btn.dataset.prompt;
        input.value = prompt;
        sendMessage();
    });
});

/* ── Auto-resize textarea ───────────────────────────────── */
input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 160) + 'px';
});

/* ── Send on Enter (Shift+Enter for newline) ────────────── */
input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

/* ── Core send / receive ────────────────────────────────── */
async function sendMessage() {
    const text = input.value.trim();
    if (!text || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = true;
    welcome.classList.add('hidden');

    appendMessage('user', text);
    input.value = '';
    input.style.height = 'auto';

    const thinkingEl = showThinking();
    setStatus('thinking');

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        });

        const data = await res.json();
        removeThinking(thinkingEl);

        if (data.error) {
            appendMessage('assistant', 'Error: ' + data.error, []);
        } else {
            appendMessage('assistant', data.reply, data.tool_calls || []);
        }
    } catch (err) {
        removeThinking(thinkingEl);
        appendMessage('assistant', 'Network error: ' + err.message, []);
    }

    setStatus('ready');
    isProcessing = false;
    sendBtn.disabled = false;
    input.focus();
}

/* ── DOM helpers ─────────────────────────────────────────── */
function appendMessage(role, text, toolCalls = []) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const isUser = role === 'user';
    const avatarClass = isUser ? 'user-av' : 'agent-av';
    const nameClass = isUser ? 'user-name' : 'agent-name';
    const avatarText = isUser ? 'U' : 'A';
    const nameText = isUser ? 'You' : 'Agent';

    let toolBadgesHtml = '';
    if (toolCalls.length > 0) {
        const badges = toolCalls.map(tc =>
            `<span class="tool-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                ${escapeHtml(tc.name)}
            </span>`
        ).join('');
        toolBadgesHtml = `<div class="tool-calls">${badges}</div>`;
    }

    const renderedBody = isUser ? escapeHtml(text) : renderMarkdown(text);

    div.innerHTML = `
        <div class="msg-header">
            <div class="msg-avatar ${avatarClass}">${avatarText}</div>
            <span class="msg-name ${nameClass}">${nameText}</span>
        </div>
        ${toolBadgesHtml}
        <div class="msg-body">${renderedBody}</div>
    `;

    messagesDiv.appendChild(div);
    scrollToBottom();
}

function showThinking() {
    const div = document.createElement('div');
    div.className = 'thinking';
    div.innerHTML = `
        <div class="msg-header">
            <div class="msg-avatar agent-av">A</div>
            <span class="msg-name agent-name">Agent</span>
        </div>
        <div class="thinking-dots">
            <span></span><span></span><span></span>
        </div>
    `;
    messagesDiv.appendChild(div);
    scrollToBottom();
    return div;
}

function removeThinking(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
}

function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
}

function setStatus(state) {
    statusDot.style.background = state === 'thinking' ? 'var(--orange)' : 'var(--green)';
    statusDot.style.boxShadow = state === 'thinking' ? '0 0 6px var(--orange)' : '0 0 6px var(--green)';
}

function renderMarkdown(text) {
    try {
        return marked.parse(text);
    } catch {
        return escapeHtml(text);
    }
}

function escapeHtml(str) {
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
}


/* ═══════════════════════════════════════════════════════════
   Working Directory Picker
   ═══════════════════════════════════════════════════════════ */

const cwdDisplay = document.getElementById('cwd-display');
const cwdPathEl = document.getElementById('cwd-path');
const dirModal = document.getElementById('dir-modal');
const dirInput = document.getElementById('dir-input');
const dirSetBtn = document.getElementById('dir-set-btn');
const dirList = document.getElementById('dir-list');
const dirBreadcrumb = document.getElementById('dir-breadcrumb');
const modalClose = document.getElementById('modal-close');

/* Fetch & display current working directory on load */
(async function loadCwd() {
    try {
        const res = await fetch('/api/cwd');
        const data = await res.json();
        cwdPathEl.textContent = data.cwd;
        dirInput.value = data.cwd;
    } catch { /* ignore */ }
})();

/* Open modal */
cwdDisplay.addEventListener('click', () => {
    dirModal.style.display = 'flex';
    browseTo(dirInput.value || '');
});

/* Close modal */
modalClose.addEventListener('click', closeModal);
dirModal.addEventListener('click', (e) => {
    if (e.target === dirModal) closeModal();
});

function closeModal() {
    dirModal.style.display = 'none';
}

/* Set directory from text input */
dirSetBtn.addEventListener('click', () => setCwd(dirInput.value.trim()));
dirInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') setCwd(dirInput.value.trim());
});

async function setCwd(path) {
    if (!path) return;
    try {
        const res = await fetch('/api/cwd', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cwd: path }),
        });
        const data = await res.json();
        if (data.error) {
            alert(data.error);
            return;
        }
        cwdPathEl.textContent = data.cwd;
        dirInput.value = data.cwd;
        closeModal();
    } catch (err) {
        alert('Error setting directory: ' + err.message);
    }
}

/* Browse directories */
async function browseTo(path) {
    dirList.innerHTML = '<div class="dir-loading">Loading...</div>';
    try {
        const res = await fetch('/api/browse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path }),
        });
        const data = await res.json();
        if (data.error) {
            dirList.innerHTML = `<div class="dir-loading">${escapeHtml(data.error)}</div>`;
            return;
        }

        // Update breadcrumb
        renderBreadcrumb(path);

        // Update input
        if (path) dirInput.value = path;

        // Render folder list
        if (data.dirs.length === 0) {
            dirList.innerHTML = '<div class="dir-loading">No subdirectories found</div>';
            return;
        }

        dirList.innerHTML = '';
        data.dirs.forEach(dir => {
            const name = dir.split(/[/\\]/).filter(Boolean).pop() || dir;
            const item = document.createElement('button');
            item.className = 'dir-item';
            item.innerHTML = `
                <span class="dir-item-icon">&#128193;</span>
                <span>${escapeHtml(name)}</span>
                <span class="dir-item-select" data-path="${escapeHtml(dir)}">Select</span>
            `;
            // Click folder name => browse into it
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('dir-item-select')) {
                    // Select button clicked — set as CWD
                    setCwd(dir);
                } else {
                    // Navigate into the folder
                    browseTo(dir);
                }
            });
            dirList.appendChild(item);
        });

    } catch (err) {
        dirList.innerHTML = `<div class="dir-loading">Error: ${escapeHtml(err.message)}</div>`;
    }
}

function renderBreadcrumb(path) {
    dirBreadcrumb.innerHTML = '';
    if (!path) {
        // Show root / drives label
        const span = document.createElement('span');
        span.className = 'dir-crumb';
        span.textContent = 'Drives';
        span.addEventListener('click', () => browseTo(''));
        dirBreadcrumb.appendChild(span);
        return;
    }

    // Split path into segments
    const parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
    let accumulated = '';

    // Root button
    const rootBtn = document.createElement('button');
    rootBtn.className = 'dir-crumb';
    rootBtn.textContent = 'Drives';
    rootBtn.addEventListener('click', () => browseTo(''));
    dirBreadcrumb.appendChild(rootBtn);

    parts.forEach((part, i) => {
        accumulated += part + '/';
        const currentPath = accumulated;

        const sep = document.createElement('span');
        sep.className = 'dir-sep';
        sep.textContent = ' / ';
        dirBreadcrumb.appendChild(sep);

        const btn = document.createElement('button');
        btn.className = 'dir-crumb';
        btn.textContent = part;
        btn.addEventListener('click', () => browseTo(currentPath));
        dirBreadcrumb.appendChild(btn);
    });
}


/* ═══════════════════════════════════════════════════════════
   Integrated Terminal
   ═══════════════════════════════════════════════════════════ */

const termPanel = document.getElementById('terminal-panel');
const termOutput = document.getElementById('terminal-output');
const termInput = document.getElementById('terminal-input');
const termCwd = document.getElementById('terminal-cwd');
const termToggle = document.getElementById('terminal-toggle');
const termClose = document.getElementById('terminal-close');
const termClear = document.getElementById('terminal-clear');

let termHistory = [];
let termHistoryIdx = -1;
let termOpen = false;

/* Toggle terminal */
termToggle.addEventListener('click', () => {
    termOpen = !termOpen;
    termPanel.style.display = termOpen ? 'flex' : 'none';
    termToggle.classList.toggle('active', termOpen);
    if (termOpen) {
        updateTermCwd();
        termInput.focus();
    }
});

termClose.addEventListener('click', () => {
    termOpen = false;
    termPanel.style.display = 'none';
    termToggle.classList.remove('active');
});

termClear.addEventListener('click', () => {
    termOutput.innerHTML = '';
});

/* Update CWD display in terminal header */
async function updateTermCwd() {
    try {
        const res = await fetch('/api/cwd');
        const data = await res.json();
        termCwd.textContent = data.cwd;
    } catch { /* ignore */ }
}

/* Run command on Enter */
termInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const cmd = termInput.value.trim();
        if (!cmd) return;
        termHistory.push(cmd);
        termHistoryIdx = termHistory.length;
        termInput.value = '';
        runTerminalCommand(cmd);
    }
    // Arrow up/down for history
    if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (termHistoryIdx > 0) {
            termHistoryIdx--;
            termInput.value = termHistory[termHistoryIdx];
        }
    }
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (termHistoryIdx < termHistory.length - 1) {
            termHistoryIdx++;
            termInput.value = termHistory[termHistoryIdx];
        } else {
            termHistoryIdx = termHistory.length;
            termInput.value = '';
        }
    }
});

async function runTerminalCommand(cmd) {
    // Show command in output
    appendTermEntry(cmd, 'Running...', 0, true);

    try {
        const res = await fetch('/api/terminal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd }),
        });
        const data = await res.json();

        // Replace the "Running..." with actual output
        const entries = termOutput.querySelectorAll('.term-entry');
        const lastEntry = entries[entries.length - 1];
        if (lastEntry) {
            const outEl = lastEntry.querySelector('.term-out, .term-err');
            if (outEl) {
                outEl.className = data.exit_code === 0 ? 'term-out' : 'term-err';
                outEl.textContent = data.output;
            }
        }

        // Update CWD display (cd commands change it)
        if (data.cwd) {
            termCwd.textContent = data.cwd;
            cwdPathEl.textContent = data.cwd;
        }

    } catch (err) {
        const entries = termOutput.querySelectorAll('.term-entry');
        const lastEntry = entries[entries.length - 1];
        if (lastEntry) {
            const outEl = lastEntry.querySelector('.term-out, .term-err');
            if (outEl) {
                outEl.className = 'term-err';
                outEl.textContent = 'Error: ' + err.message;
            }
        }
    }

    scrollTerminal();
    termInput.focus();
}

function appendTermEntry(cmd, output, exitCode, isLoading = false) {
    const div = document.createElement('div');
    div.className = 'term-entry';
    const outClass = isLoading ? 'term-out' : (exitCode === 0 ? 'term-out' : 'term-err');
    div.innerHTML = `
        <div class="term-cmd">
            <span class="term-cmd-prompt">&gt;</span>
            <span class="term-cmd-text">${escapeHtml(cmd)}</span>
        </div>
        <div class="${outClass}">${escapeHtml(output)}</div>
    `;
    termOutput.appendChild(div);
    scrollTerminal();
}

function scrollTerminal() {
    termOutput.scrollTop = termOutput.scrollHeight;
}


/* ═══════════════════════════════════════════════════════════
   Settings Panel
   ═══════════════════════════════════════════════════════════ */

async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const s = await res.json();

        document.getElementById('setting-tool-mode').value = s.tool_mode || 'any';
        document.getElementById('setting-auto-run').checked = s.auto_run_commands !== false;
        document.getElementById('setting-model').value = s.model_name || 'gemini-2.5-flash';
        document.getElementById('setting-timeout').value = s.command_timeout || 60;
        document.getElementById('setting-depth').value = s.max_dir_depth || 3;
        document.getElementById('setting-openrouter-key').value = s.openrouter_api_key || '';
    } catch { /* ignore */ }
}

document.getElementById('setting-save').addEventListener('click', async () => {
    const settings = {
        tool_mode: document.getElementById('setting-tool-mode').value,
        auto_run_commands: document.getElementById('setting-auto-run').checked,
        model_name: document.getElementById('setting-model').value,
        command_timeout: parseInt(document.getElementById('setting-timeout').value) || 60,
        max_dir_depth: parseInt(document.getElementById('setting-depth').value) || 3,
        openrouter_api_key: document.getElementById('setting-openrouter-key').value.trim(),
    };

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings),
        });
        const data = await res.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        // Show saved indicator
        const savedEl = document.getElementById('setting-saved');
        savedEl.style.display = 'inline';
        setTimeout(() => { savedEl.style.display = 'none'; }, 2000);

        // Update model badge in topbar
        const badge = document.querySelector('.model-badge');
        if (badge) {
            const modelNames = {
                'gemini-2.5-flash': 'Gemini 2.5 Flash',
                'gemini-2.0-flash': 'Gemini 2.0 Flash',
                'gemini-2.5-pro': 'Gemini 2.5 Pro',
                'gemini-2.0-pro': 'Gemini 2.0 Pro',
                'gemma-3-27b': 'Gemma 3 27B',
            };
            badge.textContent = modelNames[settings.model_name] || settings.model_name;
        }
    } catch (err) {
        alert('Error saving settings: ' + err.message);
    }
});
