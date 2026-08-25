"""
Views for inventory management.
"""
import os
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q, Count, F
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django.conf import settings

logger = logging.getLogger(__name__)

from apps.products.models import Product, Category, ProductImage
from apps.core.utils.imgbb import get_imgbb_service
from .forms import ProductForm, ProductStockForm, CategoryForm, ProductImageForm


# --- ImgBB helpers ---------------------------------------------------------

def _imgbb_field_map(result):
    """Map an ImgBBService.upload() result to this project's field names.

    Values are coerced to '' (never None) because the ImgBB URL columns are
    NOT NULL at the database level.
    """
    return {key: value or '' for key, value in dict(
        imgbb_delete_url=result.get('delete_url'),
        imgbb_id=result.get('id'),
        imgbb_url=result.get('url'),
        imgbb_display_url=result.get('display_url'),
        imgbb_thumb_url=result.get('thumb_url'),
        imgbb_medium_url=result.get('medium_url'),
    ).items()}


def _create_product_image(product, uploaded_file, is_primary, sort_order, alt_text):
    """Upload one image to ImgBB and store only its URLs for a product.

    Returns the service result dict so callers can warn on failure.
    Nothing is written to the local filesystem.
    """
    # Increment counter for unique ImgBB name
    product.image_upload_counter = F('image_upload_counter') + 1
    product.save(update_fields=['image_upload_counter'])
    product.refresh_from_db()
    
    # Generate unique name: product name + counter
    unique_name = f"{alt_text} ({product.image_upload_counter})"
    
    result = get_imgbb_service().upload(uploaded_file, name=unique_name)
    if not result['success']:
        return result
    ProductImage.objects.create(
        product=product,
        is_primary=is_primary,
        sort_order=sort_order,
        alt_text=alt_text,
        **_imgbb_field_map(result),
    )
    return result


IMGBB_REF_FIELDS = (
    'imgbb_delete_url', 'imgbb_id', 'imgbb_url',
    'imgbb_display_url', 'imgbb_thumb_url', 'imgbb_medium_url',
)


def _clear_imgbb_refs(obj):
    """Wipe every ImgBB reference field on a model instance."""
    for field in IMGBB_REF_FIELDS:
        setattr(obj, field, '')
    obj.save(update_fields=list(IMGBB_REF_FIELDS))


def _remove_product_image(image_row, delete_from_imgbb=True):
    """Remove a ProductImage and optionally its remote ImgBB copy.

    Args:
        image_row: The ProductImage instance to remove
        delete_from_imgbb: If True, attempt to delete from ImgBB. If False,
            only delete the database row (keep ImgBB image).

    Returns:
        Tuple of (db_deleted, imgbb_deleted) where:
        - db_deleted: True if database row was deleted
        - imgbb_deleted: True if ImgBB deletion was confirmed
    """
    service = get_imgbb_service()
    imgbb_deleted = False

    if delete_from_imgbb and image_row.imgbb_delete_url:
        # Try to delete from ImgBB (verified), but don't block DB deletion on failure
        imgbb_deleted = service.delete_verified(
            image_row.imgbb_delete_url,
            image_row.large_url or image_row.imgbb_display_url,
        )
        if not imgbb_deleted:
            logger.warning(
                "ImgBB deletion not confirmed for image %s (delete_url=%s), "
                "but removing database row as requested",
                image_row.pk, image_row.imgbb_delete_url
            )
    elif not delete_from_imgbb:
        # User chose not to delete from ImgBB - just clear the references
        logger.info("Keeping ImgBB image for ProductImage %s (user choice)", image_row.pk)

    # Always delete the database row when removal is requested
    image_row.delete()
    return True, imgbb_deleted


def _apply_imgbb_to_category(category, result):
    """Persist an ImgBB upload result onto a Category instance."""
    for field, value in _imgbb_field_map(result).items():
        setattr(category, field, value)
    category.save(update_fields=list(_imgbb_field_map(result).keys()))


def _remove_category_image(category, delete_remote=True):
    """Remove a category's remote ImgBB copy (verified when deleting).

    Returns False when remote deletion could not be confirmed - references
    are then kept so the purge can be retried later.
    """
    service = get_imgbb_service()
    purged = True
    if delete_remote and category.imgbb_delete_url:
        purged = service.delete_verified(
            category.imgbb_delete_url,
            category.image_url or category.imgbb_display_url,
        )
    if purged or not delete_remote:
        for field in IMGBB_REF_FIELDS:
            setattr(category, field, '')
        category.save(update_fields=list(IMGBB_REF_FIELDS))
    return purged


