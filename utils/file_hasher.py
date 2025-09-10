import hashlib
import os
from flask import current_app

class FileHasher:
    """File hashing utilities for deduplication and integrity checking"""
    
    def __init__(self):
        self.default_algorithm = 'sha256'
        self.chunk_size = 8192  # 8KB chunks for memory efficiency
    
    def calculate_hash(self, file_path_or_content, algorithm=None):
        """
        Calculate hash of file content
        
        Args:
            file_path_or_content: File path string or bytes content
            algorithm: Hash algorithm ('sha256', 'md5', 'sha1')
        
        Returns:
            str: Hexadecimal hash string
        """
        if algorithm is None:
            algorithm = current_app.config.get('HASH_ALGORITHM', self.default_algorithm)
        
        try:
            hasher = hashlib.new(algorithm)
            
            if isinstance(file_path_or_content, str):
                # File path - read in chunks for memory efficiency
                with open(file_path_or_content, 'rb') as f:
                    while chunk := f.read(self.chunk_size):
                        hasher.update(chunk)
            else:
                # Bytes content - process in chunks
                content = file_path_or_content
                for i in range(0, len(content), self.chunk_size):
                    chunk = content[i:i + self.chunk_size]
                    hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            current_app.logger.error(f'Error calculating hash: {e}')
            raise
    
    def calculate_multiple_hashes(self, file_path_or_content, algorithms=None):
        """
        Calculate multiple hashes of the same content
        
        Args:
            file_path_or_content: File path string or bytes content
            algorithms: List of hash algorithms
        
        Returns:
            dict: Dictionary with algorithm names as keys and hashes as values
        """
        if algorithms is None:
            algorithms = ['sha256', 'md5']
        
        hashers = {}
        for algorithm in algorithms:
            hashers[algorithm] = hashlib.new(algorithm)
        
        try:
            if isinstance(file_path_or_content, str):
                # File path - read in chunks
                with open(file_path_or_content, 'rb') as f:
                    while chunk := f.read(self.chunk_size):
                        for hasher in hashers.values():
                            hasher.update(chunk)
            else:
                # Bytes content - process in chunks
                content = file_path_or_content
                for i in range(0, len(content), self.chunk_size):
                    chunk = content[i:i + self.chunk_size]
                    for hasher in hashers.values():
                        hasher.update(chunk)
            
            return {alg: hasher.hexdigest() for alg, hasher in hashers.items()}
            
        except Exception as e:
            current_app.logger.error(f'Error calculating multiple hashes: {e}')
            raise
    
    def verify_file_integrity(self, file_path, expected_hash, algorithm=None):
        """
        Verify file integrity by comparing hash
        
        Args:
            file_path: Path to file
            expected_hash: Expected hash value
            algorithm: Hash algorithm to use
        
        Returns:
            bool: True if hashes match, False otherwise
        """
        try:
            actual_hash = self.calculate_hash(file_path, algorithm)
            return actual_hash.lower() == expected_hash.lower()
        except Exception as e:
            current_app.logger.error(f'Error verifying file integrity: {e}')
            return False
    
    def calculate_hash_from_stream(self, file_stream, algorithm=None):
        """
        Calculate hash from file stream (useful for uploaded files)
        
        Args:
            file_stream: File-like object
            algorithm: Hash algorithm to use
        
        Returns:
            str: Hexadecimal hash string
        """
        if algorithm is None:
            algorithm = current_app.config.get('HASH_ALGORITHM', self.default_algorithm)
        
        try:
            hasher = hashlib.new(algorithm)
            
            # Save current position
            original_position = file_stream.tell()
            
            # Go to beginning
            file_stream.seek(0)
            
            # Read and hash in chunks
            while chunk := file_stream.read(self.chunk_size):
                hasher.update(chunk)
            
            # Restore original position
            file_stream.seek(original_position)
            
            return hasher.hexdigest()
            
        except Exception as e:
            current_app.logger.error(f'Error calculating hash from stream: {e}')
            raise
    
    def get_file_signature(self, file_path_or_content):
        """
        Get comprehensive file signature including multiple hashes and metadata
        
        Args:
            file_path_or_content: File path string or bytes content
        
        Returns:
            dict: File signature with hashes and metadata
        """
        signature = {
            'sha256': None,
            'md5': None,
            'file_size': 0,
            'algorithm_used': 'sha256'
        }
        
        try:
            # Calculate multiple hashes
            hashes = self.calculate_multiple_hashes(file_path_or_content, ['sha256', 'md5'])
            signature.update(hashes)
            
            # Get file size
            if isinstance(file_path_or_content, str):
                signature['file_size'] = os.path.getsize(file_path_or_content)
            else:
                signature['file_size'] = len(file_path_or_content)
            
        except Exception as e:
            current_app.logger.error(f'Error getting file signature: {e}')
            signature['error'] = str(e)
        
        return signature
    
    def compare_files(self, file1_path, file2_path, algorithm=None):
        """
        Compare two files by hash
        
        Args:
            file1_path: Path to first file
            file2_path: Path to second file
            algorithm: Hash algorithm to use
        
        Returns:
            dict: Comparison result
        """
        result = {
            'identical': False,
            'file1_hash': None,
            'file2_hash': None,
            'file1_size': 0,
            'file2_size': 0
        }
        
        try:
            # Quick size check first
            result['file1_size'] = os.path.getsize(file1_path)
            result['file2_size'] = os.path.getsize(file2_path)
            
            if result['file1_size'] != result['file2_size']:
                # Different sizes = different files
                return result
            
            # Calculate hashes
            result['file1_hash'] = self.calculate_hash(file1_path, algorithm)
            result['file2_hash'] = self.calculate_hash(file2_path, algorithm)
            
            result['identical'] = result['file1_hash'] == result['file2_hash']
            
        except Exception as e:
            current_app.logger.error(f'Error comparing files: {e}')
            result['error'] = str(e)
        
        return result
    
    def is_duplicate_content(self, content1, content2):
        """
        Check if two byte contents are identical using hash comparison
        
        Args:
            content1: First content as bytes
            content2: Second content as bytes
        
        Returns:
            bool: True if contents are identical
        """
        try:
            # Quick size check
            if len(content1) != len(content2):
                return False
            
            # Hash comparison
            hash1 = self.calculate_hash(content1)
            hash2 = self.calculate_hash(content2)
            
            return hash1 == hash2
            
        except Exception as e:
            current_app.logger.error(f'Error checking duplicate content: {e}')
            return False
    
    def get_supported_algorithms(self):
        """Get list of supported hash algorithms"""
        return list(hashlib.algorithms_available)
    
    def validate_hash_format(self, hash_string, algorithm=None):
        """
        Validate hash string format
        
        Args:
            hash_string: Hash string to validate
            algorithm: Expected algorithm
        
        Returns:
            bool: True if format is valid
        """
        if algorithm is None:
            algorithm = self.default_algorithm
        
        expected_lengths = {
            'md5': 32,
            'sha1': 40,
            'sha256': 64,
            'sha512': 128
        }
        
        if algorithm not in expected_lengths:
            return False
        
        expected_length = expected_lengths[algorithm]
        
        # Check length and hex format
        if len(hash_string) != expected_length:
            return False
        
        try:
            int(hash_string, 16)  # Validate hex format
            return True
        except ValueError:
            return False

# Global file hasher instance
file_hasher = FileHasher()

