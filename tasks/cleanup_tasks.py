import os
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import and_

from models import db, MediaFile, FileCleanupLog
from utils import file_storage
from services import telegive_service

class CleanupTasks:
    """Scheduled cleanup tasks for media files"""
    
    def __init__(self):
        self.batch_size = 100
        self.retry_attempts = 3
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.batch_size = app.config.get('CLEANUP_BATCH_SIZE', 100)
        self.retry_attempts = app.config.get('CLEANUP_RETRY_ATTEMPTS', 3)
    
    def cleanup_scheduled_files(self):
        """
        Clean up files that are scheduled for cleanup
        
        This task runs periodically to clean up files that have been
        scheduled for cleanup after giveaway publishing.
        """
        with current_app.app_context():
            try:
                current_app.logger.info('Starting scheduled file cleanup')
                
                # Find files scheduled for cleanup
                cutoff_time = datetime.utcnow()
                
                files_to_cleanup = MediaFile.query.filter(
                    and_(
                        MediaFile.cleanup_status == 'pending',
                        MediaFile.cleanup_scheduled_at <= cutoff_time,
                        MediaFile.is_active == True
                    )
                ).limit(self.batch_size).all()
                
                if not files_to_cleanup:
                    current_app.logger.debug('No files scheduled for cleanup')
                    return {
                        'success': True,
                        'files_processed': 0,
                        'files_cleaned': 0,
                        'errors': []
                    }
                
                cleanup_stats = {
                    'files_processed': len(files_to_cleanup),
                    'files_cleaned': 0,
                    'space_freed': 0,
                    'errors': []
                }
                
                for media_file in files_to_cleanup:
                    try:
                        result = self._cleanup_single_file(media_file)
                        
                        if result['success']:
                            cleanup_stats['files_cleaned'] += 1
                            cleanup_stats['space_freed'] += result.get('space_freed', 0)
                        else:
                            cleanup_stats['errors'].append({
                                'file_id': media_file.id,
                                'error': result.get('error', 'Unknown error')
                            })
                            
                    except Exception as e:
                        error_msg = f'Error cleaning up file {media_file.id}: {str(e)}'
                        cleanup_stats['errors'].append({
                            'file_id': media_file.id,
                            'error': error_msg
                        })
                        current_app.logger.error(error_msg)
                
                # Commit all changes
                db.session.commit()
                
                current_app.logger.info(
                    f'Cleanup completed: {cleanup_stats["files_cleaned"]}/{cleanup_stats["files_processed"]} files cleaned, '
                    f'{cleanup_stats["space_freed"]} bytes freed'
                )
                
                return {
                    'success': True,
                    **cleanup_stats
                }
                
            except Exception as e:
                db.session.rollback()
                error_msg = f'Scheduled cleanup failed: {str(e)}'
                current_app.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
    
    def _cleanup_single_file(self, media_file):
        """
        Clean up a single media file
        
        Args:
            media_file: MediaFile instance
        
        Returns:
            dict: Cleanup result
        """
        result = {
            'success': False,
            'space_freed': 0,
            'error': None
        }
        
        try:
            # Delete file from storage
            deletion_result = file_storage.delete_file(media_file.file_path)
            
            if deletion_result['success']:
                # Update database record
                media_file.mark_cleanup_completed()
                result['success'] = True
                result['space_freed'] = deletion_result.get('file_size_freed', 0)
                
                # Create cleanup log
                cleanup_log = FileCleanupLog.create_log(
                    media_file.id,
                    'scheduled',
                    True,
                    file_size_freed=result['space_freed']
                )
                db.session.add(cleanup_log)
                
                current_app.logger.debug(f'File {media_file.id} cleaned up successfully')
                
            else:
                # Log cleanup failure
                result['error'] = deletion_result.get('error', 'Unknown deletion error')
                media_file.cleanup_error = result['error']
                
                cleanup_log = FileCleanupLog.create_log(
                    media_file.id,
                    'scheduled',
                    False,
                    error_message=result['error']
                )
                db.session.add(cleanup_log)
                
                current_app.logger.warning(f'Failed to clean up file {media_file.id}: {result["error"]}')
                
        except Exception as e:
            result['error'] = str(e)
            current_app.logger.error(f'Exception during file cleanup {media_file.id}: {e}')
        
        return result
    
    def cleanup_orphaned_files(self):
        """
        Clean up orphaned files (files on disk without database records)
        
        This task runs less frequently to clean up any files that may have
        been left on disk without corresponding database records.
        """
        with current_app.app_context():
            try:
                current_app.logger.info('Starting orphaned file cleanup')
                
                upload_folder = current_app.config.get('UPLOAD_FOLDER', '/app/uploads')
                
                if not os.path.exists(upload_folder):
                    return {
                        'success': True,
                        'message': 'Upload folder does not exist'
                    }
                
                orphaned_files = []
                total_size_freed = 0
                
                # Walk through all files in upload directory
                for root, dirs, files in os.walk(upload_folder):
                    for file in files:
                        if file == '.gitkeep':  # Skip placeholder files
                            continue
                        
                        file_path = os.path.join(root, file)
                        
                        # Check if file exists in database
                        media_file = MediaFile.query.filter_by(file_path=file_path).first()
                        
                        if not media_file:
                            # Orphaned file found
                            try:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                
                                orphaned_files.append({
                                    'path': file_path,
                                    'size': file_size
                                })
                                total_size_freed += file_size
                                
                                current_app.logger.info(f'Removed orphaned file: {file_path}')
                                
                            except Exception as e:
                                current_app.logger.error(f'Failed to remove orphaned file {file_path}: {e}')
                
                # Clean up empty directories
                file_storage.cleanup_empty_directories()
                
                current_app.logger.info(
                    f'Orphaned file cleanup completed: {len(orphaned_files)} files removed, '
                    f'{total_size_freed} bytes freed'
                )
                
                return {
                    'success': True,
                    'orphaned_files_removed': len(orphaned_files),
                    'space_freed': total_size_freed,
                    'files': orphaned_files
                }
                
            except Exception as e:
                error_msg = f'Orphaned file cleanup failed: {str(e)}'
                current_app.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
    
    def cleanup_old_inactive_files(self, days_old=30):
        """
        Clean up old inactive files
        
        Args:
            days_old: Number of days after which inactive files should be cleaned
        """
        with current_app.app_context():
            try:
                current_app.logger.info(f'Starting cleanup of inactive files older than {days_old} days')
                
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                old_files = MediaFile.query.filter(
                    and_(
                        MediaFile.is_active == False,
                        MediaFile.cleanup_completed_at <= cutoff_date
                    )
                ).limit(self.batch_size).all()
                
                if not old_files:
                    return {
                        'success': True,
                        'files_processed': 0,
                        'message': 'No old inactive files to clean'
                    }
                
                files_removed = 0
                space_freed = 0
                
                for media_file in old_files:
                    try:
                        # Remove file from disk if it still exists
                        if os.path.exists(media_file.file_path):
                            file_size = os.path.getsize(media_file.file_path)
                            os.remove(media_file.file_path)
                            space_freed += file_size
                        
                        # Remove database record
                        db.session.delete(media_file)
                        files_removed += 1
                        
                    except Exception as e:
                        current_app.logger.error(f'Failed to remove old file {media_file.id}: {e}')
                
                db.session.commit()
                
                current_app.logger.info(
                    f'Old file cleanup completed: {files_removed} files removed, '
                    f'{space_freed} bytes freed'
                )
                
                return {
                    'success': True,
                    'files_processed': len(old_files),
                    'files_removed': files_removed,
                    'space_freed': space_freed
                }
                
            except Exception as e:
                db.session.rollback()
                error_msg = f'Old file cleanup failed: {str(e)}'
                current_app.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
    
    def get_cleanup_statistics(self):
        """
        Get cleanup statistics
        
        Returns:
            dict: Cleanup statistics
        """
        with current_app.app_context():
            try:
                stats = {
                    'pending_cleanup': MediaFile.query.filter_by(cleanup_status='pending').count(),
                    'completed_cleanup': MediaFile.query.filter_by(cleanup_status='published_and_removed').count(),
                    'permanent_files': MediaFile.query.filter_by(cleanup_status='permanent').count(),
                    'active_files': MediaFile.query.filter_by(is_active=True).count(),
                    'inactive_files': MediaFile.query.filter_by(is_active=False).count(),
                    'total_files': MediaFile.query.count()
                }
                
                # Calculate total size of active files
                total_size = db.session.query(
                    db.func.sum(MediaFile.file_size)
                ).filter(MediaFile.is_active == True).scalar() or 0
                
                stats['total_active_size'] = total_size
                
                # Get recent cleanup logs
                recent_cleanups = FileCleanupLog.query.filter(
                    FileCleanupLog.cleanup_timestamp >= datetime.utcnow() - timedelta(days=7)
                ).count()
                
                stats['recent_cleanups'] = recent_cleanups
                
                return {
                    'success': True,
                    'statistics': stats
                }
                
            except Exception as e:
                error_msg = f'Failed to get cleanup statistics: {str(e)}'
                current_app.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

# Global cleanup tasks instance
cleanup_tasks = CleanupTasks()

