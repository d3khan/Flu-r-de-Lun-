"""
Tests for inventory management app.
"""
import os
from decimal import Decimal

import pytest
from django.urls import reverse
from django.test import Client

from apps.products.models import Product, Category, ProductImage


pytestmark = pytest.mark.django_db


class TestInventoryAuth:
    """Tests for session-based auth on inventory views."""

    def test_inventory_access_denied_without_credentials(self, client, monkeypatch):
        """Test that inventory views redirect to login without auth."""
        # Remove any existing credentials
        monkeypatch.delenv('INVENTORY_USERNAME', raising=False)
        monkeypatch.delenv('INVENTORY_PASSWORD', raising=False)
        response = client.get(reverse('inventory:dashboard'))
        assert response.status_code == 403
        assert b'Inventory access not configured' in response.content

    def test_inventory_redirects_to_login_when_not_authenticated(self, client, monkeypatch):
        """Test that inventory views redirect to login when not authenticated."""
        monkeypatch.setenv('INVENTORY_USERNAME', 'testuser')
        monkeypatch.setenv('INVENTORY_PASSWORD', 'testpass')

        response = client.get(reverse('inventory:dashboard'))
        assert response.status_code == 302
        assert reverse('inventory:login') in response.url

    def test_login_page_loads(self, client, monkeypatch):
        """Test that login page loads correctly."""
        monkeypatch.setenv('INVENTORY_USERNAME', 'testuser')
        monkeypatch.setenv('INVENTORY_PASSWORD', 'testpass')

        response = client.get(reverse('inventory:login'))
        assert response.status_code == 200
        assert b'Sign In' in response.content
        assert b'Inventory' in response.content

    def test_login_success(self, client, monkeypatch):
        """Test successful login creates session."""
        monkeypatch.setenv('INVENTORY_USERNAME', 'testuser')
        monkeypatch.setenv('INVENTORY_PASSWORD', 'testpass')

        # Post login credentials
        response = client.post(reverse('inventory:login'), {
            'username': 'testuser',
            'password': 'testpass'
        })
        assert response.status_code == 302
        assert response.url == reverse('inventory:dashboard')
        assert client.session.get('inventory_authenticated') is True

    def test_login_failure(self, client, monkeypatch):
        """Test failed login shows error."""
        monkeypatch.setenv('INVENTORY_USERNAME', 'testuser')
        monkeypatch.setenv('INVENTORY_PASSWORD', 'testpass')

        response = client.post(reverse('inventory:login'), {
            'username': 'wrong',
            'password': 'wrong'
        })
        assert response.status_code == 200
        assert b'Invalid username or password' in response.content
        assert client.session.get('inventory_authenticated') is not True

    def test_logout_clears_session(self, client, monkeypatch):
        """Test logout clears session."""
        monkeypatch.setenv('INVENTORY_USERNAME', 'testuser')
        monkeypatch.setenv('INVENTORY_PASSWORD', 'testpass')

        # Login first
        client.post(reverse('inventory:login'), {
            'username': 'testuser',
            'password': 'testpass'
        })
        assert client.session.get('inventory_authenticated') is True

        # Logout
        response = client.post(reverse('inventory:logout'))
        assert response.status_code == 302
        assert response.url == reverse('inventory:login')
        assert client.session.get('inventory_authenticated') is not True

    def test_already_authenticated_redirects_to_dashboard(self, client, monkeypatch):
        """Test that authenticated users accessing login page get redirected."""
        monkeypatch.setenv('INVENTORY_USERNAME', 'testuser')
        monkeypatch.setenv('INVENTORY_PASSWORD', 'testpass')

        # Login first
        client.post(reverse('inventory:login'), {
            'username': 'testuser',
            'password': 'testpass'
        })

        # Try to access login page again
        response = client.get(reverse('inventory:login'))
        assert response.status_code == 302
        assert response.url == reverse('inventory:dashboard')


class TestInventoryDashboard:
    """Tests for inventory dashboard view."""

    def test_dashboard_loads_with_products(self, auth_client, product):
        """Test dashboard loads with product statistics."""
        response = auth_client.get(reverse('inventory:dashboard'))
        assert response.status_code == 200
        assert b'Inventory Dashboard' in response.content
        assert product.name.encode() in response.content

    def test_dashboard_shows_correct_stats(self, auth_client, product, category):
        """Test dashboard statistics are correct."""
        # Create more products for testing with explicit SKUs
        Product.objects.create(
            name='Test Product 2',
            slug='test-product-2',
            sku='TEST-PROD-2',
            price=Decimal('100.00'),
            stock_quantity=0,
            is_active=True
        )
        Product.objects.create(
            name='Test Product 3',
            slug='test-product-3',
            sku='TEST-PROD-3',
            price=Decimal('50.00'),
            stock_quantity=3,
            low_stock_threshold=5,
            is_active=True
        )

        response = auth_client.get(reverse('inventory:dashboard'))
        assert response.status_code == 200

        # Check stats are present
        content = response.content.decode()
        assert 'Total Products' in content
        assert '3' in content  # total products
        assert 'Low Stock' in content
        assert 'Out of Stock' in content


