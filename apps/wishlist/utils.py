"""
Wishlist query helpers.
"""
from django.db.models import BooleanField, Exists, OuterRef, Value

from .models import WishlistItem


def annotate_in_wishlist(queryset, user):
    """Annotate a Product queryset with `in_wishlist` (bool) for the viewer.

    Anonymous visitors get False for every row; authenticated users get
    whether each product is in their wishlist. One EXISTS subquery covers
    the whole page regardless of result count.
    """
    if getattr(user, "is_authenticated", False):
        subquery = WishlistItem.objects.filter(
            wishlist__user=user,
            product=OuterRef("pk"),
        )
        return queryset.annotate(in_wishlist=Exists(subquery))
    return queryset.annotate(in_wishlist=Value(False, BooleanField()))
