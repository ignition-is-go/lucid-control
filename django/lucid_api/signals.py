# -*- coding: utf-8 -*-
'''
signals for automating things on the back end of the api

handles :
- creating template project connections
- service level interactions from the ServiceConnection model
'''
from __future__ import unicode_literals
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Project, ServiceConnection, TemplateProject
from .tasks import service_task, ServiceAction

logger = logging.getLogger(__name__)
logger.info("Setting up signals!")

# @receiver(post_save, sender=Project)
def execute_after_create_project(sender, instance, created, raw, using, update_fields, *args, **kwargs):
    '''
    Handles automation on creation or change of a project
    '''

    if created:
        # Template project assembly on new project
        logger.info("Got CREATE signal on %s", instance.title)
        template = TemplateProject.objects.all()[0]
        for template_connection in template.services.all():
            new_service = ServiceConnection( 
                project=instance,
                service_name=template_connection.service_name,
                connection_name=template_connection.connection_name
            )
            new_service.save()

    # catch rename and archive here as well
    else:
        # NOTE: it's possible that a rename and an archive event to happen concurrently
        changed_fields = instance.get_dirty_fields().keys()
        logger.info("Project %s has changed fields: %s", instance, changed_fields)

        # RENAME CASE
        if "title" in changed_fields or "type_code" in changed_fields:
            logger.info("Got RENAME signal on %s", instance)
            # iterate through all services and perform the action
            for service in instance.services.all():
                service_task.delay(
                    ServiceAction.RENAME,
                    service.id
                )     

        # ARCHIVE/UNARCHIVE CASE
        if "is_archived" in changed_fields:
            if instance.is_archived:
                # ARCHIVE CASE
                logger.info("Got ARCHIVE signal on %s", instance)
                # iterate through all services and perform the action
                for service in instance.services.all():
                    service.is_archived = True
                    service.save()
            else:
                # UNARCHIVE CASE
                logger.info("Got UNARCHIVE signal on %s", instance)
                # iterate through all services and perform the action
                for service in instance.services.all():
                    service.is_archived = False
                    service.save()

    
post_save.connect(
    execute_after_create_project, 
    sender=Project,
    dispatch_uid="template_project_setup")

logger.info("Connected template project handler")

# Auto create new service connections if identifier is blank
@receiver(post_save, sender=ServiceConnection, dispatch_uid="service_signals")
def execute_after_create_service(sender, instance, created, raw, using, update_fields, *args, **kwargs):
    if created:
        # make a new connection only when we create new instances
        logger.info( "Got signal to create service: %s=%s", instance.service_name, instance.identifier)
        # if the identifier has been provided, we don't need to create it
        if instance.identifier == "":
            # send celery the creation task
            service_task.delay(
                ServiceAction.CREATE,
                instance.id
                )
    
    else:
        
        # check for changes to name and archive state
        # NOTE: it's possible that a rename and an archive event to happen concurrently
        changed_fields = instance.get_dirty_fields().keys()
        logger.info("Project %s has changed fields: %s", instance, changed_fields)

        # RENAME CASE
        if "connection_name" in changed_fields:
            logger.info("Got connection RENAME signal on %s", instance)
            # iterate through all services and perform the action
            service_task.delay(
                ServiceAction.RENAME,
                instance.id
            )     

        # ARCHIVE/UNARCHIVE CASE
        if "is_archived" in changed_fields:
            if instance.is_archived:
                # ARCHIVE CASE
                logger.info("Got ARCHIVE signal on %s", instance)
                # iterate through all services and perform the action
                service_task.delay(
                    ServiceAction.ARCHIVE,
                    instance.id
                ) 

            else:
                # UNARCHIVE CASE
                logger.info("Got UNARCHIVE signal on %s", instance)
                # iterate through all services and perform the action
                service_task.delay(
                    ServiceAction.UNARCHIVE,
                    instance.id
                )
    return