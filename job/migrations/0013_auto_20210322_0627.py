# Generated by Django 3.1 on 2021-03-22 06:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0012_joberror_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobstatus',
            name='is_deletable',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AddField(
            model_name='jobstatus',
            name='is_suspendable',
            field=models.BooleanField(default=False, null=True),
        ),
    ]
