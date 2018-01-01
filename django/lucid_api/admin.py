# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Project, ProjectType, ServiceConnection, TemplateProject, TemplateServiceConnection
# Register your models here.


class ServiceConnectionInline(admin.StackedInline):
    model = ServiceConnection
    extra = 0

class ProjectAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,{'fields': [
            'type_code',
            'title',
            'is_archived'
            ]}
        ),
    ]
    inlines = [ServiceConnectionInline]

admin.site.register(Project, ProjectAdmin)

admin.site.register(ProjectType)

#### TEMPLATE PROJECT STUFF

class TemplateServiceConnectionInline(admin.StackedInline):
    model = TemplateServiceConnection
    extra = 0

class TemplateProjectAdmin(admin.ModelAdmin):
    ''' for the template project editing '''
    fieldsets = []
    inlines = [TemplateServiceConnectionInline]

    # We disable the creation of new templates and deletion of the existing, there can only be one!
    def has_add_permission(self, request):
        # disable add
        return False

    def get_action(self, request):
        # disable delete
        actions = super(TemplateProjectAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        # disable delete
        return False

admin.site.register(TemplateProject, TemplateProjectAdmin)