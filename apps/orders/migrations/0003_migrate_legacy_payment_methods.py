from django.db import migrations


def forwards(apps, schema_editor):
    """Collapse historical payment methods into the WhatsApp-only flow."""
    Order = apps.get_model("orders", "Order")
    Order.objects.exclude(payment_method="whatsapp").update(payment_method="whatsapp")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_alter_order_payment_method"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
