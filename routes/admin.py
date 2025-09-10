"""
Admin routes for database management and service administration
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text
import logging
import os
from models import db, MediaFile, FileValidationLog, FileCleanupLog

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/init-db', methods=['POST'])
def init_database():
    """Initialize database tables"""
    try:
        # Create all tables
        db.create_all()
        db.session.commit()
        
        # Verify tables were created
        tables_created = []
        try:
            # Check if main tables exist
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            
            expected_tables = ['media_files', 'file_validation_logs', 'file_cleanup_logs']
            for table in expected_tables:
                if table in tables:
                    tables_created.append(table)
        except:
            # For PostgreSQL or other databases
            tables_created = ['media_files', 'file_validation_logs', 'file_cleanup_logs']
        
        return jsonify({
            'success': True,
            'message': 'Database tables created successfully',
            'tables_created': tables_created
        }), 200
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': 'DB_INIT_FAILED'
        }), 500

@admin_bp.route('/admin/db-status', methods=['GET'])
def database_status():
    """Check database status and table information"""
    try:
        # Test basic connection
        db.session.execute(text('SELECT 1'))
        
        # Get table counts
        table_counts = {}
        try:
            table_counts['media_files'] = MediaFile.query.count()
            table_counts['validation_logs'] = FileValidationLog.query.count()
            table_counts['cleanup_logs'] = FileCleanupLog.query.count()
        except Exception as e:
            logger.warning(f"Could not get table counts: {e}")
            table_counts = {'error': 'Tables may not be initialized'}
        
        return jsonify({
            'database_connected': True,
            'message': 'Database is accessible',
            'table_counts': table_counts,
            'database_url_host': os.getenv('DATABASE_URL', '').split('@')[1].split('/')[0] if '@' in os.getenv('DATABASE_URL', '') else 'localhost'
        }), 200
        
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return jsonify({
            'database_connected': False,
            'error': str(e),
            'error_code': 'DB_CONNECTION_FAILED'
        }), 500

@admin_bp.route('/admin/cleanup-orphaned', methods=['POST'])
def cleanup_orphaned_files():
    """Clean up orphaned file records (files that don't exist on disk)"""
    try:
        orphaned_count = 0
        space_freed = 0
        
        # Find files that don't exist on disk
        media_files = MediaFile.query.filter_by(is_active=True).all()
        
        for media_file in media_files:
            if not os.path.exists(media_file.file_path):
                # File doesn't exist on disk, mark as inactive
                media_file.is_active = False
                media_file.cleanup_status = 'file_not_found'
                
                # Create cleanup log
                cleanup_log = FileCleanupLog.create_log(
                    media_file.id,
                    'orphaned_cleanup',
                    True,
                    file_size_freed=media_file.file_size
                )
                db.session.add(cleanup_log)
                
                orphaned_count += 1
                space_freed += media_file.file_size
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {orphaned_count} orphaned file records',
            'orphaned_files_cleaned': orphaned_count,
            'space_freed_bytes': space_freed
        }), 200
        
    except Exception as e:
        logger.error(f"Orphaned file cleanup failed: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': 'ORPHANED_CLEANUP_FAILED'
        }), 500

