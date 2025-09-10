import pytest
from datetime import datetime, timedelta

from models import MediaFile, FileValidationLog, FileCleanupLog

class TestMediaFile:
    """Test MediaFile model"""
    
    def test_create_media_file(self, db_session):
        """Test creating a media file"""
        media_file = MediaFile(
            account_id=12345,
            original_filename='test.jpg',
            stored_filename='test_12345_1234567890.jpg',
            file_path='/tmp/test_12345_1234567890.jpg',
            file_size=1024000,
            file_type='image',
            mime_type='image/jpeg',
            file_extension='jpg',
            file_hash='abcdef1234567890',
            uploaded_by_ip='127.0.0.1'
        )
        
        db_session.add(media_file)
        db_session.commit()
        
        assert media_file.id is not None
        assert media_file.account_id == 12345
        assert media_file.original_filename == 'test.jpg'
        assert media_file.is_active is True
        assert media_file.is_validated is False
        assert media_file.cleanup_status == 'pending'
        assert media_file.uploaded_at is not None
    
    def test_media_file_to_dict(self, sample_media_file):
        """Test MediaFile to_dict method"""
        data = sample_media_file.to_dict()
        
        assert data['id'] == sample_media_file.id
        assert data['account_id'] == sample_media_file.account_id
        assert data['original_filename'] == sample_media_file.original_filename
        assert data['file_size'] == sample_media_file.file_size
        assert data['file_type'] == sample_media_file.file_type
        assert data['is_active'] == sample_media_file.is_active
        assert 'uploaded_at' in data
    
    def test_mark_for_cleanup(self, sample_media_file):
        """Test marking file for cleanup"""
        delay_minutes = 5
        sample_media_file.mark_for_cleanup(delay_minutes)
        
        assert sample_media_file.cleanup_status == 'pending'
        assert sample_media_file.cleanup_scheduled_at is not None
        
        # Check that cleanup is scheduled for the future
        expected_time = datetime.utcnow() + timedelta(minutes=delay_minutes)
        time_diff = abs((sample_media_file.cleanup_scheduled_at - expected_time).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance
    
    def test_mark_cleanup_completed(self, sample_media_file):
        """Test marking cleanup as completed"""
        sample_media_file.mark_cleanup_completed()
        
        assert sample_media_file.is_active is False
        assert sample_media_file.cleanup_status == 'published_and_removed'
        assert sample_media_file.cleanup_completed_at is not None
    
    def test_get_file_url(self, sample_media_file):
        """Test getting file URL"""
        url = sample_media_file.get_file_url()
        expected_url = f'/api/media/{sample_media_file.id}/download'
        assert url == expected_url
    
    def test_get_file_url_with_base(self, sample_media_file):
        """Test getting file URL with base URL"""
        base_url = 'https://example.com'
        url = sample_media_file.get_file_url(base_url)
        expected_url = f'{base_url}/api/media/{sample_media_file.id}/download'
        assert url == expected_url

class TestFileValidationLog:
    """Test FileValidationLog model"""
    
    def test_create_validation_log(self, db_session, sample_media_file):
        """Test creating validation log"""
        log = FileValidationLog.create_log(
            sample_media_file.id,
            'format_check',
            True,
            details={'format': 'JPEG', 'size': '1920x1080'}
        )
        
        db_session.add(log)
        db_session.commit()
        
        assert log.id is not None
        assert log.file_id == sample_media_file.id
        assert log.validation_type == 'format_check'
        assert log.validation_passed is True
        assert log.details == {'format': 'JPEG', 'size': '1920x1080'}
        assert log.validated_at is not None
    
    def test_create_validation_log_with_error(self, db_session, sample_media_file):
        """Test creating validation log with error"""
        error_message = 'Invalid file format'
        log = FileValidationLog.create_log(
            sample_media_file.id,
            'format_check',
            False,
            error_message=error_message
        )
        
        db_session.add(log)
        db_session.commit()
        
        assert log.validation_passed is False
        assert log.error_message == error_message
    
    def test_validation_log_to_dict(self, sample_validation_log):
        """Test ValidationLog to_dict method"""
        data = sample_validation_log.to_dict()
        
        assert data['id'] == sample_validation_log.id
        assert data['file_id'] == sample_validation_log.file_id
        assert data['validation_type'] == sample_validation_log.validation_type
        assert data['validation_passed'] == sample_validation_log.validation_passed
        assert 'validated_at' in data

class TestFileCleanupLog:
    """Test FileCleanupLog model"""
    
    def test_create_cleanup_log(self, db_session, sample_media_file):
        """Test creating cleanup log"""
        log = FileCleanupLog.create_log(
            sample_media_file.id,
            'manual',
            True,
            file_size_freed=1024000
        )
        
        db_session.add(log)
        db_session.commit()
        
        assert log.id is not None
        assert log.file_id == sample_media_file.id
        assert log.cleanup_trigger == 'manual'
        assert log.cleanup_successful is True
        assert log.file_size_freed == 1024000
        assert log.cleanup_timestamp is not None
    
    def test_create_cleanup_log_with_error(self, db_session, sample_media_file):
        """Test creating cleanup log with error"""
        error_message = 'File not found'
        log = FileCleanupLog.create_log(
            sample_media_file.id,
            'scheduled',
            False,
            error_message=error_message
        )
        
        db_session.add(log)
        db_session.commit()
        
        assert log.cleanup_successful is False
        assert log.error_message == error_message
        assert log.file_size_freed is None
    
    def test_cleanup_log_to_dict(self, sample_cleanup_log):
        """Test CleanupLog to_dict method"""
        data = sample_cleanup_log.to_dict()
        
        assert data['id'] == sample_cleanup_log.id
        assert data['file_id'] == sample_cleanup_log.file_id
        assert data['cleanup_trigger'] == sample_cleanup_log.cleanup_trigger
        assert data['cleanup_successful'] == sample_cleanup_log.cleanup_successful
        assert 'cleanup_timestamp' in data

class TestModelRelationships:
    """Test model relationships"""
    
    def test_media_file_validation_logs_relationship(self, db_session, sample_media_file):
        """Test MediaFile -> ValidationLog relationship"""
        # Create validation logs
        log1 = FileValidationLog.create_log(sample_media_file.id, 'format', True)
        log2 = FileValidationLog.create_log(sample_media_file.id, 'security', True)
        
        db_session.add_all([log1, log2])
        db_session.commit()
        
        # Test relationship
        validation_logs = sample_media_file.validation_logs
        assert len(validation_logs) == 2
        assert log1 in validation_logs
        assert log2 in validation_logs
    
    def test_media_file_cleanup_logs_relationship(self, db_session, sample_media_file):
        """Test MediaFile -> CleanupLog relationship"""
        # Create cleanup logs
        log1 = FileCleanupLog.create_log(sample_media_file.id, 'manual', True)
        log2 = FileCleanupLog.create_log(sample_media_file.id, 'scheduled', False)
        
        db_session.add_all([log1, log2])
        db_session.commit()
        
        # Test relationship
        cleanup_logs = sample_media_file.cleanup_logs
        assert len(cleanup_logs) == 2
        assert log1 in cleanup_logs
        assert log2 in cleanup_logs

class TestModelValidation:
    """Test model validation and constraints"""
    
    def test_media_file_required_fields(self, db_session):
        """Test MediaFile required fields"""
        # Missing required fields should raise an error
        media_file = MediaFile()
        
        db_session.add(media_file)
        
        with pytest.raises(Exception):  # Should raise IntegrityError or similar
            db_session.commit()
    
    def test_file_hash_uniqueness_per_account(self, db_session):
        """Test file hash uniqueness constraint per account"""
        # Create first file
        file1 = MediaFile(
            account_id=12345,
            original_filename='test1.jpg',
            stored_filename='test1_12345_1.jpg',
            file_path='/tmp/test1.jpg',
            file_size=1024,
            file_type='image',
            mime_type='image/jpeg',
            file_extension='jpg',
            file_hash='same_hash',
            uploaded_by_ip='127.0.0.1'
        )
        
        # Create second file with same hash and account
        file2 = MediaFile(
            account_id=12345,
            original_filename='test2.jpg',
            stored_filename='test2_12345_2.jpg',
            file_path='/tmp/test2.jpg',
            file_size=1024,
            file_type='image',
            mime_type='image/jpeg',
            file_extension='jpg',
            file_hash='same_hash',
            uploaded_by_ip='127.0.0.1'
        )
        
        db_session.add(file1)
        db_session.commit()
        
        db_session.add(file2)
        
        # This should work since we allow duplicates for deduplication logic
        db_session.commit()
        
        # Both files should exist
        assert MediaFile.query.filter_by(file_hash='same_hash').count() == 2
    
    def test_different_accounts_same_hash(self, db_session):
        """Test same hash for different accounts is allowed"""
        # Create files with same hash but different accounts
        file1 = MediaFile(
            account_id=12345,
            original_filename='test.jpg',
            stored_filename='test_12345.jpg',
            file_path='/tmp/test_12345.jpg',
            file_size=1024,
            file_type='image',
            mime_type='image/jpeg',
            file_extension='jpg',
            file_hash='same_hash',
            uploaded_by_ip='127.0.0.1'
        )
        
        file2 = MediaFile(
            account_id=67890,
            original_filename='test.jpg',
            stored_filename='test_67890.jpg',
            file_path='/tmp/test_67890.jpg',
            file_size=1024,
            file_type='image',
            mime_type='image/jpeg',
            file_extension='jpg',
            file_hash='same_hash',
            uploaded_by_ip='127.0.0.1'
        )
        
        db_session.add_all([file1, file2])
        db_session.commit()
        
        # Both files should exist
        assert MediaFile.query.filter_by(file_hash='same_hash').count() == 2

