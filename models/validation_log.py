from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB

db = SQLAlchemy()

class FileValidationLog(db.Model):
    """File validation log table"""
    
    __tablename__ = 'file_validation_log'
    
    # Primary key
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign key
    media_file_id = db.Column(db.BigInteger, db.ForeignKey('media_files.id'), nullable=False, index=True)
    
    # Validation information
    validation_type = db.Column(db.String(50), nullable=False)  # format, size, security, content
    validation_result = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    validation_details = db.Column(JSONB, nullable=True)
    validated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(FileValidationLog, self).__init__(**kwargs)
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'media_file_id': self.media_file_id,
            'validation_type': self.validation_type,
            'validation_result': self.validation_result,
            'error_message': self.error_message,
            'validation_details': self.validation_details,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None
        }
    
    @classmethod
    def create_log(cls, media_file_id, validation_type, result, error_message=None, details=None):
        """Create a new validation log entry"""
        log = cls(
            media_file_id=media_file_id,
            validation_type=validation_type,
            validation_result=result,
            error_message=error_message,
            validation_details=details
        )
        return log
    
    def is_successful(self):
        """Check if validation was successful"""
        return self.validation_result
    
    def get_error_summary(self):
        """Get a summary of the validation error"""
        if self.validation_result:
            return None
        
        summary = f"{self.validation_type} validation failed"
        if self.error_message:
            summary += f": {self.error_message}"
        
        return summary
    
    def __repr__(self):
        status = "PASS" if self.validation_result else "FAIL"
        return f'<FileValidationLog {self.id}: {self.validation_type} - {status}>'