class TestProductList:
    """Tests for product list view."""

    def test_product_list_loads(self, auth_client, product):
        """Test product list page loads."""
        response = auth_client.get(reverse('inventory:product_list'))
        assert response.status_code == 200
        assert b'Products' in response.content
        assert product.name.encode() in response.content

    def test_product_list_search(self, auth_client, product):
        """Test product list search functionality."""
        Product.objects.create(
            name='Another Product',
            slug='another-product',
            sku='ANOTHER-PROD',
            price=Decimal('200.00'),
            stock_quantity=10,
        )

        response = auth_client.get(reverse('inventory:product_list'), {'q': 'Test'})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Test Product' in content
        assert 'Another Product' not in content

    def test_product_list_filter_by_category(self, auth_client, product, category):
        """Test product list filtering by category."""
        other_category = Category.objects.create(name='Other', slug='other')
        Product.objects.create(
            name='Other Category Product',
            slug='other-category-product',
            sku='OTHER-CAT-PROD',
            price=Decimal('300.00'),
            stock_quantity=5,
            category=other_category
        )

        response = auth_client.get(reverse('inventory:product_list'), {'category': category.pk})
        assert response.status_code == 200
        content = response.content.decode()
        assert product.name in content
        assert 'Other Category Product' not in content

    def test_product_list_filter_by_stock_status(self, auth_client):
        """Test product list filtering by stock status."""
        Product.objects.create(name='In Stock', slug='in-stock', sku='IN-STOCK', price=Decimal('100'), stock_quantity=10, low_stock_threshold=5)
        Product.objects.create(name='Low Stock', slug='low-stock', sku='LOW-STOCK', price=Decimal('100'), stock_quantity=3, low_stock_threshold=5)
        Product.objects.create(name='Out of Stock', slug='out-of-stock', sku='OUT-STOCK', price=Decimal('100'), stock_quantity=0)

        response = auth_client.get(reverse('inventory:product_list'), {'stock_status': 'low_stock'})
        assert response.status_code == 200
        content = response.content.decode()
        # Check only the product table body (tbody) for "Low Stock" product name
        tbody_start = content.find('<tbody>')
        tbody_end = content.find('</tbody>')
        tbody_content = content[tbody_start:tbody_end]
        assert 'Low Stock' in tbody_content
        assert 'In Stock' not in tbody_content
        assert 'Out of Stock' not in tbody_content

    def test_product_list_pagination(self, auth_client):
        """Test product list pagination."""
        for i in range(25):
            Product.objects.create(
                name=f'Product {i}',
                slug=f'product-{i}',
                sku=f'PROD-{i}',
                price=Decimal('100.00'),
                stock_quantity=5,
            )

        response = auth_client.get(reverse('inventory:product_list'))
        assert response.status_code == 200
        # Should show pagination
        assert b'pagination' in response.content.lower() or b'page' in response.content.lower()


class TestProductCreate:
    """Tests for product create view."""

    def test_product_create_get(self, auth_client, category):
        """Test GET product create page."""
        response = auth_client.get(reverse('inventory:product_create'))
        assert response.status_code == 200
        assert b'Add New Product' in response.content

    def test_product_create_post_valid(self, auth_client, category):
        """Test POST valid product creation."""
        data = {
            'name': 'New Product',
            'slug': 'new-product',
            'category': category.pk,
            'description': 'Test description',
            'price': '199.99',
            'stock_quantity': '10',
            'low_stock_threshold': '5',
            'weight': '0.5',
            'is_active': True,
        }
        response = auth_client.post(reverse('inventory:product_create'), data)
        assert response.status_code == 302  # redirect on success
        assert Product.objects.filter(name='New Product').exists()

    def test_product_create_post_invalid(self, auth_client):
        """Test POST invalid product creation (missing required fields)."""
        data = {
            'name': '',  # Required field missing
            'price': 'invalid',
        }
        response = auth_client.post(reverse('inventory:product_create'), data)
        assert response.status_code == 200  # form re-rendered with errors
        assert b'This field is required' in response.content or b'required' in response.content.lower()


class TestProductEdit:
    """Tests for product edit view."""

    def test_product_edit_get(self, auth_client, product):
        """Test GET product edit page."""
        response = auth_client.get(reverse('inventory:product_edit', kwargs={'pk': product.pk}))
        assert response.status_code == 200
        assert b'Edit Product' in response.content
        assert product.name.encode() in response.content

    def test_product_edit_post_valid(self, auth_client, product):
        """Test POST valid product update."""
        data = {
            'name': 'Updated Product',
            'slug': 'updated-product',
            'category': product.category.pk,
            'description': 'Updated description',
            'price': '299.99',
            'stock_quantity': '20',
            'low_stock_threshold': '5',
            'weight': '0.8',
            'is_active': True,
        }
        response = auth_client.post(
            reverse('inventory:product_edit', kwargs={'pk': product.pk}),
            data
        )
        assert response.status_code == 302
        product.refresh_from_db()
        assert product.name == 'Updated Product'
        assert product.price == Decimal('299.99')

    def test_product_edit_404(self, auth_client):
        """Test edit non-existent product returns 404."""
        response = auth_client.get(reverse('inventory:product_edit', kwargs={'pk': 99999}))
        assert response.status_code == 404