def _warn_imgbb_failure(request, label, result):
    messages.warning(request, _('Failed to upload %(label)s to ImgBB: %(error)s') % {
        'label': label,
        'error': result.get('error', 'Unknown error'),
    })


def inventory_login_required(view_func):
    """
    Decorator for session-based auth for inventory views.
    Uses INVENTORY_USERNAME and INVENTORY_PASSWORD from environment.
    Stores auth in session (expires on browser close).
    """
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if credentials are configured
        inventory_username = os.environ.get('INVENTORY_USERNAME')
        inventory_password = os.environ.get('INVENTORY_PASSWORD')

        if not inventory_username or not inventory_password:
            return HttpResponseForbidden(_('Inventory access not configured.'))

        # Check if user is authenticated in session
        if not request.session.get('inventory_authenticated'):
            return redirect('inventory:login')

        return view_func(request, *args, **kwargs)

    return wrapper


@csrf_protect
def inventory_login(request):
    """Login page for inventory management."""
    # If already authenticated, redirect to dashboard
    if request.session.get('inventory_authenticated'):
        return redirect('inventory:dashboard')

    inventory_username = os.environ.get('INVENTORY_USERNAME')
    inventory_password = os.environ.get('INVENTORY_PASSWORD')

    if not inventory_username or not inventory_password:
        return HttpResponseForbidden(_('Inventory access not configured.'))

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if username == inventory_username and password == inventory_password:
            # Set session with expiry on browser close (0 = session cookie)
            request.session['inventory_authenticated'] = True
            request.session.set_expiry(0)  # Expires when browser closes
            messages.success(request, _('Welcome to Inventory Management.'))
            return redirect('inventory:dashboard')
        else:
            messages.error(request, _('Invalid username or password.'))

    return render(request, 'inventory/login.html', {
        'title': _('Inventory Login'),
    })


def inventory_logout(request):
    """Logout from inventory management."""
    request.session.flush()
    messages.success(request, _('You have been logged out.'))
    return redirect('inventory:login')


@inventory_login_required
def inventory_dashboard(request):
    """Inventory dashboard with product overview."""
    # Get statistics
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    out_of_stock = Product.objects.filter(stock_quantity=0).count()
    low_stock = Product.objects.filter(
        stock_quantity__gt=0,
        stock_quantity__lte=models.F('low_stock_threshold')
    ).count()
    total_categories = Category.objects.count()
    total_value = Product.objects.aggregate(
        total=models.Sum(models.F('price') * models.F('stock_quantity'))
    )['total'] or 0

    # Recent products
    recent_products = Product.objects.select_related('category').prefetch_related('images').order_by('-created_at')[:10]

    # Low stock products
    low_stock_products = Product.objects.filter(
        stock_quantity__gt=0,
        stock_quantity__lte=models.F('low_stock_threshold')
    ).select_related('category').prefetch_related('images').order_by('stock_quantity')[:10]

    # Out of stock products
    out_of_stock_products = Product.objects.filter(
        stock_quantity=0,
        is_active=True
    ).select_related('category').prefetch_related('images').order_by('-updated_at')[:10]

    context = {
        'total_products': total_products,
        'active_products': active_products,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'total_categories': total_categories,
        'total_value': total_value,
        'recent_products': recent_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
    }
    return render(request, 'inventory/dashboard.html', context)


@inventory_login_required
def product_list(request):
    """List all products with filtering and search."""
    queryset = Product.objects.select_related('category').prefetch_related('images').order_by('-created_at')

    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # Stock status filter
    stock_status = request.GET.get('stock_status')
    if stock_status == 'out_of_stock':
        queryset = queryset.filter(stock_quantity=0)
    elif stock_status == 'low_stock':
        queryset = queryset.filter(
            stock_quantity__gt=0,
            stock_quantity__lte=models.F('low_stock_threshold')
        )
    elif stock_status == 'in_stock':
        queryset = queryset.filter(stock_quantity__gt=models.F('low_stock_threshold'))

    # Active filter
    is_active = request.GET.get('is_active')
    if is_active == 'true':
        queryset = queryset.filter(is_active=True)
    elif is_active == 'false':
        queryset = queryset.filter(is_active=False)

    # Sorting
    sort = request.GET.get('sort', '-created_at')
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
    queryset = queryset.order_by(sort_options.get(sort, '-created_at'))

    # Pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Categories for filter dropdown
    categories = Category.objects.filter(is_active=True).order_by('name')

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'current_category': category_id,
        'current_stock_status': stock_status,
        'current_is_active': is_active,
        'current_sort': sort,
    }
    return render(request, 'inventory/product_list.html', context)


