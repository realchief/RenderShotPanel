from django.contrib import admin
from payment.models import Payment, PromotionPackage, CouponCodes


class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'amount', 'payment_id', 'type', 'date_modified']
    search_fields = ('user__username', 'status', 'amount', 'payment_id', 'type', 'date_modified')


class PromotionPackageAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'description',
        'amount',
        'extra',
        'show_in_dashboard',
        'label_color',
        'text_color',
    ]
    list_editable = [
                     'description',
                     'amount',
                     'extra',
                     'show_in_dashboard',
                     'label_color',
                     'text_color',
    ]


class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'amount', 'is_redeemed']
    readonly_fields = ['code']
    search_fields = ('code', 'amount', 'is_redeemed')


admin.site.register(Payment, PaymentAdmin)
admin.site.register(PromotionPackage, PromotionPackageAdmin)
admin.site.register(CouponCodes, CouponAdmin)
