# -*- coding: utf-8 -*-

import time
from django.shortcuts import render
from django.http import HttpResponse


def ok(request):
    time.sleep(1)

    return HttpResponse('ok')

def fail(request):
    x = 1/0

