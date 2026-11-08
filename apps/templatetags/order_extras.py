from django import template

register = template.Library()


@register.filter
def space_number(value):
    """1250000 -> '1 250 000' (dizayndagi JS Op.formatNumber bilan bir xil ko'rinish)."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return value
    return '{:,}'.format(n).replace(',', ' ')


@register.filter
def format_phone(value):
    """+998901234567 -> '+998 90 123 45 67'."""
    if not value:
        return ''
    digits = ''.join(ch for ch in str(value) if ch.isdigit())
    if digits.startswith('998') and len(digits) == 12:
        return '+998 {} {} {} {}'.format(digits[3:5], digits[5:8], digits[8:10], digits[10:12])
    return value


@register.filter
def initials(user):
    """Foydalanuvchi avatar harflari: F.I. bo'lmasa telefon raqamdan."""
    if not user:
        return ''
    first = (user.first_name or '').strip()
    last = (user.last_name or '').strip()
    if first or last:
        return (first[:1] + last[:1]).upper()
    phone = (user.phone_number or '')
    digits = ''.join(ch for ch in phone if ch.isdigit())
    return digits[-2:] if digits else '??'

@register.filter
def tagged(messages, tag):
    """Shu tegga ega xabarlar ro'yxati: {% with errs=messages|tagged:"field-password" %}.

    Forma xatolari maydon yoniga, umumiy xabarlar esa toast sifatida chiqishi uchun.
    """
    if not messages:
        return []
    return [m for m in messages if tag in m.tags.split()]


@register.filter
def untagged(messages, tags):
    """Berilgan teglarning (vergul bilan) birortasi ham bo'lmagan xabarlar — toastlar uchun."""
    if not messages:
        return []
    skip = set(tags.split(','))
    return [m for m in messages if not skip & set(m.tags.split())]
