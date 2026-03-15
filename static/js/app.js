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
    let ids = ['btn-chat', 'btn-tools', 'btn-wa-view', 'btn-settings', 'btn-jobs', 'btn-health', 'btn-history', 'btn-knowledge', 'btn-gmail'];
    ids.forEach(id => {
        let el = document.getElementById(id);
        if (el) el.classList.remove('active');
    });

    let activeBtn = document.getElementById(active);
    if (activeBtn) activeBtn.classList.add('active');

    let toolsPanel = document.getElementById('tools-panel');
    if (toolsPanel) toolsPanel.style.display = active === 'btn-tools' ? 'block' : 'none';

    // Hide all center pane areas
    ['settings-area', 'jobs-area', 'whatsapp-area', 'file-editor-area', 'health-area', 'history-area', 'knowledge-area', 'gmail-area', 'welcome'].forEach(id => {
        let el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
}

if (document.getElementById('btn-chat')) {
    document.getElementById('btn-chat').addEventListener('click', () => {
        switchSidebarTab('btn-chat');
        // Chat button just shows the welcome screen in the center
        document.getElementById('welcome').style.display = 'flex';
    });
}

if (document.getElementById('btn-tools')) {
    document.getElementById('btn-tools').addEventListener('click', () => {
        switchSidebarTab('btn-tools');
        document.getElementById('welcome').style.display = 'flex';
    });
}

if (document.getElementById('btn-wa-view')) {
    document.getElementById('btn-wa-view').addEventListener('click', () => {
        switchSidebarTab('btn-whatsapp');
        document.getElementById('whatsapp-area').style.display = 'flex';
    });
}

if (document.getElementById('btn-settings')) {
    document.getElementById('btn-settings').addEventListener('click', () => {
        switchSidebarTab('btn-settings');
        document.getElementById('settings-area').style.display = 'flex';
        loadSettings();
    });
}

if (document.getElementById('btn-jobs')) {
    document.getElementById('btn-jobs').addEventListener('click', () => {
        switchSidebarTab('btn-jobs');
        document.getElementById('jobs-area').style.display = 'flex';
        loadJobs();
    });
}

if (document.getElementById('btn-health')) {
    document.getElementById('btn-health').addEventListener('click', () => {
        switchSidebarTab('btn-health');
        document.getElementById('health-area').style.display = 'flex';
        updateHealthStatus();
    });
}

if (document.getElementById('btn-history')) {
    document.getElementById('btn-history').addEventListener('click', () => {
        switchSidebarTab('btn-history');
        document.getElementById('history-area').style.display = 'flex';
        loadChatHistoryList();
    });
}

if (document.getElementById('btn-gmail')) {
    document.getElementById('btn-gmail').addEventListener('click', () => {
        switchSidebarTab('btn-gmail');
        document.getElementById('gmail-area').style.display = 'flex';
        updateGmailStatus();
    });
}

if (document.getElementById('btn-knowledge')) {
    document.getElementById('btn-knowledge').addEventListener('click', () => {
        switchSidebarTab('btn-knowledge');
        document.getElementById('knowledge-area').style.display = 'flex';
        if (typeof loadKnowledgeBase === 'function') loadKnowledgeBase();
    });
}

if (document.getElementById('btn-tools')) {
    document.getElementById('btn-tools').addEventListener('click', () => switchSidebarTab('btn-tools'));
}

/* Theme Toggle */
const btnThemeToggle = document.getElementById('btn-theme-toggle');
if (btnThemeToggle) {
    const isLight = localStorage.getItem('theme') === 'light';
    const hljsTheme = document.getElementById('hljs-theme');
    const svgPath = document.getElementById('theme-icon-path');

    if (isLight) {
        document.body.classList.add('light-theme');
        if (hljsTheme) hljsTheme.href = "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css";
        if (svgPath) svgPath.setAttribute('d', 'M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z');
    }

    btnThemeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        const lightOn = document.body.classList.contains('light-theme');
        localStorage.setItem('theme', lightOn ? 'light' : 'dark');

        if (hljsTheme) {
            hljsTheme.href = lightOn
                ? "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css"
                : "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css";
        }

        if (svgPath) {
            if (lightOn) {
                svgPath.setAttribute('d', 'M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z'); // Moon
            } else {
                svgPath.setAttribute('d', 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z'); // Sun
            }
        }
    });
}

/* New chat */
if (document.getElementById('btn-new-chat')) {
    document.getElementById('btn-new-chat').addEventListener('click', async () => {
        if (!confirm('Start a new chat session? This will clear the current view, but you can find this conversation in History later.')) return;

        switchSidebarTab('btn-chat');
        document.getElementById('welcome').style.display = 'flex';

        try {
            const res = await fetch('/api/reset', { method: 'POST' });
            const data = await res.json();

            messagesDiv.innerHTML = '';
            // Clear history listing if visible so it refreshes next time
            const historyContainer = document.getElementById('history-list-container');
            if (historyContainer) historyContainer.innerHTML = '';

            input.focus();
            console.log('New session started:', data.session);
        } catch (err) {
            console.error('Failed to reset session:', err);
        }
    });
}

