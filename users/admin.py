from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from users.models import Profile


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['blocked',
                    'user',
                    'credit',
                    'account_type',
                    'company_name',
                    'city',
                    'country',
                    'payment_allowed',
                    'ip_address',
                    'rate_multiplier'
                    ]

    search_fields = ('user__username', )
    list_display_links = ['user', ]
    list_editable = ('blocked',)


admin.site.register(Profile, ProfileAdmin)


class MyUserAdmin(UserAdmin):
    ordering = ('date_joined', )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')


admin.site.unregister(User)
admin.site.register(User, MyUserAdmin)

