# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.contrib import admin

from .models import Workday, WorkdayOption, Profile, DayOff

logger = logging.getLogger(__name__)

class DayOffInline(admin.StackedInline):
    model=DayOff
    extra=0
    verbose_name="Day Off"
    verbose_name_plural="Days Off"
    def get_formset(self, request, obj=None, **kwargs):
        """
        Override the formset function in order to remove the add and change buttons beside the foreign key pull-down
        menus in the inline.
        """
        formset = super(DayOffInline, self).get_formset(request, obj, **kwargs)
        form = formset.form
        widget = form.base_fields['user'].widget
        widget.can_add_related = False
        widget.can_change_related = False
        return formset

class ProfileAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">assignment_ind</i>'

    inlines = (DayOffInline,)

    # days off

    def available_vacation_days(self, obj):
        accrued, used = obj.days('vacation')
        return accrued - used

    def available_sick_days(self, obj):
        accrued, used = obj.days('sick')
        return accrued - used

    def available_flex_days(self, obj):
        accrued, used = obj.days('flex')
        return accrued - used

    # list view
    list_display = ('__str__', 'available_flex_days', 'available_vacation_days', 'available_sick_days')

admin.site.register(Profile, ProfileAdmin)


class WorkdayOptionAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">playlist_add_check</i>'

admin.site.register(WorkdayOption, WorkdayOptionAdmin) 

# class WorkdayResponseInline(admin.StackedInline):
#     model=WorkdayResponse
#     extra=0
#     verbose_name="Response"
#     verbose_name_plural="Responses"

#     # def has_add_permission(self, request):
#     #     return False
#     def has_edit_permission(self, request, obj=None):
#         return False
#     # def has_delete_permission(self, request, obj=None):
#     #     return False

#     def get_formset(self, request, obj=None, **kwargs):
#         """
#         Override the formset function in order to remove the add and change buttons beside the foreign key pull-down
#         menus in the inline.
#         """
#         formset = super(WorkdayResponseInline, self).get_formset(request, obj, **kwargs)
#         form = formset.form
#         widget = form.base_fields['response'].widget
#         widget.can_add_related = False
#         widget.can_change_related = False
#         return formset
    
#     def get_readonly_fields(self, request, obj=None):
#         return self.readonly_fields + ('timestamp',)

class WorkdayAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">update</i>'
    date_hierarchy = "date"
    
    def get_response(self, obj):
        return obj.response or "(waiting...)"
    get_response.short_description = "Response"

    list_display = ('__str__', 'get_response')

    # permissions
    def has_add_permission(self, request):
        return False
    # def has_delete_permission(self, request, obj=None):
    #     return False

    # disable adding more response types
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

    # make all fields readonly execpt a couple
    def get_readonly_fields(self, request, obj=None):
        if obj: # editing an existing object
            # All model fields as read_only
            # except skip:
            skip = ["response"]
            fields =[]
            for item in obj._meta.fields:
                logging.debug("Checking readonly for %s", item.name)
                if not item.name in skip:
                    fields.append(item.name)

            read_only = self.readonly_fields + tuple(fields)
            return read_only
        return self.readonly_fields

admin.site.register(Workday, WorkdayAdmin)