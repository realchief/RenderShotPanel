# Generated by Django 3.1 on 2021-03-10 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_profile_dropbox_outputs_share_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='rate_multiplier',
            field=models.FloatField(default=1.0, null=True),
        ),
    ]