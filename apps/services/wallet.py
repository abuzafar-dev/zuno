"""Hamkor hamyoni. Har bir pul harakati BalanceTransaction jurnaliga yoziladi."""
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.models import BalanceTransaction, User, Withdrawal

Kind = BalanceTransaction.Kind
_OPEN = [Withdrawal.Status.PENDING, Withdrawal.Status.PROCESSING]


def credit_commission(order):
    """Yetkazilgan buyurtma uchun bir marta to'lanadi (jurnaldagi unique cheklov kafolatlaydi)."""
    owner_id = order.funnel.owner_id if order.funnel_id else None
    amount = order.commission_total
    if not owner_id or amount <= 0:
        return
    _, created = BalanceTransaction.objects.get_or_create(
        order=order, kind=Kind.COMMISSION, defaults={'user_id': owner_id, 'amount': amount})
    if created:
        User.objects.filter(pk=owner_id).update(main_balance=F('main_balance') + amount)


def reverse_commission(order):
    """Yetkazilgandan keyin qaytarilsa, komissiya hisobdan qaytariladi."""
    credit = BalanceTransaction.objects.filter(order=order, kind=Kind.COMMISSION).first()
    if credit is None:
        return
    _, created = BalanceTransaction.objects.get_or_create(
        order=order, kind=Kind.REVERSAL, defaults={'user_id': credit.user_id, 'amount': -credit.amount})
    if created:
        User.objects.filter(pk=credit.user_id).update(main_balance=F('main_balance') - credit.amount)


def settle_withdrawal(pk, new_status, *, refund):
    """So'rov va foydalanuvchi qatori qulflanadi: ikki admin bir vaqtda bossa ham balans bir marta o'zgaradi."""
    with transaction.atomic():
        withdrawal = Withdrawal.objects.select_for_update().filter(pk=pk, status__in=_OPEN).first()
        if withdrawal is None:
            return False
        user = User.objects.select_for_update().get(pk=withdrawal.user_id)
        user.pending_balance -= withdrawal.amount
        if refund:
            user.main_balance += withdrawal.amount
        user.save(update_fields=['main_balance', 'pending_balance'])
        withdrawal.status = new_status
        withdrawal.processed_at = timezone.now()
        withdrawal.save(update_fields=['status', 'processed_at'])
    return True


def open_withdrawal_ids(queryset):
    return list(queryset.filter(status__in=_OPEN).values_list('pk', flat=True))
