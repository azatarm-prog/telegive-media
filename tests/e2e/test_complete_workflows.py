import pytest
import json
import time
from unittest.mock import patch

class TestCompleteUploadWorkflow:
    """Test complete file upload workflow"""
    
    def test_complete_image_upload_workflow(self, client, mock_file_upload, 
                                          sample_upload_data, mock_file_validator,
                                          mock_image_processor, mock_file_hasher,
                                          mock_file_storage, mock_security_scanner):
        """Test complete image upload workflow from start to finish"""
        
        # Step 1: Check upload status/configuration
        status_response = client.get('/api/media/upload/status')
        assert status_response.status_code == 200
        
        # Step 2: Upload file
        data = sample_upload_data.copy()
        data['file'] = mock_file_upload
        
        upload_response = client.post('/api/media/upload', data=data)
        assert upload_response.status_code == 201
        
        upload_data = json.loads(upload_response.data)
        assert upload_data['success'] is True
        file_id = upload_data['file_info']['id']
        
        # Step 3: Verify file info can be retrieved
        info_response = client.get(f'/api/media/{file_id}')
        assert info_response.status_code == 200
        
        info_data = json.loads(info_response.data)
        assert info_data['file_info']['id'] == file_id
        assert info_data['file_info']['is_validated'] is True
        
        # Step 4: Download file
        with patch('os.path.exists') as mock_exists, \
             patch('flask.send_file') as mock_send_file:
            
            mock_exists.return_value = True
            mock_send_file.return_value = 'file_content'
            
            download_response = client.get(f'/api/media/{file_id}/download')
            mock_send_file.assert_called_once()
        
        # Step 5: Associate with giveaway
        associate_data = {'giveaway_id': 1}
        associate_response = client.put(
            f'/api/media/{file_id}/associate',
            data=json.dumps(associate_data),
            content_type='application/json'
        )
        assert associate_response.status_code == 200
        
        # Step 6: Verify file is scheduled for cleanup
        info_response = client.get(f'/api/media/{file_id}')
        info_data = json.loads(info_response.data)
        assert info_data['file_info']['cleanup_status'] == 'pending'
    
    def test_complete_video_upload_workflow(self, client, mock_video_upload,
                                          sample_upload_data, mock_file_validator,
                                          mock_video_processor, mock_file_hasher,
                                          mock_file_storage):
        """Test complete video upload workflow"""
        
        # Configure mocks for video
        mock_file_validator.validate_file.return_value = {
            'valid': True,
            'file_info': {
                'filename': 'test_video.mp4',
                'file_size': 2048000,
                'file_type': 'video',
                'mime_type': 'video/mp4',
                'file_extension': 'mp4'
            },
            'errors': []
        }
        
        # Upload video file
        data = sample_upload_data.copy()
        data['file'] = mock_video_upload
        
        upload_response = client.post('/api/media/upload', data=data)
        assert upload_response.status_code == 201
        
        upload_data = json.loads(upload_response.data)
        file_info = upload_data['file_info']
        
        # Verify video-specific metadata
        assert file_info['file_type'] == 'video'
        assert file_info['mime_type'] == 'video/mp4'
        assert file_info['duration'] == 30.5  # From mock
    
    def test_duplicate_file_handling_workflow(self, client, mock_file_upload,
                                            sample_upload_data, mock_file_validator,
                                            mock_image_processor, mock_file_hasher,
                                            mock_file_storage, db_session):
        """Test duplicate file handling workflow"""
        
        # First upload
        data = sample_upload_data.copy()
        data['file'] = mock_file_upload
        
        first_response = client.post('/api/media/upload', data=data)
        assert first_response.status_code == 201
        
        first_data = json.loads(first_response.data)
        first_file_id = first_data['file_info']['id']
        
        # Reset file stream for second upload
        mock_file_upload.stream.seek(0)
        
        # Second upload with same content (same hash)
        second_response = client.post('/api/media/upload', data=data)
        assert second_response.status_code == 200  # 200 for duplicate
        
        second_data = json.loads(second_response.data)
        assert second_data['duplicate_detected'] is True
        assert second_data['existing_file_id'] == first_file_id

