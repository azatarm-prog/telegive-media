import os
from flask import Blueprint, jsonify, request, current_app
from werkzeug.exceptions import RequestEntityTooLarge

from models import db, MediaFile, FileValidationLog
from utils import (
    file_validator, image_processor, video_processor, 
    file_hasher, file_storage, security_scanner
)

# Create blueprint for upload routes
upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload media file"""
    
    try:
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided',
                'error_code': 'NO_FILE'
            }), 400
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected',
                'error_code': 'NO_FILE_SELECTED'
            }), 400
        
        # Get account_id from form data
        account_id = request.form.get('account_id')
        if not account_id:
            return jsonify({
                'success': False,
                'error': 'Account ID is required',
                'error_code': 'MISSING_ACCOUNT_ID'
            }), 400
        
        try:
            account_id = int(account_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid account ID',
                'error_code': 'INVALID_ACCOUNT_ID'
            }), 400
        
        # Get client IP for logging
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Read file content
        file.seek(0)
        file_content = file.read()
        file.seek(0)
        
        # Validate file
        validation_result = file_validator.validate_file(file)
        if not validation_result['valid']:
            # Log validation failure
            current_app.logger.warning(f'File validation failed for {file.filename}: {validation_result["errors"]}')
            
            return jsonify({
                'success': False,
                'error': 'File validation failed',
                'error_code': 'VALIDATION_FAILED',
                'details': {
                    'errors': validation_result['errors']
                }
            }), 400
        
        file_info = validation_result['file_info']
        
        # Security scan if enabled
        if security_scanner.is_scanning_enabled():
            security_result = security_scanner.scan_file(
                file_content, 
                file.filename, 
                file_info['mime_type']
            )
            
            if not security_result['safe']:
                current_app.logger.warning(f'Security scan failed for {file.filename}: {security_result["threats_detected"]}')
                
                return jsonify({
                    'success': False,
                    'error': 'File failed security scan',
                    'error_code': 'SECURITY_SCAN_FAILED',
                    'details': {
                        'threats': security_result['threats_detected'],
                        'risk_level': security_result['risk_level']
                    }
                }), 400
        
        # Calculate file hash for deduplication
        file_hash = file_hasher.calculate_hash(file_content)
        
        # Check for duplicate file
        existing_file = MediaFile.query.filter_by(
            account_id=account_id,
            file_hash=file_hash
        ).first()
        
        if existing_file and existing_file.is_active:
            # Return existing file info
            return jsonify({
                'success': True,
                'file_info': existing_file.to_dict(),
                'duplicate_detected': True,
                'existing_file_id': existing_file.id,
                'message': 'File already exists, using existing file'
            }), 200
        
        # Extract metadata based on file type
        metadata = {}
        if file_info['file_type'] == 'image':
            metadata = image_processor.extract_metadata(file_content)
        elif file_info['file_type'] == 'video':
            metadata = video_processor.extract_metadata(file_content)
        
        # Save file to storage
        storage_result = file_storage.save_file_content(
            file_content, 
            file.filename, 
            account_id
        )
        
        if not storage_result['success']:
            return jsonify({
                'success': False,
                'error': 'Failed to save file',
                'error_code': 'STORAGE_FAILED',
                'details': {
                    'error': storage_result['error']
                }
            }), 500
        
        # Create database record
        media_file = MediaFile(
            account_id=account_id,
            original_filename=file_info['filename'],
            stored_filename=storage_result['stored_filename'],
            file_path=storage_result['file_path'],
            file_size=file_info['file_size'],
            file_type=file_info['file_type'],
            mime_type=file_info['mime_type'],
            file_extension=file_info['file_extension'],
            width=metadata.get('width'),
            height=metadata.get('height'),
            duration=metadata.get('duration'),
            file_hash=file_hash,
            uploaded_by_ip=client_ip,
            is_validated=True
        )
        
        db.session.add(media_file)
        db.session.flush()  # Get the ID
        
        # Create validation log
        validation_log = FileValidationLog.create_log(
            media_file.id,
            'complete',
            True,
            details={
                'file_type': file_info['file_type'],
                'mime_type': file_info['mime_type'],
                'file_size': file_info['file_size'],
                'security_scan': security_scanner.is_scanning_enabled()
            }
        )
        db.session.add(validation_log)
        
        db.session.commit()
        
        current_app.logger.info(f'File uploaded successfully: {file.filename} -> {media_file.id}')
        
        return jsonify({
            'success': True,
            'file_info': media_file.to_dict(),
            'duplicate_detected': False
        }), 201
        
    except RequestEntityTooLarge:
        return jsonify({
            'success': False,
            'error': 'File too large',
            'error_code': 'FILE_TOO_LARGE',
            'details': {
                'max_allowed': current_app.config.get('MAX_CONTENT_LENGTH')
            }
        }), 413
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Upload error: {e}', exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Upload failed',
            'error_code': 'UPLOAD_FAILED',
            'details': {
                'error': str(e) if current_app.debug else 'Internal error'
            }
        }), 500

@upload_bp.route('/upload/status', methods=['GET'])
def upload_status():
    """Get upload status and configuration"""
    return jsonify({
        'success': True,
        'upload_config': {
            'max_content_length': current_app.config.get('MAX_CONTENT_LENGTH'),
            'max_image_size': current_app.config.get('MAX_IMAGE_SIZE'),
            'max_video_size': current_app.config.get('MAX_VIDEO_SIZE'),
            'allowed_image_extensions': current_app.config.get('ALLOWED_IMAGE_EXTENSIONS'),
            'allowed_video_extensions': current_app.config.get('ALLOWED_VIDEO_EXTENSIONS'),
            'image_quality': current_app.config.get('IMAGE_QUALITY'),
            'video_validation_enabled': current_app.config.get('VIDEO_VALIDATION_ENABLED'),
            'security_scan_enabled': security_scanner.is_scanning_enabled()
        }
    })

