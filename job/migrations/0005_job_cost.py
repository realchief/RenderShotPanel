# Generated by Django 3.1 on 2021-03-09 20:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0004_auto_20210302_1632'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='cost',
            field=models.FloatField(blank=True, default=0.0, null=True),
        ),
    ]
