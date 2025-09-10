import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import RequestEntityTooLarge

from config.settings import config
from models import init_db, db
from services import init_services
from tasks import init_tasks

def create_app(config_name=None):
    """Application factory pattern"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)
    
    # Initialize database
    init_db(app)
    
    # Initialize services
    init_services(app)
    
    # Initialize tasks
    init_tasks(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Setup logging
    setup_logging(app)
    
    return app

def init_extensions(app):
    """Initialize Flask extensions"""
    
    # CORS - Allow cross-origin requests from any origin
    CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '100 per hour')],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://')
    )
    limiter.init_app(app)
    
    # Store limiter in app for use in routes
    app.limiter = limiter

def register_blueprints(app):
    """Register application blueprints"""
    
    from routes.health import health_bp
    from routes.media import media_bp
    from routes.upload import upload_bp
    from routes.admin import admin_bp
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(media_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(admin_bp)

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'error_code': 'BAD_REQUEST'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'Unauthorized access',
            'error_code': 'UNAUTHORIZED'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Access forbidden',
            'error_code': 'FORBIDDEN'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Resource not found',
            'error_code': 'NOT_FOUND'
        }), 404
    
    @app.errorhandler(413)
    @app.errorhandler(RequestEntityTooLarge)
    def file_too_large(error):
        return jsonify({
            'success': False,
            'error': 'File too large',
            'error_code': 'FILE_TOO_LARGE',
            'details': {
                'max_allowed': app.config.get('MAX_CONTENT_LENGTH', 52428800)
            }
        }), 413
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded',
            'error_code': 'RATE_LIMIT_EXCEEDED',
            'details': {
                'retry_after': error.retry_after if hasattr(error, 'retry_after') else None
            }
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Internal server error: {error}')
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle unexpected exceptions"""
        db.session.rollback()
        app.logger.error(f'Unexpected error: {error}', exc_info=True)
        
        # Don't reveal internal error details in production
        if app.config.get('DEBUG'):
            return jsonify({
                'success': False,
                'error': str(error),
                'error_code': 'UNEXPECTED_ERROR'
            }), 500
        else:
            return jsonify({
                'success': False,
                'error': 'An unexpected error occurred',
                'error_code': 'UNEXPECTED_ERROR'
            }), 500

def setup_logging(app):
    """Setup application logging"""
    
    if not app.debug and not app.testing:
        # Production logging
        logging.basicConfig(
            level=getattr(logging, app.config.get('LOG_LEVEL', 'INFO')),
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        )
        
        app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        
        # Log to file if specified
        log_file = app.config.get('LOG_FILE')
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            app.logger.addHandler(file_handler)

# Create application instance
app = create_app()

@app.before_request
def before_request():
    """Before request handler"""
    
    # Log request details in debug mode
    if app.debug:
        app.logger.debug(f'{request.method} {request.url} - {request.remote_addr}')
    
    # Create upload directory if it doesn't exist
    upload_folder = app.config.get('UPLOAD_FOLDER', '/app/uploads')
    if not os.path.exists(upload_folder):
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except Exception as e:
            app.logger.error(f'Failed to create upload directory: {e}')

@app.after_request
def after_request(response):
    """After request handler"""
    
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Log response in debug mode
    if app.debug:
        app.logger.debug(f'Response: {response.status_code}')
    
    return response

if __name__ == '__main__':
    # Development server
    port = int(os.getenv('PORT', app.config.get('SERVICE_PORT', 8005)))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config.get('DEBUG', False)
    )

