import * as vscode from 'vscode';
import * as http from 'http';

export class MaazxProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'maazx.chatView';

    constructor(private readonly _extensionUri: vscode.Uri) { }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(data => {
            switch (data.type) {
                case 'sendMessage':
                    this._sendMessageToBackend(data.text, webviewView);
                    break;
            }
        });
    }

    private _sendMessageToBackend(prompt: string, webviewView: vscode.WebviewView) {
        // Collect editor context
        const editor = vscode.window.activeTextEditor;
        let contextData = "";

        if (editor) {
            const fileName = editor.document.fileName;
            const selection = editor.document.getText(editor.selection);
            contextData = `\n\n[Active VS Code File: ${fileName}]\n`;
            if (selection) {
                contextData += `[Selected Text:\n${selection}\n]\n`;
            }
        }

        const fullMessage = prompt + contextData;

        const postData = JSON.stringify({ message: fullMessage });

        const options = {
            hostname: 'localhost',
            port: 5000,
            path: '/api/chat',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = http.request(options, (res) => {
            res.on('data', (chunk) => {
                webviewView.webview.postMessage({ type: 'streamChunk', value: chunk.toString() });
            });
            res.on('end', () => {
                webviewView.webview.postMessage({ type: 'streamEnd' });
            });
        });

        req.on('error', (e) => {
            webviewView.webview.postMessage({ type: 'error', value: `Connection to MaazX server failed. Is python web_app.py running? Error: ${e.message}` });
        });

        req.write(postData);
        req.end();
    }

    private _getHtmlForWebview(webview: vscode.Webview) {
        // Minimal UI for testing extension bridge before porting full glassmorphism UI
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MaazX</title>
            <style>
                body {
                    padding: 0;
                    margin: 0;
                    font-family: var(--vscode-font-family);
                    color: var(--vscode-editor-foreground);
                    background-color: var(--vscode-editor-background);
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                }
                #chat-area {
                    flex: 1;
                    padding: 15px;
                    overflow-y: auto;
                }
                .message {
                    margin-bottom: 20px;
                    line-height: 1.5;
                }
                .message-user {
                    color: var(--vscode-textPreformat-foreground);
                }
                .input-area {
                    padding: 15px;
                    border-top: 1px solid var(--vscode-panel-border);
                    display: flex;
                    flex-direction: column;
                }
                textarea {
                    width: 100%;
                    background: var(--vscode-input-background);
                    color: var(--vscode-input-foreground);
                    border: 1px solid var(--vscode-input-border);
                    resize: vertical;
                    padding: 8px;
                    min-height: 60px;
                    margin-bottom: 8px;
                    box-sizing: border-box;
                    font-family: var(--vscode-font-family);
                }
                button {
                    background: var(--vscode-button-background);
                    color: var(--vscode-button-foreground);
                    border: none;
                    padding: 8px 16px;
                    cursor: pointer;
                    width: 100%;
                }
                button:hover {
                    background: var(--vscode-button-hoverBackground);
                }
            </style>
        </head>
        <body>
            <div id="chat-area">
                <div class="message"><b>MaazX:</b> Hello! I am connected to your VS Code editor. What can I help you build?</div>
            </div>
            <div class="input-area">
                <textarea id="message-input" placeholder="Ask MaazX..."></textarea>
                <button id="send-btn">Send prompt</button>
            </div>
            <script>
                const vscode = acquireVsCodeApi();
                
                const chatArea = document.getElementById('chat-area');
                const messageInput = document.getElementById('message-input');
                const sendBtn = document.getElementById('send-btn');
                
                let currentDiv = null;

                function sendMsg() {
                    const text = messageInput.value.trim();
                    if (text) {
                        chatArea.innerHTML += '<div class="message"><b class="message-user">You:</b> ' + text + '</div>';
                        vscode.postMessage({ type: 'sendMessage', text: text });
                        messageInput.value = '';
                        
                        currentDiv = document.createElement('div');
                        currentDiv.className = 'message';
                        currentDiv.innerHTML = '<b>MaazX:</b> ';
                        chatArea.appendChild(currentDiv);
                        chatArea.scrollTop = chatArea.scrollHeight;
                    }
                }

                sendBtn.addEventListener('click', sendMsg);
                messageInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMsg();
                    }
                });

                window.addEventListener('message', event => {
                    const message = event.data;
                    switch (message.type) {
                        case 'streamChunk':
                            const lines = message.value.split('\\n');
                            lines.forEach(line => {
                                if (line.startsWith('data: ')) {
                                    try {
                                        let jsonStr = line.substring(6);
                                        let data = JSON.parse(jsonStr);
                                        if (data.t === 'text') {
                                            currentDiv.innerHTML += data.c;
                                        }
                                        chatArea.scrollTop = chatArea.scrollHeight;
                                    } catch (e) {}
                                }
                            });
                            break;
                        case 'error':
                            chatArea.innerHTML += '<div class="message" style="color:var(--vscode-errorForeground)">' + message.value + '</div>';
                            break;
                    }
                });
            </script>
        </body>
        </html>`;
    }
}
