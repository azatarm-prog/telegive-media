import jwt
import requests
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime, timedelta

class AuthService:
    """Authentication service integration"""
    
    def __init__(self):
        self.auth_url = None
        self.secret_key = None
        self.token_cache = {}  # Simple in-memory cache for tokens
        self.cache_ttl = 300  # 5 minutes
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.auth_url = app.config.get('TELEGIVE_AUTH_URL')
        self.secret_key = app.config.get('SECRET_KEY')
    
    def validate_service_token(self, token):
        """
        Validate inter-service JWT token
        
        Args:
            token: JWT token string
        
        Returns:
            dict: Validation result with service info
        """
        result = {
            'valid': False,
            'service_name': None,
            'permissions': [],
            'error': None
        }
        
        try:
            # Decode JWT token
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=['HS256']
            )
            
            # Check token expiration
            if 'exp' in payload:
                exp_time = datetime.fromtimestamp(payload['exp'])
                if exp_time < datetime.utcnow():
                    result['error'] = 'Token expired'
                    return result
            
            # Extract service information
            result.update({
                'valid': True,
                'service_name': payload.get('service_name'),
                'permissions': payload.get('permissions', []),
                'account_id': payload.get('account_id'),
                'user_id': payload.get('user_id')
            })
            
        except jwt.ExpiredSignatureError:
            result['error'] = 'Token expired'
        except jwt.InvalidTokenError as e:
            result['error'] = f'Invalid token: {str(e)}'
        except Exception as e:
            result['error'] = f'Token validation error: {str(e)}'
        
        return result
    
    def validate_user_token(self, token):
        """
        Validate user authentication token with auth service
        
        Args:
            token: Authentication token
        
        Returns:
            dict: Validation result with user info
        """
        result = {
            'valid': False,
            'user_id': None,
            'account_id': None,
            'permissions': [],
            'error': None
        }
        
        # Check cache first
        cache_key = f"token:{token[:16]}"  # Use first 16 chars as cache key
        if cache_key in self.token_cache:
            cached_result, cached_time = self.token_cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(seconds=self.cache_ttl):
                return cached_result
        
        try:
            if not self.auth_url:
                result['error'] = 'Auth service URL not configured'
                return result
            
            # Call auth service to validate token
            response = requests.post(
                f"{self.auth_url}/api/auth/validate",
                json={'token': token},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('valid'):
                    result.update({
                        'valid': True,
                        'user_id': data.get('user_id'),
                        'account_id': data.get('account_id'),
                        'permissions': data.get('permissions', [])
                    })
                    
                    # Cache successful result
                    self.token_cache[cache_key] = (result.copy(), datetime.utcnow())
                else:
                    result['error'] = data.get('error', 'Token validation failed')
            else:
                result['error'] = f'Auth service error: {response.status_code}'
                
        except requests.exceptions.Timeout:
            result['error'] = 'Auth service timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Auth service unavailable'
        except Exception as e:
            result['error'] = f'Auth validation error: {str(e)}'
        
        return result
    
    def generate_service_token(self, service_name, permissions=None, expires_in=3600):
        """
        Generate JWT token for inter-service communication
        
        Args:
            service_name: Name of the service
            permissions: List of permissions
            expires_in: Token expiration in seconds
        
        Returns:
            str: JWT token
        """
        if permissions is None:
            permissions = []
        
        payload = {
            'service_name': service_name,
            'permissions': permissions,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def require_auth(self, permissions=None):
        """
        Decorator to require authentication for endpoints
        
        Args:
            permissions: Required permissions list
        
        Returns:
            Decorator function
        """
        if permissions is None:
            permissions = []
        
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get token from Authorization header
                auth_header = request.headers.get('Authorization')
                if not auth_header:
                    return jsonify({
                        'success': False,
                        'error': 'Authorization header required',
                        'error_code': 'MISSING_AUTH_HEADER'
                    }), 401
                
                # Extract token
                try:
                    token_type, token = auth_header.split(' ', 1)
                    if token_type.lower() != 'bearer':
                        return jsonify({
                            'success': False,
                            'error': 'Bearer token required',
                            'error_code': 'INVALID_AUTH_TYPE'
                        }), 401
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid authorization header format',
                        'error_code': 'INVALID_AUTH_FORMAT'
                    }), 401
                
                # Validate token
                validation_result = self.validate_user_token(token)
                
                if not validation_result['valid']:
                    return jsonify({
                        'success': False,
                        'error': validation_result['error'],
                        'error_code': 'AUTH_FAILED'
                    }), 401
                
                # Check permissions
                user_permissions = validation_result.get('permissions', [])
                if permissions and not any(perm in user_permissions for perm in permissions):
                    return jsonify({
                        'success': False,
                        'error': 'Insufficient permissions',
                        'error_code': 'INSUFFICIENT_PERMISSIONS'
                    }), 403
                
                # Add user info to request context
                request.user_id = validation_result['user_id']
                request.account_id = validation_result['account_id']
                request.user_permissions = user_permissions
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def require_service_auth(self, allowed_services=None):
        """
        Decorator to require service authentication for inter-service endpoints
        
        Args:
            allowed_services: List of allowed service names
        
        Returns:
            Decorator function
        """
        if allowed_services is None:
            allowed_services = []
        
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get service name from header
                service_name = request.headers.get('X-Service-Name')
                if not service_name:
                    return jsonify({
                        'success': False,
                        'error': 'Service name header required',
                        'error_code': 'MISSING_SERVICE_HEADER'
                    }), 401
                
                # Get token from Authorization header
                auth_header = request.headers.get('Authorization')
                if not auth_header:
                    return jsonify({
                        'success': False,
                        'error': 'Authorization header required',
                        'error_code': 'MISSING_AUTH_HEADER'
                    }), 401
                
                # Extract token
                try:
                    token_type, token = auth_header.split(' ', 1)
                    if token_type.lower() != 'bearer':
                        return jsonify({
                            'success': False,
                            'error': 'Bearer token required',
                            'error_code': 'INVALID_AUTH_TYPE'
                        }), 401
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid authorization header format',
                        'error_code': 'INVALID_AUTH_FORMAT'
                    }), 401
                
                # Validate service token
                validation_result = self.validate_service_token(token)
                
                if not validation_result['valid']:
                    return jsonify({
                        'success': False,
                        'error': validation_result['error'],
                        'error_code': 'SERVICE_AUTH_FAILED'
                    }), 401
                
                # Check if service is allowed
                if allowed_services and service_name not in allowed_services:
                    return jsonify({
                        'success': False,
                        'error': f'Service {service_name} not allowed',
                        'error_code': 'SERVICE_NOT_ALLOWED'
                    }), 403
                
                # Add service info to request context
                request.service_name = validation_result['service_name']
                request.service_permissions = validation_result['permissions']
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def clear_token_cache(self):
        """Clear token cache"""
        self.token_cache.clear()
    
    def get_cache_stats(self):
        """Get cache statistics"""
        return {
            'cached_tokens': len(self.token_cache),
            'cache_ttl': self.cache_ttl
        }

# Global auth service instance
auth_service = AuthService()

