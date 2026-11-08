import uuid
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from apps.forms import WithdrawalForm
from apps.models import BalanceTransaction, Category, Competition, Funnel, Order, Product, Survey, User, Withdrawal
from apps.services.competition import recalculate_results
from apps.utils import clean_text, parse_positive_int
from apps.views.common import paginate


def parse_funnel_discount(raw, product):
    """Chegirma hamkor komissiyasidan beriladi: butun son, 0 <= chegirma <= komissiya.
    (value, error) qaytaradi."""
    raw = (raw or '').strip()
    if not raw:
        return None, None
    try:
        value = int(raw)
    except ValueError:
        return None, "Chegirma butun son bo'lishi kerak."
    if value < 0 or value > product.commission or value >= product.price:
        return None, "Chegirma 0 dan kam va komissiyadan ko'p bo'lmasligi kerak."
    return value, None


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    def get(self, request):
        funnels = Funnel.objects.filter(owner=request.user)
        orders = Order.objects.filter(funnel__owner=request.user)
        earned = request.user.transactions.aggregate(total=Sum('amount'))['total'] or 0
        return render(request, 'dashboard.html', {
            'links_count': funnels.filter(is_active=True).count(),
            'orders_count': orders.count(),
            'delivered_count': orders.filter(status=Order.Status.DELIVERED).count(),
            'earned_total': earned,
        })


@method_decorator(login_required, name='dispatch')
class MarketView(View):
    def get(self, request, category_slug=None):
        products = Product.objects.order_by('-id')
        selected_category = None
        if category_slug:
            selected_category = get_object_or_404(Category, slug=category_slug)
            products = products.filter(category=selected_category)
        search_query = clean_text(request.GET.get('q'), 100)
        if search_query:
            products = products.filter(title__icontains=search_query)
        return render(request, 'market.html', {
            'categories': Category.objects.all(),
            'products': paginate(request, products, 9),
            'selected_category': selected_category,
            'search_query': search_query,
            'page_params': urlencode({'q': search_query}) if search_query else '',
        })

    def post(self, request, category_slug=None):
        product_id = parse_positive_int(request.POST.get('product_id'))
        title = clean_text(request.POST.get('title'))
        if not product_id:
            messages.error(request, "Mahsulot tanlanmagan.")
            return redirect(request.path)
        product = get_object_or_404(Product, id=product_id)

        if not title:
            messages.error(request, "Oqim nomini kiriting.")
            return redirect(request.path)

        discount, discount_error = parse_funnel_discount(request.POST.get('discount'), product)
        if discount_error:
            messages.error(request, discount_error)
            return redirect(request.path)

        Funnel.objects.create(
            title=title,
            slug=f"{slugify(title)[:240] or 'oqim'}-{uuid.uuid4().hex[:6]}",
            product=product,
            owner=request.user,
            discount_price=discount,
        )
        messages.success(request, f"'{title}' oqimi muvaffaqiyatli yaratildi!")
        return redirect('links')


@method_decorator(login_required, name='dispatch')
class StatisticView(View):
    def get(self, request):
        counts = {f'{status}_num': Count('orders', filter=Q(orders__status=status)) for status in Order.Status.values}
        owned = Funnel.objects.filter(owner=request.user)
        funnels = owned.annotate(**counts).order_by('-created_at')
        by_status = dict(Order.objects.filter(funnel__owner=request.user).order_by().values_list('status')
                         .annotate(total=Count('id')))
        return render(request, 'statistic.html', {
            'funnels': paginate(request, funnels.select_related('product'), 10),
            'totals': {
                'views': owned.aggregate(total=Sum('views_count'))['total'] or 0,
                **{status: by_status.get(status, 0) for status in Order.Status.values},
            },
        })


