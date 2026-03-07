/* ── Gemini Agent – Frontend Logic ───────────────────────── */

const chatArea    = document.getElementById('chat-area');
const messagesDiv = document.getElementById('messages');
const welcome     = document.getElementById('welcome');
const input       = document.getElementById('message-input');
const sendBtn     = document.getElementById('send-btn');
const statusDot   = document.getElementById('status-dot');

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

document.getElementById('btn-chat').addEventListener('click', () => {
    document.getElementById('btn-chat').classList.add('active');
    document.getElementById('btn-tools').classList.remove('active');
    document.getElementById('tools-panel').style.display = 'none';
});

document.getElementById('btn-tools').addEventListener('click', () => {
    document.getElementById('btn-tools').classList.add('active');
    document.getElementById('btn-chat').classList.remove('active');
    document.getElementById('tools-panel').style.display = 'flex';
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

    // Add user message
    appendMessage('user', text);
    input.value = '';
    input.style.height = 'auto';

    // Show thinking indicator
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
            appendMessage('assistant', `⚠️ Error: ${data.error}`, []);
        } else {
            appendMessage('assistant', data.reply, data.tool_calls || []);
        }
    } catch (err) {
        removeThinking(thinkingEl);
        appendMessage('assistant', `⚠️ Network error: ${err.message}`, []);
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
    const nameClass   = isUser ? 'user-name' : 'agent-name';
    const avatarText  = isUser ? 'U' : '⚡';
    const nameText    = isUser ? 'You' : 'Agent';

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
            <div class="msg-avatar agent-av">⚡</div>
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
    statusDot.style.boxShadow  = state === 'thinking' ? '0 0 6px var(--orange)' : '0 0 6px var(--green)';
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
