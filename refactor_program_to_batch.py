#!/usr/bin/env python3
"""
Systematic refactoring script to replace all 'program' references with 'batch' terminology.
This ensures consistency across the codebase.

Usage: python refactor_program_to_batch.py
"""

import os
import re
from pathlib import Path

# Define base directory
BASE_DIR = Path(__file__).parent

# Files to refactor (Python files only, excluding migrations and docs)
TARGET_FILES = [
    'accounts/program_admin_views.py',
    'accounts/program_action_views.py',
    'accounts/admin_views.py',
    'farms/services/program_enrollment_service.py',
]

# Define replacement patterns
# Order matters - more specific patterns first
REPLACEMENTS = [
    # Model field references
    (r'\.program_name\b', '.batch_name'),
    (r'\.program_code\b', '.batch_code'),
    (r'\.program_type\b', '.program_type'),  # Keep for now (will be removed)
    (r'\.program\b', '.program_batch'),
    
    # Query filters and annotations
    (r"'program_name__icontains'", "'batch_name__icontains'"),
    (r"'program_code__icontains'", "'batch_code__icontains'"),
    (r'program_name__icontains', 'batch_name__icontains'),
    (r'program_code__icontains', 'batch_code__icontains'),
    (r"'program__", "'program_batch__"),
    (r'program__', 'program_batch__'),
    
    # Response keys in dictionaries
    (r"'program_name':", "'batch_name':"),
    (r"'program_code':", "'batch_code':"),
    (r'"program_name":', '"batch_name":'),
    (r'"program_code":', '"batch_code":'),
    
    # Variables
    (r'\bprogram_name\b', 'batch_name'),
    (r'\bprogram_code\b', 'batch_code'),
    (r'\bprogram_type\b', 'program_type'),  # Keep for now
    (r'\bprogram_status\b', 'batch_status'),
    
    # Function parameters
    (r'program_id\b', 'batch_id'),
    
    # Comments and strings - be careful with these
    (r'Program name', 'Batch name'),
    (r'Program code', 'Batch code'),
    (r'program or code', 'batch name or code'),
]

def refactor_file(file_path: Path):
    """Apply all replacements to a single file."""
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return False
    
    print(f"📝 Processing: {file_path}")
    
    # Read original content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # Apply each replacement
    for pattern, replacement in REPLACEMENTS:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            # Count occurrences
            matches = len(re.findall(pattern, content))
            changes_made += matches
            content = new_content
    
    # Write back if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"   ✅ Made {changes_made} replacements")
        return True
    else:
        print(f"   ℹ️  No changes needed")
        return False

def main():
    """Main refactoring process."""
    print("🚀 Starting systematic Program → Batch refactoring\n")
    
    total_files = 0
    updated_files = 0
    
    for file_path_str in TARGET_FILES:
        file_path = BASE_DIR / file_path_str
        total_files += 1
        
        if refactor_file(file_path):
            updated_files += 1
        
        print()  # Empty line between files
    
    print(f"\n✨ Refactoring complete!")
    print(f"   Files processed: {total_files}")
    print(f"   Files updated: {updated_files}")
    print(f"   Files unchanged: {total_files - updated_files}")
    
    print(f"\n⚠️  IMPORTANT: Remember to:")
    print(f"   1. Test all API endpoints")
    print(f"   2. Run: python manage.py check")
    print(f"   3. Create database migration")
    print(f"   4. Update any tests")

if __name__ == '__main__':
    main()