/* Legacy button listeners removed */

/* Sidebar Navigation Pane Manager */
function showCenterPane(paneId) {
    const panes = ['settings-area', 'jobs-area', 'whatsapp-area', 'file-editor-area', 'knowledge-area'];
    panes.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = (id === paneId) ? 'flex' : 'none';
    });
    document.getElementById('welcome').style.display = 'none';
}

if (document.getElementById('btn-settings')) {
    document.getElementById('btn-settings').addEventListener('click', () => {
        showCenterPane('settings-area');
        loadSettings();
    });
}

if (document.getElementById('btn-jobs')) {
    document.getElementById('btn-jobs').addEventListener('click', () => {
        showCenterPane('jobs-area');
        loadJobs();
    });
}

if (document.getElementById('btn-wa-view')) {
    document.getElementById('btn-wa-view').addEventListener('click', () => {
        showCenterPane('whatsapp-area');
        loadWhatsAppContacts();
    });
}

if (document.getElementById('btn-knowledge')) {
    document.getElementById('btn-knowledge').addEventListener('click', () => {
        showCenterPane('knowledge-area');
        loadKnowledgeBase();
    });
}

/* WhatsApp Logout */
if (document.getElementById('wa-logout-btn')) {
    document.getElementById('wa-logout-btn').addEventListener('click', async () => {
        if (!confirm('Are you sure you want to log out of the WhatsApp session?')) return;

        const btn = document.getElementById('wa-logout-btn');
        const oldText = btn.textContent;
        btn.textContent = 'Logging out...';
        btn.disabled = true;

        try {
            await fetch('/api/whatsapp/logout', { method: 'POST' });
            alert('Logged out successfully! You will need to scan a new QR code to reconnect.');
        } catch (err) {
            alert('Failed to log out.');
        } finally {
            btn.textContent = oldText;
            btn.disabled = false;
        }
    });
}

/* Quick action buttons */
document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const prompt = btn.dataset.prompt;
        if (prompt) {
            input.value = prompt;
            sendMessage();
        }
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
    let hasEditingTool = false;

    if (toolCalls.length > 0) {
        const badges = toolCalls.map(tc => {
            if (['create_file', 'edit_file', 'patch_file', 'run_command'].includes(tc.name)) {
                hasEditingTool = true;
            }
            return `<span class="tool-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                ${escapeHtml(tc.name)}
            </span>`;
        }).join('');

        let undoBtnHtml = '';
        if (hasEditingTool && role === 'assistant') {
            undoBtnHtml = `<button class="undo-btn" onclick="undoLastAction(this)">
                <i>↶</i> Undo Action
            </button>`;
        }

        toolBadgesHtml = `<div class="tool-calls">${badges}${undoBtnHtml}</div>`;
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

async function undoLastAction(btn) {
    if (!confirm("Revert the last agent tool action? This will undo the most recent file change and restore your previous work state.")) {
        return;
    }

    btn.disabled = true;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = `<i>⏳</i> Undoing...`;

    try {
        const res = await fetch('/api/undo', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            btn.innerHTML = `<i>✓</i> Undone`;
            btn.style.color = "var(--green)";
            btn.style.background = "rgba(16, 185, 129, 0.1)";
            btn.style.borderColor = "var(--green)";
            alert(data.message);
        } else {
            btn.innerHTML = `<i>❌</i> Failed`;
            alert("Undo failed: " + data.message);
        }
    } catch (e) {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        alert("Network error calling undo.");
    }
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
        loadProjectFiles(); // Also load the right sidebar file tree
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
        loadProjectFiles(); // Refresh the right sidebar
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

        const elToolMode = document.getElementById('setting-tool-mode');
        if (elToolMode) elToolMode.value = s.tool_mode || 'any';

        const elAutoRun = document.getElementById('setting-auto-run');
        if (elAutoRun) elAutoRun.checked = s.auto_run_commands !== false;

        const elModel = document.getElementById('setting-model');
        if (elModel) elModel.value = s.model_name || 'gemini-2.5-flash';

        const elTimeout = document.getElementById('setting-timeout');
        if (elTimeout) elTimeout.value = s.command_timeout || 60;

        const elDepth = document.getElementById('setting-depth');
        if (elDepth) elDepth.value = s.max_dir_depth || 3;

        const elOpRouter = document.getElementById('setting-openrouter-key');
        if (elOpRouter) elOpRouter.value = s.openrouter_api_key || '';

        const elDeepSeek = document.getElementById('setting-deepseek-key');
        if (elDeepSeek) elDeepSeek.value = s.deepseek_api_key || '';

        const elGemini = document.getElementById('setting-gemini-key');
        if (elGemini) elGemini.value = s.gemini_api_key || '';

        const elAdmins = document.getElementById('setting-wa-admins');
        if (elAdmins) elAdmins.value = s.wa_admin_numbers || '';

        const elOwner = document.getElementById('setting-wa-owner');
        if (elOwner) elOwner.value = s.wa_owner_name || 'User';

        const elVisionPath = document.getElementById('setting-vision-path');
        if (elVisionPath) elVisionPath.value = s.google_vision_key_path || '';

        const elVisionProvider = document.getElementById('setting-vision-provider');
        if (elVisionProvider) elVisionProvider.value = s.vision_provider || 'ollama';

        const elVisionModel = document.getElementById('setting-vision-model');
        if (elVisionModel) elVisionModel.value = s.vision_model || 'moondream';

        const elLLMProvider = document.getElementById('setting-llm-provider');
        if (elLLMProvider) elLLMProvider.value = s.llm_provider || 'deepseek';

        const elLLMLocalModel = document.getElementById('setting-llm-local-model');
        if (elLLMLocalModel) elLLMLocalModel.value = s.llm_local_model || 'qwen3:8b';
    } catch { /* ignore */ }
}

