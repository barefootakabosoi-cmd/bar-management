#!/usr/bin/env python3
"""Apply v8 patch to existing bar_management project"""
import os
import sys

def patch_file(filename, patch_content, marker, before=True):
    """Insert patch_content before/after marker in filename"""
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

    # Backup
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
    print("Bar Management v7 -> v8 Patch Applier")
    print("=" * 50)
    print()

    patches = ['patch_sbis_api.py', 'patch_models.py', 'patch_app.py']
    for p in patches:
        if not os.path.exists(p):
            print(f"ERROR: {p} not found. Run from bar_management_v7 directory.")
            sys.exit(1)

    print("[1/3] Patching sbis_api.py...")
    with open('patch_sbis_api.py', 'r', encoding='utf-8') as f:
        patch = f.read()
    patch_file('sbis_api.py', patch, 'class SbisRetailAPI')

    print("[2/3] Patching models.py...")
    with open('patch_models.py', 'r', encoding='utf-8') as f:
        patch = f.read()
    patch_file('models.py', patch, "if __name__ == '__main__':")

    print("[3/3] Patching app.py...")
    with open('patch_app.py', 'r', encoding='utf-8') as f:
        patch = f.read()
    patch_file('app.py', patch, "if __name__ == '__main__':")

    print()
    print("=" * 50)
    print("Patch applied!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. flask db migrate -m 'add v8 tables'")
    print("  2. flask db upgrade")
    print("  3. python app.py")
    print()
    print("New URLs:")
    print("  /v8/openings     - Keg openings (DocOpening)")
    print("  /v8/writeoffs    - Writeoffs (АктСписания)")
    print("  /v8/sales-docs   - Sales docs (ДокОтгрИсх)")
    print("  POST /v8/sync-docs - Sync all")

if __name__ == '__main__':
    main()
