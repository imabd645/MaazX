/* ── Gemini Agent – Frontend Logic ───────────────────────── */

const chatArea = document.getElementById('chat-area');
const messagesDiv = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const input = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const statusDot = document.getElementById('status-dot');

let isProcessing = false;
let currentAbortController = null;
let currentReader = null;

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
    let ids = ['btn-chat', 'btn-tools', 'btn-wa-view', 'btn-settings', 'btn-jobs', 'btn-health', 'btn-history', 'btn-knowledge', 'btn-gmail', 'btn-db', 'btn-git'];
    ids.forEach(id => {
        let el = document.getElementById(id);
        if (el) el.classList.remove('active');
    });

    let activeBtn = document.getElementById(active);
    if (activeBtn) activeBtn.classList.add('active');

    let toolsPanel = document.getElementById('tools-panel');
    if (toolsPanel) toolsPanel.style.display = active === 'btn-tools' ? 'block' : 'none';

    // Hide all center pane areas
    ['settings-area', 'jobs-area', 'whatsapp-area', 'file-editor-area', 'health-area', 'history-area', 'knowledge-area', 'gmail-area', 'db-area', 'git-area', 'welcome', 'terminal-panel'].forEach(id => {
        let el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
}

if (document.getElementById('btn-chat')) {
    document.getElementById('btn-chat').addEventListener('click', () => {
        switchSidebarTab('btn-chat');
        // Only show welcome if the chat area has no messages
        const messagesDiv = document.getElementById('messages');
        if (messagesDiv && messagesDiv.children.length === 0) {
            document.getElementById('welcome').style.display = 'flex';
        }
    });
}

if (document.getElementById('btn-tools')) {
    document.getElementById('btn-tools').addEventListener('click', () => {
        switchSidebarTab('btn-tools');
        const messagesDiv = document.getElementById('messages');
        if (messagesDiv && messagesDiv.children.length === 0) {
            document.getElementById('welcome').style.display = 'flex';
        }
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

if (document.getElementById('btn-db')) {
    document.getElementById('btn-db').addEventListener('click', () => {
        switchSidebarTab('btn-db');
        document.getElementById('db-area').style.display = 'flex';
        typeof loadDatabases === 'function' && loadDatabases();
    });
}

if (document.getElementById('btn-git')) {
    document.getElementById('btn-git').addEventListener('click', () => {
        switchSidebarTab('btn-git');
        document.getElementById('git-area').style.display = 'flex';
        loadGitStatus();
        loadGitLog();
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

/* Close Panels (Back to Chat) */
document.querySelectorAll('.btn-close-panel').forEach(btn => {
    btn.addEventListener('click', () => {
        // Hide all center pane areas and terminal
        ['settings-area', 'jobs-area', 'whatsapp-area', 'file-editor-area', 'health-area', 'history-area', 'knowledge-area', 'gmail-area', 'db-area', 'terminal-panel'].forEach(id => {
            let el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });

        // Show welcome screen
        const welcome = document.getElementById('welcome');
        if (welcome) welcome.style.display = 'flex';

        // Remove active state from sidebar navigation buttons 
        document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

        // Focus chat input
        const chatInput = document.getElementById('message-input');
        if (chatInput) chatInput.focus();
    });
});

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
    const panes = ['settings-area', 'jobs-area', 'whatsapp-area', 'file-editor-area', 'knowledge-area', 'health-area', 'history-area', 'gmail-area'];
    panes.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = (id === paneId) ? 'flex' : 'none';
    });

    // Hide welcome screen when showing a specific pane
    const welcome = document.getElementById('welcome');
    if (welcome) welcome.style.display = 'none';
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
/* ── Core streaming send / receive ────────────────────────── */
async function sendMessage() {
    const text = input.value.trim();
    if (!text || isProcessing) return;

    isProcessing = true;
    sendBtn.disabled = false; // Keep enabled for stop functionality
    welcome.classList.add('hidden');

    appendMessage('user', text);
    input.value = '';
    input.style.height = 'auto';

    // Transform send button into stop button
    sendBtn.classList.add('stop-mode');
    sendBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>';
    sendBtn.title = 'Stop response';
    sendBtn.onclick = stopResponse;

    // Create AbortController for this request
    currentAbortController = new AbortController();

    // Create the assistant message container early for streaming (includes thinking dots)
    const messageObj = appendStreamingMessage('assistant');
    let fullText = "";
    let hasStartedText = false;

    try {
        const modeSelector = document.getElementById('chat-mode-selector');
        const selectedMode = modeSelector ? modeSelector.value : 'auto';

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, chat_mode: selectedMode }),
            signal: currentAbortController.signal,
        });

        currentReader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await currentReader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));

                        if (data.error) {
                            updateStreamingMessage(messageObj, 'Error: ' + data.error);
                        } else if (data.t === 'text') {
                            if (!hasStartedText) {
                                hasStartedText = true;
                                hideThinkingDots(messageObj);
                            }
                            fullText += data.c;
                            updateStreamingMessage(messageObj, fullText);
                        } else if (data.t === 'tool') {
                            hideThinkingDots(messageObj); // Also hide if tool starts
                            addToolBadge(messageObj, data.n, 'pending');
                        } else if (data.t === 'result') {
                            updateToolBadge(messageObj, data.n, 'success');

                            // Auto-refresh right sidebar if the tool might have changed files or directories
                            const fileModifyingTools = ['create_file', 'edit_file', 'patch_file', 'delete_file', 'run_command', 'write_to_file', 'move_file', 'copy_file'];
                            if (fileModifyingTools.includes(data.n)) {
                                if (typeof loadProjectFiles === 'function') {
                                    setTimeout(() => loadProjectFiles(), 500); // Slight delay to ensure OS sync
                                }
                            }
                        }
                    } catch (e) {
                        console.error("Error parsing SSE chunk:", e);
                    }
                }
            }
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            // User clicked stop — show partial response
            if (!fullText) {
                hideThinkingDots(messageObj);
                updateStreamingMessage(messageObj, '*[Response stopped by user]*');
            }
        } else {
            updateStreamingMessage(messageObj, 'Network error: ' + err.message);
        }
    }

    // Restore send button
    restoreSendButton();
    setStatus('ready');
    isProcessing = false;
    currentAbortController = null;
    currentReader = null;
    input.focus();
}

