# Generated by Django 3.1 on 2021-03-31 15:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0013_auto_20210322_0627'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobstatus',
            name='is_upgradable',
            field=models.BooleanField(default=False, null=True),
        ),
    ]