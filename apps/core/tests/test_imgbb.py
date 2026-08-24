"""
Tests for ImgBB service.
"""
import base64
from unittest.mock import Mock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.utils.imgbb import ImgBBService


class TestImgBBService:
    """Tests for ImgBB service."""

    def test_init_with_api_key(self):
        """Test service initialization with API key."""
        service = ImgBBService(api_key='test-key')
        assert service.api_key == 'test-key'

    def test_init_without_api_key(self):
        """Test service initialization without API key uses settings."""
        with patch('apps.core.utils.imgbb.settings') as mock_settings:
            mock_settings.IMGBB_API_KEY = 'settings-key'
            service = ImgBBService()
            assert service.api_key == 'settings-key'

    def test_upload_no_api_key(self):
        """Test upload fails when no API key configured."""
        service = ImgBBService(api_key=None)
        file = SimpleUploadedFile("test.jpg", b"fake-image", content_type="image/jpeg")
        result = service.upload(file)
        assert result['success'] is False
        assert 'IMGBB_API_KEY not configured' in result['error']

    @patch('apps.core.utils.imgbb.requests.post')
    def test_upload_success(self, mock_post):
        """Test successful image upload."""
        service = ImgBBService(api_key='test-key')
        file = SimpleUploadedFile("test.jpg", b"fake-image", content_type="image/jpeg")
        
        # Mock response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'success': True,
            'data': {
                'display_url': 'https://imgbb.com/image.jpg',
                'delete_url': 'https://imgbb.com/delete/abc123',
                'thumb': {'url': 'https://imgbb.com/thumb.jpg'},
                'medium': {'url': 'https://imgbb.com/medium.jpg'},
                'id': 'abc123',
            }
        }
        mock_post.return_value = mock_response
        
        result = service.upload(file)
        
        assert result['success'] is True
        assert result['display_url'] == 'https://imgbb.com/image.jpg'
        assert result['delete_url'] == 'https://imgbb.com/delete/abc123'
        assert result['thumb_url'] == 'https://imgbb.com/thumb.jpg'
        assert result['medium_url'] == 'https://imgbb.com/medium.jpg'
        assert result['id'] == 'abc123'

    @patch('apps.core.utils.imgbb.requests.post')
    def test_upload_failure(self, mock_post):
        """Test failed image upload."""
        service = ImgBBService(api_key='test-key')
        file = SimpleUploadedFile("test.jpg", b"fake-image", content_type="image/jpeg")
        
        mock_post.side_effect = Exception("Network error")
        
        result = service.upload(file)
        
        assert result['success'] is False
        assert 'Upload failed' in result['error']

    @patch('apps.core.utils.imgbb.requests.get')
    def test_delete_success(self, mock_get):
        """Test successful image deletion."""
        service = ImgBBService(api_key='test-key')
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = service.delete('https://imgbb.com/delete/abc123')
        
        assert result is True
        mock_get.assert_called_once_with('https://imgbb.com/delete/abc123', timeout=10)

    @patch('apps.core.utils.imgbb.requests.get')
    def test_delete_failure(self, mock_get):
        """Test failed image deletion."""
        service = ImgBBService(api_key='test-key')
        
        mock_get.side_effect = Exception("Network error")
        
        result = service.delete('https://imgbb.com/delete/abc123')
        
        assert result is False

    def test_delete_no_url(self):
        """Test delete with empty URL returns False."""
        service = ImgBBService(api_key='test-key')
        result = service.delete('')
        assert result is False
        result = service.delete(None)
        assert result is False


class TestGetImgBBService:
    """Tests for get_imgbb_service helper."""

    def test_returns_configured_service(self):
        """Test helper returns configured service."""
        with patch('apps.core.utils.imgbb.settings') as mock_settings:
            mock_settings.IMGBB_API_KEY = 'env-key'
            from apps.core.utils.imgbb import get_imgbb_service
            service = get_imgbb_service()
            assert service.api_key == 'env-key'