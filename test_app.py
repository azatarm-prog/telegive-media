from flask import Flask, jsonify, request, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import hashlib
import magic
import requests
from PIL import Image
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///test.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', '/tmp/uploads')

# Service Configuration
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'https://web-production-ddd7e.up.railway.app')
SERVICE_TOKEN = os.getenv('SERVICE_TOKEN', 'ch4nn3l_s3rv1c3_t0k3n_2025_s3cur3_r4nd0m_str1ng')
SERVICE_TOKEN_HEADER = os.getenv('SERVICE_TOKEN_HEADER', 'X-Service-Token')

# Allowed file types
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Media File model
class MediaFile(db.Model):
    __tablename__ = 'media_files'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'file_hash': self.file_hash,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

def verify_auth_token(token):
    """Verify authentication token with Auth Service"""
    try:
        headers = {SERVICE_TOKEN_HEADER: SERVICE_TOKEN}
        response = requests.post(
            f"{AUTH_SERVICE_URL}/api/auth/verify",
            json={"token": token},
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        return None
        
    except Exception as e:
        print(f"Auth verification error: {e}")
        return None

def require_auth(f):
    """Authentication decorator for protected endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        auth_data = verify_auth_token(token)
        
        if not auth_data or not auth_data.get('valid'):
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        # Add user info to request context
        request.user_id = auth_data.get('user_id')
        request.account_id = auth_data.get('account_id')
        
        return f(*args, **kwargs)
    return decorated_function

def require_service_auth(f):
    """Service-to-service authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        service_token = request.headers.get(SERVICE_TOKEN_HEADER)
        if service_token != SERVICE_TOKEN:
            return jsonify({'success': False, 'error': 'Invalid service token'}), 403
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_hash(file_path):
    """Calculate SHA256 hash of file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def get_file_type(filename):
    """Determine if file is image or video"""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return 'image'
    elif ext in ALLOWED_VIDEO_EXTENSIONS:
        return 'video'
    return 'unknown'

@app.route('/')
def root():
    return jsonify({
        'service': 'Media Management Service',
        'status': 'running',
        'version': '1.0.0',
        'environment': 'production',
        'auth_integration': 'enabled',
        'endpoints': [
            '/',
            '/health',
            '/health/detailed',
            '/api/test',
            '/api/db/init',
            '/api/db/status',
            '/api/upload',
            '/api/files',
            '/api/files/<int:file_id>',
            '/api/files/<int:file_id>/download',
            '/api/files/<int:file_id>/associate'
        ]
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'media-service',
        'version': '1.0.0'
    })

@app.route('/health/detailed')
def detailed_health():
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = {'connected': True}
        
        # Get file count
        try:
            file_count = MediaFile.query.count()
            db_status['total_files'] = file_count
        except Exception:
            db_status['total_files'] = 'unknown'
            
    except Exception as e:
        db_status = {'connected': False, 'error': str(e)}
    
    # Check upload folder
    upload_status = {
        'available': os.path.exists(app.config['UPLOAD_FOLDER']),
        'path': app.config['UPLOAD_FOLDER']
    }
    
    # Test auth service connection
    auth_status = {'connected': False}
    try:
        headers = {SERVICE_TOKEN_HEADER: SERVICE_TOKEN}
        response = requests.get(f"{AUTH_SERVICE_URL}/health", headers=headers, timeout=5)
        auth_status = {'connected': response.status_code == 200, 'url': AUTH_SERVICE_URL}
    except Exception as e:
        auth_status = {'connected': False, 'error': str(e), 'url': AUTH_SERVICE_URL}
    
    return jsonify({
        'status': 'healthy' if db_status.get('connected') else 'unhealthy',
        'service': 'media-service',
        'version': '1.0.0',
        'database': db_status,
        'storage': upload_status,
        'auth_service': auth_status,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/test')
def api_test():
    return jsonify({
        'success': True,
        'message': 'API is working',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/db/init', methods=['POST'])
@require_service_auth
def init_database():
    try:
        db.create_all()
        return jsonify({
            'success': True,
            'message': 'Database initialized successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to initialize database'
        }), 500

@app.route('/api/db/status')
@require_service_auth
def database_status():
    try:
        db.session.execute(db.text('SELECT 1'))
        
        tables_info = {}
        try:
            file_count = MediaFile.query.count()
            tables_info['media_files'] = {'count': file_count}
        except Exception as e:
            tables_info['media_files'] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'connected': True,
            'tables': tables_info,
            'database_url': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'local',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'connected': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/upload', methods=['POST'])
@require_auth
def upload_file():
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Use account_id from authenticated user
        account_id = request.account_id
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                'success': False, 
                'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Secure filename
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({'success': False, 'error': 'Invalid filename'}), 400
        
        # Create unique filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_hash = get_file_hash(file_path)
        file_type = get_file_type(filename)
        
        # Get MIME type
        try:
            mime_type = magic.from_file(file_path, mime=True)
        except:
            mime_type = 'application/octet-stream'
        
        # Save to database
        media_file = MediaFile(
            account_id=account_id,
            original_filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            file_hash=file_hash
        )
        
        db.session.add(media_file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file': media_file.to_dict(),
            'timestamp': datetime.utcnow().isoformat()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to upload file'
        }), 500

@app.route('/api/files', methods=['GET'])
@require_auth
def list_files():
    try:
        # Use account_id from authenticated user
        account_id = request.account_id
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        
        # Build query for user's files only
        query = MediaFile.query.filter_by(account_id=account_id, is_active=True)
        
        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        files = [file.to_dict() for file in pagination.items]
        
        return jsonify({
            'success': True,
            'files': files,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to list files'
        }), 500

@app.route('/api/files/<int:file_id>', methods=['GET'])
@require_auth
def get_file(file_id):
    try:
        # Only allow access to user's own files
        media_file = MediaFile.query.filter_by(
            id=file_id, 
            account_id=request.account_id, 
            is_active=True
        ).first()
        
        if not media_file:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return jsonify({
            'success': True,
            'file': media_file.to_dict(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get file'
        }), 500

@app.route('/api/files/<int:file_id>', methods=['DELETE'])
@require_auth
def delete_file(file_id):
    try:
        # Only allow deletion of user's own files
        media_file = MediaFile.query.filter_by(
            id=file_id, 
            account_id=request.account_id, 
            is_active=True
        ).first()
        
        if not media_file:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        # Soft delete
        media_file.is_active = False
        media_file.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'File deleted successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to delete file'
        }), 500

@app.route('/api/files/<int:file_id>/download', methods=['GET'])
@require_auth
def download_file(file_id):
    try:
        # Only allow download of user's own files
        media_file = MediaFile.query.filter_by(
            id=file_id, 
            account_id=request.account_id, 
            is_active=True
        ).first()
        
        if not media_file:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        if not os.path.exists(media_file.file_path):
            return jsonify({'success': False, 'error': 'File not found on disk'}), 404
        
        return send_file(
            media_file.file_path,
            as_attachment=True,
            download_name=media_file.original_filename,
            mimetype=media_file.mime_type
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to download file'
        }), 500

@app.route('/api/files/<int:file_id>/associate', methods=['POST'])
@require_auth
def associate_file(file_id):
    """Associate a file with a giveaway (for service-to-service communication)"""
    try:
        # Only allow association of user's own files
        media_file = MediaFile.query.filter_by(
            id=file_id, 
            account_id=request.account_id, 
            is_active=True
        ).first()
        
        if not media_file:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        # Get association data
        data = request.get_json()
        giveaway_id = data.get('giveaway_id')
        
        if not giveaway_id:
            return jsonify({'success': False, 'error': 'giveaway_id is required'}), 400
        
        return jsonify({
            'success': True,
            'message': 'File associated successfully',
            'file_id': file_id,
            'giveaway_id': giveaway_id,
            'file_url': f"/api/files/{file_id}/download",
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to associate file'
        }), 500

# Service-to-service endpoint for other services to get file info
@app.route('/api/service/files/<int:file_id>', methods=['GET'])
@require_service_auth
def service_get_file(file_id):
    """Service-to-service endpoint to get file information"""
    try:
        media_file = MediaFile.query.filter_by(id=file_id, is_active=True).first()
        
        if not media_file:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return jsonify({
            'success': True,
            'file': media_file.to_dict(),
            'download_url': f"/api/service/files/{file_id}/download",
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get file'
        }), 500

@app.route('/api/service/files/<int:file_id>/download', methods=['GET'])
@require_service_auth
def service_download_file(file_id):
    """Service-to-service endpoint to download files"""
    try:
        media_file = MediaFile.query.filter_by(id=file_id, is_active=True).first()
        
        if not media_file:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        if not os.path.exists(media_file.file_path):
            return jsonify({'success': False, 'error': 'File not found on disk'}), 404
        
        return send_file(
            media_file.file_path,
            as_attachment=True,
            download_name=media_file.original_filename,
            mimetype=media_file.mime_type
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to download file'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8005))
    app.run(host='0.0.0.0', port=port, debug=False)

