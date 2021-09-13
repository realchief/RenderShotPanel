from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.urls import reverse

from colorfield.fields import ColorField
from rendershot_django.utils import get_random_code, post_message_to_slack, send_update_email


class Currencies(models.TextChoices):
    USD = 'usd', _('usd')


class PaymentTypes(models.TextChoices):
    PAYPAL = 'paypal', _('Paypal')
    COUPON = 'coupon', _('Coupon')
    CREDIT_REFUND = 'credit_refund', _('Credit Refund')
    PAYMENT_REFUND = 'payment_refund', _('Payment Refund')
    CREDIT_TRANSFER = 'credit_transfer', _('Credit Transfer')
    PROMOTION = 'promotion', _('Promotion')
    COST_BALANCE = 'cost_balance', _('Cost Balance')


class PaymentStatus(models.TextChoices):
    INITIATED = 'initiated', _('Initiated')
    PENDING = 'pending', _('Pending')
    COMPLETED = 'completed', _('Completed')
    CANCELLED = 'cancelled', _('Cancelled')
    INVALID = 'invalid', _('Invalid')


class Payment(models.Model):

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=100, null=True, choices=PaymentTypes.choices, default=PaymentTypes.PAYPAL)
    status = models.CharField(max_length=100, null=True, choices=PaymentStatus.choices, default=PaymentStatus.INITIATED)
    amount = models.FloatField(default=5.0, null=True)
    payment_id = models.CharField(max_length=200, null=True, blank=True)
    order_data = models.JSONField(null=True, blank=True)
    payment_data = models.JSONField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    currency = models.CharField(max_length=100, null=True, choices=Currencies.choices, default=Currencies.USD)

    def __init__(self, *args, **kwargs):
        self.status_signals = {'on_initiated': self.on_initiated,
                               'on_pending': self.on_pending,
                               'on_completed': self.on_completed,
                               'on_cancelled': self.on_cancelled,
                               'on_invalid': self.on_invalid}

        super(Payment, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        pre_save_model = Payment.objects.filter(pk=self.pk).first()
        super(Payment, self).save(*args, **kwargs)

        if not pre_save_model:
            self.created = True

        call_status_signals = True
        if pre_save_model and pre_save_model.status == self.status:
            call_status_signals = False

        status_signal = self.status_signals.get(f'on_{self.status.lower()}', None)
        call_status_signals and status_signal and status_signal()

    def on_initiated(self):
        self.slack_payment_update('on_payment_initiated')

    def on_pending(self):
        self.slack_payment_update('on_payment_pending')

    def on_completed(self):

        if self.type == PaymentTypes.PAYPAL:
            self.user.profile.credit += self.amount
        elif self.type == PaymentTypes.COUPON:
            self.user.profile.credit += self.amount
        elif self.type == PaymentTypes.CREDIT_REFUND:
            self.user.profile.credit += self.amount
        elif self.type == PaymentTypes.PAYMENT_REFUND:
            self.user.profile.credit -= self.amount
        elif self.type == PaymentTypes.CREDIT_TRANSFER:
            self.user.profile.credit += self.amount
        elif self.type == PaymentTypes.PROMOTION:
            self.user.profile.credit += self.amount
        elif self.type == PaymentTypes.COST_BALANCE:
            self.user.profile.credit -= self.amount  # could be negative

        self.user.save()
        self.email_payment_update()
        self.slack_payment_update('on_payment_completed')

    def on_cancelled(self):
        self.slack_payment_update('on_payment_cancelled')

    def on_invalid(self):
        self.slack_payment_update('on_payment_invalid')

    def get_email_subject(self):
        subject = 'Update'

        if self.type == PaymentTypes.PAYPAL:
            subject = 'Payment Update'
        elif self.type == PaymentTypes.COUPON:
            subject = 'Coupon Update'
        elif self.type == PaymentTypes.CREDIT_REFUND:
            subject = 'Credit Refund Update'
        elif self.type == PaymentTypes.PAYMENT_REFUND:
            subject = 'Payment Refund Update'
        elif self.type == PaymentTypes.CREDIT_TRANSFER:
            subject = 'Credit Transfer Update'
        elif self.type == PaymentTypes.PROMOTION:
            subject = 'Payment Promotion Update'
        elif self.type == PaymentTypes.COST_BALANCE:
            subject = 'Cost Balance Update'

        return subject

    def get_message_subject(self):
        message = 'Payment'

        if self.type == PaymentTypes.PAYPAL:
            message = f'Payment {self.payment_id} {self.status.capitalize()}'
        elif self.type == PaymentTypes.COUPON:
            message = f'Coupon Processed'
        elif self.type == PaymentTypes.CREDIT_REFUND:
            message = f'Credit Refund Processed'
        elif self.type == PaymentTypes.PAYMENT_REFUND:
            message = f'Payment Refund Processed'
        elif self.type == PaymentTypes.CREDIT_TRANSFER:
            message = f'Credit Transfer Processed'
        elif self.type == PaymentTypes.PROMOTION:
            message = f'Payment Promotion Processed'
        elif self.type == PaymentTypes.COST_BALANCE:
            message = f'Cost Balance Processed'

        return message

    def email_payment_update(self):
        # TODO disable for ingestion
        subject = self.get_email_subject()
        message = self.get_message_subject()

        context = {'subject': subject,
                   'description': message,
                   'paragraph_01': f'This is a official receipt/confirmation for : {self.payment_id}.\n'
                                   f'Amount : {self.amount}\n'
                                   f'Current Balance : {self.user.profile.balance}',
                   'paragraph_02': f'You can view and download invoices for the payments in your online panel',
                   'action_text': f'Payment List',
                   'action_url': reverse("invoices")}

        send_update_email(self.user, context, subject, message)

    def slack_payment_update(self, event):
        # TODO disable for ingestion
        data = {'user': self.user.username,
                'user_balance': self.user.profile.balance,
                'type': self.type,
                'status': self.status,
                'amount': self.amount,
                'payment_id': self.payment_id,
                }

        post_message_to_slack(event, event, data)


class PromotionPackage(models.Model):

    name = models.CharField(max_length=100, null=True)
    description = models.CharField(max_length=100, null=True)
    amount = models.FloatField(default=0.0, null=True)
    extra = models.IntegerField(default=0, null=True)
    show_in_dashboard = models.BooleanField(default=False, null=True)
    label_color = ColorField(default='#DF3F60', null=True)
    text_color = ColorField(default='#FFF', null=True)


class CouponCodes(models.Model):
    code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    is_redeemed = models.BooleanField(default=False, null=True)
    amount = models.FloatField(default=0.0, null=True, blank=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        if created:
            id_string = str(instance.id)
            random_str = get_random_code(lenght=7)
            instance.code = random_str + id_string
            instance.save()

    def __str__(self):
        return "%s" % (self.code,)


post_save.connect(CouponCodes.post_create, sender=CouponCodes)
