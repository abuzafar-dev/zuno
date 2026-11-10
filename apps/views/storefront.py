from urllib.parse import urlencode

from django.contrib import messages
from django.db import connection
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.forms import OrderForm, TrackOrderForm
from apps.models import Category, Funnel, Order, Product
from apps.services import orders as order_service
from apps.services.orders import OrderError
from apps.utils import clean_text, client_ip, is_rate_limited, normalize_phone, parse_positive_int
from apps.views.common import paginate

ORDERS_PER_IP_PER_HOUR = 15
TRACK_ATTEMPTS = 20
CATALOG_PAGE_SIZE = 18

# Katalog saralash variantlari (?sort=...). Noma'lum qiymat - eng yangilari.
PRODUCT_SORTS = {
    'new': '-id',
    'cheap': 'price',
    'expensive': '-price',
}

TRACK_STEPS = [
    (Order.Status.NEW, 'Qabul qilindi'),
    (Order.Status.PACKING, 'Qadoqlanmoqda'),
    (Order.Status.DELIVERING, "Yo'lda"),
    (Order.Status.DELIVERED, 'Yetkazildi'),
]
TRACK_STEP_INDEX = {status: index for index, (status, _) in enumerate(TRACK_STEPS)}
TRACK_STEP_INDEX.update({Order.Status.LATER: 0, Order.Status.HOLD: 0})


def _catalog_context(request, products, **extra):
    sort = request.GET.get('sort', 'new')
    if sort not in PRODUCT_SORTS:
        sort = 'new'
    products = products.select_related('category').order_by(PRODUCT_SORTS[sort])
    return {
        'categories': Category.objects.all(),
        'products': paginate(request, products, CATALOG_PAGE_SIZE),
        'sort': sort,
        'page_params': urlencode({'sort': sort}) if sort != 'new' else '',
        **extra,
    }


def _submit_order(request, product, funnel=None):
    """Buyurtma formasini qayta ishlaydi: xato yoki muvaffaqiyat mahsulot sahifasida ko'rsatiladi."""
    if is_rate_limited('order', client_ip(request), limit=ORDERS_PER_IP_PER_HOUR, window=60 * 60):
        messages.error(request, "Buyurtmalar juda ko'p. Birozdan keyin urinib ko'ring.",
                       extra_tags='order_form field-full_name')
        return

    form = OrderForm(request.POST)
    if not form.is_valid():
        for field, field_errors in form.errors.items():
            for error in field_errors:
                messages.error(request, error, extra_tags=f'order_form field-{field}')
        return

    order = form.save(commit=False)
    order.user = request.user if request.user.is_authenticated else None
    try:
        order_service.place_order(order, product, funnel)
    except OrderError as exc:
        messages.error(request, str(exc), extra_tags='order_form field-quantity')
        return
    messages.success(request, f"Buyurtmangiz #{order.id} qabul qilindi! Operatorimiz tez orada qo'ng'iroq qiladi.",
                     extra_tags='order_form')


class HomeView(View):
    def get(self, request):
        # Bosh sahifada eng yangi 8 ta mahsulot; to'liq ro'yxat - /category/
        return render(request, 'bosh-sahifa.html', {
            'categories': Category.objects.all(),
            'products': Product.objects.select_related('category').order_by('-id')[:8],
            'products_total': Product.objects.count(),
        })


class SearchProductView(View):
    def get(self, request):
        query = clean_text(request.GET.get('product'), 100)
        found = Product.objects.filter(title__icontains=query) if query else Product.objects.none()
        return render(request, 'bosh-sahifa.html', {
            'products': paginate(request, found.select_related('category').order_by('-id'), CATALOG_PAGE_SIZE),
            'query': query,
            'is_search': True,
            'page_params': urlencode({'product': query}),
            'categories': Category.objects.all(),
        })

    def post(self, request):
        # urlencode: "&", "#", "+" kabi belgilar so'rovni buzmasin
        return redirect(f"{request.path}?{urlencode({'product': clean_text(request.POST.get('product'), 100)})}")


