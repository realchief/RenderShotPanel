# Generated by Django 3.1 on 2021-03-10 02:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('job', '0006_renderplan_display_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobError',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('error', models.CharField(blank=True, max_length=500, null=True)),
                ('description', models.CharField(blank=True, max_length=2000, null=True)),
                ('solution', models.CharField(blank=True, max_length=2000, null=True)),
                ('software', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='job.software')),
            ],
        ),
        migrations.AddField(
            model_name='job',
            name='error',
            field=models.ManyToManyField(to='job.JobError'),
        ),
    ]
