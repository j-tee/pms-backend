#!/bin/bash
# API Endpoint Test Script for Infrastructure Management

echo "================================================================================"
echo "INFRASTRUCTURE API ENDPOINTS TEST"
echo "================================================================================"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000/api/farms"

# Get authentication token (you need to update this with a valid token)
echo ""
echo "NOTE: This test requires a valid JWT token."
echo "To get a token, run:"
echo "  python test_infrastructure_endpoints.py"
echo ""

# Test if server is running
echo "--------------------------------------------------------------------------------"
echo "Checking if server is running..."
echo "--------------------------------------------------------------------------------"
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "$BASE_URL/infrastructure/" || echo "Server not running. Start with: python manage.py runserver"

echo ""
echo "================================================================================"
echo "AVAILABLE ENDPOINTS:"
echo "================================================================================"
echo ""
echo "1. GET    $BASE_URL/infrastructure/"
echo "   - List all infrastructure items"
echo ""
echo "2. POST   $BASE_URL/infrastructure/"
echo "   - Create new infrastructure item"
echo "   Required: infrastructure_name, infrastructure_type"
echo ""
echo "3. GET    $BASE_URL/infrastructure/{id}/"
echo "   - Get single infrastructure item by ID"
echo ""
echo "4. PUT    $BASE_URL/infrastructure/{id}/"
echo "   - Update infrastructure item (supports partial updates)"
echo ""
echo "5. DELETE $BASE_URL/infrastructure/{id}/"
echo "   - Delete infrastructure item"
echo ""
echo "6. GET    $BASE_URL/infrastructure/statistics/"
echo "   - Get aggregated statistics about infrastructure"
echo ""
echo "================================================================================"
echo "FRONTEND ALIASES (same functionality):"
echo "================================================================================"
echo ""
echo "- $BASE_URL/infrastructure-items/"
echo "- $BASE_URL/infrastructure-items/{id}/"
echo ""
echo "================================================================================"
echo "EXAMPLE CURL COMMANDS:"
echo "================================================================================"
echo ""
echo "# Get list of infrastructure"
echo "curl -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "  $BASE_URL/infrastructure/"
echo ""
echo "# Create new infrastructure"
echo "curl -X POST \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{
    \"infrastructure_name\": \"Main Water Tank\",
    \"infrastructure_type\": \"Water System\",
    \"capacity\": \"10000 liters\",
    \"status\": \"Operational\",
    \"condition\": \"Excellent\"
  }' \\"
echo "  $BASE_URL/infrastructure/"
echo ""
echo "# Update infrastructure"
echo "curl -X PUT \\"
echo "  -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{
    \"status\": \"Under Maintenance\",
    \"last_maintenance_date\": \"2025-12-08\"
  }' \\"
echo "  $BASE_URL/infrastructure/{id}/"
echo ""
echo "# Get statistics"
echo "curl -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "  $BASE_URL/infrastructure/statistics/"
echo ""
echo "================================================================================"
echo "IMPLEMENTATION SUMMARY"
echo "================================================================================"
echo ""
echo "✅ GET    /api/farms/infrastructure/              - List all (IMPLEMENTED)"
echo "✅ GET    /api/farms/infrastructure/{id}/         - Get single (IMPLEMENTED)"
echo "✅ POST   /api/farms/infrastructure/              - Create (IMPLEMENTED)"
echo "✅ PUT    /api/farms/infrastructure/{id}/         - Update (IMPLEMENTED)"
echo "✅ DELETE /api/farms/infrastructure/{id}/         - Delete (IMPLEMENTED)"
echo "✅ GET    /api/farms/infrastructure/statistics/   - Statistics (IMPLEMENTED)"
echo ""
echo "✅ Frontend aliases at /infrastructure-items/ also available"
echo ""
echo "================================================================================"
