import os
import re
import magic
from flask import current_app

class SecurityScanner:
    """Security scanning utilities for uploaded files"""
    
    def __init__(self):
        self.magic = magic.Magic(mime=True)
        
        # Suspicious file patterns
        self.suspicious_patterns = [
            # Script patterns
            b'<script',
            b'</script>',
            b'javascript:',
            b'vbscript:',
            b'onload=',
            b'onerror=',
            b'onclick=',
            b'onmouseover=',
            
            # Server-side script patterns
            b'<?php',
            b'<%',
            b'<asp:',
            b'#!/bin/',
            b'#!/usr/bin/',
            
            # Executable patterns
            b'MZ',  # PE executable header
            b'\x7fELF',  # ELF executable header
            
            # Archive with executables
            b'PK\x03\x04',  # ZIP header (need additional checks)
        ]
        
        # Dangerous file extensions
        self.dangerous_extensions = [
            'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js',
            'jar', 'app', 'deb', 'pkg', 'dmg', 'rpm',
            'php', 'asp', 'aspx', 'jsp', 'py', 'rb', 'pl',
            'sh', 'bash', 'zsh', 'fish'
        ]
        
        # MIME types that should be blocked
        self.blocked_mime_types = [
            'application/x-executable',
            'application/x-msdownload',
            'application/x-msdos-program',
            'application/x-dosexec',
            'application/x-winexe',
            'application/x-sh',
            'application/x-shellscript',
            'text/x-php',
            'application/x-php',
            'text/x-python',
            'application/x-python-code'
        ]
    
    def scan_file(self, file_content, filename=None, mime_type=None):
        """
        Comprehensive security scan of file content
        
        Args:
            file_content: File content as bytes
            filename: Original filename (optional)
            mime_type: MIME type (optional, will be detected if not provided)
        
        Returns:
            dict: Security scan result
        """
        result = {
            'safe': True,
            'threats_detected': [],
            'risk_level': 'low',  # low, medium, high, critical
            'scan_details': {}
        }
        
        try:
            # Detect MIME type if not provided
            if mime_type is None:
                mime_type = self._detect_mime_type(file_content)
            
            # Check MIME type
            mime_check = self._check_mime_type(mime_type)
            if not mime_check['safe']:
                result['safe'] = False
                result['threats_detected'].extend(mime_check['threats'])
                result['risk_level'] = 'high'
            
            # Check filename extension
            if filename:
                ext_check = self._check_file_extension(filename)
                if not ext_check['safe']:
                    result['safe'] = False
                    result['threats_detected'].extend(ext_check['threats'])
                    result['risk_level'] = 'high'
            
            # Check file content patterns
            pattern_check = self._check_suspicious_patterns(file_content)
            if not pattern_check['safe']:
                result['safe'] = False
                result['threats_detected'].extend(pattern_check['threats'])
                if result['risk_level'] == 'low':
                    result['risk_level'] = 'medium'
            
            # Check file headers
            header_check = self._check_file_headers(file_content)
            if not header_check['safe']:
                result['safe'] = False
                result['threats_detected'].extend(header_check['threats'])
                result['risk_level'] = 'high'
            
            # Check for embedded content
            embedded_check = self._check_embedded_content(file_content, mime_type)
            if not embedded_check['safe']:
                result['safe'] = False
                result['threats_detected'].extend(embedded_check['threats'])
                if result['risk_level'] in ['low', 'medium']:
                    result['risk_level'] = 'medium'
            
            # Store scan details
            result['scan_details'] = {
                'mime_type': mime_type,
                'file_size': len(file_content),
                'patterns_checked': len(self.suspicious_patterns),
                'header_analysis': header_check.get('details', {}),
                'content_analysis': pattern_check.get('details', {})
            }
            
        except Exception as e:
            current_app.logger.error(f'Security scan error: {e}')
            result.update({
                'safe': False,
                'threats_detected': [f'Scan error: {str(e)}'],
                'risk_level': 'critical'
            })
        
        return result
    
    def _detect_mime_type(self, file_content):
        """Detect MIME type from file content"""
        try:
            return self.magic.from_buffer(file_content)
        except Exception:
            return 'application/octet-stream'
    
    def _check_mime_type(self, mime_type):
        """Check if MIME type is safe"""
        result = {
            'safe': True,
            'threats': []
        }
        
        if mime_type in self.blocked_mime_types:
            result['safe'] = False
            result['threats'].append(f'Blocked MIME type: {mime_type}')
        
        # Additional MIME type checks
        if mime_type.startswith('application/x-'):
            # Many application/x- types are potentially dangerous
            if any(dangerous in mime_type for dangerous in ['executable', 'script', 'shellscript']):
                result['safe'] = False
                result['threats'].append(f'Potentially dangerous MIME type: {mime_type}')
        
        return result
    
    def _check_file_extension(self, filename):
        """Check if file extension is safe"""
        result = {
            'safe': True,
            'threats': []
        }
        
        # Get file extension
        extension = os.path.splitext(filename)[1].lower().lstrip('.')
        
        if extension in self.dangerous_extensions:
            result['safe'] = False
            result['threats'].append(f'Dangerous file extension: .{extension}')
        
        # Check for double extensions (e.g., file.jpg.exe)
        parts = filename.split('.')
        if len(parts) > 2:
            for part in parts[1:-1]:  # Check all but first and last part
                if part.lower() in self.dangerous_extensions:
                    result['safe'] = False
                    result['threats'].append(f'Hidden dangerous extension: .{part}')
        
        return result
    
    def _check_suspicious_patterns(self, file_content):
        """Check for suspicious patterns in file content"""
        result = {
            'safe': True,
            'threats': [],
            'details': {
                'patterns_found': []
            }
        }
        
        # Convert to lowercase for case-insensitive matching
        content_lower = file_content.lower()
        
        for pattern in self.suspicious_patterns:
            if pattern in content_lower:
                result['safe'] = False
                pattern_str = pattern.decode('utf-8', errors='ignore')
                result['threats'].append(f'Suspicious pattern found: {pattern_str}')
                result['details']['patterns_found'].append(pattern_str)
        
        # Check for URL patterns that might be malicious
        url_patterns = [
            rb'http://[^\s]+\.exe',
            rb'https://[^\s]+\.exe',
            rb'ftp://[^\s]+\.exe',
            rb'javascript:[^\s]+',
            rb'data:[^;]+;base64,'
        ]
        
        for pattern in url_patterns:
            if re.search(pattern, content_lower):
                result['safe'] = False
                result['threats'].append(f'Suspicious URL pattern found')
                result['details']['patterns_found'].append('malicious_url')
        
        return result
    
    def _check_file_headers(self, file_content):
        """Check file headers for known dangerous signatures"""
        result = {
            'safe': True,
            'threats': [],
            'details': {}
        }
        
        if len(file_content) < 4:
            return result
        
        # Check first few bytes for known signatures
        header = file_content[:16]
        
        # PE executable (Windows)
        if header.startswith(b'MZ'):
            result['safe'] = False
            result['threats'].append('Windows executable detected')
            result['details']['file_type'] = 'PE executable'
        
        # ELF executable (Linux)
        elif header.startswith(b'\x7fELF'):
            result['safe'] = False
            result['threats'].append('Linux executable detected')
            result['details']['file_type'] = 'ELF executable'
        
        # Mach-O executable (macOS)
        elif header.startswith(b'\xfe\xed\xfa\xce') or header.startswith(b'\xce\xfa\xed\xfe'):
            result['safe'] = False
            result['threats'].append('macOS executable detected')
            result['details']['file_type'] = 'Mach-O executable'
        
        # Java class file
        elif header.startswith(b'\xca\xfe\xba\xbe'):
            result['safe'] = False
            result['threats'].append('Java class file detected')
            result['details']['file_type'] = 'Java class'
        
        return result
    
    def _check_embedded_content(self, file_content, mime_type):
        """Check for embedded malicious content"""
        result = {
            'safe': True,
            'threats': []
        }
        
        # For images, check for embedded scripts or unusual content
        if mime_type.startswith('image/'):
            # Look for script tags in image files
            if b'<script' in file_content.lower():
                result['safe'] = False
                result['threats'].append('Script content found in image file')
            
            # Check for unusual text content in binary image
            text_ratio = self._calculate_text_ratio(file_content)
            if text_ratio > 0.3:  # More than 30% text is suspicious for binary image
                result['safe'] = False
                result['threats'].append('Unusual text content ratio in image')
        
        # For videos, basic checks
        elif mime_type.startswith('video/'):
            # Check for script content
            if any(pattern in file_content.lower() for pattern in [b'<script', b'javascript']):
                result['safe'] = False
                result['threats'].append('Script content found in video file')
        
        return result
    
    def _calculate_text_ratio(self, file_content):
        """Calculate ratio of printable text in file content"""
        if not file_content:
            return 0
        
        printable_chars = sum(1 for byte in file_content if 32 <= byte <= 126)
        return printable_chars / len(file_content)
    
    def is_scanning_enabled(self):
        """Check if security scanning is enabled"""
        return current_app.config.get('SECURITY_SCAN_ENABLED', False)
    
    def get_scan_summary(self, scan_result):
        """Get human-readable scan summary"""
        if scan_result['safe']:
            return "File passed security scan"
        
        threat_count = len(scan_result['threats_detected'])
        risk_level = scan_result['risk_level']
        
        summary = f"Security scan failed: {threat_count} threat(s) detected (Risk: {risk_level})"
        
        if scan_result['threats_detected']:
            summary += f" - {', '.join(scan_result['threats_detected'][:3])}"
            if len(scan_result['threats_detected']) > 3:
                summary += f" and {len(scan_result['threats_detected']) - 3} more"
        
        return summary

# Global security scanner instance
security_scanner = SecurityScanner()

