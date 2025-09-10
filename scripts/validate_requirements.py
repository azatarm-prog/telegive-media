#!/usr/bin/env python3
"""
Requirements validation script for Media Management Service
"""

import subprocess
import sys
import pkg_resources
from packaging import version
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_requirements():
    """Validate all requirements in requirements.txt"""
    
    print("🔍 Validating requirements.txt...")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read().strip().split('\n')
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False
    
    invalid_packages = []
    outdated_packages = []
    security_issues = []
    
    for req in requirements:
        if not req.strip() or req.startswith('#'):
            continue
            
        # Parse package name and version
        if '==' in req:
            package_name, package_version = req.split('==')
        else:
            package_name = req
            package_version = None
        
        package_name = package_name.strip()
        
        # Check if package exists on PyPI
        try:
            response = requests.get(f'https://pypi.org/pypi/{package_name}/json', timeout=10)
            if response.status_code != 200:
                invalid_packages.append(package_name)
                continue
                
            package_info = response.json()
            latest_version = package_info['info']['version']
            
            if package_version:
                # Check if specified version exists
                available_versions = list(package_info['releases'].keys())
                if package_version not in available_versions:
                    invalid_packages.append(f"{package_name}=={package_version}")
                    continue
                
                # Check if version is outdated (major version behind)
                try:
                    current_major = version.parse(package_version).major
                    latest_major = version.parse(latest_version).major
                    
                    if current_major < latest_major:
                        outdated_packages.append(f"{package_name}: {package_version} -> {latest_version} (major version behind)")
                    elif version.parse(package_version) < version.parse(latest_version):
                        # Minor version behind - just a warning
                        print(f"⚠️  {package_name}: {package_version} -> {latest_version} (minor update available)")
                except:
                    pass
            
            # Check for known security vulnerabilities (simplified check)
            if package_name.lower() in ['pillow', 'flask', 'requests', 'sqlalchemy']:
                # These packages often have security updates
                if package_version and version.parse(package_version) < version.parse(latest_version):
                    security_issues.append(f"{package_name}: Consider updating from {package_version} to {latest_version} for security")
            
        except Exception as e:
            print(f"⚠️  Could not validate {package_name}: {e}")
    
    # Report results
    success = True
    
    if invalid_packages:
        print("❌ Invalid packages found:")
        for pkg in invalid_packages:
            print(f"   - {pkg}")
        success = False
    
    if outdated_packages:
        print("❌ Critically outdated packages found:")
        for pkg in outdated_packages:
            print(f"   - {pkg}")
        success = False
    
    if security_issues:
        print("⚠️  Potential security issues:")
        for issue in security_issues:
            print(f"   - {issue}")
    
    if success:
        print("✅ All requirements are valid!")
    
    return success

def check_requirements_installability():
    """Check if requirements can be installed"""
    print("🔧 Testing requirements installation...")
    
    try:
        # Create a temporary virtual environment and test installation
        result = subprocess.run([
            sys.executable, '-m', 'venv', 'temp_test_env'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("❌ Failed to create test virtual environment")
            return False
        
        # Activate and install requirements
        if sys.platform == "win32":
            pip_path = "temp_test_env\\Scripts\\pip"
        else:
            pip_path = "temp_test_env/bin/pip"
        
        result = subprocess.run([
            pip_path, 'install', '-r', 'requirements.txt'
        ], capture_output=True, text=True)
        
        # Cleanup
        import shutil
        shutil.rmtree('temp_test_env', ignore_errors=True)
        
        if result.returncode != 0:
            print("❌ Requirements installation failed:")
            print(result.stderr)
            return False
        
        print("✅ Requirements can be installed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Requirements installation test failed: {e}")
        return False

def check_critical_packages():
    """Check critical packages for Media Management Service"""
    print("🔍 Checking critical packages...")
    
    critical_packages = {
        'Flask': 'Web framework',
        'Flask-SQLAlchemy': 'Database ORM',
        'Flask-CORS': 'Cross-origin requests',
        'Pillow': 'Image processing',
        'python-magic': 'File type detection',
        'APScheduler': 'Task scheduling',
        'gunicorn': 'WSGI server',
        'pytest': 'Testing framework'
    }
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements_content = f.read()
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False
    
    missing_critical = []
    
    for package, description in critical_packages.items():
        if package.lower() not in requirements_content.lower():
            missing_critical.append(f"{package} ({description})")
    
    if missing_critical:
        print("❌ Missing critical packages:")
        for pkg in missing_critical:
            print(f"   - {pkg}")
        return False
    
    print("✅ All critical packages are present")
    return True

def main():
    """Main validation process"""
    print("🚀 Starting requirements validation for Media Management Service")
    
    success = True
    
    # Check critical packages
    if not check_critical_packages():
        success = False
    
    # Validate requirements
    if not validate_requirements():
        success = False
    
    # Test installation
    if not check_requirements_installability():
        success = False
    
    if success:
        print("\n🎉 All requirements validation checks passed!")
        return 0
    else:
        print("\n❌ Requirements validation failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

