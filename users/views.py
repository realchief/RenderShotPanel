import json
import requests
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView, PasswordResetConfirmView

from django.shortcuts import render, redirect
from django.views.generic import FormView
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions

from users.forms import RegisterForm, LoginForm, UserPasswordResetForm, ProfileForm, UserPasswordChangeForm
from users.tokens import account_activation_token
from users.decorators import blocked_validation
from django.template.loader import render_to_string

from system.dbx_utils import DropboxHandler
from users.templatetags.gravatar import _gravatar

# rest framework imports
from rest_framework import permissions
from payment.models import *
from ipware import get_client_ip
from system import utils as system_utils


def is_recaptcha_valid(request):
    """
    Verify if the response for the Google recaptcha is valid.
    """
    result = requests.post('https://www.google.com/recaptcha/api/siteverify',
                           data={'secret': settings.RECAPTCHA_SECRET_KEY,
                                 'response': request.POST.get('captcha')},
                           verify=True).json().get("success", False)

    return result


class Register(FormView):

    template_name = 'registration/user_register_form.html'
    form_class = RegisterForm

    def form_valid(self, form):

        # logging.warning(self.request.POST.get('captcha'))
        #
        # if not is_recaptcha_valid(self.request):
        #     messages.error(self.request, 'Invalid reCAPTCHA. Please try again.')
        #     return redirect('register')

        user = form.save(commit=False)
        user.is_active = False
        user.save()
        return redirect('activate', username=user.username)

    def form_invalid(self, form):
        errors = json.loads(form.errors.as_json())
        for field, errors in errors.items():
            for error in errors:
                messages.error(self.request, f'{error["message"]}')

        return redirect('register')


class Login(LoginView):

    template_name = 'registration/user_login_form.html'
    form_class = LoginForm

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('dashboard')

        return super(Login, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        if not is_recaptcha_valid(request):
            messages.error(request, 'Invalid reCAPTCHA. Please try again.')
            return redirect('user_login')

        username = self.request.POST['username']
        password = self.request.POST['password1']
        remember = self.request.POST.get('remember_me', False)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'The username or password is incorrect')
            return redirect('user_login')

        if user.profile.blocked:
            messages.error(request, 'This account has been blocked for violating our terms, '
                                    'contact us if you think we made a mistake.')
            return redirect('user_login')

        if user.profile.reset_password_required:
            messages.error(request, 'Password reset is required to get your account access back.')
            return redirect('user_password_reset')

        if not user.is_active:
            return redirect('activate', username=user.username)
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            login(self.request, user)
            if not remember:
                self.request.session.set_expiry(0)

            # get user ip address when profile is ready
            client_ip, is_routable = get_client_ip(self.request)
            if client_ip:
                user.profile.ip_address = client_ip
                user.save()

            return redirect('dashboard')
        else:
            messages.error(request, 'The username or password is incorrect')
            return redirect('user_login')


class UserPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'
    extra_email_context = {'subject': 'Password Reset',
                           'description': 'Reset Your Account Password',
                           'p1': 'Please press the "Reset Password" button to initiate the password reset process.',
                           'p2': 'If clicking the link above dose not work, '
                                 'please copy and paste the URL in a new browser window instead.'}
    html_email_template_name = 'email/reset_password_email.html'
    form_class = UserPasswordResetForm

    def get_success_url(self):
        message = "We’ve emailed you instructions for setting your password, if an account exists with the email " \
                  "you entered. You should receive them shortly. If you don’t receive an email, please make sure " \
                  "you’ve entered the address you registered with, and check your spam folder."

        messages.success(self.request, message)
        return self.request.path


class UserPasswordChangeView(PasswordChangeView):
    template_name = 'registration/password_change_form.html'
    form_class = UserPasswordChangeForm
    success_url = reverse_lazy('profile')

    def get_success_url(self):
        message = "Your password was changed."

        messages.success(self.request, message)
        return super(UserPasswordChangeView, self).get_success_url()


