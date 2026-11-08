from django.db import migrations

from apps.utils import normalize_phone


def backfill(apps, schema_editor):
    User = apps.get_model('apps', 'User')
    Order = apps.get_model('apps', 'Order')
    Product = apps.get_model('apps', 'Product')

    for user in User.objects.all():
        phone = normalize_phone(user.phone_number)
        if phone and phone != user.phone_number and not User.objects.filter(phone_number=phone).exists():
            user.phone_number = phone
            user.save(update_fields=['phone_number'])

    for order in Order.objects.all():
        order.phone_number = normalize_phone(order.phone_number) or order.phone_number
        order.unit_price = order.total_price / (order.quantity or 1)
        order.save(update_fields=['phone_number', 'unit_price'])

    # Boshlang'ich komissiya narxning 10% i; admin har bir mahsulot uchun o'zgartira oladi
    for product in Product.objects.filter(commission=0):
        product.commission = round(product.price / 10, -3)
        product.save(update_fields=['commission'])


class Migration(migrations.Migration):
    dependencies = [('apps', '0008_commerce_core')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
