# Generated by Django 3.1 on 2021-04-09 22:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0004_auto_20210409_2106'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='type',
            field=models.CharField(choices=[('paypal', 'Paypal'), ('coupon', 'Coupon'), ('credit_refund', 'Credit Refund'), ('payment_refund', 'Payment Refund'), ('credit_transfer', 'Credit Transfer'), ('promotion', 'Promotion')], default='paypal', max_length=100, null=True),
        ),
    ]