class UserPasswordResetConfirmView(PasswordResetConfirmView):

    def form_valid(self, form):
        super_return = super().form_valid(form)
        form.user.profile.reset_password_required = False
        form.user.profile.save()
        return super_return


class Profile(FormView):

    template_name = 'users/profile.html'
    form_class = ProfileForm
    success_url = 'profile'

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        initial = super(Profile, self).get_initial()
        initial.update({
            'username': self.request.user.username,
            'email': self.request.user.email,
            'first_name': self.request.user.first_name,
            'last_name': self.request.user.last_name,
            'account_type': self.request.user.profile.account_type,
            'company_name': self.request.user.profile.company_name,
            'city': self.request.user.profile.city,
            'country': self.request.user.profile.country,
            'address': self.request.user.profile.address,
            'zip_code': self.request.user.profile.zip_code,
            'phone': self.request.user.profile.phone,
            'vat': self.request.user.profile.vat,
            'receive_job_email_notifs': self.request.user.profile.receive_job_email_notifs,
        })
        return initial

    def form_valid(self, form):
        user = self.request.user
        user.email = form.cleaned_data['email']
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.profile.account_type = form.cleaned_data['account_type']
        user.profile.company_name = form.cleaned_data['company_name']
        user.profile.city = form.cleaned_data['city']
        user.profile.country = form.cleaned_data['country']
        user.profile.address = form.cleaned_data['address']
        user.profile.zip_code = form.cleaned_data['zip_code']
        user.profile.phone = form.cleaned_data['phone']
        user.profile.vat = form.cleaned_data['vat']
        user.profile.receive_job_email_notifs = form.cleaned_data['receive_job_email_notifs']
        user.profile.payment_allowed = True
        user.save()

        if form.changed_data:
            messages.success(self.request, 'Profile updated successfully.')
        else:
            messages.info(self.request, 'No new changes made to profile.')
        return redirect('profile')


def activate(request, username='', token=''):
    user = User.objects.filter(username=username).first()
    if not user:
        messages.error(request, 'User data could not be fetched, make sure you are registered properly.')
        return redirect('user_login')

    if user.is_active:
        return redirect('dashboard')

    if account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)

        # create user dbx folders
        dbx = DropboxHandler(user)
        dbx.create_user_folders()
        request.user.profile.dropbox_outputs_share_link = dbx.get_user_outputs_share_link()

        # add initial credit
        system_setting = system_utils.get_system_setting()
        initial_credit = Payment.objects.create(user=user,
                                                status=PaymentStatus.COMPLETED,
                                                type=PaymentTypes.COUPON,
                                                payment_id=PaymentTypes.COUPON.label,
                                                amount=system_setting.initial_account_credit)
        initial_credit.save()
        return redirect('dashboard')

    current_site = get_current_site(request)
    site_name = current_site.name
    domain = current_site.domain
    token = account_activation_token.make_token(user)
    html = render_to_string('email/user_activation_email.html',
                            request=request,
                            context={'subject': 'Activate Account',
                                     'description': 'Welcome to RenderShot',
                                     'p1': 'Please press the "Activate" button to finish your account activation.',
                                     'token': token,
                                     'username': user.username,
                                     'current_site': current_site,
                                     'domain': domain,
                                     'site_name': site_name,
                                     'protocol': 'https',
                                     })

    user.email_user('Activate Account', "Activate Account", html_message=html)
    messages.success(request, 'A verification link has been sent to your email account.')
    return render(request, template_name='registration/user_activation_form.html', context={'user': user})


class UserAPI(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # get user avatar
        avatar_url = _gravatar(request.user.email)

        # get user output dropbox url
        dbx = DropboxHandler(request.user)
        dbx_outputs_url = dbx.get_user_outputs_link()

        return Response({"avatar_url": avatar_url,
                         "dropbox_outputs_url": dbx_outputs_url})

