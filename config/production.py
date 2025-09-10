"""
Production-specific configuration to prevent deployment issues
"""

import os

# Disable scheduler during startup to prevent application context issues
SCHEDULER_ENABLED = os.getenv('SCHEDULER_ENABLED', 'false').lower() == 'true'

# Production-safe defaults
FLASK_DEBUG = False
FLASK_ENV = 'production'
TESTING = False

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Security settings
SECURITY_SCAN_ENABLED = os.getenv('SECURITY_SCAN_ENABLED', 'false').lower() == 'true'

# Performance settings
SCHEDULER_MAX_WORKERS = int(os.getenv('SCHEDULER_MAX_WORKERS', 2))

# Rate limiting for production
RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '1000 per hour')
RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')

# File processing settings
VIDEO_VALIDATION_ENABLED = os.getenv('VIDEO_VALIDATION_ENABLED', 'true').lower() == 'true'
SECURITY_SCAN_ENABLED = os.getenv('SECURITY_SCAN_ENABLED', 'false').lower() == 'true'

