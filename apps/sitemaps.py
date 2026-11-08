from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.models import Category, Product


class ProductSitemap(Sitemap):
    changefreq = 'weekly'

    def items(self):
        return Product.objects.order_by('id')

    def location(self, item):
        return reverse('product-detail', args=[item.slug])


class CategorySitemap(Sitemap):
    changefreq = 'weekly'

    def items(self):
        return Category.objects.exclude(slug__isnull=True).order_by('id')

    def location(self, item):
        return reverse('category_detail', args=[item.slug])
