import requests
from flask import current_app
from datetime import datetime

class TelegiveService:
    """Integration with main Telegive giveaway service"""
    
    def __init__(self):
        self.service_url = None
        self.service_token = None
        self.timeout = 30
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.service_url = app.config.get('TELEGIVE_GIVEAWAY_URL')
        
        # Generate service token for authentication
        from services.auth_service import auth_service
        auth_service.init_app(app)
        self.service_token = auth_service.generate_service_token(
            'media-service',
            permissions=['media_management', 'file_cleanup']
        )
    
    def notify_file_uploaded(self, file_id, account_id, file_info):
        """
        Notify giveaway service about file upload
        
        Args:
            file_id: Media file ID
            account_id: Account ID
            file_info: File information dict
        
        Returns:
            dict: Notification result
        """
        result = {
            'success': False,
            'error': None
        }
        
        try:
            if not self.service_url:
                result['error'] = 'Giveaway service URL not configured'
                return result
            
            payload = {
                'event': 'file_uploaded',
                'data': {
                    'file_id': file_id,
                    'account_id': account_id,
                    'file_info': file_info,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            response = requests.post(
                f"{self.service_url}/api/webhooks/media",
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.service_token}',
                    'Content-Type': 'application/json',
                    'X-Service-Name': 'media-service'
                },
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                result['success'] = True
            else:
                result['error'] = f'Notification failed: {response.status_code}'
                
        except requests.exceptions.Timeout:
            result['error'] = 'Giveaway service timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Giveaway service unavailable'
        except Exception as e:
            result['error'] = f'Notification error: {str(e)}'
        
        return result
    
    def notify_file_deleted(self, file_id, account_id, deletion_info):
        """
        Notify giveaway service about file deletion
        
        Args:
            file_id: Media file ID
            account_id: Account ID
            deletion_info: Deletion information dict
        
        Returns:
            dict: Notification result
        """
        result = {
            'success': False,
            'error': None
        }
        
        try:
            if not self.service_url:
                result['error'] = 'Giveaway service URL not configured'
                return result
            
            payload = {
                'event': 'file_deleted',
                'data': {
                    'file_id': file_id,
                    'account_id': account_id,
                    'deletion_info': deletion_info,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            response = requests.post(
                f"{self.service_url}/api/webhooks/media",
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.service_token}',
                    'Content-Type': 'application/json',
                    'X-Service-Name': 'media-service'
                },
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                result['success'] = True
            else:
                result['error'] = f'Notification failed: {response.status_code}'
                
        except requests.exceptions.Timeout:
            result['error'] = 'Giveaway service timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Giveaway service unavailable'
        except Exception as e:
            result['error'] = f'Notification error: {str(e)}'
        
        return result
    
    def get_giveaway_info(self, giveaway_id):
        """
        Get giveaway information from giveaway service
        
        Args:
            giveaway_id: Giveaway ID
        
        Returns:
            dict: Giveaway information or error
        """
        result = {
            'success': False,
            'giveaway_info': None,
            'error': None
        }
        
        try:
            if not self.service_url:
                result['error'] = 'Giveaway service URL not configured'
                return result
            
            response = requests.get(
                f"{self.service_url}/api/giveaways/{giveaway_id}",
                headers={
                    'Authorization': f'Bearer {self.service_token}',
                    'X-Service-Name': 'media-service'
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                result.update({
                    'success': True,
                    'giveaway_info': data.get('giveaway_info')
                })
            elif response.status_code == 404:
                result['error'] = 'Giveaway not found'
            else:
                result['error'] = f'Failed to get giveaway info: {response.status_code}'
                
        except requests.exceptions.Timeout:
            result['error'] = 'Giveaway service timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Giveaway service unavailable'
        except Exception as e:
            result['error'] = f'Get giveaway info error: {str(e)}'
        
        return result
    
    def validate_account_access(self, account_id, user_id=None):
        """
        Validate if user has access to account
        
        Args:
            account_id: Account ID
            user_id: User ID (optional)
        
        Returns:
            dict: Validation result
        """
        result = {
            'valid': False,
            'error': None
        }
        
        try:
            if not self.service_url:
                result['error'] = 'Giveaway service URL not configured'
                return result
            
            params = {'account_id': account_id}
            if user_id:
                params['user_id'] = user_id
            
            response = requests.get(
                f"{self.service_url}/api/accounts/validate-access",
                params=params,
                headers={
                    'Authorization': f'Bearer {self.service_token}',
                    'X-Service-Name': 'media-service'
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                result.update({
                    'valid': data.get('valid', False),
                    'permissions': data.get('permissions', [])
                })
            else:
                result['error'] = f'Access validation failed: {response.status_code}'
                
        except requests.exceptions.Timeout:
            result['error'] = 'Giveaway service timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Giveaway service unavailable'
        except Exception as e:
            result['error'] = f'Access validation error: {str(e)}'
        
        return result
    
    def report_cleanup_completed(self, giveaway_id, cleanup_summary):
        """
        Report cleanup completion to giveaway service
        
        Args:
            giveaway_id: Giveaway ID
            cleanup_summary: Cleanup summary dict
        
        Returns:
            dict: Report result
        """
        result = {
            'success': False,
            'error': None
        }
        
        try:
            if not self.service_url:
                result['error'] = 'Giveaway service URL not configured'
                return result
            
            payload = {
                'giveaway_id': giveaway_id,
                'cleanup_summary': cleanup_summary,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                f"{self.service_url}/api/giveaways/{giveaway_id}/cleanup-completed",
                json=payload,
                headers={
                    'Authorization': f'Bearer {self.service_token}',
                    'Content-Type': 'application/json',
                    'X-Service-Name': 'media-service'
                },
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                result['success'] = True
            else:
                result['error'] = f'Report failed: {response.status_code}'
                
        except requests.exceptions.Timeout:
            result['error'] = 'Giveaway service timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Giveaway service unavailable'
        except Exception as e:
            result['error'] = f'Report error: {str(e)}'
        
        return result
    
    def get_service_health(self):
        """
        Check giveaway service health
        
        Returns:
            dict: Health status
        """
        result = {
            'healthy': False,
            'response_time_ms': None,
            'error': None
        }
        
        try:
            if not self.service_url:
                result['error'] = 'Giveaway service URL not configured'
                return result
            
            start_time = datetime.utcnow()
            
            response = requests.get(
                f"{self.service_url}/health",
                timeout=10  # Shorter timeout for health check
            )
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            result['response_time_ms'] = round(response_time, 2)
            
            if response.status_code == 200:
                result['healthy'] = True
            else:
                result['error'] = f'Health check failed: {response.status_code}'
                
        except requests.exceptions.Timeout:
            result['error'] = 'Health check timeout'
        except requests.exceptions.ConnectionError:
            result['error'] = 'Service unavailable'
        except Exception as e:
            result['error'] = f'Health check error: {str(e)}'
        
        return result
    
    def refresh_service_token(self):
        """Refresh service authentication token"""
        try:
            from services.auth_service import auth_service
            self.service_token = auth_service.generate_service_token(
                'media-service',
                permissions=['media_management', 'file_cleanup']
            )
            return True
        except Exception as e:
            current_app.logger.error(f'Failed to refresh service token: {e}')
            return False

# Global telegive service instance
telegive_service = TelegiveService()

