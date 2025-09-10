import os
import shutil
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

class FileStorage:
    """File storage utilities for managing uploaded files"""
    
    def __init__(self):
        self.base_upload_folder = None
    
    def get_upload_folder(self):
        """Get the configured upload folder"""
        if self.base_upload_folder is None:
            self.base_upload_folder = current_app.config.get('UPLOAD_FOLDER', '/app/uploads')
        return self.base_upload_folder
    
    def ensure_upload_folder_exists(self):
        """Ensure upload folder exists"""
        upload_folder = self.get_upload_folder()
        if not os.path.exists(upload_folder):
            try:
                os.makedirs(upload_folder, exist_ok=True)
                current_app.logger.info(f'Created upload folder: {upload_folder}')
            except Exception as e:
                current_app.logger.error(f'Failed to create upload folder: {e}')
                raise
    
    def generate_unique_filename(self, original_filename, account_id=None):
        """
        Generate unique filename for storage
        
        Args:
            original_filename: Original filename from upload
            account_id: Account ID for organization
        
        Returns:
            str: Unique filename for storage
        """
        # Secure the original filename
        secure_name = secure_filename(original_filename)
        
        # Get file extension
        name, ext = os.path.splitext(secure_name)
        
        # Generate unique identifier
        unique_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Create unique filename
        if account_id:
            unique_filename = f"{account_id}_{timestamp}_{unique_id}{ext}"
        else:
            unique_filename = f"{timestamp}_{unique_id}{ext}"
        
        return unique_filename
    
    def get_file_path(self, filename, create_subdirs=True):
        """
        Get full file path for storage
        
        Args:
            filename: Filename to store
            create_subdirs: Whether to create subdirectories
        
        Returns:
            str: Full file path
        """
        upload_folder = self.get_upload_folder()
        
        if create_subdirs:
            # Create subdirectories based on date for organization
            today = datetime.utcnow()
            year_month = today.strftime('%Y/%m')
            subdir = os.path.join(upload_folder, year_month)
            
            # Ensure subdirectory exists
            if not os.path.exists(subdir):
                os.makedirs(subdir, exist_ok=True)
            
            return os.path.join(subdir, filename)
        else:
            return os.path.join(upload_folder, filename)
    
    def save_uploaded_file(self, file_storage, account_id=None):
        """
        Save uploaded file to storage
        
        Args:
            file_storage: Flask FileStorage object
            account_id: Account ID for organization
        
        Returns:
            dict: Storage result with file paths and metadata
        """
        result = {
            'success': False,
            'stored_filename': None,
            'file_path': None,
            'file_size': 0,
            'error': None
        }
        
        try:
            # Ensure upload folder exists
            self.ensure_upload_folder_exists()
            
            # Generate unique filename
            stored_filename = self.generate_unique_filename(file_storage.filename, account_id)
            
            # Get full file path
            file_path = self.get_file_path(stored_filename)
            
            # Save file
            file_storage.save(file_path)
            
            # Verify file was saved
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                
                result.update({
                    'success': True,
                    'stored_filename': stored_filename,
                    'file_path': file_path,
                    'file_size': file_size
                })
            else:
                result['error'] = 'File was not saved successfully'
                
        except Exception as e:
            current_app.logger.error(f'Error saving uploaded file: {e}')
            result['error'] = str(e)
        
        return result
    
    def save_file_content(self, file_content, original_filename, account_id=None):
        """
        Save file content to storage
        
        Args:
            file_content: File content as bytes
            original_filename: Original filename
            account_id: Account ID for organization
        
        Returns:
            dict: Storage result
        """
        result = {
            'success': False,
            'stored_filename': None,
            'file_path': None,
            'file_size': 0,
            'error': None
        }
        
        try:
            # Ensure upload folder exists
            self.ensure_upload_folder_exists()
            
            # Generate unique filename
            stored_filename = self.generate_unique_filename(original_filename, account_id)
            
            # Get full file path
            file_path = self.get_file_path(stored_filename)
            
            # Write file content
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Verify file was saved
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                
                result.update({
                    'success': True,
                    'stored_filename': stored_filename,
                    'file_path': file_path,
                    'file_size': file_size
                })
            else:
                result['error'] = 'File was not saved successfully'
                
        except Exception as e:
            current_app.logger.error(f'Error saving file content: {e}')
            result['error'] = str(e)
        
        return result
    
    def delete_file(self, file_path):
        """
        Delete file from storage
        
        Args:
            file_path: Path to file to delete
        
        Returns:
            dict: Deletion result
        """
        result = {
            'success': False,
            'file_size_freed': 0,
            'error': None
        }
        
        try:
            if os.path.exists(file_path):
                # Get file size before deletion
                file_size = os.path.getsize(file_path)
                
                # Delete file
                os.remove(file_path)
                
                # Verify deletion
                if not os.path.exists(file_path):
                    result.update({
                        'success': True,
                        'file_size_freed': file_size
                    })
                else:
                    result['error'] = 'File still exists after deletion attempt'
            else:
                # File doesn't exist - consider this success
                result['success'] = True
                result['error'] = 'File does not exist'
                
        except Exception as e:
            current_app.logger.error(f'Error deleting file: {e}')
            result['error'] = str(e)
        
        return result
    
    def move_file(self, source_path, destination_path):
        """
        Move file from source to destination
        
        Args:
            source_path: Source file path
            destination_path: Destination file path
        
        Returns:
            dict: Move result
        """
        result = {
            'success': False,
            'error': None
        }
        
        try:
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination_path)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            
            # Move file
            shutil.move(source_path, destination_path)
            
            # Verify move
            if os.path.exists(destination_path) and not os.path.exists(source_path):
                result['success'] = True
            else:
                result['error'] = 'File move verification failed'
                
        except Exception as e:
            current_app.logger.error(f'Error moving file: {e}')
            result['error'] = str(e)
        
        return result
    
    def copy_file(self, source_path, destination_path):
        """
        Copy file from source to destination
        
        Args:
            source_path: Source file path
            destination_path: Destination file path
        
        Returns:
            dict: Copy result
        """
        result = {
            'success': False,
            'error': None
        }
        
        try:
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination_path)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_path, destination_path)
            
            # Verify copy
            if os.path.exists(destination_path):
                result['success'] = True
            else:
                result['error'] = 'File copy verification failed'
                
        except Exception as e:
            current_app.logger.error(f'Error copying file: {e}')
            result['error'] = str(e)
        
        return result
    
    def get_file_info(self, file_path):
        """
        Get file information
        
        Args:
            file_path: Path to file
        
        Returns:
            dict: File information
        """
        info = {
            'exists': False,
            'file_size': 0,
            'created_at': None,
            'modified_at': None,
            'is_readable': False,
            'is_writable': False
        }
        
        try:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                
                info.update({
                    'exists': True,
                    'file_size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime),
                    'is_readable': os.access(file_path, os.R_OK),
                    'is_writable': os.access(file_path, os.W_OK)
                })
                
        except Exception as e:
            current_app.logger.error(f'Error getting file info: {e}')
            info['error'] = str(e)
        
        return info
    
    def get_storage_stats(self):
        """
        Get storage statistics
        
        Returns:
            dict: Storage statistics
        """
        stats = {
            'total_files': 0,
            'total_size': 0,
            'upload_folder': self.get_upload_folder(),
            'folder_exists': False
        }
        
        try:
            upload_folder = self.get_upload_folder()
            
            if os.path.exists(upload_folder):
                stats['folder_exists'] = True
                
                # Walk through all files
                for root, dirs, files in os.walk(upload_folder):
                    for file in files:
                        if file != '.gitkeep':  # Skip placeholder files
                            file_path = os.path.join(root, file)
                            try:
                                stats['total_files'] += 1
                                stats['total_size'] += os.path.getsize(file_path)
                            except Exception:
                                # Skip files that can't be accessed
                                pass
                
        except Exception as e:
            current_app.logger.error(f'Error getting storage stats: {e}')
            stats['error'] = str(e)
        
        return stats
    
    def cleanup_empty_directories(self):
        """
        Remove empty directories in upload folder
        
        Returns:
            dict: Cleanup result
        """
        result = {
            'success': False,
            'directories_removed': 0,
            'error': None
        }
        
        try:
            upload_folder = self.get_upload_folder()
            
            if os.path.exists(upload_folder):
                # Walk from bottom up to remove empty directories
                for root, dirs, files in os.walk(upload_folder, topdown=False):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            # Try to remove if empty
                            os.rmdir(dir_path)
                            result['directories_removed'] += 1
                        except OSError:
                            # Directory not empty, skip
                            pass
                
                result['success'] = True
                
        except Exception as e:
            current_app.logger.error(f'Error cleaning up directories: {e}')
            result['error'] = str(e)
        
        return result

# Global file storage instance
file_storage = FileStorage()

