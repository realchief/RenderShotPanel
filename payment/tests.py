from django.test import TestCase
from django.contrib.auth.models import User
from payment.models import Payment, PaymentStatus


def create_fake_payments():
    user = User.objects.all().first()
    for i in range(100):
        payment = Payment(user=user, status=PaymentStatus.INITIATED, amount=10.0, payment_id=f"484844{i}")
        payment.save()


create_fake_payments()