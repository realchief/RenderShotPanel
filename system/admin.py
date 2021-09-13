import json

from django.db import models
from system.models import Setting, SocketConnection
from django.utils.translation import gettext_lazy as _
from django_json_widget.widgets import JSONEditorWidget

from django.contrib import admin


class SystemSetting(admin.ModelAdmin):
    list_display = [
        'config_name',
        'is_active',
        'system_status',
        'ban_disposable_emails',
        'initial_account_credit',
        'minimum_payment_amount',
    ]
    list_editable = [
        'is_active',
        'system_status',
        'ban_disposable_emails',
        'initial_account_credit',
        'minimum_payment_amount',
    ]

    fieldsets = ((_('General Setting'), {'fields': ('config_name',
                                                    'is_active',
                                                    'system_status',
                                                    'ban_disposable_emails',
                                                    'initial_account_credit',
                                                    'minimum_payment_amount')}),
                 (_('Paypal Settings'), {'fields': ('paypal_setting', )}),
                 (_('Client App Settings'), {'fields': ('client_app_setting', )}),
                 )

    formfield_overrides = {models.JSONField: {'widget': JSONEditorWidget}, }


class SocketConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'channel', 'group', 'date_created', 'date_modified']


admin.site.register(Setting, SystemSetting)
admin.site.register(SocketConnection, SocketConnectionAdmin)
