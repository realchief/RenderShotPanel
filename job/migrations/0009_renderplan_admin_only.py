# Generated by Django 3.1 on 2021-03-10 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0008_auto_20210310_0305'),
    ]

    operations = [
        migrations.AddField(
            model_name='renderplan',
            name='admin_only',
            field=models.BooleanField(default=False, null=True),
        ),
    ]
