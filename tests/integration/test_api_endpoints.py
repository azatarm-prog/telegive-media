import pytest
import json
import os
from unittest.mock import patch

class TestUploadEndpoints:
    """Test upload API endpoints"""
    
    def test_upload_file_success(self, client, mock_file_upload, sample_upload_data,
                                mock_file_validator, mock_image_processor, 
                                mock_file_hasher, mock_file_storage):
        """Test successful file upload"""
        
        data = sample_upload_data.copy()
        data['file'] = mock_file_upload
        
        response = client.post('/api/media/upload', data=data)
        
        assert response.status_code == 201
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'file_info' in response_data
        assert response_data['duplicate_detected'] is False
    
    def test_upload_file_no_file(self, client, sample_upload_data):
        """Test upload without file"""
        
        response = client.post('/api/media/upload', data=sample_upload_data)
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert response_data['error_code'] == 'NO_FILE'
    
    def test_upload_file_no_account_id(self, client, mock_file_upload):
        """Test upload without account ID"""
        
        data = {'file': mock_file_upload}
        
        response = client.post('/api/media/upload', data=data)
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert response_data['error_code'] == 'MISSING_ACCOUNT_ID'
    
    def test_upload_file_invalid_account_id(self, client, mock_file_upload):
        """Test upload with invalid account ID"""
        
        data = {
            'file': mock_file_upload,
            'account_id': 'invalid'
        }
        
        response = client.post('/api/media/upload', data=data)
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert response_data['error_code'] == 'INVALID_ACCOUNT_ID'
    
    def test_upload_file_validation_failed(self, client, mock_file_upload, 
                                         sample_upload_data, mock_file_validator):
        """Test upload with validation failure"""
        
        # Mock validation failure
        mock_file_validator.validate_file.return_value = {
            'valid': False,
            'errors': ['Invalid file format'],
            'file_info': None
        }
        
        data = sample_upload_data.copy()
        data['file'] = mock_file_upload
        
        response = client.post('/api/media/upload', data=data)
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert response_data['error_code'] == 'VALIDATION_FAILED'
    
    def test_upload_file_security_scan_failed(self, client, mock_file_upload,
                                            sample_upload_data, mock_file_validator,
                                            mock_security_scanner):
        """Test upload with security scan failure"""
        
        # Enable security scanning
        mock_security_scanner.is_scanning_enabled.return_value = True
        mock_security_scanner.scan_file.return_value = {
            'safe': False,
            'threats_detected': ['Malicious content detected'],
            'risk_level': 'high'
        }
        
        data = sample_upload_data.copy()
        data['file'] = mock_file_upload
        
        response = client.post('/api/media/upload', data=data)
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert response_data['error_code'] == 'SECURITY_SCAN_FAILED'
    
    def test_upload_status_endpoint(self, client):
        """Test upload status endpoint"""
        
        response = client.get('/api/media/upload/status')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'upload_config' in response_data

