from django.urls import path, re_path
from payment import views as payment_views

urlpatterns = [
    path('payment/', payment_views.PaymentView.as_view(), name='payment'),
    path('payment/cancelled/', payment_views.PaymentView.payment_cancelled, name='payment_cancelled'),
    path('payment/processed/', payment_views.PaymentView.payment_processed, name='payment_processed'),
    path('invoices/', payment_views.InvoiceView.as_view(), name='invoices'),
    path('invoices/generate_invoice/', payment_views.GeneratePDF.as_view(), name='generate_invoice'),
]