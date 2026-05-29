#!/usr/bin/env python3
"""Apply v8 patch to existing bar_management project"""
import os
import sys

def patch_file(filename, patch_content, marker, before=True):
    if not os.path.exists(filename):
        print(f"ERROR: {filename} not found!")
        return False
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    if patch_content.strip() in content:
        print(f"SKIP: {filename} already patched")
        return True
    if marker not in content:
        print(f"ERROR: Marker '{marker}' not found in {filename}")
        return False
    if before:
        content = content.replace(marker, patch_content + '\n\n' + marker)
    else:
        content = content.replace(marker, marker + '\n\n' + patch_content)
    backup = filename + '.v7backup'
    if not os.path.exists(backup):
        with open(backup, 'w', encoding='utf-8') as f:
            f.write(open(filename, 'r', encoding='utf-8').read())
        print(f"  Backup: {backup}")
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  Patched: {filename}")
    return True

def main():
    print("=" * 50)
    print("Bar Management v7 -> v8 Patch Applier (FIXED)")
    print("=" * 50)
    print()
    patches = ['patch_sbis_api.py', 'patch_models.py', 'patch_app.py']
    for p in patches:
        if not os.path.exists(p):
            print(f"ERROR: {p} not found.")
            sys.exit(1)
    print("[1/3] Patching sbis_api.py...")
    with open('patch_sbis_api.py', 'r', encoding='utf-8') as f:
        patch = f.read()
    if 'class SbisAPI:' in open('sbis_api.py').read():
        patch_file('sbis_api.py', patch, 'class SbisAPI:')
    else:
        patch_file('sbis_api.py', patch, 'class SbisRetailAPI:')
    print("[2/3] Patching models.py...")
    with open('patch_models.py', 'r', encoding='utf-8') as f:
        patch = f.read()
    with open('models.py', 'r') as f:
        lines = f.readlines()
    last_class_line = None
    for i, line in enumerate(lines):
        if line.startswith('class ') and '(db.Model)' in line:
            last_class_line = i
    if last_class_line is not None:
        marker = lines[last_class_line].rstrip()
        patch_file('models.py', patch, marker)
    else:
        print("ERROR: No db.Model classes found in models.py")
    print("[3/3] Patching app.py...")
    with open('patch_app.py', 'r', encoding='utf-8') as f:
        patch = f.read()
    if 'v8_openings' in open('app.py').read():
        print("SKIP: app.py already has v8 routes")
    else:
        patch_file('app.py', patch, "if __name__ == '__main__':")
    print()
    print("=" * 50)
    print("Done!")
    print("=" * 50)

if __name__ == '__main__':
    main()
