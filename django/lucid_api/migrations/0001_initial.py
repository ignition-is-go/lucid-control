# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-05 21:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Project Title')),
            ],
            options={
                'verbose_name': 'Project',
                'verbose_name_plural': 'Projects',
            },
        ),
        migrations.CreateModel(
            name='ProjectType',
            fields=[
                ('character_code', models.CharField(max_length=1, primary_key=True, serialize=False, verbose_name='Character Code')),
                ('description', models.CharField(max_length=500, verbose_name='Project Type')),
            ],
            options={
                'verbose_name': 'Project Type',
            },
        ),
        migrations.CreateModel(
            name='ServiceConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(choices=[(b'dropbox_service', b'Dropbox'), (b'ftrack_service', b'ftrack'), (b'groups_service', b'Google Groups'), (b'slack_service', b'Slack'), (b'xero_service', b'Xero')], max_length=200, verbose_name='Service Name')),
                ('connection_name', models.CharField(blank=True, default='', help_text='Used by some connection types to identify multiple connections', max_length=200)),
                ('identifier', models.CharField(blank=True, help_text='If left blank, a new connection to this service will be created.', max_length=500)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='services', to='lucid_api.Project')),
            ],
        ),
        migrations.CreateModel(
            name='TemplateProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='TemplateServiceConnection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(choices=[(b'dropbox_service', b'Dropbox'), (b'ftrack_service', b'ftrack'), (b'groups_service', b'Google Groups'), (b'slack_service', b'Slack'), (b'xero_service', b'Xero')], max_length=200, verbose_name='Service Name')),
                ('connection_name', models.CharField(blank=True, default='', max_length=200)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='services', to='lucid_api.TemplateProject')),
            ],
        ),
        migrations.AddField(
            model_name='project',
            name='type_code',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lucid_api.ProjectType'),
        ),
    ]