class TestProductDelete:
    """Tests for product delete view."""

    def test_product_delete_get(self, auth_client, product):
        """Test GET product delete confirmation page."""
        response = auth_client.get(reverse('inventory:product_delete', kwargs={'pk': product.pk}))
        assert response.status_code == 200
        assert b'Delete Product' in response.content
        assert product.name.encode() in response.content

    def test_product_delete_post(self, auth_client, product):
        """Test POST product deletion."""
        response = auth_client.post(reverse('inventory:product_delete', kwargs={'pk': product.pk}))
        assert response.status_code == 302
        assert not Product.objects.filter(pk=product.pk).exists()


class TestProductStockUpdate:
    """Tests for product stock update view."""

    def test_product_stock_update_get(self, auth_client, product):
        """Test GET stock update page."""
        response = auth_client.get(reverse('inventory:product_stock_update', kwargs={'pk': product.pk}))
        assert response.status_code == 200
        assert b'Update Stock' in response.content
        assert str(product.stock_quantity).encode() in response.content

    def test_product_stock_update_post(self, auth_client, product):
        """Test POST stock update."""
        data = {
            'stock_quantity': '50',
            'low_stock_threshold': '10',
        }
        response = auth_client.post(
            reverse('inventory:product_stock_update', kwargs={'pk': product.pk}),
            data
        )
        assert response.status_code == 302
        product.refresh_from_db()
        assert product.stock_quantity == 50
        assert product.low_stock_threshold == 10

    def test_product_stock_update_htmx(self, auth_client, product):
        """Test HTMX stock update partial."""
        data = {
            'stock_quantity': '75',
            'low_stock_threshold': '15',
        }
        response = auth_client.post(
            reverse('inventory:product_stock_update', kwargs={'pk': product.pk}),
            data,
            HTTP_HX_REQUEST='true'
        )
        assert response.status_code == 200
        # Should return JSON for HTMX
        assert response['Content-Type'] == 'application/json'


class TestCategoryList:
    """Tests for category list view."""

    def test_category_list_loads(self, auth_client, category):
        """Test category list page loads."""
        response = auth_client.get(reverse('inventory:category_list'))
        assert response.status_code == 200
        assert b'Categories' in response.content
        assert category.name.encode() in response.content

    def test_category_list_shows_product_count(self, auth_client, category, product):
        """Test category list shows product count."""
        response = auth_client.get(reverse('inventory:category_list'))
        assert response.status_code == 200
        content = response.content.decode()
        assert '1 product' in content or '1 product' in content


class TestCategoryCreate:
    """Tests for category create view."""

    def test_category_create_get(self, auth_client):
        """Test GET category create page."""
        response = auth_client.get(reverse('inventory:category_create'))
        assert response.status_code == 200
        assert b'Add New Category' in response.content

    def test_category_create_post_valid(self, auth_client):
        """Test POST valid category creation."""
        data = {
            'name': 'New Category',
            'slug': 'new-category',
            'description': 'Category description',
            'is_active': True,
            'sort_order': '1',
        }
        response = auth_client.post(reverse('inventory:category_create'), data)
        assert response.status_code == 302
        assert Category.objects.filter(name='New Category').exists()


class TestCategoryEdit:
    """Tests for category edit view."""

    def test_category_edit_get(self, auth_client, category):
        """Test GET category edit page."""
        response = auth_client.get(reverse('inventory:category_edit', kwargs={'pk': category.pk}))
        assert response.status_code == 200
        assert b'Edit Category' in response.content
        assert category.name.encode() in response.content

    def test_category_edit_post_valid(self, auth_client, category):
        """Test POST valid category update."""
        data = {
            'name': 'Updated Category',
            'slug': 'updated-category',
            'description': 'Updated description',
            'is_active': True,
            'sort_order': '5',
        }
        response = auth_client.post(
            reverse('inventory:category_edit', kwargs={'pk': category.pk}),
            data
        )
        assert response.status_code == 302
        category.refresh_from_db()
        assert category.name == 'Updated Category'
        assert category.sort_order == 5


class TestCategoryDelete:
    """Tests for category delete view."""

    def test_category_delete_get(self, auth_client, category):
        """Test GET category delete confirmation."""
        response = auth_client.get(reverse('inventory:category_delete', kwargs={'pk': category.pk}))
        assert response.status_code == 200
        assert b'Delete Category' in response.content
        assert category.name.encode() in response.content

    def test_category_delete_post(self, auth_client, category):
        """Test POST category deletion."""
        response = auth_client.post(reverse('inventory:category_delete', kwargs={'pk': category.pk}))
        assert response.status_code == 302
        assert not Category.objects.filter(pk=category.pk).exists()

    def test_category_delete_moves_products_to_uncategorized(self, auth_client, category, product):
        """Test that deleting category sets products' category to None."""
        response = auth_client.post(reverse('inventory:category_delete', kwargs={'pk': category.pk}))
        assert response.status_code == 302
        product.refresh_from_db()
        assert product.category is None


# Fixtures
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