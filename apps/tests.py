import re
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase as DjangoTestCase, TransactionTestCase

from apps.models import BalanceTransaction, Category, Funnel, Order, Product, Survey, User, Withdrawal
from apps.services import orders as order_service
from apps.utils import normalize_phone


class TestCase(DjangoTestCase):
    """So'rov limitlari (kesh) testlar orasida saqlanib qolmasin."""

    def run(self, result=None):
        cache.clear()
        return super().run(result)


class FunnelDiscountTests(TestCase):
    """Hamkor chegirmasi narxni 0 ga tushira olmasligi yoki oshira olmasligi kerak."""

    def setUp(self):
        self.product = Product.objects.create(title="Phone", price=1_000_000, commission=150_000,
                                              stock_quantity=50)
        self.affiliate = User.objects.create_user("998900000001", "Pw-123456")
        self.client = Client()
        self.client.force_login(self.affiliate)

    def create_funnel(self, discount):
        return self.client.post("/admin_page/market/", {
            "product_id": self.product.id, "title": "oqim", "discount": discount,
        })

    def order_via(self, funnel, quantity=1):
        Client().post(f"/funnel/{funnel.id}/", {
            "full_name": "Ali", "phone_number": "998901112233", "quantity": quantity,
        })
        return Order.objects.filter(funnel=funnel).latest("id")

    def test_valid_discount_applied(self):
        self.create_funnel("100000")
        funnel = Funnel.objects.get()
        self.assertEqual(funnel.discount_price, 100_000)
        self.assertEqual(self.order_via(funnel, quantity=2).total_price, 1_800_000)

    def test_no_discount(self):
        self.create_funnel("")
        funnel = Funnel.objects.get()
        self.assertIsNone(funnel.discount_price)
        self.assertEqual(self.order_via(funnel).total_price, 1_000_000)

    def test_rejects_discount_above_commission(self):
        for value in ("150001", "1000000", "5000000"):
            self.create_funnel(value)
        self.assertFalse(Funnel.objects.exists())

    def test_rejects_negative_discount(self):
        self.create_funnel("-5000000")
        self.assertFalse(Funnel.objects.exists())

    def test_rejects_non_numeric_discount_without_500(self):
        response = self.create_funnel("abc")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Funnel.objects.exists())

    def test_legacy_bad_funnel_does_not_change_price(self):
        # Tuzatishdan oldin yaratilgan noto'g'ri funnellar
        for bad in (-5_000_000, 1_000_000, 2_000_000):
            funnel = Funnel.objects.create(title="eski", slug=f"eski{bad}", product=self.product,
                                           owner=self.affiliate, discount_price=bad)
            self.assertEqual(self.order_via(funnel).total_price, 1_000_000)


class WithdrawalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("998900000001", "Pw-123456")
        self.user.main_balance = 500
        self.user.save()
        self.client = Client()
        self.client.force_login(self.user)

    def withdraw(self, **extra):
        data = {"card_number": "8600 1234 1234 1234", "amount": 200, **extra}
        return self.client.post("/admin_page/withdraw/", data)

    def test_withdrawal_moves_money_to_pending(self):
        self.withdraw()
        self.user.refresh_from_db()
        self.assertEqual(Withdrawal.objects.get().amount, 200)
        self.assertEqual((self.user.main_balance, self.user.pending_balance), (300, 200))

    def test_cannot_withdraw_more_than_balance(self):
        self.withdraw(amount=501)
        self.user.refresh_from_db()
        self.assertFalse(Withdrawal.objects.exists())
        self.assertEqual(self.user.main_balance, 500)

    def admin_action(self, action):
        from django.contrib import admin as django_admin
        from apps.admin import WithdrawalAdmin
        getattr(WithdrawalAdmin(Withdrawal, django_admin.site), action)(None, Withdrawal.objects.all())

    def test_reject_restores_balance_once(self):
        self.withdraw(amount=200)
        self.withdraw(amount=100)
        self.admin_action("mark_rejected")
        self.admin_action("mark_rejected")  # ikkinchi marta bosilsa ham o'zgarmaydi
        self.user.refresh_from_db()
        self.assertEqual((self.user.main_balance, self.user.pending_balance), (500, 0))

    def test_complete_clears_pending_once(self):
        self.withdraw(amount=200)
        self.admin_action("mark_completed")
        self.admin_action("mark_rejected")  # bajarilgan so'rovni rad etib bo'lmaydi
        self.user.refresh_from_db()
        self.assertEqual((self.user.main_balance, self.user.pending_balance), (300, 0))


