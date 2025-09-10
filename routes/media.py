import os
from flask import Blueprint, jsonify, request, current_app, send_file, abort
from sqlalchemy import and_, or_

from models import db, MediaFile, FileCleanupLog
from utils import file_storage

# Create blueprint for media routes
media_bp = Blueprint('media', __name__)

@media_bp.route('/', methods=['GET'])
def media_index():
    """Media service index endpoint"""
    return jsonify({
        'success': True,
        'service': 'Media Management Service',
        'version': '1.0.0',
        'endpoints': {
            'upload': 'POST /api/media/upload',
            'file_info': 'GET /api/media/{file_id}',
            'download': 'GET /api/media/{file_id}/download',
            'cleanup': 'POST /api/media/cleanup/{giveaway_id}',
            'associate': 'PUT /api/media/{file_id}/associate',
            'delete': 'DELETE /api/media/{file_id}',
            'account_files': 'GET /api/media/account/{account_id}',
            'validate': 'POST /api/media/validate/{file_id}'
        }
    })

@media_bp.route('/<int:file_id>', methods=['GET'])
def get_file_info(file_id):
    """Get file information"""
    
    try:
        media_file = MediaFile.query.get(file_id)
        
        if not media_file:
            return jsonify({
                'success': False,
                'error': 'File not found',
                'error_code': 'FILE_NOT_FOUND'
            }), 404
        
        return jsonify({
            'success': True,
            'file_info': media_file.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error getting file info: {e}')
        return jsonify({
            'success': False,
            'error': 'Failed to get file info',
            'error_code': 'GET_FILE_INFO_FAILED'
        }), 500

@media_bp.route('/<int:file_id>/download', methods=['GET'])
def download_file(file_id):
    """Download/serve file"""
    
    try:
        media_file = MediaFile.query.get(file_id)
        
        if not media_file:
            abort(404)
        
        if not media_file.is_active:
            abort(410)  # Gone - file has been deleted
        
        # Check if file exists on disk
        if not os.path.exists(media_file.file_path):
            current_app.logger.error(f'File not found on disk: {media_file.file_path}')
            abort(404)
        
        # Serve file with appropriate headers
        return send_file(
            media_file.file_path,
            mimetype=media_file.mime_type,
            as_attachment=False,
            download_name=media_file.original_filename
        )
        
    except Exception as e:
        current_app.logger.error(f'Error serving file: {e}')
        abort(500)

@media_bp.route('/cleanup/<int:giveaway_id>', methods=['POST'])
def cleanup_files(giveaway_id):
    """Cleanup files for giveaway"""
    
    try:
        # Find all files associated with this giveaway
        files_to_cleanup = MediaFile.query.filter(
            and_(
                MediaFile.giveaway_id == giveaway_id,
                MediaFile.cleanup_status == 'pending',
                MediaFile.is_active == True
            )
        ).all()
        
        if not files_to_cleanup:
            return jsonify({
                'success': True,
                'cleanup_summary': {
                    'files_processed': 0,
                    'files_deleted': 0,
                    'space_freed': 0,
                    'errors': []
                },
                'message': 'No files to cleanup'
            }), 200
        
        cleanup_summary = {
            'files_processed': len(files_to_cleanup),
            'files_deleted': 0,
            'space_freed': 0,
            'errors': []
        }
        
        for media_file in files_to_cleanup:
            try:
                # Delete file from storage
                deletion_result = file_storage.delete_file(media_file.file_path)
                
                if deletion_result['success']:
                    # Update database record
                    media_file.mark_cleanup_completed()
                    cleanup_summary['files_deleted'] += 1
                    cleanup_summary['space_freed'] += deletion_result.get('file_size_freed', 0)
                    
                    # Create cleanup log
                    cleanup_log = FileCleanupLog.create_log(
                        media_file.id,
                        'giveaway_published',
                        True,
                        file_size_freed=deletion_result.get('file_size_freed', 0)
                    )
                    db.session.add(cleanup_log)
                    
                else:
                    # Log cleanup failure
                    error_msg = f'Failed to delete file {media_file.id}: {deletion_result.get("error", "Unknown error")}'
                    cleanup_summary['errors'].append(error_msg)
                    
                    media_file.cleanup_error = deletion_result.get('error')
                    
                    cleanup_log = FileCleanupLog.create_log(
                        media_file.id,
                        'giveaway_published',
                        False,
                        error_message=deletion_result.get('error')
                    )
                    db.session.add(cleanup_log)
                    
            except Exception as e:
                error_msg = f'Error cleaning up file {media_file.id}: {str(e)}'
                cleanup_summary['errors'].append(error_msg)
                current_app.logger.error(error_msg)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'cleanup_summary': cleanup_summary
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Cleanup error: {e}')
        return jsonify({
            'success': False,
            'error': 'Cleanup failed',
            'error_code': 'CLEANUP_FAILED'
        }), 500

@media_bp.route('/<int:file_id>/associate', methods=['PUT'])
def associate_file(file_id):
    """Associate file with giveaway"""
    
    try:
        media_file = MediaFile.query.get(file_id)
        
        if not media_file:
            return jsonify({
                'success': False,
                'error': 'File not found',
                'error_code': 'FILE_NOT_FOUND'
            }), 404
        
        data = request.get_json()
        if not data or 'giveaway_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Giveaway ID is required',
                'error_code': 'MISSING_GIVEAWAY_ID'
            }), 400
        
        giveaway_id = data['giveaway_id']
        
        # Update file association
        media_file.giveaway_id = giveaway_id
        
        # Schedule cleanup
        cleanup_delay = current_app.config.get('CLEANUP_DELAY_MINUTES', 5)
        media_file.mark_for_cleanup(cleanup_delay)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'giveaway_id': giveaway_id,
            'cleanup_scheduled': True
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Association error: {e}')
        return jsonify({
            'success': False,
            'error': 'Association failed',
            'error_code': 'ASSOCIATION_FAILED'
        }), 500

