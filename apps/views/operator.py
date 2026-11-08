from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from apps.models import Order, Region
from apps.services import orders as order_service
from apps.services.orders import OrderError
from apps.utils import clean_text, parse_positive_int

NEW_ORDERS_LIMIT = 200

# Interfeysdagi holat nomi -> model holati
STATUS_MAP = {
    'packaging': Order.Status.PACKING,
    'shipping': Order.Status.DELIVERING,
    'delivered': Order.Status.DELIVERED,
    'pickup_later': Order.Status.LATER,
    'hold': Order.Status.HOLD,
    'returned': Order.Status.RETURNED,
    'cancelled': Order.Status.CANCELED,
    'archive': Order.Status.ARCHIVE,
}


@method_decorator(login_required, name='dispatch')
class OperatorRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_operator:
            messages.error(request, "Sizda operator panelidan foydalanish huquqi yo'q.")
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)


def _new_orders():
    return Order.objects.filter(status=Order.Status.NEW, operator__isnull=True)


class NewOrdersView(OperatorRequiredMixin, View):
    def get(self, request):
        pool = _new_orders().select_related('product', 'product__category', 'funnel', 'region').order_by('-created_at')
        return render(request, 'new-orders.html', {
            'orders': pool[:NEW_ORDERS_LIMIT],
            'regions': Region.objects.order_by('title'),
            'new_orders_count': pool.count(),
            'my_orders_count': Order.objects.filter(operator=request.user).count(),
        })


class TakeOrderView(OperatorRequiredMixin, View):
    def post(self, request, order_id):
        updated = _new_orders().filter(pk=order_id).update(operator=request.user)
        if updated:
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'message': "Bu buyurtmani boshqa operator allaqachon oldi."},
                            status=409)


class MyOrdersView(OperatorRequiredMixin, View):
    def get(self, request):
        orders = Order.objects.filter(operator=request.user).select_related(
            'product', 'funnel', 'region').order_by('-created_at')
        return render(request, 'my-orders.html', {
            'orders': orders,
            'regions': Region.objects.order_by('title'),
            'my_orders_count': orders.count(),
            'new_orders_count': _new_orders().count(),
        })


class OrderQuickStatusView(OperatorRequiredMixin, View):
    def post(self, request, order_id):
        get_object_or_404(Order, pk=order_id, operator=request.user)
        new_status = STATUS_MAP.get(request.POST.get('status'))
        if new_status is None:
            messages.error(request, "Holat noto'g'ri tanlandi.")
            return redirect('my-orders')
        try:
            order_service.change_status(order_id, new_status, operator=request.user,
                                        comment=clean_text(request.POST.get('comment'), 2000))
        except OrderError as exc:
            messages.error(request, str(exc))
            return redirect('my-orders')
        messages.success(request, f"Buyurtma #{order_id} holati yangilandi.")
        return redirect('my-orders')


class OrderDetailView(OperatorRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(Order.objects.select_related('product', 'funnel', 'region', 'district'),
                                  pk=order_id, operator=request.user)
        regions = Region.objects.order_by('title').prefetch_related('districts')
        return render(request, 'order-detail.html', {
            'order': order,
            'previous_orders': Order.objects.filter(phone_number=order.phone_number).exclude(pk=order.pk)
            .select_related('product').order_by('-created_at')[:10],
            'regions': regions,
            'districts_map': {
                region.id: sorted(((d.id, d.title) for d in region.districts.all()), key=lambda item: item[1])
                for region in regions
            },
        })

    def post(self, request, order_id):
        get_object_or_404(Order, pk=order_id, operator=request.user)
        new_status = STATUS_MAP.get(request.POST.get('status'))
        if new_status is None:
            messages.error(request, "Buyurtma holatini tanlang.")
            return redirect('order-detail', order_id=order_id)
        try:
            order_service.update_order(
                order_id, request.user,
                new_status=new_status,
                full_name=clean_text(request.POST.get('customer_name')),
                phone=request.POST.get('phone', ''),
                region_id=parse_positive_int(request.POST.get('region')),
                district_id=parse_positive_int(request.POST.get('district')),
                address=clean_text(request.POST.get('address'), 1000),
                quantity=parse_positive_int(request.POST.get('quantity')),
                comment=clean_text(request.POST.get('comment'), 2000),
            )
        except OrderError as exc:
            messages.error(request, str(exc))
            return redirect('order-detail', order_id=order_id)
        messages.success(request, f"Buyurtma #{order_id} saqlandi.")
        return redirect('my-orders')
