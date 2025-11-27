#!/usr/bin/env python3
"""
Update all view method signatures to accept both batch_id and program_id
for backward compatibility with existing URLs.
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

FILES = [
    'accounts/program_admin_views.py',
    'accounts/program_action_views.py',
]

def update_method_signatures(file_path: Path):
    """Update method signatures to accept both batch_id and program_id."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match method definitions with batch_id parameter
    # Replace: def METHOD(self, request, batch_id):
    # With: def METHOD(self, request, batch_id=None, program_id=None):
    pattern = r'(def (get|post|put|patch|delete)\(self, request), batch_id\):'
    replacement = r'\1, batch_id=None, program_id=None):'
    
    new_content = re.sub(pattern, replacement, content)
    
    # Add helper line at start of methods to handle both parameter names
    # After the method signature, add: batch_id = batch_id or program_id
    # This needs to be inserted after method def but before first line of code
    
    # Pattern: method signature followed by any docstring, then first code line
    pattern2 = r'(def (get|post|put|patch|delete)\(self, request, batch_id=None, program_id=None\):(?:\s+""".*?"""|\'\'\'.*?\'\'\')?\s+)(#.*?\n)?(\s+)([^#\s])'
    replacement2 = r'\1\n\4# Accept both batch_id and program_id for backward compatibility\n\4batch_id = batch_id or program_id\n\4\5'
    
    new_content = re.sub(pattern2, replacement2, new_content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Updated {file_path}")

def main():
    print("🔄 Updating method signatures for backward compatibility\n")
    
    for file_str in FILES:
        file_path = BASE_DIR / file_str
        if file_path.exists():
            update_method_signatures(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print("\n✨ Done!")

if __name__ == '__main__':
    main()
