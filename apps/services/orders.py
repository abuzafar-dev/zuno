"""Buyurtma hayot sikli: joylashtirish, ombor, status o'tishlari, komissiya."""
from django.db import transaction
from django.db.models import F

from apps.models import District, Order, Product, Region, Survey
from apps.services import wallet
from apps.utils import normalize_phone


class OrderError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato matni bilan."""


S = Order.Status

ALLOWED_TRANSITIONS = {
    S.NEW: {S.PACKING, S.LATER, S.HOLD, S.CANCELED, S.ARCHIVE},
    S.LATER: {S.PACKING, S.HOLD, S.CANCELED, S.ARCHIVE},
    S.HOLD: {S.PACKING, S.LATER, S.CANCELED, S.ARCHIVE},
    S.PACKING: {S.DELIVERING, S.LATER, S.HOLD, S.CANCELED},
    S.DELIVERING: {S.DELIVERED, S.RETURNED, S.HOLD},
    S.DELIVERED: {S.RETURNED, S.ARCHIVE},
    S.RETURNED: {S.ARCHIVE},
    S.CANCELED: {S.ARCHIVE},
    S.ARCHIVE: set(),
}

# Bu holatlarda tovar omborda mijoz uchun band turadi
_HOLDS_STOCK = {S.NEW, S.LATER, S.HOLD, S.PACKING, S.DELIVERING}

SURVEY_STATUS = {
    S.DELIVERED: Survey.Status.CONFIRMED,
    S.RETURNED: Survey.Status.REJECTED,
    S.CANCELED: Survey.Status.REJECTED,
}


def valid_discount(product, funnel):
    """Amaldagi chegirma. Eski noto'g'ri yozuvlar (manfiy, narxdan katta) hisobga olinmaydi."""
    discount = funnel.discount_price if funnel else None
    return discount if discount and 0 < discount < product.price else 0


def unit_price(product, funnel=None):
    return product.price - valid_discount(product, funnel)


def unit_commission(product, funnel=None):
    """Hamkor ulushi: chegirma komissiyasidan beriladi, kompaniya zarar ko'rmaydi."""
    return max(product.commission - valid_discount(product, funnel), 0)


def _is_self_purchase(order, funnel):
    owner = funnel.owner if funnel else None
    return bool(owner and (order.user_id == owner.pk or order.phone_number == owner.phone_number))


@transaction.atomic
def place_order(order, product, funnel=None):
    """Formadan kelgan saqlanmagan buyurtmani joylashtiradi va tovarni band qiladi."""
    locked = Product.objects.select_for_update().get(pk=product.pk)
    if order.quantity > locked.stock_quantity:
        if locked.stock_quantity == 0:
            raise OrderError("Afsuski, bu mahsulot hozir tugagan.")
        raise OrderError(f"Omborda faqat {locked.stock_quantity} dona qolgan.")

    order.product = locked
    order.funnel = funnel
    order.unit_price = unit_price(locked, funnel)
    order.delivery_price = locked.delivery_price
    order.unit_commission = 0 if _is_self_purchase(order, funnel) else unit_commission(locked, funnel)
    order.total_price = order.unit_price * order.quantity + order.delivery_price
    order.save()

    Product.objects.filter(pk=locked.pk).update(stock_quantity=F('stock_quantity') - order.quantity)
    return order


def _return_stock(order, quantity):
    if order.product_id and quantity:
        Product.objects.filter(pk=order.product_id).update(stock_quantity=F('stock_quantity') + quantity)


def _apply_status(order, new_status):
    old = order.status
    if new_status == old:
        return
    if new_status not in ALLOWED_TRANSITIONS.get(old, set()):
        raise OrderError(f"«{order.get_status_display()}» holatidan «{S(new_status).label}» holatiga o'tib bo'lmaydi.")

    releases = old in _HOLDS_STOCK and new_status in {S.CANCELED, S.RETURNED, S.ARCHIVE}
    if releases or (old == S.DELIVERED and new_status == S.RETURNED):
        _return_stock(order, order.quantity)
    if new_status == S.DELIVERED:
        wallet.credit_commission(order)
    elif new_status == S.RETURNED and old == S.DELIVERED:
        wallet.reverse_commission(order)
    order.status = new_status


def _log_survey(order, operator, comment):
    if order.funnel_id:
        Survey.objects.create(
            operator=operator,
            funnel=order.funnel,
            buyer_name=order.full_name,
            region=order.region,
            phone_number=order.phone_number,
            status=SURVEY_STATUS.get(order.status, Survey.Status.PROCESSING),
            comment=comment,
        )


def _locked(order_id, operator=None):
    orders = Order.objects.select_for_update(of=('self',)).select_related('funnel', 'funnel__owner')
    if operator is not None:
        orders = orders.filter(operator=operator)
    return orders.get(pk=order_id)


@transaction.atomic
def change_status(order_id, new_status, *, operator=None, comment=''):
    """Faqat statusni o'zgartiradi (tezkor tugma va admin shu yerdan o'tadi)."""
    order = _locked(order_id, operator)
    _apply_status(order, new_status)
    order.save(update_fields=['status', 'updated_at'])
    if operator is not None:
        _log_survey(order, operator, comment)
    return order


@transaction.atomic
def update_order(order_id, operator, *, new_status, full_name, phone, region_id, district_id, address, quantity,
                 comment=''):
    """Operator qo'ng'iroqdan keyin buyurtmani aniqlashtiradi."""
    order = _locked(order_id, operator)

    if quantity is not None and quantity != order.quantity:
        if order.status not in _HOLDS_STOCK:
            raise OrderError("Bu holatdagi buyurtma sonini o'zgartirib bo'lmaydi.")
        delta = quantity - order.quantity
        if delta > 0 and order.product_id:
            changed = Product.objects.filter(pk=order.product_id, stock_quantity__gte=delta).update(
                stock_quantity=F('stock_quantity') - delta)
            if not changed:
                raise OrderError("Omborda buncha mahsulot yo'q.")
        elif delta < 0:
            _return_stock(order, -delta)
        order.quantity = quantity
        order.total_price = order.unit_price * quantity + order.delivery_price

    if phone:
        normalized = normalize_phone(phone)
        if not normalized:
            raise OrderError("Telefon raqam noto'g'ri.")
        order.phone_number = normalized

    region = Region.objects.filter(pk=region_id).first() if region_id else None
    order.region = region
    order.district = District.objects.filter(pk=district_id, region=region).first() if region and district_id else None
    order.full_name = full_name or order.full_name
    order.shipping_address = address

    _apply_status(order, new_status)
    order.save()
    _log_survey(order, operator, comment)
    return order
