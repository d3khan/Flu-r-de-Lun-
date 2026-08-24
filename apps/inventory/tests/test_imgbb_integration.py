"""
Tests for inventory views with ImgBB integration.
"""
import base64
from decimal import Decimal
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from django.urls import reverse
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.products.models import Product, Category, ProductImage
from apps.core.utils.imgbb import ImgBBService


pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def auth_client(client, monkeypatch):
    """Authenticated client with session-based auth."""
    monkeypatch.setenv('INVENTORY_USERNAME', 'testuser')
    monkeypatch.setenv('INVENTORY_PASSWORD', 'testpass')
    client.post(reverse('inventory:login'), {
        'username': 'testuser',
        'password': 'testpass'
    })
    return client


@pytest.fixture
def category():
    """Create a test category."""
    return Category.objects.create(
        name='Test Category',
        slug='test-category',
        description='Test category description',
        is_active=True,
        sort_order=1
    )


@pytest.fixture
def product(category):
    """Create a test product."""
    return Product.objects.create(
        name='Test Product',
        slug='test-product',
        category=category,
        description='Test product description',
        price=Decimal('150.00'),
        compare_at_price=Decimal('200.00'),
        stock_quantity=10,
        low_stock_threshold=5,
        weight=Decimal('0.5'),
        is_active=True,
        is_featured=False,
        is_new_arrival=False,
        is_bestseller=False,
    )


class TestImgBBServiceIntegration:
    """Tests for ImgBB service integration with inventory views."""

    def test_imgbb_service_upload(self, monkeypatch):
        """Test ImgBB service upload with mocked requests."""
        monkeypatch.setenv('IMGBB_API_KEY', 'test-key')
        
        service = ImgBBService(api_key='test-key')
        file = SimpleUploadedFile("test.jpg", b"fake-image", content_type="image/jpeg")
        
        with patch('apps.core.utils.imgbb.requests.post') as mock_post:
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
            mock_post.return_value = Mock()
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.json.return_value = {
                'success': True,
                'data': {
                    'display_url': 'https://imgbb.com/image.jpg',
                    'delete_url': 'https://imgbb.com/delete/abc123',
                    'thumb': {'url': 'https://imgbb.com/thumb.jpg'},
                    'medium': {'url': 'https://imgbb.com/medium.jpg'},
                    'id': 'abc123',
                }
            }
            
            result = service.upload(file)
            
            assert result['success'] is True
            assert result['display_url'] == 'https://imgbb.com/image.jpg'
            assert result['delete_url'] == 'https://imgbb.com/delete/abc123'


class TestInventoryImgBBIntegration:
    """Tests for inventory views with ImgBB integration."""

    def test_product_create_with_imgbb_upload(self, auth_client, category, monkeypatch):
        """Test product creation with ImgBB image upload."""
        monkeypatch.setenv('IMGBB_API_KEY', 'test-key')
        
        with patch('apps.inventory.views.get_imgbb_service') as mock_get_service:
            mock_service = Mock()
            mock_service.upload.return_value = {
                'success': True,
                'display_url': 'https://imgbb.com/image.jpg',
                'delete_url': 'https://imgbb.com/delete/abc123',
                'thumb_url': 'https://imgbb.com/thumb.jpg',
                'medium_url': 'https://imgbb.com/medium.jpg',
                'id': 'abc123',
            }
            mock_get_service.return_value = mock_service
            
            # Create a valid JPEG test image
            img = Image.new('RGB', (10, 10), color='red')
            buffer = BytesIO()
            img.save(buffer, format='JPEG')
            image_content = buffer.getvalue()
            image = SimpleUploadedFile("test.jpg", image_content, content_type="image/jpeg")
            
            data = {
                'name': 'Test Product with Image',
                'slug': 'test-product-with-image',
                'category': category.pk,
                'description': 'Test description',
                'price': '199.99',
                'stock_quantity': '10',
                'low_stock_threshold': '5',
                'weight': '0.5',
                'is_active': True,
            }
            
            # Include the image in the POST data for multipart form
            post_data = data.copy()
            post_data['primary_image'] = image
            response = auth_client.post(reverse('inventory:product_create'), post_data, HTTP_AUTHORIZATION='Basic dGVzdHVzZXI6dGVzdHBhc3M=')
            
            # Should redirect on success
            assert response.status_code == 302
            assert Product.objects.filter(name='Test Product with Image').exists()
            
            # Verify product image was created with ImgBB data
            product = Product.objects.get(name='Test Product with Image')
            primary_image = product.images.filter(is_primary=True).first()
            assert primary_image is not None
            assert primary_image.imgbb_delete_url == 'https://imgbb.com/delete/abc123'
            assert primary_image.imgbb_id == 'abc123'

    def test_product_edit_with_imgbb_upload(self, auth_client, product, category, monkeypatch):
        """Test product edit with new primary image upload to ImgBB."""
        monkeypatch.setenv('IMGBB_API_KEY', 'test-key')
        
        with patch('apps.inventory.views.get_imgbb_service') as mock_get_service:
            mock_service = Mock()
            mock_service.upload.return_value = {
                'success': True,
                'display_url': 'https://imgbb.com/new-image.jpg',
                'delete_url': 'https://imgbb.com/delete/new123',
                'thumb_url': 'https://imgbb.com/thumb_new.jpg',
                'medium_url': 'https://imgbb.com/medium_new.jpg',
                'id': 'new123',
            }
            mock_service.delete.return_value = True
            mock_get_service.return_value = mock_service
            
            # Create a valid JPEG test image
            img = Image.new('RGB', (10, 10), color='blue')
            buffer = BytesIO()
            img.save(buffer, format='JPEG')
            image_content = buffer.getvalue()
            image = SimpleUploadedFile("new.jpg", image_content, content_type="image/jpeg")
            
            data = {
                'name': 'Updated Product',
                'slug': 'updated-product',
                'category': category.pk,
                'description': 'Updated description',
                'price': '299.99',
                'stock_quantity': '20',
                'low_stock_threshold': '5',
                'weight': '0.8',
                'is_active': True,
            }
            
            post_data = data.copy()
            post_data['primary_image'] = image
            response = auth_client.post(
                reverse('inventory:product_edit', kwargs={'pk': product.pk}),
                post_data,
                HTTP_AUTHORIZATION='Basic dGVzdHVzZXI6dGVzdHBhc3M='
            )
            
            assert response.status_code == 302
            product.refresh_from_db()
            assert product.name == 'Updated Product'
            
            # Check new primary image was created with ImgBB data
            primary_image = product.images.filter(is_primary=True).first()
            assert primary_image is not None
            assert primary_image.imgbb_id == 'new123'
            assert primary_image.imgbb_delete_url == 'https://imgbb.com/delete/new123'