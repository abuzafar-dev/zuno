from django.core.paginator import Paginator


def paginate(request, queryset, per_page):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))
