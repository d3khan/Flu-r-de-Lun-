"""
ImgBB service for image upload and deletion.

API v1 reference (https://api.imgbb.com/):
- POST multipart/form-data with `image` as a binary file is the recommended
  way to upload local files.
- The response exposes: id, url (original), display_url, thumb.url,
  medium.url and delete_url.

Nothing is ever stored on the local filesystem — callers persist only the
URLs returned here.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ImgBBService:
    """Service for uploading and deleting images via the ImgBB API."""

    UPLOAD_URL = "https://api.imgbb.com/1/upload"
    TIMEOUT = 60  # generous: free-tier egress can be slow
    # ibb.co sits behind Cloudflare; bare server user-agents frequently get
    # challenged (HTTP 403) on delete URLs. Send a browser-like UA.
    REQUEST_HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, 'IMGBB_API_KEY', None)

    def upload(self, file, name=None) -> dict:
        """
        Upload an image file to ImgBB via multipart/form-data.

        Args:
            file: A Django UploadedFile (or any file-like object).
            name: Optional friendly filename/title sent to ImgBB; falls back
                  to the uploaded file's own name.

        Returns:
            dict with keys:
                success (bool)
                url         - original full-size image URL
                display_url - resized display copy
                thumb_url   - small thumbnail
                medium_url  - medium resize
                delete_url  - URL that removes the image from ImgBB
                id          - ImgBB image id
                error       - failure reason (when success is False)
        """
        if not self.api_key:
            logger.error("ImgBB upload skipped: IMGBB_API_KEY is not configured.")
            return {'success': False, 'error': 'IMGBB_API_KEY not configured'}

        try:
            # Read the whole payload once so it can be sent as binary
            # multipart data (recommended over base64/urlencoded bodies).
            content = file.read()
            try:
                file.seek(0)
            except (AttributeError, OSError, ValueError):
                pass

            filename = name or getattr(file, 'name', None) or 'upload.jpg'
            content_type = getattr(file, 'content_type', '') or 'application/octet-stream'

            response = requests.post(
                self.UPLOAD_URL,
                params={'key': self.api_key},
                files={'image': (filename, content, content_type)},
                headers=self.REQUEST_HEADERS,
                timeout=self.TIMEOUT,
            )
            if response.status_code != 200:
                logger.warning(
                    "ImgBB upload failed with HTTP %s for %r: %s",
                    response.status_code, filename, response.text[:300],
                )
            response.raise_for_status()

            result = response.json()

            if result.get('success'):
                data = result.get('data') or {}
                thumb = data.get('thumb') or {}
                medium = data.get('medium') or {}
                return {
                    'success': True,
                    'url': data.get('url'),
                    'display_url': data.get('display_url'),
                    'thumb_url': thumb.get('url'),
                    'medium_url': medium.get('url'),
                    'delete_url': data.get('delete_url'),
                    'id': data.get('id'),
                }

            error = result.get('error')
            message = error.get('message') if isinstance(error, dict) else (error or 'Unknown ImgBB error')
            logger.warning("ImgBB rejected upload for %r: %s", filename, message)
            return {'success': False, 'error': message}

        except requests.exceptions.RequestException as e:
            logger.exception("ImgBB upload network error")
            return {'success': False, 'error': f'Network error: {e}'}
        except Exception as e:
            logger.exception("ImgBB upload unexpectedly failed")
            return {'success': False, 'error': f'Upload failed: {e}'}

    def delete(self, delete_url: str) -> bool:
        """
        Delete an image from ImgBB using its delete URL.

        Returns True when the request completed with HTTP 200. Failures are
        logged (with status code and a response snippet) so they are visible
        in production logs instead of silently leaving orphaned images.
        """
        if not delete_url:
            return False

        try:
            response = requests.get(
                delete_url, timeout=15, headers=self.REQUEST_HEADERS
            )
            if response.status_code != 200:
                logger.warning(
                    "ImgBB delete URL %s returned HTTP %s (body: %.300r)",
                    delete_url, response.status_code, response.text,
                )
                return False
            logger.info("ImgBB delete URL %s -> HTTP 200", delete_url)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            logger.exception("ImgBB deletion failed for %s", delete_url)
            return False
        except Exception:
            logger.exception("Unexpected error deleting ImgBB image %s", delete_url)
            return False


# Convenience function for easy import
def get_imgbb_service():
    """Get configured ImgBB service instance."""
    return ImgBBService()
