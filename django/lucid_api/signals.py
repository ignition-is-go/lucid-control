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
    # Template project assembly on new project
    logger.info("Got signal for create project: %s", instance.title)
    if created:
        template = TemplateProject.objects.all()[0]
        for template_connection in template.services.all():
            new_service = ServiceConnection( 
                project=instance,
                service_name=template_connection.service_name,
                connection_name=template_connection.connection_name
            )
            new_service.save()

    # catch renames here as well
    
post_save.connect(
    execute_after_create_project, 
    sender=Project,
    dispatch_uid="template_project_setup")

logger.info("Connected template project handler")

# Auto create new service connections if identifier is blank
@receiver(post_save, sender=ServiceConnection, dispatch_uid="service_signals")
def execute_after_create(sender, instance, created, raw, using, update_fields, *args, **kwargs):
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
    

    return