class ShopView(View):
    def get(self, request):
        return render(request, 'category.html', _catalog_context(request, Product.objects.all(), category=None))


class CategoryDetailView(View):
    def get(self, request, slug):
        category = get_object_or_404(Category, slug=slug)
        return render(request, 'category.html',
                      _catalog_context(request, Product.objects.filter(category=category), category=category))


def _product_page_context(product, funnel=None):
    unit_price = order_service.unit_price(product, funnel)
    related = []
    if product.category_id:
        related = (Product.objects.filter(category_id=product.category_id).exclude(pk=product.pk)
                   .select_related('category').order_by('-id')[:4])
    return {
        'related': related,
        'funnel': funnel,
        'product': product,
        'unit_price': unit_price,
        'first_total': unit_price + product.delivery_price,
        'max_quantity': range(1, min(product.stock_quantity, 9) + 1),
        'categories': Category.objects.all(),
    }


class ProductDetailView(View):
    def get(self, request, slug):
        product = get_object_or_404(Product.objects.select_related('category'), slug=slug)
        return render(request, 'product-detail.html', _product_page_context(product))

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        _submit_order(request, product)
        return redirect('product-detail', slug=product.slug)


class FunnelDetailView(View):
    def _funnel(self, funnel_id):
        return get_object_or_404(Funnel.objects.select_related('product', 'product__category', 'owner'),
                                 id=funnel_id, is_active=True)

    def get(self, request, funnel_id):
        funnel = self._funnel(funnel_id)
        if funnel.owner_id != request.user.pk:
            Funnel.objects.filter(pk=funnel.pk).update(views_count=F('views_count') + 1)
        return render(request, 'product-detail.html', _product_page_context(funnel.product, funnel))

    def post(self, request, funnel_id):
        funnel = self._funnel(funnel_id)
        _submit_order(request, funnel.product, funnel)
        return redirect('funnel-detail', funnel_id=funnel.id)


class TrackOrderView(View):
    """Mijoz buyurtmasini raqami va telefoni orqali kuzatadi (hisob ochish shart emas)."""

    def get(self, request):
        return render(request, 'track.html', {'categories': Category.objects.all()})

    def post(self, request):
        context = {'categories': Category.objects.all(), 'submitted': True}
        if is_rate_limited('track', client_ip(request), limit=TRACK_ATTEMPTS, window=15 * 60):
            context['error'] = "Urinishlar juda ko'p. Birozdan keyin qayta urinib ko'ring."
            return render(request, 'track.html', context, status=429)

        form = TrackOrderForm(request.POST)
        order = None
        if form.is_valid():
            order_id = parse_positive_int(form.cleaned_data['order_id'].lstrip('#'))
            phone = normalize_phone(form.cleaned_data['phone_number'])
            if order_id and phone:
                order = Order.objects.select_related('product').filter(pk=order_id, phone_number=phone).first()
        if order is None:
            # Qaysi maydon xatoligi aytilmaydi: boshqalarning buyurtmasini taxmin qilib bo'lmasin
            context['error'] = "Bunday buyurtma topilmadi. Raqam va telefonni tekshiring."
            return render(request, 'track.html', context)

        current = TRACK_STEP_INDEX.get(order.status)
        context.update({
            'order': order,
            'steps': [{'label': label, 'done': current is not None and index <= current}
                      for index, (_, label) in enumerate(TRACK_STEPS)],
            'is_stopped': current is None,
        })
        return render(request, 'track.html', context)


class TermsView(View):
    def get(self, request):
        return render(request, 'terms.html', {'categories': Category.objects.all()})


def robots_txt(request):
    lines = ['User-agent: *', 'Disallow: /admin/', 'Disallow: /admin_page/', 'Disallow: /profile/',
             f'Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml']
    return HttpResponse('\n'.join(lines) + '\n', content_type='text/plain')


def healthz(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    return JsonResponse({'status': 'ok'})
