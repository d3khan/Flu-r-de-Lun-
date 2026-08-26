from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import ListView, DetailView
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control

import requests
import hashlib
import logging

from .models import Product, Category
from apps.wishlist.utils import annotate_in_wishlist

logger = logging.getLogger(__name__)


class ProductListView(ListView):
    """Product listing with filtering and pagination."""
    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
        queryset = annotate_in_wishlist(queryset, self.request.user)
        
        # Category filter
        category_slug = self.kwargs.get('slug') or self.request.GET.get('category')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug, is_active=True)
            queryset = queryset.filter(category=category)
            self.category = category
        
        # Search
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(sku__icontains=query)
            )
        
        # Sort
        sort = self.request.GET.get('sort', '-created_at')
        sort_options = {
            'newest': '-created_at',
            'oldest': 'created_at',
            'price_asc': 'price',
            'price_desc': '-price',
            'name_asc': 'name',
            'name_desc': '-name',
        }
        queryset = queryset.order_by(sort_options.get(sort, '-created_at'))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True)
        context['current_category'] = getattr(self, 'category', None)
        context['current_sort'] = self.request.GET.get('sort', 'newest')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class ProductDetailView(DetailView):
    """Product detail page."""
    model = Product
    template_name = 'products/detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
        return annotate_in_wishlist(queryset, self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Get sort order from session or default to newest
        sort = self.request.GET.get('sort') or self.request.session.get('product_list_sort', '-created_at')
        sort_options = {
            'name': 'name',
            '-name': '-name',
            'price': 'price',
            '-price': '-price',
            'stock': 'stock_quantity',
            '-stock': '-stock_quantity',
            'created': '-created_at',
            '-created': 'created_at',
            'updated': '-updated_at',
            '-updated': 'updated_at',
        }
        order_by = sort_options.get(sort, '-created_at')
        
        # Get next/prev products in the same category with the same sort order
        category_products = Product.objects.filter(
            category=product.category,
            is_active=True
        ).order_by(order_by).values_list('slug', flat=True)
        
        slug_list = list(category_products)
        current_index = slug_list.index(product.slug) if product.slug in slug_list else -1
        
        next_product = None
        prev_product = None
        
        if current_index >= 0:
            if current_index + 1 < len(slug_list):
                next_slug = slug_list[current_index + 1]
                next_product = Product.objects.filter(slug=next_slug, is_active=True).select_related('category').prefetch_related('images').first()
            if current_index - 1 >= 0:
                prev_slug = slug_list[current_index - 1]
                prev_product = Product.objects.filter(slug=prev_slug, is_active=True).select_related('category').prefetch_related('images').first()
        
        context['next_product'] = next_product
        context['prev_product'] = prev_product
        
        # Related products from same category
        context['related_products'] = annotate_in_wishlist(
            Product.objects.filter(
                category=product.category,
                is_active=True
            ).exclude(id=product.id).prefetch_related('images'),
            self.request.user,
        )[:4]
        
        # Check if in user's wishlist
        if self.request.user.is_authenticated:
            from apps.wishlist.models import WishlistItem
            context['in_wishlist'] = WishlistItem.objects.filter(
                wishlist__user=self.request.user,
                product=product
            ).exists()
        else:
            context['in_wishlist'] = False
        
        return context


def category_detail(request, slug):
    """Category detail page."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    products = annotate_in_wishlist(
        Product.objects.filter(category=category, is_active=True)
        .select_related('category').prefetch_related('images'),
        request.user,
    )
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'products': page_obj,
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'products/category.html', context)


# HTMX partial views

def product_card(request, product_id):
    """Return product card partial for HTMX."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    return render(request, 'products/partials/_product_card.html', {'product': product})


def product_quick_view(request, product_id):
    """Return quick view modal for HTMX."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    return render(request, 'products/partials/_quick_view.html', {'product': product})


def check_stock(request, product_id):
    """AJAX endpoint to check stock status."""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    return JsonResponse({
        'in_stock': product.in_stock,
        'stock_status': product.stock_status,
        'stock_status_display': product.stock_status_display,
        'stock_quantity': product.stock_quantity,
    })


@require_GET
@cache_control(public=True, max_age=31536000, immutable=True)
def image_proxy(request):
    """
    Proxy external images (e.g., ImgBB) through Django to enable browser caching.
    
    Usage: /products/image-proxy/?url=<encoded_url>&w=<width>&h=<height>
    
    The URL is validated to only allow known external hosts (ImgBB).
    """
    external_url = request.GET.get('url')
    if not external_url:
        return HttpResponseBadRequest('Missing url parameter')
    
    # Validate URL - only allow known safe hosts
    allowed_hosts = ['ibb.co', 'i.ibb.co', 'imgbb.com']
    try:
        from urllib.parse import urlparse
        parsed = urlparse(external_url)
        if parsed.netloc not in allowed_hosts:
            logger.warning(f"Image proxy blocked non-allowed host: {parsed.netloc}")
            return HttpResponseBadRequest('Host not allowed')
    except Exception:
        return HttpResponseBadRequest('Invalid URL')
    
    # Optional size parameters for future image optimization
    width = request.GET.get('w')
    height = request.GET.get('h')
    
    # Generate cache key from URL
    cache_key = hashlib.md5(external_url.encode()).hexdigest()
    
    # Check if we have a cached version (using session as simple cache)
    # In production, use Redis or database caching
    cached = request.session.get(f'img_proxy_{cache_key}')
    if cached and not request.GET.get('refresh'):
        # We can't easily serve cached binary from session, so just proxy again
        pass
    
    try:
        # Fetch from external host with timeout
        response = requests.get(external_url, timeout=10, stream=True)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        
        # Validate content type
        allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif', 'image/heic', 'image/heif']
        if content_type not in allowed_types:
            logger.warning(f"Image proxy blocked non-image content-type: {content_type}")
            return HttpResponseBadRequest('Invalid content type')
        
        # Stream response to avoid loading full image in memory
        django_response = HttpResponse(
            response.iter_content(chunk_size=8192),
            content_type=content_type
        )
        
        # Set cache headers - 1 year, immutable
        django_response['Cache-Control'] = 'public, max-age=31536000, immutable'
        django_response['Content-Length'] = response.headers.get('Content-Length', '')
        
        return django_response
        
    except requests.Timeout:
        logger.error(f"Image proxy timeout for {external_url}")
        return HttpResponseBadRequest('Image fetch timeout')
    except requests.RequestException as e:
        logger.error(f"Image proxy error for {external_url}: {e}")
        return HttpResponseBadRequest('Failed to fetch image')