# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.apps import AppConfig


class LucidApiConfig(AppConfig):
    logger = logging.getLogger(__name__)
    name = 'lucid_api'

    verbose_name = "Lucid Control"

    icon = '<i class="material-icons">settings_input_component</i>'

    def ready(self):
        self.logger.info("Importing signals")
        from lucid_api import signals
