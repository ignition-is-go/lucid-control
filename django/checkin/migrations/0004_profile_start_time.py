# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-02 06:32
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checkin', '0003_auto_20180201_1652'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='start_time',
            field=models.TimeField(default=datetime.time(9, 1), verbose_name='Workday Start Time'),
        ),
    ]