function stopResponse() {
    // Signal backend to stop generating
    fetch('/api/chat/abort', { method: 'POST' }).catch(() => { });
    // Abort the frontend fetch
    if (currentAbortController) {
        currentAbortController.abort();
    }
    if (currentReader) {
        try { currentReader.cancel(); } catch (e) { }
    }
}

function restoreSendButton() {
    sendBtn.classList.remove('stop-mode');
    sendBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
    sendBtn.title = 'Send message';
    sendBtn.onclick = sendMessage;
    sendBtn.disabled = false;
}

function appendStreamingMessage(role) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const name = role === 'user' ? 'You' : 'MaazX';
    div.innerHTML = `
        <div class="msg-header">
            <div class="msg-avatar ${role === 'user' ? 'user-av' : 'agent-av'}">${role === 'user' ? 'U' : 'A'}</div>
            <span class="msg-name">${name}</span>
        </div>
        <div class="thinking-dots">
            <span></span><span></span><span></span>
        </div>
        <div class="tool-calls"></div>
        <div class="msg-body"></div>
    `;
    messagesDiv.appendChild(div);
    scrollToBottom();
    return div;
}

function hideThinkingDots(div) {
    const dots = div.querySelector('.thinking-dots');
    if (dots) dots.style.display = 'none';
}

