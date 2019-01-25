# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin


from .models import Project, ProjectType, ServiceConnection, TemplateProject, TemplateServiceConnection
# Register your models here.


class ServiceConnectionInlineExisting(admin.StackedInline):
    model = ServiceConnection
    extra = 0
    verbose_name_plural = "Existing Service Connections"

    fieldsets = [
        (None, {
            'fields': [
                'service_name',
                'connection_name',
                'identifier',
                'is_messenger',
                'is_archived',
                'state_message',
            ]
        })
    ]

    def get_readonly_fields(self, request, obj=None):
        read_only = ['state_message']

        if obj:
            # we're not creating, just updating
            read_only.append('service_name')

        return self.readonly_fields + tuple(read_only)

    def has_add_permission(self, request):
        return False


class ServiceConnectionInlineAdd(admin.StackedInline):
    model = ServiceConnection
    extra = 0
    verbose_name_plural = "Add a Service Connection"

    fieldsets = [
        (None, {
            'fields': [
                'service_name',
                'connection_name',
                'identifier',
                'is_messenger',
                'is_archived',
            ]
        })
    ]

    def get_readonly_fields(self, request, obj=None):
        read_only = ['state_message']

        return self.readonly_fields + tuple(read_only)

    def has_change_permission(self, request, obj=None):
        return False

# projects is Import/Export enabled!


class ProjectAdmin():
    icon = '<i class="material-icons">work</i>'

    def is_active(self, obj=None):
        '''for list display'''
        return not obj.is_archived

    is_active.short_description = "Active"
    is_active.boolean = True

    list_display = ('id', 'title', 'is_active')
    list_display_links = ('id', 'title')
    list_filter = ('is_archived',)

    fieldsets = [
        (None, {'fields': [
            'type_code',
            'title',
            'is_archived'
        ]}
        ),
    ]
    inlines = [ServiceConnectionInlineExisting, ServiceConnectionInlineAdd]

    def queryset(self, request):
        qs = super(EntryAdmin, self).queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            return qs.filter(is_archived=False)


admin.site.register(Project, ProjectAdmin)


class ProjectTypeAdmin(admin.ModelAdmin):
    icon = '<i class="material-icons">menu</i>'


admin.site.register(ProjectType, ProjectTypeAdmin)

# TEMPLATE PROJECT STUFF


class TemplateServiceConnectionInline(admin.StackedInline):
    model = TemplateServiceConnection
    extra = 0


class TemplateProjectAdmin(admin.ModelAdmin):
    ''' for the template project editing '''
    fieldsets = []
    inlines = [TemplateServiceConnectionInline]
    icon = '<i class="material-icons">add_to_photos</i>'

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
