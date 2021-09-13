# Generated by Django 3.1 on 2021-02-02 19:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CouponCodes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(blank=True, max_length=20, null=True, unique=True)),
                ('is_redeemed', models.BooleanField(default=False, null=True)),
                ('amount', models.FloatField(blank=True, default=0.0, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PromotionPackage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, null=True)),
                ('description', models.CharField(max_length=100, null=True)),
                ('amount', models.FloatField(default=0.0, null=True)),
                ('extra', models.IntegerField(default=0, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('paypal', 'Paypal'), ('coupon', 'Coupon')], default='paypal', max_length=100, null=True)),
                ('status', models.CharField(choices=[('initiated', 'Initiated'), ('pending', 'Pending'), ('completed', 'Completed'), ('refunded', 'Refunded'), ('cancelled', 'Cancelled'), ('invalid', 'Invalid')], default='initiated', max_length=100, null=True)),
                ('amount', models.FloatField(default=5.0, null=True)),
                ('payment_id', models.CharField(blank=True, max_length=200, null=True)),
                ('order_data', models.JSONField(blank=True, null=True)),
                ('payment_data', models.JSONField(blank=True, null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('currency', models.CharField(choices=[('usd', 'usd')], default='usd', max_length=100, null=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