document.getElementById('setting-save').addEventListener('click', async () => {
    const settings = {
        tool_mode: document.getElementById('setting-tool-mode')?.value || 'any',
        auto_run_commands: document.getElementById('setting-auto-run')?.checked !== false,
        model_name: document.getElementById('setting-model')?.value || 'gemini-2.5-flash',
        command_timeout: parseInt(document.getElementById('setting-timeout')?.value) || 60,
        max_dir_depth: parseInt(document.getElementById('setting-depth')?.value) || 3,
        openrouter_api_key: document.getElementById('setting-openrouter-key')?.value?.trim() || '',
        deepseek_api_key: document.getElementById('setting-deepseek-key')?.value?.trim() || '',
        gemini_api_key: document.getElementById('setting-gemini-key')?.value?.trim() || '',
        wa_admin_numbers: document.getElementById('setting-wa-admins')?.value?.trim() || '',
        wa_owner_name: document.getElementById('setting-wa-owner')?.value?.trim() || 'User',
        google_vision_key_path: document.getElementById('setting-vision-path')?.value?.trim() || '',
        vision_provider: document.getElementById('setting-vision-provider')?.value || 'ollama',
        vision_model: document.getElementById('setting-vision-model')?.value || 'moondream',
        llm_provider: document.getElementById('setting-llm-provider')?.value || 'deepseek',
        llm_local_model: document.getElementById('setting-llm-local-model')?.value?.trim() || 'qwen3:8b',
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


let indexingInterval = null;

document.getElementById('btn-index-codebase').addEventListener('click', async () => {
    const btn = document.getElementById('btn-index-codebase');
    const statusText = document.getElementById('indexing-status-text');

    btn.disabled = true;
    statusText.textContent = "Starting indexer...";

    try {
        await fetch('/api/index_codebase', { method: 'POST' });

        if (indexingInterval) clearInterval(indexingInterval);

        indexingInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/indexing_status');
                const data = await res.json();

                if (data.status === 'indexing') {
                    statusText.textContent = `Indexing... ${data.progress}%`;
                } else if (data.status === 'idle') {
                    clearInterval(indexingInterval);
                    statusText.textContent = "Indexing complete! Semantic search ready.";
                    btn.disabled = false;
                } else if (data.status.startsWith('error')) {
                    clearInterval(indexingInterval);
                    statusText.textContent = `Failed: ${data.status}`;
                    btn.disabled = false;
                }
            } catch (e) {
                console.error(e);
            }
        }, 1000);

    } catch (err) {
        statusText.textContent = "Error triggering indexing.";
        btn.disabled = false;
    }
});

/* ═══════════════════════════════════════════════════════════
   WhatsApp Contacts Management
   ═══════════════════════════════════════════════════════════ */

const waSelect = document.getElementById('wa-contact-select');
const waPhone = document.getElementById('wa-phone');
const waName = document.getElementById('wa-name');
const waRules = document.getElementById('wa-rules');
const waSaveBtn = document.getElementById('wa-save-btn');

let waContactsCache = [];

async function loadWaContacts() {
    try {
        const res = await fetch('/api/whatsapp/contacts');
        waContactsCache = await res.json();

        waSelect.innerHTML = '<option value="new">-- Add New Contact --</option>';
        waContactsCache.forEach((contact, idx) => {
            const opt = document.createElement('option');
            opt.value = idx.toString();
            opt.textContent = `${contact.name} (${contact.phone_number})`;
            waSelect.appendChild(opt);
        });
    } catch (err) {
        console.error("Error loading WA contacts:", err);
    }
}

