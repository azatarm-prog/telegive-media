import os
from .base import BaseConfig

class TestingConfig(BaseConfig):
    """Testing configuration"""
    
    TESTING = True
    WTF_CSRF_ENABLED = False
    
    # Use in-memory SQLite for testing
    DATABASE_URL = 'sqlite:///:memory:'
    
    # Disable background tasks for testing
    SCHEDULER_ENABLED = False
    
    # Disable external service calls
    TELEGIVE_AUTH_URL = None
    TELEGIVE_GIVEAWAY_URL = None
    
    # Disable security scanning for testing
    SECURITY_SCAN_ENABLED = False
    
    # Smaller limits for testing
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1MB
    MAX_IMAGE_SIZE = 512 * 1024  # 512KB
    MAX_VIDEO_SIZE = 1 * 1024 * 1024  # 1MB
    
    # Test upload folder
    UPLOAD_FOLDER = '/tmp/test_uploads'
    
    # Faster cleanup for testing
    CLEANUP_DELAY_MINUTES = 1
    CLEANUP_BATCH_SIZE = 10
    
    # Test rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '1000 per hour'
    
    # Logging
    LOG_LEVEL = 'DEBUG'
    LOG_TO_STDOUT = True

