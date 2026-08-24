"""
ImgBB service for image upload and deletion.
"""
import base64
import requests
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


class ImgBBService:
    """Service for uploading and deleting images via ImgBB API."""
    
    UPLOAD_URL = "https://api.imgbb.com/1/upload"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, 'IMGBB_API_KEY', None)
    
    def upload(self, file: UploadedFile) -> dict:
        """
        Upload an image file to ImgBB.
        
        Args:
            file: Django UploadedFile object
            
        Returns:
            dict with keys: success, display_url, delete_url, error (if failed)
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'IMGBB_API_KEY not configured'
            }
        
        try:
            # Read file and encode to base64
            file_content = file.read()
            # Rewind so later consumers (e.g. saving a local copy) can
            # read the file content again.
            try:
                file.seek(0)
            except (AttributeError, OSError):
                pass
            image_base64 = base64.b64encode(file_content).decode('utf-8')
            
            payload = {
                'key': self.api_key,
                'image': image_base64,
            }
            
            response = requests.post(self.UPLOAD_URL, data=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success'):
                data = result['data']
                return {
                    'success': True,
                    'display_url': data.get('display_url'),
                    'delete_url': data.get('delete_url'),
                    'thumb_url': data.get('thumb', {}).get('url'),
                    'medium_url': data.get('medium', {}).get('url'),
                    'id': data.get('id'),
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown ImgBB error')
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Upload failed: {str(e)}'
            }
    
    def delete(self, delete_url: str) -> bool:
        """
        Delete an image from ImgBB using the delete URL.
        
        Args:
            delete_url: The delete URL returned from upload
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not delete_url:
            return False
            
        try:
            response = requests.get(delete_url, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
        except Exception:
            return False


# Convenience function for easy import
def get_imgbb_service():
    """Get configured ImgBB service instance."""
    return ImgBBService()