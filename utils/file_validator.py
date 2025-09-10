import os
import magic
from werkzeug.utils import secure_filename
from flask import current_app

class FileValidator:
    """File validation utilities"""
    
    def __init__(self):
        self.magic = magic.Magic(mime=True)
    
    def validate_file(self, file, file_type=None):
        """
        Comprehensive file validation
        
        Args:
            file: FileStorage object from Flask
            file_type: Expected file type ('image' or 'video')
        
        Returns:
            dict: Validation result with success status and details
        """
        result = {
            'valid': False,
            'errors': [],
            'file_info': {},
            'security_passed': False
        }
        
        try:
            # Basic file checks
            if not file or not file.filename:
                result['errors'].append('No file provided')
                return result
            
            # Secure filename
            filename = secure_filename(file.filename)
            if not filename:
                result['errors'].append('Invalid filename')
                return result
            
            # Get file extension
            file_extension = self._get_file_extension(filename)
            if not file_extension:
                result['errors'].append('File has no extension')
                return result
            
            # Detect file type from extension
            detected_type = self._detect_file_type(file_extension)
            if not detected_type:
                result['errors'].append(f'Unsupported file extension: {file_extension}')
                return result
            
            # Validate against expected type
            if file_type and file_type != detected_type:
                result['errors'].append(f'Expected {file_type} file, got {detected_type}')
                return result
            
            # Read file content for validation
            file.seek(0)
            file_content = file.read()
            file.seek(0)  # Reset for future reads
            
            if not file_content:
                result['errors'].append('File is empty')
                return result
            
            # Validate file size
            file_size = len(file_content)
            size_valid, size_error = self._validate_file_size(file_size, detected_type)
            if not size_valid:
                result['errors'].append(size_error)
                return result
            
            # Validate MIME type
            mime_type = self._get_mime_type(file_content)
            mime_valid, mime_error = self._validate_mime_type(mime_type, detected_type, file_extension)
            if not mime_valid:
                result['errors'].append(mime_error)
                return result
            
            # Security validation
            security_valid, security_error = self._validate_security(file_content, mime_type)
            if not security_valid:
                result['errors'].append(security_error)
                return result
            
            # All validations passed
            result.update({
                'valid': True,
                'security_passed': True,
                'file_info': {
                    'filename': filename,
                    'file_type': detected_type,
                    'file_extension': file_extension,
                    'mime_type': mime_type,
                    'file_size': file_size
                }
            })
            
        except Exception as e:
            result['errors'].append(f'Validation error: {str(e)}')
        
        return result
    
    def _get_file_extension(self, filename):
        """Get file extension in lowercase"""
        return os.path.splitext(filename)[1].lower().lstrip('.')
    
    def _detect_file_type(self, extension):
        """Detect file type from extension"""
        image_extensions = current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', ['jpg', 'jpeg', 'png', 'gif'])
        video_extensions = current_app.config.get('ALLOWED_VIDEO_EXTENSIONS', ['mp4', 'mov', 'avi'])
        
        if extension in image_extensions:
            return 'image'
        elif extension in video_extensions:
            return 'video'
        else:
            return None
    
    def _validate_file_size(self, file_size, file_type):
        """Validate file size based on type"""
        if file_type == 'image':
            max_size = current_app.config.get('MAX_IMAGE_SIZE', 10485760)  # 10MB
        elif file_type == 'video':
            max_size = current_app.config.get('MAX_VIDEO_SIZE', 52428800)  # 50MB
        else:
            return False, 'Unknown file type'
        
        if file_size > max_size:
            return False, f'File too large: {file_size} bytes (max: {max_size} bytes)'
        
        if file_size == 0:
            return False, 'File is empty'
        
        return True, None
    
    def _get_mime_type(self, file_content):
        """Get MIME type from file content"""
        try:
            return self.magic.from_buffer(file_content)
        except Exception:
            return 'application/octet-stream'
    
    def _validate_mime_type(self, mime_type, file_type, extension):
        """Validate MIME type matches file type and extension"""
        
        # Expected MIME types for each file type
        expected_mimes = {
            'image': {
                'jpg': ['image/jpeg'],
                'jpeg': ['image/jpeg'],
                'png': ['image/png'],
                'gif': ['image/gif']
            },
            'video': {
                'mp4': ['video/mp4', 'video/quicktime'],
                'mov': ['video/quicktime'],
                'avi': ['video/x-msvideo', 'video/avi']
            }
        }
        
        if file_type not in expected_mimes:
            return False, f'Unknown file type: {file_type}'
        
        if extension not in expected_mimes[file_type]:
            return False, f'Unsupported extension for {file_type}: {extension}'
        
        expected_mime_list = expected_mimes[file_type][extension]
        if mime_type not in expected_mime_list:
            return False, f'MIME type mismatch: got {mime_type}, expected one of {expected_mime_list}'
        
        return True, None
    
    def _validate_security(self, file_content, mime_type):
        """Basic security validation"""
        
        # Check for suspicious patterns in file headers
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'onload=',
            b'onerror=',
            b'<?php',
            b'<%',
            b'#!/bin/',
            b'#!/usr/bin/'
        ]
        
        # Check first 1KB for suspicious content
        header_content = file_content[:1024].lower()
        
        for pattern in suspicious_patterns:
            if pattern in header_content:
                return False, f'Suspicious content detected: {pattern.decode("utf-8", errors="ignore")}'
        
        # Additional checks for specific MIME types
        if mime_type.startswith('image/'):
            return self._validate_image_security(file_content)
        elif mime_type.startswith('video/'):
            return self._validate_video_security(file_content)
        
        return True, None
    
    def _validate_image_security(self, file_content):
        """Security validation specific to images"""
        
        # Check for embedded scripts in image metadata
        # This is a basic check - in production, use more sophisticated tools
        
        # Look for common script patterns in the entire file
        script_patterns = [
            b'<script',
            b'javascript',
            b'eval(',
            b'document.',
            b'window.'
        ]
        
        content_lower = file_content.lower()
        for pattern in script_patterns:
            if pattern in content_lower:
                return False, f'Potentially malicious content in image: {pattern.decode("utf-8", errors="ignore")}'
        
        return True, None
    
    def _validate_video_security(self, file_content):
        """Security validation specific to videos"""
        
        # Basic video security checks
        # In production, integrate with proper video analysis tools
        
        # Check file size isn't suspiciously small for a video
        if len(file_content) < 1000:  # Less than 1KB is suspicious for video
            return False, 'Video file suspiciously small'
        
        return True, None
    
    def get_allowed_extensions(self):
        """Get all allowed file extensions"""
        image_exts = current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', [])
        video_exts = current_app.config.get('ALLOWED_VIDEO_EXTENSIONS', [])
        return {
            'image': image_exts,
            'video': video_exts,
            'all': image_exts + video_exts
        }
    
    def is_allowed_extension(self, filename):
        """Check if filename has allowed extension"""
        extension = self._get_file_extension(filename)
        allowed = self.get_allowed_extensions()['all']
        return extension in allowed

# Global validator instance
file_validator = FileValidator()

