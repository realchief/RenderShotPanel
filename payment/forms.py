from django import forms
from django.forms.widgets import ChoiceWidget
from django.utils.translation import gettext, gettext_lazy as _
from django.core.validators import RegexValidator

from payment.models import *
numeric = RegexValidator(r'^[0-9+]', 'Only digit characters.')


class PromotionPackageCustomRadioSelect(ChoiceWidget):
    input_type = 'radio'
    template_name = 'payment/promotion_package_radio_widget.html'
    option_template_name = 'payment/promotion_package_radio_option_widget.html'


class PaymentForm(forms.Form):
    request_type = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'id': 'request_type'}))

    payment_amount = forms.FloatField(label=_("Amount"),
                                      initial=30,
                                      max_value=1000,
                                      min_value=30,
                                      validators=[numeric],
                                      widget=forms.NumberInput(
                                      attrs={'class': "form-control",
                                             'placeholder': 'Enter Amount',
                                             'aria-label': "Enter Amount",
                                             'aria-describedby': "basic-addon2",
                                             'id': 'amount'})
                                      )

    promotion_package = forms.ModelChoiceField(label=_("Promotion Package"),
                                               initial=PromotionPackage.objects.first,
                                               queryset=PromotionPackage.objects.all(),
                                               widget=PromotionPackageCustomRadioSelect(
                                               attrs={'class': "form-control",
                                                      'id': 'promotion_package',
                                                      'autocomplete': False}))

    coupon_code = forms.CharField(label=_("Coupon Code"),
                                  max_length=20,
                                  min_length=8,
                                  widget=forms.TextInput(
                                  attrs={'class': "form-control",
                                         'placeholder': 'Enter Coupon Code',
                                         'id': 'inputCouponCode'})
                                  )