function updateStreamingMessage(div, text) {
    const body = div.querySelector('.msg-body');
    body.innerHTML = renderMarkdown(text);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addToolBadge(div, toolName, status) {
    const container = div.querySelector('.tool-calls');
    const badge = document.createElement('span');
    badge.className = `tool-badge ${status}`;
    badge.id = `tool-${toolName}-${Date.now()}`;
    badge.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
        </svg>
        ${escapeHtml(toolName)}
    `;
    container.appendChild(badge);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function updateToolBadge(div, toolName, status) {
    // Find the last badge of this type
    const badges = div.querySelectorAll(`.tool-badge`);
    for (let i = badges.length - 1; i >= 0; i--) {
        if (badges[i].textContent.includes(toolName)) {
            badges[i].className = `tool-badge ${status}`;
            break;
        }
    }
}

/* ── DOM helpers ─────────────────────────────────────────── */
function appendMessage(role, text, toolCalls = []) {
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const isUser = role === 'user';

    const avatarClass = isUser ? 'user-av' : 'agent-av';
    const nameClass = isUser ? 'user-name' : 'agent-name';
    const avatarText = isUser ? 'U' : 'A';
    const nameText = isUser ? 'You' : 'MaazX';

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


function scrollToBottom() {
    chatArea.scrollTop = chatArea.scrollHeight;
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

/* ── Restore chat session from DB on page load ──────────── */
(async function restoreSession() {
    try {
        const res = await fetch('/api/session');
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
            welcome.classList.add('hidden');
            for (const msg of data.messages) {
                const toolCalls = msg.tool_calls || [];
                appendMessage(msg.role, msg.content, toolCalls);
            }
        }
    } catch (err) {
        console.error('Failed to restore session:', err);
    }
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
    if (cmd === 'whoami') {
        appendTermEntry(cmd, 'MaazX - Autonomous Engineering Partner', 0);
        return;
    }
    if (cmd === 'creator') {
        appendTermEntry(cmd, 'Abdullah Masood (UET Lahore)', 0);
        return;
    }
    if (cmd === 'purpose') {
        appendTermEntry(cmd, 'Bridge AI intelligence with real-world engineering', 0);
        return;
    }
    if (cmd === 'status') {
        appendTermEntry(cmd, '● Ready to collaborate', 0);
        return;
    }

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

        // ── Auto-Heal Detection ──
        if (data.exit_code !== 0) {
            const errorPatterns = ['Traceback', 'Error:', 'Exception', 'SyntaxError', 'TypeError', 'NameError', 'ImportError', 'ModuleNotFoundError', 'FileNotFoundError', 'ValueError', 'KeyError', 'AttributeError', 'IndentationError'];
            const hasError = errorPatterns.some(p => data.output.includes(p));
            if (hasError) {
                triggerAutoHeal(cmd, data.output, data.exit_code);
            }
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

/* ── Auto-Heal Engine ── */
async function triggerAutoHeal(command, output, exitCode) {
    // Show pulsing badge in terminal
    const healBadge = document.createElement('div');
    healBadge.className = 'auto-heal-badge';
    healBadge.innerHTML = '🔧 MaazX Auto-Healing...';
    termOutput.appendChild(healBadge);
    scrollTerminal();

    // Also show a message in chat panel
    const messageObj = appendStreamingMessage('assistant');
    let fullText = '';
    hideThinkingDots(messageObj);
    updateStreamingMessage(messageObj, '*🔧 Auto-Healing terminal error...*\n\n');

    try {
        const response = await fetch('/api/terminal/auto_heal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command, output, exit_code: exitCode }),
        });

        // Check if auto-heal is disabled
        if (response.headers.get('content-type')?.includes('application/json')) {
            const jsonData = await response.json();
            if (jsonData.status === 'disabled') {
                healBadge.remove();
                updateStreamingMessage(messageObj, '*Auto-heal is disabled in Settings.*');
                return;
            }
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        if (data.t === 'text') {
                            fullText += data.c;
                            updateStreamingMessage(messageObj, '*🔧 Auto-Healing terminal error...*\n\n' + fullText);
                        } else if (data.t === 'tool') {
                            addToolBadge(messageObj, data.n, 'pending');
                        } else if (data.t === 'result') {
                            updateToolBadge(messageObj, data.n, 'success');
                            // Refresh file explorer if files were changed
                            const fileTools = ['create_file', 'edit_file', 'patch_file', 'delete_file', 'run_command'];
                            if (fileTools.includes(data.n) && typeof loadProjectFiles === 'function') {
                                setTimeout(() => loadProjectFiles(), 500);
                            }
                        }
                    } catch (e) { /* skip malformed SSE */ }
                }
            }
        }

        // Update badge to success
        healBadge.className = 'auto-heal-badge success';
        healBadge.innerHTML = '✅ Auto-heal complete';

    } catch (err) {
        healBadge.className = 'auto-heal-badge';
        healBadge.innerHTML = '❌ Auto-heal failed: ' + err.message;
        healBadge.style.color = 'var(--red)';
        healBadge.style.borderColor = 'rgba(248, 81, 73, 0.3)';
        updateStreamingMessage(messageObj, '*Auto-heal error: ' + err.message + '*');
    }

    scrollTerminal();
}

function appendTermEntry(cmd, output, exitCode, isLoading = false) {
    const div = document.createElement('div');
    div.className = 'term-entry';
    const outClass = isLoading ? 'term-out' : (exitCode === 0 ? 'term-out' : 'term-err');
    div.innerHTML = `
        <div class="term-cmd">
            <span class="term-cmd-prompt" style="color:var(--green); font-weight:bold;">maazx@terminal:~$</span>
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

        const elOpenAI = document.getElementById('setting-openai-key');
        if (elOpenAI) elOpenAI.value = s.openai_api_key || '';

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

        const elWaReplyMode = document.getElementById('setting-wa-reply-mode');
        if (elWaReplyMode) elWaReplyMode.value = s.wa_reply_mode || 'all_contacts';

        const elAutoHeal = document.getElementById('setting-auto-heal');
        if (elAutoHeal) elAutoHeal.checked = s.auto_heal_enabled !== false;
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
        openai_api_key: document.getElementById('setting-openai-key')?.value?.trim() || '',
        wa_admin_numbers: document.getElementById('setting-wa-admins')?.value?.trim() || '',
        wa_owner_name: document.getElementById('setting-wa-owner')?.value?.trim() || 'User',
        google_vision_key_path: document.getElementById('setting-vision-path')?.value?.trim() || '',
        vision_provider: document.getElementById('setting-vision-provider')?.value || 'ollama',
        vision_model: document.getElementById('setting-vision-model')?.value || 'moondream',
        llm_provider: document.getElementById('setting-llm-provider')?.value || 'deepseek',
        llm_local_model: document.getElementById('setting-llm-local-model')?.value?.trim() || 'qwen3:8b',
        wa_reply_mode: document.getElementById('setting-wa-reply-mode')?.value || 'all_contacts',
        auto_heal_enabled: document.getElementById('setting-auto-heal')?.checked !== false,
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
                'gemini-1.5-pro': 'Gemini 1.5 Pro',
                'gemini-1.5-flash': 'Gemini 1.5 Flash',
                'gemma-3-27b': 'Gemma 3 27B',
                'gpt-4.1-mini': 'GPT-4.1 Mini',
                'gpt-4.1-nano': 'GPT-4.1 Nano',
                'gpt-4o': 'GPT-4o',
                'gpt-4o-mini': 'GPT-4o Mini',
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
        const activeJobs = data.jobs || [];
        const historyJobs = data.history || [];

        container.innerHTML = '';

        // Active Section
        const activeHeader = document.createElement('h3');
        activeHeader.style.cssText = 'color:var(--text-primary); margin: 20px 0 10px 0; font-size: 16px; display: flex; align-items:center; gap: 8px;';
        activeHeader.innerHTML = `<span style="width:10px; height:10px; background:var(--green); border-radius:50%;"></span> Active Tasks`;
        container.appendChild(activeHeader);

        if (activeJobs.length === 0) {
            const empty = document.createElement('div');
            empty.style.cssText = 'color:var(--text-secondary); text-align:center; padding: 15px; background:var(--bg-tertiary); border-radius:8px; border:1px dashed var(--border);';
            empty.textContent = 'No active scheduled tasks.';
            container.appendChild(empty);
        } else {
            activeJobs.forEach(job => {
                const el = document.createElement('div');
                el.className = 'job-card';
                el.style.cssText = 'background:var(--bg-primary); border:1px solid var(--border); border-radius:8px; padding:15px; display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;';
                el.innerHTML = `
                    <div>
                        <h4 style="margin:0 0 5px 0; color:var(--text-primary);">${escapeHtml(job.name) || 'Task'}</h4>
                        <div style="font-size:12px; color:var(--text-secondary);">
                            <span style="color:var(--accent);">Next Run:</span> ${job.next_run_time}<br>
                            <span style="color:var(--blue);">Action:</span> ${escapeHtml(job.prompt)}
                        </div>
                    </div>
                    <button class="quick-btn" style="border-color:rgba(248,81,73,0.3); color:#f85149; padding: 6px 12px; font-size: 12px;" onclick="deleteJob('${job.id}')">Remove</button>
                `;
                container.appendChild(el);
            });
        }

        // History Section
        const historyHeader = document.createElement('h3');
        historyHeader.style.cssText = 'color:var(--text-secondary); margin: 30px 0 10px 0; font-size: 16px; display: flex; align-items:center; gap: 8px;';
        historyHeader.innerHTML = `<span style="width:10px; height:10px; background:var(--text-muted); border-radius:50%;"></span> Recently Executed`;
        container.appendChild(historyHeader);

        if (historyJobs.length === 0) {
            const empty = document.createElement('div');
            empty.style.cssText = 'color:var(--text-muted); text-align:center; padding: 15px; font-size: 13px;';
            empty.textContent = 'No history available.';
            container.appendChild(empty);
        } else {
            historyJobs.forEach(job => {
                const el = document.createElement('div');
                el.style.cssText = 'background:rgba(0,0,0,0.1); border:1px solid var(--border); border-radius:8px; padding:12px; display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; opacity: 0.8;';
                const statusColor = job.status === 'completed' ? 'var(--green)' : 'var(--red)';
                el.innerHTML = `
                    <div style="flex:1;">
                        <h4 style="margin:0 0 3px 0; color:var(--text-secondary); font-size: 13px;">${escapeHtml(job.name)}</h4>
                        <div style="font-size:11px; color:var(--text-muted);">
                            <span style="color:${statusColor}; font-weight: 600;">[${job.status.toUpperCase()}]</span> @ ${job.executed_at}
                        </div>
                    </div>
                `;
                container.appendChild(el);
            });
        }

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


/* ── Database Explorer Logic ──────────────────────────────── */
function loadDatabases() {
    fetch('/api/db/list').then(res => res.json()).then(data => {
        const selector = document.getElementById('db-selector');
        if (!selector) return;
        selector.innerHTML = '<option value="">Select Database...</option>';
        if (data.databases) {
            data.databases.forEach(db => {
                let opt = document.createElement('option');
                opt.value = db.path;
                opt.textContent = `${db.name} (${db.size_mb} MB)`;
                selector.appendChild(opt);
            });
        }
    }).catch(err => console.error(err));
}

function loadDatabaseTables(dbPath) {
    const list = document.getElementById('db-table-list');
    list.innerHTML = '<div style="color:var(--text-muted); font-size:12px; text-align:center; margin-top: 20px;">Loading tables...</div>';

    fetch(`/api/db/info?db=${encodeURIComponent(dbPath)}`)
        .then(res => res.json())
        .then(data => {
            list.innerHTML = '';
            if (data.error) {
                list.innerHTML = `<div style="color:var(--red); font-size:12px; padding:10px;">Error: ${data.error}</div>`;
                return;
            }
            if (!data.tables || data.tables.length === 0) {
                list.innerHTML = '<div style="color:var(--text-muted); font-size:12px; text-align:center; margin-top: 20px;">No tables found</div>';
                return;
            }

            data.tables.forEach(t => {
                let item = document.createElement('div');
                item.className = 'db-table-item';
                item.innerHTML = `<span>${t.name}</span> <span class="db-row-count">${t.row_count}</span>`;
                item.onclick = () => {
                    document.querySelectorAll('.db-table-item').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    renderTableData(dbPath, t.name);
                };
                list.appendChild(item);
            });
        }).catch(err => {
            list.innerHTML = `<div style="color:var(--red); font-size:12px; padding:10px;">Error loading tables</div>`;
        });
}

function renderTableData(dbPath, tableName) {
    document.getElementById('db-current-table').textContent = tableName;
    const btnRefresh = document.getElementById('db-refresh-btn');
    const btnQuery = document.getElementById('db-query-btn');

    btnRefresh.style.display = 'inline-block';
    btnQuery.style.display = 'inline-block';

    btnRefresh.onclick = () => renderTableData(dbPath, tableName);
    btnQuery.onclick = () => {
        const query = prompt(`Enter custom SQL query for ${dbPath}:`, `SELECT * FROM \`${tableName}\` LIMIT 10`);
        if (query) executeCustomQuery(dbPath, query);
    };

    const thead = document.getElementById('db-thead');
    const tbody = document.getElementById('db-tbody');
    thead.innerHTML = '<tr><th>Loading data...</th></tr>';
    tbody.innerHTML = '';

    fetch(`/api/db/table?db=${encodeURIComponent(dbPath)}&table=${encodeURIComponent(tableName)}&limit=100`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                thead.innerHTML = '';
                tbody.innerHTML = `<tr><td style="color:var(--red)">Error: ${data.error}</td></tr>`;
                return;
            }

            let trHead = document.createElement('tr');
            data.columns.forEach(col => {
                let th = document.createElement('th');
                th.textContent = col.name;
                trHead.appendChild(th);
            });
            thead.innerHTML = '';
            thead.appendChild(trHead);

            tbody.innerHTML = '';
            if (!data.rows || data.rows.length === 0) {
                tbody.innerHTML = `<tr><td colspan="${data.columns.length}" style="text-align:center; color:var(--text-muted); padding:20px;">Table is empty</td></tr>`;
            } else {
                data.rows.forEach(row => {
                    let tr = document.createElement('tr');
                    data.columns.forEach(col => {
                        let td = document.createElement('td');
                        td.textContent = row[col.name];
                        tr.appendChild(td);
                    });
                    tbody.appendChild(tr);
                });
            }
        }).catch(err => {
            thead.innerHTML = '';
            tbody.innerHTML = `<tr><td style="color:var(--red)">Connection Error</td></tr>`;
        });
}

