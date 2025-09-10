import pytest
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
from io import BytesIO

from utils import (
    file_validator, image_processor, video_processor,
    file_hasher, file_storage, security_scanner
)

class TestFileValidator:
    """Test FileValidator utility"""
    
    def test_validate_valid_image(self, mock_file_upload):
        """Test validating a valid image file"""
        with patch('utils.file_validator.magic.Magic') as mock_magic:
            mock_magic.return_value.from_buffer.return_value = 'image/png'
            
            result = file_validator.validate_file(mock_file_upload)
            
            assert result['valid'] is True
            assert result['file_info']['file_type'] == 'image'
            assert result['file_info']['mime_type'] == 'image/png'
            assert len(result['errors']) == 0
    
    def test_validate_invalid_extension(self):
        """Test validating file with invalid extension"""
        from werkzeug.datastructures import FileStorage
        from io import BytesIO
        
        invalid_file = FileStorage(
            stream=BytesIO(b'test content'),
            filename='test.exe',
            content_type='application/octet-stream'
        )
        
        result = file_validator.validate_file(invalid_file)
        
        assert result['valid'] is False
        assert 'Invalid file extension' in str(result['errors'])
    
    def test_validate_file_too_large(self):
        """Test validating file that's too large"""
        from werkzeug.datastructures import FileStorage
        from io import BytesIO
        
        # Create large file content
        large_content = b'x' * (100 * 1024 * 1024)  # 100MB
        
        large_file = FileStorage(
            stream=BytesIO(large_content),
            filename='large.jpg',
            content_type='image/jpeg'
        )
        
        with patch('utils.file_validator.current_app') as mock_app:
            mock_app.config.get.side_effect = lambda key, default=None: {
                'MAX_IMAGE_SIZE': 10 * 1024 * 1024,  # 10MB limit
                'MAX_VIDEO_SIZE': 50 * 1024 * 1024
            }.get(key, default)
            
            result = file_validator.validate_file(large_file)
            
            assert result['valid'] is False
            assert 'File too large' in str(result['errors'])
    
    def test_get_file_type_from_mime(self):
        """Test getting file type from MIME type"""
        assert file_validator._get_file_type_from_mime('image/jpeg') == 'image'
        assert file_validator._get_file_type_from_mime('video/mp4') == 'video'
        assert file_validator._get_file_type_from_mime('text/plain') == 'other'

class TestImageProcessor:
    """Test ImageProcessor utility"""
    
    @patch('utils.image_processor.Image.open')
    def test_extract_metadata_success(self, mock_image_open):
        """Test successful metadata extraction"""
        # Mock PIL Image
        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.format = 'JPEG'
        mock_image._getexif.return_value = {
            'DateTime': '2023:01:01 12:00:00',
            'Make': 'Canon'
        }
        mock_image_open.return_value = mock_image
        
        file_content = b'fake image content'
        result = image_processor.extract_metadata(file_content)
        
        assert result['width'] == 1920
        assert result['height'] == 1080
        assert result['format'] == 'JPEG'
        assert 'exif' in result
    
    @patch('utils.image_processor.Image.open')
    def test_extract_metadata_failure(self, mock_image_open):
        """Test metadata extraction failure"""
        mock_image_open.side_effect = Exception('Invalid image')
        
        file_content = b'invalid content'
        result = image_processor.extract_metadata(file_content)
        
        assert result['width'] is None
        assert result['height'] is None
        assert result['error'] is not None
    
    @patch('utils.image_processor.Image.open')
    def test_validate_image_content_valid(self, mock_image_open):
        """Test validating valid image content"""
        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.format = 'JPEG'
        mock_image_open.return_value = mock_image
        
        file_content = b'valid image content'
        result = image_processor.validate_image_content(file_content)
        
        assert result['valid'] is True
        assert result['width'] == 1920
        assert result['height'] == 1080
    
    @patch('utils.image_processor.Image.open')
    def test_validate_image_content_invalid(self, mock_image_open):
        """Test validating invalid image content"""
        mock_image_open.side_effect = Exception('Corrupted image')
        
        file_content = b'invalid content'
        result = image_processor.validate_image_content(file_content)
        
        assert result['valid'] is False
        assert result['error'] is not None

