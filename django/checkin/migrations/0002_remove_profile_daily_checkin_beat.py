# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-01-02 22:45
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checkin', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='daily_checkin_beat',
        ),
    ]
