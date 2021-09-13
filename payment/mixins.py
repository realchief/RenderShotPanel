import logging

from django.urls import reverse

from paypalcheckoutsdk.core import PayPalHttpClient, SandboxEnvironment, LiveEnvironment
from paypalcheckoutsdk.orders import OrdersCreateRequest
from paypalcheckoutsdk.orders import OrdersCaptureRequest

from system import utils as system_utils

logging.basicConfig(level=logging.DEBUG)


class PaypalMixin:
    try:
        system_setting = system_utils.get_system_setting()
        environment = LiveEnvironment(client_id=system_setting.paypal_setting.get('paypal_client_id'),
                                      client_secret=system_setting.paypal_setting.get('paypal_secret_id') )
        client = PayPalHttpClient(environment)
    except Exception as err:
        pass


class PaypalCreateOrderMixin(PaypalMixin):

    @staticmethod
    def build_create_request_body(amount, *args, **kwargs):
        """Method to create body with CAPTURE intent"""
        source_request = kwargs.get('request')
        return_url = source_request.build_absolute_uri(reverse('payment_processed'))
        cancel_url = source_request.build_absolute_uri(reverse('payment_cancelled'))

        application_context = {
            "return_url": kwargs.get('return_url', return_url),
            "cancel_url": kwargs.get('cancel_url', cancel_url),
            "brand_name": "RenderShot",
            "landing_page": "BILLING",
            "user_action": "CONTINUE"}

        shipping = {"method": "United States Postal Service",
                    "name": {"full_name": "John Doe"},
                    "address": {"address_line_1": "123 Townsend St",
                                "address_line_2": "Floor 6",
                                "admin_area_2": "San Francisco",
                                "admin_area_1": "CA",
                                "postal_code": "94107",
                                "country_code": "US"}}

        items = [{"name": "KeyShotRenderingService",
                  "description": "KeyShot CPU Rendering Service Credits",
                  "unit_amount": {"currency_code": "USD", "value": amount},
                  "quantity": "1",
                  "category": "DIGITAL_GOODS"},]

        purchase_units = [{
            "amount": {"currency_code": "USD", "value": amount},
            }]

        data = {"intent": "CAPTURE",
                "application_context": application_context,
                "purchase_units": purchase_units}
        return data

    def create_order(self, amount, *args, **kwargs):
        """ This is the sample function which can be sued to create an order. It uses the
            JSON body returned by buildRequestBody() to create an new Order."""

        return_url = ''
        request = OrdersCreateRequest()
        request.headers['prefer'] = 'return=representation'
        request.request_body(self.build_create_request_body(amount, *args, **kwargs))
        response = self.client.execute(request)

        for link in response.result.links:
            if link.rel == "approve":
                return_url = link.href
                break

        if return_url:
            return response, return_url


class PaypalCaptureOrderMixin(PaypalMixin):
    """this is the sample function performing payment capture on the order.
    Approved Order id should be passed as an argument to this function"""

    def capture_order(self, order_id):
        """Method to capture order using order_id"""
        request = OrdersCaptureRequest(order_id)
        response = self.client.execute(request)

        return response