class TestVideoProcessor:
    """Test VideoProcessor utility"""
    
    def test_extract_metadata_no_ffprobe(self):
        """Test metadata extraction when ffprobe is not available"""
        with patch('utils.video_processor.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError('ffprobe not found')
            
            file_content = b'video content'
            result = video_processor.extract_metadata(file_content)
            
            assert result['width'] is None
            assert result['height'] is None
            assert result['duration'] is None
            assert 'ffprobe not available' in result['error']
    
    def test_validate_video_content_basic(self):
        """Test basic video content validation"""
        # Test with MP4 header
        mp4_header = b'\x00\x00\x00\x20ftypmp42'
        result = video_processor.validate_video_content(mp4_header)
        
        # Should pass basic validation even without ffprobe
        assert result['valid'] is True
    
    def test_validate_video_content_invalid(self):
        """Test invalid video content validation"""
        invalid_content = b'not a video file'
        result = video_processor.validate_video_content(invalid_content)
        
        assert result['valid'] is False

class TestFileHasher:
    """Test FileHasher utility"""
    
    def test_calculate_hash_from_content(self):
        """Test calculating hash from file content"""
        content = b'test file content'
        hash_value = file_hasher.calculate_hash(content)
        
        assert hash_value is not None
        assert len(hash_value) == 64  # SHA-256 hex length
        assert isinstance(hash_value, str)
    
    def test_calculate_hash_from_file_path(self):
        """Test calculating hash from file path"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test file content')
            temp_file_path = temp_file.name
        
        try:
            hash_value = file_hasher.calculate_hash(temp_file_path)
            
            assert hash_value is not None
            assert len(hash_value) == 64
        finally:
            os.unlink(temp_file_path)
    
    def test_calculate_hash_consistency(self):
        """Test hash calculation consistency"""
        content = b'consistent content'
        
        hash1 = file_hasher.calculate_hash(content)
        hash2 = file_hasher.calculate_hash(content)
        
        assert hash1 == hash2
    
    def test_calculate_hash_different_content(self):
        """Test different content produces different hashes"""
        content1 = b'content one'
        content2 = b'content two'
        
        hash1 = file_hasher.calculate_hash(content1)
        hash2 = file_hasher.calculate_hash(content2)
        
        assert hash1 != hash2

class TestFileStorage:
    """Test FileStorage utility"""
    
    @patch('utils.file_storage.os.makedirs')
    @patch('utils.file_storage.open', new_callable=mock_open)
    def test_save_file_content_success(self, mock_file_open, mock_makedirs):
        """Test successful file content saving"""
        with patch('utils.file_storage.current_app') as mock_app:
            mock_app.config.get.return_value = '/tmp/uploads'
            
            content = b'test file content'
            filename = 'test.jpg'
            account_id = 12345
            
            result = file_storage.save_file_content(content, filename, account_id)
            
            assert result['success'] is True
            assert 'stored_filename' in result
            assert 'file_path' in result
            mock_file_open.assert_called_once()
    
    @patch('utils.file_storage.os.makedirs')
    @patch('utils.file_storage.open')
    def test_save_file_content_failure(self, mock_file_open, mock_makedirs):
        """Test file content saving failure"""
        mock_file_open.side_effect = IOError('Disk full')
        
        with patch('utils.file_storage.current_app') as mock_app:
            mock_app.config.get.return_value = '/tmp/uploads'
            
            content = b'test content'
            filename = 'test.jpg'
            account_id = 12345
            
            result = file_storage.save_file_content(content, filename, account_id)
            
            assert result['success'] is False
            assert 'error' in result
    
    @patch('utils.file_storage.os.path.exists')
    @patch('utils.file_storage.os.remove')
    @patch('utils.file_storage.os.path.getsize')
    def test_delete_file_success(self, mock_getsize, mock_remove, mock_exists):
        """Test successful file deletion"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024
        
        file_path = '/tmp/test_file.jpg'
        result = file_storage.delete_file(file_path)
        
        assert result['success'] is True
        assert result['file_size_freed'] == 1024
        mock_remove.assert_called_once_with(file_path)
    
    @patch('utils.file_storage.os.path.exists')
    def test_delete_file_not_exists(self, mock_exists):
        """Test deleting non-existent file"""
        mock_exists.return_value = False
        
        file_path = '/tmp/nonexistent.jpg'
        result = file_storage.delete_file(file_path)
        
        assert result['success'] is False
        assert 'not found' in result['error']
    
    def test_generate_stored_filename(self):
        """Test stored filename generation"""
        filename = 'test image.jpg'
        account_id = 12345
        
        stored_filename = file_storage._generate_stored_filename(filename, account_id)
        
        assert stored_filename.startswith('test_image_12345_')
        assert stored_filename.endswith('.jpg')
        assert len(stored_filename.split('_')) >= 4  # name_account_timestamp.ext

class TestSecurityScanner:
    """Test SecurityScanner utility"""
    
    def test_scan_safe_file(self):
        """Test scanning a safe file"""
        safe_content = b'This is safe image content'
        filename = 'safe_image.jpg'
        mime_type = 'image/jpeg'
        
        result = security_scanner.scan_file(safe_content, filename, mime_type)
        
        assert result['safe'] is True
        assert len(result['threats_detected']) == 0
        assert result['risk_level'] == 'low'
    
    def test_scan_dangerous_extension(self):
        """Test scanning file with dangerous extension"""
        content = b'executable content'
        filename = 'malware.exe'
        mime_type = 'application/x-executable'
        
        result = security_scanner.scan_file(content, filename, mime_type)
        
        assert result['safe'] is False
        assert len(result['threats_detected']) > 0
        assert result['risk_level'] in ['medium', 'high', 'critical']
    
    def test_scan_suspicious_patterns(self):
        """Test scanning content with suspicious patterns"""
        malicious_content = b'<script>alert("xss")</script>'
        filename = 'image.jpg'
        mime_type = 'image/jpeg'
        
        result = security_scanner.scan_file(malicious_content, filename, mime_type)
        
        assert result['safe'] is False
        assert any('script' in threat.lower() for threat in result['threats_detected'])
    
    def test_scan_executable_header(self):
        """Test scanning content with executable headers"""
        # PE executable header
        pe_content = b'MZ\x90\x00\x03\x00\x00\x00'
        filename = 'fake_image.jpg'
        mime_type = 'image/jpeg'
        
        result = security_scanner.scan_file(pe_content, filename, mime_type)
        
        assert result['safe'] is False
        assert any('executable' in threat.lower() for threat in result['threats_detected'])
    
    def test_is_scanning_enabled(self):
        """Test checking if scanning is enabled"""
        with patch('utils.security_scanner.current_app') as mock_app:
            mock_app.config.get.return_value = True
            
            assert security_scanner.is_scanning_enabled() is True
            
            mock_app.config.get.return_value = False
            
            assert security_scanner.is_scanning_enabled() is False
    
    def test_get_scan_summary_safe(self):
        """Test getting summary for safe scan"""
        safe_result = {
            'safe': True,
            'threats_detected': [],
            'risk_level': 'low'
        }
        
        summary = security_scanner.get_scan_summary(safe_result)
        
        assert 'passed' in summary.lower()
    
    def test_get_scan_summary_threats(self):
        """Test getting summary for scan with threats"""
        threat_result = {
            'safe': False,
            'threats_detected': ['Dangerous extension: .exe', 'Script content found'],
            'risk_level': 'high'
        }
        
        summary = security_scanner.get_scan_summary(threat_result)
        
        assert 'failed' in summary.lower()
        assert 'high' in summary.lower()
        assert '2 threat' in summary.lower()

class TestUtilityIntegration:
    """Test utility integration scenarios"""
    
    def test_complete_file_processing_pipeline(self, mock_file_upload):
        """Test complete file processing pipeline"""
        with patch('utils.file_validator.magic.Magic') as mock_magic, \
             patch('utils.image_processor.Image.open') as mock_image, \
             patch('utils.file_storage.open', mock_open()) as mock_file, \
             patch('utils.file_storage.os.makedirs'), \
             patch('utils.file_storage.current_app') as mock_app:
            
            # Setup mocks
            mock_magic.return_value.from_buffer.return_value = 'image/png'
            mock_image.return_value.size = (1920, 1080)
            mock_image.return_value.format = 'PNG'
            mock_app.config.get.return_value = '/tmp/uploads'
            
            # Validate file
            validation_result = file_validator.validate_file(mock_file_upload)
            assert validation_result['valid'] is True
            
            # Extract metadata
            file_content = mock_file_upload.read()
            metadata = image_processor.extract_metadata(file_content)
            assert metadata['width'] == 1920
            assert metadata['height'] == 1080
            
            # Calculate hash
            file_hash = file_hasher.calculate_hash(file_content)
            assert file_hash is not None
            
            # Save file
            storage_result = file_storage.save_file_content(
                file_content, 
                mock_file_upload.filename, 
                12345
            )
            assert storage_result['success'] is True
    
    def test_error_handling_in_pipeline(self):
        """Test error handling in processing pipeline"""
        from werkzeug.datastructures import FileStorage
        from io import BytesIO
        
        # Create invalid file
        invalid_file = FileStorage(
            stream=BytesIO(b'invalid content'),
            filename='test.exe',
            content_type='application/octet-stream'
        )
        
        # Validation should fail
        validation_result = file_validator.validate_file(invalid_file)
        assert validation_result['valid'] is False
        
        # Should not proceed with invalid file
        assert len(validation_result['errors']) > 0

