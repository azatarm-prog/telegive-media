from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Import all models
from .media_file import MediaFile
from .validation_log import FileValidationLog
from .cleanup_log import FileCleanupLog

# Export all models
__all__ = [
    'db',
    'MediaFile',
    'FileValidationLog',
    'FileCleanupLog'
]

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create indexes if they don't exist
        create_indexes()

def create_indexes():
    """Create database indexes"""
    try:
        # These indexes are already defined in the models via index=True
        # This function is for any additional custom indexes
        
        # Example of creating a composite index
        # db.engine.execute('''
        #     CREATE INDEX IF NOT EXISTS idx_media_files_account_giveaway 
        #     ON media_files(account_id, giveaway_id)
        # ''')
        
        db.session.commit()
    except Exception as e:
        print(f"Error creating indexes: {e}")
        db.session.rollback()

def drop_all_tables():
    """Drop all tables (for testing)"""
    db.drop_all()

def reset_database():
    """Reset database (drop and recreate all tables)"""
    drop_all_tables()
    db.create_all()
    create_indexes()

