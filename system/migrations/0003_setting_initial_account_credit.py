# Generated by Django 3.1 on 2021-03-31 15:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0002_setting_ban_disposable_emails'),
    ]

    operations = [
        migrations.AddField(
            model_name='setting',
            name='initial_account_credit',
            field=models.IntegerField(default=10, null=True),
        ),
    ]
