from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.urls')),
]

# Kichik o'rnatishlar uchun: alohida nginx bo'lmasa Django media fayllarni o'zi beradi
if settings.SERVE_MEDIA:
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]
