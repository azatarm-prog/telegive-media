#!/bin/bash
# scripts/pre-deploy-validate.sh

set -e  # Exit on any error

echo "🔍 Starting pre-deployment validation for Media Management Service..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# 1. Validate Python environment
echo "🐍 Validating Python environment..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed"
fi
print_status "Python3 is available"

# 2. Validate requirements.txt
echo "📦 Validating requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found"
fi

# Test requirements installation in temporary environment
python3 -m venv temp_venv
source temp_venv/bin/activate
pip install --quiet -r requirements.txt || print_error "Failed to install requirements"
deactivate
rm -rf temp_venv
print_status "All requirements are valid and installable"

# 3. Validate environment variables
echo "🔧 Validating environment variables..."
if [ ! -f ".env.example" ]; then
    print_error ".env.example file not found"
fi

# Check if all required variables are documented
required_vars=("DATABASE_URL" "SECRET_KEY" "SERVICE_NAME" "SERVICE_PORT" "UPLOAD_FOLDER")
for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" .env.example; then
        print_error "Required variable $var not found in .env.example"
    fi
done
print_status "All required environment variables are documented"

# 4. Validate deployment configuration
echo "🚀 Validating deployment configuration..."
if [ ! -f "Procfile" ]; then
    print_error "Procfile not found"
fi

# Validate Procfile format
if ! grep -q "web:" Procfile; then
    print_error "Procfile must contain 'web:' process definition"
fi

print_status "Deployment configuration is valid"

# 5. Validate Flask application structure
echo "🌐 Validating Flask application..."
if [ ! -f "app.py" ]; then
    print_error "app.py not found"
fi

# Test if app can be imported
python3 -c "
import sys
sys.path.append('.')
try:
    from app import create_app
    app = create_app('testing')
    print('✅ Flask app imports successfully')
except Exception as e:
    print(f'❌ Flask app import failed: {e}')
    sys.exit(1)
" || print_error "Flask application validation failed"

print_status "Flask application structure is valid"

# 6. Validate database models
echo "🗄️  Validating database models..."
python3 -c "
import sys
sys.path.append('.')
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
try:
    from app import create_app
    from models import db
    app = create_app('testing')
    with app.app_context():
        db.create_all()
    print('✅ Database models are valid')
except Exception as e:
    print(f'❌ Database model validation failed: {e}')
    sys.exit(1)
" || print_error "Database model validation failed"

print_status "Database models are valid"

# 7. Validate health endpoints
echo "🏥 Validating health endpoints..."
python3 -c "
import sys
sys.path.append('.')
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
try:
    from app import create_app
    app = create_app('testing')
    client = app.test_client()
    
    # Test health endpoints
    endpoints = ['/health']
    for endpoint in endpoints:
        response = client.get(endpoint)
        if response.status_code not in [200, 503]:  # 503 is acceptable for ready endpoint
            raise Exception(f'Health endpoint {endpoint} returned {response.status_code}')
    
    print('✅ Health endpoints are working')
except Exception as e:
    print(f'❌ Health endpoint validation failed: {e}')
    sys.exit(1)
" || print_error "Health endpoint validation failed"

print_status "Health endpoints are working"

# 8. Validate API routes
echo "🛣️  Validating API routes..."
python3 -c "
import sys
sys.path.append('.')
import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
try:
    from app import create_app
    app = create_app('testing')
    
    # Check if blueprints are registered
    blueprint_count = len(app.blueprints)
    if blueprint_count == 0:
        raise Exception('No blueprints registered')
    
    print(f'✅ {blueprint_count} blueprints registered')
except Exception as e:
    print(f'❌ API route validation failed: {e}')
    sys.exit(1)
" || print_error "API route validation failed"

print_status "API routes are valid"

# 9. Validate file upload directory structure
echo "📁 Validating file upload structure..."
if [ ! -d "uploads" ]; then
    print_error "uploads directory not found"
fi

if [ ! -f "uploads/.gitkeep" ]; then
    print_warning "uploads/.gitkeep not found - directory may not be tracked in git"
fi

print_status "File upload structure is valid"

# 10. Validate utility modules
echo "🔧 Validating utility modules..."
python3 -c "
import sys
sys.path.append('.')
try:
    from utils import file_validator, image_processor, video_processor
    from utils import file_hasher, file_storage, security_scanner
    print('✅ All utility modules import successfully')
except Exception as e:
    print(f'❌ Utility module validation failed: {e}')
    sys.exit(1)
" || print_error "Utility module validation failed"

print_status "Utility modules are valid"

# 11. Validate test suite
echo "🧪 Validating test suite..."
if [ ! -d "tests" ]; then
    print_error "tests directory not found"
fi

if [ ! -f "tests/conftest.py" ]; then
    print_error "tests/conftest.py not found"
fi

# Run a quick test to ensure test framework works
python3 -c "
import sys
sys.path.append('.')
try:
    import pytest
    # Try to collect tests
    exit_code = pytest.main(['--collect-only', '-q', 'tests/'])
    if exit_code != 0:
        raise Exception('Test collection failed')
    print('✅ Test suite is valid')
except Exception as e:
    print(f'❌ Test suite validation failed: {e}')
    sys.exit(1)
" || print_error "Test suite validation failed"

print_status "Test suite is valid"

echo "🎉 All pre-deployment validations passed!"
echo "📋 Summary:"
echo "   - Python environment: ✅"
echo "   - Requirements: ✅"
echo "   - Environment variables: ✅"
echo "   - Deployment config: ✅"
echo "   - Flask application: ✅"
echo "   - Database models: ✅"
echo "   - Health endpoints: ✅"
echo "   - API routes: ✅"
echo "   - File upload structure: ✅"
echo "   - Utility modules: ✅"
echo "   - Test suite: ✅"
echo ""
echo "🚀 Ready for deployment!"

