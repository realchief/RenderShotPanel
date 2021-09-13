import pytz
import requests

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, PasswordChangeForm
from django.utils.translation import gettext, gettext_lazy as _
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, RegexValidator

from users.models import AccountTypes
from system.utils import get_system_setting

from captcha.fields import ReCaptchaField
import captcha.widgets


def validate_disposable_email(value):
    system_setting = get_system_setting()
    if system_setting.ban_disposable_emails:
        is_disposable = False
        try:
            url = f'https://disposable.debounce.io/?email={value}'
            data = requests.get(url)
            is_disposable = data.json().get('disposable') == 'true'
        except Exception as err:
            print(err)

        if is_disposable:
            raise ValidationError(_("Sorry, the email address is invalid."), code='invalid')


def validate_unique_email(value):
    if User.objects.filter(email=value).exists():
        raise ValidationError(_('A user with that email address already exists. '),
                              params={'value': value},)


def validate_terms_of_service(value):
    if not value:
        raise ValidationError(_('Terms of Service must be accepted prior to registration.'),
                              params={'value': value},)


class RegisterForm(UserCreationForm):

    captcha = ReCaptchaField(public_key=settings.RECAPTCHA_SITE_KEY,
                             private_key=settings.RECAPTCHA_SECRET_KEY,
                             widget=captcha.widgets.ReCaptchaV3)

    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        validators=[validate_disposable_email, validate_email, validate_unique_email],
        widget=forms.EmailInput(attrs={'autocomplete': 'email',
                                       'class': "form-control",
                                       'placeholder': 'Email Address',
                                       'id': 'email'}))

    password1 = forms.CharField(label=_("Password"),
                                strip=False,
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password',
                                                                  'class': "form-control pull-left password_field",
                                                                  'placeholder': 'Password',
                                                                  'id': 'user_password',
                                                                  'data-toggle': "password",
                                                                  }),
                                help_text=password_validation.password_validators_help_text_html(),)

    password2 = forms.CharField(label=_("Password confirmation"),
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password',
                                                                  'class': "form-control pull-left password_field",
                                                                  'placeholder': 'Confirm Password',
                                                                  'id': 'user_password',
                                                                  'data-toggle': "password",
                                                                  }),
                                strip=False,
                                help_text=_("Enter the same password as before, for verification."),)

    username = forms.CharField(label=_("Username"),
                               strip=False,
                               validators=[RegexValidator(regex='^[a-zA-Z0-9]*$',
                                                          message='Username must be Alphanumeric',
                                                          code='invalid_username'), ],
                               widget=forms.TextInput(
                               attrs={'autocapitalize': 'none',
                                      'autocomplete': 'username',
                                      'class': "form-control",
                                      'placeholder': 'Username',
                                      'id': 'username'}))

    is_term_accepted = forms.BooleanField(required=False,
                                          validators=[validate_terms_of_service],
                                          widget=forms.CheckboxInput(attrs={'class': "custom-control-input",
                                                                            'id': "is_term_accepted"}),)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'is_term_accepted')


class LoginForm(AuthenticationForm):
    captcha = ReCaptchaField(public_key=settings.RECAPTCHA_SITE_KEY,
                             private_key=settings.RECAPTCHA_SECRET_KEY,
                             widget=captcha.widgets.ReCaptchaV3)

    password1 = forms.CharField(label=_("Password"),
                                strip=False,
                                widget=forms.PasswordInput(
                                attrs={'autocomplete': 'new-password',
                                       'class': "form-control pull-left password_field",
                                       'placeholder': 'Password',
                                       'data-toggle': "password",
                                       'id': 'user_password'}),
                                help_text=password_validation.password_validators_help_text_html(), )

    username = forms.CharField(label=_("Username"),
                               strip=False,
                               widget=forms.TextInput(
                               attrs={'autocapitalize': 'none',
                                      'autocomplete': 'username',
                                      'class': "form-control",
                                      'placeholder': 'Username', }))

    remember_me = forms.BooleanField(required=False,
                                     widget=forms.CheckboxInput(attrs={'class': "custom-control-input",
                                                                       'id': "remember"}),)

    class Meta:
        model = User
        fields = ('username', 'password1', 'remember_me')


class UserPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email',
                                       'class': "form-control",
                                       'placeholder': 'Email',
                                       'id': "user_or_mail"}))


class UserPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label=_("Old password"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password',
                                          'class': "form-control",
                                          'placeholder': 'Old Password',
                                          'autofocus': True}),
    )

    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password',
                                          'placeholder': 'New Password',
                                          'class': "form-control"}),
        strip=False,
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password',
                                          'placeholder': 'New Password Confirmation',
                                          'class': "form-control"}),
    )


class ProfileForm(forms.Form):
    username = forms.CharField(label=_("Username"),
                               disabled=True,
                               strip=False,
                               widget=forms.TextInput(
                               attrs={'autocapitalize': 'none',
                                      'autocomplete': 'username',
                                      'class': "form-control",
                                      'placeholder': 'UserName',
                                      'id': 'UserName'}))

    first_name = forms.CharField(label=_("First Name"),
                                 strip=False,
                                 widget=forms.TextInput(
                                 attrs={'autocapitalize': 'none',
                                        'autocomplete': 'first_name',
                                        'class': "form-control",
                                        'placeholder': 'First Name',
                                        'id': 'FirstName'}))

    email = forms.EmailField(label=_("Email"),
                             max_length=254,
                             widget=forms.EmailInput(attrs={'autocomplete': 'email',
                                                            'class': "form-control",
                                                            'placeholder': 'Email Address',
                                                            'id': "EmailAddress"}))

    last_name = forms.CharField(label=_("Last Name"),
                                strip=False,
                                widget=forms.TextInput(
                                attrs={'autocapitalize': 'none',
                                       'autocomplete': 'last_name',
                                       'class': "form-control",
                                       'placeholder': 'Last Name',
                                       'id': 'LastName'}))

    account_type = forms.ChoiceField(label=_("Account Type"),
                                     choices=AccountTypes.choices,
                                     widget=forms.Select(
                                     attrs={'autocapitalize': 'none',
                                            'autocomplete': 'account_type',
                                            'class': "form-control",
                                            'id': 'AccountType'})
                                     )

    phone = forms.CharField(label=_("Phone"),
                            strip=False,
                            required=False,
                            widget=forms.TextInput(
                            attrs={'autocapitalize': 'none',
                                   'autocomplete': 'account_type',
                                   'class': "form-control",
                                   'placeholder': 'Phone Number',
                                   'id': 'Phone'}))

    company_name = forms.CharField(label=_("Company Name"),
                                   strip=False,
                                   required=False,
                                   widget=forms.TextInput(
                                   attrs={'autocapitalize': 'none',
                                          'autocomplete': 'company_name',
                                          'class': "form-control",
                                          'placeholder': 'Company Name',
                                          'id': 'Company'}))

    address = forms.CharField(label=_("Address"),
                              strip=False,
                              widget=forms.TextInput(
                              attrs={'autocapitalize': 'none',
                                     'autocomplete': 'address',
                                     'class': "form-control",
                                     'placeholder': 'Address',
                                     'id': 'Address'}))

    zip_code = forms.CharField(label=_("Zip Code"),
                               strip=False,
                               widget=forms.TextInput(
                               attrs={'autocapitalize': 'none',
                                      'autocomplete': 'zip_code',
                                      'class': "form-control",
                                      'placeholder': 'Zip Code',
                                      'id': 'ZipCode'}))

    country = forms.ChoiceField(label=_("Country"),
                                choices=pytz.country_names.items(),
                                widget=forms.Select(
                                attrs={'autocapitalize': 'none',
                                       'autocomplete': 'country',
                                       'class': "form-control",
                                       'id': 'Country'}))

    city = forms.CharField(label=_("City"),
                           strip=False,
                           widget=forms.TextInput(
                           attrs={'autocapitalize': 'none',
                                  'autocomplete': 'city',
                                  'class': "form-control",
                                  'placeholder': 'City',
                                  'id': 'City'}))

    vat = forms.CharField(label=_("VAT"),
                          required=False,
                          help_text='Only for European Union Countries',
                          strip=False,
                          widget=forms.TextInput(
                          attrs={'autocapitalize': 'none',
                                 'autocomplete': 'vat',
                                 'class': "form-control",
                                 'placeholder': 'VAT',
                                 'id': 'VAT'}))

    receive_job_email_notifs = forms.BooleanField(required=False,
                                                  widget=forms.CheckboxInput(
                                                      attrs={'class': "custom-control-input",
                                                             'id': "ChangePlanJobsAppNotification"}))