function executeCustomQuery(dbPath, query) {
    const thead = document.getElementById('db-thead');
    const tbody = document.getElementById('db-tbody');
    thead.innerHTML = '<tr><th>Executing query...</th></tr>';
    tbody.innerHTML = '';

    fetch('/api/db/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ db: dbPath, query: query })
    })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                thead.innerHTML = '<tr><th style="color:var(--red)">Query Error</th></tr>';
                tbody.innerHTML = `<tr><td style="color:var(--red)">${data.error}</td></tr>`;
                return;
            }

            if (data.is_mutation) {
                thead.innerHTML = '<tr><th style="color:var(--green)">Success</th></tr>';
                tbody.innerHTML = `<tr><td>Rows affected: ${data.rows_affected}</td></tr>`;
                loadDatabaseTables(dbPath);
            } else {
                let trHead = document.createElement('tr');
                if (data.columns && data.columns.length > 0) {
                    data.columns.forEach(col => {
                        let th = document.createElement('th');
                        th.textContent = col.name;
                        trHead.appendChild(th);
                    });
                    thead.innerHTML = '';
                    thead.appendChild(trHead);

                    tbody.innerHTML = '';
                    if (!data.rows || data.rows.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="${data.columns.length}" style="text-align:center; color:var(--text-muted); padding:20px;">No results</td></tr>`;
                    } else {
                        data.rows.forEach(row => {
                            let tr = document.createElement('tr');
                            Object.values(row).forEach(val => {
                                let td = document.createElement('td');
                                td.textContent = val;
                                tr.appendChild(td);
                            });
                            tbody.appendChild(tr);
                        });
                    }
                } else {
                    thead.innerHTML = '<tr><th>Result</th></tr>';
                    tbody.innerHTML = `<tr><td>Query executed successfully, no data returned.</td></tr>`;
                }
            }
        })
        .catch(err => {
            thead.innerHTML = '';
            tbody.innerHTML = `<tr><td style="color:var(--red)">Connection Error</td></tr>`;
        });
}

const dbSelector = document.getElementById('db-selector');
if (dbSelector) {
    dbSelector.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val) {
            loadDatabaseTables(val);
            document.getElementById('db-thead').innerHTML = '';
            document.getElementById('db-tbody').innerHTML = '';
            document.getElementById('db-current-table').textContent = 'Select a table';
            document.getElementById('db-refresh-btn').style.display = 'none';
            document.getElementById('db-query-btn').style.display = 'none';
        } else {
            document.getElementById('db-table-list').innerHTML = '<div style="color:var(--text-muted); font-size:12px; text-align:center; margin-top: 20px;">No database selected</div>';
            document.getElementById('db-thead').innerHTML = '';
            document.getElementById('db-tbody').innerHTML = '';
            document.getElementById('db-current-table').textContent = 'Select a table';
            document.getElementById('db-refresh-btn').style.display = 'none';
            document.getElementById('db-query-btn').style.display = 'none';
        }
    });
}

/* ══════════════════════════════════════════════════════════
   GIT / SOURCE CONTROL PANEL
   ══════════════════════════════════════════════════════════ */

async function loadGitStatus() {
    try {
        const res = await fetch('/api/git/status');
        const data = await res.json();
        const branchName = document.getElementById('git-branch-name');
        const syncStatus = document.getElementById('git-sync-status');
        const noRepo = document.getElementById('git-no-repo');
        const changesSection = document.getElementById('git-changes-section');
        const commitSection = document.getElementById('git-commit-section');
        const filesList = document.getElementById('git-files-list');
        const changeCount = document.getElementById('git-change-count');

        if (!data.is_repo) {
            branchName.textContent = 'No Repository';
            syncStatus.textContent = '';
            noRepo.style.display = 'block';
            changesSection.style.display = 'none';
            commitSection.style.display = 'none';
            return;
        }

        noRepo.style.display = 'none';
        changesSection.style.display = 'block';
        commitSection.style.display = 'block';
        branchName.textContent = data.branch;

        let syncParts = [];
        if (data.ahead > 0) syncParts.push(`↑${data.ahead}`);
        if (data.behind > 0) syncParts.push(`↓${data.behind}`);
        syncStatus.textContent = syncParts.length ? syncParts.join(' ') : '✓ In sync';

        changeCount.textContent = `(${data.changed_count})`;

        if (data.changed_files.length === 0) {
            filesList.innerHTML = '<div style="padding:16px; text-align:center; color:var(--text-muted); font-size:13px;">✓ Working tree clean</div>';
            return;
        }

        const statusColors = { 'modified': 'var(--orange)', 'added': 'var(--green)', 'deleted': 'var(--red)', 'untracked': 'var(--text-muted)', 'renamed': 'var(--blue)' };
        const statusLetters = { 'modified': 'M', 'added': 'A', 'deleted': 'D', 'untracked': '?', 'renamed': 'R' };

        filesList.innerHTML = data.changed_files.map(f => `
            <div class="git-file-item">
                <span class="git-file-badge" style="color:${statusColors[f.label] || 'var(--text-muted)'}; border-color:${statusColors[f.label] || 'var(--border)'};">
                    ${statusLetters[f.label] || f.status}
                </span>
                <span class="git-file-name">${escapeHtml(f.file)}</span>
            </div>
        `).join('');
    } catch (err) {
        console.error('Git status error:', err);
    }
}

async function loadGitLog() {
    try {
        const res = await fetch('/api/git/log');
        const data = await res.json();
        const logList = document.getElementById('git-log-list');
        if (!data.commits || data.commits.length === 0) {
            logList.innerHTML = '<div style="padding:16px; text-align:center; color:var(--text-muted); font-size:13px;">No commits yet</div>';
            return;
        }
        logList.innerHTML = data.commits.map(c => `
            <div class="git-commit-item">
                <span class="git-commit-hash">${escapeHtml(c.hash)}</span>
                <span class="git-commit-msg">${escapeHtml(c.message)}</span>
                <span class="git-commit-meta">${escapeHtml(c.author)} • ${escapeHtml(c.date)}</span>
            </div>
        `).join('');
    } catch (err) {
        console.error('Git log error:', err);
    }
}

async function gitAction(url, body) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {})
        });
        const data = await res.json();
        if (data.error) {
            alert('Git Error: ' + data.error);
        } else {
            loadGitStatus();
            loadGitLog();
        }
        return data;
    } catch (err) {
        alert('Network error: ' + err.message);
    }
}

if (document.getElementById('git-commit-btn')) {
    document.getElementById('git-commit-btn').addEventListener('click', async () => {
        const msgEl = document.getElementById('git-commit-msg');
        const message = msgEl.value.trim();
        if (!message) { alert('Please write a commit message.'); msgEl.focus(); return; }
        const result = await gitAction('/api/git/commit', { message });
        if (result && result.success) msgEl.value = '';
    });
}

if (document.getElementById('git-push-btn')) {
    document.getElementById('git-push-btn').addEventListener('click', () => gitAction('/api/git/push'));
}

if (document.getElementById('git-pull-btn')) {
    document.getElementById('git-pull-btn').addEventListener('click', () => gitAction('/api/git/pull'));
}

if (document.getElementById('git-refresh-btn')) {
    document.getElementById('git-refresh-btn').addEventListener('click', () => { loadGitStatus(); loadGitLog(); });
}
