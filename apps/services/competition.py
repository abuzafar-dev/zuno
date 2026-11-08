"""Konkurs reytingi: faqat haqiqatan yetkazilgan buyurtmalar hisoblanadi."""
from django.db.models import Count, Q

from apps.models import CompetitionResult, Order, User


def recalculate_results(competition):
    leaderboard = User.objects.annotate(
        sold_count=Count(
            'owned_funnels__orders',
            filter=Q(
                owned_funnels__orders__created_at__range=(competition.start_date, competition.end_date),
                owned_funnels__orders__status=Order.Status.DELIVERED,
            ),
            distinct=True,
        )
    ).filter(sold_count__gt=0)

    seen = []
    for user in leaderboard:
        seen.append(user.pk)
        CompetitionResult.objects.update_or_create(
            competition=competition,
            user=user,
            defaults={
                'display_name': f"{user.first_name} {user.last_name}".strip() or 'Hamkor',
                'sold_count': user.sold_count,
            },
        )
    competition.results.exclude(user__in=seen).delete()
