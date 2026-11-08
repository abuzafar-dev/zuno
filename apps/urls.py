from django.contrib.sitemaps.views import sitemap
from django.urls import path

from apps.sitemaps import CategorySitemap, ProductSitemap
from apps.views import accounts, cabinet, operator, storefront

urlpatterns = [
    # Vitrina
    path('', storefront.HomeView.as_view(), name='home'),
    path('search/', storefront.SearchProductView.as_view(), name='search_product'),
    path('category/', storefront.ShopView.as_view(), name='shop'),
    path('category/<slug:slug>/', storefront.CategoryDetailView.as_view(), name='category_detail'),
    path('product-detail/<slug:slug>/', storefront.ProductDetailView.as_view(), name='product-detail'),
    path('funnel/<int:funnel_id>/', storefront.FunnelDetailView.as_view(), name='funnel-detail'),
    path('track/', storefront.TrackOrderView.as_view(), name='track-order'),
    path('shartlar/', storefront.TermsView.as_view(), name='terms'),
    path('robots.txt', storefront.robots_txt, name='robots'),
    path('sitemap.xml', sitemap, {'sitemaps': {'products': ProductSitemap, 'categories': CategorySitemap}},
         name='sitemap'),
    path('healthz/', storefront.healthz, name='healthz'),

    # Hisob
    path('login/', accounts.LoginView.as_view(), name='login'),
    path('register/', accounts.RegisterView.as_view(), name='register'),
    path('logout/', accounts.LogoutView.as_view(), name='logout'),
    path('profile/settings/', accounts.ProfileSettingsView.as_view(), name='profile-settings'),
    path('get-districts/<int:region_id>/', accounts.get_districts, name='get-districts'),

    # Hamkor kabineti
    path('admin_page/', cabinet.DashboardView.as_view(), name='dashboard'),
    path('admin_page/market/', cabinet.MarketView.as_view(), name='market'),
    path('admin_page/market/<slug:category_slug>/', cabinet.MarketView.as_view(), name='market_by_category'),
    path('admin_page/links/', cabinet.LinksView.as_view(), name='links'),
    path('admin_page/links/delete/<int:link_id>/', cabinet.DeleteLinkView.as_view(), name='delete_link'),
    path('admin_page/stats/', cabinet.StatisticView.as_view(), name='stats'),
    path('admin_page/competition/', cabinet.CompetitionView.as_view(), name='competition'),
    path('admin_page/withdraw/', cabinet.BalanceView.as_view(), name='balance'),
    path('admin_page/requests/', cabinet.SurveyView.as_view(), name='requests'),
    path('profile/referral/', cabinet.ReferralView.as_view(), name='referral'),

    # Operator paneli
    path('admin_page/orders/new/', operator.NewOrdersView.as_view(), name='new-orders'),
    path('admin_page/orders/my/', operator.MyOrdersView.as_view(), name='my-orders'),
    path('admin_page/orders/<int:order_id>/', operator.OrderDetailView.as_view(), name='order-detail'),
    path('admin_page/orders/<int:order_id>/take/', operator.TakeOrderView.as_view(), name='order-take'),
    path('admin_page/orders/<int:order_id>/status/', operator.OrderQuickStatusView.as_view(),
         name='order-quick-status'),
]
