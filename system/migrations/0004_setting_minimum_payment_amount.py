# Generated by Django 3.1 on 2021-04-01 15:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0003_setting_initial_account_credit'),
    ]

    operations = [
        migrations.AddField(
            model_name='setting',
            name='minimum_payment_amount',
            field=models.IntegerField(default=30, null=True),
        ),
    ]
