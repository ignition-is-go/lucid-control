# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse

import os
# Create your views here.

def index(request):
    return HttpResponse(os.environ.get("LOG_LEVEL"))