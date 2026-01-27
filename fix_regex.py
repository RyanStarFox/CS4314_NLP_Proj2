import re

file_path = "pages/3_📓_错题整理.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find: s = re.sub(r'\([a-zA-Z])', r'\\\1', s)
# We want to replace it with: s = re.sub(r'\\([a-zA-Z])', r'\\\\\\1', s)

# Using plain string replacement to avoid regex confusion in the replacement script itself
bad_line = r"s = re.sub(r'\([a-zA-Z])', r'\\\1', s)"
good_line = r"s = re.sub(r'\\([a-zA-Z])', r'\\\\\\1', s)"

if bad_line in content:
    new_content = content.replace(bad_line, good_line)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully fixed the regex line.")
else:
    print("Could not find the exact bad line. Dumping context around line 236:")
    lines = content.splitlines()
    for i in range(max(0, 230), min(len(lines), 245)):
        print(f"{i+1}: {lines[i]}")