const waDeleteBtn = document.getElementById('wa-delete-btn');

if (waSelect) {
    waSelect.addEventListener('change', () => {
        const val = waSelect.value;
        if (val === 'new') {
            waPhone.value = '';
            waName.value = '';
            waRules.value = '';
            waPhone.readOnly = false;
            waSaveBtn.textContent = 'Add New Contact';
            if (waDeleteBtn) waDeleteBtn.style.display = 'none';
        } else {
            const contact = waContactsCache[parseInt(val)];
            waPhone.value = contact.phone_number;
            waName.value = contact.name || '';
            waRules.value = contact.rules || '';
            waPhone.readOnly = true; // Prevent changing phone number of existing edit
            waSaveBtn.textContent = 'Save Changes';
            if (waDeleteBtn) waDeleteBtn.style.display = 'block';
        }
    });

    waSaveBtn.addEventListener('click', async () => {
        let phone = waPhone.value.trim();
        if (!phone) {
            alert('Phone number is required');
            return;
        }

        // Auto-correct and validate the phone number format
        phone = phone.replace(/[^0-9c.us@g]/gi, ''); // Strip invalid characters

        if (phone.startsWith('0')) {
            alert('Invalid Format: Do not use a leading zero. Please start with your country code (e.g. 923350806140).');
            return;
        }

        if (phone.length < 10 && !phone.includes('@')) {
            alert('Invalid Format: Phone number appears too short. Did you include the country code?');
            return;
        }

        // Auto-append @c.us if the user forgot it
        if (!phone.includes('@c.us') && !phone.includes('@g.us')) {
            phone = `${phone}@c.us`;
            waPhone.value = phone; // Update the UI so they see the corrected form
        }

        const payload = {
            phone_number: phone,
            name: waName.value.trim(),
            rules: waRules.value.trim()
        };

        waSaveBtn.textContent = 'Saving...';
        waSaveBtn.disabled = true;

        try {
            await fetch('/api/whatsapp/contacts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            waSaveBtn.textContent = 'Saved!';
            setTimeout(() => {
                waSaveBtn.textContent = 'Save Contact Rule';
                waSaveBtn.disabled = false;
            }, 1500);

            // Reload the dropdown to reflect saved data
            await loadWaContacts();

            // Reselect the saved contact in dropdown
            const idx = waContactsCache.findIndex(c => c.phone_number === phone);
            if (idx !== -1) waSelect.value = idx.toString();

        } catch (err) {
            alert('Failed to save WA contact');
            waSaveBtn.textContent = 'Save Contact Rule';
            waSaveBtn.disabled = false;
        }
    });

    if (waDeleteBtn) {
        waDeleteBtn.addEventListener('click', async () => {
            const phone = waPhone.value.trim();
            if (!phone) return;
            if (!confirm(`Are you sure you want to delete the contact rule for ${phone}?`)) return;

            waDeleteBtn.textContent = 'Deleting...';
            waDeleteBtn.disabled = true;

            try {
                await fetch('/api/whatsapp/contacts', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone_number: phone })
                });

                waDeleteBtn.textContent = 'Deleted!';
                setTimeout(() => {
                    waDeleteBtn.textContent = 'Delete Contact';
                    waDeleteBtn.disabled = false;
                }, 1500);

                await loadWaContacts();

                // Reset to "Add New Contact" mode
                waSelect.value = 'new';
                waSelect.dispatchEvent(new Event('change'));

            } catch (err) {
                alert('Failed to delete WA contact');
                waDeleteBtn.textContent = 'Delete Contact';
                waDeleteBtn.disabled = false;
            }
        });
    }

    const waClearContactBtn = document.getElementById('wa-clear-contact-btn');
    if (waClearContactBtn) {
        waClearContactBtn.addEventListener('click', async () => {
            const phone = waPhone.value.trim();
            if (!phone) {
                alert('Select or enter a contact first to clear their history.');
                return;
            }
            if (!confirm(`Are you sure you want to clear AI conversation history with ${phone}? This cannot be undone.`)) {
                return;
            }
            try {
                const res = await fetch('/api/whatsapp/history', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone_number: phone })
                });
                const data = await res.json();
                if (data.success) {
                    alert('History cleared successfully for this contact.');
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (err) {
                alert('Failed to clear history');
            }
        });
    }

    const waClearAllBtn = document.getElementById('wa-clear-all-btn');
    if (waClearAllBtn) {
        waClearAllBtn.addEventListener('click', async () => {
            if (!confirm('Are you ABSOLUTELY sure you want to clear ALL WhatsApp history for ALL contacts?')) {
                return;
            }
            try {
                const res = await fetch('/api/whatsapp/history', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();
                if (data.success) {
                    alert('All WhatsApp conversation history has been cleared.');
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (err) {
                alert('Failed to clear all history');
            }
        });
    }

    // Load immediately
    loadWaContacts();
}

/* ── Jobs Logic ────────────────────────────────────────── */
async function loadJobs() {
    const container = document.getElementById('jobs-list-container');
    if (!container) return;

    container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding: 20px;">Fetching jobs...</div>';

    try {
        const res = await fetch('/api/jobs');
        const data = await res.json();
        const jobs = data.jobs || [];

        if (jobs.length === 0) {
            container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding: 20px;">No scheduled tasks currently active. Ask the AI to schedule one!</div>';
            return;
        }

        container.innerHTML = '';
        jobs.forEach(job => {
            const el = document.createElement('div');
            el.style.cssText = 'background:var(--bg-primary); border:1px solid var(--border); border-radius:8px; padding:15px; display:flex; justify-content:space-between; align-items:center;';
            el.innerHTML = `
                <div>
                    <h4 style="margin:0 0 5px 0; color:var(--text-primary);">${job.name || 'Task'}</h4>
                    <div style="font-size:13px; color:var(--text-secondary);">
                        <span style="color:var(--accent);">Next Run:</span> ${job.next_run_time}<br>
                        <span style="color:var(--green);">Action:</span> ${job.prompt || 'No specific prompt found'}
                    </div>
                </div>
                <button class="quick-btn" style="border-color:red; color:red;" onclick="deleteJob('${job.id}')">Remove</button>
            `;
            container.appendChild(el);
        });

    } catch (err) {
        container.innerHTML = `<div style="color:red; text-align:center; padding: 20px;">Failed to load jobs: ${err.message}</div>`;
    }
}

window.deleteJob = async function (jobId) {
    if (!confirm('Are you sure you want to delete this scheduled task?')) return;

    try {
        const res = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            loadJobs();
        } else {
            alert('Failed to delete job: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        alert('Exception while deleting job: ' + err.message);
    }
}

if (document.getElementById('jobs-refresh-btn')) {
    document.getElementById('jobs-refresh-btn').addEventListener('click', loadJobs);
}

/* ── Project Explorer Logic ────────────────────────────── */

function renderFileTree(nodes, indent = 0) {
    if (!nodes || nodes.length === 0) return '';
    let html = '';
    nodes.forEach(node => {
        const pad = indent * 15;
        const icon = node.is_dir ? '&#128193;' : '&#128196;';

        // Properly escape for JS string injection
        const safePath = node.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

        if (node.is_dir) {
            html += `<div class="file-tree-item" style="padding-left: ${pad + 10}px;" title="${escapeHtml(node.path)}">
                <span class="file-tree-icon">${icon}</span>
                <span>${escapeHtml(node.name)}</span>
            </div>`;
        } else {
            // If it's a file, open the Direct File Viewer modal
            html += `<div class="file-tree-item" style="padding-left: ${pad + 10}px;" title="${escapeHtml(node.path)}" 
                onclick="openFileViewer('${safePath}')">
                <span class="file-tree-icon">${icon}</span>
                <span>${escapeHtml(node.name)}</span>
            </div>`;
        }

        if (node.is_dir && node.children && node.children.length > 0) {
            html += renderFileTree(node.children, indent + 1);
        }
    });
    return html;
}

async function loadProjectFiles() {
    const container = document.getElementById('right-sidebar-content');
    if (!container) return;

    try {
        const res = await fetch('/api/project_files');
        const data = await res.json();

        if (data.error) {
            container.innerHTML = `<div style="color:red; padding: 10px; font-size:12px;">Error: ${escapeHtml(data.error)}</div>`;
            return;
        }

        if (!data.tree || data.tree.length === 0) {
            container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding: 20px; font-size:13px;">No files found or directory is empty.</div>';
            return;
        }

        container.innerHTML = renderFileTree(data.tree);

    } catch (err) {
        container.innerHTML = `<div style="color:red; padding: 10px; font-size:12px;">Failed to load project files: ${escapeHtml(err.message)}</div>`;
    }
}

/* ── Full-Pane File Editor ───────────────────────────── */
const fileEditorArea = document.getElementById('file-editor-area');
const editorFilename = document.getElementById('editor-filename');
const editorTextarea = document.getElementById('editor-textarea');
const editorLoading = document.getElementById('editor-loading');
const editorCloseBtn = document.getElementById('editor-close-btn');
const editorSaveBtn = document.getElementById('editor-save-btn');
const editorApproveBtn = document.getElementById('editor-approve-btn');

let currentActiveFilePath = null;

if (editorCloseBtn) {
    editorCloseBtn.addEventListener('click', () => {
        fileEditorArea.style.display = 'none';

        // Show welcome screen instead of messing with chat visibility
        let welcomeEl = document.getElementById('welcome');
        if (welcomeEl) welcomeEl.style.display = 'flex';

        currentActiveFilePath = null;
    });
}

if (editorApproveBtn) {
    editorApproveBtn.addEventListener('click', () => {
        fileEditorArea.style.display = 'none';

        let welcomeEl = document.getElementById('welcome');
        if (welcomeEl) welcomeEl.style.display = 'flex';

        currentActiveFilePath = null;

        // Auto-approve the plan
        const input = document.getElementById('message-input');
        input.value = "I approve the plan, please proceed. Enable auto-run for commands if necessary.";
        document.getElementById('send-btn').click();
    });
}

if (editorSaveBtn) {
    editorSaveBtn.addEventListener('click', async () => {
        if (!currentActiveFilePath) return;

        const content = editorTextarea.value;
        const originalText = editorSaveBtn.textContent;
        editorSaveBtn.textContent = 'Saving...';
        editorSaveBtn.disabled = true;

        try {
            const res = await fetch('/api/save_file', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: currentActiveFilePath, content: content })
            });
            const data = await res.json();

            if (data.error) {
                alert(`Error saving file: ${data.error}`);
            } else {
                editorSaveBtn.textContent = 'Saved!';
                editorSaveBtn.style.color = "var(--green)";
            }
        } catch (err) {
            alert(`Network error saving file: ${err.message}`);
        } finally {
            setTimeout(() => {
                editorSaveBtn.textContent = originalText;
                editorSaveBtn.style.color = "";
                editorSaveBtn.disabled = false;
            }, 2000);
        }
    });
}