class TestCompleteCleanupWorkflow:
    """Test complete cleanup workflow"""
    
    def test_giveaway_cleanup_workflow(self, client, sample_media_file, 
                                     mock_file_storage, db_session):
        """Test complete giveaway cleanup workflow"""
        
        # Step 1: Associate file with giveaway
        giveaway_id = 1
        sample_media_file.giveaway_id = giveaway_id
        sample_media_file.cleanup_status = 'pending'
        db_session.commit()
        
        # Step 2: Trigger cleanup for giveaway
        cleanup_response = client.post(f'/api/media/cleanup/{giveaway_id}')
        assert cleanup_response.status_code == 200
        
        cleanup_data = json.loads(cleanup_response.data)
        assert cleanup_data['success'] is True
        assert cleanup_data['cleanup_summary']['files_processed'] >= 1
        
        # Step 3: Verify file is marked as cleaned up
        info_response = client.get(f'/api/media/{sample_media_file.id}')
        info_data = json.loads(info_response.data)
        assert info_data['file_info']['is_active'] is False
        assert info_data['file_info']['cleanup_status'] == 'published_and_removed'
        
        # Step 4: Verify file download returns 410 Gone
        download_response = client.get(f'/api/media/{sample_media_file.id}/download')
        assert download_response.status_code == 410
    
    def test_manual_file_deletion_workflow(self, client, sample_media_file,
                                         mock_file_storage):
        """Test manual file deletion workflow"""
        
        file_id = sample_media_file.id
        
        # Step 1: Verify file exists and is active
        info_response = client.get(f'/api/media/{file_id}')
        assert info_response.status_code == 200
        
        info_data = json.loads(info_response.data)
        assert info_data['file_info']['is_active'] is True
        
        # Step 2: Delete file manually
        delete_response = client.delete(f'/api/media/{file_id}')
        assert delete_response.status_code == 200
        
        delete_data = json.loads(delete_response.data)
        assert delete_data['success'] is True
        assert 'space_freed' in delete_data
        
        # Step 3: Verify file is marked as inactive
        info_response = client.get(f'/api/media/{file_id}')
        info_data = json.loads(info_response.data)
        assert info_data['file_info']['is_active'] is False
        
        # Step 4: Verify file download returns 410 Gone
        download_response = client.get(f'/api/media/{file_id}/download')
        assert download_response.status_code == 410

class TestAccountManagementWorkflow:
    """Test account management workflow"""
    
    def test_account_files_management_workflow(self, client, mock_file_upload,
                                             sample_upload_data, mock_file_validator,
                                             mock_image_processor, mock_file_hasher,
                                             mock_file_storage):
        """Test complete account files management workflow"""
        
        account_id = 12345
        
        # Step 1: Check initial account files (should be empty)
        files_response = client.get(f'/api/media/account/{account_id}')
        assert files_response.status_code == 200
        
        initial_data = json.loads(files_response.data)
        initial_count = len(initial_data['files'])
        
        # Step 2: Upload multiple files
        file_ids = []
        for i in range(3):
            mock_file_upload.filename = f'test_image_{i}.jpg'
            mock_file_upload.stream.seek(0)
            
            # Use different hash for each file
            mock_file_hasher.calculate_hash.return_value = f'hash_{i}'
            
            data = sample_upload_data.copy()
            data['file'] = mock_file_upload
            
            upload_response = client.post('/api/media/upload', data=data)
            assert upload_response.status_code == 201
            
            upload_data = json.loads(upload_response.data)
            file_ids.append(upload_data['file_info']['id'])
        
        # Step 3: Verify all files appear in account listing
        files_response = client.get(f'/api/media/account/{account_id}')
        files_data = json.loads(files_response.data)
        
        assert len(files_data['files']) == initial_count + 3
        assert files_data['storage_stats']['active_files'] >= 3
        
        # Step 4: Test pagination
        paginated_response = client.get(f'/api/media/account/{account_id}?page=1&limit=2')
        paginated_data = json.loads(paginated_response.data)
        
        assert len(paginated_data['files']) <= 2
        assert paginated_data['pagination']['limit'] == 2
        
        # Step 5: Test status filtering
        active_response = client.get(f'/api/media/account/{account_id}?status=active')
        active_data = json.loads(active_response.data)
        
        for file_info in active_data['files']:
            assert file_info['is_active'] is True
        
        # Step 6: Delete one file and verify inactive filtering
        delete_response = client.delete(f'/api/media/{file_ids[0]}')
        assert delete_response.status_code == 200
        
        inactive_response = client.get(f'/api/media/account/{account_id}?status=inactive')
        inactive_data = json.loads(inactive_response.data)
        
        assert len(inactive_data['files']) >= 1
        for file_info in inactive_data['files']:
            assert file_info['is_active'] is False

