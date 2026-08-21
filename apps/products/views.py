from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import ListView, DetailView
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

from .models import Product, Category


class ProductListView(ListView):
    """Product listing with filtering and pagination."""
    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
        
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
        return Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Related products from same category
        context['related_products'] = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(id=product.id).prefetch_related('images')[:4]
        
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
    products = Product.objects.filter(category=category, is_active=True).select_related('category').prefetch_related('images')
    
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