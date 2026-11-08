from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from apps.models import Competition, Funnel, Order, Product, Region, User, Withdrawal
from apps.services import orders as order_service

S = Order.Status
BUYERS = ["Dilnoza Karimova", "Jasur Toshmatov", "Madina Rahimova", "Sardor Aliyev", "Nodira Usmonova",
          "Bekzod Yusupov", "Gulnoza Saidova", "Otabek Ergashev", "Zarina Qodirova", "Aziz Nazarov"]
PATHS = {
    S.NEW: [],
    S.PACKING: [S.PACKING],
    S.DELIVERING: [S.PACKING, S.DELIVERING],
    S.DELIVERED: [S.PACKING, S.DELIVERING, S.DELIVERED],
    S.RETURNED: [S.PACKING, S.DELIVERING, S.DELIVERED, S.RETURNED],
    S.CANCELED: [S.CANCELED],
}
PLAN = [S.NEW, S.NEW, S.NEW, S.PACKING, S.DELIVERING, S.DELIVERED, S.DELIVERED, S.DELIVERED, S.RETURNED, S.CANCELED]


class Command(BaseCommand):
    help = "Namoyish uchun hamkor, operator va buyurtmalar yaratadi (faqat DEBUG=True rejimida)."

    def add_arguments(self, parser):
        parser.add_argument('--password', default='Zuno-Demo-2026')

    def handle(self, *args, password, **options):
        if not settings.DEBUG:
            raise CommandError("Namoyish foydalanuvchilari productionda yaratilmaydi (ma'lum parol bilan).")
        products = list(Product.objects.filter(stock_quantity__gt=2).order_by('id')[:3])
        if len(products) < 3:
            raise CommandError("Avval: python manage.py seed_products")

        seller = self._user('+998900000001', password, first_name='Aziza', last_name='Hamkor')
        operator = self._user('+998900000002', password, first_name='Bobur', last_name='Operator', is_operator=True)
        region = Region.objects.order_by('id').first()

        funnels = [
            Funnel.objects.get_or_create(
                slug=f'namoyish-{index}',
                defaults={'title': f"{product.title} — Instagram", 'product': product, 'owner': seller,
                          'discount_price': int(product.commission / 5), 'views_count': 120 + index * 75},
            )[0]
            for index, product in enumerate(products, 1)
        ]

        if not Order.objects.filter(funnel__in=funnels).exists():
            for index, status in enumerate(PLAN):
                funnel = funnels[index % len(funnels)]
                order = Order(full_name=BUYERS[index], phone_number=f'+99890000{1000 + index}', quantity=1 + index % 2,
                              region=region, shipping_address="Mustaqillik ko'chasi, 12-uy")
                order_service.place_order(order, funnel.product, funnel)
                if status != S.NEW or index == 2:
                    Order.objects.filter(pk=order.pk).update(operator=operator)
                for step in PATHS[status]:
                    order_service.change_status(order.pk, step)
            seller.refresh_from_db()
            amount = int(seller.main_balance / 3)
            Withdrawal.objects.create(user=seller, card_number='8600000000000000', amount=amount)
            User.objects.filter(pk=seller.pk).update(main_balance=seller.main_balance - amount, pending_balance=amount)

        now = timezone.now()
        Competition.objects.get_or_create(title="Oyning eng yaxshi hamkori", defaults={
            'image': 'competition/zuno-konkurs-banner.jpg', 'description': "Eng ko'p yetkazilgan buyurtma uchun sovrin.",
            'start_date': now - timedelta(days=10), 'end_date': now + timedelta(days=20),
        })
        self.stdout.write(self.style.SUCCESS(f"Tayyor. Hamkor: +998900000001, operator: +998900000002, parol: {password}"))

    @staticmethod
    def _user(phone, password, **fields):
        user = User.objects.filter(phone_number=phone).first()
        return user or User.objects.create_user(phone, password, **fields)
