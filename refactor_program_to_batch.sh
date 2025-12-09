#!/bin/bash
# Complete migration from "program" to "batch" terminology
# NO backward compatibility - clean break

set -e

echo "🚀 Starting COMPLETE program → batch migration (NO backward compatibility)"
echo "================================================================"
echo ""

# Step 1: Rename model files
echo "📁 Step 1: Renaming model files..."
if [ -f "farms/program_enrollment_models.py" ]; then
    mv farms/program_enrollment_models.py farms/batch_enrollment_models.py
    echo "   ✅ Renamed program_enrollment_models.py → batch_enrollment_models.py"
fi

# Step 2: Rename view files
echo "📁 Step 2: Renaming view files..."
if [ -f "accounts/program_admin_views.py" ]; then
    mv accounts/program_admin_views.py accounts/batch_admin_views.py
    echo "   ✅ Renamed program_admin_views.py → batch_admin_views.py"
fi

if [ -f "accounts/program_action_views.py" ]; then
    mv accounts/program_action_views.py accounts/batch_action_views.py
    echo "   ✅ Renamed program_action_views.py → batch_action_views.py"
fi

# Step 3: Rename policy files
echo "📁 Step 3: Renaming policy files..."
if [ -f "accounts/policies/program_policy.py" ]; then
    mv accounts/policies/program_policy.py accounts/policies/batch_policy.py
    echo "   ✅ Renamed program_policy.py → batch_policy.py"
fi

# Step 4: Rename service files
echo "📁 Step 4: Renaming service files..."
if [ -f "farms/services/program_enrollment_service.py" ]; then
    mv farms/services/program_enrollment_service.py farms/services/batch_enrollment_service.py
    echo "   ✅ Renamed program_enrollment_service.py → batch_enrollment_service.py"
fi

echo ""
echo "✨ File renaming complete!"
echo ""
echo "Next steps:"
echo "1. Run Python refactoring script to update all code references"
echo "2. Drop database and recreate migrations"
echo ""