@method_decorator(login_required, name='dispatch')
class LinksView(View):
    def get(self, request):
        query = clean_text(request.GET.get('q'), 100)
        links = Funnel.objects.filter(owner=request.user, is_active=True).select_related('product').order_by(
            '-created_at')
        if query:
            link_id = parse_positive_int(query)
            links = links.filter(id=link_id) if link_id else links.filter(title__icontains=query)
        return render(request, 'links.html', {
            'links': paginate(request, links, 6),
            'query': query,
            'page_params': urlencode({'q': query}) if query else '',
        })


@method_decorator(login_required, name='dispatch')
class DeleteLinkView(View):
    def post(self, request, link_id):
        # Yopiladi, o'chirilmaydi: bog'langan buyurtmalar va komissiya tarixi saqlansin
        funnel = get_object_or_404(Funnel, id=link_id, owner=request.user)
        funnel.is_active = False
        funnel.save(update_fields=['is_active'])
        return JsonResponse({'success': True})


class CompetitionView(View):
    RESULTS_CACHE_TTL = 10 * 60

    def get(self, request):
        competition = Competition.objects.filter(is_active=True).order_by('-start_date').first()
        results = []
        if competition:
            cache_key = f"competition:{competition.pk}:results"
            results = cache.get(cache_key)
            if results is None:
                recalculate_results(competition)
                results = list(competition.results.order_by('-sold_count').values('display_name', 'sold_count'))
                cache.set(cache_key, results, self.RESULTS_CACHE_TTL)
        return render(request, 'contest.html', {'competition': competition, 'results': results})


@method_decorator(login_required, name='dispatch')
class BalanceView(View):
    def get(self, request):
        return render(request, 'balance.html', {
            'balance': request.user.main_balance,
            'pending_balance': request.user.pending_balance,
            'withdrawals': paginate(request, request.user.withdrawals.order_by('-created_at'), 10),
            'transactions': BalanceTransaction.objects.filter(user=request.user).select_related('order')[:10],
        })

    def post(self, request):
        form = WithdrawalForm(request.POST, user=request.user)
        if not form.is_valid():
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
            return redirect('balance')

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            amount = form.cleaned_data['amount']
            if amount > user.main_balance:
                messages.error(request, "Hisobingizdagi mavjud summadan ko'p miqdor kiritdingiz.")
                return redirect('balance')

            withdrawal = form.save(commit=False)
            withdrawal.user = user
            withdrawal.status = Withdrawal.Status.PENDING
            withdrawal.save()

            user.main_balance -= amount
            user.pending_balance += amount
            user.save(update_fields=['main_balance', 'pending_balance'])

        messages.success(request, "So'rovingiz qabul qilindi. Operator tez orada ko'rib chiqadi.")
        return redirect('balance')


@method_decorator(login_required, name='dispatch')
class ReferralView(View):
    def get(self, request):
        referrals = request.user.referrals.order_by('-created_at')
        return render(request, 'referral.html', {
            'referral_link': request.build_absolute_uri(reverse('register')) + f'?id={request.user.id}',
            'referral_count': referrals.count(),
            'referrals': paginate(request, referrals, 10),
        })


@method_decorator(login_required, name='dispatch')
class SurveyView(View):
    def get(self, request):
        query = clean_text(request.GET.get('q'), 100)
        status_filter = clean_text(request.GET.get('status'), 20)

        surveys = Survey.objects.filter(funnel__owner=request.user).select_related(
            'operator', 'funnel', 'region').order_by('-created_at')
        if query:
            survey_id = parse_positive_int(query) if query.isdigit() else None
            surveys = (surveys.filter(id=survey_id) if survey_id else
                       surveys.filter(Q(buyer_name__icontains=query) | Q(phone_number__icontains=query)))
        if status_filter:
            surveys = surveys.filter(status=status_filter)

        return render(request, 'questionnaire.html', {
            'surveys': paginate(request, surveys, 10),
            'query': query,
            'status_filter': status_filter,
            'status_choices': Survey.Status.choices,
            'page_params': urlencode({k: v for k, v in (('q', query), ('status', status_filter)) if v}),
        })