class TestErrorRecoveryWorkflows:
    """Test error recovery workflows"""
    
    def test_upload_validation_failure_recovery(self, client, mock_file_upload,
                                               sample_upload_data, mock_file_validator):
        """Test recovery from upload validation failure"""
        
        # Step 1: First upload fails validation
        mock_file_validator.validate_file.return_value = {
            'valid': False,
            'errors': ['Invalid file format'],
            'file_info': None
        }
        
        data = sample_upload_data.copy()
        data['file'] = mock_file_upload
        
        failed_response = client.post('/api/media/upload', data=data)
        assert failed_response.status_code == 400
        
        failed_data = json.loads(failed_response.data)
        assert failed_data['error_code'] == 'VALIDATION_FAILED'
        
        # Step 2: Fix validation and retry
        mock_file_validator.validate_file.return_value = {
            'valid': True,
            'file_info': {
                'filename': 'test_image.jpg',
                'file_size': 1024000,
                'file_type': 'image',
                'mime_type': 'image/jpeg',
                'file_extension': 'jpg'
            },
            'errors': []
        }
        
        # Reset file stream
        mock_file_upload.stream.seek(0)
        
        success_response = client.post('/api/media/upload', data=data)
        assert success_response.status_code == 201
        
        success_data = json.loads(success_response.data)
        assert success_data['success'] is True
    
    def test_storage_failure_recovery(self, client, mock_file_upload,
                                    sample_upload_data, mock_file_validator,
                                    mock_file_storage):
        """Test recovery from storage failure"""
        
        # Step 1: Storage fails
        mock_file_storage.save_file_content.return_value = {
            'success': False,
            'error': 'Disk full'
        }
        
        data = sample_upload_data.copy()
        data['file'] = mock_file_upload
        
        failed_response = client.post('/api/media/upload', data=data)
        assert failed_response.status_code == 500
        
        failed_data = json.loads(failed_response.data)
        assert failed_data['error_code'] == 'STORAGE_FAILED'
        
        # Step 2: Storage recovers
        mock_file_storage.save_file_content.return_value = {
            'success': True,
            'stored_filename': 'test_file_12345_1234567890.jpg',
            'file_path': '/tmp/test_file_12345_1234567890.jpg'
        }
        
        # Reset file stream
        mock_file_upload.stream.seek(0)
        
        success_response = client.post('/api/media/upload', data=data)
        assert success_response.status_code == 201
        
        success_data = json.loads(success_response.data)
        assert success_data['success'] is True

