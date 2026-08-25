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
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Accepted upload formats (ImgBB-supported AND Pillow-verifiable).
ALLOWED_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.tiff')
ALLOWED_IMAGE_HELP_TEXT = 'Accepted: JPG, JPEG, PNG, GIF, WEBP, BMP or TIFF'


def image_extension_allowed(filename: str) -> bool:
    """True when the filename's extension is one ImgBB supports."""
    if not filename:
        return False
    name = filename.lower()
    return any(name.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS)


class ImgBBService:
    """Service for uploading and deleting images via the ImgBB API."""

    UPLOAD_URL = "https://api.imgbb.com/1/upload"
    TIMEOUT = 60  # generous: free-tier egress can be slow
    DELETE_MAX_ATTEMPTS = 4
    DELETE_RETRY_PAUSE = 1.0  # seconds; 3 pauses max => well under the 5s budget
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
                # ImgBB omits thumb/medium for formats it does not resize
                # (e.g. GIFs) and can return nulls - coerce everything to ''
                # so NOT NULL database columns are never fed None.
                return {
                    'success': True,
                    'url': data.get('url') or '',
                    'display_url': data.get('display_url') or '',
                    'thumb_url': thumb.get('url') or '',
                    'medium_url': medium.get('url') or '',
                    'delete_url': data.get('delete_url') or '',
                    'id': data.get('id') or '',
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


    def is_alive(self, image_url: str) -> bool:
        """True when the image URL still resolves to a fetchable resource."""
        if not image_url:
            return False
        try:
            response = requests.get(
                image_url, headers=self.REQUEST_HEADERS,
                timeout=15, stream=True,
            )
            alive = response.status_code == 200
            logger.info("ImgBB liveness probe %s -> HTTP %s (alive=%s)",
                        image_url, response.status_code, alive)
            return alive
        except requests.exceptions.RequestException:
            # Unreachable / 404 => treat as gone.
            logger.info("ImgBB liveness probe %s -> unreachable (treated as deleted)",
                        image_url)
            return False

    def delete_verified(self, delete_url: str, image_url: str = '') -> bool:
        """
        Delete an image and CONFIRM it is really gone.

        Algorithm:
          1. Hit the delete URL.
          2. Probe the original image URL - if it still resolves to a valid
             image, the deletion did not take effect yet: retry, up to
             DELETE_MAX_ATTEMPTS times.
          3. Once the probe reports the image is gone, the caller can safely
             clear every stored reference.

        Returns True once deletion is confirmed; False after exhausting the
        attempts (references should then be KEPT so a later retry can run).
        Total pause budget across attempts stays under 5 seconds.
        """
        if not delete_url:
            return False

        for attempt in range(1, self.DELETE_MAX_ATTEMPTS + 1):
            request_ok = self.delete(delete_url)

            if request_ok and not self.is_alive(image_url):
                logger.info(
                    "ImgBB image confirmed deleted on attempt %d/%d (%s)",
                    attempt, self.DELETE_MAX_ATTEMPTS, delete_url,
                )
                return True

            if attempt < self.DELETE_MAX_ATTEMPTS:
                time.sleep(self.DELETE_RETRY_PAUSE)

        logger.error(
            "ImgBB image still reachable after %d deletion attempts - "
            "keeping references for retry. delete_url=%s image_url=%s",
            self.DELETE_MAX_ATTEMPTS, delete_url, image_url,
        )
        return False


# Convenience function for easy import
def get_imgbb_service():
    """Get configured ImgBB service instance."""
    return ImgBBService()
