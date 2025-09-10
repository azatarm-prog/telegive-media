from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class FileCleanupLog(db.Model):
    """File cleanup log table"""
    
    __tablename__ = 'file_cleanup_log'
    
    # Primary key
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign key
    media_file_id = db.Column(db.BigInteger, db.ForeignKey('media_files.id'), nullable=False, index=True)
    
    # Cleanup information
    cleanup_trigger = db.Column(db.String(50), nullable=False)  # giveaway_published, manual, scheduled
    cleanup_success = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    file_size_freed = db.Column(db.BigInteger, nullable=True)
    cleanup_timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(FileCleanupLog, self).__init__(**kwargs)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'media_file_id': self.media_file_id,
            'cleanup_trigger': self.cleanup_trigger,
            'cleanup_success': self.cleanup_success,
            'error_message': self.error_message,
            'file_size_freed': self.file_size_freed,
            'cleanup_timestamp': self.cleanup_timestamp.isoformat() if self.cleanup_timestamp else None
        }
    
    @classmethod
    def create_log(cls, media_file_id, trigger, success, error_message=None, file_size_freed=None):
        """Create a new cleanup log entry"""
        log = cls(
            media_file_id=media_file_id,
            cleanup_trigger=trigger,
            cleanup_success=success,
            error_message=error_message,
            file_size_freed=file_size_freed
        )
        return log
    
    def is_successful(self):
        """Check if cleanup was successful"""
        return self.cleanup_success
    
    def get_error_summary(self):
        """Get a summary of the cleanup error"""
        if self.cleanup_success:
            return None
        
        summary = f"Cleanup failed (trigger: {self.cleanup_trigger})"
        if self.error_message:
            summary += f": {self.error_message}"
        
        return summary
    
    def get_size_freed_mb(self):
        """Get file size freed in MB"""
        if self.file_size_freed:
            return round(self.file_size_freed / (1024 * 1024), 2)
        return 0
    
    def __repr__(self):
        status = "SUCCESS" if self.cleanup_success else "FAILED"
        return f'<FileCleanupLog {self.id}: {self.cleanup_trigger} - {status}>'

