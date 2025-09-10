import os
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import and_

from models import db, MediaFile, FileValidationLog
from utils import (
    file_validator, image_processor, video_processor,
    file_hasher, security_scanner
)

class ValidationTasks:
    """Scheduled validation tasks for media files"""
    
    def __init__(self):
        self.batch_size = 50
        self.validation_timeout = 300  # 5 minutes
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.batch_size = app.config.get('VALIDATION_BATCH_SIZE', 50)
    
    def validate_pending_files(self):
        """
        Validate files that haven't been validated yet
        
        This task runs periodically to validate files that were uploaded
        but haven't completed the validation process.
        """
        with current_app.app_context():
            try:
                current_app.logger.info('Starting pending file validation')
                
                # Find files that need validation
                pending_files = MediaFile.query.filter(
                    and_(
                        MediaFile.is_validated == False,
                        MediaFile.is_active == True
                    )
                ).limit(self.batch_size).all()
                
                if not pending_files:
                    current_app.logger.debug('No pending files to validate')
                    return {
                        'success': True,
                        'files_processed': 0,
                        'files_validated': 0,
                        'errors': []
                    }
                
                validation_stats = {
                    'files_processed': len(pending_files),
                    'files_validated': 0,
                    'files_failed': 0,
                    'errors': []
                }
                
                for media_file in pending_files:
                    try:
                        result = self._validate_single_file(media_file)
                        
                        if result['success']:
                            validation_stats['files_validated'] += 1
                        else:
                            validation_stats['files_failed'] += 1
                            validation_stats['errors'].append({
                                'file_id': media_file.id,
                                'error': result.get('error', 'Unknown error')
                            })
                            
                    except Exception as e:
                        error_msg = f'Error validating file {media_file.id}: {str(e)}'
                        validation_stats['errors'].append({
                            'file_id': media_file.id,
                            'error': error_msg
                        })
                        current_app.logger.error(error_msg)
                
                # Commit all changes
                db.session.commit()
                
                current_app.logger.info(
                    f'Validation completed: {validation_stats["files_validated"]}/{validation_stats["files_processed"]} files validated'
                )
                
                return {
                    'success': True,
                    **validation_stats
                }
                
            except Exception as e:
                db.session.rollback()
                error_msg = f'Pending file validation failed: {str(e)}'
                current_app.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
    
    def _validate_single_file(self, media_file):
        """
        Validate a single media file
        
        Args:
            media_file: MediaFile instance
        
        Returns:
            dict: Validation result
        """
        result = {
            'success': False,
            'error': None,
            'validation_details': {}
        }
        
        try:
            # Check if file exists on disk
            if not os.path.exists(media_file.file_path):
                result['error'] = 'File not found on disk'
                
                # Log validation failure
                validation_log = FileValidationLog.create_log(
                    media_file.id,
                    'file_existence',
                    False,
                    error_message=result['error']
                )
                db.session.add(validation_log)
                
                return result
            
            # Validate file integrity
            integrity_result = self._validate_file_integrity(media_file)
            result['validation_details']['integrity'] = integrity_result
            
            if not integrity_result['valid']:
                result['error'] = 'File integrity validation failed'
                return result
            
            # Validate file content
            content_result = self._validate_file_content(media_file)
            result['validation_details']['content'] = content_result
            
            if not content_result['valid']:
                result['error'] = 'File content validation failed'
                return result
            
            # Security validation if enabled
            if security_scanner.is_scanning_enabled():
                security_result = self._validate_file_security(media_file)
                result['validation_details']['security'] = security_result
                
                if not security_result['valid']:
                    result['error'] = 'File security validation failed'
                    return result
            
            # Update file validation status
            media_file.is_validated = True
            media_file.validation_error = None
            
            # Create successful validation log
            validation_log = FileValidationLog.create_log(
                media_file.id,
                'complete_validation',
                True,
                details=result['validation_details']
            )
            db.session.add(validation_log)
            
            result['success'] = True
            current_app.logger.debug(f'File {media_file.id} validated successfully')
            
        except Exception as e:
            result['error'] = str(e)
            
            # Update file with validation error
            media_file.validation_error = result['error']
            
            # Log validation failure
            validation_log = FileValidationLog.create_log(
                media_file.id,
                'validation_error',
                False,
                error_message=result['error']
            )
            db.session.add(validation_log)
            
            current_app.logger.error(f'Exception during file validation {media_file.id}: {e}')
        
        return result
    
    def _validate_file_integrity(self, media_file):
        """Validate file integrity using hash comparison"""
        result = {
            'valid': False,
            'error': None
        }
        
        try:
            # Calculate current file hash
            current_hash = file_hasher.calculate_hash(media_file.file_path)
            
            # Compare with stored hash
            if current_hash == media_file.file_hash:
                result['valid'] = True
            else:
                result['error'] = 'File hash mismatch - file may be corrupted'
                
        except Exception as e:
            result['error'] = f'Hash calculation failed: {str(e)}'
        
        return result
    
    def _validate_file_content(self, media_file):
        """Validate file content based on file type"""
        result = {
            'valid': False,
            'error': None,
            'metadata': {}
        }
        
        try:
            if media_file.file_type == 'image':
                # Validate image content
                validation_result = image_processor.validate_image_content(
                    open(media_file.file_path, 'rb').read()
                )
                
                if validation_result['valid']:
                    result['valid'] = True
                    result['metadata'] = {
                        'width': validation_result.get('width'),
                        'height': validation_result.get('height'),
                        'format': validation_result.get('format')
                    }
                else:
                    result['error'] = validation_result.get('error', 'Image validation failed')
                    
            elif media_file.file_type == 'video':
                # Validate video content
                validation_result = video_processor.validate_video_content(
                    open(media_file.file_path, 'rb').read()
                )
                
                if validation_result['valid']:
                    result['valid'] = True
                    result['metadata'] = {
                        'width': validation_result.get('width'),
                        'height': validation_result.get('height'),
                        'duration': validation_result.get('duration'),
                        'format': validation_result.get('format')
                    }
                else:
                    result['error'] = validation_result.get('error', 'Video validation failed')
            else:
                result['error'] = f'Unknown file type: {media_file.file_type}'
                
        except Exception as e:
            result['error'] = f'Content validation failed: {str(e)}'
        
        return result
    
    def _validate_file_security(self, media_file):
        """Validate file security"""
        result = {
            'valid': False,
            'error': None,
            'threats': []
        }
        
        try:
            # Read file content
            with open(media_file.file_path, 'rb') as f:
                file_content = f.read()
            
            # Perform security scan
            security_result = security_scanner.scan_file(
                file_content,
                media_file.original_filename,
                media_file.mime_type
            )
            
            if security_result['safe']:
                result['valid'] = True
            else:
                result['error'] = 'Security threats detected'
                result['threats'] = security_result['threats_detected']
                
        except Exception as e:
            result['error'] = f'Security validation failed: {str(e)}'
        
        return result
    
    def revalidate_failed_files(self):
        """
        Revalidate files that previously failed validation
        
        This task gives failed files another chance at validation,
        which might succeed if the failure was temporary.
        """
        with current_app.app_context():
            try:
                current_app.logger.info('Starting revalidation of failed files')
                
                # Find files with validation errors
                failed_files = MediaFile.query.filter(
                    and_(
                        MediaFile.is_validated == False,
                        MediaFile.validation_error.isnot(None),
                        MediaFile.is_active == True
                    )
                ).limit(self.batch_size // 2).all()  # Smaller batch for revalidation
                
                if not failed_files:
                    return {
                        'success': True,
                        'files_processed': 0,
                        'files_revalidated': 0,
                        'message': 'No failed files to revalidate'
                    }
                
                revalidation_stats = {
                    'files_processed': len(failed_files),
                    'files_revalidated': 0,
                    'still_failed': 0,
                    'errors': []
                }
                
                for media_file in failed_files:
                    try:
                        # Clear previous validation error
                        media_file.validation_error = None
                        
                        # Attempt revalidation
                        result = self._validate_single_file(media_file)
                        
                        if result['success']:
                            revalidation_stats['files_revalidated'] += 1
                        else:
                            revalidation_stats['still_failed'] += 1
                            
                    except Exception as e:
                        error_msg = f'Error revalidating file {media_file.id}: {str(e)}'
                        revalidation_stats['errors'].append({
                            'file_id': media_file.id,
                            'error': error_msg
                        })
                        current_app.logger.error(error_msg)
                
                db.session.commit()
                
                current_app.logger.info(
                    f'Revalidation completed: {revalidation_stats["files_revalidated"]}/{revalidation_stats["files_processed"]} files revalidated'
                )
                
                return {
                    'success': True,
                    **revalidation_stats
                }
                
            except Exception as e:
                db.session.rollback()
                error_msg = f'File revalidation failed: {str(e)}'
                current_app.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
    
    def get_validation_statistics(self):
        """
        Get validation statistics
        
        Returns:
            dict: Validation statistics
        """
        with current_app.app_context():
            try:
                stats = {
                    'validated_files': MediaFile.query.filter_by(is_validated=True).count(),
                    'pending_validation': MediaFile.query.filter_by(is_validated=False).count(),
                    'failed_validation': MediaFile.query.filter(
                        and_(
                            MediaFile.is_validated == False,
                            MediaFile.validation_error.isnot(None)
                        )
                    ).count(),
                    'total_files': MediaFile.query.count()
                }
                
                # Get recent validation logs
                recent_validations = FileValidationLog.query.filter(
                    FileValidationLog.validated_at >= datetime.utcnow() - timedelta(days=7)
                ).count()
                
                stats['recent_validations'] = recent_validations
                
                # Get validation success rate
                if stats['total_files'] > 0:
                    stats['validation_success_rate'] = (stats['validated_files'] / stats['total_files']) * 100
                else:
                    stats['validation_success_rate'] = 0
                
                return {
                    'success': True,
                    'statistics': stats
                }
                
            except Exception as e:
                error_msg = f'Failed to get validation statistics: {str(e)}'
                current_app.logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

# Global validation tasks instance
validation_tasks = ValidationTasks()

