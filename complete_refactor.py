#!/usr/bin/env python3
"""
COMPLETE refactoring from 'program' to 'batch' terminology.
NO backward compatibility - clean break.

This script:
1. Renames model classes (ProgramBatch → Batch, GovernmentProgram → Batch)
2. Updates all imports
3. Updates all field references
4. Updates all URL patterns
5. Updates all policy class names
6. Updates database table names in Meta
7. Removes all backward compatibility code
"""

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

# All Python files that need updating
PYTHON_FILES = [
    'farms/batch_enrollment_models.py',
    'farms/models.py',
    'accounts/batch_admin_views.py',
    'accounts/batch_action_views.py',
    'accounts/admin_views.py',
    'accounts/admin_urls.py',
    'accounts/policies/batch_policy.py',
    'accounts/policies/__init__.py',
    'farms/services/batch_enrollment_service.py',
]

def replace_in_file(file_path, replacements):
    """Apply list of (pattern, replacement) tuples to file."""
    if not file_path.exists():
        print(f"⚠️  Skipping {file_path} (not found)")
        return 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    changes = 0
    
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            matches = len(re.findall(pattern, content, flags=re.MULTILINE))
            changes += matches
            content = new_content
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ {file_path.name}: {changes} replacements")
        return changes
    return 0

