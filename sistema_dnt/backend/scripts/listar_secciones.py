with open('sistema_dnt/frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '<section' in line and 'id=' in line:
        print(f"Línea {i+1}: {line.strip()[:80]}")