async function openFileViewer(path) {
    if (!fileEditorArea) return;

    currentActiveFilePath = path;

    // Switch to Chat Tab if we are elsewhere (Settings/Jobs)
    const btnChat = document.getElementById('btn-chat');
    if (btnChat && !btnChat.classList.contains('active')) {
        btnChat.click();
    }

    // Hide welcome, show editor
    let welcomeEl = document.getElementById('welcome');
    if (welcomeEl) welcomeEl.style.display = 'none';

    fileEditorArea.style.display = 'flex';

    // Extract filename for header
    const filename = path.split(/[/\\]/).filter(Boolean).pop() || path;
    editorFilename.textContent = filename;
    editorFilename.title = path; // Tooltip for full path

    // Show "Approve Plan" button if reading an implementation plan
    if (filename.toLowerCase() === 'implementation_plan.md') {
        editorApproveBtn.style.display = 'inline-flex';
    } else {
        editorApproveBtn.style.display = 'none';
    }

    editorTextarea.value = '';
    editorTextarea.style.display = 'none';
    editorLoading.style.display = 'block';
    editorLoading.textContent = 'Fetching file...';

    try {
        const res = await fetch(`/api/file_content?path=${encodeURIComponent(path)}`);
        const data = await res.json();

        if (data.error) {
            editorLoading.textContent = `Error: ${data.error}`;
            return;
        }

        editorLoading.style.display = 'none';
        editorTextarea.style.display = 'block';
        editorTextarea.value = data.content;

    } catch (err) {
        editorLoading.textContent = `Network Error: ${err.message}`;
    }
}