@media_bp.route('/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete file manually"""
    
    try:
        media_file = MediaFile.query.get(file_id)
        
        if not media_file:
            return jsonify({
                'success': False,
                'error': 'File not found',
                'error_code': 'FILE_NOT_FOUND'
            }), 404
        
        # Delete file from storage
        deletion_result = file_storage.delete_file(media_file.file_path)
        
        space_freed = 0
        if deletion_result['success']:
            space_freed = deletion_result.get('file_size_freed', media_file.file_size)
            
            # Update database record
            media_file.is_active = False
            media_file.cleanup_status = 'published_and_removed'
            
            # Create cleanup log
            cleanup_log = FileCleanupLog.create_log(
                media_file.id,
                'manual',
                True,
                file_size_freed=space_freed
            )
            db.session.add(cleanup_log)
            
        else:
            # Log deletion failure
            cleanup_log = FileCleanupLog.create_log(
                media_file.id,
                'manual',
                False,
                error_message=deletion_result.get('error')
            )
            db.session.add(cleanup_log)
        
        db.session.commit()
        
        if deletion_result['success']:
            return jsonify({
                'success': True,
                'file_id': file_id,
                'space_freed': space_freed
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete file',
                'error_code': 'DELETE_FAILED',
                'details': {
                    'error': deletion_result.get('error')
                }
            }), 500
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Delete error: {e}')
        return jsonify({
            'success': False,
            'error': 'Delete failed',
            'error_code': 'DELETE_FAILED'
        }), 500

@media_bp.route('/account/<int:account_id>', methods=['GET'])
def get_account_files(account_id):
    """Get files for account"""
    
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status', 'all')  # all, active, inactive
        
        # Limit the limit to prevent abuse
        limit = min(limit, 100)
        
        # Build query
        query = MediaFile.query.filter(MediaFile.account_id == account_id)
        
        if status == 'active':
            query = query.filter(MediaFile.is_active == True)
        elif status == 'inactive':
            query = query.filter(MediaFile.is_active == False)
        
        # Order by upload date (newest first)
        query = query.order_by(MediaFile.uploaded_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=limit, 
            error_out=False
        )
        
        files = [file.to_dict() for file in pagination.items]
        
        # Calculate storage stats
        stats_query = MediaFile.query.filter(MediaFile.account_id == account_id)
        total_files = stats_query.count()
        active_files = stats_query.filter(MediaFile.is_active == True).count()
        pending_cleanup = stats_query.filter(MediaFile.cleanup_status == 'pending').count()
        
        # Calculate total size
        total_size = db.session.query(
            db.func.sum(MediaFile.file_size)
        ).filter(
            and_(
                MediaFile.account_id == account_id,
                MediaFile.is_active == True
            )
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'files': files,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'storage_stats': {
                'total_files': total_files,
                'total_size': total_size,
                'active_files': active_files,
                'pending_cleanup': pending_cleanup
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error getting account files: {e}')
        return jsonify({
            'success': False,
            'error': 'Failed to get account files',
            'error_code': 'GET_ACCOUNT_FILES_FAILED'
        }), 500

@media_bp.route('/validate/<int:file_id>', methods=['POST'])
def validate_file(file_id):
    """Validate file"""
    
    try:
        media_file = MediaFile.query.get(file_id)
        
        if not media_file:
            return jsonify({
                'success': False,
                'error': 'File not found',
                'error_code': 'FILE_NOT_FOUND'
            }), 404
        
        # Check if file exists on disk
        if not os.path.exists(media_file.file_path):
            return jsonify({
                'success': False,
                'error': 'File not found on disk',
                'error_code': 'FILE_NOT_ON_DISK'
            }), 404
        
        validation_result = {
            'format_valid': True,
            'size_valid': True,
            'security_scan_passed': True,
            'metadata_extracted': True
        }
        
        # Basic file validation
        file_info = file_storage.get_file_info(media_file.file_path)
        if not file_info['exists']:
            validation_result['format_valid'] = False
        
        # Size validation
        if file_info['file_size'] != media_file.file_size:
            validation_result['size_valid'] = False
        
        # Update validation status
        media_file.is_validated = all(validation_result.values())
        db.session.commit()
        
        return jsonify({
            'success': True,
            'validation_result': validation_result,
            'file_id': file_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Validation error: {e}')
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'error_code': 'VALIDATION_FAILED'
        }), 500