class TestSecurityWorkflows:
    """Test security-related workflows"""
    
    def test_security_scan_workflow(self, client, mock_file_upload,
                                  sample_upload_data, mock_file_validator,
                                  mock_security_scanner):
        """Test security scanning workflow"""
        
        # Step 1: Enable security scanning
        mock_security_scanner.is_scanning_enabled.return_value = True
        
        # Step 2: Upload safe file
        mock_security_scanner.scan_file.return_value = {
            'safe': True,
            'threats_detected': [],
            'risk_level': 'low'
        }
        
        data = sample_upload_data.copy()
        data['file'] = mock_file_upload
        
        safe_response = client.post('/api/media/upload', data=data)
        assert safe_response.status_code == 201
        
        # Step 3: Upload malicious file
        mock_security_scanner.scan_file.return_value = {
            'safe': False,
            'threats_detected': ['Malicious script detected'],
            'risk_level': 'high'
        }
        
        # Reset file stream
        mock_file_upload.stream.seek(0)
        
        malicious_response = client.post('/api/media/upload', data=data)
        assert malicious_response.status_code == 400
        
        malicious_data = json.loads(malicious_response.data)
        assert malicious_data['error_code'] == 'SECURITY_SCAN_FAILED'
        assert 'threats' in malicious_data['details']

class TestPerformanceWorkflows:
    """Test performance-related workflows"""
    
    @pytest.mark.skip(reason="Performance testing requires specific setup")
    def test_concurrent_uploads(self, client):
        """Test concurrent file uploads"""
        # This would test multiple simultaneous uploads
        # Implementation depends on testing framework capabilities
        pass
    
    @pytest.mark.skip(reason="Performance testing requires specific setup")
    def test_large_file_upload(self, client):
        """Test large file upload handling"""
        # This would test uploading files near the size limit
        # Implementation depends on test environment setup
        pass
    
    def test_batch_operations_workflow(self, client, mock_file_storage):
        """Test batch operations workflow"""
        
        # This test simulates batch cleanup operations
        # which would be triggered by scheduled tasks
        
        # Step 1: Create multiple files for cleanup
        giveaway_id = 1
        
        # Step 2: Trigger batch cleanup
        cleanup_response = client.post(f'/api/media/cleanup/{giveaway_id}')
        assert cleanup_response.status_code == 200
        
        cleanup_data = json.loads(cleanup_response.data)
        assert cleanup_data['success'] is True
        
        # Verify cleanup summary contains expected fields
        summary = cleanup_data['cleanup_summary']
        assert 'files_processed' in summary
        assert 'files_deleted' in summary
        assert 'space_freed' in summary
        assert 'errors' in summary

class TestIntegrationWithExternalServices:
    """Test integration with external services"""
    
    def test_service_health_check_workflow(self, client):
        """Test service health check workflow"""
        
        # Step 1: Basic health check
        health_response = client.get('/health')
        assert health_response.status_code == 200
        
        health_data = json.loads(health_response.data)
        assert health_data['status'] == 'healthy'
        
        # Step 2: Detailed health check
        detailed_response = client.get('/health/detailed')
        assert detailed_response.status_code == 200
        
        detailed_data = json.loads(detailed_response.data)
        assert 'checks' in detailed_data
        assert 'database' in detailed_data['checks']
    
    @patch('services.telegive_service.telegive_service')
    def test_giveaway_service_integration_workflow(self, mock_telegive, client,
                                                  sample_media_file):
        """Test integration with giveaway service"""
        
        # Mock giveaway service responses
        mock_telegive.notify_file_uploaded.return_value = {'success': True}
        mock_telegive.notify_file_deleted.return_value = {'success': True}
        
        file_id = sample_media_file.id
        
        # Step 1: Associate file with giveaway (should notify giveaway service)
        associate_data = {'giveaway_id': 1}
        associate_response = client.put(
            f'/api/media/{file_id}/associate',
            data=json.dumps(associate_data),
            content_type='application/json'
        )
        assert associate_response.status_code == 200
        
        # Step 2: Delete file (should notify giveaway service)
        with patch('utils.file_storage.file_storage') as mock_storage:
            mock_storage.delete_file.return_value = {
                'success': True,
                'file_size_freed': 1024000
            }
            
            delete_response = client.delete(f'/api/media/{file_id}')
            assert delete_response.status_code == 200

