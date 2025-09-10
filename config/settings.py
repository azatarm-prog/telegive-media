import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class"""
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/telegive')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 20,
        'max_overflow': 0
    }
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Service Configuration
    SERVICE_NAME = os.getenv('SERVICE_NAME', 'media-service')
    SERVICE_PORT = int(os.getenv('SERVICE_PORT', 8005))
    
    # File Storage
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', '/app/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB
    
    # File Type Configuration
    ALLOWED_IMAGE_EXTENSIONS = os.getenv('ALLOWED_IMAGE_EXTENSIONS', 'jpg,jpeg,png,gif').split(',')
    ALLOWED_VIDEO_EXTENSIONS = os.getenv('ALLOWED_VIDEO_EXTENSIONS', 'mp4,mov,avi').split(',')
    
    # File Size Limits
    MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE', 10485760))  # 10MB
    MAX_VIDEO_SIZE = int(os.getenv('MAX_VIDEO_SIZE', 52428800))  # 50MB
    
    # Other Services
    TELEGIVE_AUTH_URL = os.getenv('TELEGIVE_AUTH_URL', 'https://telegive-auth.railway.app')
    TELEGIVE_GIVEAWAY_URL = os.getenv('TELEGIVE_GIVEAWAY_URL', 'https://telegive-service.railway.app')
    
    # File Processing
    IMAGE_QUALITY = int(os.getenv('IMAGE_QUALITY', 85))
    VIDEO_VALIDATION_ENABLED = os.getenv('VIDEO_VALIDATION_ENABLED', 'true').lower() == 'true'
    HASH_ALGORITHM = os.getenv('HASH_ALGORITHM', 'sha256')
    
    # Cleanup Configuration
    CLEANUP_DELAY_MINUTES = int(os.getenv('CLEANUP_DELAY_MINUTES', 5))
    CLEANUP_BATCH_SIZE = int(os.getenv('CLEANUP_BATCH_SIZE', 100))
    CLEANUP_RETRY_ATTEMPTS = int(os.getenv('CLEANUP_RETRY_ATTEMPTS', 3))
    
    # CDN Configuration (optional)
    CDN_ENABLED = os.getenv('CDN_ENABLED', 'false').lower() == 'true'
    CDN_BASE_URL = os.getenv('CDN_BASE_URL', 'https://cdn.example.com')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100 per hour')
    
    # Security
    SECURITY_SCAN_ENABLED = os.getenv('SECURITY_SCAN_ENABLED', 'false').lower() == 'true'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL', 'postgresql://test:test@localhost:5432/test_telegive')
    UPLOAD_FOLDER = '/tmp/test_uploads'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

