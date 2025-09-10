import os
import tempfile
import pytest
from unittest.mock import Mock, patch

from app import create_app
from models import db, MediaFile, FileValidationLog, FileCleanupLog

@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Create temporary upload directory
    upload_dir = tempfile.mkdtemp()
    
    app = create_app('testing')
    app.config.update({
        'DATABASE_URL': f'sqlite:///{db_path}',
        'UPLOAD_FOLDER': upload_dir,
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
        'SECURITY_SCAN_ENABLED': False,  # Disable for testing
        'TELEGIVE_AUTH_URL': 'http://test-auth-service',
        'TELEGIVE_GIVEAWAY_URL': 'http://test-giveaway-service'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def db_session(app):
    """Create database session for testing"""
    with app.app_context():
        yield db.session
        db.session.rollback()

@pytest.fixture
def sample_media_file(db_session):
    """Create sample media file for testing"""
    media_file = MediaFile(
        account_id=12345,
        original_filename='test_image.jpg',
        stored_filename='test_image_12345_1234567890.jpg',
        file_path='/tmp/test_image_12345_1234567890.jpg',
        file_size=1024000,
        file_type='image',
        mime_type='image/jpeg',
        file_extension='jpg',
        width=1920,
        height=1080,
        file_hash='abcdef1234567890',
        uploaded_by_ip='127.0.0.1',
        is_validated=True
    )
    
    db_session.add(media_file)
    db_session.commit()
    
    return media_file

@pytest.fixture
def sample_validation_log(db_session, sample_media_file):
    """Create sample validation log for testing"""
    validation_log = FileValidationLog.create_log(
        sample_media_file.id,
        'complete',
        True,
        details={'file_type': 'image', 'mime_type': 'image/jpeg'}
    )
    
    db_session.add(validation_log)
    db_session.commit()
    
    return validation_log

@pytest.fixture
def sample_cleanup_log(db_session, sample_media_file):
    """Create sample cleanup log for testing"""
    cleanup_log = FileCleanupLog.create_log(
        sample_media_file.id,
        'manual',
        True,
        file_size_freed=1024000
    )
    
    db_session.add(cleanup_log)
    db_session.commit()
    
    return cleanup_log

@pytest.fixture
def mock_file_upload():
    """Mock file upload for testing"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    # Create mock image data
    image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
    
    return FileStorage(
        stream=BytesIO(image_data),
        filename='test_image.png',
        content_type='image/png'
    )

@pytest.fixture
def mock_video_upload():
    """Mock video file upload for testing"""
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    # Create mock video data (minimal MP4 header)
    video_data = b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom\x00\x00\x00\x08free'
    
    return FileStorage(
        stream=BytesIO(video_data),
        filename='test_video.mp4',
        content_type='video/mp4'
    )

@pytest.fixture
def auth_headers():
    """Mock authentication headers"""
    return {
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
    }

@pytest.fixture
def service_headers():
    """Mock service authentication headers"""
    return {
        'Authorization': 'Bearer test-service-token',
        'X-Service-Name': 'test-service',
        'Content-Type': 'application/json'
    }

@pytest.fixture
def mock_auth_service():
    """Mock authentication service"""
    with patch('services.auth_service.auth_service') as mock:
        mock.validate_user_token.return_value = {
            'valid': True,
            'user_id': 123,
            'account_id': 12345,
            'permissions': ['media_upload', 'media_manage']
        }
        mock.validate_service_token.return_value = {
            'valid': True,
            'service_name': 'test-service',
            'permissions': ['media_management']
        }
        yield mock

@pytest.fixture
def mock_telegive_service():
    """Mock telegive service"""
    with patch('services.telegive_service.telegive_service') as mock:
        mock.notify_file_uploaded.return_value = {'success': True}
        mock.notify_file_deleted.return_value = {'success': True}
        mock.get_giveaway_info.return_value = {
            'success': True,
            'giveaway_info': {'id': 1, 'title': 'Test Giveaway'}
        }
        mock.validate_account_access.return_value = {
            'valid': True,
            'permissions': ['media_upload']
        }
        yield mock

@pytest.fixture
def mock_file_storage():
    """Mock file storage operations"""
    with patch('utils.file_storage.file_storage') as mock:
        mock.save_file_content.return_value = {
            'success': True,
            'stored_filename': 'test_file_12345_1234567890.jpg',
            'file_path': '/tmp/test_file_12345_1234567890.jpg'
        }
        mock.delete_file.return_value = {
            'success': True,
            'file_size_freed': 1024000
        }
        mock.get_file_info.return_value = {
            'exists': True,
            'file_size': 1024000,
            'mime_type': 'image/jpeg'
        }
        yield mock

@pytest.fixture
def mock_security_scanner():
    """Mock security scanner"""
    with patch('utils.security_scanner.security_scanner') as mock:
        mock.is_scanning_enabled.return_value = False
        mock.scan_file.return_value = {
            'safe': True,
            'threats_detected': [],
            'risk_level': 'low'
        }
        yield mock

@pytest.fixture
def mock_file_validator():
    """Mock file validator"""
    with patch('utils.file_validator.file_validator') as mock:
        mock.validate_file.return_value = {
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
        yield mock

@pytest.fixture
def mock_image_processor():
    """Mock image processor"""
    with patch('utils.image_processor.image_processor') as mock:
        mock.extract_metadata.return_value = {
            'width': 1920,
            'height': 1080,
            'format': 'JPEG'
        }
        mock.validate_image_content.return_value = {
            'valid': True,
            'width': 1920,
            'height': 1080,
            'format': 'JPEG'
        }
        yield mock

@pytest.fixture
def mock_video_processor():
    """Mock video processor"""
    with patch('utils.video_processor.video_processor') as mock:
        mock.extract_metadata.return_value = {
            'width': 1920,
            'height': 1080,
            'duration': 30.5,
            'format': 'MP4'
        }
        mock.validate_video_content.return_value = {
            'valid': True,
            'width': 1920,
            'height': 1080,
            'duration': 30.5,
            'format': 'MP4'
        }
        yield mock

@pytest.fixture
def mock_file_hasher():
    """Mock file hasher"""
    with patch('utils.file_hasher.file_hasher') as mock:
        mock.calculate_hash.return_value = 'abcdef1234567890'
        yield mock

# Test data fixtures
@pytest.fixture
def sample_upload_data():
    """Sample upload form data"""
    return {
        'account_id': '12345'
    }

@pytest.fixture
def sample_associate_data():
    """Sample file association data"""
    return {
        'giveaway_id': 1
    }

# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Cleanup test files after each test"""
    yield
    # Cleanup logic can be added here if needed
    pass

