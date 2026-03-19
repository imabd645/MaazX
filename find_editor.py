with open(r'F:\AI Agnet\static\js\app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
for i, line in enumerate(lines):
    if 'editor-textarea' in line or 'editor-filename' in line or 'editor-loading' in line or 'editor-save-btn' in line or 'editor-close-btn' in line:
        out.append(f"[{i+1}] {line.strip()}\n")
    if 'loadFile(' in line or 'function loadFile' in line:
        out.append(f"--- func loadFile [{i+1}] ---\n")

with open(r'F:\AI Agnet\out.txt', 'w', encoding='utf-8') as f:
    f.writelines(out)
