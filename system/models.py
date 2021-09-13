from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


channel_layer = get_channel_layer()


class SystemStatus(models.TextChoices):
    ONLINE = 'online', _('Online')
    OFFLINE = 'offline', _('Offline')
    MAINTENANCE = 'maintenance', _('Maintenance')


class Setting(models.Model):
    config_name = models.CharField(_('config_name'), max_length=150, null=True, blank=True)
    is_active = models.BooleanField(_('is_active'), null=True, max_length=150, default=False)
    paypal_setting = models.JSONField(null=True, blank=True)
    client_app_setting = models.JSONField(null=True, blank=True)
    system_status = models.CharField(max_length=100, null=True, choices=SystemStatus.choices, default=SystemStatus.ONLINE)
    ban_disposable_emails = models.BooleanField(null=True, max_length=150, default=False)
    initial_account_credit = models.IntegerField(default=10, null=True)
    minimum_payment_amount = models.IntegerField(default=30, null=True)

    def __str__(self):
        return self.config_name

    @classmethod
    def post_save(cls, sender, instance, created, *args, **kwargs):
        if created:
            return
        if not instance.is_active:
            return
        from system.serializers import SystemStatusSerializer

        serialized_setting = SystemStatusSerializer(instance)
        async_to_sync(channel_layer.group_send)('client', {'type': 'send_message',
                                                           'event': 'system_status_changed',
                                                           'data': serialized_setting.data})


post_save.connect(Setting.post_save, sender=Setting)


class SocketConnection(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    channel = models.CharField(_('channel'), max_length=200, null=True, blank=True)
    group = models.CharField(_('group'), max_length=200, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

