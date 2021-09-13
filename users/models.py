from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
import pytz
from rest_framework.authtoken.models import Token

from payment.models import PaymentStatus
from rendershot_django.utils import post_message_to_slack
from system.dbx_utils import DropboxHandler


class AccountTypes(models.TextChoices):
    PERSONAL = 'personal', _('Personal')
    COMPANY = 'company', _('Company')


class Profile(models.Model):

    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    account_type = models.CharField(max_length=100, null=True, choices=AccountTypes.choices, default=AccountTypes.PERSONAL)
    company_name = models.CharField(max_length=100, null=True)
    city = models.CharField(max_length=100, null=True)
    country = models.TextField(max_length=50, null=True, choices=pytz.country_names.items())
    address = models.CharField(max_length=1000, null=True)
    zip_code = models.CharField(max_length=100, null=True)
    phone = models.CharField(max_length=100, null=True)
    vat = models.CharField(max_length=100, null=True)
    payment_allowed = models.BooleanField(default=False, null=True)
    credit = models.FloatField(default=0.0, null=True)
    blocked = models.BooleanField(default=False, null=True)
    receive_job_email_notifs = models.BooleanField(default=True, null=True)
    ip_address = models.CharField(max_length=250, null=True)
    dropbox_outputs_share_link = models.CharField(max_length=250, null=True)
    rate_multiplier = models.FloatField(default=1.0, null=True)
    reset_password_required = models.BooleanField(default=False, null=True)
    chunk_size_override = models.IntegerField(default=1, null=True)

    def __str__(self):
        return self.user.username

    @property
    def total_payment(self):
        total = 0
        for payment in self.user.payment_set.all():
            if type(payment.amount) in [int, float] and payment.status == PaymentStatus.COMPLETED:
                total += payment.amount
        return total

    @property
    def payment_count(self):
        return len(self.user.payment_set.all())

    @property
    def ticket_count(self):
        return len(self.user.ticket_set.all())

    @property
    def job_count(self):
        return len(self.user.job_set.exclude(status__name='deleted').all())

    @property
    def balance(self):
        jobs = self.user.job_set.all()
        spent_amount = float()

        for job in jobs:
            spent_amount += job.cost

        balance = self.credit - (spent_amount * self.user.profile.rate_multiplier)
        return balance

    def is_network_rendering_allowed(self):
        return self.user.groups.filter(name='network_rendering').exists()


@receiver(post_save, sender=User)
def update_user_profile(sender, instance, created, **kwargs):
    if created:
        Token.objects.create(user=instance)
        Profile.objects.create(user=instance)
        # TODO disable for ingestion
        post_message_to_slack("New Registration",
                              f"New User : {instance.username} Registered",
                              {'user': instance.username,
                               'email': instance.email})

    instance.profile.save()


@receiver(post_delete, sender=User)
def update_user_dropbox(sender, instance, **kwargs):

    # TODO disable for ingestion
    dbx = DropboxHandler(instance)
    if dbx.dropbox:
        dbx.delete_user_folders()