def main():
    print("🔄 COMPLETE Program → Batch Refactoring (NO Backward Compatibility)")
    print("=" * 70)
    print()
    
    total_changes = 0
    
    # ========================================
    # 1. Update batch_enrollment_models.py
    # ========================================
    print("📝 1. Updating batch_enrollment_models.py...")
    replacements = [
        # Remove backward compatibility alias
        (r'\n# Backward compatibility alias\nGovernmentProgram = ProgramBatch\n?', ''),
        
        # Rename ProgramBatch to Batch
        (r'\bclass ProgramBatch\(', 'class Batch('),
        (r'\bProgramBatch\b', 'Batch'),
        
        # Update table name
        (r"db_table = 'farms_governmentprogram'", "db_table = 'farms_batch'"),
        
        # Update verbose names
        (r"verbose_name = 'Program Batch'", "verbose_name = 'Batch'"),
        (r"verbose_name_plural = 'Program Batches'", "verbose_name_plural = 'Batches'"),
        
        # Update ForeignKey references
        (r'ProgramEnrollmentApplication', 'BatchEnrollmentApplication'),
        (r'ProgramEnrollmentReview', 'BatchEnrollmentReview'),
        (r'ProgramEnrollmentQueue', 'BatchEnrollmentQueue'),
        
        # Update field names in help text
        (r'program batch', 'batch'),
        (r'Program batch', 'Batch'),
    ]
    total_changes += replace_in_file(BASE_DIR / 'farms/batch_enrollment_models.py', replacements)
    
    # ========================================
    # 2. Update farms/models.py imports
    # ========================================
    print("📝 2. Updating farms/models.py...")
    replacements = [
        (r'from \.program_enrollment_models import', 'from .batch_enrollment_models import'),
        (r'\bGovernmentProgram\b', 'Batch'),
        (r'\bProgramBatch\b', 'Batch'),
        (r'\bProgramEnrollmentApplication\b', 'BatchEnrollmentApplication'),
        (r'\bProgramEnrollmentReview\b', 'BatchEnrollmentReview'),
        (r'\bProgramEnrollmentQueue\b', 'BatchEnrollmentQueue'),
    ]
    total_changes += replace_in_file(BASE_DIR / 'farms/models.py', replacements)
    
    # ========================================
    # 3. Update view files
    # ========================================
    print("📝 3. Updating view files...")
    view_replacements = [
        # Import statements
        (r'from farms\.program_enrollment_models import', 'from farms.batch_enrollment_models import'),
        (r'from \.program_enrollment_models import', 'from .batch_enrollment_models import'),
        
        # Model references
        (r'\bGovernmentProgram\b', 'Batch'),
        (r'\bProgramBatch\b', 'Batch'),
        (r'\bProgramEnrollmentApplication\b', 'BatchEnrollmentApplication'),
        (r'\bProgramEnrollmentReview\b', 'BatchEnrollmentReview'),
        
        # Policy imports and references
        (r'from accounts\.policies\.program_policy import ProgramPolicy', 'from accounts.policies.batch_policy import BatchPolicy'),
        (r'\bProgramPolicy\b', 'BatchPolicy'),
        
        # Class names
        (r'AdminProgramListView', 'AdminBatchListView'),
        (r'AdminProgramDetailView', 'AdminBatchDetailView'),
        (r'AdminProgramCreateView', 'AdminBatchCreateView'),
        (r'AdminProgramUpdateView', 'AdminBatchUpdateView'),
        (r'AdminProgramDeleteView', 'AdminBatchDeleteView'),
        (r'AdminProgramToggleActiveView', 'AdminBatchToggleActiveView'),
        (r'AdminProgramCloseApplicationsView', 'AdminBatchCloseApplicationsView'),
        (r'AdminProgramExtendDeadlineView', 'AdminBatchExtendDeadlineView'),
        (r'AdminProgramParticipantsView', 'AdminBatchParticipantsView'),
        (r'AdminProgramStatisticsView', 'AdminBatchStatisticsView'),
        (r'AdminProgramDuplicateView', 'AdminBatchDuplicateView'),
        
        # URL parameter names - remove backward compatibility
        (r'program_id=None, ', ''),
        (r', program_id=None', ''),
        (r'batch_id = batch_id or program_id', ''),
        (r'# Accept both batch_id and program_id for backward compatibility\n\s+', ''),
        
        # Comments
        (r'Program Management', 'Batch Management'),
        (r'government program', 'batch'),
        (r'Government program', 'Batch'),
    ]
    
    for view_file in ['accounts/batch_admin_views.py', 'accounts/batch_action_views.py', 'accounts/admin_views.py']:
        total_changes += replace_in_file(BASE_DIR / view_file, view_replacements)
    
    # ========================================
    # 4. Update admin_urls.py
    # ========================================
    print("📝 4. Updating admin_urls.py...")
    replacements = [
        # Update imports
        (r'from \.program_admin_views import', 'from .batch_admin_views import'),
        (r'from \.program_action_views import', 'from .batch_action_views import'),
        
        # Update class names in imports
        (r'AdminProgramListView', 'AdminBatchListView'),
        (r'AdminProgramDetailView', 'AdminBatchDetailView'),
        (r'AdminProgramCreateView', 'AdminBatchCreateView'),
        (r'AdminProgramUpdateView', 'AdminBatchUpdateView'),
        (r'AdminProgramDeleteView', 'AdminBatchDeleteView'),
        (r'AdminProgramToggleActiveView', 'AdminBatchToggleActiveView'),
        (r'AdminProgramCloseApplicationsView', 'AdminBatchCloseApplicationsView'),
        (r'AdminProgramExtendDeadlineView', 'AdminBatchExtendDeadlineView'),
        (r'AdminProgramParticipantsView', 'AdminBatchParticipantsView'),
        (r'AdminProgramStatisticsView', 'AdminBatchStatisticsView'),
        (r'AdminProgramDuplicateView', 'AdminBatchDuplicateView'),
        
        # Remove ALL /programs/ URLs - keep only /batches/
        (r"# Program management views.*?\n", "# Batch management views\n"),
        (r"# Batch/Program Management.*?# ={40,}\n", "# Batch Management\n"),
        (r"# ={40,}\n# DEPRECATED: Program URLs.*?path\('programs.*?\n", ""),
        (r"path\('programs/.*?\n", ""),
    ]
    total_changes += replace_in_file(BASE_DIR / 'accounts/admin_urls.py', replacements)
    
    # ========================================
    # 5. Update batch_policy.py
    # ========================================
    print("📝 5. Updating batch_policy.py...")
    replacements = [
        # Rename class
        (r'\bclass ProgramPolicy\(', 'class BatchPolicy('),
        
        # Update method names
        (r'def can_view_program\(', 'def can_view_batch('),
        (r'def can_create_program\(', 'def can_create_batch('),
        (r'def can_edit_program\(', 'def can_edit_batch('),
        (r'def can_delete_program\(', 'def can_delete_batch('),
        (r'def can_apply_to_program\(', 'def can_apply_to_batch('),
        (r'def can_view_program_applications\(', 'def can_view_batch_applications('),
        (r'def can_view_program_participants\(', 'def can_view_batch_participants('),
        (r'def scope_programs\(', 'def scope_batches('),
        
        # Update parameter names
        (r'\bprogram\b(?!\s*=)', 'batch'),
        
        # Update imports in method bodies
        (r'from farms\.models import GovernmentProgram', 'from farms.models import Batch'),
        (r'from farms\.models import ProgramEnrollmentApplication', 'from farms.models import BatchEnrollmentApplication'),
        (r'\bGovernmentProgram\b', 'Batch'),
        (r'\bProgramEnrollmentApplication\b', 'BatchEnrollmentApplication'),
    ]
    total_changes += replace_in_file(BASE_DIR / 'accounts/policies/batch_policy.py', replacements)
    
    # ========================================
    # 6. Update policies/__init__.py
    # ========================================
    print("📝 6. Updating policies/__init__.py...")
    replacements = [
        (r'from \.program_policy import ProgramPolicy', 'from .batch_policy import BatchPolicy'),
        (r'\bProgramPolicy\b', 'BatchPolicy'),
    ]
    if (BASE_DIR / 'accounts/policies/__init__.py').exists():
        total_changes += replace_in_file(BASE_DIR / 'accounts/policies/__init__.py', replacements)
    
    # ========================================
    # 7. Update service files
    # ========================================
    print("📝 7. Updating service files...")
    replacements = [
        (r'from farms\.program_enrollment_models import', 'from farms.batch_enrollment_models import'),
        (r'\bGovernmentProgram\b', 'Batch'),
        (r'\bProgramBatch\b', 'Batch'),
        (r'\bProgramEnrollmentApplication\b', 'BatchEnrollmentApplication'),
        (r'\bProgramEnrollmentReview\b', 'BatchEnrollmentReview'),
    ]
    total_changes += replace_in_file(BASE_DIR / 'farms/services/batch_enrollment_service.py', replacements)
    
    print()
    print("=" * 70)
    print(f"✨ Refactoring complete! Total changes: {total_changes}")
    print()
    print("⚠️  CRITICAL NEXT STEPS:")
    print("1. Delete db.sqlite3")
    print("2. Delete all migration files (except __init__.py)")
    print("3. Run: python manage.py makemigrations")
    print("4. Run: python manage.py migrate")
    print("5. Run: python manage.py check")
    print()

if __name__ == '__main__':
    main()
