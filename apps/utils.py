"""Ilova bo'ylab ishlatiladigan kichik yordamchilar. Bu modul modellarni import qilmaydi."""
import re
import uuid

from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify

_UZ_PHONE = re.compile(r'^(?:998)?(\d{9})$')


def normalize_phone(raw):
    """Telefonni yagona ko'rinishga keltiradi: '+998901234567'. Noto'g'ri bo'lsa ''."""
    digits = re.sub(r'\D', '', raw or '')
    match = _UZ_PHONE.match(digits)
    return f'+998{match.group(1)}' if match else ''


def clean_text(raw, max_length=255):
    """So'rovdan kelgan matn: PostgreSQL NUL belgini qabul qilmaydi, uzunligi ustun bilan cheklanadi."""
    return (raw or '').replace('\x00', '').strip()[:max_length]


def parse_positive_int(raw):
    """Musbat butun son yoki None - noto'g'ri qiymat 500 xato bermasin."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if 0 < value <= 2_147_483_647 else None


def unique_slug(model, text, *, fallback, exclude_pk=None):
    """Takrorlanmas slug. Lotin harfi bo'lmagan nomda fallback ishlatiladi."""
    max_length = model._meta.get_field('slug').max_length
    base = slugify(text or '')[:max_length - 8].strip('-') or fallback
    slug = base
    others = model.objects.exclude(pk=exclude_pk) if exclude_pk else model.objects.all()
    while others.filter(slug=slug).exists():
        slug = f'{base}-{uuid.uuid4().hex[:6]}'
    return slug


def client_ip(request):
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


def is_rate_limited(scope, identifier, *, limit, window):
    """Oynada urinishlarni sanaydi. Chegaradan oshsa True."""
    key = f'throttle:{scope}:{identifier}'
    cache.add(key, 0, window)
    try:
        return cache.incr(key) > limit
    except ValueError:  # kalit shu orada muddati tugab o'chgan
        cache.set(key, 1, window)
        return False
