# -*- coding: utf-8 -*-

import time
from django.shortcuts import render
from django.http import HttpResponse


def allow(request):
    time.sleep(1)

    return HttpResponse('allow')


def forbid(request):
    time.sleep(1)

    return HttpResponse('forbid')

