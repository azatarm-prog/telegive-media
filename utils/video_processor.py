import os
import subprocess
import json
import tempfile
from flask import current_app

class VideoProcessor:
    """Video processing and metadata extraction utilities"""
    
    def __init__(self):
        self.ffprobe_cmd = 'ffprobe'
        self.ffmpeg_cmd = 'ffmpeg'
    
    def extract_metadata(self, file_path_or_content):
        """
        Extract metadata from video file using ffprobe
        
        Args:
            file_path_or_content: File path string or bytes content
        
        Returns:
            dict: Video metadata including dimensions, duration, format, etc.
        """
        metadata = {
            'width': None,
            'height': None,
            'duration': None,
            'format': None,
            'codec': None,
            'bitrate': None,
            'fps': None,
            'file_size': None
        }
        
        temp_file = None
        try:
            # Handle bytes content by writing to temp file
            if isinstance(file_path_or_content, bytes):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
                temp_file.write(file_path_or_content)
                temp_file.close()
                file_path = temp_file.name
                metadata['file_size'] = len(file_path_or_content)
            else:
                file_path = file_path_or_content
                metadata['file_size'] = os.path.getsize(file_path)
            
            # Use ffprobe to extract metadata
            metadata.update(self._extract_ffprobe_data(file_path))
            
        except Exception as e:
            current_app.logger.error(f'Error extracting video metadata: {e}')
            metadata['error'] = str(e)
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass
        
        return metadata
    
    def _extract_ffprobe_data(self, file_path):
        """Extract video data using ffprobe"""
        metadata = {}
        
        try:
            # ffprobe command to get JSON output
            cmd = [
                self.ffprobe_cmd,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f'ffprobe failed: {result.stderr}')
            
            data = json.loads(result.stdout)
            
            # Extract format information
            if 'format' in data:
                format_info = data['format']
                metadata['duration'] = float(format_info.get('duration', 0))
                metadata['bitrate'] = int(format_info.get('bit_rate', 0))
                metadata['format'] = format_info.get('format_name', '')
            
            # Extract video stream information
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if video_stream:
                metadata['width'] = int(video_stream.get('width', 0))
                metadata['height'] = int(video_stream.get('height', 0))
                metadata['codec'] = video_stream.get('codec_name', '')
                
                # Calculate FPS
                fps_str = video_stream.get('r_frame_rate', '0/1')
                if '/' in fps_str:
                    num, den = fps_str.split('/')
                    if int(den) > 0:
                        metadata['fps'] = round(int(num) / int(den), 2)
                
        except subprocess.TimeoutExpired:
            raise Exception('Video analysis timed out')
        except json.JSONDecodeError:
            raise Exception('Failed to parse ffprobe output')
        except Exception as e:
            raise Exception(f'ffprobe analysis failed: {str(e)}')
        
        return metadata
    
    def validate_video_content(self, file_content):
        """
        Validate video content using ffprobe
        
        Args:
            file_content: Video file content as bytes
        
        Returns:
            dict: Validation result with video info
        """
        result = {
            'valid': False,
            'width': None,
            'height': None,
            'duration': None,
            'format': None,
            'error': None
        }
        
        if not current_app.config.get('VIDEO_VALIDATION_ENABLED', True):
            # Skip validation if disabled
            result['valid'] = True
            result['format'] = 'unknown'
            return result
        
        temp_file = None
        try:
            # Write content to temp file for ffprobe
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
            temp_file.write(file_content)
            temp_file.close()
            
            # Extract metadata
            metadata = self._extract_ffprobe_data(temp_file.name)
            
            # Check if we got valid video data
            if metadata.get('width') and metadata.get('height'):
                result.update({
                    'valid': True,
                    'width': metadata['width'],
                    'height': metadata['height'],
                    'duration': metadata.get('duration'),
                    'format': metadata.get('format')
                })
            else:
                result['error'] = 'No valid video stream found'
                
        except Exception as e:
            result['error'] = str(e)
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass
        
        return result
    
    def create_thumbnail(self, input_path, output_path, timestamp='00:00:01'):
        """
        Create thumbnail from video at specified timestamp
        
        Args:
            input_path: Path to input video
            output_path: Path to save thumbnail
            timestamp: Time position for thumbnail (HH:MM:SS format)
        
        Returns:
            dict: Thumbnail creation result
        """
        result = {
            'success': False,
            'thumbnail_size': 0,
            'error': None
        }
        
        try:
            cmd = [
                self.ffmpeg_cmd,
                '-i', input_path,
                '-ss', timestamp,
                '-vframes', '1',
                '-q:v', '2',
                '-y',  # Overwrite output file
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            
            if os.path.exists(output_path):
                result['thumbnail_size'] = os.path.getsize(output_path)
                result['success'] = True
            else:
                result['error'] = 'Thumbnail file not created'
                
        except subprocess.CalledProcessError as e:
            result['error'] = f'ffmpeg failed: {e.stderr.decode() if e.stderr else str(e)}'
        except subprocess.TimeoutExpired:
            result['error'] = 'Thumbnail creation timed out'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def get_video_info(self, file_path):
        """Get comprehensive video information"""
        info = {
            'exists': os.path.exists(file_path),
            'file_size': 0,
            'metadata': {}
        }
        
        if info['exists']:
            info['file_size'] = os.path.getsize(file_path)
            info['metadata'] = self.extract_metadata(file_path)
        
        return info
    
    def validate_video_constraints(self, metadata):
        """
        Validate video against configured constraints
        
        Args:
            metadata: Video metadata dict
        
        Returns:
            dict: Validation result
        """
        result = {
            'valid': True,
            'errors': []
        }
        
        # Check duration (max 5 minutes = 300 seconds)
        max_duration = 300
        if metadata.get('duration', 0) > max_duration:
            result['valid'] = False
            result['errors'].append(f'Video too long: {metadata["duration"]}s (max: {max_duration}s)')
        
        # Check dimensions (max 1920x1080)
        max_width = 1920
        max_height = 1080
        
        width = metadata.get('width', 0)
        height = metadata.get('height', 0)
        
        if width > max_width or height > max_height:
            result['valid'] = False
            result['errors'].append(f'Video resolution too high: {width}x{height} (max: {max_width}x{max_height})')
        
        return result
    
    def is_ffmpeg_available(self):
        """Check if ffmpeg/ffprobe are available"""
        try:
            subprocess.run([self.ffprobe_cmd, '-version'], 
                         capture_output=True, check=True, timeout=5)
            subprocess.run([self.ffmpeg_cmd, '-version'], 
                         capture_output=True, check=True, timeout=5)
            return True
        except Exception:
            return False

# Global video processor instance
video_processor = VideoProcessor()

