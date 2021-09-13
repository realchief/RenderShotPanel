import datetime

from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import View, ListView
from django.utils.decorators import method_decorator
from django.http import HttpResponse

from payment.forms import PaymentForm
from users.decorators import blocked_validation
from payment.models import PromotionPackage, CouponCodes, Payment, PaymentStatus, PaymentTypes
from payment.mixins import PaypalCreateOrderMixin, PaypalCaptureOrderMixin
from payment.utils import render_pdf_view
from system import utils as system_utils


class PaymentView(View):
    template_name = 'payment/payment.html'

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        payment_form = PaymentForm()
        return render(self.request,
                      template_name=self.template_name,
                      context={'user': self.request.user,
                               "payment_form": payment_form,
                               'promotion_packages': PromotionPackage.objects.all()})

    def post(self, request, *args, **kwargs):

        request_types = {'process_fund': self.process_fund,
                         'process_package': self.process_package,
                         'process_coupon': self.process_coupon}

        if 'request_type' not in request.POST:
            messages.error(request, 'Request is not valid.')
            return redirect('payment')

        try:
            return request_types[request.POST['request_type']]()
        except Exception as err:
            messages.error(request, 'Something went wrong with processing request.')
            return redirect('payment')

    def process_coupon(self):
        posted_code = self.request.POST.get('coupon_code', None)
        coupon = CouponCodes.objects.filter(code=posted_code).first()

        if not coupon:
            messages.error(self.request, 'Coupon code is not valid.')
            return redirect('payment')

        if coupon.is_redeemed:
            messages.warning(self.request, 'This coupon code has already been redeemed.')
            return redirect('payment')

        coupon.is_redeemed = True
        coupon.save()

        payment = Payment(user=self.request.user,
                          type=PaymentTypes.COUPON,
                          payment_id=PaymentTypes.COUPON.label,
                          status=PaymentStatus.COMPLETED,
                          amount=coupon.amount)
        payment.save()
        messages.success(self.request, f'Coupon code is redeemed and {coupon.amount} USD added to your credits.')
        return redirect('payment')

    def process_fund(self):
        system_setting = system_utils.get_system_setting()
        amount = self.request.POST.get('payment_amount')
        minimum_amount = system_setting.minimum_payment_amount
        if minimum_amount > int(amount):
            messages.error(self.request, f'Entered amount is lower that the minimum valid amount of ${minimum_amount}.')
            return redirect('payment')

        return self.make_payment(amount)

    def process_package(self):
        posted_package_id = self.request.POST.get('promotion_package', None)
        package = PromotionPackage.objects.filter(pk=posted_package_id).first()
        if posted_package_id and package:
            return self.make_payment(package.amount)

        messages.error(self.request, 'Could not process selected payment package.')
        return redirect('payment')

    def make_payment(self, amount):
        payment = Payment(user=self.request.user,
                          status=PaymentStatus.INITIATED,
                          amount=amount)

        if not payment:
            messages.error(self.request, 'Payment record could not be initiated.')
            return redirect('payment')

        order_url = ''
        order_object = PaypalCreateOrderMixin()

        try:
            order_response, order_url = order_object.create_order(payment.amount, request=self.request)
            payment.order_data = order_response.result.__dict__.get("_dict", dict())
            payment.payment_id = order_response.result.id
            payment.status = PaymentStatus.PENDING
        except Exception as err:
            messages.error(self.request, 'PayPal Payment record could not be initiated.')
            payment.status = PaymentStatus.CANCELLED

        payment.save()
        return redirect(order_url or 'payment')

    @staticmethod
    def payment_processed(request, *args, **kwargs):
        token = request.GET.get('token', None)
        payment = Payment.objects.filter(payment_id=token).first()
        if not payment:
            payment.status = PaymentStatus.CANCELLED
            payment.save()
            messages.error(request, 'Something wrong with payment system.')
            return redirect('payment')

        if payment.status == PaymentStatus.COMPLETED:
            messages.warning(request, 'Payment has already been been processed')
        elif payment.status == PaymentStatus.PENDING:
            # calculating extra promotion credits
            package = PromotionPackage.objects.filter(amount=payment.amount).first()
            extra_credits = 0.0
            if package:
                extra_credits = (payment.amount / 100) * package.extra
                Payment.objects.create(user=request.user,
                                       amount=extra_credits,
                                       status=PaymentStatus.COMPLETED,
                                       payment_id=package.description,
                                       type=PaymentTypes.PROMOTION)

            try:
                capture_object = PaypalCaptureOrderMixin()
                captured_payment = capture_object.capture_order(token)
                payment.payment_data = captured_payment.result.__dict__.get("_dict", dict())
                payment.status = PaymentStatus.COMPLETED
                messages.success(request, f'Payment has been successfully processed '
                                          f'{payment.amount + extra_credits} USD added to your credits.')
                request.user.save()
                payment.save()
            except Exception as err:
                messages.error(request, 'Something went wrong with payment system.')
        else:
            messages.warning(request, 'Payment status could not be validated.')

        return redirect('payment')

    @staticmethod
    def payment_cancelled(request, *args, **kwargs):
        payment = Payment.objects.filter(payment_id=request.GET.get('token', None)).first()
        if payment:
            payment.status = PaymentStatus.CANCELLED
            payment.save()
        messages.warning(request, 'Payment cancelled.')
        return redirect('payment')


class InvoiceView(ListView):
    model = Payment
    paginate_by = 10
    context_object_name = 'payments'
    template_name = 'payment/invoices.html'
    ordering = ['-date_created']

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        self.queryset = Payment.objects.filter(user=self.request.user).exclude(status=PaymentStatus.CANCELLED)
        return super(InvoiceView, self).get_queryset()


class GeneratePDF(View):

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        payment_id = request.GET.get('payment_id', "")
        payment = Payment.objects.filter(type=PaymentTypes.PAYPAL, payment_id=payment_id).first()

        admin = User.objects.filter(username='admin', is_superuser=True).first()
        if not payment:
            messages.error(request, 'Payment record could not be found.')
            return redirect('invoices')

        data = {'user': request.user,
                'admin': admin,
                'today': datetime.date.today(),
                'payment': payment,
                }

        pdf = render_pdf_view('payment/invoice_template.html', data)
        return HttpResponse(pdf, content_type='application/pdf')