@inventory_login_required
def product_create(request):
    """Create a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()

            # Primary image -> uploaded to ImgBB and stored as primary
            primary_image = request.FILES.get('primary_image')
            if primary_image:
                result = _create_product_image(product, primary_image, True, 0, product.name)
                if not result['success']:
                    _warn_imgbb_failure(request, _('primary image'), result)

            # Additional images -> each uploaded to ImgBB
            additional_files = form.cleaned_data.get('additional_images') or []
            base_sort = product.images.count()
            for idx, image in enumerate(additional_files):
                sort_order = base_sort + idx
                result = _create_product_image(
                    product,
                    image,
                    False,
                    sort_order,
                    f'{product.name} - Image {sort_order + 1}',
                )
                if not result['success']:
                    _warn_imgbb_failure(request, _('image'), result)

            messages.success(request, _('Product "%(name)s" created successfully.') % {'name': product.name})
            return redirect('inventory:product_list')
    else:
        form = ProductForm()

    context = {
        'form': form,
        'title': _('Add New Product'),
        'submit_text': _('Create Product'),
    }
    return render(request, 'inventory/product_form.html', context)


@inventory_login_required
def product_edit(request, pk):
    """Edit an existing product."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()

            failed_removals = []
            imgbb_failures = []

            # 1) Explicit removals of existing images. Each image carries a
            #    hidden marker input (remove_image_<pk>); the ✕ button sets
            #    its value to "1" instead of deleting the DOM node, so the
            #    intent actually reaches the server.
            for image in list(product.images.all()):
                if request.POST.get(f'remove_image_{image.pk}') == '1':
                    # Check if user wants to also delete from ImgBB
                    delete_from_imgbb = request.POST.get(f'delete_imgbb_{image.pk}') == '1'
                    db_deleted, imgbb_deleted = _remove_product_image(image, delete_from_imgbb)
                    if not imgbb_deleted and delete_from_imgbb:
                        imgbb_failures.append(image.alt_text or f'#{image.pk}')

            # 2) Primary image:
            #    - new file provided  -> delete the old one (ImgBB + row),
            #      then upload the new one
            #    - no file provided   -> keep the current image and its ImgBB id
            primary_image = request.FILES.get('primary_image')
            if primary_image:
                old_primary = product.primary_image
                if old_primary:
                    db_deleted, imgbb_deleted = _remove_product_image(old_primary, True)
                    if not imgbb_deleted:
                        messages.warning(request, _(
                            'The previous primary image could not be deleted from '
                            'ImgBB right now - it was removed from the product but may still exist on ImgBB.'
                        ))
                result = _create_product_image(product, primary_image, True, 0, product.name)
                if not result['success']:
                    _warn_imgbb_failure(request, _('primary image'), result)

            # 3) Additional images: appended; untouched ones keep their ImgBB ids
            additional_files = form.cleaned_data.get('additional_images') or []
            base_sort = product.images.count()
            for idx, image in enumerate(additional_files):
                sort_order = base_sort + idx
                result = _create_product_image(
                    product,
                    image,
                    False,
                    sort_order,
                    f'{product.name} - Image {sort_order + 1}',
                )
                if not result['success']:
                    _warn_imgbb_failure(request, _('image'), result)

            messages.success(request, _('Product "%(name)s" updated successfully.') % {'name': product.name})
            if imgbb_failures:
                messages.warning(request, ngettext(
                    '%(count)s image could not be deleted from ImgBB '
                    'right now - it was removed from the product but may still exist on ImgBB.',
                    '%(count)s images could not be deleted from ImgBB '
                    'right now - they were removed from the product but may still exist on ImgBB.',
                    len(imgbb_failures),
                ) % {'count': len(imgbb_failures)})
            return redirect('inventory:product_list')
    else:
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'title': _('Edit Product: %(name)s') % {'name': product.name},
        'submit_text': _('Update Product'),
    }
    return render(request, 'inventory/product_form.html', context)


