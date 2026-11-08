from django.contrib import admin, messages
from django.contrib.admin import TabularInline, ModelAdmin
from django.contrib.auth.admin import UserAdmin

from apps.models import (BalanceTransaction, Category, Competition, CompetitionResult, District, Funnel, Order, Product,
                         ProductImage, Region, Survey, User, Withdrawal)
from apps.services import orders as order_service, wallet


@admin.register(User)
class UserAdmin(UserAdmin):
    ordering = ('phone_number',)
    list_display = ('phone_number', 'first_name', 'last_name', 'region', 'district',
                    'is_operator', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_operator', 'region', 'district')
    list_editable = ('is_operator',)
    search_fields = ('phone_number', 'first_name', 'last_name', 'telegram_id')

    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('first_name', 'last_name', 'region', 'district', 'telegram_id', 'bio')}),
        ('Ruxsatlar', {'fields': ('is_active', 'is_operator', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Muhim sanalar', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password', 'first_name', 'last_name', 'region', 'district',
                       'is_active', 'is_operator', 'is_staff'),
        }),
    )

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('id', 'title', 'slug', 'parent', 'image')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('parent',)
    search_fields = ('title', 'slug')


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ('id', 'title', 'category', 'price', 'commission', 'delivery_price', 'stock_quantity', 'created_at')
    prepopulated_fields = {'slug': ('title',)}
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'description')
    inlines = [ProductImageInline]


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ('id', 'full_name', 'phone_number', 'product', 'quantity', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone_number')
    readonly_fields = ('unit_price', 'delivery_price', 'unit_commission', 'total_price')

    def save_model(self, request, obj, form, change):
        # Status faqat servis orqali o'zgaradi: ombor va komissiya shu yerda hisoblanadi
        if change and 'status' in form.changed_data:
            new_status, obj.status = obj.status, form.initial['status']
            super().save_model(request, obj, form, change)
            try:
                order_service.change_status(obj.pk, new_status)
            except order_service.OrderError as exc:
                self.message_user(request, str(exc), messages.ERROR)
            return
        super().save_model(request, obj, form, change)


@admin.register(Region)
class RegionAdmin(ModelAdmin):
    list_display = ('id', 'title')
    search_fields = ('title',)


@admin.register(District)
class DistrictAdmin(ModelAdmin):
    list_display = ('id', 'title', 'region')
    list_filter = ('region',)
    search_fields = ('title',)


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title',)


@admin.register(CompetitionResult)
class CompetitionResultAdmin(admin.ModelAdmin):
    list_display = ('competition', 'display_name', 'sold_count', 'updated_at')
    list_filter = ('competition',)
    search_fields = ('display_name',)
    ordering = ('-sold_count',)


@admin.register(Funnel)
class FunnelAdmin(ModelAdmin):
    list_display = ('id', 'title', 'product', 'owner', 'discount_price', 'views_count', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'owner__phone_number')
    raw_id_fields = ('product', 'owner')


@admin.register(Survey)
class SurveyAdmin(ModelAdmin):
    list_display = ('id', 'buyer_name', 'phone_number', 'status', 'operator', 'funnel', 'created_at')
    list_filter = ('status',)
    search_fields = ('buyer_name', 'phone_number')


@admin.register(BalanceTransaction)
class BalanceTransactionAdmin(ModelAdmin):
    """Jurnal faqat o'qish uchun: balansni qo'lda o'zgartirib bo'lmaydi."""
    list_display = ('id', 'user', 'kind', 'amount', 'order', 'created_at')
    list_filter = ('kind',)
    search_fields = ('user__phone_number',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'card_number', 'amount', 'status', 'created_at', 'processed_at')
    list_filter = ('status',)
    search_fields = ('card_number', 'user__phone_number')
    readonly_fields = ('created_at',)
    actions = ['mark_completed', 'mark_rejected']

    def mark_completed(self, request, queryset):
        for pk in wallet.open_withdrawal_ids(queryset):
            wallet.settle_withdrawal(pk, Withdrawal.Status.COMPLETED, refund=False)

    mark_completed.short_description = "Tanlanganlarni 'Bajarildi' deb belgilash"

    def mark_rejected(self, request, queryset):
        for pk in wallet.open_withdrawal_ids(queryset):
            wallet.settle_withdrawal(pk, Withdrawal.Status.REJECTED, refund=True)

    mark_rejected.short_description = "Tanlanganlarni rad etish (pul hisobga qaytadi)"