@admin_bp.route('/admin/stats', methods=['GET'])
def get_service_stats():
    """Get comprehensive service statistics"""
    try:
        stats = {
            'database': {
                'connected': True,
                'total_files': 0,
                'active_files': 0,
                'inactive_files': 0,
                'total_storage_bytes': 0,
                'validation_logs': 0,
                'cleanup_logs': 0
            },
            'storage': {
                'upload_folder': os.getenv('UPLOAD_FOLDER', '/app/uploads'),
                'upload_folder_exists': False,
                'max_file_size': os.getenv('MAX_CONTENT_LENGTH', '52428800')
            },
            'service': {
                'name': os.getenv('SERVICE_NAME', 'media-service'),
                'port': os.getenv('SERVICE_PORT', '8005'),
                'environment': os.getenv('FLASK_ENV', 'production')
            }
        }
        
        # Get database statistics
        try:
            stats['database']['total_files'] = MediaFile.query.count()
            stats['database']['active_files'] = MediaFile.query.filter_by(is_active=True).count()
            stats['database']['inactive_files'] = MediaFile.query.filter_by(is_active=False).count()
            
            # Calculate total storage
            result = db.session.execute(text('SELECT SUM(file_size) FROM media_files WHERE is_active = true'))
            total_storage = result.scalar() or 0
            stats['database']['total_storage_bytes'] = total_storage
            
            stats['database']['validation_logs'] = FileValidationLog.query.count()
            stats['database']['cleanup_logs'] = FileCleanupLog.query.count()
            
        except Exception as e:
            logger.warning(f"Could not get database stats: {e}")
            stats['database']['error'] = str(e)
        
        # Check storage folder
        upload_folder = stats['storage']['upload_folder']
        stats['storage']['upload_folder_exists'] = os.path.exists(upload_folder)
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': 'STATS_FAILED'
        }), 500

@admin_bp.route('/admin/reset-db', methods=['POST'])
def reset_database():
    """Reset database (DANGER: This will delete all data)"""
    # Only allow in development/testing
    if os.getenv('FLASK_ENV') == 'production':
        return jsonify({
            'success': False,
            'error': 'Database reset not allowed in production',
            'error_code': 'OPERATION_NOT_ALLOWED'
        }), 403
    
    try:
        # Drop all tables
        db.drop_all()
        
        # Recreate all tables
        db.create_all()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Database reset successfully',
            'warning': 'All data has been deleted'
        }), 200
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': 'DB_RESET_FAILED'
        }), 500

@admin_bp.route('/admin/health-check', methods=['GET'])
def admin_health_check():
    """Comprehensive admin health check"""
    try:
        health_status = {
            'overall_status': 'healthy',
            'checks': {
                'database': 'unknown',
                'storage': 'unknown',
                'models': 'unknown'
            },
            'details': {}
        }
        
        # Database check
        try:
            db.session.execute(text('SELECT 1'))
            health_status['checks']['database'] = 'connected'
            health_status['details']['database'] = 'Connection successful'
        except Exception as e:
            health_status['checks']['database'] = 'disconnected'
            health_status['details']['database'] = str(e)
            health_status['overall_status'] = 'unhealthy'
        
        # Storage check
        upload_folder = os.getenv('UPLOAD_FOLDER', '/app/uploads')
        try:
            if os.path.exists(upload_folder) and os.access(upload_folder, os.W_OK):
                health_status['checks']['storage'] = 'accessible'
                health_status['details']['storage'] = f'Upload folder {upload_folder} is writable'
            else:
                health_status['checks']['storage'] = 'inaccessible'
                health_status['details']['storage'] = f'Upload folder {upload_folder} not accessible'
                health_status['overall_status'] = 'degraded'
        except Exception as e:
            health_status['checks']['storage'] = 'error'
            health_status['details']['storage'] = str(e)
            health_status['overall_status'] = 'degraded'
        
        # Models check
        try:
            # Try to query each model
            MediaFile.query.limit(1).all()
            FileValidationLog.query.limit(1).all()
            FileCleanupLog.query.limit(1).all()
            health_status['checks']['models'] = 'working'
            health_status['details']['models'] = 'All models accessible'
        except Exception as e:
            health_status['checks']['models'] = 'error'
            health_status['details']['models'] = str(e)
            health_status['overall_status'] = 'unhealthy'
        
        status_code = 200 if health_status['overall_status'] == 'healthy' else 503
        
        return jsonify({
            'success': True,
            'health': health_status
        }), status_code
        
    except Exception as e:
        logger.error(f"Admin health check failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_code': 'HEALTH_CHECK_FAILED'
        }), 500

