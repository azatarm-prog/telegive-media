"""
Environment configuration management for Media Management Service
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class ServiceConfig:
    name: str
    port: int
    url: Optional[str] = None
    required: bool = True
    timeout: int = 10

class EnvironmentManager:
    """Centralized environment configuration management"""
    
    def __init__(self):
        self.env = Environment(os.getenv('ENVIRONMENT', os.getenv('FLASK_ENV', 'development')))
        self._config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration based on environment"""
        
        base_config = {
            'SECRET_KEY': self._get_required('SECRET_KEY'),
            'DATABASE_URL': self._get_required('DATABASE_URL'),
            'SERVICE_NAME': os.getenv('SERVICE_NAME', 'media-service'),
            'SERVICE_PORT': int(os.getenv('SERVICE_PORT', 8005)),
            'FLASK_DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
            'REDIS_URL': os.getenv('REDIS_URL'),
            'UPLOAD_FOLDER': os.getenv('UPLOAD_FOLDER', '/app/uploads'),
            'MAX_CONTENT_LENGTH': int(os.getenv('MAX_CONTENT_LENGTH', 52428800)),
            'MAX_IMAGE_SIZE': int(os.getenv('MAX_IMAGE_SIZE', 10485760)),
            'MAX_VIDEO_SIZE': int(os.getenv('MAX_VIDEO_SIZE', 52428800)),
        }
        
        # Service discovery configuration
        services_config = {
            'auth': ServiceConfig(
                name='auth',
                port=8001,
                url=os.getenv('TELEGIVE_AUTH_URL'),
                required=True
            ),
            'channel': ServiceConfig(
                name='channel',
                port=8002,
                url=os.getenv('TELEGIVE_CHANNEL_URL'),
                required=False
            ),
            'bot': ServiceConfig(
                name='bot',
                port=8003,
                url=os.getenv('TELEGIVE_BOT_URL'),
                required=False
            ),
            'participant': ServiceConfig(
                name='participant',
                port=8004,
                url=os.getenv('TELEGIVE_PARTICIPANT_URL'),
                required=False
            ),
            'giveaway': ServiceConfig(
                name='giveaway',
                port=8006,
                url=os.getenv('TELEGIVE_GIVEAWAY_URL'),
                required=False
            ),
        }
        
        # Environment-specific overrides
        if self.env == Environment.DEVELOPMENT:
            base_config.update({
                'FLASK_DEBUG': True,
                'LOG_LEVEL': 'DEBUG',
                'UPLOAD_FOLDER': '/tmp/uploads'
            })
            # Use localhost URLs for development
            for service in services_config.values():
                if not service.url:
                    service.url = f"http://localhost:{service.port}"
        
        elif self.env == Environment.TESTING:
            base_config.update({
                'FLASK_DEBUG': True,
                'LOG_LEVEL': 'DEBUG',
                'DATABASE_URL': 'sqlite:///:memory:',
                'UPLOAD_FOLDER': '/tmp/test_uploads',
                'SECURITY_SCAN_ENABLED': False,
                'SCHEDULER_ENABLED': False
            })
            # Disable external services for testing
            for service in services_config.values():
                service.required = False
                if not service.url:
                    service.url = f"http://localhost:{service.port}"
        
        elif self.env == Environment.PRODUCTION:
            base_config.update({
                'FLASK_DEBUG': False,
                'LOG_LEVEL': 'INFO'
            })
            # Validate all required services have URLs in production
            for service in services_config.values():
                if service.required and not service.url:
                    raise ValueError(f"Required service {service.name} URL not configured for production")
        
        base_config['SERVICES'] = services_config
        return base_config
    
    def _get_required(self, key: str) -> str:
        """Get required environment variable"""
        value = os.getenv(key)
        if not value:
            if self.env == Environment.TESTING:
                # Provide defaults for testing
                defaults = {
                    'SECRET_KEY': 'test-secret-key',
                    'DATABASE_URL': 'sqlite:///:memory:'
                }
                return defaults.get(key, f'test-{key.lower()}')
            raise ValueError(f"Required environment variable {key} is not set")
        return value
    
    def _validate_config(self):
        """Validate configuration"""
        required_keys = ['SECRET_KEY', 'DATABASE_URL', 'SERVICE_NAME']
        
        for key in required_keys:
            if key not in self._config or not self._config[key]:
                raise ValueError(f"Required configuration {key} is missing")
        
        # Validate database URL format
        db_url = self._config['DATABASE_URL']
        if not db_url.startswith(('postgresql://', 'sqlite://', 'mysql://')):
            raise ValueError("DATABASE_URL must be a valid database connection string")
        
        # Validate upload folder
        upload_folder = self._config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            try:
                os.makedirs(upload_folder, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Cannot create upload folder {upload_folder}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get(key, default)
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get service URL by name"""
        services = self._config.get('SERVICES', {})
        service = services.get(service_name)
        return service.url if service else None
    
    def is_service_required(self, service_name: str) -> bool:
        """Check if service is required"""
        services = self._config.get('SERVICES', {})
        service = services.get(service_name)
        return service.required if service else False
    
    def get_all_service_urls(self) -> Dict[str, str]:
        """Get all configured service URLs"""
        services = self._config.get('SERVICES', {})
        return {name: service.url for name, service in services.items() if service.url}
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.env == Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.env == Environment.PRODUCTION
    
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.env == Environment.TESTING
    
    def export_env_template(self) -> str:
        """Export environment template for documentation"""
        template = [
            "# Media Management Service Configuration",
            f"SERVICE_NAME={self._config['SERVICE_NAME']}",
            f"SERVICE_PORT={self._config['SERVICE_PORT']}",
            "SECRET_KEY=your-secret-key-here",
            "FLASK_DEBUG=False",
            "ENVIRONMENT=production",
            "",
            "# Database",
            "DATABASE_URL=postgresql://user:password@host:port/database",
            "",
            "# File Storage",
            f"UPLOAD_FOLDER={self._config['UPLOAD_FOLDER']}",
            f"MAX_CONTENT_LENGTH={self._config['MAX_CONTENT_LENGTH']}",
            f"MAX_IMAGE_SIZE={self._config['MAX_IMAGE_SIZE']}",
            f"MAX_VIDEO_SIZE={self._config['MAX_VIDEO_SIZE']}",
            "",
            "# External Services"
        ]
        
        services = self._config.get('SERVICES', {})
        for name, service in services.items():
            env_var = f"TELEGIVE_{name.upper()}_URL"
            example_url = f"https://telegive-{name}-production.up.railway.app"
            required_note = " # Required" if service.required else " # Optional"
            template.append(f"{env_var}={example_url}{required_note}")
        
        template.extend([
            "",
            "# Optional",
            "REDIS_URL=redis://localhost:6379",
            "SECURITY_SCAN_ENABLED=false",
            "LOG_LEVEL=INFO"
        ])
        
        return "\n".join(template)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            'environment': self.env.value,
            'service_name': self._config['SERVICE_NAME'],
            'service_port': self._config['SERVICE_PORT'],
            'debug_mode': self._config['FLASK_DEBUG'],
            'database_type': self._config['DATABASE_URL'].split('://')[0],
            'upload_folder': self._config['UPLOAD_FOLDER'],
            'services_configured': len([s for s in self._config['SERVICES'].values() if s.url]),
            'required_services_configured': len([s for s in self._config['SERVICES'].values() if s.required and s.url])
        }

# Global instance
env_manager = EnvironmentManager()

