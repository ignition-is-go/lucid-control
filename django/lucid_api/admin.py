# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Project, ProjectType, ServiceConnection
# Register your models here.

admin.site.register(ProjectType)

class ServiceConnectionInline(admin.StackedInline):
    model = ServiceConnection
    extra = 0

class ProjectAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['type_code', 'title']}),
    ]
    inlines = [ServiceConnectionInline]

admin.site.register(Project, ProjectAdmin)