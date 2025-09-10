import os
import psutil
from flask import Blueprint, jsonify, current_app
from models import db
from sqlalchemy import text

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    
    try:
        # Check database connection
        db_status = check_database_connection()
        
        # Check storage
        storage_info = check_storage()
        
        # Check external services
        external_services = check_external_services()
        
        # Overall health status
        is_healthy = (
            db_status['connected'] and 
            storage_info['available'] and
            all(service['accessible'] for service in external_services.values())
        )
        
        response = {
            'status': 'healthy' if is_healthy else 'unhealthy',
            'service': current_app.config.get('SERVICE_NAME', 'media-service'),
            'version': '1.0.0',
            'database': db_status,
            'storage': storage_info,
            'external_services': external_services
        }
        
        status_code = 200 if is_healthy else 503
        return jsonify(response), status_code
        
    except Exception as e:
        current_app.logger.error(f'Health check failed: {e}')
        return jsonify({
            'status': 'unhealthy',
            'service': current_app.config.get('SERVICE_NAME', 'media-service'),
            'error': str(e)
        }), 503

def check_database_connection():
    """Check database connection status"""
    try:
        # Simple query to test connection
        result = db.session.execute(text('SELECT 1'))
        result.fetchone()
        
        # Get file count from media_files table
        file_count_result = db.session.execute(text('SELECT COUNT(*) FROM media_files'))
        total_files = file_count_result.scalar()
        
        return {
            'connected': True,
            'total_files': total_files
        }
    except Exception as e:
        current_app.logger.error(f'Database health check failed: {e}')
        return {
            'connected': False,
            'error': str(e)
        }

def check_storage():
    """Check storage status"""
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', '/app/uploads')
        
        # Check if upload folder exists
        if not os.path.exists(upload_folder):
            return {
                'available': False,
                'error': 'Upload folder does not exist',
                'upload_folder': upload_folder
            }
        
        # Get disk usage
        disk_usage = psutil.disk_usage(upload_folder)
        available_space_gb = disk_usage.free / (1024**3)
        total_space_gb = disk_usage.total / (1024**3)
        used_space_gb = disk_usage.used / (1024**3)
        
        # Count files in upload folder
        file_count = 0
        try:
            for root, dirs, files in os.walk(upload_folder):
                file_count += len(files)
        except Exception:
            file_count = 'unknown'
        
        return {
            'available': True,
            'upload_folder': upload_folder,
            'available_space_gb': round(available_space_gb, 2),
            'total_space_gb': round(total_space_gb, 2),
            'used_space_gb': round(used_space_gb, 2),
            'usage_percentage': round((used_space_gb / total_space_gb) * 100, 2),
            'total_files': file_count
        }
        
    except Exception as e:
        current_app.logger.error(f'Storage health check failed: {e}')
        return {
            'available': False,
            'error': str(e)
        }

def check_external_services():
    """Check external service connectivity"""
    import requests
    
    services = {}
    
    # Check auth service
    auth_url = current_app.config.get('TELEGIVE_AUTH_URL')
    if auth_url:
        services['auth_service'] = check_service_url(f"{auth_url}/health")
    
    # Check giveaway service
    giveaway_url = current_app.config.get('TELEGIVE_GIVEAWAY_URL')
    if giveaway_url:
        services['telegive_service'] = check_service_url(f"{giveaway_url}/health")
    
    return services

def check_service_url(url, timeout=5):
    """Check if a service URL is accessible"""
    try:
        response = requests.get(url, timeout=timeout)
        return {
            'accessible': response.status_code == 200,
            'status_code': response.status_code,
            'response_time_ms': round(response.elapsed.total_seconds() * 1000, 2)
        }
    except requests.exceptions.Timeout:
        return {
            'accessible': False,
            'error': 'Timeout'
        }
    except requests.exceptions.ConnectionError:
        return {
            'accessible': False,
            'error': 'Connection error'
        }
    except Exception as e:
        return {
            'accessible': False,
            'error': str(e)
        }

@health_bp.route('/health/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check with more information"""
    
    try:
        # Basic health info
        basic_health = health_check()
        health_data = basic_health[0].get_json()
        
        # Add system information
        health_data['system'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
        
        # Add configuration info (non-sensitive)
        health_data['configuration'] = {
            'max_content_length': current_app.config.get('MAX_CONTENT_LENGTH'),
            'max_image_size': current_app.config.get('MAX_IMAGE_SIZE'),
            'max_video_size': current_app.config.get('MAX_VIDEO_SIZE'),
            'allowed_image_extensions': current_app.config.get('ALLOWED_IMAGE_EXTENSIONS'),
            'allowed_video_extensions': current_app.config.get('ALLOWED_VIDEO_EXTENSIONS'),
            'cleanup_delay_minutes': current_app.config.get('CLEANUP_DELAY_MINUTES'),
            'cdn_enabled': current_app.config.get('CDN_ENABLED')
        }
        
        return jsonify(health_data), basic_health[1]
        
    except Exception as e:
        current_app.logger.error(f'Detailed health check failed: {e}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

