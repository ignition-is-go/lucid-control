# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from .models import Workday, WorkdayOption, Profile, WorkdayResponse

class ProfileAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">assignment_ind</i>'

admin.site.register(Profile, ProfileAdmin)


class WorkdayOptionAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">playlist_add_check</i>'

admin.site.register(WorkdayOption, WorkdayOptionAdmin) 

class WorkdayResponseInline(admin.StackedInline):
    model=WorkdayResponse
    extra=0

    # def has_add_permission(self, request):
    #     return False
    def has_edit_permission(self, request, obj=None):
        return False
    # def has_delete_permission(self, request, obj=None):
    #     return False

    def get_formset(self, request, obj=None, **kwargs):
        """
        Override the formset function in order to remove the add and change buttons beside the foreign key pull-down
        menus in the inline.
        """
        formset = super(WorkdayResponseInline, self).get_formset(request, obj, **kwargs)
        form = formset.form
        widget = form.base_fields['response'].widget
        widget.can_add_related = False
        widget.can_change_related = False
        return formset
    
    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ('timestamp',)

class WorkdayAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">update</i>'
    date_hierarchy = "date"
    
    def response_count(self, obj):
        return obj.responses.count()
    response_count.short_description = "Response Count"

    list_display = ('__str__', 'response_count')

    # show responses
    inlines = [WorkdayResponseInline]

    # permissions
    def has_add_permission(self, request):
        return False
    # def has_delete_permission(self, request, obj=None):
    #     return False
    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            # All model fields as read_only
            return self.readonly_fields + tuple([item.name for item in obj._meta.fields])
        return self.readonly_fields

admin.site.register(Workday, WorkdayAdmin)