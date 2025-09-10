import os
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import io
from flask import current_app

class ImageProcessor:
    """Image processing and metadata extraction utilities"""
    
    def __init__(self):
        self.supported_formats = ['JPEG', 'PNG', 'GIF']
    
    def extract_metadata(self, file_path_or_content):
        """
        Extract metadata from image file
        
        Args:
            file_path_or_content: File path string or bytes content
        
        Returns:
            dict: Image metadata including dimensions, format, etc.
        """
        metadata = {
            'width': None,
            'height': None,
            'format': None,
            'mode': None,
            'has_transparency': False,
            'exif_data': {},
            'file_size': None
        }
        
        try:
            # Open image
            if isinstance(file_path_or_content, str):
                # File path
                with Image.open(file_path_or_content) as img:
                    metadata.update(self._extract_basic_info(img))
                    metadata.update(self._extract_exif_data(img))
                metadata['file_size'] = os.path.getsize(file_path_or_content)
            else:
                # Bytes content
                with Image.open(io.BytesIO(file_path_or_content)) as img:
                    metadata.update(self._extract_basic_info(img))
                    metadata.update(self._extract_exif_data(img))
                metadata['file_size'] = len(file_path_or_content)
                
        except Exception as e:
            current_app.logger.error(f'Error extracting image metadata: {e}')
            metadata['error'] = str(e)
        
        return metadata
    
    def _extract_basic_info(self, img):
        """Extract basic image information"""
        return {
            'width': img.width,
            'height': img.height,
            'format': img.format,
            'mode': img.mode,
            'has_transparency': self._has_transparency(img)
        }
    
    def _extract_exif_data(self, img):
        """Extract EXIF data from image"""
        exif_data = {}
        
        try:
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif = img._getexif()
                
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # Convert bytes to string for JSON serialization
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8')
                        except UnicodeDecodeError:
                            value = str(value)
                    
                    # Skip complex data types
                    if isinstance(value, (str, int, float)):
                        exif_data[tag] = value
                        
        except Exception as e:
            current_app.logger.debug(f'Error extracting EXIF data: {e}')
        
        return {'exif_data': exif_data}
    
    def _has_transparency(self, img):
        """Check if image has transparency"""
        try:
            if img.mode in ('RGBA', 'LA'):
                return True
            elif img.mode == 'P':
                return 'transparency' in img.info
            elif img.format == 'GIF':
                return img.is_animated or 'transparency' in img.info
            return False
        except Exception:
            return False
    
    def optimize_image(self, input_path, output_path, quality=None, max_width=None, max_height=None):
        """
        Optimize image for storage
        
        Args:
            input_path: Path to input image
            output_path: Path to save optimized image
            quality: JPEG quality (1-100)
            max_width: Maximum width for resizing
            max_height: Maximum height for resizing
        
        Returns:
            dict: Optimization result with new file size and dimensions
        """
        result = {
            'success': False,
            'original_size': 0,
            'optimized_size': 0,
            'compression_ratio': 0,
            'new_dimensions': None
        }
        
        try:
            # Get original file size
            result['original_size'] = os.path.getsize(input_path)
            
            with Image.open(input_path) as img:
                # Convert to RGB if necessary (for JPEG)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Resize if needed
                if max_width or max_height:
                    img = self._resize_image(img, max_width, max_height)
                
                # Set quality
                if quality is None:
                    quality = current_app.config.get('IMAGE_QUALITY', 85)
                
                # Save optimized image
                save_kwargs = {'format': 'JPEG', 'quality': quality, 'optimize': True}
                img.save(output_path, **save_kwargs)
                
                # Get results
                result['optimized_size'] = os.path.getsize(output_path)
                result['compression_ratio'] = (result['original_size'] - result['optimized_size']) / result['original_size']
                result['new_dimensions'] = (img.width, img.height)
                result['success'] = True
                
        except Exception as e:
            current_app.logger.error(f'Error optimizing image: {e}')
            result['error'] = str(e)
        
        return result
    
    def _resize_image(self, img, max_width, max_height):
        """Resize image while maintaining aspect ratio"""
        original_width, original_height = img.size
        
        # Calculate new dimensions
        if max_width and max_height:
            # Fit within both constraints
            ratio = min(max_width / original_width, max_height / original_height)
        elif max_width:
            ratio = max_width / original_width
        elif max_height:
            ratio = max_height / original_height
        else:
            return img
        
        # Only resize if image is larger than constraints
        if ratio < 1:
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return img
    
    def create_thumbnail(self, input_path, output_path, size=(150, 150)):
        """
        Create thumbnail from image
        
        Args:
            input_path: Path to input image
            output_path: Path to save thumbnail
            size: Thumbnail size tuple (width, height)
        
        Returns:
            dict: Thumbnail creation result
        """
        result = {
            'success': False,
            'thumbnail_size': 0,
            'dimensions': None
        }
        
        try:
            with Image.open(input_path) as img:
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Save thumbnail
                img.save(output_path, 'JPEG', quality=80, optimize=True)
                
                result['thumbnail_size'] = os.path.getsize(output_path)
                result['dimensions'] = img.size
                result['success'] = True
                
        except Exception as e:
            current_app.logger.error(f'Error creating thumbnail: {e}')
            result['error'] = str(e)
        
        return result
    
    def validate_image_content(self, file_content):
        """
        Validate image content and extract basic info
        
        Args:
            file_content: Image file content as bytes
        
        Returns:
            dict: Validation result with image info
        """
        result = {
            'valid': False,
            'width': None,
            'height': None,
            'format': None,
            'error': None
        }
        
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                # Verify image can be loaded
                img.verify()
                
                # Re-open for metadata (verify() closes the image)
                img = Image.open(io.BytesIO(file_content))
                
                result.update({
                    'valid': True,
                    'width': img.width,
                    'height': img.height,
                    'format': img.format
                })
                
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_image_info(self, file_path):
        """Get comprehensive image information"""
        info = {
            'exists': os.path.exists(file_path),
            'file_size': 0,
            'metadata': {}
        }
        
        if info['exists']:
            info['file_size'] = os.path.getsize(file_path)
            info['metadata'] = self.extract_metadata(file_path)
        
        return info

# Global image processor instance
image_processor = ImageProcessor()