// ── Knowledge Base ─────────────────────────────────────────

async function loadKnowledgeBase() {
    const container = document.getElementById('kb-list-container');
    if (!container) return;

    container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding: 20px;">Loading documents...</div>';

    try {
        const res = await fetch('/api/knowledge/list');
        const data = await res.json();

        container.innerHTML = '';
        if (!data.files || data.files.length === 0) {
            container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding: 20px;">No documents uploaded yet.</div>';
            return;
        }

        data.files.forEach(file => {
            const sizeKB = (file.size / 1024).toFixed(1);
            const div = document.createElement('div');
            div.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:var(--bg-tertiary); padding: 15px; border-radius:8px; border:1px solid var(--border);';
            div.innerHTML = `
                <div style="display:flex; flex-direction:column;">
                    <span style="font-weight:600; color:var(--text-primary); font-size:14px;">${file.filename}</span>
                    <span style="font-size:12px; color:var(--text-muted); margin-top:4px;">${sizeKB} KB</span>
                </div>
                <button class="quick-btn" onclick="deleteKnowledgeDoc('${file.filename}')" style="color:#f85149; border-color:transparent; padding:6px 10px;" title="Delete Document">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6"/></svg>
                </button>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        container.innerHTML = `<div style="color:#f85149; padding: 20px;">Failed to load documents: ${err.message}</div>`;
    }
}

// Attach to window so onclick can find it
window.deleteKnowledgeDoc = async function (filename) {
    if (!confirm(`Are you sure you want to delete ${filename} from the AI Knowledge Base?`)) return;

    try {
        const res = await fetch('/api/knowledge/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        loadKnowledgeBase();
    } catch (err) {
        alert('Failed to delete document: ' + err.message);
    }
};

const kbUploadBtn = document.getElementById('kb-upload-btn');
const kbFileInput = document.getElementById('kb-file-input');
if (kbUploadBtn && kbFileInput) {
    kbUploadBtn.addEventListener('click', () => kbFileInput.click());

    kbFileInput.addEventListener('change', async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const originalText = kbUploadBtn.textContent;
        kbUploadBtn.textContent = 'Uploading...';
        kbUploadBtn.disabled = true;

        try {
            for (let i = 0; i < files.length; i++) {
                const formData = new FormData();
                formData.append('file', files[i]);

                const res = await fetch('/api/knowledge/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();

                if (!res.ok) throw new Error(data.error || 'Upload failed');
            }
            loadKnowledgeBase();
        } catch (err) {
            alert('Upload error: ' + err.message);
        } finally {
            kbUploadBtn.textContent = originalText;
            kbUploadBtn.disabled = false;
            kbFileInput.value = ''; // Reset input
        }
    });
}
const chatUploadBtn = document.getElementById('chat-upload-btn');
const chatFileInput = document.getElementById('chat-file-input');

if (chatUploadBtn && chatFileInput) {
    chatUploadBtn.addEventListener('click', () => chatFileInput.click());

    chatFileInput.addEventListener('change', async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        chatUploadBtn.style.color = 'var(--accent)';
        chatUploadBtn.style.opacity = '0.5';
        chatUploadBtn.disabled = true;

        try {
            let names = [];
            for (let i = 0; i < files.length; i++) {
                const formData = new FormData();
                formData.append('file', files[i]);
                names.push(files[i].name);

                const res = await fetch('/api/knowledge/upload', {
                    method: 'POST',
                    body: formData
                });
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.error || 'Upload failed');
                }
            }

            // Successfully uploaded. Now trigger the agent.
            const inputEl = document.getElementById('message-input');
            const fileList = names.join(', ');
            inputEl.value = `I have uploaded ${fileList} to the Knowledge Base. Please search these documents and tell me what they are about, and answer any relevant questions.`;

            // Trigger auto-send
            document.getElementById('send-btn').click();

            // Refresh Knowledge Base list if visible elsewhere
            if (typeof loadKnowledgeBase === 'function') loadKnowledgeBase();

        } catch (err) {
            alert('Upload error: ' + err.message);
        } finally {
            chatUploadBtn.style.color = '';
            chatUploadBtn.style.opacity = '';
            chatUploadBtn.disabled = false;
            chatFileInput.value = ''; // Reset input
        }
    });
}

// ── Health Dashboard Logic ───────────────────────────────
let healthPollingInterval = null;

async function updateHealthStatus() {
    const logContent = document.getElementById('health-log-content');
    if (!logContent) return;

    const log = (msg) => {
        const time = new Date().toLocaleTimeString();
        logContent.innerHTML += `<div>[${time}] ${msg}</div>`;
        logContent.scrollTop = logContent.scrollHeight;
    };

    try {
        const res = await fetch('/api/health');
        const data = await res.json();

        // Update indicators
        updateIndicator('gemini', data.gemini);
        updateIndicator('deepseek', data.deepseek);
        updateIndicator('bridge', data.bridge);

        if (data.bridge === 'offline') {
            log('<span style="color:var(--red)">BRIDGE OFFLINE: Connection to Node.js failed.</span>');
        }

    } catch (err) {
        log('<span style="color:var(--red)">HEALTH CHECK FAILED: Backend unreachable.</span>');
    }
}

function updateIndicator(service, status) {
    const indicator = document.getElementById(`status-${service}`);
    const desc = document.getElementById(`desc-${service}`);
    if (!indicator || !desc) return;

    indicator.className = 'status-indicator'; // Reset

    if (status === 'online') {
        indicator.textContent = 'Operational';
        indicator.classList.add('status-online');
        desc.textContent = 'Service is running normally.';
    } else if (status === 'offline') {
        indicator.textContent = 'Offline';
        indicator.classList.add('status-offline');
        desc.textContent = 'Connection timeout or process stopped.';
    } else {
        indicator.textContent = 'Error';
        indicator.classList.add('status-warning');
        desc.textContent = status; // Show exact error
    }
}

// Start polling
if (!healthPollingInterval) {
    updateHealthStatus();
    healthPollingInterval = setInterval(updateHealthStatus, 15000); // Poll every 15s
}

const btnRestartBridge = document.getElementById('btn-restart-bridge');
if (btnRestartBridge) {
    btnRestartBridge.addEventListener('click', async () => {
        const originalText = btnRestartBridge.innerHTML;
        btnRestartBridge.innerHTML = 'Restarting...';
        btnRestartBridge.disabled = true;

        try {
            const res = await fetch('/api/restart_bridge', { method: 'POST' });
            const data = await res.json();

            if (data.success) {
                alert('Restart command sent! Waiting for bridge to re-initialize...');
                setTimeout(updateHealthStatus, 5000);
            } else {
                throw new Error(data.error);
            }
        } catch (err) {
            alert('Restart failed: ' + err.message);
        } finally {
            btnRestartBridge.innerHTML = originalText;
            btnRestartBridge.disabled = false;
        }
    });
}

// ── History Management ────────────────────────────────────
async function loadChatHistoryList() {
    const container = document.getElementById('history-list-container');
    if (!container) return;

    container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding: 20px;">Fetching past sessions...</div>';

    try {
        const res = await fetch('/api/history');
        const data = await res.json();

        if (!data.sessions || data.sessions.length === 0) {
            container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding: 40px;">No chat history found. Start a new chat to begin!</div>';
            return;
        }

        container.innerHTML = '';
        data.sessions.forEach(session => {
            const date = new Date(session.last_ts * 1000).toLocaleString();
            const card = document.createElement('div');
            card.className = 'history-card';
            card.innerHTML = `
                <div class="history-info">
                    <div class="history-session-id">Session: ${session.session}</div>
                    <div class="history-meta">
                        <span>${session.msg_count} messages</span>
                        <span>Last active: ${date}</span>
                    </div>
                </div>
                <div class="history-actions">
                    <button class="delete-btn" title="Delete Session">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"></polyline>
                            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                        </svg>
                    </button>
                </div>
            `;

            // Click to load
            card.addEventListener('click', (e) => {
                if (e.target.closest('.delete-btn')) return;
                loadPastSession(session.session);
            });

            // Click to delete
            const delBtn = card.querySelector('.delete-btn');
            delBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (confirm('Are you sure you want to delete this session? This cannot be undone.')) {
                    await deleteSession(session.session);
                }
            });

            container.appendChild(card);
        });

    } catch (err) {
        container.innerHTML = `<div style="color:var(--red); text-align:center; padding: 20px;">Error loading history: ${err.message}</div>`;
    }
}

async function loadPastSession(sessionId) {
    try {
        const res = await fetch(`/api/history/${sessionId}`);
        const data = await res.json();

        // Switch back to chat view
        switchSidebarTab('btn-chat');
        document.getElementById('welcome').style.display = 'none';

        // Clear and load messages
        const messagesContainer = document.getElementById('messages');
        messagesContainer.innerHTML = '';

        data.messages.forEach(msg => {
            appendMessage(msg.role, msg.content, msg.tool_calls);
        });

        // Update current session ID in app context if possible or just visual
        window.current_session_id = sessionId;

    } catch (err) {
        alert('Failed to load session: ' + err.message);
    }
}

async function deleteSession(sessionId) {
    try {
        const res = await fetch(`/api/history/${sessionId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            loadChatHistoryList(); // Refresh
        } else {
            throw new Error(data.error || 'Delete failed');
        }
    } catch (err) {
        alert('Error deleting session: ' + err.message);
    }
}

document.getElementById('history-refresh-btn')?.addEventListener('click', loadChatHistoryList);

/* ── Gmail Integration Logic ────────────────────────────── */
async function updateGmailStatus() {
    const statusIcon = document.getElementById('gmail-status-icon');
    const statusText = document.getElementById('gmail-status-text');
    const statusDesc = document.getElementById('gmail-status-desc');
    const connectBtn = document.getElementById('btn-gmail-connect');
    const disconnectBtn = document.getElementById('btn-gmail-disconnect');

    if (!statusIcon) return;

    try {
        const res = await fetch('/api/gmail/status');
        const data = await res.json();

        if (data.connected) {
            statusIcon.textContent = '✅';
            statusText.textContent = 'Gmail Connected';
            statusDesc.textContent = 'Your Google account is linked. The AI can now access your emails.';
            connectBtn.style.display = 'none';
            disconnectBtn.style.display = 'block';
        } else {
            statusIcon.textContent = '📧';
            statusText.textContent = 'Gmail Disconnected';
            statusDesc.textContent = 'Connect your Google account to enable email capabilities.';
            connectBtn.style.display = 'block';
            disconnectBtn.style.display = 'none';
        }
    } catch (err) {
        statusText.textContent = 'Error checking status';
        console.error(err);
    }
}

document.getElementById('btn-gmail-connect')?.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/gmail/auth');
        const data = await res.json();
        if (data.auth_url) {
            window.open(data.auth_url, '_blank', 'width=600,height=700');
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        alert('Failed to start Gmail auth.');
    }
});

document.getElementById('btn-gmail-disconnect')?.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to disconnect your Gmail account?')) return;
    try {
        await fetch('/api/gmail/logout', { method: 'POST' });
        updateGmailStatus();
    } catch (err) {
        alert('Failed to disconnect Gmail.');
    }
});

// Periodic check if area is visible
setInterval(() => {
    const area = document.getElementById('gmail-area');
    if (area && area.style.display === 'flex') {
        updateGmailStatus();
    }
}, 5000);

