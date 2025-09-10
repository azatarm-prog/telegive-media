from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///test.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# Initialize database
db = SQLAlchemy(app)

# Simple Media File model
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

@app.route('/')
def root():
    return jsonify({
        'service': 'Media Management Service',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': [
            '/',
            '/health',
            '/health/detailed',
            '/api/test',
            '/api/db/init',
            '/api/db/status'
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
    
    return jsonify({
        'status': 'healthy' if db_status.get('connected') else 'unhealthy',
        'service': 'media-service',
        'version': '1.0.0',
        'database': db_status,
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
def init_database():
    try:
        # Create all tables
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
def database_status():
    try:
        # Test connection
        db.session.execute(db.text('SELECT 1'))
        
        # Get table info
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8005))
    app.run(host='0.0.0.0', port=port, debug=False)

