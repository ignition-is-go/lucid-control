# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-10 00:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lucid_api', '0007_auto_20171207_1547'),
    ]

    operations = [
        migrations.AddField(
            model_name='serviceconnection',
            name='state_message',
            field=models.CharField(blank=True, default='', max_length=1000, verbose_name='Status'),
        ),
    ]
