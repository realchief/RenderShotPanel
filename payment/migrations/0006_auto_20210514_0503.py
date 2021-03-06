# Generated by Django 3.1 on 2021-05-14 05:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0005_auto_20210409_2219'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[('initiated', 'Initiated'), ('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('invalid', 'Invalid')], default='initiated', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='payment',
            name='type',
            field=models.CharField(choices=[('paypal', 'Paypal'), ('coupon', 'Coupon'), ('credit_refund', 'Credit Refund'), ('payment_refund', 'Payment Refund'), ('credit_transfer', 'Credit Transfer'), ('promotion', 'Promotion'), ('cost_balance', 'Cost Balance')], default='paypal', max_length=100, null=True),
        ),
    ]
