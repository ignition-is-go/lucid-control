# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-07 23:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lucid_api', '0006_projecttype_is_default'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='projecttype',
            name='is_default',
        ),
        migrations.AlterField(
            model_name='project',
            name='type_code',
            field=models.ForeignKey(default='P', on_delete=django.db.models.deletion.CASCADE, to='lucid_api.ProjectType', verbose_name='Type'),
        ),
    ]
