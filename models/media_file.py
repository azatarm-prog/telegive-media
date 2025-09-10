from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class MediaFile(db.Model):
    """Media files table - primary responsibility of this service"""
    
    __tablename__ = 'media_files'
    
    # Primary key
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign keys
    account_id = db.Column(db.BigInteger, nullable=False, index=True)
    giveaway_id = db.Column(db.BigInteger, nullable=True, index=True)  # NULL until associated with giveaway
    
    # File information
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # image, video
    mime_type = db.Column(db.String(100), nullable=False)
    file_extension = db.Column(db.String(10), nullable=False)
    
    # File metadata
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.Float, nullable=True)  # For videos in seconds
    file_hash = db.Column(db.String(64), nullable=False, index=True)  # SHA-256 hash for deduplication
    
    # Upload information
    uploaded_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    uploaded_by_ip = db.Column(db.String(45), nullable=True)
    upload_session_id = db.Column(db.String(255), nullable=True)
    
    # Cleanup tracking
    cleanup_status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # pending, published_and_removed, permanent
    cleanup_scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cleanup_completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cleanup_error = db.Column(db.Text, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_validated = db.Column(db.Boolean, nullable=False, default=False)
    validation_error = db.Column(db.Text, nullable=True)
    
    # Relationships
    validation_logs = db.relationship('FileValidationLog', backref='media_file', lazy='dynamic', cascade='all, delete-orphan')
    cleanup_logs = db.relationship('FileCleanupLog', backref='media_file', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(MediaFile, self).__init__(**kwargs)
    
    def to_dict(self, include_sensitive=False):
        """Convert model to dictionary"""
        data = {
            'id': self.id,
            'account_id': self.account_id,
            'giveaway_id': self.giveaway_id,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'file_extension': self.file_extension,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'cleanup_status': self.cleanup_status,
            'is_active': self.is_active,
            'is_validated': self.is_validated
        }
        
        if include_sensitive:
            data.update({
                'file_path': self.file_path,
                'file_hash': self.file_hash,
                'uploaded_by_ip': self.uploaded_by_ip,
                'upload_session_id': self.upload_session_id,
                'cleanup_scheduled_at': self.cleanup_scheduled_at.isoformat() if self.cleanup_scheduled_at else None,
                'cleanup_completed_at': self.cleanup_completed_at.isoformat() if self.cleanup_completed_at else None,
                'cleanup_error': self.cleanup_error,
                'validation_error': self.validation_error
            })
        
        return data
    
    def get_file_url(self, base_url=None):
        """Get file URL for serving"""
        if base_url:
            return f"{base_url}/api/media/{self.id}/download"
        return f"/api/media/{self.id}/download"
    
    def is_image(self):
        """Check if file is an image"""
        return self.file_type == 'image'
    
    def is_video(self):
        """Check if file is a video"""
        return self.file_type == 'video'
    
    def can_cleanup(self):
        """Check if file can be cleaned up"""
        return self.cleanup_status == 'pending' and self.giveaway_id is not None
    
    def mark_for_cleanup(self, delay_minutes=5):
        """Mark file for cleanup after specified delay"""
        from datetime import timedelta
        self.cleanup_scheduled_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
        self.cleanup_status = 'pending'
    
    def mark_cleanup_completed(self):
        """Mark cleanup as completed"""
        self.cleanup_status = 'published_and_removed'
        self.cleanup_completed_at = datetime.utcnow()
        self.is_active = False
    
    def mark_permanent(self):
        """Mark file as permanent (no cleanup)"""
        self.cleanup_status = 'permanent'
        self.cleanup_scheduled_at = None
    
    def __repr__(self):
        return f'<MediaFile {self.id}: {self.original_filename}>'

