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

    ordering = ('-date',)

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

class DayOffAdmin(admin.ModelAdmin):
    '''
    Days off list
    '''
    model=DayOff
    icon='<i class="material-icons">nature_people</i>'

    ordering = ('-date',)

    list_display = ('date', 'user', 'type','amount', 'note')
    list_filter = ('user', 'type', 'date', 'note')
    

class ProfileAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">assignment_ind</i>'

    inlines = (DayOffInline,)
    fieldsets = [
        (None, {
            'fields': [
                'user',
                'slack_user',
                'start_time',
                'is_active'
            ]
        })
    ]

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


class WorkdayOptionAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">playlist_add_check</i>'


class WorkdayAdmin(admin.ModelAdmin):
    icon='<i class="material-icons">update</i>'
    date_hierarchy = "date"
    
    def get_response(self, obj):
        return obj.response or "(waiting...)"
    get_response.short_description = "Response"

    list_display = ('__str__', 'get_response')

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


# Register in order of usefullness

admin.site.register(Workday, WorkdayAdmin)
admin.site.register(DayOff,DayOffAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(WorkdayOption, WorkdayOptionAdmin) 
