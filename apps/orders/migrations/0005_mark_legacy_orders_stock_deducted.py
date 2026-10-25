from django.db import migrations


def mark_legacy_orders(apps, schema_editor):
    """Treat orders created before the status-based rule as already deducted.

    Historically stock was taken out of the catalogue the moment an order was
    placed. Only the new flow defers that to the first Confirmed/Processing/
    Delivered status. Flagging existing orders keeps them from deducting twice
    when staff change their status after this release.
    """
    Order = apps.get_model('orders', 'Order')
    Order.objects.exclude(status__in=['cancelled', 'refunded']).update(stock_deducted=True)


def unmark_legacy_orders(apps, schema_editor):
    """Reverse is intentionally a no-op: the original data cannot be recovered."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_order_stock_deducted_and_more'),
    ]

    operations = [
        migrations.RunPython(mark_legacy_orders, unmark_legacy_orders),
    ]
