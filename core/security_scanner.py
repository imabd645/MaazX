import os
import re
import json

# Compile regexes for performance
# Secrets catching combinations of key words and high entropy strings or known prefixes
SECRET_PATTERNS = [
    (re.compile(r'(?i)(api[_-]?key|secret[_-]?key|password|token|access[_-]?token)\s*[:=]\s*[\'"][A-Za-z0-9_\-]{16,}[\'"]'), "High-entropy secret assignment"),
    (re.compile(r'(?i)(ghp_[A-Za-z0-9]{36}|sk-[a-zA-Z0-9]{48}|sk-ant-[a-zA-Z0-9_\-]{40,})'), "Known provider token (GitHub, OpenAI, Anthropic)"),
    (re.compile(r'(?i)bearer\s+[A-Za-z0-9\-\._~\+\/]+=*'), "Bearer token string"),
]

# Basic SQLi indicators (string concatenation or format strings in queries)
# This is a heuristic and will have false positives, but useful for awareness
SQLI_PATTERNS = [
    (re.compile(r'(?i)(select|insert|update|delete|drop)\s+.*?(%s|%d|%f).*?%'), "Possible SQL injection via old-style string formatting"),
    (re.compile(r'(?i)(select|insert|update|delete|drop)\s+.*?\+'), "Possible SQL injection via string concatenation"),
    (re.compile(r'(?i)f[\'"](select|insert|update|delete|drop).*?\{.*?\}'), "Possible SQL injection via f-string formatting"),
]

# Lightweight vulnerable dependencies check (examples, can be expanded)
# Looking for commonly outdated packages in requirements.txt or package.json
VULNERABLE_PACKAGES = {
    "requirements.txt": [
        ("requests", re.compile(r'requests==([0-1]\.|2\.[0-2][0-9]\.)'), "requests < 2.30.0 may have vulnerabilities"),
        ("flask", re.compile(r'flask==([0-1]\.|2\.0\.)'), "Flask < 2.1.0 has known issues"),
        ("django", re.compile(r'django==([0-3]\.)'), "Django < 4.0 is EOL"),
        ("jinja2", re.compile(r'jinja2==([0-2]\.)'), "Jinja2 < 3.0 has known XSS vulnerabilities"),
    ],
    "package.json": [
        ("react", re.compile(r'"react"\s*:\s*"[\^~]?(15|16|17)\.'), "React < 18 is outdated"),
        ("lodash", re.compile(r'"lodash"\s*:\s*"[\^~]?(3|4\.17\.[0-2][0-1]?)"'), "lodash < 4.17.21 has known prototype pollution"),
    ]
}

def scan_directory(directory_path, limit_files=1000):
    """Scans the directory for vulnerabilities."""
    findings = {
        "secrets": [],
        "sqli": [],
        "dependencies": []
    }
    
    ignore_dirs = {'.git', 'node_modules', 'venv', 'env', '__pycache__', '.venv', '.next', 'dist', 'build'}
    ignore_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg', '.mp4', '.pdf', '.zip', '.tar', '.gz', '.pyc', '.db', '.sqlite', '.sqlite3'}
    
    files_scanned = 0
    
    for root, dirs, files in os.walk(directory_path):
        # Mutate dirs in-place to avoid walking ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        
        for file in files:
            if file.startswith('.'):
                continue
            
            ext = os.path.splitext(file)[1].lower()
            if ext in ignore_extensions:
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, directory_path)
            
            # 1. Dependency Scanning
            if file == "requirements.txt":
                scan_dependencies(file_path, rel_path, "requirements.txt", findings["dependencies"])
                continue
            elif file == "package.json":
                scan_dependencies(file_path, rel_path, "package.json", findings["dependencies"])
                continue
            
            # 2. File Content Scanning (Secrets & SQLi)
            # Skip large files (>1MB) to prevent memory/regex stalling
            try:
                if os.path.getsize(file_path) > 1024 * 1024:
                    continue
            except OSError:
                continue
                
            files_scanned += 1
            if files_scanned > limit_files:
                break # Hard limit to prevent hanging on massive codebases
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    # Fast preliminary checks before running expensive regex
                    line_lower = line.lower()
                    
                    # Secrets
                    if any(kw in line_lower for kw in ['key', 'secret', 'pass', 'token', 'bearer', 'sk-', 'ghp_']):
                        for pattern, desc in SECRET_PATTERNS:
                            if pattern.search(line):
                                findings["secrets"].append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "snippet": line.strip()[:100], # truncate long lines
                                    "description": desc
                                })
                                break # Only flag once per line category
                                
                    # SQLi
                    if any(verb in line_lower for verb in ['select ', 'insert ', 'update ', 'delete ', 'drop ']):
                        for pattern, desc in SQLI_PATTERNS:
                            if pattern.search(line):
                                findings["sqli"].append({
                                    "file": rel_path,
                                    "line": line_num,
                                    "snippet": line.strip()[:100],
                                    "description": desc
                                })
                                break
                                
            except Exception:
                pass # Ignore unreadable files

        if files_scanned > limit_files:
            break
            
    return findings

def scan_dependencies(file_path, rel_path, file_type, results_list):
    """Scans specific dependency files for known outdated/vulnerable packages."""
    if file_type not in VULNERABLE_PACKAGES:
        return
        
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        for pkg_name, pattern, desc in VULNERABLE_PACKAGES[file_type]:
            if pattern.search(content):
                results_list.append({
                    "file": rel_path,
                    "line": 1, # General file level warning
                    "snippet": f"Found potentially vulnerable package: {pkg_name}",
                    "description": desc
                })
    except Exception:
        pass