@inventory_login_required
def product_delete(request, pk):
    """Delete a product.

    POST params:
        delete_images: when 'on' (the switch's default state) every remote
            ImgBB copy grouped under this product is deleted as well. When
            absent, ties are severed instead: the ImgBB metadata is cleared
            so the images stay hosted, untracked, and a future re-upload of
            the same picture creates a fresh, conflict-free entry.
    """
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        name = product.name
        delete_remote = request.POST.get('delete_images') == 'on'
        imgbb_service = get_imgbb_service()
        failed_purges = 0

        for image_row in product.images.all():
            if delete_remote:
                # Verified deletion: retries + liveness probe per image.
                if image_row.imgbb_delete_url and not imgbb_service.delete_verified(
                    image_row.imgbb_delete_url,
                    image_row.large_url or image_row.imgbb_display_url,
                ):
                    failed_purges += 1
            else:
                # Sever ties: forget the remote copies exist.
                image_row.imgbb_delete_url = ''
                image_row.imgbb_id = ''
                image_row.save(update_fields=['imgbb_delete_url', 'imgbb_id'])

        product.delete()
        messages.success(request, _('Product "%(name)s" deleted successfully.') % {'name': name})
        if failed_purges:
            messages.warning(
                request,
                ngettext(
                    '%(count)s image could not be deleted from ImgBB — check the server logs; '
                    'you may need to remove it manually via its delete link.',
                    '%(count)s images could not be deleted from ImgBB — check the server logs; '
                    'you may need to remove them manually via their delete links.',
                    failed_purges,
                ) % {'count': failed_purges},
            )
        return redirect('inventory:product_list')

    context = {
        'product': product,
    }
    return render(request, 'inventory/product_confirm_delete.html', context)


@inventory_login_required
def product_stock_update(request, pk):
    """Quick stock update for a product."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = ProductStockForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            if request.headers.get('HX-Request'):
                return JsonResponse({
                    'success': True,
                    'stock_quantity': product.stock_quantity,
                    'stock_status': product.stock_status,
                    'stock_status_display': product.stock_status_display,
                })
            messages.success(request, _('Stock updated for "%(name)s".') % {'name': product.name})
            return redirect('inventory:product_list')
    else:
        form = ProductStockForm(instance=product)

    if request.headers.get('HX-Request'):
        return render(request, 'inventory/partials/_stock_form.html', {
            'form': form,
            'product': product,
        })

    context = {
        'form': form,
        'product': product,
        'is_htmx': request.headers.get('HX-Request'),
    }
    return render(request, 'inventory/product_stock.html', context)


@inventory_login_required
def category_list(request):
    """List all categories."""
    categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('sort_order', 'name')

    context = {
        'categories': categories,
    }
    return render(request, 'inventory/category_list.html', context)


@inventory_login_required
def category_create(request):
    """Create a new category."""
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()

            # Upload the image to ImgBB (no local copy is kept)
            image = form.cleaned_data.get('image')
            if image:
                result = get_imgbb_service().upload(image, name=category.name)
                if result['success']:
                    _apply_imgbb_to_category(category, result)
                else:
                    _warn_imgbb_failure(request, _('image'), result)

            messages.success(request, _('Category "%(name)s" created successfully.') % {'name': category.name})
            return redirect('inventory:category_list')
    else:
        form = CategoryForm()

    context = {
        'form': form,
        'title': _('Add New Category'),
        'submit_text': _('Create Category'),
    }
    return render(request, 'inventory/category_form.html', context)


@inventory_login_required
def category_edit(request, pk):
    """Edit an existing category."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            category = form.save()

            # New image provided -> replace: delete the old remote copy,
            # upload the new one. No file -> keep current ImgBB ids untouched.
            image = form.cleaned_data.get('image')
            if image:
                old_delete_url = category.imgbb_delete_url
                result = get_imgbb_service().upload(image, name=category.name)
                if result['success']:
                    if old_delete_url:
                        get_imgbb_service().delete(old_delete_url)
                    _apply_imgbb_to_category(category, result)
                else:
                    _warn_imgbb_failure(request, _('image'), result)

            messages.success(request, _('Category "%(name)s" updated successfully.') % {'name': category.name})
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)

    context = {
        'form': form,
        'category': category,
        'title': _('Edit Category: %(name)s') % {'name': category.name},
        'submit_text': _('Update Category'),
    }
    return render(request, 'inventory/category_form.html', context)


@inventory_login_required
def category_delete(request, pk):
    """Delete a category."""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        name = category.name
        # Remove the remote ImgBB copy grouped under this category (verified)
        if category.imgbb_delete_url:
            get_imgbb_service().delete_verified(
                category.imgbb_delete_url,
                category.image_url or category.imgbb_display_url,
            )
        category.delete()
        messages.success(request, _('Category "%(name)s" deleted successfully.') % {'name': name})
        return redirect('inventory:category_list')

    context = {
        'category': category,
    }
    return render(request, 'inventory/category_confirm_delete.html', context)


# Import models for F expressions
from django.db import models