class AccountSecurityTests(TestCase):
    STRONG = "Murakkab-Parol-2026"

    def register(self, client=None, password=None, **extra):
        password = password or self.STRONG
        return (client or Client()).post("/register/", {
            "phone_number": "998901234567", "password": password, "conf_password": password, **extra,
        })

    def test_weak_passwords_rejected(self):
        for weak in ("abc", "12345678", "password"):
            self.register(password=weak)
        self.assertFalse(User.objects.exists())

    def test_strong_password_registers(self):
        self.register()
        self.assertTrue(User.objects.filter(phone_number="+998901234567").exists())

    def test_invalid_ref_id_does_not_crash(self):
        for bad in ("x", "-1", "999999"):
            response = self.register(ref_id=bad)
            self.assertEqual(response.status_code, 302, bad)
            User.objects.all().delete()

    def test_referral_link_records_referrer(self):
        referrer = User.objects.create_user("998900000009", self.STRONG)
        client = Client()
        client.get(f"/register/?id={referrer.id}")  # referal havola ochildi
        self.register(client=client)              # keyin bosh sahifadagi modal yuborildi
        self.assertEqual(User.objects.get(phone_number="+998901234567").referred_by, referrer)

    def test_referral_link_has_no_redirect_hop(self):
        user = User.objects.create_user("998900000009", self.STRONG)
        client = Client()
        client.force_login(user)
        link = client.get("/profile/referral/").context["referral_link"]
        self.assertIn("/register/?id=", link)

    def password_change(self, client, current, new, confirm=None):
        return client.post("/profile/settings/", {
            "_password_change": "1", "current_password": current,
            "new_password": new, "confirm_password": confirm or new,
        })

    def test_password_change_requires_current_password(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        client = Client()
        client.force_login(user)
        self.password_change(client, "noto'g'ri", "Yangi-Parol-2027")
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.STRONG))

    def test_password_change_rejects_weak_new_password(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        client = Client()
        client.force_login(user)
        self.password_change(client, self.STRONG, "123456")
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.STRONG))

    def test_password_change_works(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        client = Client()
        client.force_login(user)
        self.password_change(client, self.STRONG, "Yangi-Parol-2027")
        user.refresh_from_db()
        self.assertTrue(user.check_password("Yangi-Parol-2027"))

    def test_logout_is_post_only(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        client = Client()
        client.force_login(user)
        self.assertEqual(client.get("/logout/").status_code, 405)
        self.assertIn("_auth_user_id", client.session)
        client.post("/logout/")
        self.assertNotIn("_auth_user_id", client.session)


class ProductionSettingsTests(TestCase):
    def test_refuses_known_secret_key_when_not_debug(self):
        import os
        import subprocess
        import sys
        from pathlib import Path
        env = {**os.environ, "DEBUG": "False", "SECRET_KEY": "django-insecure-change-me-in-.env",
               "DJANGO_SETTINGS_MODULE": "root.settings"}
        result = subprocess.run([sys.executable, "-c", "import django; django.setup()"],
                                cwd=Path(__file__).resolve().parent.parent, env=env,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ImproperlyConfigured", result.stderr)


class LogoutTemplateTests(TestCase):
    def test_logout_links_submit_post_form(self):
        user = User.objects.create_user("998900000001", "Murakkab-Parol-2026", is_operator=True)
        client = Client()
        client.force_login(user)
        for url in ("/admin_page/", "/admin_page/orders/new/", "/admin_page/orders/my/", "/profile/settings/"):
            html = client.get(url).content.decode()
            self.assertIn('<form id="logout-form" action="/logout/" method="post"', html, url)
            self.assertIn("getElementById('logout-form').submit()", html, url)
            self.assertNotIn('href="/logout/"', html, url)
            self.assertNotIn("/profile/logout", html, url)


class BrandingTests(TestCase):
    """Mijozga ko'rinadigan sahifalarda faqat ZUNO brendi bo'lishi kerak."""

    def assertZuno(self, response):
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("ZUNO", html)
        self.assertIn("apps/brand/", html)

    def test_storefront_uses_zuno_brand_and_metadata(self):
        response = self.client.get("/")
        self.assertZuno(response)
        html = response.content.decode()
        self.assertIn('property="og:site_name" content="ZUNO"', html)
        self.assertIn('rel="manifest"', html)

    def test_product_page_title(self):
        product = Product.objects.create(title="Phone", price=1_000_000, slug="phone", stock_quantity=2)
        response = self.client.get(f"/product-detail/{product.slug}/")
        self.assertZuno(response)
        self.assertIn("<title>Phone — ZUNO</title>", response.content.decode())

    def test_operator_panel_uses_zuno_brand(self):
        operator = User.objects.create_user("998900000002", "Pw-123456", is_operator=True)
        self.client.force_login(operator)
        self.assertZuno(self.client.get("/admin_page/orders/new/"))

    def test_referral_link_points_to_existing_funnel_route(self):
        user = User.objects.create_user("998900000003", "Pw-123456")
        product = Product.objects.create(title="Phone", price=1_000_000)
        funnel = Funnel.objects.create(title="oqim", slug="oqim-1", product=product, owner=user)
        self.client.force_login(user)
        html = self.client.get("/admin_page/links/").content.decode()
        self.assertIn(f"http://testserver/funnel/{funnel.id}/", html)
        self.assertEqual(self.client.get(f"/funnel/{funnel.id}/").status_code, 200)


class AuthFormFeedbackTests(TestCase):
    """Forma xatolari tegishli maydon ostida, bitta ro'yxatda va qulay holda chiqishi kerak."""

    STRONG = "Murakkab-Parol-2026"
    INVALID_INPUT = re.compile(r'<input[^>]*aria-invalid="true"')
    TOAST = 'class="app-toast'
    ALERT = 'class="zuno-alert zuno-alert--'

    def register(self, password, confirm=None):
        return self.client.post("/register/", {
            "phone_number": "998901234567", "password": password,
            "conf_password": confirm if confirm is not None else password,
        }, follow=True)

    def test_weak_password_errors_grouped_under_password_field(self):
        html = self.register("123").content.decode()
        self.assertFalse(User.objects.exists())
        self.assertIn('data-auth-open="register"', html)
        self.assertEqual(len(self.INVALID_INPUT.findall(html)), 1)
        self.assertIn('aria-describedby="register-password-help register-password-error"', html)
        start = html.index('id="register-password-error"')
        block = html[start:html.index("</div>", start)]
        self.assertIn('class="is-multiple"', block)
        self.assertEqual(block.count("<li>"), 3)  # qisqa + oddiy + faqat raqam
        self.assertNotIn(self.TOAST, html)  # forma xatosi toastda takrorlanmaydi
        self.assertIn("8", block)  # eng kam uzunlik haqidagi xabar

    def test_password_mismatch_shown_under_confirmation(self):
        html = self.register(self.STRONG, "Boshqa-Parol-2026").content.decode()
        self.assertIn('id="register-password2-error"', html)
        self.assertIn("Parollar mos tushmadi!", html)

    def test_no_errors_before_submission(self):
        html = self.client.get("/").content.decode()
        self.assertIn('data-auth-open=""', html)
        self.assertNotIn(self.ALERT, html)
        self.assertFalse(self.INVALID_INPUT.search(html))

    def test_login_error_is_generic_and_opens_login_tab(self):
        html = self.client.post("/login/", {"phone_number": "998900000000", "password": "x"},
                                follow=True).content.decode()
        self.assertIn('data-auth-open="login"', html)
        self.assertIn('id="login-error"', html)
        self.assertFalse(self.INVALID_INPUT.search(html))  # qaysi maydon xatoligi oshkor qilinmaydi

    def test_successful_registration_still_works(self):
        response = self.register(self.STRONG)
        self.assertRedirects(response, "/profile/settings/")
        self.assertTrue(User.objects.filter(phone_number="+998901234567").exists())

    def test_settings_password_errors_inline(self):
        user = User.objects.create_user("998900000001", self.STRONG)
        self.client.force_login(user)
        html = self.client.post("/profile/settings/", {
            "_password_change": "1", "current_password": self.STRONG,
            "new_password": "12345678", "confirm_password": "12345678",
        }, follow=True).content.decode()
        self.assertIn('id="id_new_password-error"', html)
        self.assertNotIn(self.TOAST, html)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.STRONG))


class StorefrontTests(TestCase):
    """Bosh sahifa, katalog saralash, qidiruv va buyurtma formasining haqiqiy xatti-harakati."""

    def setUp(self):
        self.cat = Category.objects.create(title="Elektronika", slug="elektronika")
        self.cheap = Product.objects.create(title="Arzon quloqchin", slug="arzon", price=100_000, commission=20_000,
                                            category=self.cat, stock_quantity=3)
        self.pricey = Product.objects.create(title="Qimmat noutbuk", slug="qimmat", price=9_000_000,
                                             category=self.cat, stock_quantity=0)

    def titles(self, response):
        return [p.title for p in response.context["products"]]

    def test_home_shows_latest_products_and_real_counts(self):
        for i in range(10):
            Product.objects.create(title=f"P{i}", slug=f"p{i}", price=1000)
        response = self.client.get("/")
        self.assertEqual(len(response.context["products"]), 8)
        self.assertEqual(response.context["products_total"], 12)
        html = response.content.decode()
        self.assertNotIn("Eng ko'p sotiladigan", html)  # tasdiqlanmagan da'vo olib tashlangan
        self.assertNotIn("bepul yetkazib", html)

    def test_catalog_sorting_and_state_kept_in_pagination(self):
        self.assertEqual(self.titles(self.client.get("/category/?sort=cheap"))[0], "Arzon quloqchin")
        self.assertEqual(self.titles(self.client.get("/category/?sort=expensive"))[0], "Qimmat noutbuk")
        response = self.client.get("/category/elektronika/?sort=bad")
        self.assertEqual(response.context["sort"], "new")
        for i in range(20):
            Product.objects.create(title=f"S{i}", slug=f"s{i}", price=1000 + i)
        html = self.client.get("/category/?sort=cheap").content.decode()
        self.assertIn('href="?sort=cheap&amp;page=2"', html)

    def test_out_of_stock_badge_from_real_stock(self):
        html = self.client.get("/category/").content.decode()
        self.assertEqual(html.count("zuno-pcard__badge is-out"), 1)

    def test_search_encodes_query_and_shows_empty_state(self):
        response = self.client.post("/search/", {"product": "a&b #1"})
        self.assertEqual(response["Location"], "/search/?product=a%26b+%231")
        html = self.client.get("/search/?product=yo'q-mahsulot").content.decode()
        self.assertIn("Hech narsa topilmadi", html)
        self.assertIn(self.titles(self.client.get("/search/?product=noutbuk"))[0], "Qimmat noutbuk")

    def test_order_success_shown_only_after_save(self):
        response = self.client.post("/product-detail/arzon/", {
            "full_name": "O'g'iloy", "phone_number": "+998(90) 123-45-67", "quantity": "2"}, follow=True)
        order = Order.objects.get()
        self.assertEqual(order.total_price, 200_000)
        html = response.content.decode()
        self.assertIn(f"Buyurtmangiz #{order.id} qabul qilindi", html)
        self.assertIn('class="zuno-success"', html)
        self.assertNotIn('class="app-toast', html)

    def test_order_errors_inline_and_nothing_saved(self):
        html = self.client.post("/product-detail/arzon/", {"full_name": "", "phone_number": "", "quantity": "0"},
                                follow=True).content.decode()
        self.assertFalse(Order.objects.exists())
        self.assertNotIn('class="zuno-success"', html)
        for field in ("order-name", "order-phone", "quantity"):
            self.assertIn(f'id="{field}-error"', html)

    def test_funnel_page_form_posts_to_funnel_with_discount(self):
        owner = User.objects.create_user("998900000005", "Pw-123456")
        funnel = Funnel.objects.create(title="o", slug="o-1", product=self.cheap, owner=owner, discount_price=10_000)
        html = self.client.get(f"/funnel/{funnel.id}/").content.decode()
        self.assertIn(f'action="/funnel/{funnel.id}/"', html)
        self.assertIn("90 000 so'm", html)
        self.client.post(f"/funnel/{funnel.id}/", {"full_name": "Ali", "phone_number": "998901234567", "quantity": "1"})
        order = Order.objects.get()
        self.assertEqual((order.funnel_id, order.total_price), (funnel.id, 90_000))

    def test_dashboard_has_no_dead_favorites_link(self):
        user = User.objects.create_user("998900000006", "Pw-123456")
        self.client.force_login(user)
        self.assertNotIn("liked-products", self.client.get("/admin_page/").content.decode())


class OrderLifecycleTests(TestCase):
    """Ombor, yakuniy narx, status qoidalari va hamkor komissiyasi."""

    def setUp(self):
        self.owner = User.objects.create_user("998900000010", "Pw-123456")
        self.operator = User.objects.create_user("998900000011", "Pw-123456", is_operator=True)
        self.product = Product.objects.create(title="Soat", slug="soat", price=500_000, delivery_price=30_000,
                                              commission=50_000, stock_quantity=5)
        self.funnel = Funnel.objects.create(title="o", slug="o-2", product=self.product, owner=self.owner,
                                            discount_price=10_000)

    def place(self, quantity=2, phone="998901234567"):
        self.client.post(f"/funnel/{self.funnel.id}/", {"full_name": "Ali", "phone_number": phone, "quantity": quantity})
        order = Order.objects.latest("id")
        Order.objects.filter(pk=order.pk).update(operator=self.operator)
        return order

    def walk(self, order, *statuses):
        for status in statuses:
            order_service.change_status(order.pk, status)

    def balance(self):
        self.owner.refresh_from_db()
        return self.owner.main_balance

    def stock(self):
        self.product.refresh_from_db()
        return self.product.stock_quantity

    S = Order.Status

    def test_order_snapshots_price_delivery_and_reserves_stock(self):
        order = self.place()
        self.assertEqual((order.unit_price, order.delivery_price, order.unit_commission), (490_000, 30_000, 40_000))
        self.assertEqual(order.total_price, 1_010_000)
        self.assertEqual(order.phone_number, "+998901234567")
        self.assertEqual(self.stock(), 3)

    def test_cannot_order_more_than_stock(self):
        self.client.post(f"/funnel/{self.funnel.id}/", {"full_name": "A", "phone_number": "998901234567", "quantity": 6})
        self.assertFalse(Order.objects.exists())
        self.assertEqual(self.stock(), 5)

    def test_commission_paid_once_only_after_delivery(self):
        order = self.place()
        self.walk(order, self.S.PACKING, self.S.DELIVERING)
        self.assertEqual(self.balance(), 0)
        self.walk(order, self.S.DELIVERED, self.S.DELIVERED)
        self.assertEqual(self.balance(), 80_000)
        self.assertEqual(BalanceTransaction.objects.filter(order=order).count(), 1)

    def test_return_after_delivery_reverses_commission_and_restocks(self):
        order = self.place()
        self.walk(order, self.S.PACKING, self.S.DELIVERING, self.S.DELIVERED, self.S.RETURNED)
        self.assertEqual(self.balance(), 0)
        self.assertEqual(self.stock(), 5)
        self.assertEqual(BalanceTransaction.objects.filter(order=order).count(), 2)

    def test_cancel_restores_stock_without_commission(self):
        order = self.place()
        self.walk(order, self.S.CANCELED)
        self.assertEqual(self.stock(), 5)
        self.assertEqual(self.balance(), 0)

    def test_illegal_transition_rejected(self):
        order = self.place()
        with self.assertRaises(order_service.OrderError):
            self.walk(order, self.S.DELIVERED)
        order.refresh_from_db()
        self.assertEqual(order.status, self.S.NEW)

    def test_self_purchase_earns_nothing(self):
        order = self.place(phone=self.owner.phone_number)
        self.assertEqual(order.unit_commission, 0)

    def test_operator_quantity_edit_adjusts_stock_and_total(self):
        order = self.place(quantity=1)
        self.client.force_login(self.operator)
        self.client.post(f"/admin_page/orders/{order.id}/", {
            "status": "packaging", "quantity": "3", "customer_name": "Ali", "phone": "998901234567",
            "region": "abc", "district": "xyz", "address": "Toshkent",
        })
        order.refresh_from_db()
        self.assertEqual((order.quantity, order.status, order.total_price), (3, self.S.PACKING, 1_500_000))
        self.assertEqual(self.stock(), 2)
        self.assertEqual(Survey.objects.count(), 1)

    def test_deleted_link_keeps_orders_and_stops_selling(self):
        order = self.place()
        self.client.force_login(self.owner)
        self.client.post(f"/admin_page/links/delete/{self.funnel.id}/")
        order.refresh_from_db()
        self.assertEqual(order.funnel_id, self.funnel.id)
        self.assertEqual(self.client.get(f"/funnel/{self.funnel.id}/").status_code, 404)

    def test_visitor_view_counted_but_owner_not(self):
        self.client.force_login(self.owner)
        self.client.get(f"/funnel/{self.funnel.id}/")
        self.client.logout()
        self.client.get(f"/funnel/{self.funnel.id}/")
        self.funnel.refresh_from_db()
        self.assertEqual(self.funnel.views_count, 1)

    def test_track_order_requires_matching_phone(self):
        order = self.place()
        wrong = self.client.post("/track/", {"order_id": order.id, "phone_number": "998900000099"})
        self.assertContains(wrong, "topilmadi")
        right = self.client.post("/track/", {"order_id": f"#{order.id}", "phone_number": "+998 90 123 45 67"})
        self.assertContains(right, "Soat")


class RobustInputTests(TestCase):
    """Noto'g'ri kiritilgan qiymatlar 500 xato bermasligi kerak (PostgreSQL ayniqsa qattiqqo'l)."""

    def setUp(self):
        self.user = User.objects.create_user("998900000020", "Pw-123456", is_operator=True)
        self.client.force_login(self.user)

    def test_nul_byte_and_huge_values_in_queries(self):
        for url in ("/search/?product=a%00b", "/admin_page/market/?q=a%00", "/admin_page/links/?q=99999999999999999999",
                    "/admin_page/requests/?q=99999999999999999999&status=%00", "/category/?sort=%00&page=x"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_non_numeric_ids_in_forms(self):
        self.assertEqual(self.client.post("/admin_page/market/", {"product_id": "abc", "title": "x"}).status_code, 302)
        self.assertEqual(self.client.post("/profile/settings/", {"region": "abc"}).status_code, 302)

    def test_overlong_profile_is_rejected_cleanly(self):
        response = self.client.post("/profile/settings/", {"first_name": "x" * 500})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")

    def test_login_is_rate_limited(self):
        client = Client()
        for _ in range(9):
            response = client.post("/login/", {"phone_number": "998900000020", "password": "wrong"}, follow=True)
        self.assertContains(response, "Urinishlar juda ko")

    def test_login_redirects_to_safe_next_only(self):
        client = Client()
        response = client.post("/login/", {"phone_number": "998900000020", "password": "Pw-123456",
                                           "next": "https://evil.example/"})
        self.assertEqual(response["Location"], "/admin_page/orders/new/")

    def test_slug_collisions_get_unique_values(self):
        first = Product.objects.create(title="Bir xil", price=1)
        second = Product.objects.create(title="Bir xil", price=1)
        self.assertNotEqual(first.slug, second.slug)

    def test_normalize_phone(self):
        for raw in ("+998(90) 123-45-67", "998901234567", "901234567"):
            self.assertEqual(normalize_phone(raw), "+998901234567")
        self.assertEqual(normalize_phone("12345"), "")


class ConcurrencyTests(TransactionTestCase):
    """PostgreSQL qatorlarni qulflaydi: bir vaqtdagi so'rovlar ombor va balansni buzmasligi kerak."""

    def run_parallel(self, func, times):
        def worker():
            try:
                return func()
            except order_service.OrderError:
                return None
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=times) as pool:
            return [future.result() for future in [pool.submit(worker) for _ in range(times)]]

    def test_last_item_sold_once(self):
        product = Product.objects.create(title="Oxirgi", slug="oxirgi", price=1000, stock_quantity=1)

        def buy():
            return order_service.place_order(Order(full_name="A", phone_number="+998901234567", quantity=1), product)

        results = self.run_parallel(buy, 8)
        self.assertEqual(sum(result is not None for result in results), 1)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 0)

    def test_commission_credited_once_under_double_click(self):
        owner = User.objects.create_user("998900000030", "Pw-123456")
        product = Product.objects.create(title="K", slug="k", price=1000, commission=100, stock_quantity=2)
        funnel = Funnel.objects.create(title="o", slug="o-k", product=product, owner=owner)
        order = order_service.place_order(Order(full_name="A", phone_number="+998901234567", quantity=1), product, funnel)
        for status in (Order.Status.PACKING, Order.Status.DELIVERING):
            order_service.change_status(order.pk, status)

        self.run_parallel(lambda: order_service.change_status(order.pk, Order.Status.DELIVERED), 6)
        owner.refresh_from_db()
        self.assertEqual(owner.main_balance, 100)
