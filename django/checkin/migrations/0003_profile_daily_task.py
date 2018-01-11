# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-02 22:50
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('django_celery_beat', '0001_initial'),
        ('checkin', '0002_remove_profile_daily_checkin_beat'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='daily_task',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='django_celery_beat.PeriodicTask', verbose_name='Daily Check-in Schedule'),
        ),
    ]
