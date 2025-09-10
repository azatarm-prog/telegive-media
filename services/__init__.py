# Services package initialization

from .auth_service import auth_service
from .telegive_service import telegive_service

# Export all service instances
__all__ = [
    'auth_service',
    'telegive_service'
]

def init_services(app):
    """Initialize all services with Flask app"""
    auth_service.init_app(app)
    telegive_service.init_app(app)