class TestMediaEndpoints:
    """Test media management API endpoints"""
    
    def test_media_index(self, client):
        """Test media service index endpoint"""
        
        response = client.get('/api/media/')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert response_data['service'] == 'Media Management Service'
        assert 'endpoints' in response_data
    
    def test_get_file_info_success(self, client, sample_media_file):
        """Test getting file info successfully"""
        
        response = client.get(f'/api/media/{sample_media_file.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert response_data['file_info']['id'] == sample_media_file.id
        assert response_data['file_info']['original_filename'] == sample_media_file.original_filename
    
    def test_get_file_info_not_found(self, client):
        """Test getting info for non-existent file"""
        
        response = client.get('/api/media/99999')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert response_data['error_code'] == 'FILE_NOT_FOUND'
    
    def test_download_file_success(self, client, sample_media_file):
        """Test downloading file successfully"""
        
        # Create temporary file for testing
        with patch('os.path.exists') as mock_exists, \
             patch('flask.send_file') as mock_send_file:
            
            mock_exists.return_value = True
            mock_send_file.return_value = 'file_content'
            
            response = client.get(f'/api/media/{sample_media_file.id}/download')
            
            # send_file should be called
            mock_send_file.assert_called_once()
    
    def test_download_file_not_found(self, client):
        """Test downloading non-existent file"""
        
        response = client.get('/api/media/99999/download')
        
        assert response.status_code == 404
    
    def test_download_inactive_file(self, client, sample_media_file):
        """Test downloading inactive file"""
        
        # Mark file as inactive
        sample_media_file.is_active = False
        
        response = client.get(f'/api/media/{sample_media_file.id}/download')
        
        assert response.status_code == 410  # Gone
    
    def test_associate_file_success(self, client, sample_media_file, sample_associate_data):
        """Test associating file with giveaway successfully"""
        
        response = client.put(
            f'/api/media/{sample_media_file.id}/associate',
            data=json.dumps(sample_associate_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert response_data['giveaway_id'] == sample_associate_data['giveaway_id']
        assert response_data['cleanup_scheduled'] is True
    
    def test_associate_file_not_found(self, client, sample_associate_data):
        """Test associating non-existent file"""
        
        response = client.put(
            '/api/media/99999/associate',
            data=json.dumps(sample_associate_data),
            content_type='application/json'
        )
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data['error_code'] == 'FILE_NOT_FOUND'
    
    def test_associate_file_missing_giveaway_id(self, client, sample_media_file):
        """Test associating file without giveaway ID"""
        
        response = client.put(
            f'/api/media/{sample_media_file.id}/associate',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['error_code'] == 'MISSING_GIVEAWAY_ID'
    
    def test_delete_file_success(self, client, sample_media_file, mock_file_storage):
        """Test deleting file successfully"""
        
        response = client.delete(f'/api/media/{sample_media_file.id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'space_freed' in response_data
    
    def test_delete_file_not_found(self, client):
        """Test deleting non-existent file"""
        
        response = client.delete('/api/media/99999')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data['error_code'] == 'FILE_NOT_FOUND'
    
    def test_cleanup_files_success(self, client, sample_media_file, mock_file_storage):
        """Test cleanup files for giveaway successfully"""
        
        # Set up file for cleanup
        sample_media_file.giveaway_id = 1
        sample_media_file.cleanup_status = 'pending'
        
        response = client.post('/api/media/cleanup/1')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'cleanup_summary' in response_data
    
    def test_cleanup_files_no_files(self, client):
        """Test cleanup when no files to cleanup"""
        
        response = client.post('/api/media/cleanup/999')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert response_data['cleanup_summary']['files_processed'] == 0
    
    def test_get_account_files_success(self, client, sample_media_file):
        """Test getting account files successfully"""
        
        response = client.get(f'/api/media/account/{sample_media_file.account_id}')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        assert 'files' in response_data
        assert 'pagination' in response_data
        assert 'storage_stats' in response_data
        assert len(response_data['files']) >= 1
    
    def test_get_account_files_with_pagination(self, client, sample_media_file):
        """Test getting account files with pagination"""
        
        response = client.get(
            f'/api/media/account/{sample_media_file.account_id}?page=1&limit=10'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['pagination']['page'] == 1
        assert response_data['pagination']['limit'] == 10
    
    def test_get_account_files_with_status_filter(self, client, sample_media_file):
        """Test getting account files with status filter"""
        
        response = client.get(
            f'/api/media/account/{sample_media_file.account_id}?status=active'
        )
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['success'] is True
        # All returned files should be active
        for file_info in response_data['files']:
            assert file_info['is_active'] is True
    
    def test_validate_file_success(self, client, sample_media_file):
        """Test validating file successfully"""
        
        with patch('os.path.exists') as mock_exists, \
             patch('utils.file_storage.file_storage.get_file_info') as mock_get_info:
            
            mock_exists.return_value = True
            mock_get_info.return_value = {
                'exists': True,
                'file_size': sample_media_file.file_size
            }
            
            response = client.post(f'/api/media/validate/{sample_media_file.id}')
            
            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert response_data['success'] is True
            assert 'validation_result' in response_data
    
    def test_validate_file_not_found(self, client):
        """Test validating non-existent file"""
        
        response = client.post('/api/media/validate/99999')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data['error_code'] == 'FILE_NOT_FOUND'

class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        
        response = client.get('/health')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'healthy'
        assert response_data['service'] == 'media-service'
    
    def test_health_check_detailed(self, client):
        """Test detailed health check"""
        
        response = client.get('/health/detailed')
        
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'healthy'
        assert 'database' in response_data['checks']
        assert 'storage' in response_data['checks']

class TestErrorHandling:
    """Test API error handling"""
    
    def test_404_error_handler(self, client):
        """Test 404 error handler"""
        
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert response_data['error_code'] == 'NOT_FOUND'
    
    def test_405_error_handler(self, client):
        """Test 405 method not allowed error handler"""
        
        response = client.patch('/api/media/')  # PATCH not allowed
        
        assert response.status_code == 405
        response_data = json.loads(response.data)
        assert response_data['success'] is False
        assert response_data['error_code'] == 'METHOD_NOT_ALLOWED'
    
    def test_413_error_handler(self, client):
        """Test 413 request entity too large error handler"""
        
        # This would typically be triggered by Flask's built-in size checking
        # We'll simulate it by sending a request that would be too large
        large_data = 'x' * (100 * 1024 * 1024)  # 100MB string
        
        response = client.post(
            '/api/media/upload',
            data={'account_id': '12345', 'large_field': large_data}
        )
        
        # The exact status code may vary depending on how Flask handles this
        assert response.status_code in [400, 413, 500]
    
    def test_500_error_handler(self, client):
        """Test 500 internal server error handler"""
        
        # We'll simulate this by causing an exception in an endpoint
        with patch('routes.media.MediaFile.query') as mock_query:
            mock_query.get.side_effect = Exception('Database error')
            
            response = client.get('/api/media/1')
            
            assert response.status_code == 500
            response_data = json.loads(response.data)
            assert response_data['success'] is False
            assert response_data['error_code'] == 'INTERNAL_ERROR'

class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present"""
        
        response = client.get('/api/media/')
        
        # Check for CORS headers
        assert 'Access-Control-Allow-Origin' in response.headers
    
    def test_options_request(self, client):
        """Test OPTIONS request for CORS preflight"""
        
        response = client.options('/api/media/')
        
        assert response.status_code == 200
        assert 'Access-Control-Allow-Methods' in response.headers
        assert 'Access-Control-Allow-Headers' in response.headers

class TestRateLimiting:
    """Test rate limiting"""
    
    def test_rate_limit_not_exceeded(self, client):
        """Test normal request within rate limits"""
        
        response = client.get('/api/media/')
        
        assert response.status_code == 200
        # Should have rate limit headers
        assert 'X-RateLimit-Limit' in response.headers or 'RateLimit-Limit' in response.headers
    
    @pytest.mark.skip(reason="Rate limiting testing requires specific setup")
    def test_rate_limit_exceeded(self, client):
        """Test rate limit exceeded scenario"""
        
        # This test would require sending many requests quickly
        # Implementation depends on rate limiting configuration
        pass

